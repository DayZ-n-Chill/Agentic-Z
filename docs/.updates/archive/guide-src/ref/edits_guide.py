_src = open(__file__.replace('edits_guide.py', '../make_guide.py'), encoding='utf-8').read()
_addons = _src[_src.index('addons = """<section aria-labelledby="g-addons">'):_src.index('def grab(html, sid):')]
_grab = _src[_src.index('def grab(html, sid):'):_src.index('quality = """<section aria-labelledby="g-quality">')]

EDITS = [
    ('<td>The Tier 2 rules were one 239-line file. They are now a 143-line core plus five topic files of 24 to 56 lines (see "Rule tiers"). Most skills read only the core, 40%% less; <code>/dayz-deploy-pbo</code> and <code>/dayz-gate</code> also point to the bundle mods section of <code>conventions/config.md</code>. Agents read the core plus the topic files their job needs:<ul><li>One topic file: 17%% to 30%% less than before.</li><li>Two topic files: <code>dayz-mod-debugger</code> (226 lines) and <code>dayz-mod-architect</code> (231 lines) read slightly less; the vehicle, weapon and audio and FX specialists (251 lines) read more.</li><li>Three topic files: <code>dayz-mod-reviewer</code> (283 lines) reads more.</li></ul></td>',
     '<td>The Tier 2 rules are a 143-line core plus five topic files of 24 to 56 lines (see "Rule tiers"). Most skills read only the core; <code>/dayz-deploy-pbo</code> and <code>/dayz-gate</code> also point to the bundle mods section of <code>conventions/config.md</code>. Agents read the core plus the topic files their job needs, up to 283 lines for <code>dayz-mod-reviewer</code>, which reads three.</td>'),
    ('<p class="example">The existing specialists were extended too: a full Enforce Script reference,',
     '<p class="example">The workers have matching references: a full Enforce Script reference,'),
    (_addons, '''versions = """<section aria-labelledby="g-versions">
 <h2 id="g-versions">Versions</h2>
 <p>Version 2.0.0 follows 1.6.0; there is no 1.7.0 or 1.8.0. The release notes are in <code>docs/release-notes/</code>.</p>
 <div class="tbl"><table><thead><tr><th scope="col">Version</th><th scope="col">Contents</th></tr></thead><tbody>
  <tr><th scope="row">1.6.0 (<code>main</code>)</th><td>14 agents and 29 skills (25 DayZ): the workers, reviewer and debugger, the Figma-to-DayZ pipeline, and the <code>dayz-rag</code> search server with source and wiki search.</td></tr>
  <tr><th scope="row">2.0.0 (<code>develop</code>)</th><td>30 agents and 44 skills (40 DayZ): the orchestrator, leads and router, eight domain specialists with knowledge packs, script gates, hooks, the token-saving layer, the side panel, answer tests and CI. Search covers vanilla source only.</td></tr>
 </tbody></table></div>
</section>
"""

'''),
    (_grab, '''# The team chart's heading would clash with the guide's own "Architecture" section.
chart = re.sub(r'id="h-chart">[^<]*</h2>', 'id="h-chart">Team structure</h2>', chart)

'''),
    ('<p>Every agent, skill and shared file was graded by independent Claude reviewers against the code on <code>develop</code>, fixed and regraded until no reviewer found a defect.</p>',
     '<p>Every agent, skill and shared file is graded by independent Claude reviewers against the code on <code>develop</code>. A fixer never grades its own work, and an item counts as A+ only when a fresh reviewer finds nothing concrete to fix.</p>'),
    ('<p>The grading method, every grade with its reason, and the defects grading found are in the <b>Agentic-Z Agent Team</b> document.</p>',
     '<p>The <b>Agentic-Z Agent Team</b> document has the grading method and the current grade of every item.</p>'),
    ('The behavior and visual gates are tested with fixtures only and have not run in a live DayZ session yet.</p>',
     'The behavior and visual gates are tested with fixtures only and have not run in a live DayZ session.</p>'),
    ('savers + coming + spec_flows + workflows + addons + quality, skills, packs,',
     'savers + coming + spec_flows + workflows + quality + versions, skills, packs,'),
]
