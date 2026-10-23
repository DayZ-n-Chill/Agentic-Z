import re
_src = open(__file__.replace('edits_method.py', '../method_section.py'), encoding='utf-8').read()
_rounds = _src[_src.index(' <h3>Rounds</h3>'):_src.index(' <h3>Reproducing the review</h3>')]
_counts = _src[_src.index(' <h3>Final counts</h3>'):_src.index(' <h3>Reviewers</h3>')]
_reviewers = _src[_src.index(' <h3>Reviewers</h3>'):_src.index(' <h3>Standards</h3>')]
_noteprompt = _src[_src.index('Grade the "Grading method" section of the'):_src.index('Output a table: Item | Grade | Why | To reach A+.</code></pre>\n <p class="example">')]

EDITS = [
    (_rounds, ''),
    (_counts, ''' <h3>Current counts</h3>
 <p>The grades cover @TOTAL@ items on <code>origin/develop</code>. @APLUS@ of them are at A+: @AG_A@ of the @AG_N@ agents, @SK_A@ of the @SK_N@ skills and @SH_A@ of the @SH_N@ shared items (hooks, the search server, the panel, scripts and wrappers, answer tests, rules files, knowledge packs and this method note). Each item shows its latest grade. The grades come from <code>final_grades.json</code> and <code>final_grades_shared.json</code>; <code>clean-repo</code> is graded in two batches and counts once.</p>

'''),
    (_reviewers, ''' <h3>Reviewers</h3>
 <ul>
  <li><b>Independent reviewers.</b> Every review starts new Claude reviewers with no memory of earlier reviews. A full review uses six: two for the agents, three for the skills, and one for everything shared (the hooks, the search server, the panel, the scripts and wrappers, the answer tests, the rules files, the knowledge packs and this note). The few shared files that are not graded are listed under "Limits".</li>
  <li><b>Read only.</b> Reviewers cannot edit files. They read every file, run the tests where the session allows it, and check claims against the code and the vanilla DayZ files on the P: drive. A reviewer whose session does not allow pytest says so in its reasons.</li>
  <li><b>Separate fixers.</b> Other agents fix the findings, each owning its own files. A fixer never grades its own work.</li>
  <li><b>Regrade.</b> New reviewers grade every fixed item again. An item counts as A+ only when an independent reviewer gives it A+.</li>
 </ul>

'''),
    ('Six Enforce Script worked examples (01, 04, 05, 06, 08 and 09) are still marked as vendored and not checked on P:.',
     'Six Enforce Script worked examples (01, 04, 05, 06, 08 and 09) are marked as vendored and not checked on P:.'),
    ('<td>It states the rubric for every kind of item and the grading prompts, gives one row per round with its PRs, and every count, source and claim in it matches the repo and the grade files.</td>',
     '<td>It states the rubric for every kind of item, the grade scale and the grading prompts, and every count, source and claim in it matches the repo and the grade files.</td>'),
    (_noteprompt, '''Grade the "Grading method" section of the
Agentic-Z agent team guide. Check that it states who grades, the rubric for
every kind of item graded (agents, skills, hooks, search server, panel, rules
files, knowledge packs, scripts, answer tests and this note), the grade scale,
and the grading prompt for every kind; and that every count matches
final_grades.json and final_grades_shared.json. Scale A+ to D. A+ means
nothing concrete left to fix. For anything lower, name a concrete defect a
reader would actually hit.
'''),
    ('a stricter reviewer can find a new edge case. Every round found real defects; they are listed in "Defects found by grading".</p>',
     'a stricter reviewer can find a new edge case.</p>'),
]
