"""Bring the non-grade sections of agentic-z-team.html up to origin/develop (v2.0.0)."""
import pathlib

here = pathlib.Path(__file__).parent
p = here / 'agentic-z-team.html'
t = p.read_text(encoding='utf-8')


def replace(sid, new):
    global t
    s = t.index('<section aria-labelledby="%s">' % sid)
    e = t.index('</section>', s) + len('</section>')
    t = t[:s] + new.strip() + t[e:]


def edit(old, new):
    global t
    assert t.count(old) == 1, old[:80]
    t = t.replace(old, new)


replace('h-features', '''
<section aria-labelledby="h-features">
 <h2 id="h-features">The AI features</h2>
 <p>Everything Agentic-Z 2.0.0 gives an AI agent, beyond the agents themselves: what each one is, and what it does for you.</p>
 <div class="tbl"><table>
  <thead><tr><th scope="col">Feature</th><th scope="col">What it is</th><th scope="col">What it does for you</th></tr></thead>
  <tbody>
   <tr class="grp"><th colspan="3" scope="colgroup">Knowledge and search</th></tr>
   <tr><th scope="row">RAG search: game files</th><td>A searchable index of the vanilla DayZ files on your P drive (scripts, configs, layouts, materials, economy XML), built with Voyage AI code embeddings and stored in LanceDB.</td><td>Agents find vanilla code by meaning, like "how does food spoil", instead of guessing class names. Tool: <code>search_dayz_source</code>.</td></tr>
   <tr><th scope="row">File lookup</th><td>Opens an exact file and line range on the P drive, and refuses anything outside it.</td><td>Agents read the real source behind a search hit. Tool: <code>get_dayz_file</code>.</td></tr>
   <tr><th scope="row">Cite then verify</th><td>A rule every agent follows: a search hit is a hint until the real file confirms it.</td><td>Answers come with <code>path:line</code> references you can check, and fewer made-up classes.</td></tr>
   <tr><th scope="row">Cited answers</th><td><code>/dayz-ask</code> answers a vanilla question, checks every hit against P:, and falls back to a keyword search when there is no index or key.</td><td>A plain English question gets an answer with checked <code>path:line</code> citations.</td></tr>
   <tr><th scope="row">Prebuilt index</th><td><code>/dayz-search-download</code> pulls a ready-made index from GitHub.</td><td>A fresh install gets search without spending Voyage credits on embedding.</td></tr>
   <tr><th scope="row">Knowledge packs</th><td>DayZ know-how under <code>.claude/skills/_shared/</code>: ten specialist packs, an Enforce Script pack with references, patterns, framework guides and 13 worked examples, and the Figma rules.</td><td>Agents load only the pack their task needs, so they work from facts checked against P:.</td></tr>
   <tr class="grp"><th colspan="3" scope="colgroup">The agent team</th></tr>
   <tr><th scope="row">Orchestrator and leads</th><td>A planner that runs as your main session, an architect, and one lead per team.</td><td>You describe a mod once and approve a plan; the team splits and tracks the work.</td></tr>
   <tr><th scope="row">Specialists</th><td>DayZ experts for script, config, models, textures, UI, maps, server and Workbench, plus saving data, AI, vehicles, weapons, wearables, animation, audio and FX, and physics.</td><td>Each task goes to an agent that knows that corner of DayZ.</td></tr>
   <tr><th scope="row">Gatekeepers</th><td>Mod review, layout check, build check, in-game test and behavior test, each answering PASS or FAIL.</td><td>Nothing reaches you until it builds and loads in game with clean logs.</td></tr>
   <tr><th scope="row">Router</th><td><code>/dayz-route</code> keyword rules, then Jev when a TypeSafe key is set, then the Haiku <code>dayz-router</code>.</td><td>Most requests reach the right handler with no model tokens.</td></tr>
   <tr><th scope="row">Figma pipeline (optional)</th><td>Three agents that turn a Figma frame into a checked DayZ <code>.layout</code>.</td><td>An extra for people who design menus in Figma. Unused otherwise.</td></tr>
   <tr><th scope="row">Agent creator</th><td>An agent that writes and checks new agent files.</td><td>New agents follow the same template and rules.</td></tr>
   <tr class="grp"><th colspan="3" scope="colgroup">Rules and learning</th></tr>
   <tr><th scope="row">Three tiers</th><td>Repo rules, then DayZ rules (a core file plus five topic files), then agents and packs. The more specific tier wins.</td><td>Every agent works from the same rules without each file repeating them.</td></tr>
   <tr><th scope="row">Corrections become rules</th><td><code>/dayz-record-correction</code> drafts a rule from your correction and saves it after your yes.</td><td>You correct a mistake once and the whole team stops making it.</td></tr>
   <tr><th scope="row">Agent memory</th><td>Each worker agent keeps notes in the project's own <code>.claude/agent-memory/</code> folder. Gates and the lead have none.</td><td>Agents remember your project's choices between sessions, wherever you cloned it.</td></tr>
   <tr class="grp"><th colspan="3" scope="colgroup">Hooks</th></tr>
   <tr><th scope="row">Edit check</th><td>A syntax check after every <code>config.cpp</code> or <code>.layout</code> edit.</td><td>A missing <code>;</code> or <code>}</code> is fixed in the same turn, before a build fails on it.</td></tr>
   <tr><th scope="row">Scope guard</th><td>Denies edits to other mods while <code>/dayz-scope-mod</code> is set.</td><td>An agent working on one mod can't damage another.</td></tr>
   <tr><th scope="row">Paste-in router</th><td>Reads what you paste: crash logs go to triage, <code>types.xml</code> chunks to a checked merge, Figma and GitHub links to their workflow.</td><td>You paste, and the right workflow starts without explaining what it is.</td></tr>
   <tr class="grp"><th colspan="3" scope="colgroup">Safety</th></tr>
   <tr><th scope="row">Permission lists</th><td>A shipped allow list and deny list for shell commands, and an explicit tool list on every agent.</td><td>Agents can run the repo's own skills, but not inline code or new installs.</td></tr>
   <tr><th scope="row">Read-only checkers</th><td>The mod reviewer, layout validator, build checker, in-game tester and debugger can't edit files, and the lead and physics specialist have no write tools.</td><td>The agents that judge the work don't quietly change it.</td></tr>
   <tr class="grp"><th colspan="3" scope="colgroup">Works everywhere</th></tr>
   <tr><th scope="row">Three AI tools</th><td><code>/sync-skills</code> links the same skills into Claude Code, Codex and Gemini.</td><td>Use whichever AI tool you like; the skills are the same.</td></tr>
   <tr><th scope="row">Plugin or clone</th><td>Install as a Claude Code plugin, or clone the repo as a mod template.</td><td>Plugin users update through the marketplace; clones use <code>/agentic-z-update</code>.</td></tr>
   <tr><th scope="row">Side panel</th><td><code>agentic-z-panel</code> 0.3.0, a second plugin with DayZ state and one-click buttons.</td><td>Build, check, launch, stop, open the editors and read the logs without spending tokens.</td></tr>
   <tr><th scope="row">Self-checking repo</th><td>2,845 tests, 18 panel tests, answer tests for 23 of the 30 agents, a CI workflow on GitHub, and <code>/docs-sync</code> to keep the wiki matching the source.</td><td>Broken agents, missing files and wrong tool names are caught before release.</td></tr>
  </tbody>
 </table></div>
</section>
''')

replace('h-status', '''
<section aria-labelledby="h-status">
 <h2 id="h-status">Does it work? Checked October 22, 2026</h2>
 <p>Each feature was checked against <code>origin/develop</code> at version 2.0.0 (commit <code>e70cf1a</code>), or the table says why it couldn't be yet.</p>
 <div class="status-key"><span><span class="pill ok">Works</span> checked</span><span><span class="pill warn">Needs a step</span> works once you do one thing</span><span><span class="pill todo">Not run yet</span> built, waiting for a real DayZ session</span></div>
 <div class="tbl"><table>
  <thead><tr><th scope="col">Feature</th><th scope="col">Status</th><th scope="col">What was checked</th></tr></thead>
  <tbody>
   <tr><th scope="row">Test suite</th><td><span class="pill ok">Works</span></td><td><code>py -m pytest -q .claude scripts/dev hooks</code> in a clean worktree of <code>origin/develop</code> collects 2,845 tests, plus 18 panel tests. They check every agent and skill is registered, every file and skill they name exists, gates can't edit, tier files match, and every wrapper points at a real script.</td></tr>
   <tr><th scope="row">Panel tests</th><td><span class="pill ok">Works</span></td><td><code>claude plugin test mods/agentic-z-panel</code> runs 18 tests.</td></tr>
   <tr><th scope="row">CI on GitHub</th><td><span class="pill ok">Works</span></td><td>The tests workflow passed on the last three pushes to <code>develop</code>, the newest being the merge of PR #144, the last grading fix.</td></tr>
   <tr><th scope="row">Answer tests (evals)</th><td><span class="pill ok">Works</span></td><td>23 of the 30 agents have a question file and a score in <code>evals/baseline.json</code>. Seven are not covered yet.</td></tr>
   <tr><th scope="row">DayZ facts in the packs</th><td><span class="pill ok">Works</span></td><td>The graders opened the cited lines on P: for every pack. Six Enforce Script examples are still marked as vendored and not checked.</td></tr>
   <tr><th scope="row">RAG search: game files</th><td><span class="pill warn">Needs a step</span></td><td>The index on disk is the August 10, 2026 build (52,048 chunks). The search timeout fix ships in 2.0.0, which is on <code>develop</code> and not yet released. Needs a Voyage API key in <code>.env</code> and a full re-index to pick up class windowing.</td></tr>
   <tr><th scope="row">Orchestrator, leads, gates in a real session</th><td><span class="pill todo">Not run yet</span></td><td>Nothing in this build has run against a real DayZ session. The first real test is building one small mod end to end.</td></tr>
   <tr><th scope="row">Behavior and visual gates</th><td><span class="pill todo">Not run yet</span></td><td>Tested with fixtures only. The test mission and the window capture have never run in a live session.</td></tr>
  </tbody>
 </table></div>
</section>
''')

replace('h-bugs', '''
<section aria-labelledby="h-bugs">
 <h2 id="h-bugs">Real bugs the grading found and fixed</h2>
 <p>Each one was found by an independent reviewer, fixed by a separate fixer, and covered by a test.</p>
 <div class="tbl"><table>
  <thead><tr><th scope="col">Bug</th><th scope="col">What could happen</th><th scope="col">Found in</th></tr></thead>
  <tbody>
   <tr><th scope="row">Search tools missing after install</th><td>Agents installed from the plugin had no RAG search tools at all.</td><td>v1.7.0</td></tr>
   <tr><th scope="row">Cleanup could delete your mod</th><td><code>/dayz-clean-workspace</code> could delete a mod you cloned in by hand, git history included.</td><td>v1.7.0</td></tr>
   <tr><th scope="row">Update swept in your changes</th><td><code>/agentic-z-update</code> could put your unrelated staged changes into its own commit.</td><td>v1.7.0</td></tr>
   <tr><th scope="row">Index download never worked</th><td><code>/dayz-search-download</code> looked for a file name no release uses.</td><td>v1.7.0</td></tr>
   <tr><th scope="row">RAG skipped big classes</th><td>About 39% of the code in large script classes like PlayerBase was never searchable.</td><td>v1.7.0</td></tr>
   <tr><th scope="row">Server could not find split types</th><td><code>/dayz-split-types</code> pointed the economy at the wrong folder and loaded entries twice.</td><td>v1.7.0</td></tr>
   <tr><th scope="row">Failed build blocked rebuilds</th><td>One failed first build made every later build refuse.</td><td>v1.7.0</td></tr>
   <tr><th scope="row">Line endings broke updates</th><td>On Windows, every upstream change looked like a local edit.</td><td>v1.7.0</td></tr>
   <tr><th scope="row">Port already in use</th><td>A second test session connected to the old server instead of failing clearly.</td><td>v1.7.0</td></tr>
   <tr><th scope="row">Old textures and atlases counted as new</th><td>A stale <code>.paa</code> from an earlier run was reported as freshly built.</td><td>v1.7.0</td></tr>
   <tr><th scope="row">Wrong project picked up</th><td>With two Agentic-Z projects on one machine, a skill could work on the other project's workspace.</td><td>v2.0.0</td></tr>
   <tr><th scope="row">UI styles left out of the PBO</th><td><code>/dayz-build-pbo</code> did not pack <code>.styles</code> files, so menus that use them shipped without their styles.</td><td>v2.0.0</td></tr>
   <tr><th scope="row">Server-only mods sent to clients</th><td><code>/dayz-launch-test</code> had no way to keep a server-only mod off the client.</td><td>v2.0.0</td></tr>
   <tr><th scope="row">Lint stopped good mods</th><td><code>/dayz-lint</code> failed builds on findings that do not stop a mod loading.</td><td>v2.0.0</td></tr>
   <tr><th scope="row">Unsafe names in the behavior gate</th><td>A crafted instance or template name could point the behavior test outside its folder.</td><td>v2.0.0</td></tr>
   <tr><th scope="row">Spec written into an import</th><td>A rerun of <code>/dayz-init</code> could write <code>spec.md</code> into a linked mod you imported.</td><td>v2.0.0</td></tr>
   <tr><th scope="row">Balance compared the wrong items</th><td><code>/dayz-balance</code> missed mod overrides of a vanilla class with the same name.</td><td>v2.0.0</td></tr>
   <tr><th scope="row">Upgrade guard missed changes</th><td><code>/dayz-upgrade-guard</code> missed inherited members and config keys written in a different case.</td><td>v2.0.0</td></tr>
   <tr><th scope="row">Conflict check refused linked mods</th><td><code>/dayz-conflict-check --ingame</code> refused <code>@mods</code> that were links.</td><td>v2.0.0</td></tr>
   <tr><th scope="row">Requests routed to the wrong owner</th><td><code>/dayz-route</code> sent spawn and modded class requests to object specialists instead of their owners.</td><td>v2.0.0</td></tr>
   <tr><th scope="row">Wrong vanilla facts in the new packs</th><td>The vehicle, wearables, audio, AI and animation packs had wrong line citations and class facts, all corrected against P:.</td><td>v2.0.0</td></tr>
   <tr><th scope="row">Gates kept memory</th><td>The read-only gates had a memory folder, which a gate that only judges should not have.</td><td>v2.0.0</td></tr>
  </tbody>
 </table></div>
</section>
''')

replace('h-open', '''
<section aria-labelledby="h-open">
 <h2 id="h-open">Open items and decisions</h2>
 <div class="tbl"><table>
  <thead><tr><th scope="col">Item</th><th scope="col">State</th><th scope="col">Needs</th></tr></thead>
  <tbody>
   <tr><th scope="row">Live DayZ checks</th><td>Still owed. Nothing in this build has run against a real DayZ session: not the team loop, not the in-game, behavior or visual gates, not the panel's launch buttons.</td><td>Build one small mod end to end with DayZ running on the user's PC. Asked for before it runs.</td></tr>
   <tr><th scope="row">Release 2.0.0 to <code>main</code></th><td>Version 2.0.0 and its release notes are on <code>develop</code>. CI passes there.</td><td>User: say yes to merging <code>develop</code> into <code>main</code>. Nothing is released until then.</td></tr>
   <tr><th scope="row">Items below A+</th><td>33 of 164 graded items are below A+. Their defects are listed in "Why each item got its grade" and are not fixed yet.</td><td>A fix round, then a fresh independent regrade.</td></tr>
   <tr><th scope="row">Answer tests for seven agents</th><td>No question file yet for the build checker, in-game tester, architect, lead, orchestrator, router and Figma to layout.</td><td>Write their question files and record a baseline.</td></tr>
   <tr><th scope="row">RAG search</th><td>The installed plugin (1.6.0) has the search timeout bug. The fix is in 2.0.0.</td><td>The release, a Voyage API key in <code>.env</code>, and a full re-index.</td></tr>
  </tbody>
 </table></div>
</section>
''')

replace('h-roadmap', '''
<section aria-labelledby="h-roadmap">
 <h2 id="h-roadmap">Token savers and workflows (built in 2.0.0) and the roadmap</h2>
 <p>Every token saver and workflow below is built, tested and on <code>develop</code>. None has run against a live DayZ session yet.</p>
 <h3>Save tokens</h3>
 <div class="tbl"><table>
  <thead><tr><th scope="col">Saver</th><th scope="col">What it does</th></tr></thead>
  <tbody>
   <tr><th scope="row">Script-only gates</th><td><code>/dayz-gate build</code>, <code>ingame</code>, <code>behavior</code> and <code>visual</code> are plain scripts that print PASS, FAIL or ERROR. Claude only wakes up when something fails. The biggest saving.</td></tr>
   <tr><th scope="row">Log triage</th><td>52 known errors, each with its fix and owner. Only new errors go to the debugger, and <code>triage.py --learn</code> adds your own.</td></tr>
   <tr><th scope="row">Router</th><td>Keyword rules first, then TypeSafe's Jev when <code>TYPESAFE_API_KEY</code> is set, then the Haiku <code>dayz-router</code>.</td></tr>
   <tr><th scope="row">Hooks</th><td>The edit check, the scope guard and the paste-in router.</td></tr>
   <tr><th scope="row">Status line</th><td>P:, active mod, DayZ Diag and index age under the prompt, with no tokens.</td></tr>
   <tr><th scope="row">Cheaper models</th><td>The build engineer and router run on Haiku, the docs writer on Sonnet.</td></tr>
   <tr><th scope="row">Smaller rules loading</th><td>Tier 2 split into a core file and five topic files: a typical agent run reads 31% less rules text.</td></tr>
   <tr><th scope="row">Panel and wrappers</th><td>The <code>agentic-z-panel</code> buttons and a <code>.bat</code> for every runnable skill run the scripts directly.</td></tr>
   <tr><th scope="row">Shorter descriptions</th><td>About 2,100 tokens less loaded into every session.</td></tr>
  </tbody>
 </table></div>
 <h3>Workflows</h3>
 <div class="specs">
  <div class="sg"><h3>Paste in</h3><ul><li>Crash log or RPT</li><li>Screenshot of a bug</li><li>Figma link</li><li>GitHub link</li><li>types.xml chunk</li></ul></div>
  <div class="sg"><h3>Build faster</h3><ul><li>Mod recipes</li><li>Live log watch</li><li>Behavior and visual gates</li><li>Release pack</li></ul></div>
  <div class="sg"><h3>Stay healthy</h3><ul><li>Upgrade guard</li><li>Conflict check with CF, COT, Expansion</li><li>Balance sheet against vanilla</li><li>Health page per mod</li></ul></div>
  <div class="sg"><h3>Serve owners</h3><ul><li>Server kit</li><li>Cited answers about vanilla</li><li>Answer tests</li><li>Layout preview</li></ul></div>
 </div>
 <h3>Roadmap</h3>
 <ol class="steps">
  <li><span><b>Live DayZ checks.</b> Build one small mod end to end with DayZ running, and run the in-game, behavior and visual gates for real.</span></li>
  <li><span><b>Release 2.0.0.</b> Merge <code>develop</code> into <code>main</code> after the user's yes.</span></li>
  <li><span><b>Close the open defects.</b> Fix every item below A+, then a fresh independent regrade.</span></li>
  <li><span><b>Answer tests for the last seven agents.</b></span></li>
  <li><span><b>Add-ons plugin.</b> An optional <code>agentic-z-addons</code> plugin for outside tools, built only after the core is done and only for the add-ons the user names.</span></li>
 </ol>
</section>
''')

replace('h-fix', '''
<section aria-labelledby="h-fix">
 <h2 id="h-fix">What changed from Agentic-Z 1.6.0</h2>
 <p>Each row comes from the quality review or the 2.0.0 build.</p>
 <div class="tbl"><table>
  <thead><tr><th scope="col">Change</th><th scope="col">Why</th></tr></thead>
  <tbody>
   <tr><th scope="row"><span class="pill new">New</span> Orchestrator, architect and team leads</th><td>Before, you picked a specialist yourself and nothing split a mod into tasks or checked that the pieces fit.</td></tr>
   <tr><th scope="row"><span class="pill new">New</span> Eight specialists with knowledge packs</th><td>Saving data, AI, vehicles, weapons, wearables, animation, audio and FX, and physics each have an agent and a pack checked against P:.</td></tr>
   <tr><th scope="row"><span class="pill new">New</span> Script-only gates</th><td>A reviewer existed, but nothing forced a check before a build. Now every wave has to lint, pack cleanly and load in game with clean logs.</td></tr>
   <tr><th scope="row"><span class="pill new">New</span> Workflows and hooks</th><td>Recipes, log watch, release pack, server kit, upgrade guard, conflict check, balance, health page, cited answers, layout preview and the paste-in router.</td></tr>
   <tr><th scope="row"><span class="pill move">Moved</span> Debugger on the fail path</th><td>Triage sends known errors straight to the owner; the debugger gets only new ones.</td></tr>
   <tr><th scope="row"><span class="pill fix">Fix</span> Search works after install</th><td>An installed agent had no search tools at all. Every agent now asks for the tools under both names.</td></tr>
   <tr><th scope="row"><span class="pill fix">Fix</span> Every agent ships in the plugin</th><td>The Figma and layout agents and two skills weren't registered, so plugin users never got them. A test now checks every agent and skill.</td></tr>
   <tr><th scope="row"><span class="pill new">New</span> Corrections become rules</th><td>A skill turns your correction into a rule in the right tier, only after your yes.</td></tr>
   <tr><th scope="row"><span class="pill fix">Gone</span> Wiki search</th><td>The wiki crawler, <code>/dayz-search-wiki-index</code> and the <code>search_dayz_wiki</code> tool were removed. The search server covers vanilla DayZ source only.</td></tr>
  </tbody>
 </table></div>
</section>
''')

replace('h-tiers', '''
<section aria-labelledby="h-tiers">
 <h2 id="h-tiers">The three tiers every agent works from</h2>
 <p>The more specific tier wins, and no tier repeats another.</p>
 <div class="tbl"><table>
  <thead><tr><th scope="col">Tier</th><th scope="col">What it holds</th><th scope="col">Loads</th></tr></thead>
  <tbody>
   <tr><th scope="row">1 · Repo rules</th><td>How every agent works: communication, tooling, memory, routing. <code>CLAUDE.md</code>, <code>AGENTS.md</code>, <code>GEMINI.md</code>.</td><td>Every agent, every task</td></tr>
   <tr><th scope="row">2 · DayZ rules</th><td>Enforce Script style, config and asset rules, environment, vanilla search. <code>dayz-conventions.md</code> plus topic files for config, assets, scripts, UI and server.</td><td>All DayZ work</td></tr>
   <tr><th scope="row">3 · Agents and knowledge packs</th><td>The 30 agents, the 44 skills, and the packs below.</td><td>Only what the task needs</td></tr>
  </tbody>
 </table></div>
</section>
''')

replace('h-agents', '''
<section aria-labelledby="h-agents">
 <h2 id="h-agents">The agents</h2>
 <p>30 agents in all. "New" means added since version 1.6.0.</p>
 <div class="tbl"><table>
  <thead><tr><th scope="col">Agent</th><th scope="col">Job</th><th scope="col">Since 1.6.0</th></tr></thead>
  <tbody>
   <tr class="grp"><th colspan="3" scope="colgroup">Plan</th></tr>
   <tr><th scope="row">Mod orchestrator</th><td>Plans the mod with you, splits it into small tasks, hands them to leads, runs the gates, tracks what is done.</td><td><span class="pill new">New</span></td></tr>
   <tr><th scope="row">Mod architect</th><td>Plans the classes, files, assets and behavior checks before work starts.</td><td><span class="pill new">New</span></td></tr>
   <tr><th scope="row">Lead (one agent, six teams)</th><td>Runs one team: script, config, art, UI, server or release. Splits its share into worker tasks and checks the results fit.</td><td><span class="pill new">New</span></td></tr>
   <tr class="grp"><th colspan="3" scope="colgroup">Workers</th></tr>
   <tr><th scope="row">Script engineer</th><td>Writes Enforce Script: modded classes, RPCs, game logic.</td><td><span class="pill keep">Keep</span></td></tr>
   <tr><th scope="row">Workbench plugins</th><td>Builds tools inside Enfusion Workbench.</td><td><span class="pill keep">Keep</span></td></tr>
   <tr><th scope="row">Config engineer</th><td>Writes config.cpp, class inheritance and hidden selections.</td><td><span class="pill keep">Keep</span></td></tr>
   <tr><th scope="row">Object Builder</th><td>Sets up .p3d models, LODs, selections and doors.</td><td><span class="pill keep">Keep</span></td></tr>
   <tr><th scope="row">Textures and materials</th><td>Handles .paa textures and .rvmat materials.</td><td><span class="pill keep">Keep</span></td></tr>
   <tr><th scope="row">UI engineer</th><td>Builds .layout files and the scripts that drive them.</td><td><span class="pill keep">Keep</span></td></tr>
   <tr><th scope="row">Figma cleaner</th><td>Tidies a Figma frame so it can be converted.</td><td><span class="pill keep">Keep</span></td></tr>
   <tr><th scope="row">Figma to layout</th><td>Turns the cleaned frame into a DayZ .layout, and repairs one the validator failed.</td><td><span class="pill keep">Keep</span></td></tr>
   <tr><th scope="row">Server admin</th><td>types.xml, init.c and server settings.</td><td><span class="pill keep">Keep</span></td></tr>
   <tr><th scope="row">Map builder</th><td>Terrain Builder and DayZ Editor work.</td><td><span class="pill keep">Keep</span></td></tr>
   <tr><th scope="row">Build engineer</th><td>Runs the build, test server and launch skills (Haiku).</td><td><span class="pill new">New</span></td></tr>
   <tr><th scope="row">Docs writer</th><td>Keeps the mod's README, changelog and classname list current (Sonnet).</td><td><span class="pill new">New</span></td></tr>
   <tr class="grp"><th colspan="3" scope="colgroup">Specialists</th></tr>
   <tr><th scope="row">Saving data</th><td>Saving data across restarts, save versions, base building, and a data audit before release. Works under the script lead.</td><td><span class="pill new">New</span></td></tr>
   <tr><th scope="row">AI</th><td>Infected, animals and human AI such as patrols and guards, written from scratch. Works under the script lead.</td><td><span class="pill new">New</span></td></tr>
   <tr><th scope="row">Vehicles</th><td>Cars, boats and helicopters: engine, gearbox, wheels, doors, fluids, seats and damage. Works under the config lead.</td><td><span class="pill new">New</span></td></tr>
   <tr><th scope="row">Weapons</th><td>Weapons, magazines, ammo, attachments, recoil and fire modes. Works under the config lead.</td><td><span class="pill new">New</span></td></tr>
   <tr><th scope="row">Wearables</th><td>Clothing, characters, inventory slots, protection, color variants and proxies. Works under the art lead.</td><td><span class="pill new">New</span></td></tr>
   <tr><th scope="row">Animation</th><td>model.cfg animations, RTM files and the Blender handoff. Works under the art lead.</td><td><span class="pill new">New</span></td></tr>
   <tr><th scope="row">Audio and FX</th><td>Sound shaders, sound sets and particle effects. Works under any lead that needs it.</td><td><span class="pill new">New</span></td></tr>
   <tr><th scope="row">Physics</th><td>Weight, collision LODs, dropping, throwing and contact. Diagnoses and hands the fix to the owner; never edits. Works under any lead.</td><td><span class="pill new">New</span></td></tr>
   <tr class="grp"><th colspan="3" scope="colgroup">Support</th></tr>
   <tr><th scope="row">Router</th><td>Cheap Haiku agent behind <code>/dayz-route</code> that decides who handles a request.</td><td><span class="pill new">New</span></td></tr>
   <tr><th scope="row">Agent creator</th><td>Writes and checks new agent files against the agent standard.</td><td><span class="pill keep">Keep</span></td></tr>
   <tr class="grp"><th colspan="3" scope="colgroup">Gatekeepers (read only)</th></tr>
   <tr><th scope="row">Mod reviewer</th><td>Checks the mod against the DayZ conventions, PASS or FAIL.</td><td><span class="pill keep">Keep</span></td></tr>
   <tr><th scope="row">Layout validator</th><td>Checks a <code>.layout</code> against the Figma-to-DayZ rules without editing it; the UI gate.</td><td><span class="pill keep">Keep</span></td></tr>
   <tr><th scope="row">Build checker and in-game tester</th><td>Fallbacks for when <code>/dayz-gate build</code> or <code>/dayz-gate ingame</code> itself breaks.</td><td><span class="pill new">New</span></td></tr>
   <tr><th scope="row">Debugger</th><td>Reads the logs for errors triage does not know, and names the cause and the owner.</td><td><span class="pill move">Moved</span></td></tr>
  </tbody>
 </table></div>
</section>
''')

replace('h-skills', '''
<section aria-labelledby="h-skills">
 <h2 id="h-skills">The skills</h2>
 <p>44 slash commands any agent or person can run: 40 ship in the plugin, and four are for clones only. Every skill that touches P: or DayZ Tools checks the environment first with <code>/dayz-preflight</code>; the documented exceptions include <code>/dayz-stop-test</code>, so it still works as an emergency stop.</p>
 <div class="tbl"><table>
  <thead><tr><th scope="col">Skill</th><th scope="col">What it does</th></tr></thead>
  <tbody>
   <tr class="grp"><th colspan="2" scope="colgroup">Setup</th></tr>
   <tr><th scope="row"><code>/dayz-init</code></th><td>Setup wizard on first run, with an optional spec step; a status hub for the active mod after that.</td></tr>
   <tr><th scope="row"><code>/dayz-preflight</code></th><td>Checks the P drive, DayZ Tools, vanilla data and the Workshop link.</td></tr>
   <tr><th scope="row"><code>/dayz-workdrive</code></th><td>Mounts the P drive after a reboot without opening DayZ Tools.</td></tr>
   <tr><th scope="row"><code>/dayz-setup-objectbuilder</code></th><td>Configures Object Builder on a new machine.</td></tr>
   <tr class="grp"><th colspan="2" scope="colgroup">Mods</th></tr>
   <tr><th scope="row"><code>/dayz-new-mod</code></th><td>Creates a new mod with the standard folders and files.</td></tr>
   <tr><th scope="row"><code>/dayz-import-mod</code></th><td>Brings an existing mod folder or a GitHub repo into the workspace.</td></tr>
   <tr><th scope="row"><code>/dayz-add-scaffold</code></th><td>Adds missing standard pieces to an existing mod.</td></tr>
   <tr><th scope="row"><code>/dayz-recipe</code></th><td>Starts a plan from a recipe (new weapon, new vest, new craftable) for the architect to finish.</td></tr>
   <tr><th scope="row"><code>/dayz-scope-mod</code></th><td>Locks editing to one mod.</td></tr>
   <tr><th scope="row"><code>/dayz-clean-workspace</code></th><td>Removes mods it created, and their builds.</td></tr>
   <tr class="grp"><th colspan="2" scope="colgroup">Build</th></tr>
   <tr><th scope="row"><code>/dayz-lint</code></th><td>Finds errors that would stop a mod loading, before packing. Runs first inside the build gate and <code>/dayz-build-pbo</code>.</td></tr>
   <tr><th scope="row"><code>/dayz-build-pbo</code></th><td>Packs a mod into a PBO with AddonBuilder.</td></tr>
   <tr><th scope="row"><code>/dayz-deploy-pbo</code></th><td>Copies prebuilt PBOs and keys into place without AddonBuilder.</td></tr>
   <tr class="grp"><th colspan="2" scope="colgroup">Test</th></tr>
   <tr><th scope="row"><code>/dayz-add-server</code></th><td>Sets up a local test server instance.</td></tr>
   <tr><th scope="row"><code>/dayz-launch-test</code></th><td>Starts a diag server and client with your mods.</td></tr>
   <tr><th scope="row"><code>/dayz-stop-test</code></th><td>Stops the test session.</td></tr>
   <tr><th scope="row"><code>/dayz-cot-bootstrap</code></th><td>Gives you admin in Community Online Tools on the test server.</td></tr>
   <tr><th scope="row"><code>/dayz-logwatch</code></th><td>Watches the logs during a test session and triages each new error as it appears.</td></tr>
   <tr class="grp"><th colspan="2" scope="colgroup">Checks, routing and status</th></tr>
   <tr><th scope="row"><code>/dayz-gate</code></th><td>Build, in-game, behavior and visual checks as scripts that print PASS or FAIL, with known-error triage.</td></tr>
   <tr><th scope="row"><code>/dayz-conflict-check</code></th><td>Finds prefix, path and class collisions with CF, COT and Expansion.</td></tr>
   <tr><th scope="row"><code>/dayz-upgrade-guard</code></th><td>After a DayZ update, lists mod classes whose vanilla parents changed.</td></tr>
   <tr><th scope="row"><code>/dayz-balance</code></th><td>Compares item stats with similar vanilla items and flags outliers.</td></tr>
   <tr><th scope="row"><code>/dayz-health</code></th><td>A page per mod with the last build, last test, open findings and gate history.</td></tr>
   <tr><th scope="row"><code>/dayz-route</code></th><td>Shows which skill, specialist or team should handle a request.</td></tr>
   <tr><th scope="row"><code>/dayz-statusline</code></th><td>Installs a status line with P:, the active mod, DayZ Diag and index age.</td></tr>
   <tr class="grp"><th colspan="2" scope="colgroup">Art and UI</th></tr>
   <tr><th scope="row"><code>/dayz-pack-texture</code></th><td>Converts images to <code>.paa</code> and checks their suffixes.</td></tr>
   <tr><th scope="row"><code>/dayz-build-imageset</code></th><td>Packs UI sprites into an imageset.</td></tr>
   <tr><th scope="row"><code>/dayz-layout-preview</code></th><td>Draws a <code>.layout</code> as PNGs at several screen sizes and flags widgets off screen.</td></tr>
   <tr><th scope="row"><code>/dayz-p3d-audit</code></th><td>Finds collision, physics and structure problems in models.</td></tr>
   <tr><th scope="row"><code>/dayz-particles</code></th><td>Reference for making particle effects without Workbench.</td></tr>
   <tr><th scope="row"><code>/dayz-launch-objectbuilder</code></th><td>Opens Object Builder on a model.</td></tr>
   <tr><th scope="row"><code>/dayz-launch-workbench</code></th><td>Opens Workbench on a mod's project.</td></tr>
   <tr class="grp"><th colspan="2" scope="colgroup">Server economy</th></tr>
   <tr><th scope="row"><code>/dayz-edit-types</code></th><td>Adds, changes, removes or merges <code>types.xml</code> entries.</td></tr>
   <tr><th scope="row"><code>/dayz-split-types</code></th><td>Splits one big <code>types.xml</code> into 19 category files.</td></tr>
   <tr class="grp"><th colspan="2" scope="colgroup">Release</th></tr>
   <tr><th scope="row"><code>/dayz-release-pack</code></th><td>Writes the Workshop description, a changelog entry, the classname list and server-owner install notes.</td></tr>
   <tr><th scope="row"><code>/dayz-server-kit</code></th><td>Zips types.xml entries, cfgeconomycore lines, load order and the public key for server owners.</td></tr>
   <tr class="grp"><th colspan="2" scope="colgroup">RAG search</th></tr>
   <tr><th scope="row"><code>/dayz-search-index</code></th><td>Builds the game-files index.</td></tr>
   <tr><th scope="row"><code>/dayz-search-download</code></th><td>Downloads a prebuilt index instead.</td></tr>
   <tr><th scope="row"><code>/dayz-ask</code></th><td>Answers a plain-English question about vanilla DayZ with checked path:line citations.</td></tr>
   <tr class="grp"><th colspan="2" scope="colgroup">Team and repo</th></tr>
   <tr><th scope="row"><code>/dayz-record-correction</code></th><td>Turns your correction into a team rule.</td></tr>
   <tr><th scope="row"><code>/sync-skills</code></th><td>Links the skills into Claude Code, Codex and Gemini (clones only).</td></tr>
   <tr><th scope="row"><code>/agentic-z-update</code></th><td>Pulls template updates into a clone (clones only).</td></tr>
   <tr><th scope="row"><code>/docs-sync</code></th><td>Keeps the docs wiki matching the source files (clones only).</td></tr>
   <tr><th scope="row"><code>/clean-repo</code></th><td>Repo-wide cleanup across every domain (clones only).</td></tr>
  </tbody>
 </table></div>
 <p class="example">The side panel is a separate plugin, not a skill: <code>/plugin install agentic-z-panel@dayz-n-chill</code>, then <code>/dayz-panel</code> opens it.</p>
</section>
''')

replace('h-specs', '''
<section aria-labelledby="h-specs">
 <h2 id="h-specs">The knowledge packs</h2>
 <p>All under <code>.claude/skills/_shared/</code>. Any worker can load any of them for one task, and every game fact in them cites a P: file and line.</p>
 <div class="specs">
  <div class="sg"><h3>Specialist packs</h3><ul><li>Saving data</li><li>AI</li><li>Vehicles</li><li>Weapons</li><li>Wearables</li><li>Animation</li><li>Audio and FX</li><li>Physics</li><li>Models and LODs</li><li>Textures and rvmats</li></ul></div>
  <div class="sg"><h3>Enforce Script</h3><ul><li>Language and core API references</li><li>Patterns: modded classes, RPCs, net sync, persistence, actions, scheduler, JSON config</li><li>13 worked examples</li></ul></div>
  <div class="sg"><h3>Frameworks</h3><ul><li>Community Framework</li><li>Dabs Framework</li><li>Central Economy</li><li>Input bindings</li><li>Vanilla plugins</li></ul></div>
  <div class="sg"><h3>UI</h3><ul><li>GUI layouts and widgets</li><li>Figma to DayZ rules</li><li>Imagesets (a section of the widget API reference, not a pack of its own)</li></ul></div>
  <div class="sg"><h3>Rules</h3><ul><li>Tier 2 core</li><li>Config, assets, scripts, UI and server topics</li><li>Container base</li></ul></div>
 </div>
</section>
''')

# Specialist workflows (team copy): match the guide's corrected rows.
edit('<li>The layout checker compares it with the design; the in-game test opens it.</li>',
     '<li>The layout checker checks it against the Figma-to-DayZ rules and <code>/dayz-layout-preview</code> draws it; the in-game test opens it.</li>')
edit('<li>Compares the .layout with the design.</li><li>Reports PASS or FAIL with each difference.</li>',
     '<li>Checks the .layout against the Figma-to-DayZ rules: file format and widget classes.</li><li>Reports PASS or FAIL with each problem and its line. Never edits.</li>')
edit('<li>Gives the server lead a types.xml entry; the in-game test spawns and drives it.</li>',
     '<li>Gives the server lead a types.xml entry; the behavior gate spawns it and a person-run checklist covers driving.</li>')
edit('<li>In-game test fires, reloads and fits each attachment.</li>',
     '<li>The behavior gate spawns it and fits each attachment; a person-run checklist covers firing and reloading.</li>')
edit('<li>Hands the fix to the Object Builder or config specialist.</li><li>In-game test drops, throws and shoots it.</li>',
     '<li>Hands the fix to the Object Builder or config specialist; it never edits.</li><li>A person-run in-game test drops, throws and shoots it, which the behavior gate cannot.</li>')

edit('<p class="foot">Built on the <code>feature/agent-team</code> branch of Agentic-Z. Committed and pushed for review (PR #52), not merged yet. Written to become the overview page on the Agentic-Z wiki.</p>',
     '<p class="foot">Agentic-Z 2.0.0, as built on <code>origin/develop</code> (commit <code>e70cf1a</code>, October 22, 2026). Not yet released to <code>main</code>.</p>')

p.write_text(t, encoding='utf-8')
print('ok')
