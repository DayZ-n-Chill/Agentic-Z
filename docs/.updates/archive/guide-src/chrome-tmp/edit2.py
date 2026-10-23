import pathlib, sys
d = pathlib.Path(r"H:\Projects\Agentic-Z\docs\.updates\guide-src")
def sub(name, pairs):
    p = d / name; s = p.read_text(encoding="utf-8")
    for o, n in pairs:
        if s.count(o) != 1: sys.exit(f"{name} no match: {o}")
        s = s.replace(o, n)
    p.write_text(s, encoding="utf-8"); print(name, "ok")
sub("agentic-z-team.html", [
 ("tbody th{font-weight:600;white-space:normal;overflow-wrap:break-word}",
  "tbody th{font-weight:600;white-space:normal;overflow-wrap:break-word}\n/* The .tbl card draws the outer edge; the last row needs no rule of its own */\ntbody tr:last-child>*{border-bottom:0}"),
])
sub("pdf_common.py", [
 (".sg,ol.steps li,tr{break-inside:avoid}\nh2,h3,tr.grp{break-after:avoid}",
  "/* Keep every block whole; only a table taller than a page splits, between rows, with its header repeated */\n"
  ".tbl,table,tr,.chart,pre,.sg,.specs,ul,ol,ol.steps li,.legend,.status-key,figure{break-inside:avoid}\n"
  "thead{display:table-header-group}\n"
  "h2,h3,tr.grp,.legend,.status-key{break-after:avoid}"),
])
