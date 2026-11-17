"""Fase 04a: ciclo de vida estricto de proxies MLOD."""

import itertools
import math
import re

import pytest

from builders import build_cube_p3d
from helpers import read_p3d, write_bytes


IDENTITY = (
    (1.0, 0.0, 0.0),
    (0.0, 1.0, 0.0),
    (0.0, 0.0, 1.0),
)
ENGINE_CORRECTION = (
    (-1.0, 0.0, 0.0),
    (0.0, 0.0, 1.0),
    (0.0, 1.0, 0.0),
)
ROT_Y90 = (
    (0.0, 0.0, -1.0),
    (0.0, 1.0, 0.0),
    (1.0, 0.0, 0.0),
)


def _matrix_close(actual, expected, tolerance=1e-9):
    for row_actual, row_expected in zip(actual, expected):
        assert tuple(row_actual) == pytest.approx(
            tuple(row_expected), abs=tolerance
        )


def _matrix_multiply(left, right):
    return tuple(
        tuple(
            sum(left[row][inner] * right[inner][column] for inner in range(3))
            for column in range(3)
        )
        for row in range(3)
    )


def _transform_triangle(matrix, triangle):
    return tuple(
        tuple(
            sum(matrix[row][column] * point[column] for column in range(3))
            for row in range(3)
        )
        for point in triangle
    )


def _lod_snapshot(lod):
    point_index = {id(point): index for index, point in enumerate(lod.points)}
    face_index = {id(face): index for index, face in enumerate(lod.faces)}
    return {
        "points": [
            (tuple(point.coords), point.flags, point.mass)
            for point in lod.points
        ],
        "facenormals": [tuple(normal) for normal in lod.facenormals],
        "faces": [
            (
                tuple(
                    (vertex.point_index, vertex.normal_index, tuple(vertex.uv))
                    for vertex in face.vertices
                ),
                face.flags,
                face.texture,
                face.material,
            )
            for face in lod.faces
        ],
        "sharp_edges": list(lod.sharp_edges),
        "properties": list(lod.properties.items()),
        "selections": [
            (
                name,
                tuple(
                    sorted(
                        (point_index[id(point)], weight)
                        for point, weight in selection.points.items()
                    )
                ),
                tuple(
                    sorted(
                        (face_index[id(face)], weight)
                        for face, weight in selection.faces.items()
                    )
                ),
                selection.all_points is lod.points,
                selection.all_faces is lod.faces,
            )
            for name, selection in lod.selections.items()
        ],
    }


def _proxy_objects(lod, name):
    selection = lod.selections[name]
    face = next(iter(selection.faces))
    points = tuple(lod.points[vertex.point_index] for vertex in face.vertices)
    normal_index = face.vertices[0].normal_index
    return selection, face, points, normal_index


def _add_unrelated_triangle_after_proxy(fork, lod):
    base = len(lod.points)
    for coords in (
        (10.0, 0.0, 0.0),
        (10.0, 1.0, 0.0),
        (10.0, 0.0, 1.0),
    ):
        point = fork.Point()
        point.coords = coords
        lod.points.append(point)
    lod.facenormals.append((1.0, 0.0, 0.0))
    normal_index = len(lod.facenormals) - 1
    face = fork.Face(lod.points, lod.facenormals)
    for point_index in range(base, base + 3):
        vertex = fork.Vertex(lod.points, lod.facenormals)
        vertex.point_index = point_index
        vertex.normal_index = normal_index
        vertex.uv = (0.0, 0.0)
        face.vertices.append(vertex)
    lod.faces.append(face)
    selection = lod.new_selection("after_proxy")
    selection.points = {lod.points[index]: 1 for index in range(base, base + 3)}
    selection.faces = {face: 1}
    lod.sharp_edges.append((base, base + 2))
    return selection, face, tuple(lod.points[base:base + 3])


def test_proxy_engine_correction_squared_is_exact_identity(fork):
    """Exact comparison: P' contains only 0 and +/-1."""
    assert _matrix_multiply(
        fork.PROXY_ENGINE_CORRECTION,
        fork.PROXY_ENGINE_CORRECTION,
    ) == IDENTITY


def test_proxy_engine_correction_twice_restores_proxy_triangle(fork):
    """Exact comparison: P' only permutes and negates components."""
    triangle = (
        (1.0, 2.0, 3.0),
        (1.0, 2.01, 3.0),
        (1.02, 2.0, 3.0),
    )
    corrected = _transform_triangle(fork.PROXY_ENGINE_CORRECTION, triangle)
    restored = _transform_triangle(fork.PROXY_ENGINE_CORRECTION, corrected)

    assert restored == triangle


def test_proxy_frame_conversion_uses_involutive_dayz_correction(fork):
    """Breaks if the raw/engine conversion omits P' or applies it on the wrong
    side."""
    assert fork.PROXY_ENGINE_CORRECTION == ENGINE_CORRECTION
    _matrix_close(fork.proxy_frame_to_engine(IDENTITY), ENGINE_CORRECTION)
    _matrix_close(fork.proxy_frame_from_engine(IDENTITY), ENGINE_CORRECTION)
    _matrix_close(
        fork.proxy_frame_from_engine(fork.proxy_frame_to_engine(ROT_Y90)),
        ROT_Y90,
    )
    _matrix_close(
        fork.proxy_frame_to_engine(fork.proxy_frame_from_engine(ROT_Y90)),
        ROT_Y90,
    )


@pytest.mark.parametrize(
    "rotation",
    [
        ((1.0, 0.0), (0.0, 1.0)),
        ((2.0, 0.0, 0.0), (0.0, 2.0, 0.0), (0.0, 0.0, 2.0)),
        ((1.0, 0.25, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        ((-1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        ((math.nan, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        ((10 ** 1000, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
    ],
)
def test_canonical_proxy_triangle_rejects_invalid_rotation(fork, rotation):
    """Breaks if a non-rotation matrix can reach proxy geometry."""
    with pytest.raises(ValueError, match="rotation"):
        fork.canonical_proxy_triangle((0.0, 0.0, 0.0), rotation=rotation)


@pytest.mark.parametrize(
    "scale", [0.0, -0.001, math.nan, math.inf, 1e-50, 10 ** 1000]
)
def test_canonical_proxy_triangle_rejects_invalid_or_f32_degenerate_scale(
    fork, scale
):
    """Breaks if the scale produces a null triangle once serialised to float32."""
    with pytest.raises(ValueError, match="scale"):
        fork.canonical_proxy_triangle((0.0, 0.0, 0.0), scale=scale)


@pytest.mark.parametrize(
    ("path", "index", "error_type", "message"),
    [
        ("", 1, ValueError, "path"),
        ("\\lf\\bad\0path", 1, ValueError, "NUL"),
        ("\\lf\\proxy.p3d", 1, ValueError, "p3d"),
        ("\\lf\\PROXY.P3D", 1, ValueError, "p3d"),
        ("\\lf\\proxy", True, TypeError, "index"),
        ("\\lf\\proxy", 1.0, TypeError, "index"),
        ("\\lf\\proxy", 0, ValueError, "index"),
        ("\\lf\\proxy", -1, ValueError, "index"),
    ],
)
def test_add_proxy_rejects_bad_path_or_index_without_mutation(
    fork, path, index, error_type, message
):
    """Breaks if validation happens after the LOD's lists are touched."""
    lod = build_cube_p3d(fork).lods[0]
    before = _lod_snapshot(lod)
    with pytest.raises(error_type, match=message):
        lod.add_proxy(path, index=index)
    assert _lod_snapshot(lod) == before


@pytest.mark.parametrize(
    "control",
    ["\n", "\r", "\t", "\x1f", "\x7f", "\x85"],
)
def test_add_proxy_rejects_control_characters_without_mutation(fork, control):
    """Breaks if a proxy path can carry non-printable control characters."""
    lod = build_cube_p3d(fork).lods[0]
    before = _lod_snapshot(lod)

    with pytest.raises(ValueError, match="control"):
        lod.add_proxy(f"\\lf\\control{control}path")

    assert _lod_snapshot(lod) == before


def test_every_proxy_name_accepted_by_add_is_enumerated(fork):
    """Breaks if add accepts a name that get_proxies then omits."""
    alphabet = ("a", "Z", "0", "_", "-", ".", "\\", "/", " ", ":")
    candidates = [
        "".join(characters)
        for length in (1, 2)
        for characters in itertools.product(alphabet, repeat=length)
    ]
    candidates.extend(
        [
            "\\lf\\line\nbreak",
            "\\lf\\carriage\rreturn",
            "\\lf\\tab\tpath",
            "\\lf\\delete\x7fpath",
            "\\lf\\c1\x85path",
        ]
    )
    lod = build_cube_p3d(fork).lods[0]
    accepted_names = []
    for index, candidate in enumerate(candidates, start=1):
        try:
            accepted_names.append(lod.add_proxy(candidate, index=index))
        except ValueError:
            continue

    enumerated_names = {item["name"] for item in lod.get_proxies()}

    assert accepted_names
    assert enumerated_names == set(accepted_names)


@pytest.mark.parametrize(
    ("rotation", "scale"),
    [
        (((-1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)), 0.001),
        (IDENTITY, 0.0),
        (IDENTITY, math.nan),
    ],
)
def test_add_proxy_rejects_bad_transform_without_mutation(
    fork, rotation, scale
):
    """Breaks if an invalid transform leaves points, normals or faces partly
    written."""
    lod = build_cube_p3d(fork).lods[0]
    before = _lod_snapshot(lod)
    with pytest.raises(ValueError):
        lod.add_proxy(
            "\\lf\\proxy",
            index=1,
            rotation=rotation,
            scale=scale,
        )
    assert _lod_snapshot(lod) == before


def test_raw_default_keeps_legacy_triangle_and_frame_descriptor(fork):
    """Breaks if a later version changes what the positional raw argument
    meant."""
    triangle = fork.canonical_proxy_triangle(
        (1.0, 2.0, 3.0),
        ROT_Y90,
        0.01,
    )
    assert triangle == [
        [1.0, 2.0, 3.0],
        [1.0, 2.01, 3.0],
        [1.02, 2.0, 3.0],
    ]
    lod = build_cube_p3d(fork).lods[0]
    lod.add_proxy(
        "\\lf\\raw",
        3,
        (1.0, 2.0, 3.0),
        ROT_Y90,
        0.01,
    )
    descriptor = lod.get_proxies()[0]
    _matrix_close(descriptor["frame"], ROT_Y90, tolerance=1e-9)


def test_get_proxies_exposes_both_frames_and_scale(fork):
    """Breaks if the descriptor confuses raw with engine space, or loses the
    scale."""
    lod = build_cube_p3d(fork).lods[0]
    name = lod.add_proxy(
        "\\lf\\raw",
        index=4,
        origin=(0.25, -0.5, 0.75),
        rotation=ROT_Y90,
        scale=0.025,
    )
    descriptor = {item["name"]: item for item in lod.get_proxies()}[name]
    expected_engine = (
        (0.0, 0.0, 1.0),
        (1.0, 0.0, 0.0),
        (0.0, 1.0, 0.0),
    )
    _matrix_close(descriptor["frame"], ROT_Y90)
    _matrix_close(descriptor["raw_frame"], ROT_Y90)
    _matrix_close(descriptor["engine_frame"], expected_engine)
    assert descriptor["scale"] == pytest.approx(0.025, abs=1e-12)


def test_get_proxies_returns_independent_frame_and_raw_frame_values(fork):
    """Breaks if the two public keys share the same mutable list."""
    lod = build_cube_p3d(fork).lods[0]
    name = lod.add_proxy(
        "\\lf\\independent-frames",
        rotation=ROT_Y90,
        scale=0.025,
    )
    descriptor = {item["name"]: item for item in lod.get_proxies()}[name]
    _matrix_close(descriptor["frame"], ROT_Y90)
    _matrix_close(descriptor["raw_frame"], ROT_Y90)
    assert descriptor["frame"] == descriptor["raw_frame"]

    raw_before = [row[:] for row in descriptor["raw_frame"]]
    descriptor["frame"][0][0] = 123.0
    assert descriptor["raw_frame"] == raw_before

    frame_before = [row[:] for row in descriptor["frame"]]
    descriptor["raw_frame"][1][1] = 456.0
    assert descriptor["frame"] == frame_before
    assert descriptor["frame"] is not descriptor["raw_frame"]


def test_engine_space_identity_roundtrips_as_engine_identity(fork):
    """Breaks if add_proxy applies the DayZ correction zero times or twice."""
    lod = build_cube_p3d(fork).lods[0]
    name = lod.add_proxy(
        "\\lf\\engine",
        index=1,
        rotation=IDENTITY,
        scale=0.01,
        space="engine",
    )
    descriptor = {item["name"]: item for item in lod.get_proxies()}[name]
    _matrix_close(descriptor["raw_frame"], ENGINE_CORRECTION)
    _matrix_close(descriptor["engine_frame"], IDENTITY)


def test_proxy_descriptors_survive_save_reload(fork):
    """Breaks if the new fields depend on in-memory objects that are never
    serialised."""
    p3d = build_cube_p3d(fork)
    lod = p3d.lods[0]
    name = lod.add_proxy(
        "\\lf\\roundtrip",
        index=12,
        origin=(0.5, -0.25, 1.25),
        rotation=ROT_Y90,
        scale=0.02,
    )
    reread = read_p3d(fork, write_bytes(p3d))
    descriptor = {
        item["name"]: item for item in reread.lods[0].get_proxies(strict=True)
    }[name]
    assert descriptor["anchor"] == pytest.approx((0.5, -0.25, 1.25), abs=1e-6)
    _matrix_close(descriptor["raw_frame"], ROT_Y90, tolerance=1e-3)
    assert descriptor["scale"] == pytest.approx(0.02, abs=1e-6)


@pytest.mark.parametrize(
    "mutation",
    [
        "four_points",
        "no_face",
        "wrong_face_points",
        "fractional_weight",
        "invalid_point_index",
        "nonfinite_coords",
        "nonfinite_normal",
        "normal_mismatch",
        "degenerate",
    ],
)
def test_strict_enumeration_rejects_each_malformed_proxy(fork, mutation):
    """Breaks if strict=True lets bad anatomy through, as the legacy mode did."""
    lod = build_cube_p3d(fork).lods[0]
    name = lod.add_proxy("\\lf\\strict", index=1)
    selection = lod.selections[name]
    if mutation == "four_points":
        selection.points[lod.points[0]] = 1
        assert lod.get_proxies() == []
    elif mutation == "no_face":
        selection.faces = {}
        assert len(lod.get_proxies()) == 1
    elif mutation == "wrong_face_points":
        proxy_point = next(iter(selection.points))
        del selection.points[proxy_point]
        selection.points[lod.points[0]] = 1
        assert len(lod.get_proxies()) == 1
    elif mutation == "fractional_weight":
        first = next(iter(selection.points))
        selection.points[first] = 0.5
        assert len(lod.get_proxies()) == 1
    elif mutation == "invalid_point_index":
        next(iter(selection.faces)).vertices[0].point_index = -1
    elif mutation == "nonfinite_coords":
        next(iter(selection.points)).coords = (math.nan, 0.0, 0.0)
    elif mutation == "nonfinite_normal":
        normal_index = next(iter(selection.faces)).vertices[0].normal_index
        lod.facenormals[normal_index] = (math.nan, 0.0, 0.0)
    elif mutation == "normal_mismatch":
        normal_index = next(iter(selection.faces)).vertices[0].normal_index
        lod.facenormals[normal_index] = (0.0, 1.0, 0.0)
    else:
        for index, point in enumerate(selection.points):
            point.coords = (float(index), 0.0, 0.0)
    with pytest.raises(ValueError, match=re.escape(repr(name))):
        lod.get_proxies(strict=True)


def test_align_proxy_mutates_only_exclusive_geometry_in_place(fork):
    """Breaks if align recreates objects or bindings, or touches unrelated
    anatomy."""
    lod = build_cube_p3d(fork).lods[0]
    lod.sharp_edges[:] = [(0, 1), (2, 3)]
    name = lod.add_proxy("\\lf\\aligned", index=7)
    selection, face, points, normal_index = _proxy_objects(lod, name)

    owning_lists = (
        id(lod.points),
        id(lod.facenormals),
        id(lod.faces),
        id(lod.selections),
    )
    counts = (
        len(lod.points),
        len(lod.facenormals),
        len(lod.faces),
        len(lod.selections),
    )
    unrelated = {
        "points": tuple(
            (id(point), tuple(point.coords), point.flags, point.mass)
            for point in lod.points[:-3]
        ),
        "normals": tuple(lod.facenormals[:normal_index]),
        "faces": tuple(id(item) for item in lod.faces if item is not face),
        "sharp_edges": tuple(lod.sharp_edges),
        "component_points": tuple(lod.selections["Component01"].points),
        "component_faces": tuple(lod.selections["Component01"].faces),
    }

    result = lod.align_proxy(
        name,
        origin=(0.25, -0.5, 0.75),
        rotation=IDENTITY,
        scale=0.02,
        space="engine",
    )

    assert result == name
    assert lod.selections[name] is selection
    assert next(iter(selection.faces)) is face
    assert tuple(lod.points[v.point_index] for v in face.vertices) == points
    assert face.vertices[0].normal_index == normal_index
    assert all(v.normal_index == normal_index for v in face.vertices)
    assert (
        id(lod.points),
        id(lod.facenormals),
        id(lod.faces),
        id(lod.selections),
    ) == owning_lists
    assert (
        len(lod.points),
        len(lod.facenormals),
        len(lod.faces),
        len(lod.selections),
    ) == counts
    assert tuple(
        (id(point), tuple(point.coords), point.flags, point.mass)
        for point in lod.points[:-3]
    ) == unrelated["points"]
    assert tuple(lod.facenormals[:normal_index]) == unrelated["normals"]
    assert tuple(id(item) for item in lod.faces if item is not face) == \
        unrelated["faces"]
    assert tuple(lod.sharp_edges) == unrelated["sharp_edges"]
    assert tuple(lod.selections["Component01"].points) == \
        unrelated["component_points"]
    assert tuple(lod.selections["Component01"].faces) == \
        unrelated["component_faces"]

    descriptor = {
        item["name"]: item for item in lod.get_proxies(strict=True)
    }[name]
    assert descriptor["anchor"] == pytest.approx((0.25, -0.5, 0.75))
    _matrix_close(descriptor["engine_frame"], IDENTITY)
    assert descriptor["scale"] == pytest.approx(0.02)


def test_aligned_proxy_descriptor_survives_save_reload(fork):
    """Breaks if align only updates state that MLOD does not serialise."""
    p3d = build_cube_p3d(fork)
    lod = p3d.lods[0]
    name = lod.add_proxy("\\lf\\persist-align", index=8)
    lod.align_proxy(
        name,
        origin=(-0.25, 0.75, 1.5),
        rotation=ROT_Y90,
        scale=0.015,
    )

    reread = read_p3d(fork, write_bytes(p3d))
    descriptor = {
        item["name"]: item
        for item in reread.lods[0].get_proxies(strict=True)
    }[name]
    assert descriptor["anchor"] == pytest.approx(
        (-0.25, 0.75, 1.5), abs=1e-6
    )
    _matrix_close(descriptor["raw_frame"], ROT_Y90, tolerance=1e-3)
    assert descriptor["scale"] == pytest.approx(0.015, abs=1e-6)


@pytest.mark.parametrize(
    "sharing",
    [
        "point_face",
        "point_selection",
        "face_selection",
        "normal_face",
        "sharp_edge",
    ],
)
def test_align_proxy_rejects_shared_anatomy_atomically(fork, sharing):
    """Breaks if align can modify data another object also owns."""
    lod = build_cube_p3d(fork).lods[0]
    name = lod.add_proxy("\\lf\\shared", index=1)
    selection, face, points, normal_index = _proxy_objects(lod, name)
    proxy_point_index = lod.points.index(points[0])

    if sharing == "point_face":
        lod.faces[0].vertices[0].point_index = proxy_point_index
    elif sharing == "point_selection":
        lod.selections["Component01"].points[points[0]] = 1
    elif sharing == "face_selection":
        lod.selections["Component01"].faces[face] = 1
    elif sharing == "normal_face":
        lod.faces[0].vertices[0].normal_index = normal_index
    else:
        lod.sharp_edges.append((0, proxy_point_index))

    before = _lod_snapshot(lod)
    with pytest.raises(ValueError, match="shared"):
        lod.align_proxy(
            name,
            origin=(1.0, 2.0, 3.0),
            rotation=ROT_Y90,
            scale=0.01,
        )
    assert _lod_snapshot(lod) == before


@pytest.mark.parametrize(
    ("name", "origin", "rotation", "scale", "space", "message"),
    [
        ("proxy:\\lf\\missing.001", (0.0, 0.0, 0.0), IDENTITY, 0.001,
         "raw", "does not exist"),
        ("not-a-proxy", (0.0, 0.0, 0.0), IDENTITY, 0.001,
         "raw", "name"),
        ("proxy:\\lf\\align.001", (math.nan, 0.0, 0.0), IDENTITY, 0.001,
         "raw", "anchor"),
        ("proxy:\\lf\\align.001", (10 ** 1000, 0.0, 0.0), IDENTITY, 0.001,
         "raw", "anchor"),
        ("proxy:\\lf\\align.001", (0.0, 0.0, 0.0), IDENTITY, 0.0,
         "raw", "scale"),
        ("proxy:\\lf\\align.001", (0.0, 0.0, 0.0), IDENTITY, 0.001,
         "world", "space"),
    ],
)
def test_align_proxy_rejects_invalid_input_without_mutation(
    fork, name, origin, rotation, scale, space, message
):
    """Breaks if align validates after its first write."""
    lod = build_cube_p3d(fork).lods[0]
    lod.add_proxy("\\lf\\align", index=1)
    before = _lod_snapshot(lod)
    with pytest.raises(ValueError, match=message):
        lod.align_proxy(
            name,
            origin=origin,
            rotation=rotation,
            scale=scale,
            space=space,
        )
    assert _lod_snapshot(lod) == before


def test_remove_proxy_deletes_exact_anatomy_and_remaps_survivors(fork):
    """Breaks if remove leaves dangling indices, or replaces lists or
    bindings."""
    lod = build_cube_p3d(fork).lods[0]
    name = lod.add_proxy("\\lf\\remove", index=9)
    proxy_selection, proxy_face, proxy_points, _normal_index = \
        _proxy_objects(lod, name)
    unrelated_selection, unrelated_face, unrelated_points = \
        _add_unrelated_triangle_after_proxy(fork, lod)

    owning_lists = (
        id(lod.points),
        id(lod.facenormals),
        id(lod.faces),
        id(lod.selections),
        id(lod.sharp_edges),
    )
    counts = (
        len(lod.points),
        len(lod.facenormals),
        len(lod.faces),
        len(lod.selections),
    )
    component = lod.selections["Component01"]
    component_points = tuple(component.points)
    component_faces = tuple(component.faces)
    normal_pool = tuple(lod.facenormals)

    result = lod.remove_proxy(name)

    assert result == name
    assert name not in lod.selections
    assert proxy_selection not in lod.selections.values()
    assert proxy_face not in lod.faces
    assert all(point not in lod.points for point in proxy_points)
    assert (
        id(lod.points),
        id(lod.facenormals),
        id(lod.faces),
        id(lod.selections),
        id(lod.sharp_edges),
    ) == owning_lists
    assert (
        len(lod.points),
        len(lod.facenormals),
        len(lod.faces),
        len(lod.selections),
    ) == (counts[0] - 3, counts[1], counts[2] - 1, counts[3] - 1)
    assert tuple(lod.facenormals) == normal_pool

    assert lod.selections["after_proxy"] is unrelated_selection
    assert next(iter(unrelated_selection.faces)) is unrelated_face
    assert tuple(unrelated_selection.points) == unrelated_points
    assert [vertex.point_index for vertex in unrelated_face.vertices] == \
        [8, 9, 10]
    assert tuple(lod.points[index] for index in (8, 9, 10)) == \
        unrelated_points
    assert lod.sharp_edges == [(8, 10)]
    assert lod.selections["Component01"] is component
    assert tuple(component.points) == component_points
    assert tuple(component.faces) == component_faces
    assert all(
        selection.all_points is lod.points and selection.all_faces is lod.faces
        for selection in lod.selections.values()
    )
    assert lod.get_proxies(strict=True) == []


def test_removed_proxy_stays_removed_after_save_reload(fork):
    """Breaks if remove only cleans up Python objects and not the persisted
    MLOD."""
    p3d = build_cube_p3d(fork)
    lod = p3d.lods[0]
    name = lod.add_proxy("\\lf\\persist-remove", index=2)
    _add_unrelated_triangle_after_proxy(fork, lod)
    lod.remove_proxy(name)

    reread = read_p3d(fork, write_bytes(p3d))
    assert reread.lods[0].get_proxies(strict=True) == []
    assert len(reread.lods[0].points) == 11
    assert len(reread.lods[0].faces) == 7
    assert reread.lods[0].sharp_edges == [(8, 10)]


def test_remove_proxy_remaps_a_surviving_proxy_for_later_strict_use(fork):
    """Breaks if the first remove invalidates the next proxy's indices."""
    lod = build_cube_p3d(fork).lods[0]
    first = lod.add_proxy("\\lf\\first", index=1)
    second = lod.add_proxy(
        "\\lf\\second",
        index=2,
        origin=(1.0, 2.0, 3.0),
        scale=0.01,
    )

    assert lod.remove_proxy(first) == first
    descriptors = {
        item["name"]: item for item in lod.get_proxies(strict=True)
    }
    assert set(descriptors) == {second}
    assert descriptors[second]["anchor"] == pytest.approx((1.0, 2.0, 3.0))
    assert lod.remove_proxy(second) == second
    assert lod.get_proxies(strict=True) == []


@pytest.mark.parametrize(
    "sharing",
    [
        "point_face",
        "point_selection",
        "face_selection",
        "normal_face",
        "sharp_edge",
    ],
)
def test_remove_proxy_rejects_shared_anatomy_atomically(fork, sharing):
    """Breaks if remove deletes anatomy that also belongs to another object."""
    lod = build_cube_p3d(fork).lods[0]
    name = lod.add_proxy("\\lf\\shared-remove", index=1)
    selection, face, points, normal_index = _proxy_objects(lod, name)
    proxy_point_index = lod.points.index(points[0])

    if sharing == "point_face":
        lod.faces[0].vertices[0].point_index = proxy_point_index
    elif sharing == "point_selection":
        lod.selections["Component01"].points[points[0]] = 1
    elif sharing == "face_selection":
        lod.selections["Component01"].faces[face] = 1
    elif sharing == "normal_face":
        lod.faces[0].vertices[0].normal_index = normal_index
    else:
        lod.sharp_edges.append((0, proxy_point_index))

    before = _lod_snapshot(lod)
    with pytest.raises(ValueError, match="shared"):
        lod.remove_proxy(name)
    assert _lod_snapshot(lod) == before


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("invalid_face_index", "invalid point index"),
        ("malformed_edge", "malformed sharp edge"),
        ("invalid_edge_index", "invalid point index"),
        ("selection_alias", "shared"),
        ("duplicate_point_slot", "exactly once"),
        ("duplicate_face_slot", "exactly once"),
    ],
)
def test_remove_proxy_validates_complete_remap_plan_before_mutation(
    fork, mutation, message
):
    """Breaks if an invalid remap target causes a partial deletion."""
    lod = build_cube_p3d(fork).lods[0]
    name = lod.add_proxy("\\lf\\atomic-remove", index=1)
    selection, face, points, _normal_index = _proxy_objects(lod, name)

    if mutation == "invalid_face_index":
        lod.faces[0].vertices[0].point_index = len(lod.points)
    elif mutation == "malformed_edge":
        lod.sharp_edges.append((0, 1, 2))
    elif mutation == "invalid_edge_index":
        lod.sharp_edges.append((0, len(lod.points)))
    elif mutation == "selection_alias":
        lod.selections["alias"] = selection
    elif mutation == "duplicate_point_slot":
        lod.points.append(points[0])
    else:
        lod.faces.append(face)

    before = _lod_snapshot(lod)
    with pytest.raises(ValueError, match=message):
        lod.remove_proxy(name)
    assert _lod_snapshot(lod) == before


@pytest.mark.parametrize(
    ("name", "message"),
    [
        ("not-a-proxy", "name"),
        ("proxy:\\lf\\missing.001", "does not exist"),
    ],
)
def test_remove_proxy_rejects_invalid_name_without_mutation(
    fork, name, message
):
    """Breaks if the name is validated after the LOD is touched."""
    lod = build_cube_p3d(fork).lods[0]
    lod.add_proxy("\\lf\\remove", index=1)
    before = _lod_snapshot(lod)
    with pytest.raises(ValueError, match=message):
        lod.remove_proxy(name)
    assert _lod_snapshot(lod) == before
