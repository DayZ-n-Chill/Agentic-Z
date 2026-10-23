import pathlib, re, pymupdf
here = pathlib.Path(__file__).parent.parent
out = here / 'ref' / 'check'
out.mkdir(exist_ok=True)
terms = ['fixed', 'now ', 'no longer', 'used to', 'since 1.', 'PR #', 'round']
for name, tag in (('Agentic-Z Guide.pdf', 'guide'), ('Agentic-Z Agent Team.pdf', 'team')):
    doc = pymupdf.open(here / name)
    print('==', name, doc.page_count, 'pages')
    heads = {}
    for i, page in enumerate(doc):
        text = page.get_text()
        for term in terms:
            for m in re.finditer(re.escape(term), text, re.I):
                ctx = text[max(0, m.start() - 70):m.end() + 50].replace('\n', ' ')
                print('  p%d [%s] %s' % (i + 1, term, ctx))
        for h in ('Current grades', 'Grading method', 'Limits', 'Versions', 'Quality', 'Domain specialists'):
            if h in text and h not in heads:
                heads[h] = i
    print('  sections:', heads)
    pages = sorted({1} | {v for v in heads.values()})
    for i in pages:
        doc[i].get_pixmap(dpi=70).save(out / ('current-%s-p%02d.png' % (tag, i + 1)))
    print('  rendered', [p + 1 for p in pages])
