import json

import py3d


def contract_value():
    return {
        "schema_version": "dayz-model-preflight-v1",
        "scale": {
            "lod_index": 0,
            "expected_dimensions_m": [2.0, 4.0, 6.0],
            "tolerance_m": [0.01, 0.01, 0.01],
        },
        "bones": {
            "requirements": [
                {"lod_index": 0, "selections": ["Pelvis"]}
            ]
        },
        "winding": {
            "source_model": "source.p3d",
            "transform": [
                [1.0, 0.0, 0.0, 0.0],
                [0.0, 1.0, 0.0, 0.0],
                [0.0, 0.0, 1.0, 0.0],
                [0.0, 0.0, 0.0, 1.0],
            ],
            "position_tolerance_m": 1e-5,
            "faces": [
                {
                    "source": {"lod_index": 0, "face_index": 0},
                    "target": {"lod_index": 0, "face_index": 0},
                }
            ],
        },
    }


def write_contract(directory, value=None):
    if value is None:
        value = contract_value()
    path = directory / "contract.json"
    path.write_text(
        json.dumps(value, sort_keys=True), encoding="utf-8", newline=""
    )
    return path


def make_lod(
    points,
    faces=((0, 1, 2),),
    selections=None,
    resolution=0.0,
    masses=False,
):
    lod = py3d.LOD()
    lod.resolution = resolution
    for coords in points:
        point = py3d.Point()
        point.coords = tuple(coords)
        point.mass = 1.0 if masses else None
        lod.points.append(point)
    lod.facenormals.append((0.0, 0.0, 1.0))
    for indices in faces:
        face = py3d.Face(lod.points, lod.facenormals)
        for point_index in indices:
            vertex = py3d.Vertex(lod.points, lod.facenormals)
            vertex.point_index = point_index
            vertex.normal_index = 0
            face.vertices.append(vertex)
        lod.faces.append(face)
    for name, membership in (selections or {}).items():
        selection = lod.new_selection(name)
        selection.points = {
            lod.points[index]: 1 for index in membership.get("points", ())
        }
        selection.faces = {
            lod.faces[index]: 1 for index in membership.get("faces", ())
        }
    return lod


def save_model(path, lods):
    model = py3d.P3D()
    model.lods.extend(lods)
    model.save(path)
    return path


def box_points(dimensions=(2.0, 4.0, 6.0)):
    x, y, z = (component / 2.0 for component in dimensions)
    return [
        (-x, -y, -z),
        (x, -y, -z),
        (-x, y, -z),
        (x, y, -z),
        (-x, -y, z),
        (x, -y, z),
        (-x, y, z),
        (x, y, z),
    ]
