import pathlib, re
p = pathlib.Path(__file__).parent / 'make_guide.py'
t = p.read_text(encoding='utf-8')

def rep(old, new, count=1):
    global t
    assert old in t, old[:80]
    t = t.replace(old, new) if count == 0 else t.replace(old, new, count)

rep("'id=\"h-chart\">The mod team (next release)'", "'id=\"h-chart\">The mod team'")
rep("Checks, routing and status (next release)", "Checks, routing and status")
rep("'Bohemia wiki', 'on hold next release'", "'Bohemia wiki', 'DayZ pages'")
rep('<h2 id="g-savers">Token savers (next release)</h2>', '<h2 id="g-savers">Token savers</h2>')
rep('(index on hold in the next release)', '')
rep(" (next release). It plans the mod", ". It plans the mod")
rep("<p class=\"foot\">Agentic-Z by DayZ n' Chill. Items marked \"next release\" are in review and not in version 1.6.0 yet.</p>", "<p class=\"foot\">Agentic-Z by DayZ n' Chill.</p>")
t = t.replace(' (next release)', '')

# specialists section: present as part of the product
rep('<h2 id="g-coming">Coming next: new specialists</h2>', '<h2 id="g-coming">Specialists for every part of a mod</h2>')
rep("<p>Eight new specialists are planned. They join the existing team leads as workers, so the way you work does not change. Each one brings its own reference pack, checked against the vanilla game files, and loaded only when a task needs it. A new <code>/dayz-lint</code> check will run inside the build check to catch errors that stop a mod from loading.</p>",
    "<p>Beyond scripts, configs, art, UI, maps and servers, Agentic-Z has specialists for saving data, vehicles, weapons, wearables, animation, audio, physics and AI. Each works under a team lead and brings its own reference pack, checked against the vanilla game files and loaded only when a task needs it. <code>/dayz-lint</code> runs inside the build check and stops a mod that would fail to load before it is packed.</p>")
rep(' <h3>How each one is built</h3>', ' <h3>How every specialist\'s knowledge is checked</h3>')
rep("<p class=\"example\">Also planned: a deeper script reference, more UI coverage, a texture and material cookbook, model and LOD rules, animated doors, a short spec step in <code>/dayz-init</code>, and a layout preview at several screen sizes.</p>",
    "<p class=\"example\">The existing specialists go deeper too: a full Enforce Script reference, Dabs and widget UI coverage, a texture and material cookbook, model and LOD rules, animated doors, a short spec step in <code>/dayz-init</code> before building, and a layout preview at several screen sizes.</p>")
# strip NEW tags from the copied diagrams
rep("grow_chart = grow_chart[:grow_chart.index('</svg></div>') + len('</svg></div>')]",
    "grow_chart = grow_chart[:grow_chart.index('</svg></div>') + len('</svg></div>')]\n"
    "grow_chart = re.sub(r'<rect class=\"tag\"[^>]*/><text class=\"tag-t\"[^>]*>NEW</text>', '', grow_chart).replace(' (NEW)', '').replace('/dayz-lint (NEW)', '/dayz-lint')")
if not t.startswith('import pathlib, re'):
    t = t.replace('import pathlib', 'import pathlib, re', 1) if t.startswith('import pathlib\n') else 'import re\n' + t

# skills: lint + workflow commands
rep("""   <tr><th scope="row"><code>/dayz-panel</code></th><td>Opens the agentic-z-panel buttons (separate plugin).</td></tr>""",
"""   <tr><th scope="row"><code>/dayz-panel</code></th><td>Opens the agentic-z-panel buttons (separate plugin).</td></tr>
   <tr><th scope="row"><code>/dayz-lint</code></th><td>Finds errors that would stop a mod from loading, before packing. Runs inside the build check.</td></tr>""")

# workflows section
wf = '''
workflows = """<section aria-labelledby="g-workflows">
 <h2 id="g-workflows">Workflows</h2>
 <p>Ready-made jobs for the things modders do every week. Each runs as a script where it can, and asks the AI only for judgment.</p>
 <h3>Paste it in</h3>
 <div class="tbl"><table><thead><tr><th scope="col">Paste</th><th scope="col">What happens</th></tr></thead><tbody>
  <tr><th scope="row">A crash log or RPT</th><td>Triage matches it against known errors, names the cause and the fix, and hands anything new to the debugger.</td></tr>
  <tr><th scope="row">A screenshot of a bug</th><td>Finds the widget, texture or class on screen and routes it to the right specialist.</td></tr>
  <tr><th scope="row">A Figma link</th><td>Runs the Figma pipeline and returns a checked <code>.layout</code>.</td></tr>
  <tr><th scope="row">A Workshop or GitHub link</th><td>Imports the mod into <code>workspace\\\\</code> and fills in the missing standard pieces.</td></tr>
  <tr><th scope="row">A types.xml chunk</th><td>Checks the entries and merges them into the server economy.</td></tr>
 </tbody></table></div>
 <h3>Commands</h3>
 <div class="tbl"><table><thead><tr><th scope="col">Command</th><th scope="col">What it does</th></tr></thead><tbody>
  <tr><th scope="row"><code>/dayz-recipe</code></th><td>Starts a mod from a template ("new weapon", "new vest", "new craftable") that pre-fills the plan.</td></tr>
  <tr><th scope="row"><code>/dayz-gate behavior</code></th><td>Runs a test mission that spawns and uses each new item and reports PASS or FAIL per feature.</td></tr>
  <tr><th scope="row"><code>/dayz-logwatch</code></th><td>Watches the logs during a test session and flags script errors the moment they appear.</td></tr>
  <tr><th scope="row"><code>/dayz-gate visual</code></th><td>Takes screenshots during the in-game test and compares them with the expected look.</td></tr>
  <tr><th scope="row"><code>/dayz-release-pack</code></th><td>Writes the Workshop description, changelog, classname list and server-owner install notes.</td></tr>
  <tr><th scope="row"><code>/dayz-server-kit</code></th><td>Zips types.xml entries, cfgeconomycore lines, load order and keys for server owners.</td></tr>
  <tr><th scope="row"><code>/dayz-upgrade-guard</code></th><td>After a DayZ update, re-indexes the game files and flags mod classes whose vanilla parents changed.</td></tr>
  <tr><th scope="row"><code>/dayz-conflict-check</code></th><td>Loads your mod with CF, COT and Expansion and reports class and path collisions.</td></tr>
  <tr><th scope="row"><code>/dayz-balance</code></th><td>Compares your items' stats with similar vanilla items and flags outliers.</td></tr>
  <tr><th scope="row"><code>/dayz-health</code></th><td>A page per mod with the last build, last test, open review findings and test history.</td></tr>
  <tr><th scope="row"><code>/dayz-ask</code></th><td>Answers a plain-English question about vanilla DayZ with <code>path:line</code> citations.</td></tr>
 </tbody></table></div>
 <p class="example">Answer tests (evals) check each agent's answers so a change can only make them better. Prompt caching and a cache of repeated search answers keep every session cheaper.</p>
</section>
"""
'''
anchor = "\ndef table(head, rows):"
t = t.replace(anchor, wf + anchor, 1)
rep('    savers + coming + quality, skills, packs,', '    savers + coming + workflows + quality, skills, packs,')
p.write_text(t, encoding='utf-8')
print('ok')
