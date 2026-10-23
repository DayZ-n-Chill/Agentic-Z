import pathlib, sys
p = pathlib.Path(r"H:\Projects\Agentic-Z\docs\.updates\guide-src\pdf_common.py")
s = p.read_text(encoding="utf-8")
pairs = [
 (".wrap>*+*{margin-top:26px}", ".wrap>*+*{margin-top:32px}"),
 ("section>*+*{margin-top:12px}",
  "section>*+*{margin-top:12px}\nsection>:is(.chart,.tbl,pre,.specs,ul,ol)+:not(.foot){margin-top:24px}\n"
  "section>h3:not(:first-child){margin-top:32px}\nsection>.chart+.foot{margin-top:8px}"),
 (".chart{border:1px solid var(--rule);padding:8px;background:var(--surface)}", ".chart{border:1px solid var(--rule);padding:12px;background:var(--surface)}"),
 (".wrap>header>*+*{margin-top:6px}", ".wrap>header>*+*{margin-top:8px}"),
 ("th,td{padding:6px 10px}", "th,td{padding:8px 12px}"),
 ("        y = r.height - 8 * 72 / 25.4\n", "        y = r.height - 9 * 72 / 25.4  # baseline centered in the 18 mm bottom margin\n"),
]
for o, n in pairs:
    if s.count(o) != 1: sys.exit("no match: " + o)
    s = s.replace(o, n)
p.write_text(s, encoding="utf-8"); print("ok")
