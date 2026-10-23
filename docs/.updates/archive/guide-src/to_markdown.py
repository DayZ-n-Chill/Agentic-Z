"""Write the guide and team pages as Markdown for review before any PDF build."""
import pathlib, re
from markdownify import markdownify

here = pathlib.Path(__file__).parent
out = here.parent
for src, dst in (('agentic-z-guide.html', 'Agentic-Z Guide.md'), ('agentic-z-team.html', 'Agentic-Z Agent Team.md')):
    t = (here / src).read_text(encoding='utf-8')
    t = re.sub(r'<(style|script|svg)\b.*?</\1>', '', t, flags=re.S)
    t = re.sub(r'<div class="chart".*?</div>', '*[diagram]*', t, flags=re.S)
    md = markdownify(t, heading_style='ATX', bullets='-')
    md = re.sub(r'\n{3,}', '\n\n', md).strip() + '\n'
    (out / dst).write_text(md, encoding='utf-8')
    print(dst, len(md.split()), 'words')
