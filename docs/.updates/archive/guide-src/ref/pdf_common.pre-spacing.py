"""Shared PDF build for the guide and team pages: dark print CSS, a cover page
printed on its own, then pymupdf merges them, fills the page margins dark and
stamps the private footer with page numbers on every inside page."""
import pathlib, subprocess
import pymupdf

here = pathlib.Path(__file__).parent
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
BG = (0x12 / 255, 0x14 / 255, 0x19 / 255)
RED = (1, 0x6b / 255, 0x6b / 255)
MUTED = (0xa9 / 255, 0xb0 / 255, 0xbb / 255)
FOOTER = "Agentic-Z · DayZ n' Chill · github.com/DayZ-n-Chill/Agentic-Z"

BASE_CSS = """<style>
@page{size:Letter;margin:14mm 12mm 18mm;background:#121419}
html,body{background:#121419!important;-webkit-print-color-adjust:exact;print-color-adjust:exact}
body{font-size:12.5px;margin:0}
p{max-width:92ch}
.cover{display:none}
.wrap{max-width:none;padding:0;display:block}
.wrap>*+*{margin-top:26px}
section{display:block}
section>*+*{margin-top:12px}
h1{font-size:30px}
.lede{font-size:14px}
.chart{border:1px solid var(--rule);padding:8px;background:var(--surface)}
.chart svg{min-width:0;width:100%;margin:0 auto}
.wrap>header>*+*{margin-top:6px}
.sg,ol.steps li,tr{break-inside:avoid}
h2,h3,tr.grp{break-after:avoid}
.tbl{overflow:visible}
.specs{grid-template-columns:repeat(3,1fr);gap:12px}
.sg{break-inside:avoid}
table{min-width:0;font-size:12px}
th,td{padding:6px 10px}
.foot{font-size:11px}
code{font-family:var(--mono);font-size:.92em}
.pdf-head{display:flex;justify-content:space-between;align-items:baseline;border-bottom:2px solid var(--accent);padding-bottom:8px;font-family:var(--mono);font-size:10px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
__EXTRA__
</style>"""

COVER_CSS = """<style>
@page{size:Letter;margin:0;background:#121419}
html,body{margin:0;background:#121419;-webkit-print-color-adjust:exact;print-color-adjust:exact}
.cover{height:100vh;min-height:0;padding:30mm 22mm 34mm}
.cover h1.cover-title{font-size:96px}
.cover-sub{font-size:30px}
.cover-desc{font-size:15px}
.cover-foot{font-size:10px}
</style>"""


def chrome_pdf(html_path, pdf_path):
    subprocess.run([CHROME, "--headless=new", "--disable-gpu",
        f"--user-data-dir={here / 'chrome-tmp'}", "--no-pdf-header-footer", "--virtual-time-budget=8000",
        f"--print-to-pdf={pdf_path}", html_path.as_uri()], check=True, timeout=180)


def build(src_name, stem, pdf_name, head_right, extra_css):
    body = (here / src_name).read_text(encoding="utf-8")
    # Title, fonts and every <style> block of the page (the guide adds a second one)
    styles = body[:body.index('<div class="wrap">')]
    cover = body[body.index('<section class="cover"'):]
    cover = cover[:cover.index("</section>") + len("</section>")]

    # Inside pages
    html = '<!doctype html><html><head><meta charset="utf-8">' + body.replace(
        "</style>", "</style>" + BASE_CSS.replace("__EXTRA__", extra_css), 1).replace(
        '<div class="wrap">',
        '<div class="wrap"><div class="pdf-head"><span>Agentic-Z &middot; DayZ n\' Chill</span><span>%s</span></div>' % head_right, 1) + "</html>"
    out_html = here / f"{stem}-print.html"
    out_html.write_text(html, encoding="utf-8")

    # Cover page
    cover_html = here / f"{stem}-cover-print.html"
    cover_html.write_text('<!doctype html><html><head><meta charset="utf-8">' + styles + COVER_CSS +
                          '</head><body>' + cover + '</body></html>', encoding="utf-8")

    tmp_body = here / "chrome-tmp" / f"{stem}-body.pdf"
    tmp_cover = here / "chrome-tmp" / f"{stem}-cover.pdf"
    chrome_pdf(out_html, tmp_body)
    chrome_pdf(cover_html, tmp_cover)

    doc = pymupdf.open(tmp_cover)
    while doc.page_count > 1:
        doc.delete_page(-1)
    doc.insert_pdf(pymupdf.open(tmp_body))
    total = doc.page_count
    for i, page in enumerate(doc):
        r = page.rect
        page.draw_rect(r, color=None, fill=BG, overlay=False)
        if i == 0:
            continue
        y = r.height - 8 * 72 / 25.4
        x0 = 12 * 72 / 25.4
        page.insert_text((x0, y), FOOTER, fontsize=7.5, fontname="helv", color=MUTED)
        num = f"{i + 1} / {total}"
        w = pymupdf.get_text_length(num, fontname="helv", fontsize=7.5)
        page.insert_text((r.width - x0 - w, y), num, fontsize=7.5, fontname="helv", color=MUTED)
    pdf = here / pdf_name
    doc.save(pdf, garbage=3, deflate=True)
    print(pdf, total, "pages", pdf.stat().st_size)
