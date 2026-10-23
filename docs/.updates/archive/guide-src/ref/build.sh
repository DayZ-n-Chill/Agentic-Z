set -e
cd "H:/Projects/Agentic-Z/docs/.updates/guide-src"
py method_section.py && py add_final_grades.py && py make_guide.py && py make_guide_pdf.py && py make_pdf.py
for f in agentic-z-guide-print.html agentic-z-team-print.html; do "/c/Program Files/Google/Chrome/Application/chrome.exe" --headless=new --disable-gpu --user-data-dir="$(pwd -W)/chrome-tmp" --virtual-time-budget=8000 --dump-dom "file:///$(pwd -W)/$f" 2>/dev/null | grep -o 'data-pager="[^"]*"'; done
py -c "
import pymupdf,pathlib
o=pathlib.Path('ref/final2');o.mkdir(exist_ok=True)
for f in o.glob('*.png'): f.unlink()
s=pathlib.Path('ref/f2sheet');s.mkdir(exist_ok=True)
for f in s.glob('*.png'): f.unlink()
for n,t in (('Agentic-Z Guide.pdf','g'),('Agentic-Z Agent Team.pdf','t')):
    d=pymupdf.open(n); print(n,d.page_count)
    for i,p in enumerate(d): p.get_pixmap(dpi=90).save(f'ref/final2/{t}{i+1:02d}.png')
"
py ref/sheet.py ref/final2 ref/f2sheet 6
