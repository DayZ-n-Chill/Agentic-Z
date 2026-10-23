import json, pathlib
here = pathlib.Path(__file__).parent
p = here / 'agentic-z-team.html'

# Counts come from the grade files at build time; clean-repo was graded twice and counts once.
rows = {}
for f in ('final_grades.json', 'final_grades_shared.json'):
    for g in json.loads((here / f).read_text(encoding='utf-8')):
        rows[(g['batch'].split('-')[0], g['item'])] = g['grade']
count = {}
for (grp, _), grade in rows.items():
    a, n = count.get(grp, (0, 0))
    count[grp] = (a + (grade == 'A+'), n + 1)
TOTAL = len(rows)
APLUS = sum(v == 'A+' for v in rows.values())
t = p.read_text(encoding='utf-8')
s = t.index('<section aria-labelledby="h-method">')
e = t.index('</section>', s) + len('</section>')

new = '''<section aria-labelledby="h-method">
 <h2 id="h-method">Grading method</h2>
 <p>Every agent, skill and shared file is graded by AI reviewers, not by the author, against Anthropic's published best practices for Claude Code. Each reviewer is a Claude instance started fresh for the job: it sees the files, the rubric and the standards, never the earlier grades or the author's opinion. This is not an official Anthropic rating; it is a repeatable review that anyone can rerun with the prompts under "Reproducing the review".</p>

 <h3>Current counts</h3>
 <p>The grades cover @TOTAL@ items on <code>origin/develop</code>. @APLUS@ of them are at A+: @AG_A@ of the @AG_N@ agents, @SK_A@ of the @SK_N@ skills and @SH_A@ of the @SH_N@ shared items (hooks, the search server, the panel, scripts and wrappers, answer tests, rules files, knowledge packs and this method note). Each item shows its latest grade. The grades come from <code>final_grades.json</code> and <code>final_grades_shared.json</code>; <code>clean-repo</code> is graded in two batches and counts once.</p>

 <h3>Reviewers</h3>
 <ul>
  <li><b>Independent reviewers.</b> Every review starts new Claude reviewers with no memory of earlier reviews. A full review uses six: two for the agents, three for the skills, and one for everything shared (the hooks, the search server, the panel, the scripts and wrappers, the answer tests, the rules files, the knowledge packs and this note). The few shared files that are not graded are listed under "Limits".</li>
  <li><b>Read only.</b> Reviewers cannot edit files. They read every file, run the tests where the session allows it, and check claims against the code and the vanilla DayZ files on the P: drive. A reviewer whose session does not allow pytest says so in its reasons.</li>
  <li><b>Separate fixers.</b> Other agents fix the findings, each owning its own files. A fixer never grades its own work.</li>
  <li><b>Regrade.</b> New reviewers grade every fixed item again. An item counts as A+ only when an independent reviewer gives it A+.</li>
 </ul>

 <h3>Standards</h3>
 <ul>
  <li><b>Anthropic's standards:</b> the Claude Code subagent documentation (code.claude.com/docs/en/sub-agents), the Agent Skills best practices (docs.claude.com/en/docs/agents-and-tools/agent-skills/best-practices), the Claude Code hooks reference (code.claude.com/docs/en/hooks) and plugins reference (code.claude.com/docs/en/plugins-reference), and for the search server, the Model Context Protocol tool guidance.</li>
  <li><b>Agentic-Z's own rules:</b> <code>CLAUDE.md</code> (Tier 1), the DayZ rules file and its topic files (Tier 2), the agent standard in <code>agent-creator.md</code>, and <code>docs/prompt-conventions.md</code>.</li>
  <li><b>The real game:</b> DayZ facts are checked against the vanilla files on P: (for example which file holds CfgSurfaces, which texture suffixes exist, which widget classes can be a layout's root). Six Enforce Script worked examples (01, 04, 05, 06, 08 and 09) are marked as vendored and not checked on P:.</li>
 </ul>

 <h3>Rubric: agents and skills</h3>
 <div class="tbl"><table>
  <thead><tr><th scope="col">For agents</th><th scope="col">For skills</th></tr></thead>
  <tbody>
   <tr><td><b>Description:</b> a precise third person contract saying what it does and when to use it, with a realistic example and valid YAML.</td><td><b>Frontmatter:</b> the name matches the folder; the description says what it does and when to use it, in the third person, kept short.</td></tr>
   <tr><td><b>Tools:</b> only what the role needs, and everything the instructions ask it to do. Read only roles cannot edit.</td><td><b>Instructions:</b> concise, accurate to the code (every claim and sample output checked against the script), with a clear "how to run".</td></tr>
   <tr><td><b>Body:</b> lean and specific, pointing at shared rules instead of repeating them, capital letter rules used sparingly.</td><td><b>Script:</b> readable, clear error messages, non zero exit on failure, no dead code, shared helpers reused, the environment check run first where the rules require.</td></tr>
   <tr><td><b>Correct and consistent:</b> every path, skill, agent and tool it names exists and is used correctly; no contradiction with the rules or the team flow; DayZ facts verified.</td><td><b>Tests:</b> exist, cover the risky logic, and pass.</td></tr>
   <tr><td><b>Handoffs:</b> says what it returns and to whom.</td><td><b>Safety:</b> anything destructive is guarded with a backup, a dry run or a confirmation.</td></tr>
  </tbody>
 </table></div>

 <h3>Rubric: shared items</h3>
 <p>The @SH_N@ shared items are not agents or skills, so each kind is judged by what it is:</p>
 <div class="tbl"><table>
  <thead><tr><th scope="col">Kind of item</th><th scope="col">What the reviewer checks</th></tr></thead>
  <tbody>
   <tr><th scope="row">Hooks</th><td>The output JSON is correct for the hook event, a bug in the hook never blocks the session, the plugin and clone wiring match, and tests feed the hook input through stdin.</td></tr>
   <tr><th scope="row">Search server</th><td>Every tool carries read only annotations, tool descriptions are clear, errors come back as <code>isError</code> results, and tests cover the tools.</td></tr>
   <tr><th scope="row">Panel plugin</th><td>The plugin manifest and hook wiring follow the plugins reference, and its own tests pass.</td></tr>
   <tr><th scope="row">Rules files</th><td>Every rule is true of the code, nothing repeats another tier, and every path and skill named exists.</td></tr>
   <tr><th scope="row">Knowledge packs</th><td>Game facts cite a P: file and line or are marked as unverified, the cited lines hold when opened on P:, and nothing contradicts the checked references.</td></tr>
   <tr><th scope="row">Scripts, wrappers and repo tests</th><td>The tests run and pass, the documentation and help text match the code, and failures exit non zero with a clear message.</td></tr>
   <tr><th scope="row">Answer tests (evals)</th><td>The cases test what the agent is for, the runner and baselines match, and a change can only keep or raise a score.</td></tr>
   <tr><th scope="row">This method note</th><td>It states the rubric for every kind of item, the grade scale and the grading prompts, and every count, source and claim in it matches the repo and the grade files.</td></tr>
  </tbody>
 </table></div>

 <h3>Grade scale</h3>
 <div class="tbl"><table>
  <thead><tr><th scope="col">Grade</th><th scope="col">Meaning</th></tr></thead>
  <tbody>
   <tr><th scope="row"><span class="pill ok">A+</span></th><td>Ship it unchanged as an example of best practice. The reviewer found nothing concrete to fix.</td></tr>
   <tr><th scope="row"><span class="pill keep">A, A-</span></th><td>Very good, with one or two concrete defects a user could hit.</td></tr>
   <tr><th scope="row"><span class="pill warn">B+ to B-</span></th><td>Works, but has real gaps: claims that don't match the code, missing tests, unclear handoffs.</td></tr>
   <tr><th scope="row"><span class="pill fix">C+ to D</span></th><td>Wrong or risky in ways a user will hit, or built on an approach that can't reach A.</td></tr>
  </tbody>
 </table></div>
 <p>Every grade below A+ must name the concrete defect and the exact fix. Style preferences alone cannot lower a grade.</p>

 <h3>Reproducing the review</h3>
 <p>Start a fresh Claude Code session in the repo and give it one of these four prompts. For agents:</p>
 <pre><code>Read-only grading task. Do not edit files. Be strict and independent; you have
not seen earlier grades. Grade every file in .claude/agents/*.md against
Anthropic's current Claude Code subagent standards and the repo's agent standard
in .claude/agents/agent-creator.md: precise third-person description with an
example; minimal tools that cover the body; lean body with references over
inlining; every path, skill, agent and DayZ fact correct and consistent with
CLAUDE.md, .claude/skills/_shared/dayz-conventions.md and the team flow; a Report
naming its recipient. Scale A+ to D. A+ means nothing concrete left to fix. For
anything lower, name a concrete defect a user would actually hit.
Output a table: Agent | Grade | Why | To reach A+.</code></pre>
 <p>For skills:</p>
 <pre><code>Read-only grading task. Do not edit files. Be strict and independent; you have
not seen earlier grades. Grade every skill in .claude/skills/*/ (SKILL.md, its
scripts and its tests) against Anthropic's Agent Skills best practices and the
repo's rules: name matches the folder; third-person description of what it does
and when to use it; instructions accurate to the script; readable script with
clear errors and non-zero exit on failure; preflight first where the rules
require; tests that cover the risky logic and pass; destructive steps guarded
by a backup, dry run or confirmation. Run py -m pytest -q on the skill's tests.
Scale A+ to D. A+ means nothing concrete left to fix. For anything lower, name a
concrete defect a user would actually hit.
Output a table: Skill | Grade | Why | To reach A+.</code></pre>
 <p>For everything else:</p>
 <pre><code>Read-only grading task. Do not edit files. Be strict and independent; you have
not seen earlier grades. Grade every hook in hooks/, the MCP server in
.claude/mcp/dayz-rag/, the panel plugin in mods/agentic-z-panel/, every wrapper
in scripts/, the answer tests in evals/, the rules files and every knowledge
pack under .claude/skills/_shared/. Hooks: correct output JSON for the event,
never block on their own bug, tests through stdin. MCP server: read-only
annotations, clear tool descriptions, errors returned as isError, tests. Panel:
follows the plugins reference, its tests pass. Rules files: every rule true of
the code. Knowledge packs: game facts cite a P: file and line or are marked
unverified, and the cited lines hold (open them on P:). Scripts and answer
tests: tests run, documentation matches the code. Run
py -m pytest -q .claude scripts/dev hooks. Scale A+ to D. A+ means nothing
concrete left to fix. For anything lower, name a concrete defect a user would
actually hit. Output a table: Item | Grade | Why | To reach A+.</code></pre>
 <p>For this method note:</p>
 <pre><code>Read-only grading task. Do not edit files. Be strict and independent; you have
not seen earlier grades. Grade the "Grading method" section of the
Agentic-Z agent team guide. Check that it states who grades, the rubric for
every kind of item graded (agents, skills, hooks, search server, panel, rules
files, knowledge packs, scripts, answer tests and this note), the grade scale,
and the grading prompt for every kind; and that every count matches
final_grades.json and final_grades_shared.json. Scale A+ to D. A+ means
nothing concrete left to fix. For anything lower, name a concrete defect a
reader would actually hit.
Output a table: Item | Grade | Why | To reach A+.</code></pre>
 <p class="example">Because each reviewer is new, two runs can word findings differently, and a stricter reviewer can find a new edge case.</p>
</section>'''

for k, v in {'@TOTAL@': TOTAL, '@APLUS@': APLUS,
             '@AG_A@': count['agents'][0], '@AG_N@': count['agents'][1],
             '@SK_A@': count['skills'][0], '@SK_N@': count['skills'][1],
             '@SH_A@': count['shared'][0], '@SH_N@': count['shared'][1]}.items():
    new = new.replace(k, str(v))
assert '@' not in new.replace('&#64;', ''), 'unfilled placeholder'
t = t[:s] + new + t[e:]
p.write_text(t, encoding='utf-8')
print('ok')
