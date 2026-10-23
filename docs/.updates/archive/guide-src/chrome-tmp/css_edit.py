"""Temporary: targeted find-and-replace of CSS rules in the current files (asserts each old rule occurs once)."""
import pathlib, sys
here = pathlib.Path(__file__).resolve().parent.parent

def sub(name, pairs):
    p = here / name
    s = p.read_text(encoding="utf-8")
    for old, new in pairs:
        n = s.count(old)
        if n != 1:
            sys.exit(f"{name}: expected 1 match, found {n}: {old[:70]}")
        s = s.replace(old, new)
    p.write_text(s, encoding="utf-8")
    print(name, len(pairs), "edits")

# Spacing scale used everywhere: 4, 8, 12, 16, 24, 32, 48 px
sub("agentic-z-team.html", [
    ("header{display:grid;gap:10px}", "header{display:grid;gap:12px}"),
    ("section{display:grid;gap:18px;min-width:0}",
     "section{display:grid;gap:16px;min-width:0}\n"
     "/* Vertical rhythm: 16px between items, 24px after a block (diagram, table, code, list, cards), 32px above a sub-heading */\n"
     "section>:is(.chart,.tbl,pre,.specs,ul,ol)+:not(.foot){margin-top:8px}\n"
     "section>h3:not(:first-child){margin-top:16px}\n"
     "section>.chart+.foot{margin-top:-4px}"),
    (".chart{overflow-x:auto;background:var(--surface);border:1px solid var(--rule);border-radius:14px;padding:12px}",
     ".chart{overflow-x:auto;background:var(--surface);border:1px solid var(--rule);border-radius:14px;padding:16px}"),
    (".legend{display:flex;flex-wrap:wrap;gap:8px 20px;", ".legend{display:flex;flex-wrap:wrap;gap:8px 24px;"),
    ("th,td{text-align:left;padding:10px 16px;border-bottom:1px solid var(--rule);vertical-align:top}",
     "th,td{text-align:left;padding:12px 16px;border-bottom:1px solid var(--rule);vertical-align:top}"),
    ("thead th{font-family:var(--mono);font-size:12px;", "thead th{vertical-align:bottom;font-family:var(--mono);font-size:12px;"),
    ("border-radius:999px;padding:1px 9px;border:1px solid;white-space:nowrap}",
     "border-radius:999px;padding:2px 8px;line-height:1.4;border:1px solid;white-space:nowrap}"),
    ("border-radius:12px;padding:16px 18px;display:grid;gap:10px;align-content:start}",
     "border-radius:12px;padding:16px;display:grid;gap:12px;align-content:start}"),
    (".wrap .sg ul{list-style:none;margin:0;padding:0;display:flex;flex-wrap:wrap;gap:6px}",
     ".wrap ul{margin:0;padding-left:24px;display:grid;gap:8px}\n.wrap td>ul{margin-top:8px}\n"
     "pre{background:var(--band);border:1px solid var(--rule);border-radius:10px;padding:16px;overflow-x:auto;font-family:var(--mono);font-size:13px;line-height:1.5;margin:0}\n"
     ".wrap .sg ul{list-style:none;margin:0;padding:0;display:flex;flex-wrap:wrap;gap:8px}"),
    ("ol.steps{margin:0;padding:0;list-style:none;counter-reset:s;display:grid;gap:10px}",
     "ol.steps{margin:0;padding:0;list-style:none;counter-reset:s;display:grid;gap:12px}"),
    # Circle and text share a baseline (the number sits on the first line), 12px gap, wrapped lines stay in the text column
    ("ol.steps li{counter-increment:s;display:grid;grid-template-columns:36px 1fr;gap:12px;align-items:start;max-width:75ch}",
     "ol.steps li{counter-increment:s;display:grid;grid-template-columns:26px minmax(0,1fr);column-gap:12px;align-items:baseline}"),
    ("ol.steps li::before{content:counter(s);font-family:var(--mono);font-size:13px;width:28px;height:28px;",
     "ol.steps li::before{content:counter(s);font-family:var(--mono);font-size:12px;line-height:1;width:26px;height:26px;box-sizing:border-box;"),
    ("ol.flow{margin:0;padding-left:1.2em}ol.flow li{margin:0 0 2px}", "ol.flow{margin:0;padding-left:24px}ol.flow li{margin:0 0 4px}ol.flow li:last-child{margin:0}"),
    (".cover{min-height:100vh;box-sizing:border-box;display:flex;flex-direction:column;padding:72px 0 28px}",
     ".cover{min-height:100vh;box-sizing:border-box;display:flex;flex-direction:column;padding:72px 0 32px}"),
    ("border-radius:1px;margin:40px 0 28px}", "border-radius:1px;margin:48px 0 24px}"),
    ("color:var(--accent);margin-top:14px}", "color:var(--accent);margin-top:16px}"),
    ("max-width:56ch;margin-top:26px}", "max-width:56ch;margin-top:24px}"),
])
