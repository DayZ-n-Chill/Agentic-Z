import pathlib, sys
p = pathlib.Path(r"H:\Projects\Agentic-Z\docs\.updates\guide-src\pdf_common.py")
s = p.read_text(encoding="utf-8")
pairs = [
 ("h2,h3,tr.grp,.legend,.status-key{break-after:avoid}",
  "h2,h3,tr.grp,.legend,.status-key{break-after:avoid}\n"
  "/* An intro line stays with the block it introduces */\n"
  "section>p:has(+:is(.tbl,.chart,pre,.specs,ul,ol)){break-after:avoid}\n"
  "/* Blocks taller than a page (marked by the script below) may split, between rows only */\n"
  ".pdf-tall,.pdf-tall table{break-inside:auto}\n"
  "/* Lay the screen pass out at the printed content width so the script measures real heights */\n"
  "@media screen{html{width:725px}}"),
 ("__EXTRA__\n</style>\"\"\"",
  "__EXTRA__\n</style><script>addEventListener('load',()=>{document.querySelectorAll('.tbl,.specs,.chart,pre,section>ul,section>ol')"
  ".forEach(e=>{if(e.getBoundingClientRect().height>900)e.classList.add('pdf-tall')})})</script>\"\"\""),
]
for o, n in pairs:
    if s.count(o) != 1: sys.exit("no match: " + o)
    s = s.replace(o, n)
p.write_text(s, encoding="utf-8"); print("ok")
