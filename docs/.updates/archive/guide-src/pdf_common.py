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
.wrap>*+*{margin-top:32px}
section{display:block}
section>*+*{margin-top:12px}
section>:is(.chart,.tbl,pre,.specs,ul,ol)+:not(.foot){margin-top:24px}
section>h3:not(:first-child){margin-top:32px}
section>.chart+.foot{margin-top:8px}
h1{font-size:30px}
.lede{font-size:14px}
.chart{border:1px solid var(--rule);padding:12px;background:var(--surface)}
.chart svg{min-width:0;width:100%;margin:0 auto}
.wrap>header>*+*{margin-top:8px}
/* Keep every block whole; only a table taller than a page splits, between rows, with its header repeated */
.tbl,table,tr,.chart,pre,.sg,.specs,ul,ol,ol.steps li,.legend,.status-key,figure{break-inside:avoid}
thead{display:table-header-group}
h2,h3,tr.grp,.legend,.status-key{break-after:avoid}
/* An intro line stays with the block it introduces */
section>p:has(+:is(.tbl,.chart,pre,.specs,ul,ol)){break-after:avoid}
section>h2+p{break-after:avoid}
/* Paragraphs stay whole, and a caption or follow-up line stays with the block above it */
p{break-inside:avoid}
section>:is(.chart,ul)+p{break-before:avoid}
/* The script below places every page break itself; a block that starts a page has no top margin */
.pdf-pg{break-before:page!important;margin-top:0!important}
/* A non-table block taller than a page (marked by the script) may split */
.pdf-tall{break-inside:auto}
/* Lay the screen pass out at the printed content width so the script measures real heights */
@media screen{html{width:725px}}
.tbl{overflow:visible}
.specs{grid-template-columns:repeat(3,1fr);gap:12px}
.sg{break-inside:avoid}
table{min-width:0;font-size:12px}
th,td{padding:8px 12px}
.foot,.status-key{font-size:11px}
.legend{font-size:11.5px;gap:6px 14px}
code{font-family:var(--mono);font-size:.92em}
.pdf-head{display:flex;justify-content:space-between;align-items:baseline;border-bottom:2px solid var(--accent);padding-bottom:8px;font-family:var(--mono);font-size:10px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
__EXTRA__
</style><script>
/* Print pagination, run on the screen pass at the printed width. It walks the
   blocks in order, fills each page, and adds explicit page breaks itself:
   a block or keep-together chain that fits moves whole to the next page, and
   only a table taller than a page splits, into separate cards (one per page)
   with the header repeated, at least 3 rows per part, never ending a part on a
   group header, and between groups when the group fits on one page. */
addEventListener('load',()=>document.fonts.ready.then(()=>{
 const PH=926, wrap=document.querySelector('.wrap'), log=[];
 const vis=e=>getComputedStyle(e).display!=='none';
 const els=[];
 for(const t of wrap.children){if(!vis(t))continue;if(t.tagName==='SECTION'){for(const c of t.children)if(vis(c))els.push(c)}else els.push(t)}
 let prev=null;
 const B=els.map(el=>{const r=el.getBoundingClientRect(),cs=getComputedStyle(el);
  const b={el,h:r.height,gap:prev===null?0:r.top-prev,forced:cs.breakBefore==='page',keepNext:cs.breakAfter==='avoid',keepPrev:cs.breakBefore==='avoid'};
  prev=r.bottom;
  const tb=el.matches('.tbl')&&el.querySelector('table');
  if(tb&&b.h>PH){const th=tb.tHead;b.tbl=tb;b.theadH=th?th.getBoundingClientRect().height:0;
   b.rows=[...tb.querySelectorAll(':scope>tbody>tr')].map(tr=>({el:tr,h:tr.getBoundingClientRect().height,grp:tr.classList.contains('grp')}));
   b.frame=b.h-b.theadH-b.rows.reduce((s,x)=>s+x.h,0)}
  return b});
 const units=[];
 B.forEach((b,i)=>{if(i&&!b.forced&&(B[i-1].keepNext||b.keepPrev))units[units.length-1].push(b);else units.push([b])});
 let y=0;
 const pg=el=>{const s=el.parentElement;(s.tagName==='SECTION'&&s.firstElementChild===el?s:el).classList.add('pdf-pg')};
 const H=u=>u.reduce((s,b,i)=>s+(i?b.gap:0)+b.h,0);
 const sum=(r,a,z)=>{let s=0;for(let i=a;i<z;i++)s+=r[i].h;return s};
 const data=(r,a,z)=>{let n=0;for(let i=a;i<z;i++)if(!r[i].grp)n++;return n};
 function choose(T,s,space){
  const r=T.rows,n=r.length,ok=[];
  for(let k=s+1;k<n;k++){if(sum(r,s,k)>space)break;
   if(!r[k-1].grp&&data(r,s,k)>=3&&data(r,k,n)>=3)ok.push(k)}
  if(!ok.length)return -1;
  const kmax=ok[ok.length-1];
  if(r[kmax].grp)return kmax;
  let gs=kmax-1;while(gs>s&&!r[gs].grp)gs--;
  let ge=kmax;while(ge<n&&!r[ge].grp)ge++;
  // Break before the group when the whole group fits on one page and the page stays at least half full
  if(r[gs].grp&&gs>s&&ok.includes(gs)&&T.frame+T.theadH+sum(r,gs,ge)<=PH&&sum(r,s,gs)>=space/2)return gs;
  return kmax}
 function split(u,ti){
  const T=u[ti],pre=u.slice(0,ti),post=u.slice(ti+1),r=T.rows,n=r.length;
  const preH=pre.length?H(pre)+T.gap:0,postH=post.length?H(post)+post[0].gap:0;
  const first=u[0];
  if(first.forced&&y>0){pg(first.el);y=0}
  let used=(y>0?first.gap:0)+y+preH;
  const parts=[];let s=0;
  for(;;){
   const space=PH-used-T.frame-T.theadH;
   if(sum(r,s,n)+postH<=space){parts.push([s,n]);y=used+T.frame+T.theadH+sum(r,s,n)+postH;break}
   let k=choose(T,s,space);
   if(k<0&&!parts.length&&y>0){pg(first.el);y=0;used=preH;continue}
   if(k<0){k=s+1;while(k<n-1&&sum(r,s,k+1)<=space)k++;log.push('forced split '+k)}
   parts.push([s,k]);s=k;used=0;y=0}
  if(parts.length<2)return;
  // Fix the column widths so every part lines up with the first
  const tb=T.tbl,row=[...tb.rows].find(x=>!x.querySelector('[colspan]'));
  const cg=document.createElement('colgroup');
  for(const c of row.cells){const col=document.createElement('col');col.style.width=c.getBoundingClientRect().width+'px';cg.append(col)}
  tb.querySelectorAll(':scope>colgroup').forEach(c=>c.remove());
  tb.prepend(cg);tb.style.tableLayout='fixed';
  let after=T.el;
  for(const [a,z] of parts.slice(1)){
   const d=T.el.cloneNode(false),t=tb.cloneNode(false);
   t.append(cg.cloneNode(true));if(tb.tHead)t.append(tb.tHead.cloneNode(true));
   const body=document.createElement('tbody');for(let i=a;i<z;i++)body.append(r[i].el);
   t.append(body);d.append(t);d.classList.add('pdf-pg');after.after(d);after=d}
  log.push('split '+(tb.closest('section')?.getAttribute('aria-labelledby'))+' '+parts.map(p=>p.join('-')).join(','))}
 function place(u){
  const first=u[0],h=H(u);
  if(first.forced&&y>0){pg(first.el);y=0}
  const g=y>0?first.gap:0;
  if(y+g+h<=PH){y+=g+h;return}
  const ti=u.findIndex(b=>b.rows);
  if(ti>=0)return split(u,ti);
  if(h>PH&&u.length>1){let j=1;for(let i=1;i<u.length;i++)if(u[i].h>u[j].h)j=i;place(u.slice(0,j));place(u.slice(j));return}
  if(y>0)pg(first.el);
  if(h>PH){first.el.classList.add('pdf-tall');log.push('tall '+first.el.tagName+' '+Math.round(h));y=h%PH}else y=h}
 units.forEach(place);
 document.documentElement.dataset.pager=log.join(' | ');
}));
</script>"""

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
        y = r.height - 9 * 72 / 25.4  # baseline centered in the 18 mm bottom margin
        x0 = 12 * 72 / 25.4
        page.insert_text((x0, y), FOOTER, fontsize=7.5, fontname="helv", color=MUTED)
        num = f"{i + 1} / {total}"
        w = pymupdf.get_text_length(num, fontname="helv", fontsize=7.5)
        page.insert_text((r.width - x0 - w, y), num, fontsize=7.5, fontname="helv", color=MUTED)
    pdf = here / pdf_name
    doc.save(pdf, garbage=3, deflate=True)
    print(pdf, total, "pages", pdf.stat().st_size)
