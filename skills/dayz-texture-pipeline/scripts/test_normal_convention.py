#!/usr/bin/env python3
"""Fixtures of known convention for normal_convention.py (next to this file).

Synthetic height fields encoded as DirectX (Y-) and as OpenGL (Y+) normal maps, with an albedo
built from the same heights. Generated in the test, so no third-party texture ships with the
repo. Needs numpy and Pillow; without them the module skips (the CI runner installs pytest only).

Run: python -m pytest skills/dayz-texture-pipeline/scripts -q
"""
import json
import math
import sys
from fractions import Fraction
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")
Image = pytest.importorskip("PIL.Image")

sys.path.insert(0, str(Path(__file__).resolve().parent))
import normal_convention as nc  # noqa: E402

SIZE = 96


def _height() -> "np.ndarray":
    """Deterministic pits: no random generator, so the fixture is the same on every numpy."""
    rows, cols = np.mgrid[0:SIZE, 0:SIZE].astype(np.float64)
    h = np.zeros((SIZE, SIZE))
    for i in range(36):
        cy = (i * 37 % 89) + 4.0
        cx = (i * 53 % 83) + 6.0
        sigma = 2.5 + (i % 4)
        h -= np.exp(-((rows - cy) ** 2 + (cols - cx) ** 2) / (2.0 * sigma ** 2))
    return h


def _encode(dh_dcol: "np.ndarray", dh_drow: "np.ndarray", convention: str, k: float = 4.0) -> "Image.Image":
    nx = -k * dh_dcol
    # DirectX: +Y points down the rows; OpenGL: +Y points up, so the row slope keeps its sign.
    ny = -k * dh_drow if convention == "DirectX" else k * dh_drow
    nz = np.ones_like(nx)
    length = np.sqrt(nx ** 2 + ny ** 2 + nz ** 2)
    rgb = np.stack([nx / length, ny / length, nz / length], axis=-1)
    return Image.fromarray(np.round((rgb + 1.0) * 0.5 * 255.0).astype(np.uint8), "RGB")


def _normal_map(h: "np.ndarray", convention: str) -> "Image.Image":
    return _encode(np.gradient(h, axis=1), np.gradient(h, axis=0), convention)


def _grey(g: "np.ndarray") -> "Image.Image":
    return Image.fromarray(np.round(np.stack([g * 0.9, g, g * 0.8], axis=-1) * 255.0).astype(np.uint8), "RGB")


def _albedo(h: "np.ndarray") -> "Image.Image":
    return _grey(0.25 + 0.6 * (h - h.min()) / (h.max() - h.min()))     # hollows darker


def _ribs(size: int = 128):
    """Ribs whose amplitude grows down the image: across a hollow the surface curves one way
    along x and the other way along y (the counter-example of R21 round 1, analytic slopes)."""
    rows, cols = np.mgrid[0:size, 0:size].astype(np.float64)
    omega = 2.0 * np.pi * 3 / size
    beta = 4.0 / (size - 1)
    amplitude = np.exp(4.0 * (rows / (size - 1) - 0.5))
    h = np.cos(omega * cols) * amplitude
    dh_dcol = -omega * np.sin(omega * cols) * amplitude
    dh_drow = beta * np.cos(omega * cols) * amplitude
    return h, dh_dcol, dh_drow


@pytest.fixture(scope="module")
def maps():
    h = _height()
    rows, cols = np.mgrid[0:SIZE, 0:SIZE].astype(np.float64)
    return {
        "DirectX": _normal_map(h, "DirectX"),
        "OpenGL": _normal_map(h, "OpenGL"),
        "albedo": _albedo(h),
        "flat_albedo": Image.new("RGB", (SIZE, SIZE), (140, 140, 140)),
        # a pattern with no relation to the heights: finite, weak correlations
        "weak_albedo": _grey(0.5 + 0.3 * np.sin(1.7 * cols + 2.3 * rows)),
    }


@pytest.mark.parametrize("convention", ["DirectX", "OpenGL"])
def test_known_convention_is_read_back(maps, convention):
    result = nc.detect(maps[convention], maps["albedo"])
    assert result["verdict"] == convention, result
    assert result["albedo_verdict"] == convention and result["curl_verdict"] == convention, result
    # the red channel calibrates: across a pit d(nx)/dx falls where the albedo is dark.
    # Both readings are strong on this fixture (about 0.75); a green derivative taken along the
    # wrong axis still keeps the sign here but drops to about 0.14, so the bound is 0.5.
    assert result["corr_red"] < -0.5, result
    assert abs(result["corr_green"]) > 0.5, result
    assert result["pixels_with_detail"] > SIZE * SIZE // 10


@pytest.mark.parametrize("convention", ["DirectX", "OpenGL"])
def test_dark_ridges_instead_of_dark_hollows_keep_the_verdict(maps, convention):
    # the red channel calibrates the sign: an albedo darker on the ridges flips both correlations
    inverted = Image.fromarray(255 - np.asarray(maps["albedo"]), "RGB")
    result = nc.detect(maps[convention], inverted)
    assert result["verdict"] == convention, result
    assert result["corr_red"] > 0.1, result


@pytest.mark.parametrize("convention", ["DirectX", "OpenGL"])
def test_opposite_curvatures_make_the_albedo_reading_lie_and_the_verdict_abstain(convention):
    h, dh_dcol, dh_drow = _ribs()
    result = nc.detect(_encode(dh_dcol, dh_drow, convention), _albedo(h))
    wrong = "OpenGL" if convention == "DirectX" else "DirectX"
    # the albedo reading alone is wrong here, with strong correlations ...
    assert result["albedo_verdict"] == wrong, result
    assert abs(result["corr_red"]) > 0.5 and abs(result["corr_green"]) > 0.3, result
    # ... the curl reading is right, and the two disagreeing is never a verdict
    assert result["curl_verdict"] == convention, result
    assert result["verdict"] == "INCONCLUSIVE", result


@pytest.mark.parametrize("convention", ["DirectX", "OpenGL"])
def test_a_sum_of_x_and_y_profiles_leaves_the_curl_reading_without_signal(convention):
    # h = f(col) + g(row) has no mixed derivative, so both curl residuals are equal noise
    rows, cols = np.mgrid[0:SIZE, 0:SIZE].astype(np.float64)
    omega = 2.0 * np.pi * 4 / SIZE
    h = np.cos(omega * cols) + np.cos(omega * rows)
    result = nc.detect(_normal_map(h, convention), _albedo(h))
    assert result["albedo_verdict"] == convention, result
    assert result["curl_verdict"] == "INCONCLUSIVE", result
    assert result["verdict"] == "INCONCLUSIVE", result


@pytest.mark.parametrize("convention", ["DirectX", "OpenGL"])
def test_one_weak_channel_is_enough_to_abstain(maps, convention):
    # red weak, green strong: on the pits |red| 0.745 < |green| 0.775
    result = nc.detect(maps[convention], maps["albedo"], min_corr=0.76)
    assert abs(result["corr_red"]) < 0.76 <= abs(result["corr_green"]), result
    assert result["albedo_verdict"] == "INCONCLUSIVE" and result["verdict"] == "INCONCLUSIVE", result
    # green weak, red strong: on the ribs |red| 0.807 > |green| 0.677
    h, dh_dcol, dh_drow = _ribs()
    result = nc.detect(_encode(dh_dcol, dh_drow, convention), _albedo(h), min_corr=0.74)
    assert abs(result["corr_green"]) < 0.74 <= abs(result["corr_red"]), result
    assert result["albedo_verdict"] == "INCONCLUSIVE", result


def test_weak_albedo_correlations_are_inconclusive(maps):
    result = nc.detect(maps["DirectX"], maps["weak_albedo"])
    assert math.isfinite(result["corr_red"]) and math.isfinite(result["corr_green"]), result
    assert max(abs(result["corr_red"]), abs(result["corr_green"])) < nc.MIN_CORR, result
    assert result["albedo_verdict"] == "INCONCLUSIVE", result
    assert result["verdict"] == "INCONCLUSIVE", result


def test_flat_albedo_is_inconclusive_not_directx(maps):
    # no hollow signal: both correlations are undefined. The contributed script read NaN as DirectX.
    result = nc.detect(maps["OpenGL"], maps["flat_albedo"])
    assert result["verdict"] == "INCONCLUSIVE", result
    assert not math.isfinite(result["corr_green"])
    assert result["curl_verdict"] == "OpenGL", result


def test_inverting_green_only_negates_the_green_correlation(maps):
    # why an inverted-green run is no control: it cannot disagree with the original reading
    arr = np.asarray(maps["DirectX"]).copy()
    arr[:, :, 1] = 255 - arr[:, :, 1]
    flipped = nc.detect(Image.fromarray(arr, "RGB"), maps["albedo"])
    original = nc.detect(maps["DirectX"], maps["albedo"])
    assert flipped["corr_green"] == pytest.approx(-original["corr_green"], abs=0.02)
    assert flipped["corr_red"] == pytest.approx(original["corr_red"], abs=1e-12)
    assert flipped["curl_residual_directx"] == pytest.approx(original["curl_residual_opengl"], rel=0.05)


def _strict_json(text):
    def refuse(token):
        raise ValueError("non-JSON number %s" % token)
    return json.loads(text, parse_constant=refuse)


def test_cli_exit_codes_and_json(maps, tmp_path, capsys):
    paths = {}
    for name in ("DirectX", "OpenGL", "albedo", "flat_albedo"):
        paths[name] = tmp_path / ("%s.png" % name)
        maps[name].save(paths[name])
    small = tmp_path / "small.png"
    maps["albedo"].resize((SIZE // 2, SIZE // 2)).save(small)

    for convention in ("DirectX", "OpenGL"):
        code = nc.main(["--normal", str(paths[convention]), "--albedo", str(paths["albedo"]), "--json"])
        out = _strict_json(capsys.readouterr().out)
        assert code == 0 and out["verdict"] == convention, out

    code = nc.main(["--normal", str(paths["DirectX"]), "--albedo", str(paths["flat_albedo"]), "--json"])
    out = _strict_json(capsys.readouterr().out)       # undefined numbers are null, never NaN
    assert code == 2 and out["verdict"] == "INCONCLUSIVE" and out["corr_red"] is None, out
    assert nc.main(["--normal", str(paths["DirectX"]), "--albedo", str(paths["flat_albedo"])]) == 2
    assert "INCONCLUSIVE" in capsys.readouterr().out
    # --min-corr reaches the albedo reading: one weak channel makes the CLI abstain
    assert nc.main(["--normal", str(paths["DirectX"]), "--albedo", str(paths["albedo"]), "--min-corr", "0.76"]) == 2
    assert "INCONCLUSIVE" in capsys.readouterr().out
    assert nc.main(["--normal", str(paths["DirectX"]), "--albedo", str(small)]) == 1
    assert "differ in size" in capsys.readouterr().err


@pytest.mark.parametrize("convention", ["DirectX", "OpenGL"])
def test_the_curl_floor_compares_the_residual_difference(maps, convention):
    r = nc.detect(maps[convention], maps["albedo"])
    assert r["curl_verdict"] == convention
    d = abs(r["curl_residual_directx"] - r["curl_residual_opengl"])
    raised = nc.detect(maps[convention], maps["albedo"], curl_floor=d + 1e-9)
    assert raised["curl_verdict"] == "INCONCLUSIVE", raised
    assert raised["verdict"] == "INCONCLUSIVE", raised
    lowered = nc.detect(maps[convention], maps["albedo"], curl_floor=d - 1e-9)
    assert lowered["curl_verdict"] == convention, lowered
    # a difference exactly equal to the floor is noise too (receptor addition: kills <= -> <)
    at = nc.detect(maps[convention], maps["albedo"], curl_floor=d)
    assert at["curl_verdict"] == "INCONCLUSIVE", at


def test_residuals_within_one_quantization_step_are_inconclusive():
    # smooth single-period field: the residuals sit half an 8-bit step apart (0 and 1/255),
    # under the floor (2/255), so the ratio test alone would name DirectX but the floor abstains
    rows, cols = np.mgrid[0:SIZE, 0:SIZE].astype(np.float64)
    omega = 2.0 * np.pi / SIZE
    h = 0.3 * np.cos(omega * cols) * np.cos(omega * rows)
    result = nc.detect(
        _encode(np.gradient(h, axis=1), np.gradient(h, axis=0), "DirectX"),
        _albedo(h),
    )
    rd = result["curl_residual_directx"]
    rg = result["curl_residual_opengl"]
    assert min(rd, rg) < nc.CURL_RATIO * max(rd, rg), result
    assert abs(rd - rg) <= nc.CURL_FLOOR, result
    assert result["curl_verdict"] == "INCONCLUSIVE", result


def test_json_reports_the_curl_floor(maps, tmp_path, capsys):
    normal_path = tmp_path / "normal.png"
    albedo_path = tmp_path / "albedo.png"
    maps["DirectX"].save(normal_path)
    maps["albedo"].save(albedo_path)
    nc.main(["--normal", str(normal_path), "--albedo", str(albedo_path), "--json"])
    out = _strict_json(capsys.readouterr().out)
    assert out["curl_floor"] == pytest.approx(2.0 / 255.0)


def test_a_difference_of_exactly_one_step_is_noise():
    # the residual medians of vanilla vineyardfence_wires_nohq (product test, 2026-10-04): 4/255 and
    # 2/255 as computed. Their difference is one step plus a few ulps, so a bare <= let it through.
    rd, rg = 0.015686274509803977, 0.007843137254901933
    assert abs(rd - rg) > nc.CURL_FLOOR
    assert nc._curl_verdict(rd, rg, nc.CURL_RATIO, nc.CURL_FLOOR) == "INCONCLUSIVE"
    # one and a half steps apart is signal
    assert nc._curl_verdict(rd + 1.0 / 255.0, rg, nc.CURL_RATIO, nc.CURL_FLOOR) == "OpenGL"
    assert nc._curl_verdict(rg, rd + 1.0 / 255.0, nc.CURL_RATIO, nc.CURL_FLOOR) == "DirectX"


def _split_curl(base, k=1):
    """Pits encoded in `base`; the last k block-columns (16 px each on the 6x6 grid of a 96-px map) in the
    other convention, with a flat albedo there: only the curl reading splits across the blocks."""
    other = "OpenGL" if base == "DirectX" else "DirectX"
    h = _height()
    n = np.asarray(_normal_map(h, base)).copy()
    n[:, SIZE - 16 * k:] = np.asarray(_normal_map(h, other))[:, SIZE - 16 * k:]
    a = np.asarray(_albedo(h)).copy()
    a[:, SIZE - 16 * k:] = 140
    return Image.fromarray(n, "RGB"), Image.fromarray(a, "RGB")


def _split_albedo(base, k):
    """Pits on the left, ribs on the last k block-columns, all encoded in `base`: the curl reading is right
    everywhere, the albedo reading is wrong on the ribs, so only the albedo reading splits."""
    h = _height()
    rh, rdx, rdy = _ribs(SIZE)
    dhc, dhr = np.gradient(h, axis=1), np.gradient(h, axis=0)
    w = 16 * k
    dhc[:, SIZE - w:] = rdx[:, SIZE - w:]
    dhr[:, SIZE - w:] = rdy[:, SIZE - w:]
    a = np.asarray(_albedo(h)).copy()
    a[:, SIZE - w:] = np.asarray(_albedo(rh))[:, SIZE - w:]
    return _encode(dhc, dhr, base), Image.fromarray(a, "RGB")


def test_block_edges_round_to_the_nearest_pixel():
    assert nc._block_edges(1024, 6) == [0, 171, 341, 512, 683, 853, 1024]
    assert nc._block_edges(96, 6) == [0, 16, 32, 48, 64, 80, 96]


def test_stable_needs_one_agreeing_block_and_bounds_the_opposed_share():
    F = Fraction
    # an exactly full third of opposed blocks still passes, one more is too much
    assert nc._stable(2, 1, F(1, 3)) is True
    assert nc._stable(1, 1, F(1, 3)) is False
    assert nc._stable(9, 1, F(1, 10)) is True
    assert nc._stable(8, 1, F(1, 10)) is False
    # no agreeing block, no stability, even with nothing opposed
    assert nc._stable(0, 0, F(1, 3)) is False
    assert nc._stable(1, 0, F(1, 10)) is True


def test_every_block_gets_the_thresholds_of_the_whole_map(maps):
    # receptor addition: min_corr, the curl ratio and the curl floor reach each block's reading.
    # A threshold no block can clear silences that reading in every block.
    nrm = np.asarray(maps["DirectX"]).astype(np.float64) / 255.0 * 2.0 - 1.0
    nx, ny, nz = nrm[:, :, 0], nrm[:, :, 1], nrm[:, :, 2]
    albedo = nc._albedo_fields(nx, ny, maps["albedo"], nc.BLUR_RADIUS, nc.DETAIL_MIN, nc.LUMA_MIN)
    curl = nc._curl_fields(nx, ny, nz, nc.DETAIL_MIN)

    def counts(min_corr=nc.MIN_CORR, ratio=nc.CURL_RATIO, floor=nc.CURL_FLOOR):
        return nc._block_counts(albedo, curl, nx.shape, "DirectX", 6, min_corr, ratio, floor)

    assert counts() == {"albedo": [36, 0], "curl": [36, 0]}
    assert counts(min_corr=2.0)["albedo"] == [0, 0]
    assert counts(floor=1.0)["curl"] == [0, 0]
    assert counts(ratio=0.0)["curl"] == [0, 0]


@pytest.mark.parametrize("convention", ["DirectX", "OpenGL"])
def test_known_convention_is_stable_across_the_blocks(maps, convention):
    r = nc.detect(maps[convention], maps["albedo"])
    assert r["verdict"] == convention
    assert r["block_grid"] == 6
    assert r["curl_blocks_agree"] == 36 and r["curl_blocks_opposed"] == 0, r
    assert r["albedo_blocks_agree"] == 36 and r["albedo_blocks_opposed"] == 0, r
    assert r["blocks_stable"] is True


@pytest.mark.parametrize("base", ["DirectX", "OpenGL"])
def test_one_block_column_in_the_other_convention_abstains(base):
    n, a = _split_curl(base)
    r = nc.detect(n, a)
    # the global readings still name the base convention ...
    assert r["albedo_verdict"] == base and r["curl_verdict"] == base, r
    # ... but one block-column of six in the other convention is 1/6, over the 1/10 curl bound
    assert r["curl_blocks_agree"] == 30 and r["curl_blocks_opposed"] == 6, r
    assert r["blocks_stable"] is False
    assert r["verdict"] == "INCONCLUSIVE"
    # with a single block there is nothing to compare against, so the check passes by default
    r1 = nc.detect(n, a, block_grid=1)
    assert r1["verdict"] == base
    assert (r1["curl_blocks_agree"], r1["curl_blocks_opposed"],
            r1["albedo_blocks_agree"], r1["albedo_blocks_opposed"]) == (1, 0, 1, 0), r1


@pytest.mark.parametrize("base", ["DirectX", "OpenGL"])
@pytest.mark.parametrize("k, expected, opposed", [(1, "candidate", 6), (2, "candidate", 12), (3, "INCONCLUSIVE", 18)])
def test_the_albedo_reading_tolerates_a_third_of_the_blocks(base, k, expected, opposed):
    n, a = _split_albedo(base, k)
    r = nc.detect(n, a)
    want = base if expected == "candidate" else "INCONCLUSIVE"
    assert r["verdict"] == want, r
    assert r["albedo_blocks_opposed"] == opposed, r
    assert r["albedo_blocks_agree"] == 36 - opposed, r
    # the curl reading is right everywhere on this fixture
    assert r["curl_blocks_opposed"] == 0, r


def test_inverting_green_mirrors_the_block_counts(maps):
    arr = np.asarray(maps["DirectX"]).copy()
    arr[:, :, 1] = 255 - arr[:, :, 1]
    flipped = nc.detect(Image.fromarray(arr, "RGB"), maps["albedo"])
    original = nc.detect(maps["DirectX"], maps["albedo"])
    assert flipped["verdict"] == "OpenGL"
    assert (flipped["curl_blocks_agree"], flipped["curl_blocks_opposed"]) == \
           (original["curl_blocks_agree"], original["curl_blocks_opposed"]), flipped
    assert (flipped["albedo_blocks_agree"], flipped["albedo_blocks_opposed"]) == \
           (original["albedo_blocks_agree"], original["albedo_blocks_opposed"]), flipped
    n, a = _split_curl("DirectX")
    arr = np.asarray(n).copy()
    arr[:, :, 1] = 255 - arr[:, :, 1]
    inverted = nc.detect(Image.fromarray(arr, "RGB"), a)
    assert inverted["verdict"] == "INCONCLUSIVE"
    assert inverted["curl_verdict"] == "OpenGL"
    assert inverted["curl_blocks_agree"] == 30 and inverted["curl_blocks_opposed"] == 6, inverted


def test_json_reports_the_block_counts(maps, tmp_path, capsys):
    n, a = _split_curl("DirectX")
    normal_path = tmp_path / "normal.png"
    albedo_path = tmp_path / "albedo.png"
    n.save(normal_path)
    a.save(albedo_path)
    code = nc.main(["--normal", str(normal_path), "--albedo", str(albedo_path), "--json"])
    out = _strict_json(capsys.readouterr().out)
    assert code == 2
    assert out["verdict"] == "INCONCLUSIVE"
    assert out["curl_blocks_opposed"] == 6
    assert out["blocks_stable"] is False
    assert out["block_grid"] == 6
    assert out["block_curl_max_opposed"] == pytest.approx(0.1)
    assert out["block_albedo_max_opposed"] == pytest.approx(1 / 3)
    # an undefined albedo reading reports no counts and no stability
    maps["OpenGL"].save(normal_path)
    maps["flat_albedo"].save(albedo_path)
    nc.main(["--normal", str(normal_path), "--albedo", str(albedo_path), "--json"])
    out = _strict_json(capsys.readouterr().out)
    assert out["verdict"] == "INCONCLUSIVE"
    assert out["blocks_stable"] is None
    for key in ("curl_blocks_agree", "curl_blocks_opposed", "albedo_blocks_agree", "albedo_blocks_opposed"):
        assert out[key] is None


def _invert_green(img):
    arr = np.asarray(img).copy()
    arr[:, :, 1] = 255 - arr[:, :, 1]
    return Image.fromarray(arr, "RGB")


@pytest.mark.parametrize("case", ["pits", "split_curl", "split_albedo"])
def test_inverting_green_is_exactly_antisymmetric(maps, case):
    # review v3 round 1: with a decoding that only negates up to a few ulps, a tie in the ratio test could
    # give a candidate in one copy only. (2c - 255) / 255 negates exactly, so every number flips exactly.
    if case == "pits":
        n, a = maps["DirectX"], maps["albedo"]
    elif case == "split_curl":
        n, a = _split_curl("DirectX")
    else:
        n, a = _split_albedo("DirectX", 3)
    original, flipped = nc.detect(n, a), nc.detect(_invert_green(n), a)
    assert flipped["corr_green"] == -original["corr_green"]
    assert flipped["corr_red"] == original["corr_red"]
    assert flipped["curl_residual_directx"] == original["curl_residual_opengl"]
    assert flipped["curl_residual_opengl"] == original["curl_residual_directx"]
    swap = {"DirectX": "OpenGL", "OpenGL": "DirectX", "INCONCLUSIVE": "INCONCLUSIVE"}
    assert flipped["verdict"] == swap[original["verdict"]], (original, flipped)
    for key in ("curl_blocks_agree", "curl_blocks_opposed", "albedo_blocks_agree", "albedo_blocks_opposed",
                "blocks_stable"):
        assert flipped[key] == original[key], key


def test_blocks_partition_the_map_and_reuse_the_whole_map_fields(maps, monkeypatch):
    # review v3 round 1: windows that drop a row or a column, or blocks read with other masks, passed the
    # count-based tests. Record every reading: the first is the whole map, then one per block.
    calls = {"albedo": [], "curl": []}
    real_albedo, real_curl = nc._albedo_reading, nc._curl_reading

    def spy_albedo(fields, window, min_corr):
        calls["albedo"].append((fields, window, (min_corr,)))
        return real_albedo(fields, window, min_corr)

    def spy_curl(fields, window, curl_ratio, curl_floor):
        calls["curl"].append((fields, window, (curl_ratio, curl_floor)))
        return real_curl(fields, window, curl_ratio, curl_floor)

    monkeypatch.setattr(nc, "_albedo_reading", spy_albedo)
    monkeypatch.setattr(nc, "_curl_reading", spy_curl)
    result = nc.detect(maps["DirectX"], maps["albedo"])
    assert result["verdict"] == "DirectX", result
    for name in ("albedo", "curl"):
        (fields, window, thresholds), blocks = calls[name][0], calls[name][1:]
        assert window == (slice(None), slice(None)), name
        assert len(blocks) == nc.BLOCK_GRID ** 2, name
        cover = np.zeros((SIZE, SIZE), dtype=int)
        for block_fields, block_window, block_thresholds in blocks:
            assert block_fields is fields, name            # the whole map's derivatives and masks, unchanged
            assert block_thresholds == thresholds, name
            cover[block_window] += 1
        assert (cover == 1).all(), name                    # every pixel in exactly one block


def _faint_half(base):
    """Pits encoded in `base` on the left half; on the right half (three block-columns) a faint relief in the
    other convention whose decoded |nx| + |ny| never exceeds 10/255, below DETAIL_MIN, so it lies outside both
    masks, with an albedo dark in its hollows: it would vote the other convention if a mask were ignored."""
    other = "OpenGL" if base == "DirectX" else "DirectX"
    h = _height()
    n = np.asarray(_normal_map(h, base)).copy()
    a = np.asarray(_albedo(h)).copy()
    rows, cols = np.mgrid[0:SIZE, 0:SIZE].astype(np.float64)
    omega = 2.0 * np.pi / 8
    faint = np.cos(omega * cols) * np.cos(omega * rows)
    half = SIZE // 2
    n[:, half:] = np.asarray(_encode(np.gradient(faint, axis=1), np.gradient(faint, axis=0), other, k=0.04))[:, half:]
    a[:, half:] = np.asarray(_albedo(faint))[:, half:]
    return Image.fromarray(n, "RGB"), Image.fromarray(a, "RGB")


@pytest.mark.parametrize("base", ["DirectX", "OpenGL"])
def test_relief_outside_the_masks_does_not_vote(base):
    # review v3 round 2 (R3, P3): a reader that ignores its mask, in the blocks or on the whole map, passed the
    # tests. Here the right half carries the other convention below DETAIL_MIN: only masked pixels may count.
    n, a = _faint_half(base)
    nrm = np.asarray(n).astype(np.int64)
    alb = np.asarray(a).astype(np.float64) / 255.0
    tilt = (np.abs(2 * nrm[:, :, 0] - 255) + np.abs(2 * nrm[:, :, 1] - 255)) / 255.0
    luma = 0.2126 * alb[:, :, 0] + 0.7152 * alb[:, :, 1] + 0.0722 * alb[:, :, 2]
    assert tilt[:, SIZE // 2:].max() <= nc.DETAIL_MIN            # the faint half is outside the detail mask
    result = nc.detect(n, a)
    assert result["pixels_with_detail"] == int(((tilt > nc.DETAIL_MIN) & (luma > nc.LUMA_MIN)).sum()), result
    assert result["verdict"] == base, result
    assert (result["curl_blocks_agree"], result["curl_blocks_opposed"]) == (18, 0), result
    assert (result["albedo_blocks_agree"], result["albedo_blocks_opposed"]) == (18, 0), result
    assert result["blocks_stable"] is True, result


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
