"""Capture a game window from outside the game with PrintWindow (Windows only).

Used by /dayz-gate visual and the dayz-testbridge MCP server. DayZ scripts
cannot save a usable screenshot (vanilla MakeScreenshot,
P:\\scripts\\1_core\\proto\\proto.c:142, writes no file on diag), so the
picture is taken from the rendered client window. PrintWindow with
PW_RENDERFULLCONTENT reads the window's own content even when it is behind
other windows, so a capture never moves the mouse or brings the window to the
front. Pitfalls: skills/dayz-launch-test/references/window-capture-pitfalls.md.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

PW_CLIENTONLY = 0x1
PW_RENDERFULLCONTENT = 0x2  # asks DWM for the window's own content, so DirectX windows behind others work


class CaptureError(ValueError):
    """No visible window, a minimized window, PrintWindow failed, or an all-black frame."""


def _pil():
    try:
        from PIL import Image
    except ImportError as e:
        raise CaptureError("Pillow is not installed. Install it: py -m pip install pillow") from e
    return Image


def capture_window(pid: int, out: Path, crop: Optional[tuple[int, int, int, int]] = None) -> tuple[int, int]:
    """Save the client area of the visible window of process `pid` as a PNG; returns (width, height) saved.

    `crop` is (x, y, width, height) in client-area pixels. Raises CaptureError
    when the process has no visible window, the window is minimized (a
    minimized window draws nothing), PrintWindow fails, or the picture is all black.
    """
    import ctypes
    from ctypes import wintypes

    user32, gdi32 = ctypes.windll.user32, ctypes.windll.gdi32
    try:  # physical pixels on a scaled display
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except OSError:
        user32.SetProcessDPIAware()

    found: list[tuple[int, int]] = []
    proc_pid = wintypes.DWORD()
    rect = wintypes.RECT()

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def each(hwnd, _):
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(proc_pid))
        if proc_pid.value == pid and user32.IsWindowVisible(hwnd) and user32.GetClientRect(hwnd, ctypes.byref(rect)):
            found.append((rect.right * rect.bottom, hwnd))
        return True

    user32.EnumWindows(each, 0)
    if not found:
        raise CaptureError(f"DayZ client PID {pid} has no visible window")
    hwnd = max(found)[1]
    if user32.IsIconic(hwnd):
        raise CaptureError(f"the DayZ client window (PID {pid}) is minimized; a minimized window draws nothing")
    user32.GetClientRect(hwnd, ctypes.byref(rect))
    width, height = rect.right, rect.bottom
    if width <= 0 or height <= 0:
        raise CaptureError(f"the DayZ client window (PID {pid}) has no client area")

    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG), ("biHeight", wintypes.LONG),
                    ("biPlanes", wintypes.WORD), ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                    ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
                    ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD), ("biClrImportant", wintypes.DWORD)]

    window_dc = user32.GetDC(hwnd)
    memory_dc = gdi32.CreateCompatibleDC(window_dc)
    bitmap = gdi32.CreateCompatibleBitmap(window_dc, width, height)
    try:
        gdi32.SelectObject(memory_dc, bitmap)
        if not user32.PrintWindow(hwnd, memory_dc, PW_CLIENTONLY | PW_RENDERFULLCONTENT):
            raise CaptureError(f"PrintWindow could not read the DayZ client window (PID {pid})")
        pixels = ctypes.create_string_buffer(width * height * 4)
        header = BITMAPINFOHEADER(ctypes.sizeof(BITMAPINFOHEADER), width, -height, 1, 32, 0, 0, 0, 0, 0, 0)
        gdi32.GetDIBits(memory_dc, bitmap, 0, height, pixels, ctypes.byref(header), 0)
    finally:
        gdi32.DeleteObject(bitmap)
        gdi32.DeleteDC(memory_dc)
        user32.ReleaseDC(hwnd, window_dc)
    return save_bgra(pixels.raw, width, height, out, crop)


def save_bgra(raw: bytes, width: int, height: int, out: Path,
              crop: Optional[tuple[int, int, int, int]] = None) -> tuple[int, int]:
    """Write 32-bit BGRA pixels as a PNG; an all-black picture is a failed capture, not a shot."""
    Image = _pil()
    image = Image.frombuffer("RGBA", (width, height), raw, "raw", "BGRA", 0, 1).convert("RGB")
    if crop is not None:
        x, y, w, h = crop
        image = image.crop((x, y, x + w, y + h))
    if image.getextrema() == ((0, 0), (0, 0), (0, 0)):
        raise CaptureError("the capture is all black: the client drew nothing (is it still loading or minimized?)")
    image.save(out)
    return image.size
