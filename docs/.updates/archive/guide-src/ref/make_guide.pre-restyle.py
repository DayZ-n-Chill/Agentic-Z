import pathlib, re
here = pathlib.Path(__file__).parent
team = (here / 'agentic-z-team.html').read_text(encoding='utf-8')
style = team[team.index('<style>'):team.index('</style>') + len('</style>')]
fonts = team[team.index('<link rel="preconnect"'):team.index('<style>')]
chart = team[team.index('<section aria-labelledby="h-chart">'):]
chart = chart[:chart.index('</section>') + len('</section>')]
chart = chart.replace('id="h-chart">The flowchart', 'id="h-chart">The mod team')
skills = team[team.index('<section aria-labelledby="h-skills">'):]
skills = skills[:skills.index('</section>') + len('</section>')]
skills = skills.replace('id="h-skills">The skills', 'id="h-skills">Every skill')

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
a += box(440, 10, 260, 56, 'b-you', 'You', 'ask in plain English')
a += arrow(570, 66, 570, 96)
a += box(400, 98, 340, 56, 'b-orch', 'Claude Code', 'Codex and Gemini CLI get skills and rules')
a += arrow(570, 154, 570, 184)
a += '<rect class="band" x="40" y="186" width="1060" height="150" rx="12"/><text class="lay" x="140" y="210" style="text-anchor:start">AGENTIC-Z</text>'
a += box(60, 224, 230, 96, 'b-play', 'Rules', 'Tier 1 and Tier 2')
a += box(310, 224, 230, 96, 'b-lead', 'Agents', 'DayZ specialists')
a += box(560, 224, 230, 96, 'b-lead', 'Skills', 'slash commands')
a += box(810, 224, 270, 96, 'b-orch2', 'dayz-rag server', 'RAG search tools')
for x in (175, 425, 675):
    a += arrow(x, 336, x, 380)
a += arrow(945, 336, 945, 380)
a += box(60, 382, 230, 60, 'b-work', 'Your mod', 'workspace\\<ModName>')
a += box(310, 382, 230, 60, 'b-work', 'P: drive', 'vanilla data, junctions')
a += box(560, 382, 230, 60, 'b-work', 'DayZ Tools + game', 'AddonBuilder, Diag')
a += box(810, 382, 270, 60, 'b-work', 'Search index on disk', 'LanceDB + Voyage AI')
arch = svg(1140, 460, 'How Agentic-Z fits together', a)

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
s += '<polyline class="ln" points="1050,130 1050,155 200,155 200,178" fill="none" marker-end="url(#ah)"/>'
setup = svg(1140, 290, 'Setup steps', s)

# 3 daily loop
loop = [('Edit', 'with an agent'), ('/dayz-build-pbo', 'pack the PBO'), ('/dayz-launch-test', 'server + client'), ('Read logs', 'script.log, RPT'), ('/dayz-stop-test', 'close DayZ')]
d = ''
pos = [(40, 30), (430, 30), (820, 30), (820, 170), (430, 170)]
for i, (t, sub) in enumerate(loop):
    x, y = pos[i]
    d += box(x, y, 300, 90, 'b-lead', t, sub)
d += arrow(340, 75, 428, 75) + arrow(730, 75, 818, 75) + arrow(970, 120, 970, 168) + arrow(820, 215, 732, 215)
d += '<polyline class="ln learn" points="430,215 190,215 190,122" fill="none" marker-end="url(#ah)"/><text class="note learn-t" x="200" y="245">Fix and repeat</text>'
d += box(820, 310, 300, 70, 'b-you', 'Ready?', 'publish with DayZ Tools Publisher')
d += arrow(970, 260, 970, 308)
daily = svg(1140, 400, 'Daily loop', d)

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
wave = svg(1140, 250, 'One wave of work', w)

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
r += box(860, 192, 262, 60, 'b-you', 'Agent', 'searches by meaning')
r += arrow(860, 222, 700, 222)
r += box(440, 192, 258, 60, 'b-gate', 'Verify', 'opens the real file')
r += '<text class="note" x="20" y="232">Or skip building: /dayz-search-download installs a prebuilt index.</text>'
rag = svg(1140, 270, 'RAG search pipeline', r)

# 6 tiers
tt = ''
tt += box(170, 20, 800, 70, 'b-play', 'Tier 1: repo rules', 'CLAUDE.md, AGENTS.md, GEMINI.md, every agent, every task')
tt += box(220, 104, 700, 70, 'b-lead', 'Tier 2: DayZ rules', 'dayz-conventions.md plus conventions/*.md topic files, all DayZ work')
tt += box(270, 188, 600, 70, 'b-orch', 'Tier 3: agents, skills, knowledge packs', 'only what the task needs')
tt += '<text class="note" x="570" y="282" text-anchor="middle">The more specific tier wins. /dayz-record-correction turns your corrections into rules.</text>'
tiers = svg(1140, 300, 'Three tiers', tt)


# 7 token savers
rr = ''
rr += box(20, 40, 200, 64, 'b-you', 'Your request', '')
rr += arrow(220, 72, 262, 72)
rr += box(264, 40, 220, 64, 'b-play', 'Keyword rules', 'free, instant')
rr += arrow(484, 72, 526, 72)
rr += box(528, 40, 220, 64, 'b-orch2', 'Jev', 'if TYPESAFE_API_KEY set')
rr += arrow(748, 72, 790, 72)
rr += box(792, 40, 220, 64, 'b-orch2', 'dayz-router', 'Haiku, cheap')
rr += '<polyline class="ln" points="374,104 374,160 900,160" fill="none" marker-end="url(#ah)"/>'
rr += '<polyline class="ln" points="638,104 638,160" fill="none"/>'
rr += '<line class="ln" x1="902" y1="104" x2="902" y2="140" marker-end="url(#ah)"/>'
rr += box(800, 142, 320, 60, 'b-lead', 'Skill, specialist or team', '')
rr += '<text class="note" x="20" y="190">Each step only runs if the one before was not confident.</text>'
router = svg(1140, 215, 'Router', rr)
savers = """<section aria-labelledby="g-savers">
 <h2 id="g-savers">Token savers</h2>
 <p>These move mechanical work out of the AI, so it only spends tokens on judgment work: planning, writing code and configs, review and real diagnosis.</p>
 %s
 <div class="tbl"><table><thead><tr><th scope="col">Feature</th><th scope="col">What it does</th><th scope="col">How to use it</th></tr></thead><tbody>
  <tr><th scope="row">Script-only checks</th><td>Builds the mod or loads it in game and prints PASS or FAIL, with no AI involved.</td><td><code>/dayz-gate build &lt;ModName&gt;</code>, <code>/dayz-gate ingame &lt;ModName&gt;</code></td></tr>
  <tr><th scope="row">Log triage</th><td>Matches failures against 52 known errors with their fix and owner. Only new errors go to the debugger.</td><td>Runs inside <code>/dayz-gate</code>; <code>triage.py --learn</code> adds your own.</td></tr>
  <tr><th scope="row">Router</th><td>Decides who handles a request: keyword rules, then Jev, then a cheap Haiku router.</td><td><code>/dayz-route "&lt;request&gt;"</code> (the AI runs it first)</td></tr>
  <tr><th scope="row">Edit hooks</th><td>Checks <code>config.cpp</code> and <code>.layout</code> syntax after every edit, and blocks edits to other mods while scoped.</td><td>Automatic with the plugin or a clone.</td></tr>
  <tr><th scope="row">Paste-in router</th><td>Reads what you paste: crash logs are triaged on the spot, <code>types.xml</code> chunks are checked for a merge, Figma and GitHub links start their workflow.</td><td>Automatic; just paste.</td></tr>
  <tr><th scope="row">Status line</th><td>Shows P:, the active mod, whether DayZ Diag is running and the search index age.</td><td><code>/dayz-statusline</code> once per project.</td></tr>
  <tr><th scope="row">Launcher panel</th><td>A panel beside the chat with buttons for mount P:, build, the build and in-game checks, deploy, launch, stop, Workbench, Object Builder, test logs, the health page and the release pack, plus a field that asks <code>/dayz-ask</code>.</td><td><code>/plugin install agentic-z-panel@dayz-n-chill</code>, then <code>/dayz-panel</code>.</td></tr>
  <tr><th scope="row">Cheaper models</th><td>The build engineer and router run on Haiku, the docs writer on Sonnet.</td><td>Automatic.</td></tr>
  <tr><th scope="row">Smaller rules</th><td>The DayZ rules file is split into a 143-line core and five topic files of 24 to 56 lines. Most skills read only the core, 40%% less than the old 239-line file; <code>/dayz-deploy-pbo</code> and <code>/dayz-gate</code> also point to the bundle mods section of the config topic file. Each agent reads the core plus the topic files its job needs. With one topic file that is 17%% to 30%% less than before. With two it depends on which two: the mod debugger (226 lines) and the mod architect (231 lines) still read a little less, while the vehicle, weapon and audio and FX specialists (251 lines) read more, and so does the mod reviewer with three (283 lines).</td><td>Automatic.</td></tr>
  <tr><th scope="row">No-token wrappers</th><td>A <code>.bat</code> for every runnable skill, so you can run it yourself with no AI involved.</td><td>See <code>scripts\\README.md</code>.</td></tr>
  <tr><th scope="row">Shorter descriptions</th><td>Every skill and agent description loads into every session, so they were cut to about 2,100 tokens less.</td><td>Automatic.</td></tr>
 </tbody></table></div>
</section>
""" % router

team_html = (here / 'agentic-z-team.html').read_text(encoding='utf-8')
gsec = team_html[team_html.index('<section aria-labelledby="h-growth">'):]
grow_chart = gsec[gsec.index('<div class="chart">'):]
grow_chart = grow_chart[:grow_chart.index('</svg></div>') + len('</svg></div>')]
grow_chart = re.sub(r'<rect class="tag"[^>]*/><text class="tag-t"[^>]*>NEW</text>', '', grow_chart).replace(' (NEW)', '').replace('/dayz-lint (NEW)', '/dayz-lint')
cycle_start = gsec.index('<div class="chart">', gsec.index('<h3>The same cycle'))
cycle_chart = gsec[cycle_start:gsec.index('</svg></div>', cycle_start) + len('</svg></div>')]
coming = """<section aria-labelledby="g-coming">
 <h2 id="g-coming">Specialists for every part of a mod</h2>
 <p>Beyond scripts, configs, art, UI, maps and servers, Agentic-Z has specialists for saving data, vehicles, weapons, wearables, animation, audio, physics and AI. Each works under a team lead and brings its own reference pack, checked against the vanilla game files and loaded only when a task needs it. <code>/dayz-lint</code> runs inside the build check and stops a mod that would fail to load before it is packed.</p>
 %s
 <div class="tbl"><table><thead><tr><th scope="col">Specialist</th><th scope="col">Covers</th><th scope="col">Works under</th></tr></thead><tbody>
  <tr><th scope="row"><code>dayz-persistence-specialist</code></th><td>Saving data across restarts, save versions, base building, a check before release that nothing gets lost.</td><td>Script lead</td></tr>
  <tr><th scope="row"><code>dayz-vehicle-specialist</code></th><td>Cars, boats and helicopters.</td><td>Config lead</td></tr>
  <tr><th scope="row"><code>dayz-weapon-specialist</code></th><td>Weapons, attachments and magazines.</td><td>Config lead</td></tr>
  <tr><th scope="row"><code>dayz-wearables-specialist</code></th><td>Clothing, characters, slots and proxies.</td><td>Art lead</td></tr>
  <tr><th scope="row"><code>dayz-animation-specialist</code></th><td>model.cfg animations, RTM and the Blender handoff.</td><td>Art lead</td></tr>
  <tr><th scope="row"><code>dayz-audio-fx-specialist</code></th><td>Sound sets, sound shaders and particles.</td><td>Any lead</td></tr>
  <tr><th scope="row"><code>dayz-physics-specialist</code></th><td>Collisions, contact and thrown objects.</td><td>Any lead</td></tr>
  <tr><th scope="row"><code>dayz-ai-specialist</code></th><td>AI behavior patterns.</td><td>Script lead</td></tr>
 </tbody></table></div>

 <h3 id="g-spec-detail">Each specialist in detail</h3>
 <div class="tbl spc"><table><thead><tr><th scope="col" colspan="2"><code>dayz-persistence-specialist</code></th></tr></thead><tbody>
  <tr><th scope="row">What it does</th><td>Makes modded items and systems keep their data across server restarts. It writes the save and load code (OnStoreSave and OnStoreLoad), stamps every save with a version number, and writes the upgrade path so old saves still load after the mod changes. It covers base building parts that must survive restarts, and before release it runs a data audit that checks every saved field is written and read back in the same order.</td></tr>
  <tr><th scope="row">Ask it for</th><td>"Make my safe keep its code and contents after a restart, and do not break saves from the last version."</td></tr>
  <tr><th scope="row">Works under</th><td>Script lead (the release audit goes to the server lead)</td></tr>
  <tr><th scope="row">Hands back</th><td>Save and load code with a version number, a migration note for old saves, and an audit report for the server lead.</td></tr>
 </tbody></table></div>
 <div class="tbl spc"><table><thead><tr><th scope="col" colspan="2"><code>dayz-vehicle-specialist</code></th></tr></thead><tbody>
  <tr><th scope="row">What it does</th><td>Builds cars, boats and helicopters. It sets up the vehicle class and its simulation (engine, gearbox, axles, wheels), the parts that attach to it (doors, hood, trunk, wheels, battery, spark plug), its fluids (fuel, oil, coolant, brake fluid), seats and crew positions, and how it takes damage. Vanilla DayZ ships native helicopter base classes (Helicopter, HelicopterAuto and HelicopterScript) but no flyable helicopter, so it builds flyable ones on those classes with the user's own code, never copied from another mod.</td></tr>
  <tr><th scope="row">Ask it for</th><td>"Add a four door pickup with its own doors and a bigger fuel tank."</td></tr>
  <tr><th scope="row">Works under</th><td>Config lead</td></tr>
  <tr><th scope="row">Hands back</th><td>CfgVehicles entries, the CarScript, BoatScript or HelicopterScript class, attachment slots, and a types.xml entry for the server lead.</td></tr>
 </tbody></table></div>
 <div class="tbl spc"><table><thead><tr><th scope="col" colspan="2"><code>dayz-weapon-specialist</code></th></tr></thead><tbody>
  <tr><th scope="row">What it does</th><td>Builds firearms and everything that goes with them: the weapon class, magazines, ammunition, attachment slots for optics, suppressors, stocks and handguards, recoil, fire modes and muzzle effects. It inherits from the closest vanilla weapon so reloading, jamming and damage behave like the base game.</td></tr>
  <tr><th scope="row">Ask it for</th><td>"Add a scoped hunting rifle that takes a five round magazine and the vanilla long range optics."</td></tr>
  <tr><th scope="row">Works under</th><td>Config lead</td></tr>
  <tr><th scope="row">Hands back</th><td>CfgWeapons, CfgMagazines and CfgAmmo entries, a recoil class, and a list of the model selections the art lead must provide.</td></tr>
 </tbody></table></div>
 <div class="tbl spc"><table><thead><tr><th scope="col" colspan="2"><code>dayz-wearables-specialist</code></th></tr></thead><tbody>
  <tr><th scope="row">What it does</th><td>Builds clothing, gear and characters: which inventory slot an item uses, how many slots it holds, its protection and insulation, the hidden selections that let one model carry several textures, and how it shows on the character through proxies. It covers new survivor characters too.</td></tr>
  <tr><th scope="row">Ask it for</th><td>"Make a plate carrier with three colors that fits the vest slot and holds six items."</td></tr>
  <tr><th scope="row">Works under</th><td>Art lead</td></tr>
  <tr><th scope="row">Hands back</th><td>Config entries, hidden selection names, texture slots for each color, and proxy notes for the Object Builder specialist.</td></tr>
 </tbody></table></div>
 <div class="tbl spc"><table><thead><tr><th scope="col" colspan="2"><code>dayz-animation-specialist</code></th></tr></thead><tbody>
  <tr><th scope="row">What it does</th><td>Makes things move: doors, lids, hatches, triggers and moving parts. It writes the skeletonBones for the moving parts and the class Animations block in model.cfg (rotations, movements and hiding parts), while the Object Builder specialist keeps the rest of model.cfg. It handles .rtm animation files, and writes the handoff for models built in Blender so bones and selections line up when they reach Object Builder.</td></tr>
  <tr><th scope="row">Ask it for</th><td>"Make the doors on my bunker open and close when a player uses them."</td></tr>
  <tr><th scope="row">Works under</th><td>Art lead</td></tr>
  <tr><th scope="row">Hands back</th><td>The skeletonBones and class Animations entries for model.cfg, the selection and bone names the model needs, and the script hook that plays the animation, for the script specialist to write.</td></tr>
 </tbody></table></div>
 <div class="tbl spc"><table><thead><tr><th scope="col" colspan="2"><code>dayz-audio-fx-specialist</code></th></tr></thead><tbody>
  <tr><th scope="row">What it does</th><td>Handles sound and visual effects: sound shaders and sound sets, how far a sound carries and how loud it is, and particle effects such as smoke, sparks and muzzle flashes. It builds on the /dayz-particles skill for particle files.</td></tr>
  <tr><th scope="row">Ask it for</th><td>"Give my generator a running sound that fades with distance and a puff of exhaust smoke."</td></tr>
  <tr><th scope="row">Works under</th><td>Any lead that needs it</td></tr>
  <tr><th scope="row">Hands back</th><td>CfgSoundShaders and CfgSoundSets entries, particle files, and the script lines that play them.</td></tr>
 </tbody></table></div>
 <div class="tbl spc"><table><thead><tr><th scope="col" colspan="2"><code>dayz-physics-specialist</code></th></tr></thead><tbody>
  <tr><th scope="row">What it does</th><td>Makes objects behave physically: their weight, collision shapes in the Geometry and Fire Geometry LODs, how they land when dropped or thrown, and how they push against players and vehicles. It catches the common faults, such as items falling through floors or bullets passing through walls.</td></tr>
  <tr><th scope="row">Ask it for</th><td>"My crate falls through the floor when I drop it. Fix it."</td></tr>
  <tr><th scope="row">Works under</th><td>Any lead that needs it</td></tr>
  <tr><th scope="row">Hands back</th><td>Geometry and mass fixes for the Object Builder specialist and any config changes for the config lead.</td></tr>
 </tbody></table></div>
 <div class="tbl spc"><table><thead><tr><th scope="col" colspan="2"><code>dayz-ai-specialist</code></th></tr></thead><tbody>
  <tr><th scope="row">What it does</th><td>Builds behavior for computer controlled characters: infected, animals and human AI such as patrols and guards. It learns the patterns other modders use by studying how they work, then writes the user's own version. Nothing is copied from another mod.</td></tr>
  <tr><th scope="row">Ask it for</th><td>"Add a patrol of guards that walk a route around my military base and react to gunfire."</td></tr>
  <tr><th scope="row">Works under</th><td>Script lead</td></tr>
  <tr><th scope="row">Hands back</th><td>Script classes for the behavior, the config the server lead needs to spawn them, and notes on server performance.</td></tr>
 </tbody></table></div>
 <h3>How every specialist's knowledge is checked</h3>
 %s
 <p class="example">The existing specialists go deeper too: a full Enforce Script reference, Dabs and widget UI coverage, a texture and material cookbook, model and LOD rules, animated doors, a short spec step in <code>/dayz-init</code> before building, and a layout preview at several screen sizes.</p>
</section>
""" % (grow_chart, cycle_chart)

spec_flows = """<section aria-labelledby="g-spec-flows">
 <h2 id="g-spec-flows">Specialist workflows</h2>
 <p>Every task goes through the same team loop: the user approves the plan, the orchestrator hands tasks to the leads, the leads hand them to specialists, and the gates check the work. Inside that loop each specialist works through its own steps. The specialists that write DayZ content look up vanilla first: they Grep for a class or symbol name they know, use RAG search for questions by meaning or after two or three failed greps, and read the real file before relying on a hit. The build engineer, docs writer, build checker, in-game tester and Figma cleaner have no RAG tool; they work from the mod, its logs or the Figma file.</p>
 <div class="tbl"><table>
  <thead><tr><th scope="col">Specialist</th><th scope="col">Its steps inside the loop</th></tr></thead>
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
 <h2 id="g-addons">Add-ons</h2>
 <p>The core runs on DayZ Tools, the vanilla game files, Python and Claude Code. A few parts need more: RAG search needs a Voyage AI key, the Figma pipeline needs a Figma MCP server, <code>/dayz-p3d-audit</code> needs py3d, <code>/dayz-build-imageset</code>, <code>/dayz-layout-preview</code> and <code>/dayz-gate visual</code> need Pillow, and <code>/dayz-cot-bootstrap</code> needs the CF and COT mods.</p>
 <p>An optional <code>agentic-z-addons</code> plugin for other tools, such as Blender, an AI 3D generator or another MCP server, is planned. No add-on ships yet, and the plugin marketplace lists only <code>agentic-z</code> and <code>agentic-z-panel</code>. Each add-on will be a workflow that connects the outside tool at one point in the loop, usually handing a finished model to the Object Builder specialist, so the normal gates can check it like any other work. The rules it would follow:</p>
 <ul>
  <li><b>Optional:</b> the core will never load an add-on unless the user installs it.</li>
  <li><b>Same gates:</b> anything an add-on produces will go through the mod review, the build check and the in-game test.</li>
  <li><b>No reverse engineering:</b> no add-on will unpack protected mods or turn binarized models back into editable ones.</li>
 </ul>
</section>
"""

def grab(html, sid):
    s = html.index('<section aria-labelledby="%s">' % sid)
    return html[s:html.index('</section>', s) + len('</section>')]
quality = ''.join(grab(team_html, sid) for sid in ('h-method', 'h-grades', 'h-grade-detail', 'h-bugs'))
quality = quality

workflows = """<section aria-labelledby="g-workflows">
 <h2 id="g-workflows">Workflows</h2>
 <p>Ready-made jobs for the things modders do every week. Each runs as a script where it can, and asks the AI only for judgment.</p>
 <h3>Paste it in</h3>
 <div class="tbl"><table><thead><tr><th scope="col">Paste</th><th scope="col">What happens</th></tr></thead><tbody>
  <tr><th scope="row">A crash log or RPT</th><td>Triage matches it against known errors, names the cause and the fix, and hands anything new to the debugger.</td></tr>
  <tr><th scope="row">A screenshot of a bug</th><td>The paste hook suggests a specialist: a UI problem to the UI specialist, a texture or material problem to the asset specialist, an error message or wrong behavior to the script specialist. The router agent sends an error message on screen to the mod debugger (or to gate triage) instead, so the two can disagree on that case.</td></tr>
  <tr><th scope="row">A Figma link</th><td>Runs the Figma pipeline and returns a checked <code>.layout</code>.</td></tr>
  <tr><th scope="row">A GitHub link</th><td>Points at <code>/dayz-import-mod --source &lt;link&gt;</code>, which imports the mod into <code>workspace\\</code> and can fill in the missing standard pieces.</td></tr>
  <tr><th scope="row">A Steam Workshop link</th><td>Refused with the reason: Workshop content is packed, binarized and often protected.</td></tr>
  <tr><th scope="row">A types.xml chunk</th><td>Checks the entries and points at <code>/dayz-edit-types --merge</code> to merge them, with any problems listed.</td></tr>
 </tbody></table></div>
 <h3>Commands</h3>
 <div class="tbl"><table><thead><tr><th scope="col">Command</th><th scope="col">What it does</th></tr></thead><tbody>
  <tr><th scope="row"><code>/dayz-recipe</code></th><td>Starts a mod from a template ("new weapon", "new vest", "new craftable") that pre-fills the plan.</td></tr>
  <tr><th scope="row"><code>/dayz-gate behavior</code></th><td>Runs a test mission that spawns and uses each new item and reports PASS or FAIL per feature.</td></tr>
  <tr><th scope="row"><code>/dayz-logwatch</code></th><td>Watches the logs during a test session and flags script errors the moment they appear.</td></tr>
  <tr><th scope="row"><code>/dayz-gate visual</code></th><td>Takes screenshots during the in-game test and compares them with stored baselines.</td></tr>
  <tr><th scope="row"><code>/dayz-release-pack</code></th><td>Writes the Workshop description, changelog, classname list and server-owner install notes.</td></tr>
  <tr><th scope="row"><code>/dayz-server-kit</code></th><td>Zips types.xml entries, cfgeconomycore lines, the load order and the public <code>.bikey</code> for server owners. It never packs a <code>.biprivatekey</code>.</td></tr>
  <tr><th scope="row"><code>/dayz-upgrade-guard</code></th><td>Snapshots vanilla before a DayZ update, then lists the mod classes whose vanilla parents changed, and can rebuild the search index.</td></tr>
  <tr><th scope="row"><code>/dayz-conflict-check</code></th><td>Finds collisions with CF, COT and Expansion without extracting them. For packed mods (the usual Workshop install) it reads only the PBO headers, so it compares prefixes, paths and script file names; config and script classes are compared only for unpacked mods. <code>--ingame</code> loads them together in a test session, which is how class clashes with packed mods show up.</td></tr>
  <tr><th scope="row"><code>/dayz-balance</code></th><td>Compares your items' stats with similar vanilla items and flags outliers.</td></tr>
  <tr><th scope="row"><code>/dayz-health</code></th><td>A page per mod with the last build, last test, open findings and the history of every gate run.</td></tr>
  <tr><th scope="row"><code>/dayz-ask</code></th><td>Answers a plain-English question about vanilla DayZ with <code>path:line</code> citations.</td></tr>
 </tbody></table></div>
 <p class="example">Answer tests (evals) check 23 of the 30 agents, and a change may only keep or raise a score. Prompt caching is left to Claude Code, which does it on its own; Agentic-Z has no rule or test of its own for it. The behavior and visual gates are tested with fixtures only; they have not run in a live DayZ session yet.</p>
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
('<code>dayz-mod-reviewer</code>', 'Audits a mod before you build, PASS or FAIL.', '"Review workspace/MyVest before I build."'),
('<code>figma-node-normalizer</code>, <code>figma-to-dayz-layout</code>, <code>dayz-layout-validator</code>', 'Optional: turn a Figma frame into a .layout; the validator checks it without editing.', '"Turn this Figma frame into a DayZ menu."'),
('<code>dayz-orchestrator</code> and team', 'Plans a whole mod, runs leads, workers and checks.', 'Plugin: <code>claude --agent agentic-z:dayz-orchestrator</code>. Clone: <code>claude --agent dayz-orchestrator</code>.'),
('<code>dayz-mod-architect</code>', 'Plans a mod: classes, files, assets and a task list.', 'Started by the orchestrator.'),
('<code>dayz-lead</code>', 'Runs one team (script, config, art, UI, server, release) and its review checks.', 'Started by the orchestrator.'),
('<code>dayz-build-checker</code>, <code>dayz-ingame-tester</code>', 'Backup checks used when <code>/dayz-gate</code> itself fails.', 'Started by the orchestrator.'),
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
('<code>dayz-router</code>', 'Cheap Haiku agent that decides who handles a request.', 'Used by <code>/dayz-route</code>.'),
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
('Does it cost money?', 'Agentic-Z itself is free to use for DayZ mods (see LICENSE). You need your own AI tool (Claude Code for everything, or Codex CLI or Gemini CLI for the skills and rules). RAG search needs a Voyage AI key; the last full index build embedded about 66M tokens, and the current indexer makes more chunks, so check Voyage pricing. <code>/dayz-search-download</code> skips the build with a prebuilt index, but that index is older than the current indexer, and searching still needs the key to embed your questions.'),
('Which AI tools work?', 'Claude Code gets everything. Codex CLI and Gemini CLI get the skills (<code>/sync-skills</code> links them into all three) and the rules files (<code>AGENTS.md</code> and <code>GEMINI.md</code>). The agents, the hooks and RAG search are Claude Code features.'),
('Plugin or clone?', 'Plugin to add it to an existing project (skills show as <code>/agentic-z:...</code>). Clone to start a new mod project. Not both at once, or every skill loads twice.'),
('Will it touch my other mods?', 'Skills never write to your other mods. Besides your mod, its P: link, its test server and its build folder, they write only their own state: <code>.claude\\local-memory\\</code>, <code>.claude\\settings.local.json</code>, the search index in <code>~\\.claude\\dayz-search-index\\</code>, the <code>P:\\Mods</code> link, Object Builder settings in the registry, the skill links from <code>/sync-skills</code>, rule files after your yes in <code>/dayz-record-correction</code>, vanilla snapshots in <code>~\\.claude\\dayz-upgrade-guard\\</code> (about 10 MB each), the behavior gate copy of your test server in <code>.server\\&lt;instance&gt;-behavior\\</code>, gate results and the health page in <code>.server\\!Health\\&lt;ModName&gt;\\</code>, and in <code>output\\</code> the plans, the visual gate screenshots, the layout preview images in <code>output\\layout-preview\\</code>, the answer test results in <code>output\\evals\\</code>, and the release texts and server kit zip in <code>output\\&lt;ModName&gt;-release\\</code>. <code>/agentic-z-update</code> also checks updated template files out into your clone, commits them, and writes <code>.claude\\.upstream-baseline</code> and <code>.claude\\.upstream-update.lock</code>. <code>/dayz-scope-mod &lt;ModName&gt;</code> blocks edits to every other mod in <code>workspace\\</code>.'),
('Does it publish to the Workshop?', 'No. Builds land in <code>P:\\Mods\\@&lt;ModName&gt;</code>, which the launcher loads. You publish with DayZ Tools Publisher.'),
('Can I work on several mods?', 'Yes. Each mod lives in <code>workspace\\&lt;ModName&gt;</code>. Pick "Set up or switch to another mod" in the <code>/dayz-init</code> hub.'),
('Where are the logs?', 'Server: <code>.server\\&lt;instance&gt;\\Profiles\\</code>. Client: <code>.server\\!ClientDiagLogs\\</code>.'),
('Does P: stay mounted?', 'No, it does not survive a reboot. Run <code>/dayz-workdrive</code> after booting.'),
('Do I need the DayZ Server?', 'Yes, installed, whenever you add a test server instance or refresh its mission: <code>/dayz-add-server</code> copies the mission template from the DayZ Server install each time it creates an instance, and again for <code>--refresh-mission</code>.'),
('How do I update?', 'Plugin: through the Claude Code plugin marketplace. Clone: <code>/agentic-z-update</code>.'),
('Is it safe to run?', 'In a clone, the shipped settings allow the repo\'s own skills and scripts and deny <code>python -c</code>, <code>python -m</code>, <code>node -e</code>, <code>node -p</code>, <code>npx</code>, and <code>npm install</code> or <code>npm i</code> with a package name. Plain <code>npm install</code> and <code>npm ci</code> are allowed. Other inline forms such as <code>py -c</code> are not on the allow list either, so they ask you first. A plugin install does not get these settings, because plugins cannot ship permissions. The mod reviewer, layout validator, build checker, in-game tester and debugger have no Edit or Write tools (four of them can run Bash for their checks).'),
('Can I teach it my style?', 'Yes. Correct it once and run <code>/dayz-record-correction</code>; the rule is saved after your yes.'),
]

doc = '''<title>Agentic-Z Guide</title>
<meta name="claude:viewport-fit-sides" content="cover">
%s%s
<div class="wrap">
<header>
 <h1>Agentic-Z Guide</h1>
 <p class="lede">Everything you need to install, set up and use Agentic-Z, the AI agent stack for DayZ modding. This edition covers version 2.0.0: 30 agents, 44 skills, three hooks and a side panel. Read it top to bottom once and you will not need to ask.</p>
</header>

<section aria-labelledby="g-what">
 <h2 id="g-what">What Agentic-Z is</h2>
 <p>Agentic-Z turns Claude Code into a DayZ modding partner. It brings DayZ specialist agents, slash commands that drive DayZ Tools for you, house rules for clean mods, and a search over the vanilla game files so the AI looks things up instead of guessing. Codex CLI and Gemini CLI get the skills and the rules files; the agents, hooks and RAG search are Claude Code features.</p>
 <div class="specs">
  <div class="sg"><h3>Specialists</h3><ul><li>Scripts, configs, UI</li><li>Models and textures</li><li>Maps and server</li><li>Saving data and AI</li><li>Vehicles and weapons</li><li>Wearables and animation</li><li>Audio, FX and physics</li><li>Review and debugging</li></ul></div>
  <div class="sg"><h3>Skills</h3><ul><li>Setup wizard</li><li>Lint and build PBO</li><li>Launch test and gates</li><li>types.xml</li><li>Textures and layouts</li><li>Release pack</li></ul></div>
  <div class="sg"><h3>RAG search</h3><ul><li>Vanilla scripts</li><li>Configs</li><li>Layouts</li><li>Materials</li></ul></div>
  <div class="sg"><h3>Works with</h3><ul><li>Claude Code: everything</li><li>Codex CLI: skills and rules</li><li>Gemini CLI: skills and rules</li></ul></div>
 </div>
</section>

<section aria-labelledby="g-fit">
 <h2 id="g-fit">How it fits together</h2>
 <p>You talk to your AI tool. Agentic-Z gives it rules, agents, skills and a search server, and those drive your mod folder, the P: drive, DayZ Tools and the game.</p>
 %s
</section>

<section aria-labelledby="g-req">
 <h2 id="g-req">What you need</h2>
 %s
 <p class="example">RAG search is optional. To use it, install its Python packages with <code>pip install -r .claude\\mcp\\dayz-rag\\requirements.txt</code> (and <code>.claude\\skills\\dayz-search-index\\requirements.txt</code> to build the index), then add <code>VOYAGE_API_KEY=pa-...</code> to <code>.env</code> at the repo root.</p>
</section>

<section aria-labelledby="g-setup">
 <h2 id="g-setup">Install and first setup</h2>
 %s
 <h3>Option A: clone as a template (new mod project)</h3>
 <pre><code>git clone https://github.com/DayZ-n-Chill/Agentic-Z.git my-dayz-mod
cd my-dayz-mod
python .claude\\skills\\sync-skills\\sync.py</code></pre>
 <h3>Option B: install as a Claude Code plugin (existing project)</h3>
 <pre><code>/plugin marketplace add DayZ-n-Chill/Agentic-Z
/plugin install agentic-z@dayz-n-chill</code></pre>
 <p>Plugin skills show with an <code>agentic-z:</code> prefix, for example <code>/agentic-z:dayz-build-pbo</code>. Pick one option only.</p>
 <h3>Then run the wizard</h3>
 <pre><code>/dayz-init</code></pre>
 <p>It asks if you are starting a new mod or importing one, the mod name, which map to test on, and whether to build and launch. It fixes what it can (mounting P:, the <code>P:\\Mods</code> link) and tells you how to fix the rest. Every run after that shows a status hub for your active mod.</p>
</section>

<section aria-labelledby="g-loop">
 <h2 id="g-loop">Your daily loop</h2>
 %s
 <ol class="steps">
  <li><span>Ask an agent for the change, for example "add a hidden selection for the camo".</span></li>
  <li><span><code>/dayz-build-pbo &lt;ModName&gt;</code> packs the mod into <code>P:\\Mods\\@&lt;ModName&gt;\\Addons\\</code>.</span></li>
  <li><span><code>/dayz-launch-test &lt;ModName&gt; --server &lt;instance&gt;</code> starts a diag server and client with your mod.</span></li>
  <li><span>Check the logs, or hand them to <code>dayz-mod-debugger</code>.</span></li>
  <li><span><code>/dayz-stop-test</code> closes DayZ. Fix and repeat.</span></li>
 </ol>
</section>

<section aria-labelledby="g-agents">
 <h2 id="g-agents">Working with the agents</h2>
 <p>Just describe what you want; Claude picks the right specialist. You can also name one, for example "use the dayz-config-specialist to...".</p>
 %s
</section>

%s
<section aria-labelledby="g-wave">
 <h2 id="g-wave">How the team checks work</h2>
 <p>Start the team with <code>claude --agent agentic-z:dayz-orchestrator</code> after a plugin install, or <code>claude --agent dayz-orchestrator</code> in a clone. It plans the mod with you, waits for your yes, then runs waves of work. Each wave goes through the build check, the in-game test and, when <code>output\\&lt;ModName&gt;-plan\\behavior-checks.json</code> exists, the behavior test, a scripted mission that spawns and uses each new item. Nothing reaches you until it builds, loads in game with clean logs and, when the plan lists behavior checks, passes the behavior test.</p>
 %s
</section>

<section aria-labelledby="g-rag">
 <h2 id="g-rag">RAG search</h2>
 %s
 %s
 <p>Agents Grep first when they know an exact class or symbol name, and use RAG search for questions by meaning. A search hit is only a hint until the agent opens the real file, so answers come with <code>path:line</code> references you can check.</p>
</section>

<section aria-labelledby="g-tiers">
 <h2 id="g-tiers">The three tiers of rules</h2>
 %s
</section>

%s
%s
%s

<section aria-labelledby="g-layout">
 <h2 id="g-layout">Where everything lives</h2>
 <p>Your files and the main places the skills write to. The repo's own tool folders are left out.</p>
 <pre><code>&lt;repo&gt;\\
  workspace\\&lt;ModName&gt;\\           your mod source
  .server\\&lt;instance&gt;\\            local test server (mission, serverDZ.cfg, Profiles)
  .server\\&lt;instance&gt;-behavior\\   copy of the instance the behavior gate runs in
  .server\\!ClientDiagLogs\\       client logs
  .server\\!Health\\&lt;ModName&gt;\\     stored gate results for /dayz-health
  .claude\\local-memory\\          your author handle, active project, wizard state
  output\\&lt;ModName&gt;-plan\\         the plan, behavior checks and the visual shots list
  output\\&lt;ModName&gt;-visual\\       screenshots per run, and the baselines to keep
  output\\&lt;ModName&gt;-release\\      release pack and server kit
  output\\                        other one-off deliverables
~\\.claude\\dayz-search-index\\     RAG search index
~\\.claude\\dayz-upgrade-guard\\    vanilla snapshots for /dayz-upgrade-guard
P:\\
  &lt;ModName&gt;\\                     link to workspace\\&lt;ModName&gt;
  Mods\\@&lt;ModName&gt;\\Addons\\        built PBO (Mods links to DayZ\\!Workshop)
  dz\\                            vanilla data you extracted once
  scripts\\                       vanilla scripts, also read by the skills</code></pre>
</section>

<section aria-labelledby="g-env">
 <h2 id="g-env">Settings you might need</h2>
 %s
</section>

<section aria-labelledby="g-safe">
 <h2 id="g-safe">Safety</h2>
 <ul>
  <li>In a clone, the shipped <code>.claude/settings.json</code> allows the repo's own skills and scripts (plus <code>npm install</code> and <code>npm ci</code> from the lockfile), and blocks <code>python -c</code>, <code>python -m</code>, <code>node -e</code>, adding new npm packages and <code>npx</code>. A plugin install does not get this file, because plugins cannot ship permissions.</li>
  <li>Every agent has an explicit tool list. The five gates (mod reviewer, layout validator, build checker, in-game tester and debugger) have no Edit or Write tools; four of them have Bash to run their checks, and only the debugger has no Bash. Two agents have general web or remote design access: <code>agent-creator</code> has WebFetch, and <code>figma-node-normalizer</code> uses the remote Figma MCP tools. The 21 agents that use RAG search also send text off the machine: <code>search_dayz_source</code> embeds the query through the hosted Voyage AI API.</li>
  <li><code>/dayz-scope-mod &lt;ModName&gt;</code> blocks edits to every other mod in <code>workspace\\</code> (start Claude Code from the project root); <code>--clear</code> lifts it.</li>
  <li>Cleanup only removes what the toolkit made, and destructive steps ask first or need <code>--yes</code>.</li>
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
 <h2 id="g-help">Getting help and contributing</h2>
 <p>Discord: <code>discord.gg/dayznchill</code>. Repo: <code>github.com/DayZ-n-Chill/Agentic-Z</code>. To contribute, branch from <code>develop</code> (named <code>feature/</code>, <code>fix/</code> or <code>docs/</code>), and open the pull request against <code>develop</code>.</p>
</section>
<p class="foot">Agentic-Z by DayZ n' Chill.</p>
</div>
''' % (
    fonts, style + '<style>pre{background:var(--band);border:1px solid var(--rule);border-radius:10px;padding:12px 14px;overflow-x:auto;font-family:var(--mono);font-size:13px;line-height:1.5;margin:0}h3{margin-top:6px}tbody th{white-space:normal;width:30%}.wrap ul{margin:0;padding-left:20px;display:grid;gap:6px}</style>',
    arch,
    table(['What', 'Why'], [
        ('Windows', 'DayZ Tools and the P: drive are Windows only.'),
        ('DayZ (Steam)', 'The diag client ships next to the game and runs your tests.'),
        ('DayZ Tools (Steam, free)', 'AddonBuilder, P: drive mounting, ImageToPAA.'),
        ('DayZ Server (Steam)', 'Only to copy the mission template once.'),
        ('P: mounted, vanilla data extracted', 'Configs inherit from vanilla classes on P:.'),
        ('Python 3.10+ on PATH', 'The skills are Python scripts.'),
        ('Claude Code (or Codex CLI or Gemini CLI)', 'Your AI tool. Codex CLI and Gemini CLI get the skills and rules files only.'),
    ]),
    setup, daily,
    table(['Agent', 'What it does', 'Ask it'], agents),
    chart.replace('<section aria-labelledby="h-chart">', '<section aria-labelledby="h-chart">'),
    wave,
    rag,
    table(['Tool', 'What it does'], [
        ('<code>search_dayz_source</code>', 'Search vanilla scripts, configs, layouts and materials by meaning.'),
        ('<code>get_dayz_file</code>', 'Open an exact file and line range on P:.'),
        ('<code>list_indexed_sources</code>', 'Show what is indexed and when.'),
    ]),
    tiers,
    savers + coming + spec_flows + workflows + addons + quality, skills, packs,
    table(['Variable', 'Points to'], [
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
