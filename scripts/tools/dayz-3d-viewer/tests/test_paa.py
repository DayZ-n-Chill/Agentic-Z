import pytest

from dayz_3d_viewer import PAAFile, convert_paa_to_png
from dayz_3d_viewer.paa_to_png import PAA_RGBA8888

from viewer_support import write_dxt1_paa, write_rgba8888_paa


def test_rgba8888_round_trip_pixels(tmp_path):
    pytest.importorskip("PIL", reason="Pillow is needed to decode PAA pixels")
    pixels = []
    for index in range(16):
        pixels.append((index * 16, 32, 64, 255))
    paa_path = write_rgba8888_paa(tmp_path / "flat.paa", pixels, 4, 4)
    paa = PAAFile(str(paa_path))
    assert paa.paa_type == PAA_RGBA8888
    image = paa.decode_mipmap(0)
    assert image.size == (4, 4)
    for index, expected in enumerate(pixels):
        x = index % 4
        y = index // 4
        assert image.getpixel((x, y)) == expected
    png = tmp_path / "flat.png"
    convert_paa_to_png(str(paa_path), str(png))
    assert png.is_file()
    assert png.stat().st_size > 0


def test_dxt1_synthetic_decodes_to_red_channel(tmp_path):
    pytest.importorskip("PIL", reason="Pillow is needed to decode PAA pixels")
    paa_path = write_dxt1_paa(tmp_path / "dxt.paa")
    image = PAAFile(str(paa_path)).decode_mipmap(0)
    assert image.size == (4, 4)
    red, green, blue, alpha = image.getpixel((0, 0))
    assert red > 200
    assert green < 40
    assert blue < 40
    assert alpha == 255


def test_swiz_tag_is_recorded_and_not_applied(tmp_path):
    """SWIZ is stored on the file object and never read by decode_mipmap."""
    import inspect

    from dayz_3d_viewer import paa_to_png

    source = inspect.getsource(paa_to_png.PAAFile.decode_mipmap)
    assert "SWIZ" not in source
    assert "tags" not in source


def test_empty_paa_raises_viewer_error_not_struct_error(tmp_path):
    from dayz_3d_viewer import ViewerError

    empty = tmp_path / "empty.paa"
    empty.write_bytes(b"")
    with pytest.raises(ViewerError, match="truncated header"):
        PAAFile(str(empty))


def test_paa_without_mipmaps_raises_viewer_error_on_decode(tmp_path):
    from dayz_3d_viewer import ViewerError

    header_only = tmp_path / "nomips.paa"
    header_only.write_bytes(PAA_RGBA8888.to_bytes(2, "little") + b"\x00\x00")
    paa = PAAFile(str(header_only))
    assert paa.mipmaps == []
    with pytest.raises(ViewerError, match="No mipmaps"):
        paa.decode_mipmap(0)
