import pathlib
p = pathlib.Path(__file__).parent / 'agentic-z-team.html'
t = p.read_text(encoding='utf-8')

DEFS = '<defs><marker id="ah2" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" style="fill:var(--line)"/></marker></defs>'

def box(x, y, w, h, cls, title, sub=''):
    s = '<rect class="%s" x="%d" y="%d" width="%d" height="%d" rx="8"/>' % (cls, x, y, w, h)
    if sub:
        s += '<text class="tw" x="%d" y="%d">%s</text><text class="s" x="%d" y="%d">%s</text>' % (x + w // 2, y + h // 2 - 3, title, x + w // 2, y + h // 2 + 13, sub)
    else:
        s += '<text class="tw" x="%d" y="%d">%s</text>' % (x + w // 2, y + h // 2 + 5, title)
    return s

def tag(x, y):
    return '<rect class="tag" x="%d" y="%d" width="40" height="16" rx="4"/><text class="tag-t" x="%d" y="%d">NEW</text>' % (x, y, x + 20, y + 12)

leads = [
 ('Script lead', ['Script engineer', 'Workbench plugins'], ['Saving data', 'AI']),
 ('Config lead', ['Config engineer'], ['Vehicles', 'Weapons']),
 ('Art lead', ['Object Builder', 'Textures'], ['Wearables', 'Animation']),
 ('UI lead', ['UI engineer', 'Figma cleaner', 'Figma to layout'], []),
 ('Server lead', ['Server admin', 'Map builder'], ['Data audit']),
 ('Release lead', ['Build engineer', 'Docs writer'], []),
]
g = DEFS
g += box(420, 10, 300, 50, 'b-orch', 'Mod orchestrator', 'unchanged')
g += '<line class="ln" x1="570" y1="60" x2="570" y2="80"/><line class="ln" x1="95" y1="80" x2="1045" y2="80"/>'
for i, (lead, old, new) in enumerate(leads):
    x = 20 + i * 185
    g += '<line class="ln" x1="%d" y1="80" x2="%d" y2="98" marker-end="url(#ah2)"/>' % (x + 75, x + 75)
    g += box(x, 100, 170, 46, 'b-lead', lead)
    y = 162
    for w in old:
        g += box(x, y, 170, 32, 'b-work', w); y += 40
    for w in new:
        g += box(x, y, 170, 32, 'b-play', w); g += tag(x + 128, y - 8); y += 40
g += '<rect class="b-spec" x="20" y="340" width="1100" height="40" rx="8"/><text class="tspec" x="570" y="365">Shared by all: Physics and Audio/FX specialists, called by any lead that needs them (NEW)</text>'
g += '<rect class="gwrap" x="20" y="396" width="1100" height="50" rx="10"/><text class="tspec" x="570" y="426">Same gates: /dayz-lint (NEW) runs inside /dayz-gate build, then the in-game test</text>'
grow_svg = '<div class="chart"><svg viewBox="0 0 1140 460" role="img" aria-label="Where the new specialists join the team">%s</svg></div>' % g

c = DEFS
steps = [('Research', 'topic list'), ('Write', 'our own reference'), ('Verify', 'separate agent vs P:'), ('Answer tests', 'evals'), ('Wire in', 'lead, router, reviewer'), ('Grade', 'fix to A+'), ('Ship', 'PR, guide, PDFs')]
for i, (a, b) in enumerate(steps):
    x = 10 + i * 162
    c += box(x, 20, 146, 60, 'b-lead' if i not in (2, 5) else 'b-gate', a, b)
    if i < len(steps) - 1:
        c += '<line class="ln" x1="%d" y1="50" x2="%d" y2="50" marker-end="url(#ah2)"/>' % (x + 146, x + 162)
cycle_svg = '<div class="chart"><svg viewBox="0 0 1140 100" role="img" aria-label="Cycle for every new specialist">%s</svg></div>' % c

section = '''<section aria-labelledby="h-growth">
 <h2 id="h-growth">Growing the team: new specialists (plan)</h2>
 <p>Agentic-Z stays the base. The loop does not change: plan, leads, workers, gates, ship. New material only adds workers, knowledge packs and one check inside the existing build gate. Every fact is verified against the vanilla files on P: and written fresh in our own words; nothing is copied from outside sources.</p>
 %s
 <h3>Build order</h3>
 <ol class="steps">
  <li><span><b>Research map.</b> Every topic from outside research and the knowledge pack, sorted into the subjects below. Private, not in the repo.</span></li>
  <li><span><b>Foundation.</b> Client and server ownership rules added to the DayZ rules, a <code>references/</code> folder layout for specialists, and an empty answer-tests (evals) folder.</span></li>
  <li><span><b><code>/dayz-lint</code>.</b> Our own checker for errors that would stop a mod from loading, run inside <code>/dayz-gate build</code> and <code>/dayz-build-pbo</code> before packing. Its findings feed the known-errors triage.</span></li>
  <li><span><b>Saving data specialist (persistence):</b> storage, save versions and migrations, base building, and a pre-release check that nothing gets lost.</span></li>
  <li><span><b>Vehicle specialist:</b> cars, boats, helicopters and flight.</span></li>
  <li><span><b>Weapon specialist:</b> CfgWeapons, attachments, magazines, selections.</span></li>
  <li><span><b>Wearables specialist:</b> clothing, characters, slots and proxy alignment.</span></li>
  <li><span><b>Animation specialist:</b> model.cfg animation sources, RTM, and the Blender handoff.</span></li>
  <li><span><b>Audio and FX specialist:</b> sound shaders and sound sets, with the existing particles skill.</span></li>
  <li><span><b>Physics specialist:</b> collision layers, contact and thrown objects.</span></li>
  <li><span><b>AI specialist:</b> how Expansion's AI behaves, learned by observation only, never copied.</span></li>
  <li><span><b>Upgrade what exists:</b> deeper script reference, UI (Dabs and widgets), texture and rvmat cookbook, model and LOD rules, animated doors in the object builder, a short spec step in <code>/dayz-init</code>, and a layout preview at several screen sizes.</span></li>
 </ol>
 <h3>The same cycle for every specialist</h3>
 %s
 <h3>New specialists</h3>
 <div class="tbl"><table>
  <thead><tr><th scope="col">Specialist</th><th scope="col">Covers</th><th scope="col">Joins</th></tr></thead>
  <tbody>
   <tr><th scope="row">dayz-persistence-specialist</th><td>Saving data, save versions, migrations, base building, pre-release data audit.</td><td>Script lead (audit: server lead)</td></tr>
   <tr><th scope="row">dayz-vehicle-specialist</th><td>Cars, boats, helicopters, get-in actions, flight.</td><td>Config lead</td></tr>
   <tr><th scope="row">dayz-weapon-specialist</th><td>Weapons, attachments, magazines, bones and selections.</td><td>Config lead</td></tr>
   <tr><th scope="row">dayz-wearables-specialist</th><td>Clothing, characters, slots, proxies.</td><td>Art lead</td></tr>
   <tr><th scope="row">dayz-animation-specialist</th><td>model.cfg animations, RTM, Blender handoff.</td><td>Art lead</td></tr>
   <tr><th scope="row">dayz-audio-fx-specialist</th><td>Sound shaders, sound sets, client-only audio, particles.</td><td>Any lead</td></tr>
   <tr><th scope="row">dayz-physics-specialist</th><td>Collision layers, contact, thrown objects.</td><td>Any lead</td></tr>
   <tr><th scope="row">dayz-ai-specialist</th><td>Expansion AI behavior patterns, written fresh.</td><td>Script lead</td></tr>
  </tbody>
 </table></div>
 <h3>What we take and what we leave</h3>
 <div class="tbl"><table>
  <thead><tr><th scope="col">Verdict</th><th scope="col">Items</th></tr></thead>
  <tbody>
   <tr><th scope="row"><span class="pill new">Build new</span></th><td>Persistence, base building, data audit, vehicles, aviation, weapons, clothing, characters, proxy alignment, doors, physics, sound, AI patterns, animation pipeline, <code>/dayz-lint</code>, layout preview, answer tests.</td></tr>
   <tr><th scope="row"><span class="pill keep">Keep ours</span></th><td>Preflight, p3d audit, particles, PBO build, in-game testing, mod workflow, the DayZ rules and script style (the pack copied these from Agentic-Z), the CLAUDE, AGENTS and GEMINI files.</td></tr>
   <tr><th scope="row"><span class="pill move">Expand ours</span></th><td>Script reference, UI development, texture pipeline, model pipeline, a spec step before building.</td></tr>
   <tr><th scope="row"><span class="pill todo">Later</span></th><td>Blender animation and assembly, UV atlas, 3D viewer, p3d inspector, model preflight, animation format checkers, vehicle proxy checks.</td></tr>
   <tr><th scope="row"><span class="pill fix">Don't take</span></th><td>Racing-game vehicle rips, PBO reverse engineering, scraped notes and Discord dumps, the pack's MIT label, copied Expansion or VPP code, AI 3D generators, the pack's bookkeeping system.</td></tr>
  </tbody>
 </table></div>
 <p class="example">In-game testing of each specialist needs DayZ launched on Brian's PC; it is asked for before it runs.</p>
</section>

''' % (grow_svg, cycle_svg)

anchor = '<section aria-labelledby="h-fix">'
assert t.count(anchor) == 1
t = t.replace(anchor, section + anchor)
p.write_text(t, encoding='utf-8')
print('ok')
