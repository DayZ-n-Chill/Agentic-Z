from dayz_3d_viewer import PAAFile, convert_paa_to_png
from dayz_3d_viewer.paa_to_png import PAA_RGBA8888

from _support import write_dxt1_paa, write_rgba8888_paa


def test_rgba8888_round_trip_pixels(tmp_path):
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
