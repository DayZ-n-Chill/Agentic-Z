"""Write paginated HTML of both documents (Paged.js) for capture into Figma."""
import pathlib
from build_pdfs import DOCS, DOCS_TO_BUILD, clean_markdown, to_html

OUT = pathlib.Path(__file__).parent / "figma"
OUT.mkdir(exist_ok=True)
SCREEN = """
@page { @bottom-left { content: "Agentic-Z  |  " string(doctitle); font: 7.5pt "Segoe UI", Arial, sans-serif; color: #6b7684; }
        @bottom-right { content: counter(page); font: 7.5pt "Segoe UI", Arial, sans-serif; color: #6b7684; } }
@page :first { @bottom-left { content: none; } @bottom-right { content: none; } }
.cover h1 { string-set: doctitle content(text); }
.toc .p::after { content: target-counter(attr(href url), page); }
@media screen {
  html, body { background: #e6e8ec; }
  .pagedjs_pages { display: flex; flex-direction: column; align-items: center; gap: 48px; padding: 48px 0; }
  .pagedjs_page { background: #fff; box-shadow: 0 1px 4px rgba(0,0,0,.18); }
}
"""
for md_name, subtitle in DOCS_TO_BUILD:
    page, _ = to_html(clean_markdown((DOCS / md_name).read_text(encoding="utf-8")), subtitle, {})
    page = page.replace(f'<base href="{DOCS.as_uri()}/">', '<base href="/">')
    page = page.replace('<span class="p"></span>', '').replace('<span class="dots"></span>', '<span class="dots"></span><span class="p" href="#"></span>')
    import re
    page = re.sub(r'<a href="(#[^"]+)"><span class="t">(.*?)</span><span class="dots"></span><span class="p" href="#"></span>',
                  r'<a href="\1"><span class="t">\2</span><span class="dots"></span><span class="p" href="\1"></span>', page)
    page = page.replace("</style>", SCREEN + "</style>", 1)
    page = page.replace("</head>", '<script src="https://unpkg.com/pagedjs@0.4.3/dist/paged.polyfill.js"></script>'
                        '<script src="https://mcp.figma.com/mcp/html-to-design/capture.js" async></script></head>')
    name = "guide.html" if "Guide" in md_name else "team.html"
    (OUT / name).write_text(page, encoding="utf-8")
    print(name, len(page))
