<script>
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
</script>
