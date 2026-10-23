"""Build the two Agentic-Z PDFs from their Markdown sources.

Book-style print layout: a cover, a contents page with real page numbers,
then continuous flow. Chapters do not force page breaks (that leaves empty
half pages); instead headings are kept with the content under them, tables
split between rows with the header repeated, and figures are never cut.
Run: py build_pdfs.py   (needs Chrome, python-markdown and pymupdf)
"""
import html
import pathlib
import re
import subprocess
import sys

import markdown
import pymupdf

HERE = pathlib.Path(__file__).resolve().parent
DOCS = HERE.parent
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
DATE = "October 2026"
DOCS_TO_BUILD = [
    ("Agentic-Z Guide.md", "User Guide"),
    ("Agentic-Z Agent Team.md", "Agent Team Design"),
]

CSS = (HERE / "book.css").read_text(encoding="utf-8")


def clean_markdown(md: str) -> str:
    lines = md.splitlines()
    # Drop anything before the H1 (a stray title line exported above it).
    start = next(i for i, l in enumerate(lines) if l.startswith("# "))
    lines = lines[start:]
    out, fence = [], False
    for line in lines:
        if line.startswith("```"):
            fence = not fence
        elif not fence:
            # Angle-bracket placeholders outside code spans are text, not HTML.
            parts = re.split(r"(`[^`]*`)", line)
            line = "".join(p if p.startswith("`") else re.sub(r"<(?=[A-Za-z/])", "&lt;", p) for p in parts)
            # Every heading and image needs a blank line above it to parse as a block.
            if (line.startswith("#") or line.startswith("![")) and out and out[-1].strip():
                out.append("")
        out.append(line)
    return "\n".join(out) + "\n"


def to_html(md: str, subtitle: str, toc_pages: dict) -> tuple[str, str]:
    body = markdown.markdown(
        md, extensions=["tables", "fenced_code", "toc", "sane_lists"],
        extension_configs={"toc": {"toc_depth": "2-3"}},
    )
    # The toc extension numbers duplicate ids in document order, so a small h4 can
    # take the plain id a chapter heading links to. Give the plain id to the h2/h3.
    for hid in re.findall(r'<h4 id="([^"]+)"', body):
        if f'id="{hid}_1"' in body and re.search(rf'<h[23] id="{hid}_1"', body):
            body = body.replace(f'<h4 id="{hid}"', f'<h4 id="{hid}_h4"', 1)
            body = re.sub(rf'<h([23]) id="{hid}_1"', rf'<h id="{hid}"', body, count=1)
    title = re.search(r"<h1[^>]*>(.*?)</h1>", body).group(1)
    body = re.sub(r"<h1[^>]*>.*?</h1>\s*", "", body, count=1)
    # The opening paragraph becomes the cover summary.
    lede = re.search(r"<p>(.*?)</p>\s*", body, re.S)
    body = body[:lede.start()] + body[lede.end():]

    # Replace the Markdown contents list with a dotted-leader contents page.
    m = re.search(r'<h2 id="contents">Contents</h2>\s*(<ul>.*?</ul>)\s*(?=<h2)', body, re.S)
    toc_items = re.findall(r'<li><a href="#([^"]+)">(.*?)</a>(\s*<ul>)?', m.group(1))
    rows = []
    # Top-level entries are the h2 ids; the rest are h3.
    h2_ids = set(re.findall(r'<h2 id="([^"]+)"', body))
    for anchor, text, _ in toc_items:
        lvl = "l1" if anchor in h2_ids else "l2"
        page = toc_pages.get(anchor, "")
        rows.append(f'<li class="{lvl}"><a href="#{anchor}"><span class="t">{text}</span>'
                    f'<span class="dots"></span><span class="p">{page}</span></a></li>')
    toc = '<section class="toc"><h2 class="toc-h">Contents</h2><ol>' + "".join(rows) + "</ol></section>"
    body = body[:m.start()] + body[m.end():]

    # Table polish: group rows ("**Agents** | | ") span the full width.
    def group_row(mm):
        cells = re.findall(r"<td[^>]*>(.*?)</td>", mm.group(0), re.S)
        if len(cells) > 1 and re.fullmatch(r"<strong>.*</strong>", cells[0].strip()) and not any(c.strip() for c in cells[1:]):
            return f'<tr class="grp"><td colspan="{len(cells)}">{cells[0]}</td></tr>'
        return mm.group(0)
    body = re.sub(r"<tr>\s*(<td.*?</td>\s*)+</tr>", group_row, body, flags=re.S)
    # Tables whose header cell is an agent name are spec cards.
    body = re.sub(r"<table>(\s*<thead>\s*<tr>\s*<th[^>]*><code>)", r'<table class="card">\1', body)
    # Name tables by column count so widths can be tuned.
    def tag_cols(mm):
        n = len(re.findall(r"<th", mm.group(0).split("</thead>")[0]))
        t = mm.group(0)
        return t.replace("<table", f'<table data-cols="{n}"', 1)
    body = re.sub(r"<table.*?</table>", tag_cols, body, flags=re.S)
    # Figures: image plus caption from its alt text.
    body = re.sub(r'<p><img alt="([^"]*)" src="([^"]+)" ?/?></p>',
                  lambda mm: f'<figure><img src="{mm.group(2)}" alt="{mm.group(1)}">'
                             + (f"<figcaption>{mm.group(1)}</figcaption>" if mm.group(1) != "Diagram" else "")
                             + "</figure>", body)
    # Keep a heading and the first block under it together by wrapping them.
    body = re.sub(r"(<h[234][^>]*>.*?</h[234]>)\s*(<p>.*?</p>)", r'<div class="keep">\1\2</div>', body, flags=re.S)

    cover = (f'<section class="cover"><div class="brand">Agentic-Z</div>'
             f'<h1>{title}</h1><div class="sub">{subtitle}</div><div class="rule"></div>'
             f'<p class="lede">{lede.group(1)}</p>'
             f'<div class="meta">Version 2.0.0 &nbsp;&middot;&nbsp; {DATE}<br>DayZ n\' Chill &nbsp;&middot;&nbsp; github.com/DayZ-n-Chill/Agentic-Z</div></section>')
    page = (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{title}</title>'
            f'<base href="{DOCS.as_uri()}/"><style>{CSS}</style></head><body>'
            f'{cover}{toc}<main>{body}</main></body></html>')
    return page, html.unescape(re.sub("<[^>]+>", "", title))


def print_pdf(page: str, out: pathlib.Path):
    src = HERE / "tmp" / (out.stem + ".html")
    src.parent.mkdir(exist_ok=True)
    src.write_text(page, encoding="utf-8")
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    f"--user-data-dir={HERE / 'tmp' / 'chrome'}", "--virtual-time-budget=5000",
                    f"--print-to-pdf={out}", src.as_uri()], check=True, capture_output=True)


def heading_pages(pdf: pathlib.Path, anchors: list) -> dict:
    """Read the contents-page links in order; each one points at its heading's page."""
    doc = pymupdf.open(pdf)
    names = doc.resolve_names()
    return {a: names[a]["page"] + 1 for a in anchors}


def finish(pdf: pathlib.Path, title: str, md_html: str, pages: dict):
    doc = pymupdf.open(pdf)
    font = pymupdf.Font("helv")
    for i, p in enumerate(doc):
        if i == 0:
            continue
        w, h = p.rect.width, p.rect.height
        p.draw_line((54, h - 40), (w - 54, h - 40), color=(0.80, 0.82, 0.86), width=0.5)
        p.insert_text((54, h - 27), f"Agentic-Z  |  {title}", fontsize=7.5, fontname="helv", color=(0.42, 0.46, 0.52))
        num = str(i + 1)
        p.insert_text((w - 54 - font.text_length(num, 7.5), h - 27), num, fontsize=7.5, fontname="helv", color=(0.42, 0.46, 0.52))
    # PDF bookmarks from the headings, so readers can jump by section.
    outline = [[1, "Contents", 2]]
    for lvl, anchor, text in re.findall(r'<h([23]) id="([^"]+)">(.*?)</h[23]>', md_html):
        if anchor in pages:
            outline.append([int(lvl) - 1, html.unescape(re.sub("<[^>]+>", "", text)), pages[anchor]])
    doc.set_toc(outline)
    doc.set_metadata({"title": f"Agentic-Z {title}", "author": "DayZ n' Chill"})
    tmp = pdf.with_suffix(".tmp.pdf")
    doc.save(tmp, garbage=3, deflate=True)
    doc.close()
    tmp.replace(pdf)


def main():
    for md_name, subtitle in DOCS_TO_BUILD:
        md = clean_markdown((DOCS / md_name).read_text(encoding="utf-8"))
        out = DOCS / md_name.replace(".md", ".pdf")
        page, _ = to_html(md, subtitle, {})
        print_pdf(page, out)
        anchors = re.findall(r'<li class="l\d"><a href="#([^"]+)"', page)
        pages = heading_pages(out, anchors)  # second pass fills contents page numbers
        page, _ = to_html(md, subtitle, pages)
        print_pdf(page, out)
        finish(out, subtitle, page, pages)
        print(out.name, pymupdf.open(out).page_count, "pages")


if __name__ == "__main__":
    sys.exit(main())
