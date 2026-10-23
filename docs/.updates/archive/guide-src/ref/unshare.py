"""Replace 'shared' labels in the guide sources with neutral terms.
Leaves code paths such as _shared/ and identifiers alone."""
import pathlib, re

here = pathlib.Path(__file__).resolve().parent.parent
pairs = [
    ('shared knowledge packs', 'knowledge packs'),
    ('Shared knowledge packs', 'Knowledge packs'),
    ('the shared DayZ playbook', 'the DayZ playbook'),
    ('Shared playbook', 'DayZ playbook'),
    ('shared playbook', 'DayZ playbook'),
    ('the shared template', 'the standard template'),
    ('pointing at shared rules', 'pointing at the rules files'),
    ('shared helpers reused', 'common helpers reused'),
    ('Rules and shared files', 'Rules and core files'),
    ('everything shared (', 'everything else ('),
    ('Rubric: shared items', 'Rubric: core items'),
    ('The 90 shared items', 'The 90 core items'),
    ('The few shared files', 'The few core files'),
    ('shared items', 'core items'),
    ('shared files', 'core files'),
    ('shared file', 'core file'),
    ('Shared by all:', 'Any team:'),
    ('Shared items', 'Core items'),
    ('Shared files', 'Core files'),
]
files = ['make_guide.py', 'agentic-z-team.html', 'method_section.py', 'add_final_grades.py']
for name in files:
    p = here / name
    t = p.read_text(encoding='utf-8')
    n0 = t
    for a, b in pairs:
        # skip occurrences inside code paths like _shared/
        t = re.sub(r'(?<![_/\w])' + re.escape(a), b, t)
    if t != n0:
        p.write_text(t, encoding='utf-8')
        print(name, 'updated')
