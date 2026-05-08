"""Zip wiki/build/ contents (not the folder itself) for manual upload."""
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
src = REPO / "wiki" / "build"
out = REPO / "wiki" / "wiki-build.zip"

if out.exists():
    out.unlink()

with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for f in src.rglob("*"):
        if f.is_file():
            z.write(f, f.relative_to(src))

print(f"wrote {out.relative_to(REPO)} ({out.stat().st_size / 1024 / 1024:.1f} MB)")
