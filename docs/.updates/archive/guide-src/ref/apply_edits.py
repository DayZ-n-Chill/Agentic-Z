"""Targeted edits on the live file: re-read, replace each exact string once, write back at once.
Usage: py apply_edits.py <target> <edits.py>; edits.py defines EDITS = [(old, new), ...]
and optionally SECTIONS = {section_id: new_html or ''} and SUBS = [(section_id, regex, repl)]."""
import pathlib, re, sys, runpy

target = pathlib.Path(sys.argv[1])
spec = runpy.run_path(sys.argv[2])
t = target.read_text(encoding='utf-8')
for old, new in spec.get('EDITS', []):
    n = t.count(old)
    assert n == 1, (n, old[:120])
    t = t.replace(old, new)


def bounds(sid):
    s = t.index('<section aria-labelledby="%s">' % sid)
    return s, t.index('</section>', s) + len('</section>')


for sid, rx, repl in spec.get('SUBS', []):
    s, e = bounds(sid)
    body, n = re.subn(rx, repl, t[s:e])
    assert n, (sid, rx)
    t = t[:s] + body + t[e:]
for sid, new in spec.get('SECTIONS', {}).items():
    if '<section aria-labelledby="%s">' % sid not in t:
        continue
    s, e = bounds(sid)
    if not new:  # drop the section and the blank line after it
        while t[e:e + 1] == '\n':
            e += 1
    t = t[:s] + new + t[e:]
target.write_text(t, encoding='utf-8')
print('ok', target.name)
