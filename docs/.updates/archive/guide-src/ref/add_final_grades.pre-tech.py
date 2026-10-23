"""Rebuild the 'Quality by version' and 'Why each item got its grade' sections
of agentic-z-team.html from final_grades.json and final_grades_shared.json."""
import html, json, pathlib, re

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
    elif g in ('n/a', 'not built'):
        c = 'todo'
    else:
        c = 'fix'
    return '<span class="pill %s">%s</span>' % (c, g)


# Old v1.6.0 and v1.7.0 grades, read from the current table.
s, e = section('h-grades')
old = {}
for m in re.finditer(r'<tr><th scope="row"><code>([^<]+)</code></th><td><span class="pill \w+">([^<]+)</span></td><td><span class="pill \w+">([^<]+)</span></td>', t[s:e]):
    old[m.group(1).lstrip('/')] = (m.group(2), m.group(3))
ALIAS = {
    'dayz-rag MCP server (server.py, voyage_common.py, README, tests)': 'dayz-rag search server',
    '.claude/skills/_shared/dayz-conventions.md (Tier 2 core)': 'DayZ rules file (Tier 2)',
    '_shared/skill_helpers.py + test_skill_helpers.py': 'Shared skill helpers',
    'mods/agentic-z-panel (plugin.json, hooks.json, register.tsx, register.test.tsx, types)': 'dayz-panel',
}

# One row per item; clean-repo was graded twice (both A+), keep the later review.
rows = {}
for g in grades:
    group = g['batch'].split('-')[0]
    rows[(group, g['item'])] = g


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
        return 'Grading method note (the "How the grading works" section of this document)'
    if name.startswith('Pack: '):
        return 'Knowledge pack <code>%s</code>' % html.escape(name[6:])
    return '<code>%s</code>' % html.escape(name)


groups = [('Agents', sorted(k[1] for k in rows if k[0] == 'agents')),
          ('Skills', sorted(k[1] for k in rows if k[0] == 'skills'))]
shared = [k[1] for k in rows if k[0] == 'shared']
for gname in SHARED_ORDER:
    groups.append((gname, [n for n in shared if shared_group(n) == gname]))


def key_of(gname, name):
    if gname == 'Agents':
        return ('agents', name)
    if gname == 'Skills':
        return ('skills', name)
    return ('shared', name)


total = len(rows)
aplus = sum(1 for g in rows.values() if g['grade'] == 'A+')
by = {}
for (grp, _), g in rows.items():
    a, n = by.get(grp, (0, 0))
    by[grp] = (a + (g['grade'] == 'A+'), n + 1)
summary = {k: '%d of %d' % v for k, v in by.items()}

# Section 1: quality by version.
vt = ''
for gname, names in groups:
    vt += '   <tr class="grp"><th colspan="4" scope="colgroup">%s</th></tr>\n' % gname
    for n in names:
        g = rows[key_of(gname, n)]
        o = old.get(ALIAS.get(n, n).lstrip('/'), ('not built', 'not built'))
        vt += '   <tr><th scope="row">%s</th><td>%s</td><td>%s</td><td>%s</td></tr>\n' % (label(n), pill(o[0]), pill(o[1]), pill(g['grade']))

grades_sec = '''<section aria-labelledby="h-grades">
 <h2 id="h-grades">Quality by version</h2>
 <p>Every agent and skill was graded at v1.6.0, again after the v1.7.0 grading rounds, and a final time for v2.0.0 by fresh, independent AI reviewers (see "How the grading works"). The v2.0.0 grades also cover the hooks, the search server, the panel, the scripts, the answer tests and every knowledge pack. Items that did not exist yet show "not built"; shared files that were not graded at a version show "n/a".</p>
 <div class="chart"><svg viewBox="0 0 1140 190" role="img" aria-label="Agentic-Z versions and grades">
<defs><marker id="ahv" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" style="fill:var(--line)"/></marker></defs>
<rect class="b-gate" x="10" y="20" width="250" height="120" rx="10"/>
<text class="t" x="135" y="50" font-size="16">v1.6.0</text><text class="s" x="135" y="70">Released. First graded.</text>
<text class="tw" x="135" y="96">Mostly B and C</text><text class="s" x="135" y="116">0 of 54 at A+, 84 tests</text>
<line class="ln" x1="260" y1="80" x2="296" y2="80" marker-end="url(#ahv)"/>
<rect class="b-lead" x="298" y="20" width="250" height="120" rx="10"/>
<text class="t" x="423" y="50" font-size="16">v1.7.0</text><text class="s" x="423" y="70">Agent team, 5 grading rounds</text>
<text class="tw" x="423" y="96">Mostly A and A+</text><text class="s" x="423" y="116">22 of 54 at A+, 1,064 tests</text>
<line class="ln" x1="548" y1="80" x2="584" y2="80" marker-end="url(#ahv)"/>
<rect class="b-orch2" x="586" y="20" width="250" height="120" rx="10"/>
<text class="t" x="711" y="50" font-size="16">v1.8.0</text><text class="s" x="711" y="70">Token savers, panel, wrappers</text>
<text class="tw" x="711" y="96">Built and tested</text><text class="s" x="711" y="116">1,332 tests</text>
<line class="ln" x1="836" y1="80" x2="872" y2="80" marker-end="url(#ahv)"/>
<rect class="b-play" x="874" y="20" width="256" height="120" rx="10"/>
<text class="t" x="1002" y="50" font-size="16">v2.0.0</text><text class="s" x="1002" y="70">30 agents, 44 skills, packs</text>
<text class="tw" x="1002" y="96">%d of %d at A+</text><text class="s" x="1002" y="116">2,845 tests plus 18 panel tests</text>
<text class="note" x="570" y="172" text-anchor="middle">Each version is graded by fresh reviewers. A grade only moves up when a new reviewer confirms it.</text>
</svg></div>
 <p class="example">At v2.0.0, %s agents, %s skills and %s shared items are at A+. Each remaining lower grade names the defect the latest grader found on <code>develop</code>, in "Why each item got its grade". Tests went from 84 at v1.6.0 to 2,845 at v2.0.0 (<code>py -m pytest -q .claude scripts/dev hooks</code> on <code>origin/develop</code>), plus 18 panel tests.</p>
 <div class="status-key"><span>All three columns are grades from independent reviewers. The v2.0.0 column is the final grade, not a goal.</span></div>
 <div class="tbl"><table>
  <thead><tr><th scope="col">Item</th><th scope="col">v1.6.0<br>released</th><th scope="col">v1.7.0<br>agent team</th><th scope="col">v2.0.0<br>final</th></tr></thead>
  <tbody>
%s  </tbody>
 </table></div>
</section>''' % (aplus, total, summary['agents'], summary['skills'], summary['shared'], vt)

dt = ''
for gname, names in groups:
    dt += '   <tr class="grp"><th colspan="3" scope="colgroup">%s</th></tr>\n' % gname
    for n in names:
        g = rows[key_of(gname, n)]
        reason = html.escape(g['reason'], quote=False)
        reason = re.sub(r'`([^`]+)`', lambda m: '<code>%s</code>' % m.group(1), reason)
        if n == 'Method note (read first)':
            reason += ' Since this grade, that section was rewritten in this document: real test counts, all six reviewers, the hooks and plugins references, a rubric for the items that are not agents or skills, the grading prompts, one row per grading round and the caveat about unchecked examples. It has not been regraded, so the grade stays B+.'
        dt += '   <tr><th scope="row">%s</th><td>%s</td><td>%s</td></tr>\n' % (label(n), pill(g['grade']), reason)

detail_sec = '''<section aria-labelledby="h-grade-detail">
 <h2 id="h-grade-detail">Why each item got its grade</h2>
 <p>The latest independent grader's reason for each grade, in the grader's words. An A+ means the grader found nothing concrete to fix. Each remaining lower grade names the defect the latest grader found on <code>develop</code>.</p>
 <div class="tbl"><table>
  <thead><tr><th scope="col">Item</th><th scope="col">v2.0.0</th><th scope="col">Why</th></tr></thead>
  <tbody>
%s  </tbody>
 </table></div>
</section>''' % dt

s, e = section('h-grades')
t = t[:s] + grades_sec + t[e:]
# The "Items below A+" row of "Open items and decisions".
t, n = re.subn(r'<tr><th scope="row">Items below A\+</th><td>.*?</td>',
               lambda m: '<tr><th scope="row">Items below A+</th><td>%d of %d graded items are below A+. The reason for each in "Why each item got its grade" names the defect the latest grader found on <code>develop</code>.</td>' % (total - aplus, total), t)
assert n == 1, n
s, e = section('h-grade-detail')
t = t[:s] + detail_sec + t[e:]
p.write_text(t, encoding='utf-8')
print('ok', aplus, total, summary)
