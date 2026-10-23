EDITS = [
    # Cover and lede
    ('work together as one DayZ modding team, and how every part was graded by independent reviewers.</p>',
     'work together as one DayZ modding team, and how every part is graded by independent reviewers.</p>'),
    ('three hooks and the <code>dayz-rag</code> MCP search server, all graded by independent reviewers. It is on <code>develop</code> and not yet released to <code>main</code>.',
     'three hooks and the <code>dayz-rag</code> MCP search server, each graded by independent reviewers. Version 2.0.0 is on <code>develop</code>; <code>main</code> carries 1.6.0.'),
    # Components
    ('server and Workbench, plus eight specialists added in 2.0.0. See "Agents".',
     'server and Workbench, plus eight domain specialists. See "Agents".'),
    # Verification status
    ('<p>Checked against <code>origin/develop</code> on October 22, 2026. Version 2.0.0 was set in commit <code>e70cf1a</code> (PR #119); the results below are for the head of <code>develop</code>, commit <code>2902f83</code> (PR #144).</p>',
     '<p>Checked against <code>origin/develop</code> at commit <code>2902f83</code> (version 2.0.0) on October 22, 2026.</p>'),
    ('<span><span class="pill todo">Not run yet</span> built, waiting for a real DayZ session</span>',
     '<span><span class="pill todo">Not run live</span> tested without a real DayZ session</span>'),
    ('<td>The <code>tests</code> workflow passed on the last three pushes to <code>develop</code>, the newest being the merge of PR #144, the last grading fix.</td>',
     '<td>The <code>tests</code> workflow passes on <code>develop</code> at commit <code>2902f83</code>. It runs on every pull request and every push to <code>develop</code> and <code>main</code>.</td>'),
    ('The seven without are listed in "Open items".</td>',
     'The seven without are listed in "Limits".</td>'),
    ('Six Enforce Script examples are still marked as vendored and not checked.</td>',
     'Six Enforce Script examples are marked as vendored and not checked.</td>'),
    ('<td>The index on disk is the August 10, 2026 build (52,048 chunks). The search timeout fix ships in 2.0.0, which is not yet released. Needs a Voyage API key in <code>.env</code> and a full re-index to pick up class windowing.</td>',
     '<td>Needs a Voyage API key in <code>.env</code> and an index built by <code>/dayz-search-index</code> with class windowing, which indexes large script classes in full. The index on disk is the August 10, 2026 build (52,048 chunks), which predates class windowing.</td>'),
    ('<tr><th scope="row">Orchestrator, leads and gates in a real session</th><td><span class="pill todo">Not run yet</span></td><td>Nothing in this build has run against a real DayZ session. The first real test is building one small mod end to end.</td></tr>',
     '<tr><th scope="row">Orchestrator, leads and gates in a real session</th><td><span class="pill todo">Not run live</span></td><td>Tested with scripts and fixtures only; not run against a real DayZ session.</td></tr>'),
    ('<tr><th scope="row">Behavior and visual gates</th><td><span class="pill todo">Not run yet</span></td><td>Tested with fixtures only. The test mission and the window capture have never run in a live session.</td></tr>',
     '<tr><th scope="row">Behavior and visual gates</th><td><span class="pill todo">Not run live</span></td><td>Tested with fixtures only. The test mission and the window capture have not run in a live session.</td></tr>'),
    # Token savers
    ('<h2 id="h-roadmap">Token savers, workflows and roadmap</h2>\n <p>All token savers and workflows below are built, tested and on <code>develop</code>. None has run in a live DayZ session yet.</p>',
     '<h2 id="h-roadmap">Token savers and workflows</h2>\n <p>All token savers and workflows below are built and tested. None has run in a live DayZ session.</p>'),
    ('<tr><th scope="row">Shorter descriptions</th><td>About 2,100 tokens less loaded into every session.</td></tr>',
     '<tr><th scope="row">Short descriptions</th><td>Agent and skill descriptions are kept short, since every session loads them.</td></tr>'),
    # Agents
    ('all shipped in the plugin. "New" means added since 1.6.0; "Moved" means the role changed. Agents with no model',
     'all shipped in the plugin. Agents with no model'),
    ('<th scope="col">Role</th><th scope="col">Since 1.6.0</th></tr>',
     '<th scope="col">Role</th></tr>'),
    ('<th colspan="3" scope="colgroup">Specialists (added in 2.0.0)</th>',
     '<th colspan="3" scope="colgroup">Specialists</th>'),
    ('client-only audio and particle effects (with the existing <code>/dayz-particles</code> skill).',
     'client-only audio and particle effects (with the <code>/dayz-particles</code> skill).'),
    # Skills and packs
    ('each with its reason. Some of them still read P::', 'each with its reason. Some of them read P::'),
    ('<li><b>Unchecked.</b> Six of the 13 worked examples (01, 04, 05, 06, 08 and 09) are still marked as vendored and not checked on P:.</li>',
     '<li><b>Unchecked.</b> Six of the 13 worked examples (01, 04, 05, 06, 08 and 09) are marked as vendored and not checked on P:.</li>'),
]

SUBS = [
    # Agents table: drop the "Since 1.6.0" column
    ('h-agents', r'<td><span class="pill \w+">\w+</span></td></tr>', '</tr>'),
    ('h-agents', r'colspan="3"', 'colspan="2"'),
    # Token savers: rules loading as it is, no before and after
    ('h-roadmap', r'(?s)<tr><th scope="row">Smaller rules loading</th><td>.*?</td></tr>',
     '<tr><th scope="row">Small rules loading</th><td>Tier 2 is a 143-line core and five topic files of 24 to 56 lines. Most skills read only the core; <code>/dayz-deploy-pbo</code> and <code>/dayz-gate</code> also point to the bundle mods section of the config topic file. Each agent reads the core plus the topic files its job needs, up to 283 lines for <code>dayz-mod-reviewer</code>, which reads three.</td></tr>'),
    # Roadmap list
    ('h-roadmap', r'(?s)\n <h3>Roadmap</h3>\n <p>.*?</p>\n <ol class="steps">.*?</ol>', ''),
    # Specialists section
    ('h-growth', r'<h2 id="h-growth">Specialist expansion \(2\.0\.0\)</h2>\n <p>.*?</p>',
     '<h2 id="h-growth">Domain specialists</h2>\n <p>Eight specialist agents, each with its own knowledge pack, work under the team leads alongside the workers, and <code>/dayz-lint</code> runs inside the build gate. Every fact in the packs is checked against the vanilla files on P: and written fresh; nothing is copied from other mods.</p>'),
    ('h-growth', r'<rect class="tag"[^>]*/><text class="tag-t"[^>]*>NEW</text>', ''),
    ('h-growth', r' \(NEW\)', ''),
    ('h-growth', r'<text class="s" x="570" y="48">unchanged</text>', '<text class="s" x="570" y="48">plans and tracks the mod</text>'),
    ('h-growth', r'(?s)\n <h3>Build order</h3>\n <ol class="steps">.*?</ol>', ''),
    ('h-growth', r'<h3>Specialist build cycle</h3>',
     '<h3>Knowledge verification cycle</h3>\n <p>Each specialist and its pack go through the same cycle: research, a reference written in Agentic-Z\'s own words, a check of every fact against P: by a separate agent, answer tests, wiring into the lead, router and reviewer, and independent grading.</p>'),
    ('h-growth', r'(?s)\n <h3>Scope decisions</h3>\n <div class="tbl">.*?</div>', ''),
    ('h-growth', r'<p class="example">In-game testing of the specialists is part of the live DayZ checks in "Open items"\.</p>',
     '<p class="example">The specialists have not run in a live DayZ session; see "Limits".</p>'),
]

SECTIONS = {
    'h-bugs': '',
    'h-open': '''<section aria-labelledby="h-open">
 <h2 id="h-open">Limits</h2>
 <ul>
  <li><b>Live DayZ session.</b> Nothing in 2.0.0 has run against a real DayZ session: not the team loop, the in-game, behavior or visual gates, or the panel's launch buttons. The behavior and visual gates are tested with fixtures only.</li>
  <li><b>Published version.</b> Version 2.0.0 is on <code>develop</code>; <code>main</code> carries 1.6.0.</li>
  <li><b>Answer tests.</b> 23 of the 30 agents have them. <code>dayz-build-checker</code>, <code>dayz-ingame-tester</code>, <code>dayz-mod-architect</code>, <code>dayz-lead</code>, <code>dayz-orchestrator</code>, <code>dayz-router</code> and <code>figma-to-dayz-layout</code> have no question file.</li>
  <li><b>Files not graded.</b> Nine answer test files, <code>expansion_style.md</code>, <code>examples/layouts.md</code> and the nine <code>enscript-style/</code> section files.</li>
  <li><b>Unchecked examples.</b> Six of the 13 Enforce Script worked examples are marked as vendored and not checked on P:.</li>
  <li><b>Preflight exceptions.</b> The DayZ rules file has 14 exception entries naming 21 skills that skip the preflight gate; <code>docs/dayz-modding.md</code> lists five of them.</li>
 </ul>
</section>''',
    'h-fix': '''<section aria-labelledby="h-fix">
 <h2 id="h-fix">Versions</h2>
 <p>What each published version of the <code>agentic-z</code> plugin contains, from <code>plugin.json</code> and <code>docs/release-notes/</code>. Version 2.0.0 follows 1.6.0; there is no 1.7.0 or 1.8.0.</p>
 <div class="tbl"><table>
  <thead><tr><th scope="col">Version</th><th scope="col">Agents</th><th scope="col">Skills</th><th scope="col">Contents</th></tr></thead>
  <tbody>
   <tr><th scope="row">1.6.0 (<code>main</code>, tag <code>v1.6.0</code>)</th><td>14</td><td>29, of which 25 DayZ skills</td><td>Workers for script, config, models, textures, UI, maps, server and Workbench; <code>dayz-mod-reviewer</code> and <code>dayz-mod-debugger</code>; <code>agent-creator</code>; the Figma-to-DayZ pipeline (<code>figma-node-normalizer</code>, <code>figma-to-dayz-layout</code>, <code>dayz-layout-validator</code>) and its rules file; the <code>dayz-rag</code> search server with vanilla source search and wiki search.</td></tr>
   <tr><th scope="row">2.0.0 (<code>develop</code>)</th><td>30</td><td>44, of which 40 DayZ skills in the plugin</td><td>The orchestrator, architect, team leads and router; eight domain specialists with knowledge packs; the build, in-game, behavior and visual gates as scripts, with log triage; the edit check, scope guard and paste-in hooks; the token-saving layer and a <code>.bat</code> wrapper for every runnable skill; the <code>agentic-z-panel</code> 0.3.0 side panel; answer tests and CI. The search server covers vanilla DayZ source only.</td></tr>
  </tbody>
 </table></div>
</section>''',
}
