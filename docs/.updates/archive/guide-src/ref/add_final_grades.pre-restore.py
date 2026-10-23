"""Rebuild the "Current grades" section of agentic-z-team.html from
final_grades.json and final_grades_shared.json: one row per graded item, one grade column."""
import html, json, pathlib

here = pathlib.Path(__file__).parent
p = here / 'agentic-z-team.html'
t = p.read_text(encoding='utf-8')
grades = json.loads((here / 'final_grades.json').read_text(encoding='utf-8'))
grades += json.loads((here / 'final_grades_shared.json').read_text(encoding='utf-8'))


def section(sid):
    s = t.index('<section aria-labelledby="%s">' % sid)
    return s, t.index('</section>', s) + len('</section>')


def pill(g):
    if g == 'A+':
        c = 'ok'
    elif g.startswith('A'):
        c = 'keep'
    elif g.startswith('B'):
        c = 'warn'
    else:
        c = 'fix'
    return '<span class="pill %s">%s</span>' % (c, g)


# One row per item; an item graded twice (clean-repo) keeps its later grade.
rows = {}
for g in grades:
    rows[(g['batch'].split('-')[0], g['item'])] = g


def shared_group(name):
    if name.startswith('hooks/'):
        return 'Hooks'
    if name.startswith(('dayz-rag', 'mods/')):
        return 'Search server and panel'
    if name.startswith(('evals/', 'scripts/dev/test_run_evals', 'scripts/dev/run_evals')):
        return 'Answer tests (evals)'
    if name.startswith('scripts/'):
        return 'Scripts and repo tests'
    if name.startswith('Pack:'):
        return 'Specialist knowledge packs'
    if name.startswith('enscript/'):
        return 'Enforce Script pack'
    return 'Rules and shared files'


SHARED_ORDER = ['Rules and shared files', 'Specialist knowledge packs', 'Enforce Script pack', 'Hooks',
                'Search server and panel', 'Answer tests (evals)', 'Scripts and repo tests']


def label(name):
    if name == 'Method note (read first)':
        return 'Grading method note (the "Grading method" section of this document)'
    if name.startswith('Pack: '):
        return 'Knowledge pack <code>%s</code>' % html.escape(name[6:])
    return '<code>%s</code>' % html.escape(name)


groups = [('Agents', 'agents', sorted(k[1] for k in rows if k[0] == 'agents')),
          ('Skills', 'skills', sorted(k[1] for k in rows if k[0] == 'skills'))]
shared = [k[1] for k in rows if k[0] == 'shared']
for gname in SHARED_ORDER:
    groups.append((gname, 'shared', [n for n in shared if shared_group(n) == gname]))

total = len(rows)
aplus = sum(1 for g in rows.values() if g['grade'] == 'A+')
by = {}
for (grp, _), g in rows.items():
    a, n = by.get(grp, (0, 0))
    by[grp] = (a + (g['grade'] == 'A+'), n + 1)
summary = {k: '%d of %d' % v for k, v in by.items()}

body = ''
for gname, grp, names in groups:
    body += '   <tr class="grp"><th colspan="2" scope="colgroup">%s</th></tr>\n' % gname
    for n in names:
        body += '   <tr><th scope="row">%s</th><td>%s</td></tr>\n' % (label(n), pill(rows[(grp, n)]['grade']))

grades_sec = '''<section aria-labelledby="h-grades">
 <h2 id="h-grades">Current grades</h2>
 <p>The current grade of every graded item on <code>origin/develop</code>, given by independent reviewers as described in "Grading method". %d of %d items are at A+: %s agents, %s skills and %s shared items. A+ means the reviewer found nothing concrete to fix.</p>
 <div class="tbl"><table>
  <thead><tr><th scope="col">Item</th><th scope="col">Grade</th></tr></thead>
  <tbody>
%s  </tbody>
 </table></div>
</section>''' % (aplus, total, summary['agents'], summary['skills'], summary['shared'], body)

s, e = section('h-grades')
t = t[:s] + grades_sec + t[e:]
# The per-item reasons are not part of the document.
if '<section aria-labelledby="h-grade-detail">' in t:
    s, e = section('h-grade-detail')
    while t[e:e + 1] == '\n':
        e += 1
    t = t[:s] + t[e:]
p.write_text(t, encoding='utf-8')
print('ok', aplus, total, summary)
