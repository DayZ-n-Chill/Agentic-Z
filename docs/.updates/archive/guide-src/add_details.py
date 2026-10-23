import pathlib, html
p = pathlib.Path(__file__).parent / 'agentic-z-team.html'
t = p.read_text(encoding='utf-8')
E = html.escape

# (item, latest independent grade, why that grade, what was done after)
details = [
('Agents', [
('agent-creator','A+','Rules match the current subagent spec, including memory, maxTurns, color, nested agents and the two-name search tool rule.','Nothing left.'),
('dayz-asset-specialist','A','It could rename the user\'s source images, which the texture skill says only the user should do.','Never renames; reports a wrong or missing suffix to the art lead with a suggestion. The texture skill now accepts the full vanilla suffix set.'),
('dayz-build-checker','A','A payload-only bundle (no config.cpp) would fail the build gate every wave.','Bundles without config.cpp are checked with /dayz-deploy-pbo instead; it also stops a running session before building.'),
('dayz-build-engineer','A-','It launched without the mod\'s dependency mods and could not set up an instance whose name is not a map name.','Launches dependencies first (from requiredAddons or the brief) and passes --map for custom instance names.'),
('dayz-config-specialist','A+','Inheritance, CfgPatches and path rules are correct and specific.','Nothing left.'),
('dayz-docs-writer','A','After a types split, it looked for sample entries in a file that is now empty.','Also searches every file listed in cfgeconomycore.xml.'),
('dayz-ingame-tester','A','It launched without dependency mods, which gives false failures.','Launches dependencies first; a missing dependency PBO is a FAIL.'),
('dayz-layout-validator','A-','It failed layouts with empty spacer widgets, which vanilla uses on purpose.','Empty spacers are allowed (at most a note).'),
('dayz-lead','A+','Team table, gates, fix loop and report all match the orchestrator.','Nothing left.'),
('dayz-map-specialist','A+','Every path it cites exists on the P drive.','Nothing left.'),
('dayz-mod-architect','A+','Plans without building and reports to the orchestrator with citations.','Nothing left.'),
('dayz-mod-debugger','A+','Log locations and known error codes match Tier 2 and the gates that call it.','Nothing left.'),
('dayz-mod-reviewer','A-','It failed the common retexture pattern, where a child class inherits hiddenSelections from its parent.','Resolves inherited selections from the parent class before comparing.'),
('dayz-object-builder','A-','It said autocenter is never set in config.cpp, but placed objects need it there too.','Follows the audit references: placed objects get autocenter on the LOD and in config.cpp; kits and handhelds never do.'),
('dayz-orchestrator','A','It ran /dayz-new-mod without an author handle, which fails on every first run.','Reads the cached handle or asks the user, then passes --author.'),
('dayz-script-specialist','A+','Layer, modded-class and server-check rules match the style guide.','Nothing left.'),
('dayz-server-admin','A+','Edit and split skill usage, folder rules and settings all match the skills.','Nothing left.'),
('dayz-ui-specialist','A+','Recolor guidance matches Tier 2 and Figma input goes back to the caller.','Nothing left.'),
('dayz-workbench-specialist','A+','Every cited Workbench source path exists, and it verifies APIs before writing.','Nothing left.'),
('figma-node-normalizer','A','It only knew the Figma plugin\'s tool names, so other Figma setups looked unavailable.','Lists each Figma tool under all three names it can load as.'),
('figma-to-dayz-layout','A+','Mapping, sizing and formatting follow the rules doc and vanilla layouts.','Nothing left.'),
]),
('Skills', [
('agentic-z-update','B+','On Windows line endings, every upstream change looked like a local edit.','Compares git object ids instead of raw bytes; tested with core.autocrlf on.'),
('clean-repo','A+','Dry runs first, one confirmation, honest exit codes, all tested.','Nothing left.'),
('dayz-add-scaffold','A-','It found the project only from the current folder, so running from a subfolder failed.','Uses the shared project lookup; tested from a subfolder.'),
('dayz-add-server','B+','.gitignore hid the server config the docs say is tracked, and bad instance names crashed.','.gitignore fixed and checked; Windows-illegal characters are refused.'),
('dayz-build-imageset','A-','An old atlas left from a previous run counted as success.','The atlas must be newer than the run; empty sets clear their old outputs.'),
('dayz-build-pbo','B','One failed first build blocked every later build.','Marks a deploy folder it creates before building; tested fail-then-rebuild.'),
('dayz-clean-workspace','A','A failed delete hid the real reason.','Prints the actual error.'),
('dayz-cot-bootstrap','A-','A crashed server or client waited out the full 10-minute timeout.','Stops as soon as either process exits and names where to look.'),
('dayz-deploy-pbo','A','A crafted mod name could point outside the mods folder.','Validates the name like /dayz-new-mod; tested with path traversal.'),
('dayz-edit-types','A-','It would edit the wrong XML file and only touched the first duplicate entry.','Refuses non-types files and duplicate target names.'),
('dayz-import-mod','A-','A skipped scaffold piece still reported success.','A skipped piece is a failure with its retry command.'),
('dayz-init','A-','It saved state nothing read, and an import could be planned in a way that always failed.','Saves only what is used; imports require --scaffold or --no-scaffold.'),
('dayz-launch-objectbuilder','A','It copied a registry check from another skill instead of reusing it.','Loads the check from the Object Builder setup skill.'),
('dayz-launch-test','B+','Its port wait duplicated a shared helper and leaked a socket, and a bad prefs file crashed it.','Uses the shared port check; bad prefs fall back with a warning; wait loop tested.'),
('dayz-launch-workbench','A+','Preflight first, flags and lookup match the docs, every failure tested.','Nothing left.'),
('dayz-new-mod','A','Junction errors and a failed project-file rewrite were hidden.','Shows the real error and warns when nothing was rewritten.'),
('dayz-p3d-audit','A-','Its rvmat stage reference did not match vanilla materials.','Stage table rebuilt from real vanilla rvmats; severity matches the script.'),
('dayz-pack-texture','B+','It refused valid vanilla suffixes such as _ca and _as.','Accepts every vanilla suffix ImageToPAA supports; tested.'),
('dayz-particles','A+','Every claim checked out against vanilla scripts.','Nothing left.'),
('dayz-preflight','A+','Resolvers, junction handling and output match the code; 24 tests.','Nothing left.'),
('dayz-record-correction','A-','Run from a linked skill, it edited the wrong project\'s rule files.','Resolves the real Agentic-Z folder through the link first.'),
('dayz-scope-mod','A+','Rule syntax matches Claude Code\'s docs; tracks only its own rules.','Nothing left.'),
('dayz-search-download','A','A dropped connection mid-download showed a traceback.','Network errors exit cleanly with the URL and reason; old index kept.'),
('dayz-search-index','A-','A bad API key crashed with a traceback and spent tokens were not logged.','Clean one-line failure; tokens spent are logged; tested.'),
('dayz-search-wiki-index','D','It gets past the wiki\'s Cloudflare bot check with a copied browser cookie, and has no tests.','On hold for Brian\'s decision.'),
('dayz-setup-objectbuilder','A','Its "factory reset" did not actually reset.','--force backs up, deletes the key, then re-imports defaults.'),
('dayz-split-types','A+','Backups, folder fix and verification all match the code.','Nothing left.'),
('dayz-stop-test','A+','Correct error mapping, tested with a stub.','Nothing left.'),
('dayz-workdrive','A+','Resolution order and fallbacks match the code; 27 tests.','Nothing left.'),
('docs-sync','A-','Its drift notice was invisible to users, because Stop-hook output goes to the debug log.','Reports drift through the visible systemMessage channel.'),
('sync-skills','A+','All link states and flags match the docs; 20 tests.','Nothing left.'),
]),
('Shared', [
('dayz-rag search server','A+','Read-only tools, clear errors, retries with a timeout, P drive guard; 54 tests.','Nothing left.'),
('DayZ rules file (Tier 2)','B','Its inventorySlot example was wrong for current vanilla, and its texture suffix list was too short.','Example rewritten from real vanilla classes; suffix list widened; references corrected.'),
('Shared skill helpers','A+','Every helper is used, documented and tested.','Nothing left.'),
]),
]

def pill(g):
    c = 'ok' if g == 'A+' else 'keep' if g.startswith('A') else 'warn' if g.startswith('B') else 'fix'
    return '<span class="pill %s">%s</span>' % (c, g)

rows = []
for group, items in details:
    rows.append('<tr class="grp"><th colspan="4" scope="colgroup">%s</th></tr>' % group)
    for name, g, why, done in items:
        rows.append('<tr><th scope="row"><code>%s</code></th><td>%s</td><td>%s</td><td>%s</td></tr>' % (E(name), pill(g), E(why), E(done)))

detail_section = '''<section aria-labelledby="h-grade-detail">
 <h2 id="h-grade-detail">Why each item got its grade</h2>
 <p>The latest independent reviewer's reason for each grade, and what was changed afterwards. "Nothing left" means the reviewer found nothing to fix.</p>
 <div class="tbl"><table>
  <thead><tr><th scope="col">Item</th><th scope="col">Latest</th><th scope="col">Why</th><th scope="col">Done since</th></tr></thead>
  <tbody>
   %s
  </tbody>
 </table></div>
</section>

<section aria-labelledby="h-method">
 <h2 id="h-method">How the grading worked</h2>
 <ol class="steps">
  <li><span>Three reviewers graded every agent and skill against Anthropic's Claude Code best practices for agents and skills and the repo's own rules, using a scale from A+ to D. A+ means "ship it unchanged as an example of best practice".</span></li>
  <li><span>Each reviewer was new and had not seen earlier grades. They read every file, checked claims against the scripts and the real DayZ files on the P drive, and ran every test, but changed nothing.</span></li>
  <li><span>Fixers then worked through every item below A+, each owning its own files so they did not collide, and added a test for every behavior change.</span></li>
  <li><span>This repeated five times. Every round was committed and pushed to PR #52 on the <code>feature/agent-team</code> branch.</span></li>
 </ol>
 <div class="tbl"><table>
  <thead><tr><th scope="col">Round</th><th scope="col">What happened</th><th scope="col">Tests</th></tr></thead>
  <tbody>
   <tr><th scope="row">Start</th><td>Agents mostly C+ to B-, skills mostly B to C, nothing at A+.</td><td class="num">84</td></tr>
   <tr><th scope="row">1</th><td>Agents rewritten to the lean standard, docs matched to code, tests added to every skill.</td><td class="num">627</td></tr>
   <tr><th scope="row">2</th><td>DayZ facts checked against the P drive, shared helpers, safer dry runs and backups.</td><td class="num">793</td></tr>
   <tr><th scope="row">3</th><td>Split-types server bug, safer setup, launch and update skills.</td><td class="num">919</td></tr>
   <tr><th scope="row">4</th><td>Cleanup safety, update commits, index download, full class indexing.</td><td class="num">974</td></tr>
   <tr><th scope="row">5</th><td>Build and update edge cases, vanilla-accurate rules, visible hook output.</td><td class="num">1,064</td></tr>
  </tbody>
 </table></div>
</section>

<section aria-labelledby="h-bugs">
 <h2 id="h-bugs">Real bugs the grading found and fixed</h2>
 <div class="tbl"><table>
  <thead><tr><th scope="col">Bug</th><th scope="col">What could happen</th></tr></thead>
  <tbody>
   <tr><th scope="row">Search tools missing after install</th><td>Agents installed from the plugin had no RAG search tools at all.</td></tr>
   <tr><th scope="row">Cleanup could delete your mod</th><td><code>/dayz-clean-workspace</code> could delete a mod you cloned in by hand, git history included.</td></tr>
   <tr><th scope="row">Update swept in your changes</th><td><code>/agentic-z-update</code> could put your unrelated staged changes into its own commit.</td></tr>
   <tr><th scope="row">Index download never worked</th><td><code>/dayz-search-download</code> looked for a file name no release uses.</td></tr>
   <tr><th scope="row">RAG skipped big classes</th><td>About 39%% of the code in large script classes like PlayerBase was never searchable.</td></tr>
   <tr><th scope="row">Server could not find split types</th><td><code>/dayz-split-types</code> pointed the economy at the wrong folder and loaded entries twice.</td></tr>
   <tr><th scope="row">Failed build blocked rebuilds</th><td>One failed first build made every later build refuse.</td></tr>
   <tr><th scope="row">Line endings broke updates</th><td>On Windows, every upstream change looked like a local edit.</td></tr>
   <tr><th scope="row">Test launch timeout crash</th><td><code>/dayz-launch-test</code> crashed instead of reporting a server that never started.</td></tr>
   <tr><th scope="row">Edit-types lost comments</th><td>Editing <code>types.xml</code> threw away its comments and rewrote the file even when nothing changed.</td></tr>
   <tr><th scope="row">Port already in use</th><td>A second test session connected to the old server instead of failing clearly.</td></tr>
   <tr><th scope="row">Old textures and atlases counted as new</th><td>A stale <code>.paa</code> from an earlier run was reported as freshly built.</td></tr>
  </tbody>
 </table></div>
</section>

<section aria-labelledby="h-open">
 <h2 id="h-open">Open items and decisions</h2>
 <div class="tbl"><table>
  <thead><tr><th scope="col">Item</th><th scope="col">State</th><th scope="col">Needs</th></tr></thead>
  <tbody>
   <tr><th scope="row">Final recheck</th><td>Items fixed after the last independent check are not yet reconfirmed.</td><td>Brian: run one more recheck, or stop and build a real mod as the proof.</td></tr>
   <tr><th scope="row">Wiki crawler</th><td>On hold. It gets past the Bohemia wiki's Cloudflare check with a copied browser cookie.</td><td>Brian: drop it (recommended), keep it, or ask Bohemia for API access.</td></tr>
   <tr><th scope="row">GitHub test workflow</th><td>Ready locally at <code>.github/workflows/tests.yml</code>, not pushed.</td><td>Brian: run <code>gh auth refresh -h github.com -s workflow</code>, or commit the file.</td></tr>
   <tr><th scope="row">RAG search</th><td>The installed plugin (1.6.0) has the search timeout bug; the fix is on <code>develop</code> and in PR #52.</td><td>A release with the fix, a Voyage API key in <code>.env</code>, and a full re-index to pick up class windowing.</td></tr>
   <tr><th scope="row">PR #52</th><td>Open against <code>develop</code>, five rounds pushed.</td><td>Brian: review and merge.</td></tr>
   <tr><th scope="row">First real build</th><td>The orchestrator, leads and gates have not run on a real mod yet.</td><td>Build one small mod end to end.</td></tr>
  </tbody>
 </table></div>
</section>

<section aria-labelledby="h-roadmap">
 <h2 id="h-roadmap">Next: planned after the A+ pass</h2>
 <h3>Save tokens</h3>
 <div class="tbl"><table>
  <thead><tr><th scope="col">Idea</th><th scope="col">What it does</th></tr></thead>
  <tbody>
   <tr><th scope="row">Script-only gates</th><td>The build check and in-game test become plain scripts that print PASS or FAIL. Claude only wakes up when something fails. The biggest saving.</td></tr>
   <tr><th scope="row">Router (Jev or our own)</th><td>A fast sorter sends each request to a skill, a single specialist, or the full team. It uses TypeSafe's Jev when the user has a <code>TYPESAFE_API_KEY</code>. Otherwise it uses our own: keyword rules first, then a Haiku-pinned <code>dayz-router</code> that returns a route and a confidence.</td></tr>
   <tr><th scope="row">Log triage</th><td>New errors are compared against past errors in the RAG index. Only new ones go to the debugger.</td></tr>
   <tr><th scope="row">Status line mod</th><td>Always shows P drive, active mod, test session and index state.</td></tr>
   <tr><th scope="row">Edit hooks</th><td>A syntax check after every <code>config.cpp</code> or <code>.layout</code> edit, and a guard against editing other mods.</td></tr>
   <tr><th scope="row">Cheaper models</th><td>Simple roles run on Sonnet or Haiku, judgment roles on the strongest model.</td></tr>
   <tr><th scope="row">Smaller rules loading</th><td>Split the Tier 2 file by topic so each agent loads only its part. Cache repeated RAG answers.</td></tr>
  </tbody>
 </table></div>
 <h3>New workflows</h3>
 <div class="specs">
  <div class="sg"><h3>Paste in</h3><ul><li>Crash log or RPT</li><li>Screenshot of a bug</li><li>Figma link</li><li>Workshop or GitHub link</li><li>types.xml chunk</li></ul></div>
  <div class="sg"><h3>Build faster</h3><ul><li>Mod recipes</li><li>Live log watch</li><li>Visual check</li><li>Release pack</li></ul></div>
  <div class="sg"><h3>Stay healthy</h3><ul><li>Upgrade guard after DayZ updates</li><li>Conflict checker vs CF, COT, Expansion</li><li>Balance sheet vs vanilla</li><li>Mod health dashboard</li></ul></div>
  <div class="sg"><h3>Serve owners</h3><ul><li>Server-owner kit</li><li>Ask the codebase with citations</li><li>Per-agent evals</li><li>Prompt caching</li></ul></div>
 </div>
</section>

''' % '\n   '.join(rows)

anchor = '<section aria-labelledby="h-fix">'
assert t.count(anchor) == 1
t = t.replace(anchor, detail_section + anchor)
p.write_text(t, encoding='utf-8')
print('ok')
