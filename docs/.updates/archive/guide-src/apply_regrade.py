"""Merge a regrade file into final_grades.json and final_grades_shared.json.

Usage: py apply_regrade.py [regrade.json]   (default: final_regrade_r4.json)

The regrade file is a list of {"item", "grade", "reason"}. Each entry replaces
the grade and reason of the matching item in the two grade files. Names match
after path prefixes such as ".claude/skills/" are removed, so "dayz-gate" and
".claude/skills/dayz-gate" are the same item, and "hooks/edit_check.py" matches
"hooks/edit_check.py (+ test_edit_check.py)". Both grade files are backed up to
<name>.bak-<regrade name>.json before the first write. Nothing is written if any
regrade item has no match.
"""
import json, pathlib, shutil, sys

here = pathlib.Path(__file__).parent
FILES = ['final_grades.json', 'final_grades_shared.json']
PREFIXES = ('.claude/skills/', '.claude/agents/', '.claude/', 'skills/', 'agents/')


def norm(name):
    n = name.strip().replace('\\', '/').lstrip('/').lower()
    for p in PREFIXES:
        if n.startswith(p):
            n = n[len(p):]
            break
    if n.endswith('/skill.md'):
        n = n[:-len('/skill.md')]
    return n


def matches(existing, wanted):
    e = norm(existing)
    if e == wanted or e == wanted + '.md' or e + '.md' == wanted:
        return True
    return e.startswith(wanted + ' ')


regrade_path = here / (sys.argv[1] if len(sys.argv) > 1 else 'final_regrade_r4.json')
regrade = json.loads(regrade_path.read_text(encoding='utf-8'))
data = {f: json.loads((here / f).read_text(encoding='utf-8')) for f in FILES}

unmatched, changed = [], 0
for r in regrade:
    wanted = norm(r['item'])
    hits = [g for f in FILES for g in data[f] if norm(g['item']) == wanted]
    if not hits:
        hits = [g for f in FILES for g in data[f] if matches(g['item'], wanted)]
    if not hits:
        unmatched.append(r['item'])
        continue
    for g in hits:
        if (g['grade'], g['reason']) != (r['grade'], r['reason']):
            print('%-45s %s -> %s' % (g['item'][:45], g['grade'], r['grade']))
            g['grade'], g['reason'] = r['grade'], r['reason']
            changed += 1

if unmatched:
    print('ERROR: no match for: ' + ', '.join(unmatched))
    sys.exit(1)

for f in FILES:
    src = here / f
    bak = here / ('%s.bak-%s.json' % (src.stem, regrade_path.stem))
    if not bak.exists():
        shutil.copy2(src, bak)
    src.write_text(json.dumps(data[f], indent=0, ensure_ascii=False), encoding='utf-8')

rows = {}
for f in FILES:
    for g in data[f]:
        rows[(g['batch'].split('-')[0], g['item'])] = g['grade']
total = len(rows)
aplus = sum(v == 'A+' for v in rows.values())
print('merged %d of %d regrade items, %d changed; %d of %d at A+' % (len(regrade), len(regrade), changed, aplus, total))
