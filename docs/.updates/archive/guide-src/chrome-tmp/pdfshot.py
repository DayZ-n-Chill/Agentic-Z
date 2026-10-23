"""Temporary helper: render the PDF pages holding given texts into ref/check/spacing-<tag>-<n>.png.
Usage: py chrome-tmp/pdfshot.py <pdf> <tag> <text|#pageno> ..."""
import pathlib, sys
import pymupdf

here = pathlib.Path(__file__).resolve().parent.parent
doc = pymupdf.open(here / sys.argv[1])
tag = sys.argv[2]
print("pages", doc.page_count)
for q in sys.argv[3:]:
    if q.startswith("#"):
        n = int(q[1:])
    else:
        n = next(i for i, p in enumerate(doc) if i and q in p.get_text())
    out = here / "ref" / "check" / f"spacing-{tag}-p{n + 1}.png"
    doc[n].get_pixmap(dpi=70).save(out)
    print(q, "->", out.name)
