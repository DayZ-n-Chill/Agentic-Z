"""One-time patch: bring make_guide.py's own sections up to origin/develop (v2.0.0)."""
import pathlib

p = pathlib.Path(__file__).parent / 'make_guide.py'
s = p.read_text(encoding='utf-8')

R = [
# header
('the AI agent stack for DayZ modding. Read it top to bottom once and you will not need to ask.</p>',
 'the AI agent stack for DayZ modding. This edition covers version 2.0.0: 30 agents, 44 skills, three hooks and a side panel. Read it top to bottom once and you will not need to ask.</p>'),
# what it is
('<div class="sg"><h3>Specialists</h3><ul><li>Scripts</li><li>Configs</li><li>Textures</li><li>Models</li><li>UI</li><li>Maps</li><li>Server</li><li>Debugging</li></ul></div>',
 '<div class="sg"><h3>Specialists</h3><ul><li>Scripts, configs, UI</li><li>Models and textures</li><li>Maps and server</li><li>Saving data and AI</li><li>Vehicles and weapons</li><li>Wearables and animation</li><li>Audio, FX and physics</li><li>Review and debugging</li></ul></div>'),
('<div class="sg"><h3>Skills</h3><ul><li>Setup wizard</li><li>Build PBO</li><li>Launch test</li><li>types.xml</li><li>Textures</li></ul></div>',
 '<div class="sg"><h3>Skills</h3><ul><li>Setup wizard</li><li>Lint and build PBO</li><li>Launch test and gates</li><li>types.xml</li><li>Textures and layouts</li><li>Release pack</li></ul></div>'),
# token savers
('<td>Matches failures against 24 known errors with their fix and owner. Only new errors go to the debugger.</td>',
 '<td>Matches failures against 52 known errors with their fix and owner. Only new errors go to the debugger.</td>'),
('<td>Checks <code>config.cpp</code> and <code>.layout</code> syntax after every edit, and blocks edits to other mods while scoped.</td><td>Automatic with the plugin.</td></tr>',
 '<td>Checks <code>config.cpp</code> and <code>.layout</code> syntax after every edit, and blocks edits to other mods while scoped.</td><td>Automatic with the plugin or a clone.</td></tr>\n  <tr><th scope="row">Paste-in router</th><td>Reads what you paste: crash logs are triaged on the spot, <code>types.xml</code> chunks are checked for a merge, Figma and GitHub links start their workflow.</td><td>Automatic; just paste.</td></tr>'),
('<td>A panel beside the chat with buttons for mount P:, build, launch, stop, Workbench and Object Builder.</td>',
 '<td>A panel beside the chat with buttons for mount P:, build, the build and in-game checks, deploy, launch, stop, Workbench, Object Builder, test logs, the health page and the release pack, plus a field that asks <code>/dayz-ask</code>.</td>'),
('<tr><th scope="row">Cheaper models</th><td>Simple roles run on Haiku or Sonnet.</td><td>Automatic.</td></tr>',
 '<tr><th scope="row">Cheaper models</th><td>The build engineer and router run on Haiku, the docs writer on Sonnet.</td><td>Automatic.</td></tr>'),
('<td>The DayZ rules file is split by topic; a typical agent run reads 31%% less.</td><td>Automatic.</td></tr>',
 '<td>The DayZ rules file is split by topic; a typical agent run reads 31%% less.</td><td>Automatic.</td></tr>\n  <tr><th scope="row">No-token wrappers</th><td>A <code>.bat</code> for every runnable skill, so you can run it yourself with no AI involved.</td><td>See <code>scripts\\\\README.md</code>.</td></tr>\n  <tr><th scope="row">Shorter descriptions</th><td>Every skill and agent description loads into every session, so they were cut to about 2,100 tokens less.</td><td>Automatic.</td></tr>'),
# specialist workflows
('<li>Gives the server lead a types.xml entry; the in-game test spawns and drives it.</li>',
 '<li>Gives the server lead a types.xml entry; the behavior gate spawns it and a person-run checklist covers driving.</li>'),
('<li>In-game test fires, reloads and fits each attachment.</li>',
 '<li>The behavior gate spawns it and fits each attachment; a person-run checklist covers firing and reloading.</li>'),
('<li>Hands the fix to the Object Builder or config specialist.</li><li>In-game test drops, throws and shoots it.</li>',
 '<li>Hands the fix to the Object Builder or config specialist; it never edits.</li><li>A person-run in-game test drops, throws and shoots it, which the behavior gate cannot.</li>'),
('<li>Reports PASS or FAIL with each problem and its line.</li></ol>',
 '<li>Reports PASS or FAIL with each problem and its line. Never edits.</li></ol>'),
('<li>The layout checker checks it against the Figma-to-DayZ rules; the in-game test opens it.</li>',
 '<li>The layout checker checks it against the Figma-to-DayZ rules and <code>/dayz-layout-preview</code> draws it; the in-game test opens it.</li>'),
# workflows
('<tr><th scope="row">A screenshot of a bug</th><td>Finds the widget, texture or class on screen and routes it to the right specialist.</td></tr>',
 '<tr><th scope="row">A screenshot of a bug</th><td>Routes it to the right specialist: a UI problem to the UI specialist, a texture or material problem to the asset specialist, an error or wrong behavior to the script specialist.</td></tr>'),
('<tr><th scope="row">A Workshop or GitHub link</th><td>Imports the mod into <code>workspace\\\\</code> and fills in the missing standard pieces.</td></tr>',
 '<tr><th scope="row">A GitHub link</th><td>Points at <code>/dayz-import-mod --source &lt;link&gt;</code>, which imports the mod into <code>workspace\\\\</code> and can fill in the missing standard pieces.</td></tr>\n  <tr><th scope="row">A Steam Workshop link</th><td>Refused with the reason: Workshop content is packed, binarized and often protected.</td></tr>'),
('<tr><th scope="row">A types.xml chunk</th><td>Checks the entries and merges them into the server economy.</td></tr>',
 '<tr><th scope="row">A types.xml chunk</th><td>Checks the entries and points at <code>/dayz-edit-types --merge</code> to merge them, with any problems listed.</td></tr>'),
('<td>Takes screenshots during the in-game test and compares them with the expected look.</td>',
 '<td>Takes screenshots during the in-game test and compares them with stored baselines.</td>'),
('<td>After a DayZ update, re-indexes the game files and flags mod classes whose vanilla parents changed.</td>',
 '<td>Snapshots vanilla before a DayZ update, then lists the mod classes whose vanilla parents changed, and can rebuild the search index.</td>'),
('<td>Loads your mod with CF, COT and Expansion and reports class and path collisions.</td>',
 '<td>Finds prefix, path and class collisions with CF, COT and Expansion from their configs and PBO headers, without extracting them; <code>--ingame</code> also loads them together in a test session.</td>'),
('<td>A page per mod with the last build, last test, open review findings and test history.</td>',
 '<td>A page per mod with the last build, last test, open findings and the history of every gate run.</td>'),
('<p class="example">Answer tests (evals) check each agent\'s answers so a change can only make them better. Claude Code caches prompts automatically, and Agentic-Z keeps its big rules files stable so the cache holds from one request to the next.</p>',
 '<p class="example">Answer tests (evals) check 22 of the 30 agents, and a change may only keep or raise a score. Claude Code caches prompts automatically, and Agentic-Z keeps its big rules files stable so the cache holds from one request to the next. The behavior and visual gates are tested with fixtures only; they have not run in a live DayZ session yet.</p>'),
# agents table
("('<code>figma-node-normalizer</code>, <code>figma-to-dayz-layout</code>, <code>dayz-layout-validator</code>', 'Optional: turn a Figma frame into a checked .layout.'",
 "('<code>figma-node-normalizer</code>, <code>figma-to-dayz-layout</code>, <code>dayz-layout-validator</code>', 'Optional: turn a Figma frame into a .layout; the validator checks it without editing.'"),
("('<code>dayz-build-engineer</code>', 'Builds the PBO and starts a test session for you.'",
 "('<code>dayz-build-engineer</code>', 'Builds the PBO (or deploys a prebuilt bundle) and starts a test session for you.'"),
# trouble
("('Mod does not load in game',",
 "('<code>ERROR</code> from <code>/dayz-gate</code> asking for <code>--deps</code>', 'The mod\\'s config.cpp needs non-vanilla addons, such as CF.', 'Pass them: <code>/dayz-gate ingame &lt;ModName&gt; --deps CF</code>.'),\n('<code>FAIL</code> from <code>/dayz-lint</code> before a build', 'An error that would stop the mod loading.', 'Fix the <code>file:line</code> it names; each finding names its owner.'),\n('Mod does not load in game',"),
# faq
("RAG search needs a Voyage AI key; a full index build embeds about 66M tokens, so check Voyage pricing.",
 "RAG search needs a Voyage AI key; the last full index build embedded about 66M tokens, and the current indexer makes more chunks, so check Voyage pricing."),
("The reviewer and debugger cannot edit files; the layout validator edits only in cleanup mode, when you ask it to repair a file.",
 "The mod reviewer, layout validator, build checker, in-game tester and debugger cannot edit files."),
# safety
("<li>Every agent has an explicit tool list. The reviewer and debugger cannot edit files.</li>",
 "<li>Every agent has an explicit tool list. The five gates (mod reviewer, layout validator, build checker, in-game tester and debugger) cannot edit files, and no agent has network tools.</li>"),
# folders
("  output\\\\                     plans and other one-off deliverables",
 "  .server\\\\!Health\\\\&lt;ModName&gt;\\\\   stored gate results for /dayz-health\n  output\\\\&lt;ModName&gt;-plan\\\\       the plan, behavior checks and visual shots\n  output\\\\&lt;ModName&gt;-release\\\\    release pack and server kit\n  output\\\\                     other one-off deliverables"),
# settings
("        ('<code>TYPESAFE_API_KEY</code>', 'Turns on Jev in /dayz-route.'),",
 "        ('<code>VOYAGE_FREE_TIER_TOKENS</code>', 'Your Voyage token budget, when your plan differs from the default the indexer warns against.'),\n        ('<code>DAYZ_RAG_MAX_DISTANCE</code>', 'Default distance cutoff for search hits (unset by default).'),\n        ('<code>TYPESAFE_API_KEY</code>', 'Turns on Jev in /dayz-route.'),"),
]
for a, b in R:
    assert s.count(a) == 1, a[:90]
    s = s.replace(a, b)
p.write_text(s, encoding='utf-8')
print('patched', len(R))
