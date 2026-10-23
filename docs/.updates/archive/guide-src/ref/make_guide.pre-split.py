import pathlib, re
here = pathlib.Path(__file__).parent
team = (here / 'agentic-z-team.html').read_text(encoding='utf-8')
style = team[team.index('<style>'):team.index('</style>') + len('</style>')]
fonts = team[team.index('<link rel="preconnect"'):team.index('<style>')]
chart = team[team.index('<section aria-labelledby="h-chart">'):]
chart = chart[:chart.index('</section>') + len('</section>')]
chart = chart.replace('id="h-chart">The flowchart', 'id="h-chart">The mod team')
skills = """<section aria-labelledby="h-skills">
 <h2 id="h-skills">Skill reference</h2>
 <p>44 skills (slash commands) that agents and users can run. 40 ship in the plugin; <code>/sync-skills</code>, <code>/agentic-z-update</code>, <code>/docs-sync</code> and <code>/clean-repo</code> are clone only.</p>
 <ul>
  <li><b>Environment check:</b> 18 of the 40 plugin DayZ skills run <code>/dayz-preflight</code> first (preflight itself is the check).</li>
  <li><b>Exceptions:</b> the Tier 2 rules file has 14 exception entries naming 21 skills, each with its reason. <code>/dayz-lint</code>, <code>/dayz-balance</code>, <code>/dayz-conflict-check</code>, <code>/dayz-recipe</code>, <code>/dayz-layout-preview</code> and <code>/dayz-upgrade-guard</code> still read P: but only read files and write a report; <code>/dayz-ask</code> only checks that P: is mounted; <code>/dayz-gate</code> gates through the scripts it calls; <code>/dayz-stop-test</code> skips the check.</li>
  <li><b>Reference only:</b> <code>/dayz-particles</code> has no script.</li>
 </ul>
 <div class="tbl"><table>
  <thead><tr><th scope="col">Skill</th><th scope="col">Function</th></tr></thead>
  <tbody>
   <tr class="grp"><th colspan="2" scope="colgroup">Setup</th></tr>
   <tr><th scope="row"><code>/dayz-init</code></th><td>Setup wizard on first run, with an optional spec step; a status hub for the active mod after that.</td></tr>
   <tr><th scope="row"><code>/dayz-preflight</code></th><td>Checks that P: is mounted, DayZ Tools is installed, vanilla data is extracted and the <code>P:\\Mods</code> Workshop link exists.</td></tr>
   <tr><th scope="row"><code>/dayz-workdrive</code></th><td>Mounts P: after a reboot without opening DayZ Tools.</td></tr>
   <tr><th scope="row"><code>/dayz-setup-objectbuilder</code></th><td>Configures Object Builder on a new machine.</td></tr>
   <tr class="grp"><th colspan="2" scope="colgroup">Mods</th></tr>
   <tr><th scope="row"><code>/dayz-new-mod</code></th><td>Creates a mod with the standard folders and files.</td></tr>
   <tr><th scope="row"><code>/dayz-import-mod</code></th><td>Imports an existing mod folder or a GitHub repo into <code>workspace\\</code>.</td></tr>
   <tr><th scope="row"><code>/dayz-add-scaffold</code></th><td>Adds missing standard pieces to an existing mod.</td></tr>
   <tr><th scope="row"><code>/dayz-recipe</code></th><td>Starts a plan from a template (new weapon, new vest, new craftable) for <code>dayz-mod-architect</code> to finish.</td></tr>
   <tr><th scope="row"><code>/dayz-scope-mod</code></th><td>Locks editing to one mod; <code>--clear</code> lifts it.</td></tr>
   <tr><th scope="row"><code>/dayz-clean-workspace</code></th><td>Removes mods it created, and their builds.</td></tr>
   <tr class="grp"><th colspan="2" scope="colgroup">Build</th></tr>
   <tr><th scope="row"><code>/dayz-lint</code></th><td>Finds errors that would stop a mod loading, before packing. Runs first inside <code>/dayz-gate build</code> and <code>/dayz-build-pbo</code>.</td></tr>
   <tr><th scope="row"><code>/dayz-build-pbo</code></th><td>Packs a mod into a PBO with AddonBuilder.</td></tr>
   <tr><th scope="row"><code>/dayz-deploy-pbo</code></th><td>Copies prebuilt PBOs and keys into place without AddonBuilder.</td></tr>
   <tr class="grp"><th colspan="2" scope="colgroup">Test</th></tr>
   <tr><th scope="row"><code>/dayz-add-server</code></th><td>Creates a local test server instance.</td></tr>
   <tr><th scope="row"><code>/dayz-launch-test</code></th><td>Starts a DayZ Diag server and client with the given mods.</td></tr>
   <tr><th scope="row"><code>/dayz-stop-test</code></th><td>Stops the test session. Skips the environment check so it works as an emergency stop.</td></tr>
   <tr><th scope="row"><code>/dayz-cot-bootstrap</code></th><td>Grants you admin in Community Online Tools on the test server.</td></tr>
   <tr><th scope="row"><code>/dayz-logwatch</code></th><td>Watches the logs during a test session and triages each new error as it appears.</td></tr>
   <tr class="grp"><th colspan="2" scope="colgroup">Gates and checks</th></tr>
   <tr><th scope="row"><code>/dayz-gate</code></th><td>Build, in-game, behavior and visual gates as scripts that print <code>PASS</code> or <code>FAIL</code>, with known-error triage. <code>behavior</code> runs a test mission that spawns and uses each new item and reports per feature; <code>visual</code> takes screenshots in game and compares them with stored baselines.</td></tr>
   <tr><th scope="row"><code>/dayz-conflict-check</code></th><td>Finds collisions with CF, COT and Expansion without extracting them. For packed mods (the usual Workshop install) it reads only the PBO headers, so it compares prefixes, paths and script file names; config and script classes are compared only for unpacked mods. <code>--ingame</code> loads them together in a test session, which is how class clashes with packed mods show up.</td></tr>
   <tr><th scope="row"><code>/dayz-upgrade-guard</code></th><td>Snapshots vanilla before a DayZ update, then lists mod classes whose vanilla parents changed; can rebuild the search index.</td></tr>
   <tr><th scope="row"><code>/dayz-balance</code></th><td>Compares item stats with similar vanilla items and flags outliers.</td></tr>
   <tr><th scope="row"><code>/dayz-health</code></th><td>A page per mod with the last build, last test, open findings and the history of every gate run.</td></tr>
   <tr class="grp"><th colspan="2" scope="colgroup">Routing and status</th></tr>
   <tr><th scope="row"><code>/dayz-route</code></th><td>Prints which skill, specialist or team should handle a request (see "Token savers").</td></tr>
   <tr><th scope="row"><code>/dayz-statusline</code></th><td>Installs a status line with P:, the active mod, DayZ Diag and index age.</td></tr>
   <tr class="grp"><th colspan="2" scope="colgroup">Art and UI</th></tr>
   <tr><th scope="row"><code>/dayz-pack-texture</code></th><td>Converts images to <code>.paa</code> and checks their suffixes.</td></tr>
   <tr><th scope="row"><code>/dayz-build-imageset</code></th><td>Packs UI sprites into an imageset.</td></tr>
   <tr><th scope="row"><code>/dayz-layout-preview</code></th><td>Renders a <code>.layout</code> to PNGs at several screen sizes and flags widgets off screen.</td></tr>
   <tr><th scope="row"><code>/dayz-p3d-audit</code></th><td>Finds collision, physics and structure problems in models.</td></tr>
   <tr><th scope="row"><code>/dayz-particles</code></th><td>Reference for making particle effects without Workbench; no script.</td></tr>
   <tr><th scope="row"><code>/dayz-launch-objectbuilder</code></th><td>Opens Object Builder on a model.</td></tr>
   <tr><th scope="row"><code>/dayz-launch-workbench</code></th><td>Opens Workbench on a mod's project.</td></tr>
   <tr class="grp"><th colspan="2" scope="colgroup">Server economy</th></tr>
   <tr><th scope="row"><code>/dayz-edit-types</code></th><td>Adds, changes, removes or merges <code>types.xml</code> entries.</td></tr>
   <tr><th scope="row"><code>/dayz-split-types</code></th><td>Splits one large <code>types.xml</code> into 19 category files.</td></tr>
   <tr class="grp"><th colspan="2" scope="colgroup">Release</th></tr>
   <tr><th scope="row"><code>/dayz-release-pack</code></th><td>Writes the Workshop description, a changelog entry, the classname list and server-owner install notes.</td></tr>
   <tr><th scope="row"><code>/dayz-server-kit</code></th><td>Zips <code>types.xml</code> entries, <code>cfgeconomycore</code> lines, the load order and the public <code>.bikey</code> for server owners. Never packs a <code>.biprivatekey</code>.</td></tr>
   <tr class="grp"><th colspan="2" scope="colgroup">RAG search</th></tr>
   <tr><th scope="row"><code>/dayz-search-index</code></th><td>Builds the game-files index.</td></tr>
   <tr><th scope="row"><code>/dayz-search-download</code></th><td>Installs a prebuilt index instead.</td></tr>
   <tr><th scope="row"><code>/dayz-ask</code></th><td>Answers a plain-English question about vanilla DayZ with checked <code>path:line</code> citations.</td></tr>
   <tr class="grp"><th colspan="2" scope="colgroup">Team and repo</th></tr>
   <tr><th scope="row"><code>/dayz-record-correction</code></th><td>Writes your correction into the right rule tier after your approval.</td></tr>
   <tr><th scope="row"><code>/sync-skills</code></th><td>Links the skills into Claude Code, Codex CLI and Gemini CLI (clone only).</td></tr>
   <tr><th scope="row"><code>/agentic-z-update</code></th><td>Pulls template updates into a clone (clone only).</td></tr>
   <tr><th scope="row"><code>/docs-sync</code></th><td>Keeps the docs wiki in line with the source files (clone only).</td></tr>
   <tr><th scope="row"><code>/clean-repo</code></th><td>Repo-wide cleanup across every domain (clone only).</td></tr>
  </tbody>
 </table></div>
 <p class="example">The side panel is a separate plugin, not a skill: <code>/plugin install agentic-z-panel@dayz-n-chill</code>, then <code>/dayz-panel</code>.</p>
</section>"""

packs = team[team.index('<section aria-labelledby="h-specs">'):]
packs = packs[:packs.index('</section>') + len('</section>')]

def box(x, y, w, h, cls, title, sub=''):
    s = '<rect class="%s" x="%d" y="%d" width="%d" height="%d" rx="8"/>' % (cls, x, y, w, h)
    if sub:
        s += '<text class="t" x="%d" y="%d" font-size="14">%s</text><text class="s" x="%d" y="%d">%s</text>' % (x + w // 2, y + h // 2 - 3, title, x + w // 2, y + h // 2 + 14, sub)
    else:
        s += '<text class="t" x="%d" y="%d" font-size="14">%s</text>' % (x + w // 2, y + h // 2 + 5, title)
    return s

def arrow(x1, y1, x2, y2):
    return '<line class="ln" x1="%d" y1="%d" x2="%d" y2="%d" marker-end="url(#ah)"/>' % (x1, y1, x2, y2)

DEFS = '<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z"/></marker></defs>'

def svg(w, h, title, body):
    return '<div class="chart"><svg viewBox="0 0 %d %d" role="img" aria-label="%s">%s%s</svg></div>' % (w, h, title, DEFS, body)

# 1 architecture
a = ''
a += box(440, 10, 260, 56, 'b-you', 'User', 'plain-English request')
a += arrow(570, 66, 570, 96)
a += box(400, 98, 340, 56, 'b-orch', 'Claude Code', 'Codex and Gemini CLI get skills and rules')
a += arrow(570, 154, 570, 184)
a += '<rect class="band" x="40" y="186" width="1060" height="150" rx="12"/><text class="lay" x="140" y="210" style="text-anchor:start">AGENTIC-Z</text>'
a += box(60, 224, 230, 96, 'b-play', 'Rules', 'Tier 1 and Tier 2')
a += box(310, 224, 230, 96, 'b-lead', 'Agents', 'DayZ specialists')
a += box(560, 224, 230, 96, 'b-lead', 'Skills', 'slash commands')
a += box(810, 224, 270, 96, 'b-orch2', 'dayz-rag', 'MCP server')
for x in (175, 425, 675):
    a += arrow(x, 336, x, 380)
a += arrow(945, 336, 945, 380)
a += box(60, 382, 230, 60, 'b-work', 'Your mod', 'workspace\\&lt;ModName&gt;')
a += box(310, 382, 230, 60, 'b-work', 'P: drive', 'vanilla data, junctions')
a += box(560, 382, 230, 60, 'b-work', 'DayZ Tools + game', 'AddonBuilder, Diag')
a += box(810, 382, 270, 60, 'b-work', 'Search index on disk', 'LanceDB + Voyage AI')
arch = svg(1140, 460, 'Architecture', a)

# 2 setup flow
steps = [('Install', 'plugin or clone'), ('/dayz-init', 'setup wizard'), ('Environment check', 'the wizard checks P:, Tools, data'), ('Your mod', 'the wizard: new mod or import'), ('Test server', 'the wizard: /dayz-add-server'), ('Search index', 'optional: /dayz-search-download')]
s = ''
for i, (t, sub) in enumerate(steps):
    row, col = divmod(i, 3)
    x = 40 + col * 370; y = 40 + row * 150
    s += box(x, y, 320, 90, 'b-lead' if i else 'b-you', t, sub)
    s += '<text class="chip" x="%d" y="%d">STEP %d</text>' % (x + 160, y - 10, i + 1)
    if col < 2:
        s += arrow(x + 320, y + 45, x + 370, y + 45)
s += '<polyline class="ln" points="1050,130 1050,152 80,152 80,188" fill="none" marker-end="url(#ah)"/>'
setup = svg(1140, 290, 'Setup sequence', s)

# 3 daily loop
loop = [('Edit', 'with an agent'), ('/dayz-build-pbo', 'pack the PBO'), ('/dayz-launch-test', 'server + client'), ('Read logs', 'script.log, RPT'), ('/dayz-stop-test', 'close DayZ')]
d = ''
pos = [(40, 30), (430, 30), (820, 30), (820, 170), (430, 170)]
for i, (t, sub) in enumerate(loop):
    x, y = pos[i]
    d += box(x, y, 300, 90, 'b-lead', t, sub)
d += arrow(340, 75, 428, 75) + arrow(730, 75, 818, 75) + arrow(970, 120, 970, 168) + arrow(820, 215, 732, 215)
d += '<polyline class="ln learn" points="430,215 190,215 190,122" fill="none" marker-end="url(#ah)"/><text class="note learn-t" x="200" y="245">Fix, then rebuild</text>'
d += box(820, 310, 300, 70, 'b-you', 'Release', 'publish with DayZ Tools Publisher')
d += arrow(970, 260, 970, 308)
daily = svg(1140, 400, 'Build loop', d)

# 4 one wave
w = ''
w += box(20, 40, 150, 64, 'b-work', 'Workers', 'one task each')
w += arrow(170, 72, 196, 72)
w += box(198, 40, 170, 64, 'b-gate', 'Mod review', 'lead runs it')
w += arrow(368, 72, 394, 72)
w += box(396, 40, 170, 64, 'b-gate', 'Layout check', 'UI tasks only')
w += arrow(566, 72, 592, 72)
w += box(594, 40, 170, 64, 'b-gate', 'Build check', 'once per wave')
w += arrow(764, 72, 790, 72)
w += box(792, 40, 160, 64, 'b-gate', 'In-game test', 'logs must be clean')
w += arrow(952, 72, 978, 72)
w += box(980, 40, 150, 64, 'b-gate', 'Behavior test', 'if the plan has checks')
w += '<polyline class="ln fail" points="1055,104 1055,170 620,170" fill="none" marker-end="url(#ah)"/>'
w += '<polyline class="ln fail" points="872,104 872,170" fill="none"/>'
w += box(420, 140, 200, 60, 'b-orch2', 'Debugger', 'reads the logs')
w += '<polyline class="ln fail" points="420,170 110,170 110,106" fill="none" marker-end="url(#ah)"/>'
w += '<text class="note fail-t" x="690" y="190">New or unclear FAIL</text><text class="note fail-t" x="260" y="190">Back to the worker with the cause</text>'
w += '<text class="note" x="20" y="232">Review and layout failures go straight back to the worker. Known errors skip the debugger: triage sends the fix to the owning lead.</text>'
wave = svg(1140, 250, 'Gate sequence for one wave', w)

# 5 rag
r = ''
r += box(20, 74, 220, 64, 'b-work', 'Vanilla files on P:', 'scripts, configs, layouts')
r += arrow(240, 106, 286, 106)
r += box(288, 74, 200, 64, 'b-lead', 'Indexer', '/dayz-search-index')
r += arrow(488, 106, 524, 106)
r += box(526, 74, 190, 64, 'b-orch2', 'Voyage AI', 'voyage-code-3')
r += arrow(716, 106, 752, 106)
r += box(754, 74, 170, 64, 'b-play', 'LanceDB', 'on your disk')
r += arrow(924, 106, 960, 106)
r += box(962, 74, 160, 64, 'b-lead', 'dayz-rag', 'MCP server')
r += arrow(1042, 138, 1042, 190)
r += box(860, 192, 262, 60, 'b-you', 'Agent', 'semantic query')
r += arrow(860, 222, 700, 222)
r += box(440, 192, 258, 60, 'b-gate', 'Verify', 'open the cited file')
r += '<text class="note" x="20" y="232">Or skip building: /dayz-search-download installs a prebuilt index.</text>'
rag = svg(1140, 270, 'RAG search pipeline', r)

# 6 tiers
tt = ''
tt += box(170, 20, 800, 70, 'b-play', 'Tier 1: repo rules', 'CLAUDE.md, AGENTS.md, GEMINI.md, every agent, every task')
tt += box(220, 104, 700, 70, 'b-lead', 'Tier 2: DayZ rules', 'dayz-conventions.md plus conventions/*.md topic files, all DayZ work')
tt += box(270, 188, 600, 70, 'b-orch', 'Tier 3: agents, skills, knowledge packs', 'only what the task needs')
tt += '<text class="note" x="570" y="282" text-anchor="middle">The more specific tier wins. /dayz-record-correction turns your corrections into rules.</text>'
tiers = svg(1140, 300, 'Rule tiers', tt)


# 7 token savers
rr = ''
rr += box(20, 40, 200, 64, 'b-you', 'Your request', '')
rr += arrow(220, 72, 262, 72)
rr += box(264, 40, 220, 64, 'b-play', 'Keyword rules', 'local, no model call')
rr += arrow(484, 72, 526, 72)
rr += box(528, 40, 220, 64, 'b-orch2', 'Jev', 'if TYPESAFE_API_KEY set')
rr += arrow(748, 72, 790, 72)
rr += box(792, 40, 220, 64, 'b-orch2', 'dayz-router', 'Haiku agent')
rr += '<polyline class="ln" points="374,104 374,160 900,160" fill="none" marker-end="url(#ah)"/>'
rr += '<polyline class="ln" points="638,104 638,160" fill="none"/>'
rr += '<line class="ln" x1="902" y1="104" x2="902" y2="140" marker-end="url(#ah)"/>'
rr += box(800, 142, 320, 60, 'b-lead', 'Skill, specialist or team', '')
rr += '<text class="note" x="20" y="190">Each stage runs only when the previous stage is below its confidence threshold.</text>'
router = svg(1140, 215, 'Routing chain', rr)
savers = """<section aria-labelledby="g-savers">
 <h2 id="g-savers">Token savers</h2>
 <p>These features move mechanical work to scripts or smaller models. Model tokens go to planning, writing code and configs, review and diagnosis.</p>
 %s
 <div class="tbl"><table><thead><tr><th scope="col">Feature</th><th scope="col">Behavior</th><th scope="col">Usage</th></tr></thead><tbody>
  <tr><th scope="row">Script gates</th><td>Build the mod or load it in game and print <code>PASS</code> or <code>FAIL</code> with no model call. Exit codes are in "Gates".</td><td><code>/dayz-gate build &lt;ModName&gt;</code>, <code>/dayz-gate ingame &lt;ModName&gt;</code></td></tr>
  <tr><th scope="row">Log triage</th><td>Matches each failure against 52 known errors in <code>known-errors.json</code>, each with a fix and an owning agent. Only new errors go to <code>dayz-mod-debugger</code>.</td><td>Runs inside <code>/dayz-gate</code>. <code>triage.py --learn</code> adds entries.</td></tr>
  <tr><th scope="row">Router</th><td>Picks the handler in three stages: keyword rules in <code>rules.json</code>, then Jev (TypeSafe's routing model, only with <code>TYPESAFE_API_KEY</code> set), then the <code>dayz-router</code> agent on Haiku. A stage result is final at confidence 0.8 or more.</td><td><code>/dayz-route "&lt;request&gt;"</code>. The main session runs it first for a new DayZ request.</td></tr>
  <tr><th scope="row">Hooks</th><td>The PostToolUse hook <code>edit_check.py</code> checks <code>config.cpp</code> and <code>.layout</code> syntax after every <code>Edit</code>, <code>Write</code> or <code>MultiEdit</code> and returns the problems to Claude. The PreToolUse hook <code>scope_guard.py</code> denies edits to other mods while <code>/dayz-scope-mod</code> is active. The UserPromptSubmit hook <code>paste_router.py</code> is described in "Paste-in routing".</td><td>Registered by the plugin (<code>hooks/hooks.json</code>) and by a clone (<code>.claude/settings.json</code>).</td></tr>
  <tr><th scope="row">Status line</th><td>Shows whether P: is mounted, the active mod, whether DayZ Diag is running and the search index age.</td><td><code>/dayz-statusline</code>, once per project.</td></tr>
  <tr><th scope="row">Launcher panel</th><td>A panel beside the chat with buttons for mount P:, build, the build and in-game gates, deploy, launch, stop, Workbench, Object Builder, test logs, the health page and the release pack, plus a field that sends a question to <code>/dayz-ask</code>.</td><td><code>/plugin install agentic-z-panel@dayz-n-chill</code>, then <code>/dayz-panel</code>.</td></tr>
  <tr><th scope="row">Smaller models</th><td><code>dayz-build-engineer</code> and <code>dayz-router</code> run on Haiku, <code>dayz-docs-writer</code> on Sonnet.</td><td>Set in each agent's <code>model:</code> field.</td></tr>
  <tr><th scope="row">Split rules</th><td>The Tier 2 rules were one 239-line file. They are now a 143-line core plus five topic files of 24 to 56 lines (see "Rule tiers"). Most skills read only the core, 40%% less; <code>/dayz-deploy-pbo</code> and <code>/dayz-gate</code> also point to the bundle mods section of <code>conventions/config.md</code>. Agents read the core plus the topic files their job needs:<ul><li>One topic file: 17%% to 30%% less than before.</li><li>Two topic files: <code>dayz-mod-debugger</code> (226 lines) and <code>dayz-mod-architect</code> (231 lines) read slightly less; the vehicle, weapon and audio and FX specialists (251 lines) read more.</li><li>Three topic files: <code>dayz-mod-reviewer</code> (283 lines) reads more.</li></ul></td><td>Automatic.</td></tr>
  <tr><th scope="row">No-model wrappers</th><td>A <code>.bat</code> for every runnable skill, to run it without the AI.</td><td>Listed in <code>scripts\\README.md</code>.</td></tr>
  <tr><th scope="row">Shorter descriptions</th><td>Every skill and agent description loads into every session. They were cut by about 2,100 tokens in total.</td><td>Automatic.</td></tr>
 </tbody></table></div>
</section>
""" % router

team_html = (here / 'agentic-z-team.html').read_text(encoding='utf-8')
gsec = team_html[team_html.index('<section aria-labelledby="h-growth">'):]
grow_chart = gsec[gsec.index('<div class="chart">'):]
grow_chart = grow_chart[:grow_chart.index('</svg></div>') + len('</svg></div>')]
grow_chart = re.sub(r'<rect class="tag"[^>]*/><text class="tag-t"[^>]*>NEW</text>', '', grow_chart).replace(' (NEW)', '').replace('/dayz-lint (NEW)', '/dayz-lint')
cycle_start = gsec.index('<div class="chart">', gsec.index('<div class="chart">') + 1)  # second chart: the specialist build cycle
cycle_chart = gsec[cycle_start:gsec.index('</svg></div>', cycle_start) + len('</svg></div>')]
coming = """<section aria-labelledby="g-coming">
 <h2 id="g-coming">Domain specialists</h2>
 <p>Eight specialists cover saving data, vehicles, weapons, wearables, animation, audio and FX, physics and AI, alongside the script, config, art, UI, map and server workers. Each works under a team lead and has its own knowledge pack, checked against the vanilla game files and loaded only when a task needs it. The one-line index is in "Agents"; the tables below give each one's scope and output.</p>
 %s
 <h3 id="g-spec-detail">Specialist reference</h3>
 <div class="tbl spc"><table><thead><tr><th scope="col" colspan="2"><code>dayz-persistence-specialist</code></th></tr></thead><tbody>
  <tr><th scope="row">Scope</th><td>Keeps modded items and systems' data across server restarts. Writes the save and load code (<code>OnStoreSave</code> and <code>OnStoreLoad</code>), stamps every save with a version number, and writes the upgrade path so old saves still load after the mod changes. Covers base building parts that must survive restarts. Before release it runs a data audit that checks every saved field is written and read back in the same order.</td></tr>
  <tr><th scope="row">Example request</th><td>"Make my safe keep its code and contents after a restart, and do not break saves from the last version."</td></tr>
  <tr><th scope="row">Lead</th><td>Script lead (the release audit goes to the server lead)</td></tr>
  <tr><th scope="row">Returns</th><td>Save and load code with a version number, a migration note for old saves, and an audit report for the server lead.</td></tr>
 </tbody></table></div>
 <div class="tbl spc"><table><thead><tr><th scope="col" colspan="2"><code>dayz-vehicle-specialist</code></th></tr></thead><tbody>
  <tr><th scope="row">Scope</th><td>Cars, boats and helicopters: the vehicle class and its simulation (engine, gearbox, axles, wheels), attached parts (doors, hood, trunk, wheels, battery, spark plug), fluids (fuel, oil, coolant, brake fluid), seats and crew positions, and damage. Vanilla DayZ ships native helicopter base classes (<code>Helicopter</code>, <code>HelicopterAuto</code> and <code>HelicopterScript</code>) but no flyable helicopter, so flyable ones are built on those classes with the user's own code, never copied from another mod.</td></tr>
  <tr><th scope="row">Example request</th><td>"Add a four door pickup with its own doors and a bigger fuel tank."</td></tr>
  <tr><th scope="row">Lead</th><td>Config lead</td></tr>
  <tr><th scope="row">Returns</th><td>CfgVehicles entries, the <code>CarScript</code>, <code>BoatScript</code> or <code>HelicopterScript</code> class, attachment slots, and a <code>types.xml</code> entry for the server lead.</td></tr>
 </tbody></table></div>
 <div class="tbl spc"><table><thead><tr><th scope="col" colspan="2"><code>dayz-weapon-specialist</code></th></tr></thead><tbody>
  <tr><th scope="row">Scope</th><td>Firearms: the weapon class, magazines, ammunition, attachment slots (optics, suppressors, stocks, handguards), recoil, fire modes and muzzle effects. Inherits from the closest vanilla weapon so reloading, jamming and damage behave like the base game.</td></tr>
  <tr><th scope="row">Example request</th><td>"Add a scoped hunting rifle that takes a five round magazine and the vanilla long range optics."</td></tr>
  <tr><th scope="row">Lead</th><td>Config lead</td></tr>
  <tr><th scope="row">Returns</th><td>CfgWeapons, CfgMagazines and CfgAmmo entries, a recoil class, and the model selections the art lead must provide.</td></tr>
 </tbody></table></div>
 <div class="tbl spc"><table><thead><tr><th scope="col" colspan="2"><code>dayz-wearables-specialist</code></th></tr></thead><tbody>
  <tr><th scope="row">Scope</th><td>Clothing, gear and characters: inventory slot, slots held, protection and insulation, hidden selections that let one model carry several textures, and display on the character through proxies. Covers new survivor characters.</td></tr>
  <tr><th scope="row">Example request</th><td>"Make a plate carrier with three colors that fits the vest slot and holds six items."</td></tr>
  <tr><th scope="row">Lead</th><td>Art lead</td></tr>
  <tr><th scope="row">Returns</th><td>Config entries, hidden selection names, texture slots for each color, and proxy notes for <code>dayz-object-builder</code>.</td></tr>
 </tbody></table></div>
 <div class="tbl spc"><table><thead><tr><th scope="col" colspan="2"><code>dayz-animation-specialist</code></th></tr></thead><tbody>
  <tr><th scope="row">Scope</th><td>Moving parts such as doors, lids, hatches and triggers. Writes the <code>skeletonBones</code> for the moving parts and the <code>class Animations</code> block in <code>model.cfg</code> (rotations, movements, hiding parts); <code>dayz-object-builder</code> keeps the rest of <code>model.cfg</code>. Handles <code>.rtm</code> animation files and writes the Blender handoff so bones and selections line up in Object Builder.</td></tr>
  <tr><th scope="row">Example request</th><td>"Make the doors on my bunker open and close when a player uses them."</td></tr>
  <tr><th scope="row">Lead</th><td>Art lead</td></tr>
  <tr><th scope="row">Returns</th><td>The <code>skeletonBones</code> and <code>class Animations</code> entries, the selection and bone names the model needs, and the script hook that plays the animation, for <code>dayz-script-specialist</code> to write.</td></tr>
 </tbody></table></div>
 <div class="tbl spc"><table><thead><tr><th scope="col" colspan="2"><code>dayz-audio-fx-specialist</code></th></tr></thead><tbody>
  <tr><th scope="row">Scope</th><td>Sound shaders and sound sets, sound range and volume, and particle effects such as smoke, sparks and muzzle flashes. Uses the <code>/dayz-particles</code> skill for particle files.</td></tr>
  <tr><th scope="row">Example request</th><td>"Give my generator a running sound that fades with distance and a puff of exhaust smoke."</td></tr>
  <tr><th scope="row">Lead</th><td>Any lead</td></tr>
  <tr><th scope="row">Returns</th><td>CfgSoundShaders and CfgSoundSets entries, particle files, and the script lines that play them.</td></tr>
 </tbody></table></div>
 <div class="tbl spc"><table><thead><tr><th scope="col" colspan="2"><code>dayz-physics-specialist</code></th></tr></thead><tbody>
  <tr><th scope="row">Scope</th><td>Weight, collision shapes in the Geometry and Fire Geometry LODs, how objects land when dropped or thrown, and contact with players and vehicles. Diagnoses common faults such as items falling through floors or bullets passing through walls.</td></tr>
  <tr><th scope="row">Example request</th><td>"My crate falls through the floor when I drop it. Fix it."</td></tr>
  <tr><th scope="row">Lead</th><td>Any lead</td></tr>
  <tr><th scope="row">Returns</th><td>Geometry and mass fixes for <code>dayz-object-builder</code> and config changes for the config lead.</td></tr>
 </tbody></table></div>
 <div class="tbl spc"><table><thead><tr><th scope="col" colspan="2"><code>dayz-ai-specialist</code></th></tr></thead><tbody>
  <tr><th scope="row">Scope</th><td>Behavior for computer controlled characters: infected, animals and human AI such as patrols and guards. Studies the patterns other modders use, then writes the user's own version; nothing is copied from another mod.</td></tr>
  <tr><th scope="row">Example request</th><td>"Add a patrol of guards that walk a route around my military base and react to gunfire."</td></tr>
  <tr><th scope="row">Lead</th><td>Script lead</td></tr>
  <tr><th scope="row">Returns</th><td>Script classes for the behavior, the config the server lead needs to spawn them, and server performance notes.</td></tr>
 </tbody></table></div>
 <h3>Knowledge verification cycle</h3>
 %s
 <p class="example">The existing specialists were extended too: a full Enforce Script reference, Dabs and widget UI coverage, a texture and material cookbook, model and LOD rules, animated doors, a spec step in <code>/dayz-init</code> before building, and <code>/dayz-layout-preview</code> for several screen sizes.</p>
</section>
""" % (grow_chart, cycle_chart)

spec_flows = """<section aria-labelledby="g-spec-flows">
 <h2 id="g-spec-flows">Specialist procedures</h2>
 <p>Each specialist's steps inside the team loop described in "Gates". Specialists that write DayZ content look up vanilla first, as described in "RAG search". <code>dayz-build-engineer</code>, <code>dayz-docs-writer</code>, <code>dayz-build-checker</code>, <code>dayz-ingame-tester</code> and <code>figma-node-normalizer</code> have no RAG tools; they work from the mod, its logs or the Figma file.</p>
 <div class="tbl"><table>
  <thead><tr><th scope="col">Specialist</th><th scope="col">Procedure</th></tr></thead>
  <tbody>
   <tr class="grp"><th colspan="2" scope="colgroup">Script lead</th></tr>
   <tr><th scope="row"><code>dayz-script-specialist</code></th><td><ol class="flow"><li>Searches the vanilla scripts for the class it will change and reads the real file.</li><li>Writes a <code>modded class</code> in the right layer (3_Game, 4_World or 5_Mission) and calls <code>super</code>.</li><li>Adds RPCs only where client and server must talk, and checks which side runs each line.</li><li><code>/dayz-lint</code> and the build gate check and pack it (nothing compiles Enforce Script there); the in-game gate catches compile errors and reads script.log.</li></ol></td></tr>
   <tr><th scope="row"><code>dayz-workbench-specialist</code></th><td><ol class="flow"><li>Reads how vanilla Workbench plugins are registered.</li><li>Writes the plugin script and its tool panel.</li><li>Never opens Workbench itself: it tells the user to open it with <code>/dayz-launch-workbench --mod &lt;ModName&gt;</code>.</li><li>Returns the plugin and the steps to load and run it.</li></ol></td></tr>
   <tr><th scope="row"><code>dayz-persistence-specialist</code></th><td><ol class="flow"><li>Lists every value that must survive a restart.</li><li>Writes OnStoreSave and OnStoreLoad, with a version number written first.</li><li>Adds an upgrade path so saves from the last version still load.</li><li>Runs the data audit: every field is written and read back in the same order.</li><li>Hands the audit to the server lead before release.</li></ol></td></tr>
   <tr><th scope="row"><code>dayz-ai-specialist</code></th><td><ol class="flow"><li>Studies how vanilla infected and animals decide what to do.</li><li>Writes the behavior as its own script classes, never copied from another mod.</li><li>Gives the server lead the spawn setup.</li><li>In-game test watches the behavior and server performance.</li></ol></td></tr>
   <tr class="grp"><th colspan="2" scope="colgroup">Config lead</th></tr>
   <tr><th scope="row"><code>dayz-config-specialist</code></th><td><ol class="flow"><li>Finds the closest vanilla parent class (Grep for known names, RAG search for questions by meaning) and reads its definition on disk, cited as <code>path:line</code>.</li><li>Writes CfgPatches with the right requiredAddons, then the class itself.</li><li>Matches hiddenSelections to the names in the model.</li><li><code>/dayz-lint</code> and the build gate check it loads.</li></ol></td></tr>
   <tr><th scope="row"><code>dayz-vehicle-specialist</code></th><td><ol class="flow"><li>Picks the closest vanilla vehicle as the parent.</li><li>Writes the vehicle class and its simulation: engine, gearbox, axles, wheels.</li><li>Adds attachment slots for doors, hood, trunk, wheels, battery and plug, and the fluids.</li><li>Writes the CarScript or BoatScript class for seats, doors and damage.</li><li>Gives the server lead a types.xml entry; the behavior gate spawns it and a person-run checklist covers driving.</li></ol></td></tr>
   <tr><th scope="row"><code>dayz-weapon-specialist</code></th><td><ol class="flow"><li>Picks the closest vanilla weapon as the parent.</li><li>Writes the weapon, magazine and ammo classes and the attachment slots.</li><li>Sets recoil and fire modes.</li><li>Lists the model selections and memory points the art lead must provide.</li><li>The behavior gate spawns it and fits each attachment; a person-run checklist covers firing and reloading.</li></ol></td></tr>
   <tr class="grp"><th colspan="2" scope="colgroup">Art lead</th></tr>
   <tr><th scope="row"><code>dayz-object-builder</code></th><td><ol class="flow"><li>Specifies the LODs (visual, geometry, fire geometry, view geometry and memory) as numbered Object Builder steps; the user builds them, since it cannot edit a .p3d.</li><li>Names the selections and memory points the config and animations need, and writes model.cfg.</li><li>Runs <code>/dayz-p3d-audit</code> after the user saves the model.</li><li>Hands the selection names to the config lead.</li></ol></td></tr>
   <tr><th scope="row"><code>dayz-asset-specialist</code></th><td><ol class="flow"><li>Checks each texture has the right suffix (_co, _nohq, _smdi and the rest).</li><li>Packs them with <code>/dayz-pack-texture</code>.</li><li>Writes the .rvmat for each material.</li><li>Writes a look checklist for the user to check in Object Builder or in game; it never launches either.</li></ol></td></tr>
   <tr><th scope="row"><code>dayz-wearables-specialist</code></th><td><ol class="flow"><li>Picks the inventory slot and the closest vanilla item as the parent.</li><li>Sets slots held, protection and insulation.</li><li>Sets hidden selections so one model carries every color.</li><li>Notes the proxy positions for the Object Builder specialist.</li><li>The behavior gate wears each color class; a person checks in game how each color looks.</li></ol></td></tr>
   <tr><th scope="row"><code>dayz-animation-specialist</code></th><td><ol class="flow"><li>Lists the moving parts and their bones.</li><li>Writes skeletonBones for the moving parts and the class Animations block in model.cfg; the Object Builder specialist keeps the rest of model.cfg.</li><li>Gives the user the bone and selection names for their own Blender export.</li><li>Names the script hook that plays the animation; the script specialist writes that code, and the in-game test uses it.</li></ol></td></tr>
   <tr class="grp"><th colspan="2" scope="colgroup">UI lead</th></tr>
   <tr><th scope="row"><code>dayz-ui-specialist</code></th><td><ol class="flow"><li>Reads the vanilla layout closest to the new screen.</li><li>Writes the .layout and the script class that drives it.</li><li>Builds icons into an imageset with <code>/dayz-build-imageset</code>.</li><li>The layout checker checks it against the Figma-to-DayZ rules and <code>/dayz-layout-preview</code> draws it; the in-game test opens it.</li></ol></td></tr>
   <tr><th scope="row"><code>figma-node-normalizer</code></th><td><ol class="flow"><li>Reads the Figma frame.</li><li>Cleans layer names and structure so they map to DayZ widgets.</li><li>Hands the clean tree to the layout converter.</li></ol></td></tr>
   <tr><th scope="row"><code>figma-to-dayz-layout</code></th><td><ol class="flow"><li>Turns the clean tree into a DayZ .layout.</li><li>Uses only widget types the game supports.</li><li>Hands it to the layout checker.</li></ol></td></tr>
   <tr class="grp"><th colspan="2" scope="colgroup">Server lead</th></tr>
   <tr><th scope="row"><code>dayz-server-admin</code></th><td><ol class="flow"><li>Writes types.xml entries with <code>/dayz-edit-types</code>.</li><li>Adds events, spawn points and gameplay settings where needed.</li><li>Splits large economy files with <code>/dayz-split-types</code>.</li><li>Sets up a missing test server instance with <code>/dayz-add-server</code> (it starts nothing), and gives you the <code>/dayz-launch-test</code> command instead of starting the server itself.</li></ol></td></tr>
   <tr><th scope="row"><code>dayz-map-specialist</code></th><td><ol class="flow"><li>Writes layers.cfg and the surface and clutter configs; if it needs the user's own layers.cfg and it is missing, it stops and asks for it.</li><li>Gives numbered steps for the DayZ Editor export and the Terrain Builder import and generation, which the user carries out.</li><li>Returns the files and the steps to rebuild the map.</li></ol></td></tr>
   <tr class="grp"><th colspan="2" scope="colgroup">Release lead</th></tr>
   <tr><th scope="row"><code>dayz-build-engineer</code></th><td><ol class="flow"><li>Packs the mod with <code>/dayz-build-pbo</code>.</li><li>Starts the test session with <code>/dayz-launch-test</code>.</li><li>Reports the build result to the release lead, who passes it to the orchestrator.</li></ol></td></tr>
   <tr><th scope="row"><code>dayz-docs-writer</code></th><td><ol class="flow"><li>Reads what changed in the wave.</li><li>Updates the README, changelog and classname list.</li><li>With <code>/dayz-release-pack</code>, writes the Workshop text and server-owner notes.</li></ol></td></tr>
   <tr class="grp"><th colspan="2" scope="colgroup">Any lead</th></tr>
   <tr><th scope="row"><code>dayz-audio-fx-specialist</code></th><td><ol class="flow"><li>Reads the vanilla sound or particle closest to the request.</li><li>Writes the sound shader and sound set, or the particle with <code>/dayz-particles</code>.</li><li>Adds the script line that plays it.</li><li>In-game test listens and looks.</li></ol></td></tr>
   <tr><th scope="row"><code>dayz-physics-specialist</code></th><td><ol class="flow"><li>Reads the model's geometry LODs and mass.</li><li>Finds the fault: missing geometry, wrong mass or bad collision.</li><li>Hands the fix to the Object Builder or config specialist; it never edits.</li><li>A person-run in-game test drops, throws and shoots it, which the behavior gate cannot.</li></ol></td></tr>
   <tr class="grp"><th colspan="2" scope="colgroup">Checks and fixes</th></tr>
   <tr><th scope="row"><code>dayz-mod-reviewer</code></th><td><ol class="flow"><li>Reads the finished task against the DayZ rules file.</li><li>Lists each problem with the specialist who owns it.</li><li>Never edits files.</li></ol></td></tr>
   <tr><th scope="row"><code>dayz-layout-validator</code></th><td><ol class="flow"><li>Checks the .layout against the Figma-to-DayZ rules: file format and widget classes.</li><li>Reports PASS or FAIL with each problem and its line. Never edits.</li></ol></td></tr>
   <tr><th scope="row"><code>dayz-build-checker</code></th><td><ol class="flow"><li>Runs only when <code>/dayz-gate build</code> itself breaks.</li><li>Reads the AddonBuilder output and names the failing file.</li></ol></td></tr>
   <tr><th scope="row"><code>dayz-ingame-tester</code></th><td><ol class="flow"><li>Runs only when <code>/dayz-gate ingame</code> itself breaks.</li><li>Reads the logs from the test session and reports what failed.</li></ol></td></tr>
   <tr><th scope="row"><code>dayz-mod-debugger</code></th><td><ol class="flow"><li>Gets new errors that triage does not know.</li><li>Reads script.log, RPT and crash files back to the line that failed.</li><li>Reports the cause, evidence, location and fix to whoever called it (the orchestrator or a lead), naming the worker agent that owns the fix.</li></ol></td></tr>
  </tbody>
 </table></div>
</section>
"""
addons = """<section aria-labelledby="g-addons">
 <h2 id="g-addons">Add-ons (planned)</h2>
 <p>An optional <code>agentic-z-addons</code> plugin is planned for outside tools such as Blender, an AI 3D generator or another MCP server. No add-on ships yet; the plugin marketplace lists only <code>agentic-z</code> and <code>agentic-z-panel</code>. Each add-on will be a workflow that connects the outside tool at one point in the loop, usually handing a finished model to <code>dayz-object-builder</code>, so the normal gates check it like any other work. Planned rules:</p>
 <ul>
  <li><b>Opt-in:</b> the core never loads an add-on the user has not installed.</li>
  <li><b>Same gates:</b> add-on output goes through the mod review, the build gate and the in-game gate.</li>
  <li><b>No reverse engineering:</b> no add-on unpacks protected mods or converts binarized models back to editable ones.</li>
 </ul>
</section>
"""

def grab(html, sid):
    s = html.index('<section aria-labelledby="%s">' % sid)
    return html[s:html.index('</section>', s) + len('</section>')]
quality = ''.join(grab(team_html, sid) for sid in ('h-method', 'h-grades', 'h-grade-detail', 'h-bugs'))
# The shared sections above come from agentic-z-team.html as written there.
# Guide-only adjustments: the team chart's heading would clash with the guide's
# own "Architecture" section, and the method note points at a team-only section.
chart = re.sub(r'id="h-chart">[^<]*</h2>', 'id="h-chart">Team structure</h2>', chart)
quality = re.sub(r'as "Files not graded" under "Open items(?: and decisions)?" lists',
                 'as "Files not graded" in the Agentic-Z Agent Team document lists', quality)

workflows = """<section aria-labelledby="g-workflows">
 <h2 id="g-workflows">Paste-in routing</h2>
 <p>The UserPromptSubmit hook <code>paste_router.py</code> recognizes what you paste and adds context that points Claude at the matching workflow. It never blocks a prompt.</p>
 <div class="tbl"><table><thead><tr><th scope="col">Pasted input</th><th scope="col">Result</th></tr></thead><tbody>
  <tr><th scope="row">Crash log, RPT or <code>script.log</code> lines</th><td>Triaged in the hook against the <code>/dayz-gate</code> known errors: cause and fix for known lines; new lines go to <code>dayz-mod-debugger</code>.</td></tr>
  <tr><th scope="row">Screenshot of a bug</th><td>The hook suggests a specialist: UI problems to <code>dayz-ui-specialist</code>, texture or material problems to <code>dayz-asset-specialist</code>, an error message or wrong behavior to <code>dayz-script-specialist</code>. The <code>dayz-router</code> agent sends an on-screen error message to <code>dayz-mod-debugger</code> (or gate triage) instead, so the two can disagree on that case.</td></tr>
  <tr><th scope="row">Figma link</th><td>Runs the Figma pipeline and returns a checked <code>.layout</code>.</td></tr>
  <tr><th scope="row">GitHub link</th><td>Points at <code>/dayz-import-mod --source &lt;link&gt;</code>, which imports the mod into <code>workspace\\</code> and can add the missing standard pieces.</td></tr>
  <tr><th scope="row">Steam Workshop link</th><td>Refused with the reason: Workshop content is packed, binarized and often protected.</td></tr>
  <tr><th scope="row"><code>types.xml</code> chunk</th><td>Checks the entries, lists any problems and points at <code>/dayz-edit-types --merge</code>.</td></tr>
 </tbody></table></div>
 <p class="example">Answer tests (evals) cover 23 of the 30 agents, and a change may only keep or raise a score. Prompt caching is left to Claude Code, which handles it itself; Agentic-Z has no rule or test for it. The behavior and visual gates are tested with fixtures only and have not run in a live DayZ session yet.</p>
</section>
"""

def table(head, rows):
    h = ''.join('<th scope="col">%s</th>' % c for c in head)
    b = ''.join('<tr><th scope="row">%s</th>%s</tr>' % (r[0], ''.join('<td>%s</td>' % c for c in r[1:])) for r in rows)
    return '<div class="tbl"><table><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>' % (h, b)

agents = [
('<code>dayz-script-specialist</code>', 'Enforce Script: modded classes, RPCs, game logic.', '"Make my medkit heal over 30 seconds."'),
('<code>dayz-config-specialist</code>', 'config.cpp, CfgPatches, inheritance, hidden selections.', '"Write the CfgVehicles entry for my vest."'),
('<code>dayz-asset-specialist</code>', 'Textures (.paa) and materials (.rvmat).', '"Pack vest_camo_co.png and make an rvmat."'),
('<code>dayz-object-builder</code>', '.p3d models: LODs, selections, Object Builder steps.', '"Set up hidden selections on my vest model."'),
('<code>dayz-ui-specialist</code>', '.layout files, HUD and menu scripts.', '"Add a compass to the HUD."'),
('<code>dayz-map-specialist</code>', 'Terrain Builder, layers.cfg, surfaces, clutter.', '"Export my base from DayZ Editor to Terrain Builder."'),
('<code>dayz-server-admin</code>', 'types.xml, events, init.c, cfggameplay.', '"Make my vest spawn rarely in military zones."'),
('<code>dayz-workbench-specialist</code>', 'Workbench plugins (editor tools).', '"A plugin that checks texture suffixes."'),
('<code>dayz-mod-debugger</code>', 'Reads logs and crash files to find the cause.', '"My server crashes on start, here is the RPT."'),
('<code>dayz-mod-reviewer</code>', 'Read-only audit of a mod; returns PASS or FAIL.', '"Review workspace/MyVest before I build."'),
('<code>figma-node-normalizer</code>, <code>figma-to-dayz-layout</code>, <code>dayz-layout-validator</code>', 'Optional Figma pipeline: Figma frame to <code>.layout</code>; the validator checks it without editing.', '"Turn this Figma frame into a DayZ menu."'),
('<code>dayz-orchestrator</code> and team', 'Plans a whole mod, runs leads, workers and checks.', 'Plugin: <code>claude --agent agentic-z:dayz-orchestrator</code>. Clone: <code>claude --agent dayz-orchestrator</code>.'),
('<code>dayz-mod-architect</code>', 'Plans a mod: classes, files, assets and a task list.', 'Started by the orchestrator.'),
('<code>dayz-lead</code>', 'Runs one team (script, config, art, UI, server, release) and its review checks.', 'Started by the orchestrator.'),
('<code>dayz-build-checker</code>, <code>dayz-ingame-tester</code>', 'Fallback gates used when a <code>/dayz-gate</code> script errors (exit 2).', 'Started by the orchestrator.'),
('<code>dayz-build-engineer</code>', 'Builds the PBO (or deploys a prebuilt bundle) and starts a test session for you.', '"Build MyVest and start a test on chernarus."'),
('<code>dayz-docs-writer</code>', 'Writes the mod README, changelog and classname list.', '"Update the MyVest docs."'),
('<code>dayz-persistence-specialist</code>', 'Saving data across restarts, save versions, base building, and a data audit before release.', '"Make my safe keep its code and contents after a restart."'),
('<code>dayz-ai-specialist</code>', 'Infected, animals and human AI such as patrols and guards, written from scratch.', '"Add guards that patrol my base and react to gunfire."'),
('<code>dayz-vehicle-specialist</code>', 'Cars, boats and helicopters: engine, gearbox, wheels, doors, fluids, seats and damage.', '"Add a four door pickup with a bigger fuel tank."'),
('<code>dayz-weapon-specialist</code>', 'Weapons, magazines, ammo, attachments, recoil and fire modes.', '"Add a hunting rifle that takes a five round magazine."'),
('<code>dayz-wearables-specialist</code>', 'Clothing, characters, inventory slots, protection, color variants and proxies.', '"Make a plate carrier in three colors."'),
('<code>dayz-animation-specialist</code>', 'model.cfg animations, RTM files and the Blender handoff.', '"Make my bunker doors open and close."'),
('<code>dayz-audio-fx-specialist</code>', 'Sound shaders, sound sets and particle effects.', '"Give my generator a running sound and exhaust smoke."'),
('<code>dayz-physics-specialist</code>', 'Weight, collision LODs, dropping, throwing and contact.', '"My crate falls through the floor. Fix it."'),
('<code>dayz-router</code>', 'Haiku agent that picks the handler when the <code>/dayz-route</code> stages are not confident.', 'Called after <code>/dayz-route</code>.'),
('<code>agent-creator</code>', 'Writes and checks new agent files.', '"Create an agent that reviews RPC security."'),
]

trouble = [
('<code>[FAIL] P:\\ is NOT mounted</code>', 'P: is not mounted (it does not survive a reboot).', 'Mount it in DayZ Tools, or run <code>/dayz-workdrive</code>.'),
('<code>[WARN] DayZ Tools not detected</code>', 'Not installed, or installed somewhere unusual.', 'Install from Steam (Tools), or set <code>DAYZ_TOOLS_PATH</code>.'),
('<code>[WARN] Vanilla DayZ data not detected on P:\\</code>', 'Game data not extracted.', 'DayZ Tools, Extract Game Data (once per Tools update).'),
('<code>P:\\Mods\\</code> missing, a real folder, or dangling', 'Built PBOs must land in the Workshop folder.', '<code>cmd /c mklink /J P:\\Mods "&lt;DayZ install&gt;\\!Workshop"</code>'),
('<code>Connection failed 0x00020005</code>', 'serverDZ.cfg lacks <code>allowFilePatching = 1;</code>.', 'Rerun <code>/dayz-add-server &lt;instance&gt;</code>.'),
('"Mission script has no main function"', 'Server found no valid mission folder.', '<code>/dayz-add-server &lt;instance&gt; --refresh-mission</code>'),
('<code>[FAIL] DayZDiag_x64.exe not found</code>', 'Incomplete DayZ install.', 'Verify DayZ in Steam; Diag ships next to DayZ_x64.exe.'),
('<code>[FAIL] P:\\&lt;ModName&gt; exists as a real folder, not a link</code>, or <code>is a link pointing at ...</code>', 'A folder, or a link to somewhere else, is already there.', 'Move it, or <code>cmd /c rmdir P:\\&lt;ModName&gt;</code> if it is a stray link.'),
('<code>[FAIL] Mod \'&lt;ModName&gt;\' has no Addons folder at ...</code>, or <code>has no .pbo files in ...</code>', 'Launched before building.', 'Run <code>/dayz-build-pbo &lt;ModName&gt;</code> first.'),
('<code>[FAIL] P:\\&lt;ModName&gt; junction is missing</code>', 'The P: link to your mod folder is gone.', '<code>/dayz-add-scaffold &lt;ModName&gt; --piece junction</code>.'),
('<code>ERROR</code> from <code>/dayz-gate</code> asking for <code>--deps</code>', 'The mod\'s config.cpp needs non-vanilla addons, such as CF.', 'Pass them: <code>/dayz-gate ingame &lt;ModName&gt; --deps CF</code>.'),
('<code>FAIL</code> from <code>/dayz-lint</code> before a build', 'An error that would stop the mod loading.', 'Fix the <code>file:line</code> it names; each finding names its owner.'),
('Mod does not load in game', 'One of the setup pieces is off.', 'Run <code>/dayz-preflight</code>, check the junction, CfgPatches entry, PBO date, the server <code>script*.log</code>, and that the client used <code>-mod=P:\\Mods\\@&lt;ModName&gt;</code>.'),
]

faq = [
('Does it cost money?', 'Agentic-Z is free to use for DayZ mods (see <code>LICENSE</code>). You need your own AI tool (see "Overview" for what each one supports). RAG search needs a Voyage AI key: the last full index build embedded about 66M tokens, and the current indexer makes more chunks, so check Voyage pricing. The prebuilt index from <code>/dayz-search-download</code> avoids the build cost; see "RAG search".'),
('Will it touch my other mods?', 'No skill writes to your other mods. Besides your mod, its P: link, its test server and its build folder, skills write only the state listed in "File layout". <code>/dayz-scope-mod &lt;ModName&gt;</code> also blocks edits to every other mod in <code>workspace\\</code>.'),
('Does it publish to the Workshop?', 'No. Builds land in <code>P:\\Mods\\@&lt;ModName&gt;</code>, which the launcher loads. Publish with DayZ Tools Publisher.'),
('Can I work on several mods?', 'Yes. Each mod lives in <code>workspace\\&lt;ModName&gt;</code>. Select "Set up or switch to another mod" in the <code>/dayz-init</code> hub.'),
('Is it safe to run?', 'See "Permissions and safety".'),
]

doc = '''<title>Agentic-Z Guide</title>
<meta name="claude:viewport-fit-sides" content="cover">
%s%s
<div class="wrap">
<section class="cover" aria-label="Cover">
 <div class="cover-kicker">Guide &middot; October 2026</div>
 <div class="cover-bar"></div>
 <h1 class="cover-title">Agentic-Z</h1>
 <p class="cover-sub">The Guide</p>
 <p class="cover-desc">How to install Agentic-Z, set up your DayZ modding environment and work with its agents and skills, from your first mod to a tested build on your own test server.</p>
 <div class="cover-foot">Agentic-Z &middot; DayZ n' Chill &middot; github.com/DayZ-n-Chill/Agentic-Z</div>
</section>
<header>
 <h1>Agentic-Z Guide</h1>
 <p class="lede">Reference for installing, configuring and using Agentic-Z, the AI agent stack for DayZ modding. This edition covers version 2.0.0: 30 agents, 44 skills, three hooks and a side panel plugin.</p>
</header>

<section aria-labelledby="g-what">
 <h2 id="g-what">Overview</h2>
 <p>Agentic-Z is a Claude Code plugin and repo template for DayZ modding. It adds DayZ specialist agents, skills (slash commands) that drive DayZ Tools, rules files for mod conventions, and the <code>dayz-rag</code> MCP server, which searches the vanilla game files so agents cite real files instead of guessing.</p>
 <div class="specs">
  <div class="sg"><h3>Specialists</h3><ul><li>Scripts, configs, UI</li><li>Models and textures</li><li>Maps and server</li><li>Saving data and AI</li><li>Vehicles and weapons</li><li>Wearables and animation</li><li>Audio, FX and physics</li><li>Review and debugging</li></ul></div>
  <div class="sg"><h3>Skills</h3><ul><li>Setup wizard</li><li>Lint and build PBO</li><li>Launch test and gates</li><li>types.xml</li><li>Textures and layouts</li><li>Release pack</li></ul></div>
  <div class="sg"><h3>RAG search</h3><ul><li>Vanilla scripts</li><li>Configs</li><li>Layouts</li><li>Materials</li></ul></div>
 </div>
 %s
</section>

<section aria-labelledby="g-fit">
 <h2 id="g-fit">Architecture</h2>
 <p>The AI tool loads the rules, agents and skills and calls the <code>dayz-rag</code> MCP server. These act on the mod folder, the P: drive, DayZ Tools and the game, and the search index on disk.</p>
 %s
</section>

<section aria-labelledby="g-req">
 <h2 id="g-req">Requirements</h2>
 %s
 <h3>Optional features</h3>
 %s
</section>

<section aria-labelledby="g-setup">
 <h2 id="g-setup">Installation and setup</h2>
 %s
 <p>Install Agentic-Z one way only. A clone and a plugin together load every skill twice.</p>
 %s
 <h3>Option A: clone as a template</h3>
 <pre><code>git clone https://github.com/DayZ-n-Chill/Agentic-Z.git my-dayz-mod
cd my-dayz-mod
python .claude\\skills\\sync-skills\\sync.py</code></pre>
 <h3>Option B: install as a Claude Code plugin</h3>
 <pre><code>/plugin marketplace add DayZ-n-Chill/Agentic-Z
/plugin install agentic-z@dayz-n-chill</code></pre>
 <h3>Setup wizard</h3>
 <pre><code>/dayz-init</code></pre>
 <p>On first run the wizard asks for: new mod or import, the mod name, the test map, and whether to build and launch. It fixes what it can (mounts P:, creates the <code>P:\\Mods</code> link) and prints the fix for the rest. Later runs open a status hub for the active mod.</p>
</section>

<section aria-labelledby="g-loop">
 <h2 id="g-loop">Build loop</h2>
 %s
 <ol class="steps">
  <li><span>Ask an agent for the change, for example "add a hidden selection for the camo".</span></li>
  <li><span><code>/dayz-build-pbo &lt;ModName&gt;</code> packs the mod into <code>P:\\Mods\\@&lt;ModName&gt;\\Addons\\</code>.</span></li>
  <li><span><code>/dayz-launch-test &lt;ModName&gt; --server &lt;instance&gt;</code> starts a DayZ Diag server and client with the mod loaded.</span></li>
  <li><span>Read the logs (locations in "File layout"), or pass them to <code>dayz-mod-debugger</code>.</span></li>
  <li><span><code>/dayz-stop-test</code> stops every <code>DayZDiag_x64.exe</code> process.</span></li>
 </ol>
</section>

<section aria-labelledby="g-agents">
 <h2 id="g-agents">Agents</h2>
 <p>Describe the task and Claude Code picks the specialist, or name one: "use the dayz-config-specialist to ...". Full scope and output of the eight domain specialists are in "Domain specialists".</p>
 %s
</section>

%s
<section aria-labelledby="g-wave">
 <h2 id="g-wave">Gates</h2>
 <p><code>dayz-orchestrator</code> runs a full mod build as the main session. Start it with <code>claude --agent agentic-z:dayz-orchestrator</code> (plugin) or <code>claude --agent dayz-orchestrator</code> (clone). It plans the mod with <code>dayz-mod-architect</code>, waits for your approval, then runs the work in waves. Each wave passes these gates in order; who runs which gate is in "Team structure".</p>
 <div class="tbl"><table><thead><tr><th scope="col">Gate</th><th scope="col">Runs</th><th scope="col">Checks</th></tr></thead><tbody>
  <tr><th scope="row">Mod review (<code>dayz-mod-reviewer</code>)</th><td>Every task</td><td>Convention compliance and common defects; read only.</td></tr>
  <tr><th scope="row">Layout check (<code>dayz-layout-validator</code>)</th><td>Every <code>.layout</code> change</td><td>The Figma-to-DayZ rules; read only.</td></tr>
  <tr><th scope="row">Build (<code>/dayz-gate build</code>)</th><td>Once per wave</td><td><code>/dayz-lint</code>, then AddonBuilder output.</td></tr>
  <tr><th scope="row">In-game (<code>/dayz-gate ingame</code>)</th><td>Once per wave</td><td>Server and client logs after the client joins the mission.</td></tr>
  <tr><th scope="row">Behavior (<code>/dayz-gate behavior</code>)</th><td>Once per wave, when <code>output\\&lt;ModName&gt;-plan\\behavior-checks.json</code> exists</td><td>A scripted mission spawns and uses each new item.</td></tr>
 </tbody></table></div>
 <p><code>/dayz-gate</code> prints its verdict on the first line: <code>PASS</code> (exit 0), <code>FAIL</code> (exit 1) or <code>ERROR</code> (exit 2). On an <code>ERROR</code> from the gate script itself, the orchestrator falls back to <code>dayz-build-checker</code> or <code>dayz-ingame-tester</code>; the behavior gate has no fallback agent. Nothing reaches you until it builds, loads in game with clean logs and, when the plan lists behavior checks, passes the behavior gate.</p>
 %s
</section>

<section aria-labelledby="g-rag">
 <h2 id="g-rag">RAG search</h2>
 <p>The <code>dayz-rag</code> MCP server searches an index of the vanilla files on P:. <code>/dayz-search-index</code> builds the index with Voyage AI embeddings (<code>voyage-code-3</code> by default) into LanceDB at <code>~\\.claude\\dayz-search-index\\</code>. <code>/dayz-search-download</code> installs a prebuilt index instead; it is older than the current indexer. Searching still needs <code>VOYAGE_API_KEY</code>, because each query is embedded through the Voyage AI API.</p>
 %s
 %s
 <p>Lookup order: agents Grep first when they know an exact class or symbol name, and use RAG search for questions by meaning or after two or three failed greps. A hit is a hint until the agent opens the real file, so answers cite <code>path:line</code>.</p>
</section>

<section aria-labelledby="g-tiers">
 <h2 id="g-tiers">Rule tiers</h2>
 %s
 <p>Tier 2 is <code>.claude/skills/_shared/dayz-conventions.md</code> (143 lines) plus five topic files in <code>conventions/</code>: <code>config.md</code>, <code>assets.md</code>, <code>scripts.md</code>, <code>ui.md</code> and <code>server.md</code>. After you correct an agent, <code>/dayz-record-correction</code> writes the rule into the right tier once you approve it.</p>
</section>

%s
%s
%s

<section aria-labelledby="g-layout">
 <h2 id="g-layout">File layout</h2>
 <p>Your files and every location the skills write to, apart from the repo's own tool folders.</p>
 <pre><code>&lt;repo&gt;\\
  workspace\\&lt;ModName&gt;\\           your mod source
  .server\\&lt;instance&gt;\\            local test server (mission, serverDZ.cfg, Profiles)
  .server\\&lt;instance&gt;\\Profiles\\   server logs
  .server\\&lt;instance&gt;-behavior\\   copy of the instance the behavior gate runs in
  .server\\!ClientDiagLogs\\       client logs
  .server\\!Health\\&lt;ModName&gt;\\     stored gate results and the /dayz-health page
  .claude\\local-memory\\          your author handle, active project, wizard state
  .claude\\settings.local.json     local settings
  .claude\\.upstream-baseline      written by /agentic-z-update
  .claude\\.upstream-update.lock   written by /agentic-z-update
  output\\&lt;ModName&gt;-plan\\         the plan, behavior checks and the visual shots list
  output\\&lt;ModName&gt;-visual\\       visual gate screenshots per run, and the baselines
  output\\&lt;ModName&gt;-release\\      release pack texts and server kit zip
  output\\layout-preview\\         /dayz-layout-preview images
  output\\evals\\                  answer test results
  output\\                        other one-off deliverables
~\\.claude\\dayz-search-index\\     RAG search index
~\\.claude\\dayz-upgrade-guard\\    vanilla snapshots for /dayz-upgrade-guard (about 10 MB each)
P:\\
  &lt;ModName&gt;\\                     link to workspace\\&lt;ModName&gt;
  Mods\\@&lt;ModName&gt;\\Addons\\        built PBO (Mods links to DayZ\\!Workshop)
  dz\\                            vanilla data you extracted once
  scripts\\                       vanilla scripts, also read by the skills</code></pre>
 <p>Other writes: Object Builder settings in the registry (<code>/dayz-setup-objectbuilder</code>), the skill links from <code>/sync-skills</code>, rule files after your approval in <code>/dayz-record-correction</code>, and, for <code>/agentic-z-update</code>, updated template files checked out into your clone and committed.</p>
</section>

<section aria-labelledby="g-env">
 <h2 id="g-env">Configuration</h2>
 <p>Environment variables. Set them only when the default location or behavior does not fit.</p>
 %s
</section>

<section aria-labelledby="g-safe">
 <h2 id="g-safe">Permissions and safety</h2>
 <ul>
  <li><b>Shipped permissions (clone only):</b> <code>.claude/settings.json</code> allows the repo's own skills and scripts, plus <code>npm install</code> and <code>npm ci</code> from the lockfile. It denies <code>python -c</code>, <code>python -m</code>, <code>node -e</code>, <code>node -p</code>, <code>npx</code>, and <code>npm install</code> or <code>npm i</code> with a package name. Other inline forms such as <code>py -c</code> are not on the allow list, so they prompt first. A plugin install does not get this file, because plugins cannot ship permissions.</li>
  <li><b>Agent tools:</b> every agent has an explicit tool list. The five gates (<code>dayz-mod-reviewer</code>, <code>dayz-layout-validator</code>, <code>dayz-build-checker</code>, <code>dayz-ingame-tester</code> and <code>dayz-mod-debugger</code>) have no Edit or Write tools; four of them have Bash to run their checks, and only the debugger has no Bash.</li>
  <li><b>Network access:</b> <code>agent-creator</code> has WebFetch, and <code>figma-node-normalizer</code> uses the remote Figma MCP tools. The 21 agents that use RAG search send query text to the hosted Voyage AI API through <code>search_dayz_source</code>. With <code>TYPESAFE_API_KEY</code> set, <code>/dayz-route</code> sends the request text to <code>api.typesafe.ai</code> for Jev.</li>
  <li><b>Scope lock:</b> <code>/dayz-scope-mod &lt;ModName&gt;</code> blocks edits to every other mod in <code>workspace\\</code> (start Claude Code from the project root); <code>--clear</code> lifts it.</li>
  <li><b>Cleanup:</b> cleanup removes only what the toolkit made, and destructive steps ask first or need <code>--yes</code>.</li>
 </ul>
</section>

<section aria-labelledby="g-trouble">
 <h2 id="g-trouble">Troubleshooting</h2>
 %s
</section>

<section aria-labelledby="g-faq">
 <h2 id="g-faq">FAQ</h2>
 %s
</section>

<section aria-labelledby="g-help">
 <h2 id="g-help">Support and contributing</h2>
 <p>Discord: <code>discord.gg/dayznchill</code>. Repo: <code>github.com/DayZ-n-Chill/Agentic-Z</code>. Contributing: branch from <code>develop</code> with a <code>feature/</code>, <code>fix/</code> or <code>docs/</code> prefix and open the pull request against <code>develop</code>.</p>
</section>
<p class="foot">Agentic-Z by DayZ n' Chill.</p>
</div>
''' % (
    fonts, style + '<style>pre{background:var(--band);border:1px solid var(--rule);border-radius:10px;padding:12px 14px;overflow-x:auto;font-family:var(--mono);font-size:13px;line-height:1.5;margin:0}h3{margin-top:6px}tbody th{white-space:normal;width:30%}.wrap ul{margin:0;padding-left:20px;display:grid;gap:6px}</style>',
    table(['Feature', 'Claude Code', 'Codex CLI', 'Gemini CLI'], [
        ('Skills', 'Yes', 'Yes, linked by <code>/sync-skills</code>', 'Yes, linked by <code>/sync-skills</code>'),
        ('Rules file', '<code>CLAUDE.md</code>', '<code>AGENTS.md</code>', '<code>GEMINI.md</code>'),
        ('Agents, hooks, RAG search', 'Yes', 'No', 'No'),
    ]),
    arch,
    table(['Requirement', 'Needed for'], [
        ('Windows', 'DayZ Tools and the P: drive are Windows only.'),
        ('DayZ (Steam)', 'Test sessions: <code>DayZDiag_x64.exe</code> ships next to <code>DayZ_x64.exe</code>.'),
        ('DayZ Tools (Steam, free)', 'AddonBuilder, P: drive mounting and ImageToPAA.'),
        ('DayZ Server (Steam, app 223350)', '<code>/dayz-add-server</code> copies the mission template from it for each new instance and for <code>--refresh-mission</code>.'),
        ('P: mounted, vanilla data extracted', 'Configs inherit from the vanilla classes on P:.'),
        ('Python 3.10+ on PATH', 'The skills are Python scripts.'),
        ('Claude Code, Codex CLI or Gemini CLI', 'The AI tool. Feature support is in "Overview".'),
    ]),
    table(['Feature', 'Needs'], [
        ('RAG search', '<code>pip install -r .claude\\mcp\\dayz-rag\\requirements.txt</code> and <code>VOYAGE_API_KEY=pa-...</code> in <code>.env</code> at the repo root.'),
        ('Building the index (<code>/dayz-search-index</code>)', 'Also <code>pip install -r .claude\\skills\\dayz-search-index\\requirements.txt</code>.'),
        ('Figma pipeline', 'A Figma MCP server.'),
        ('<code>/dayz-p3d-audit</code>', 'py3d.'),
        ('<code>/dayz-build-imageset</code>, <code>/dayz-layout-preview</code>, <code>/dayz-gate visual</code>', 'Pillow.'),
        ('<code>/dayz-cot-bootstrap</code>', 'The CF and COT mods.'),
    ]),
    setup,
    table(['', 'Option A: clone', 'Option B: plugin'], [
        ('Use for', 'A new mod project', 'An existing project'),
        ('Skill names', '<code>/dayz-build-pbo</code>', '<code>/agentic-z:dayz-build-pbo</code>'),
        ('Orchestrator', '<code>claude --agent dayz-orchestrator</code>', '<code>claude --agent agentic-z:dayz-orchestrator</code>'),
        ('Permissions', 'Shipped in <code>.claude/settings.json</code>', 'None; plugins cannot ship permissions'),
        ('Updates', '<code>/agentic-z-update</code>', 'The Claude Code plugin marketplace'),
    ]),
    daily,
    table(['Agent', 'Scope', 'Example request or entry point'], agents),
    chart.replace('<section aria-labelledby="h-chart">', '<section aria-labelledby="h-chart">'),
    wave,
    rag,
    table(['MCP tool', 'Function'], [
        ('<code>search_dayz_source</code>', 'Searches vanilla scripts, configs, layouts and materials by meaning.'),
        ('<code>get_dayz_file</code>', 'Opens an exact file and line range on P:.'),
        ('<code>list_indexed_sources</code>', 'Lists what is indexed and when.'),
    ]),
    tiers,
    savers + coming + spec_flows + workflows + addons + quality, skills, packs,
    table(['Variable', 'Purpose'], [
        ('<code>DAYZ_TOOLS_PATH</code>', 'DayZ Tools install (holds Bin\\AddonBuilder).'),
        ('<code>DAYZ_GAME_PATH</code>', 'DayZ game install (DayZ_x64.exe and its !Workshop folder).'),
        ('<code>DAYZ_DIAG_PATH</code>', 'DayZDiag_x64.exe, when it is not next to the game.'),
        ('<code>DAYZ_VANILLA_DATA_PATH</code>', 'Extracted vanilla data, when it is not at P:\\dz.'),
        ('<code>DAYZ_WORK_DRIVE</code>', 'The work drive folder /dayz-workdrive mounts as P:.'),
        ('<code>DAYZ_SERVER_PATH</code>', 'DayZ Server install, used by /dayz-add-server.'),
        ('<code>VOYAGE_API_KEY</code>', 'In .env, for RAG search.'),
        ('<code>VOYAGE_MODEL</code>', 'Voyage embedding model for the index and searches (default voyage-code-3).'),
        ('<code>VOYAGE_FREE_TIER_TOKENS</code>', 'Your Voyage token budget, when your plan differs from the default the indexer warns against.'),
        ('<code>DAYZ_RAG_MAX_DISTANCE</code>', 'Default distance cutoff for search hits (unset by default).'),
        ('<code>TYPESAFE_API_KEY</code>', 'Turns on Jev in /dayz-route.'),
    ]),
    table(['Symptom', 'Cause', 'Fix'], trouble),
    table(['Question', 'Answer'], faq),
)
(here / 'agentic-z-guide.html').write_text(doc, encoding='utf-8')
print('ok', doc.count('<h2'))
