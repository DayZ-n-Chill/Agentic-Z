"""Page audit: blank space at the bottom of each page, stranded headings, and contact sheets."""
import pathlib, sys
import pymupdf
HERE = pathlib.Path(__file__).parent
for name in sys.argv[1:]:
    doc = pymupdf.open(HERE.parent / name)
    tag = name[:-4].split()[-1].lower()
    out = HERE / "tmp" / "pages"; out.mkdir(parents=True, exist_ok=True)
    for f in out.glob(f"{tag}*.png"): f.unlink()
    print(f"== {name}: {doc.page_count} pages")
    for i, page in enumerate(doc):
        if i < 2: continue
        H = page.rect.height
        bottom_limit = H - 0.85 * 72
        blocks = [b for b in page.get_text("dict")["blocks"] if b["bbox"][3] < bottom_limit + 4]
        draws = [d["rect"].y1 for d in page.get_drawings() if d["rect"].y1 < bottom_limit + 4]
        imgs = [r.y1 for r in (page.get_image_rects(x[0])[0] for x in page.get_images()) ] if page.get_images() else []
        last = max([b["bbox"][3] for b in blocks] + draws + imgs + [0])
        free = (bottom_limit - last) / (bottom_limit - 54)
        # Last text line on page: is it a heading?
        lines = [(l["bbox"][3], s) for b in blocks if b["type"] == 0 for l in b["lines"] for s in l["spans"][:1] if s["text"].strip()]
        lines.sort(key=lambda x: x[0])
        flag = []
        if free > 0.18 and i != doc.page_count - 1: flag.append(f"blank {free:.0%}")
        if lines:
            tail = lines[-1][1]
            if "Segoe" in tail["font"] and "Semibold" in tail["font"] and tail["size"] >= 11: flag.append(f"heading at bottom: {tail['text'][:40]!r}")
        if flag: print(f"  p{i+1}: " + "; ".join(flag))
    for i, page in enumerate(doc):
        page.get_pixmap(dpi=60).save(out / f"{tag}{i+1:02d}.png")
