import pymupdf, sys, pathlib
here = pathlib.Path(__file__).resolve().parents[2]
out = here / "ref" / "check"
for f, tag in [("Agentic-Z Guide.pdf", "guide"), ("Agentic-Z Agent Team.pdf", "team")]:
    d = pymupdf.open(here / f)
    hits = {}
    for i, p in enumerate(d):
        t = p.get_text()
        for k, name in [("SPECIALIST PACKS", "packs"), ("Imagesets (a section", "packs"), ("Where the new specialists", "newspec"),
                        ("Released. First graded", "versions"), ("You (the user)", "flowchart"), ("SKILL", "table")]:
            if k in t and name not in hits: hits[name] = i
    hits["cover"] = 0; hits["p2"] = 1
    print(tag, d.page_count, hits)
    for name, i in hits.items():
        d[i].get_pixmap(dpi=70).save(out / f"{tag}-{name}-p{i+1}.png")
