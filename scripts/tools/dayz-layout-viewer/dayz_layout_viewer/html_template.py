"""Self-contained HTML shell for the layout preview.

This is a structural approximation. It is not the Enfusion widget rasterizer.
"""

TEMPLATE = r"""<!doctype html>
<html><head><meta charset="utf-8"><title>__TITLE__ -- DayZ layout preview (v2)</title>
<style>
:root{--bg:#15171c;--panel:#1e2129;--edge:#333a46;--ink:#dfe4ec;--dim:#8a93a3;--accent:#4a90d9;--warn:#e0a33a;--bad:#d9534a;--bind:#8e5cd0;}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:13px/1.4 "Segoe UI",Roboto,Arial,sans-serif}
#bar{position:sticky;top:0;z-index:50;display:flex;flex-wrap:wrap;gap:10px;align-items:center;padding:8px 12px;background:var(--panel);border-bottom:1px solid var(--edge)}
#bar b{color:#fff} .sep{width:1px;height:20px;background:var(--edge)}
label.tog{display:inline-flex;gap:5px;align-items:center;cursor:pointer;color:var(--dim)}
select,button{background:#262a34;color:var(--ink);border:1px solid var(--edge);border-radius:4px;padding:4px 8px;font:inherit;cursor:pointer}
#warnpill{color:var(--warn)}
#wrap{padding:18px;display:flex;gap:18px;align-items:flex-start}
#stageOuter{background:#0c0d10;border:1px solid var(--edge);border-radius:6px;overflow:hidden;position:relative;box-shadow:0 0 0 1px #000 inset}
#stage{position:relative;transform-origin:top left;background:repeating-conic-gradient(#0f1013 0% 25%,#121317 0% 50%) 0/40px 40px}
.w{position:absolute;overflow:visible}
.w.clip{overflow:hidden}
.w>.lbl{position:absolute;left:0;top:-13px;font-size:9px;line-height:11px;color:var(--dim);white-space:nowrap;pointer-events:none;opacity:0;background:#000a;padding:0 3px;border-radius:2px}
body.labels .w:hover>.lbl{opacity:1;z-index:9}
.txt{width:100%;height:100%;display:flex;overflow:hidden}
.txt>span{width:100%}
.ph{position:absolute;inset:0;background-image:repeating-linear-gradient(45deg,#2a2f3a 0 6px,#20242d 6px 12px);opacity:.5}
.badge{position:absolute;top:1px;right:1px;font-size:8px;line-height:10px;padding:0 3px;border-radius:2px;color:#000;pointer-events:none}
.b-assumed{background:var(--warn)} .b-unknown{background:var(--bad);color:#fff} .b-spacer{background:#3aa0a0;color:#001}
.b-bind{position:absolute;left:1px;bottom:1px;background:var(--bind);color:#fff;font-size:8px;line-height:10px;padding:0 3px;border-radius:2px;pointer-events:none}
body.debug .w{outline:1px dashed #ffffff22}
body.debug .w[data-render="1"]{outline:1px dashed #4a90d966}
.hidden-w{display:none}
body.showhidden .hidden-w{display:block;opacity:.32;outline:1px dotted var(--bad)}
#side{width:320px;flex:0 0 320px;position:sticky;top:56px}
#side .card{background:var(--panel);border:1px solid var(--edge);border-radius:6px;padding:10px 12px;margin-bottom:12px}
#side h3{margin:0 0 6px;font-size:12px;color:var(--dim);text-transform:uppercase;letter-spacing:.5px}
#info{font-size:12px;white-space:pre-wrap;color:var(--ink);min-height:60px}
#diag{max-height:200px;overflow:auto;font-size:11px}
#diag .d{color:var(--warn);padding:2px 0;border-bottom:1px solid #ffffff0f}
.note{color:var(--dim);font-size:11px}
kbd{background:#0c0d10;border:1px solid var(--edge);border-radius:3px;padding:0 4px;font-size:11px}
</style></head>
<body class="labels">
<div id="bar">
  <b>DayZ layout preview</b><span id="src" class="note"></span>
  <span class="sep"></span>
  <label class="note">Resolution <select id="vp"></select></label>
  <label class="note">Fit <select id="fit"><option value="fit">fit width</option><option value="1">100%</option><option value="0.75">75%</option><option value="0.5">50%</option></select></label>
  <span class="sep"></span>
  <label class="tog"><input type="checkbox" id="tHidden"> show hidden</label>
  <label class="tog"><input type="checkbox" id="tDebug"> outlines</label>
  <label class="tog"><input type="checkbox" id="tLabels" checked> labels</label>
  <span class="sep"></span>
  <span id="warnpill"></span>
</div>
<div id="wrap">
  <div id="stageOuter"><div id="stage"></div></div>
  <div id="side">
    <div class="card"><h3>Hover a widget</h3><div id="info">Move the mouse over the preview.</div></div>
    <div class="card"><h3>Approximation -- trust in-game for</h3>
      <div class="note">- pixel colors (many set via script <kbd>SetColor</kbd>)<br>- fonts (Metron bitmap atlases; here approximated)<br>- PAA/EDDS textures (shown hatched)<br>- spacer auto-layout (Grid/Wrap/Scroll; shows authored values)<br>- anchors marked <span style="color:var(--warn)">assumed</span> (phase-1)</div>
    </div>
    <div class="card"><h3>Parser diagnostics (<span id="dn">0</span>)</h3><div id="diag"></div></div>
  </div>
</div>
<script>
var VIEWPORTS = /*__VIEWPORTS_JSON__*/;
var stage=document.getElementById('stage'), stageOuter=document.getElementById('stageOuter');
var info=document.getElementById('info'), vpSel=document.getElementById('vp'), fitSel=document.getElementById('fit');
document.getElementById('src').textContent = VIEWPORTS[0].doc.source.path;
VIEWPORTS.forEach(function(v,i){var o=document.createElement('option');o.value=i;o.textContent=v.label;vpSel.appendChild(o);});

function fontFamilyFor(f){f=(f||'').toLowerCase();return f.indexOf('7segment')>=0?'"Courier New",monospace':'"Bahnschrift","Roboto Condensed","Arial Narrow",sans-serif';}
function fontWeightFor(f){f=(f||'').toLowerCase();if(f.indexOf('bold')>=0||f.indexOf('black')>=0||f==='gui/fonts/metron')return 700;if(f.indexOf('light')>=0)return 300;return 400;}
function first(a){return Array.isArray(a)?a[0]:a;}
function attrNum(at,k,d){var v=first(at[k]);return v==null?d:Number(v);}
function attrStr(at,k,d){var v=first(at[k]);return v==null?d:String(v);}
function rgbaFromColorAttr(v){if(!v||v.length<3)return null;var r=Number(v[0]),g=Number(v[1]),b=Number(v[2]),a=v.length>3?Number(v[3]):1;return 'rgba('+Math.round(r*255)+','+Math.round(g*255)+','+Math.round(b*255)+','+a+')';}
function rgbaFromProcedural(s){var m=/color\(([^)]+)\)/i.exec(s||'');if(!m)return null;var p=m[1].split(',').map(function(x){return parseFloat(x);});if(p.length<3)return null;var a=p.length>3?p[3]:1;return 'rgba('+Math.round(p[0]*255)+','+Math.round(p[1]*255)+','+Math.round(p[2]*255)+','+a+')';}
var HALIGN={center:'center',right:'flex-end',left:'flex-start','1':'center','2':'flex-end','0':'flex-start'};
var VALIGN={center:'center',bottom:'flex-end',top:'flex-start','1':'center','2':'flex-end','0':'flex-start'};
var NONVIS={FrameWidgetClass:1,PanelWidgetClass:1,ScrollWidgetClass:1,GridSpacerWidgetClass:1,WrapSpacerWidgetClass:1,CanvasWidgetClass:1,SpacerWidgetClass:1};
var SPACER={GridSpacerWidgetClass:1,WrapSpacerWidgetClass:1,ScrollWidgetClass:1,SpacerWidgetClass:1};

function widgetEl(node){
  var g=node.geometry; if(!g) return null;
  var el=document.createElement('div');
  el.className='w'+(g.clipChildren?' clip':'')+(g.visible?'':' hidden-w');
  el.style.left=g.position.x+'px'; el.style.top=g.position.y+'px';
  el.style.width=g.size.width+'px'; el.style.height=g.size.height+'px';
  var at=node.attrs||{};
  var cls=node['class']; var isSpacer=!!SPACER[cls];
  el.dataset.render = (!NONVIS[cls])?'1':'0';
  var bg=rgbaFromColorAttr(at.color);
  var img=attrStr(at,'image0','')||attrStr(at,'imageTexture','');
  if(!bg && img && img.charAt(0)==='#') bg=rgbaFromProcedural(img);
  if(bg){el.style.background=bg;}
  else if(img && img.length){var ph=document.createElement('div');ph.className='ph';el.appendChild(ph);}
  else if(NONVIS[cls]){el.style.outline='1px solid #ffffff14';}
  if(g.alpha!=null){el.style.opacity=g.alpha;}
  var textRaw=attrStr(at,'text','');
  if(cls==='TextWidgetClass'||cls==='RichTextWidgetClass'||cls==='MultilineTextWidgetClass'||cls==='ButtonWidgetClass'||cls==='EditBoxWidgetClass'){
    var t=document.createElement('div');t.className='txt';
    t.style.justifyContent=HALIGN[attrStr(at,'text halign','left')]||'flex-start';
    t.style.alignItems=VALIGN[attrStr(at,'text valign','center')]||'center';
    var span=document.createElement('span');
    var disp=textRaw; if(disp.indexOf('#STR_')===0||disp.indexOf('#str_')===0)disp='['+disp+']';
    if(!disp && node.bindingName) disp='{'+node.bindingName+'}';
    span.textContent=disp;
    var tp=attrNum(at,'text_proportion',null);
    var fs; if(tp!=null){fs=tp*g.size.height;} else {var fnt=attrStr(at,'font','');var m=/(\d+)$/.exec(fnt);fs=m?Number(m[1]):Math.min(g.size.height*0.6,26);}
    span.style.fontSize=Math.max(6,fs)+'px';
    span.style.fontFamily=fontFamilyFor(attrStr(at,'font',''));
    span.style.fontWeight=fontWeightFor(attrStr(at,'font',''));
    span.style.textAlign=(attrStr(at,'text halign','left').replace('_ref',''))||'left';
    span.style.whiteSpace=(attrNum(at,'wrap',1)===0)?'nowrap':'normal';
    span.style.overflow='hidden';
    if(!bg && cls==='ButtonWidgetClass') el.style.outline='1px solid #ffffff22';
    t.appendChild(span);el.appendChild(t);
  }
  if(g.status==='assumed'){var ba=document.createElement('div');ba.className='badge b-assumed';ba.textContent='≈';ba.title=(g.notes||[]).join(' | ');el.appendChild(ba);}
  else if(g.status==='unknown-anchor'){var bu=document.createElement('div');bu.className='badge b-unknown';bu.textContent='?';bu.title=(g.notes||[]).join(' | ');el.appendChild(bu);}
  if(isSpacer){var bs=document.createElement('div');bs.className='badge b-spacer';bs.textContent='⊞';bs.title='Spacer: children auto-laid-out by the engine in-game; preview shows AUTHORED child positions.';el.appendChild(bs);}
  if(node.bindingName){var bb=document.createElement('div');bb.className='b-bind';bb.textContent='→'+node.bindingName;el.appendChild(bb);}
  var lbl=document.createElement('div');lbl.className='lbl';lbl.textContent=cls.replace('WidgetClass','')+(node.name?(' · '+node.name):'');el.appendChild(lbl);
  el.addEventListener('mouseenter',function(ev){ev.stopPropagation();info.textContent=
    cls+(node.name?('  «'+node.name+'»'):'')+'\n'+
    'pos  '+g.position.x.toFixed(1)+', '+g.position.y.toFixed(1)+' px\n'+
    'size '+g.size.width.toFixed(1)+' x '+g.size.height.toFixed(1)+' px\n'+
    'flags h/v pos='+g.flags.hexactpos+'/'+g.flags.vexactpos+' size='+g.flags.hexactsize+'/'+g.flags.vexactsize+' (1=px,0=proportional)\n'+
    'anchor '+g.anchor.horizontal+' / '+g.anchor.vertical+'\n'+
    'visible='+g.visible+'  ignorePointer='+g.ignorePointer+'  status='+g.status+
    (node.bindingName?('\nbinding -> '+node.bindingName):'')+(node.relayCommand?('\nrelay -> '+node.relayCommand):'')+
    ((g.notes&&g.notes.length)?('\n'+g.notes.join('\n')):'');
  });
  for(var i=0;i<node.children.length;i++){var ce=widgetEl(node.children[i]); if(ce) el.appendChild(ce);}
  return el;
}

var curScale=1;
function render(){
  var idx=Number(vpSel.value); var V=VIEWPORTS[idx]; var doc=V.doc;
  stage.style.width=V.width+'px'; stage.style.height=V.height+'px';
  stage.innerHTML='';
  for(var i=0;i<doc.roots.length;i++){var e=widgetEl(doc.roots[i]); if(e) stage.appendChild(e);}
  var diag=document.getElementById('diag'); diag.innerHTML='';
  var ds=doc.diagnostics||[]; document.getElementById('dn').textContent=ds.length;
  ds.forEach(function(d){var x=document.createElement('div');x.className='d';x.textContent='L'+d.line+': '+d.message+' ('+d['class']+(d.name?(' '+d.name):'')+')';diag.appendChild(x);});
  document.getElementById('warnpill').textContent=ds.length?('⚠ '+ds.length+' parser warnings'):'';
  applyFit();
}
function applyFit(){
  var idx=Number(vpSel.value); var V=VIEWPORTS[idx];
  var mode=fitSel.value;
  if(mode==='fit'){var avail=stageOuter.parentElement.clientWidth - 340; curScale=Math.min(1,avail/V.width);}
  else curScale=Number(mode);
  stage.style.transform='scale('+curScale+')';
  stageOuter.style.width=(V.width*curScale)+'px'; stageOuter.style.height=(V.height*curScale)+'px';
}
vpSel.onchange=render; fitSel.onchange=applyFit; window.addEventListener('resize',applyFit);
document.getElementById('tHidden').onchange=function(e){document.body.classList.toggle('showhidden',e.target.checked);};
document.getElementById('tDebug').onchange=function(e){document.body.classList.toggle('debug',e.target.checked);};
document.getElementById('tLabels').onchange=function(e){document.body.classList.toggle('labels',e.target.checked);};
render();
</script></body></html>
"""
