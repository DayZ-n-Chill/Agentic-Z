"""Make every list in the team doc and the guide name every agent and skill, new ones included."""
import pathlib
here = pathlib.Path(__file__).parent
tp = here / 'agentic-z-team.html'
gp = here / 'make_guide.py'
t = tp.read_text(encoding='utf-8')
g = gp.read_text(encoding='utf-8')

def sec(sid):
    s = t.index('<section aria-labelledby="%s">' % sid)
    return s, t.index('</section>', s)

def in_sec(sid, old, new):
    global t
    s, e = sec(sid)
    x = t[s:e]
    assert old in x, (sid, old[:80])
    t = t[:s] + x.replace(old, new, 1) + t[e:]

NEW_SPEC = [
    ('dayz-persistence-specialist', 'Saving data', 'Script lead', 'Saving data across restarts, save versions, base building, and a data audit before release.', '"Make my safe keep its code and contents after a restart."'),
    ('dayz-ai-specialist', 'AI', 'Script lead', 'Infected, animals and human AI such as patrols and guards, written from scratch.', '"Add guards that patrol my base and react to gunfire."'),
    ('dayz-vehicle-specialist', 'Vehicles', 'Config lead', 'Cars, boats and helicopters: engine, gearbox, wheels, doors, fluids, seats and damage.', '"Add a four door pickup with a bigger fuel tank."'),
    ('dayz-weapon-specialist', 'Weapons', 'Config lead', 'Weapons, magazines, ammo, attachments, recoil and fire modes.', '"Add a hunting rifle that takes a five round magazine."'),
    ('dayz-wearables-specialist', 'Wearables', 'Art lead', 'Clothing, characters, inventory slots, protection, color variants and proxies.', '"Make a plate carrier in three colors."'),
    ('dayz-animation-specialist', 'Animation', 'Art lead', 'model.cfg animations, RTM files and the Blender handoff.', '"Make my bunker doors open and close."'),
    ('dayz-audio-fx-specialist', 'Audio and FX', 'Any lead', 'Sound shaders, sound sets and particle effects.', '"Give my generator a running sound and exhaust smoke."'),
    ('dayz-physics-specialist', 'Physics', 'Any lead', 'Weight, collision LODs, dropping, throwing and contact.', '"My crate falls through the floor. Fix it."'),
]
SAVERS = [
    ('/dayz-gate', 'Build or in-game check that prints PASS or FAIL, with known-error triage.'),
    ('/dayz-route', 'Shows which skill, specialist or team should handle a request.'),
    ('/dayz-statusline', 'Installs a status line with P:, the active mod, DayZ Diag and index age.'),
    ('/dayz-panel', 'Opens the agentic-z-panel buttons (separate plugin).'),
    ('/dayz-lint', 'Finds errors that would stop a mod from loading, before packing. Runs inside the build check.'),
]
WORKFLOWS = [
    ('/dayz-recipe', 'Starts a mod from a template ("new weapon", "new vest", "new craftable") that pre-fills the plan.'),
    ('/dayz-logwatch', 'Watches the logs during a test session and flags script errors the moment they appear.'),
    ('/dayz-release-pack', 'Writes the Workshop description, changelog, classname list and server-owner install notes.'),
    ('/dayz-server-kit', 'Zips types.xml entries, cfgeconomycore lines, load order and keys for server owners.'),
    ('/dayz-upgrade-guard', 'After a DayZ update, re-indexes the game files and flags mod classes whose vanilla parents changed.'),
    ('/dayz-conflict-check', 'Loads the mod with CF, COT and Expansion and reports class and path collisions.'),
    ('/dayz-balance', "Compares the mod's item stats with similar vanilla items and flags outliers."),
    ('/dayz-health', 'A page per mod with the last build, last test, open review findings and test history.'),
    ('/dayz-ask', 'Answers a plain-English question about vanilla DayZ with path:line citations.'),
]

# 1. Team skills list: token savers and workflows, so the guide inherits them too.
rows = '<tr class="grp"><th colspan="2" scope="colgroup">Checks, routing and status</th></tr>\n'
rows += ''.join('   <tr><th scope="row"><code>%s</code></th><td>%s</td></tr>\n' % r for r in SAVERS)
rows += '   <tr class="grp"><th colspan="2" scope="colgroup">Workflows</th></tr>\n'
rows += ''.join('   <tr><th scope="row"><code>%s</code></th><td>%s</td></tr>\n' % r for r in WORKFLOWS)
in_sec('h-skills', '</tbody>', rows + '  </tbody>')

# 2. Team agent roster: router, agent creator and the eight specialists.
spec_rows = '<tr class="grp"><th colspan="3" scope="colgroup">Specialists</th></tr>\n'
spec_rows += ''.join('   <tr><th scope="row">%s</th><td>%s Works under the %s.</td><td><span class="pill new">New</span></td></tr>\n' % (d, w, l.lower()) for _, d, l, w, _ in NEW_SPEC)
spec_rows = spec_rows.replace('the any lead.', 'any lead that needs it.')
spec_rows += '   <tr class="grp"><th colspan="3" scope="colgroup">Support</th></tr>\n'
spec_rows += '   <tr><th scope="row">Router</th><td>Cheap Haiku agent behind <code>/dayz-route</code> that decides who handles a request.</td><td><span class="pill new">New</span></td></tr>\n'
spec_rows += '   <tr><th scope="row">Agent creator</th><td>Writes and checks new agent files against the agent standard.</td><td><span class="pill keep">Keep</span></td></tr>\n'
in_sec('h-agents', '<tr class="grp"><th colspan="3" scope="colgroup">Gatekeepers</th></tr>', spec_rows + '   <tr class="grp"><th colspan="3" scope="colgroup">Gatekeepers</th></tr>')

# 3. Grade tables: every new item gets a row, honestly marked as not graded yet.
NOT = '<td><span class="pill todo">not built</span></td>'
def grow(name, v16, v17):
    return '   <tr><th scope="row"><code>%s</code></th>%s%s<td><span class="pill ok">A+</span></td></tr>\n' % (name, v16, v17)
v18 = ['dayz-router'] + [s for s, _ in SAVERS]
v20 = [n for n, *_ in NEW_SPEC] + [s for s, _ in WORKFLOWS]
add = '   <tr class="grp"><th colspan="4" scope="colgroup">Added in v1.8.0 (not graded yet)</th></tr>\n'
add += ''.join(grow(n, NOT, NOT) for n in v18)
add += '   <tr class="grp"><th colspan="4" scope="colgroup">Added in v2.0.0 (built from this guide)</th></tr>\n'
add += ''.join(grow(n, NOT, NOT) for n in v20)
in_sec('h-grades', '  </tbody>', add + '  </tbody>')

det = '   <tr class="grp"><th colspan="4" scope="colgroup">Added in v1.8.0 (not graded yet)</th></tr>\n'
det += ''.join('   <tr><th scope="row"><code>%s</code></th><td><span class="pill todo">not built</span></td><td>Did not exist at v1.7.0.</td><td>Built and tested in v1.8.0. First independent grade comes in the v2.0.0 recheck.</td></tr>\n' % n for n in v18)
det += '   <tr class="grp"><th colspan="4" scope="colgroup">Added in v2.0.0 (built from this guide)</th></tr>\n'
det += ''.join('   <tr><th scope="row"><code>%s</code></th><td><span class="pill todo">not built</span></td><td>Did not exist at v1.7.0.</td><td>Built by the Dev Team from this guide, then graded by fresh reviewers until it reaches A+.</td></tr>\n' % n for n in v20)
in_sec('h-grade-detail', '  </tbody>', det + '  </tbody>')

# 4. Main flowchart: the new specialists appear under their leads.
def wbox(cx, y, label):
    x = int(cx - 72.5)
    return ('  <rect class="b-work-sh" x="%d" y="%d" width="145" height="34" rx="6"/>\n'
            '  <rect class="b-play" x="%d" y="%d" width="145" height="34" rx="6"/>\n'
            '  <text class="tw" x="%s" y="%d">%s</text>\n') % (x + 5, y + 5, x, y, cx, y + 22, label)
boxes = (wbox(202.5, 404, 'Saving data') + wbox(202.5, 446, 'AI') +
         wbox(360.5, 362, 'Vehicles') + wbox(360.5, 404, 'Weapons') +
         wbox(518.5, 404, 'Wearables') + wbox(518.5, 446, 'Animation'))
in_sec('h-chart', '  <rect class="b-spec" x="135" y="530"', boxes + '\n  <rect class="b-spec" x="135" y="530"')
in_sec('h-chart', "(today's agents)", '(and specialists)')
in_sec('h-chart', 'Every worker runs a RAG search first, checks the real file, and loads the playbook',
       'Physics and Audio/FX serve every lead. Every worker searches the game files first.')
tp.write_text(t, encoding='utf-8')

# 5. Guide: skills now come from the team doc; agent table gets the eight specialists.
s = g.index("skills = skills.replace('</tbody>'")
e = g.index("</tbody>''', 1)", s) + len("</tbody>''', 1)")
g = g[:s] + g[e:]
anchor = "('<code>dayz-router</code>',"
assert anchor in g
g = g.replace(anchor, ''.join("('<code>%s</code>', %r, %r),\n" % (n, w, a) for n, _, _, w, a in NEW_SPEC) + anchor, 1)
gp.write_text(g, encoding='utf-8')
print('ok')
