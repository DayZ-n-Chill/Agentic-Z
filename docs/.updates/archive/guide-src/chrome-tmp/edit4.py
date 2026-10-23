import pathlib, sys
p = pathlib.Path(r"H:\Projects\Agentic-Z\docs\.updates\guide-src\pdf_common.py")
s = p.read_text(encoding="utf-8")
o = "section>p:has(+:is(.tbl,.chart,pre,.specs,ul,ol)){break-after:avoid}"
n = (o + "\nsection>h2+p{break-after:avoid}\n"
     "/* Paragraphs stay whole, and a caption or follow-up line stays with the block above it */\n"
     "p{break-inside:avoid}\n"
     "section>:is(.chart,.tbl,pre,.specs,ul,ol)+p{break-before:avoid}")
if s.count(o) != 1: sys.exit("no match")
p.write_text(s.replace(o, n), encoding="utf-8"); print("ok")
