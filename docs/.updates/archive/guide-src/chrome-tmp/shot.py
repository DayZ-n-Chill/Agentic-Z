"""Temporary screenshot helper: full-page shot of a guide-src page, cropped to sections.
Usage: py chrome-tmp/shot.py <page.html> <tag> <id> [<id> ...]   (id 'cover' = the cover)"""
import json, pathlib, re, subprocess, sys
from PIL import Image

here = pathlib.Path(__file__).resolve().parent.parent
tmp = here / "chrome-tmp"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
W = 1280
src, tag, ids = sys.argv[1], sys.argv[2], sys.argv[3:]
html = (here / src).read_text(encoding="utf-8")
# Cover uses 100vh; pin it to one screen so a tall window doesn't stretch it
probe = """<script>addEventListener('load',()=>{const o={H:document.documentElement.scrollHeight};
document.querySelectorAll('h2[id],section.cover').forEach(h=>{const s=h.closest('section')||h;const r=s.getBoundingClientRect();
o[h.id||'cover']=[r.top+scrollY,r.bottom+scrollY]});const p=document.createElement('pre');p.id='POS';p.textContent=JSON.stringify(o);document.body.appendChild(p)})</script>"""
fix = "<style>.cover{min-height:900px!important;height:900px}</style>"
shot = tmp / f"_shot_{tag}.html"
shot.write_text(html + fix + probe, encoding="utf-8")
common = [CHROME, "--headless=new", "--disable-gpu", f"--user-data-dir={tmp}", "--hide-scrollbars", "--virtual-time-budget=5000"]
dom = subprocess.run(common + [f"--window-size={W},900", "--dump-dom", shot.as_uri()], capture_output=True, text=True, encoding="utf-8", timeout=120).stdout
pos = json.loads(re.search(r'<pre id="POS">(.*?)</pre>', dom, re.S).group(1).replace("&quot;", '"'))
H = int(pos["H"]) + 40
full = tmp / f"_full_{tag}.png"
subprocess.run(common + [f"--window-size={W},{H}", f"--screenshot={full}", shot.as_uri()], check=True, timeout=180, capture_output=True)
img = Image.open(full)
out = here / "ref" / "check"
for i in ids:
    a, b = pos[i]
    img.crop((0, max(0, int(a) - 24), W, min(img.height, int(b) + 24))).save(out / f"spacing-{tag}-{i}.png")
    print(i, int(a), int(b))
print("height", H)
