#!/usr/bin/env python3
"""
P3D Inspector - viewer generator.

Writes one HTML page from a Recipe JSON: the model flat shaded, the collision LODs
as wireframes, memory points as spheres that can be dragged, axis ends and the
box_placing corners that follow the drag, snap to grid, and an export of the edited
Recipe. Labels are plain HTML overlays and the bounding boxes are hand-built lines.

The page loads Three.js 0.185.1 as ES modules through an importmap from jsDelivr,
with OrbitControls, so opening it needs a network. The scaffold comes from
viewer_core.py, which ships with the 3D viewer tool.

Usage:
  python p3d_inspector_viewer.py <recipe.json> [output.html]
  python p3d_inspector_viewer.py --demo [output.html]

Offline tool: it does not touch P:\\, DayZ Tools or the game, so it does not gate
on /dayz-preflight.
"""
import importlib.util
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
# The scaffold emitter, first where the 3D viewer tool keeps it.
VIEWER_CORE_PATHS = (
    REPO / "scripts" / "tools" / "dayz-3d-viewer" / "dayz_3d_viewer" / "viewer_core.py",
    REPO / "skills" / "_shared" / "viewer_core.py",
)
VIEWER_CORE_CONTRACT = "dayz-viewer-core/1"
THREE_VERSION = "0.185.1"
VIEWER_CORE_API = ("importmap_script", "module_imports", "boot_js", "loop_js")


def load_viewer_core(paths=VIEWER_CORE_PATHS):
    """Load viewer_core.py from the first path that holds the contract this script was written for."""
    for path in paths:
        if not path.is_file():
            continue
        spec = importlib.util.spec_from_file_location("viewer_core", path)
        if spec is None or spec.loader is None:
            continue
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if (
            getattr(mod, "VIEWER_CORE_CONTRACT", None) == VIEWER_CORE_CONTRACT
            and getattr(mod, "THREE_VERSION", None) == THREE_VERSION
            and all(callable(getattr(mod, name, None)) for name in VIEWER_CORE_API)
        ):
            return mod
    raise ImportError(
        "viewer_core.py (contract %s, three %s) not found at: %s"
        % (VIEWER_CORE_CONTRACT, THREE_VERSION, ", ".join(str(path) for path in paths))
    )


def generate_inspector_html(recipe, output_path=None, model_name=None):
    if model_name is None:
        model_name = recipe.get("meta", {}).get("source", "P3D Model")

    visual_data = None
    for lod in recipe.get("lods", []):
        if lod["type"] == "visual_0" and "geometry" in lod:
            visual_data = lod
            break
    if not visual_data:
        for lod in recipe.get("lods", []):
            if lod["type"].startswith("visual") and "geometry" in lod:
                visual_data = lod
                break

    wireframes = {}
    _WF_TYPES = ("geometry","fire_geometry","view_geometry",
                 "landcontact","roadway","paths","hitpoints")
    for lod in recipe.get("lods", []):
        if lod["type"] in _WF_TYPES and "wireframe" in lod:
            wireframes[lod["type"]] = lod["wireframe"]

    lod_summary = []
    for lod in recipe.get("lods", []):
        lod_summary.append({
            "type": lod["type"],
            "points": lod.get("num_points", 0),
            "faces": lod.get("num_faces", 0),
            "selections": list(lod.get("selections", {}).keys()),
        })

    ref_paths = recipe.get("referenced_paths", {"textures": [], "materials": []})

    rj = json.dumps({
        "visual": visual_data["geometry"] if visual_data else None,
        "wireframes": wireframes,
        "memory_points": recipe.get("memory_points", []),
        "axes": recipe.get("axes", {}),
        "bbox": recipe.get("bounding_box"),
        "lod_summary": lod_summary,
        "visual_selections": visual_data.get("selections", {}) if visual_data else {},
        "ref_paths": ref_paths,
        "meta": recipe.get("meta", {}),
    })

    vc = load_viewer_core()
    html = _html(model_name, rj)
    html = html.replace("__VC_IMPORTMAP__", vc.importmap_script())
    html = html.replace("__VC_IMPORTS__", vc.module_imports(("OrbitControls",), three_alias="T"))
    html = html.replace("__VC_BOOT__", vc.boot_js(
        three="T",
        scene="scene",
        camera="cam",
        renderer="ren",
        controls="ctrl",
        grid="grid",
        canvas_expr=None,
        insert_before=("vp", "vp.firstChild"),
        container_expr="vp",
        background="0x1a1a2e",
        fov=50,
        near=0.001,
        far=200,
        pixel_ratio="Math.min(devicePixelRatio,2)",
        tone_mapping="ACESFilmicToneMapping",
        tone_exposure=1.2,
        grid_size=2,
        grid_divisions=40,
        grid_color1="0x333355",
        grid_color2="0x222244",
        grid_visible=False,
        resize="container",
        resize_pixel_ratio="Math.min(devicePixelRatio,2)",
        loop=True,
        post_controls_hook="__vcFrame",
    ))
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
    return html

def _html(name, rj):
    return '<!DOCTYPE html>\n<html lang="en"><head>\n' \
    '<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">\n' \
    '<title>P3D Inspector — ' + name + '</title>\n' \
    r"""<style>
:root{--bg:#1a1a2e;--panel:rgba(15,15,30,0.92);--border:rgba(255,255,255,0.08);--text:#d0d0d0;--text-dim:#777;--accent:#4fc3f7}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--bg);color:var(--text);font-family:'Segoe UI',system-ui,sans-serif;overflow:hidden;height:100vh}
#app{display:flex;height:100vh}
#viewport{flex:1;position:relative;overflow:hidden}
#sidebar{width:320px;background:var(--panel);border-left:1px solid var(--border);display:flex;flex-direction:column;overflow:hidden;flex-shrink:0}
#viewport canvas{display:block}
#label-overlay{position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;overflow:hidden;z-index:5}
.lbl3d{position:absolute;font-size:10px;padding:2px 6px;border-radius:3px;background:rgba(0,0,0,0.75);white-space:nowrap;pointer-events:none;transform:translate(-50%,-100%);display:none}
#toolbar{position:absolute;top:12px;left:12px;display:flex;gap:6px;flex-wrap:wrap;z-index:10;max-width:calc(100% - 24px)}
#stats{position:absolute;top:12px;right:12px;background:var(--panel);border-radius:8px;padding:8px 12px;font-size:12px;line-height:1.6;z-index:10}
#stats .label{color:var(--text-dim)} #stats .val{color:var(--accent);font-weight:600}
#hint{position:absolute;bottom:12px;left:50%;transform:translateX(-50%);background:var(--panel);border-radius:8px;padding:6px 16px;font-size:11px;color:var(--text-dim);z-index:10;white-space:nowrap}
.btn{background:rgba(255,255,255,0.07);border:1px solid var(--border);color:var(--text);padding:6px 12px;border-radius:6px;cursor:pointer;font-size:12px;transition:all .15s;user-select:none;white-space:nowrap}
.btn:hover{background:rgba(255,255,255,0.13)} .btn.active{background:rgba(79,195,247,0.2);border-color:var(--accent);color:var(--accent)}
.btn-geo{border-color:#00e676;color:#00e676;opacity:.7} .btn-geo.active{background:rgba(0,230,118,0.15);opacity:1}
.btn-fire{border-color:#ff5252;color:#ff5252;opacity:.7} .btn-fire.active{background:rgba(255,82,82,0.15);opacity:1}
.btn-view{border-color:#448aff;color:#448aff;opacity:.7} .btn-view.active{background:rgba(68,138,255,0.15);opacity:1}
.btn-land{border-color:#cddc39;color:#cddc39;opacity:.7} .btn-land.active{background:rgba(205,220,57,0.15);opacity:1}
.btn-road{border-color:#00bcd4;color:#00bcd4;opacity:.7} .btn-road.active{background:rgba(0,188,212,0.15);opacity:1}
.btn-path{border-color:#e91e63;color:#e91e63;opacity:.7} .btn-path.active{background:rgba(233,30,99,0.15);opacity:1}
.btn-hit{border-color:#ff9800;color:#ff9800;opacity:.7} .btn-hit.active{background:rgba(255,152,0,0.15);opacity:1}
.btn-export{border-color:#81c784;color:#81c784} .btn-export:hover{background:rgba(129,199,132,0.15)}
.btn-export.copied{background:rgba(129,199,132,0.25);border-color:#81c784;color:#fff}
.panel-header{padding:14px 16px 10px;font-size:14px;font-weight:600;color:#fff;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center;flex-shrink:0}
.panel-header .badge{background:var(--accent);color:#000;border-radius:10px;padding:1px 8px;font-size:11px;font-weight:700}
#tabs{display:flex;border-bottom:1px solid var(--border);flex-shrink:0}
.tab{flex:1;padding:8px;text-align:center;font-size:12px;cursor:pointer;color:var(--text-dim);border-bottom:2px solid transparent;transition:all .15s}
.tab:hover{color:var(--text)} .tab.active{color:var(--accent);border-bottom-color:var(--accent)}
.tab-content{display:none;flex:1;overflow-y:auto} .tab-content.active{display:block}
.mp-item{padding:8px 16px;border-bottom:1px solid var(--border);cursor:pointer;transition:background .1s;display:flex;align-items:center;gap:10px}
.mp-item:hover{background:rgba(255,255,255,0.04)} .mp-item.selected{background:rgba(79,195,247,0.1);border-left:3px solid var(--accent)}
.mp-dot{width:10px;height:10px;border-radius:50%;flex-shrink:0}
.mp-info{flex:1;min-width:0} .mp-name{font-size:13px;font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.mp-coords{font-size:11px;color:var(--text-dim);font-family:Consolas,monospace} .mp-cat{font-size:10px;padding:1px 6px;border-radius:3px;background:rgba(255,255,255,0.06);color:var(--text-dim)}
.lod-item{padding:8px 16px;border-bottom:1px solid var(--border);font-size:12px}
.lod-type{font-weight:600;color:var(--accent);text-transform:uppercase;font-size:11px} .lod-detail{color:var(--text-dim);margin-top:2px}
.lod-sels{margin-top:4px;display:flex;flex-wrap:wrap;gap:4px} .lod-sel-tag{font-size:10px;padding:1px 6px;border-radius:3px;background:rgba(255,255,255,0.06);color:var(--text-dim)}
.path-item{padding:6px 16px;font-size:11px;font-family:Consolas,monospace;color:var(--text-dim);border-bottom:1px solid var(--border);word-break:break-all} .path-item.warn{color:#ffb74d}
.path-section{padding:8px 16px 4px;font-size:11px;font-weight:600;color:var(--text);text-transform:uppercase}
#selection-info{border-top:1px solid var(--border);padding:12px 16px;background:rgba(0,0,0,0.3);min-height:80px;flex-shrink:0}
#selection-info .si-title{font-size:12px;font-weight:600;color:var(--accent);margin-bottom:6px}
#selection-info .si-row{font-size:11px;margin-bottom:2px;display:flex;justify-content:space-between}
#selection-info .si-label{color:var(--text-dim)} #selection-info .si-val{font-family:Consolas,monospace;color:var(--text)}
#selection-info .si-empty{color:var(--text-dim);font-size:12px;font-style:italic}
#export-modal{position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.7);z-index:2000;display:none;align-items:center;justify-content:center}
#export-modal.show{display:flex}
#export-box{background:#1a1a2e;border:1px solid var(--accent);border-radius:10px;width:600px;max-height:80vh;display:flex;flex-direction:column;padding:16px}
#export-box h3{margin:0 0 10px;color:var(--accent);font-size:14px}
#export-textarea{flex:1;min-height:300px;background:#111;color:#ccc;border:1px solid var(--border);border-radius:6px;padding:10px;font-family:Consolas,monospace;font-size:11px;resize:none}
#export-btns{display:flex;gap:8px;margin-top:10px;justify-content:flex-end}
#export-btns button{padding:6px 16px;border-radius:6px;cursor:pointer;font-size:12px;border:1px solid var(--border);background:rgba(255,255,255,0.07);color:var(--text)}
#export-btns .primary{background:rgba(79,195,247,0.2);border-color:var(--accent);color:var(--accent)}
#coord-display{position:fixed;top:100px;left:12px;background:rgba(0,0,0,0.88);border:1px solid var(--accent);border-radius:6px;padding:8px 12px;font-family:Consolas,monospace;font-size:12px;color:var(--accent);z-index:1000;pointer-events:none;display:none;white-space:pre;line-height:1.8;box-shadow:0 4px 12px rgba(0,0,0,0.5)}
::-webkit-scrollbar{width:6px} ::-webkit-scrollbar-track{background:transparent} ::-webkit-scrollbar-thumb{background:rgba(255,255,255,0.1);border-radius:3px}
</style>
</head>
<body>
<div id="app">
  <div id="viewport">
    <div id="label-overlay"></div>
    <div id="toolbar">
      <button class="btn active" id="btn-visual" onclick="TL('visual')">Visual</button>
      <button class="btn btn-geo" id="btn-geometry" onclick="TL('geometry')">Geometry</button>
      <button class="btn btn-fire" id="btn-fire_geometry" onclick="TL('fire_geometry')">Fire Geo</button>
      <button class="btn btn-view" id="btn-view_geometry" onclick="TL('view_geometry')">View Geo</button>
      <button class="btn btn-land" id="btn-landcontact" onclick="TL('landcontact')">LandContact</button>
      <button class="btn btn-road" id="btn-roadway" onclick="TL('roadway')">Roadway</button>
      <button class="btn btn-path" id="btn-paths" onclick="TL('paths')">Paths</button>
      <button class="btn btn-hit" id="btn-hitpoints" onclick="TL('hitpoints')">HitPoints</button>
      <button class="btn active" id="btn-memory" onclick="TL('memory')">Memory Pts</button>
      <button class="btn active" id="btn-axes" onclick="TL('axes')">Axes</button>
      <button class="btn active" id="btn-bbox" onclick="TL('bbox')">Bounds</button>
      <button class="btn" id="btn-labels" onclick="TL('labels')">Labels</button>
      <button class="btn" id="btn-grid" onclick="TL('grid')">Grid</button>
      <button class="btn" id="btn-wireframe" onclick="TL('wireframe')">Wireframe</button>
      <button class="btn btn-export" id="btn-export" onclick="exportRecipe()">Export Recipe</button>
    </div>
    <div id="stats"></div>
    <div id="coord-display"></div>
    <div id="hint">LMB: Orbit | Click sphere: Select | Drag sphere: Move | Shift: Snap | 1/2: Grid 1cm/5cm | RMB: Pan</div>
  </div>
  <div id="sidebar">
    <div class="panel-header">
      <span class="title">""" + name + r"""</span>
      <span class="badge" id="mode-badge">AUDIT</span>
    </div>
    <div id="tabs">
      <div class="tab active" data-tab="points" onclick="ST('points')">Points</div>
      <div class="tab" data-tab="lods" onclick="ST('lods')">LODs</div>
      <div class="tab" data-tab="selections" onclick="ST('selections')">Selections</div>
      <div class="tab" data-tab="paths" onclick="ST('paths')">Paths</div>
    </div>
    <div class="tab-content active" id="tc-points"></div>
    <div class="tab-content" id="tc-lods"></div>
    <div class="tab-content" id="tc-selections"></div>
    <div class="tab-content" id="tc-paths"></div>
    <div id="selection-info"><div class="si-empty">Click a memory point to inspect</div></div>
  </div>
</div>
<div id="export-modal" onclick="if(event.target===this)closeExport()">
  <div id="export-box">
    <h3>Recipe JSON — Select All + Copy</h3>
    <textarea id="export-textarea" readonly></textarea>
    <div id="export-btns">
      <button onclick="closeExport()">Close</button>
      <button class="primary" onclick="selectAllExport()">Select All</button>
    </div>
  </div>
</div>
__VC_IMPORTMAP__
<script type="module">
__VC_IMPORTS__

const R=""" + rj + r""";

const CC={center:0x4fc3f7,interaction:0xef5350,axis:0x7e57c2,placing:0xffb74d,port:0xff7043,proxy:0x78909c,other:0x9e9e9e};
const CS={center:'#4fc3f7',interaction:'#ef5350',axis:'#7e57c2',placing:'#ffb74d',port:'#ff7043',proxy:'#78909c',other:'#9e9e9e'};
const WC={geometry:0x00e676,fire_geometry:0xff5252,view_geometry:0x448aff,
  landcontact:0xcddc39,roadway:0x00bcd4,paths:0xe91e63,hitpoints:0xff9800};

const vp=document.getElementById('viewport');
__VC_BOOT__

// Lights
scene.add(new T.AmbientLight(0xffffff,0.45));
const d1=new T.DirectionalLight(0xffffff,0.9);d1.position.set(2,3,2);scene.add(d1);
const d2=new T.DirectionalLight(0x8888ff,0.25);d2.position.set(-2,1,-1);scene.add(d2);
const d3=new T.DirectionalLight(0xffffcc,0.15);d3.position.set(0,-1,-2);scene.add(d3);

// Layers
const L={visual:new T.Group(),geometry:new T.Group(),fire_geometry:new T.Group(),view_geometry:new T.Group(),
  landcontact:new T.Group(),roadway:new T.Group(),paths:new T.Group(),hitpoints:new T.Group(),
  memory:new T.Group(),axes:new T.Group(),bbox:new T.Group(),wireframe:new T.Group()};
L.visual.visible=true;
L.geometry.visible=false; L.fire_geometry.visible=false; L.view_geometry.visible=false;
L.landcontact.visible=false; L.roadway.visible=false; L.paths.visible=false; L.hitpoints.visible=false;
L.memory.visible=true; L.axes.visible=true; L.bbox.visible=true; L.wireframe.visible=false;
for(const g of Object.values(L)) scene.add(g);

// ── Labels (pure HTML overlay, NO CSS2DRenderer) ──────────────────
const lblOverlay=document.getElementById('label-overlay');
const labels3d=[]; // {div, pos:Vector3, mpIndex?:number}
let labelsOn=false;

function addLabel(text,x,y,z,color,mpIndex){
  const d=document.createElement('div');
  d.className='lbl3d';
  d.textContent=text;
  d.style.color=color||'#999';
  lblOverlay.appendChild(d);
  const entry={div:d,pos:new T.Vector3(x,y,z)};
  if(mpIndex!==undefined) entry.mpIndex=mpIndex;
  labels3d.push(entry);
  return entry;
}
function updateLabels(){
  if(!labelsOn){return;}
  const w=vp.clientWidth,h=vp.clientHeight;
  const v=new T.Vector3();
  for(const lb of labels3d){
    v.copy(lb.pos); v.project(cam);
    if(v.z>1){lb.div.style.display='none';continue;}
    const sx=(v.x*0.5+0.5)*w;
    const sy=(-v.y*0.5+0.5)*h;
    lb.div.style.display='block';
    lb.div.style.left=sx+'px';
    lb.div.style.top=sy+'px';
  }
}

// ── Build Visual Mesh ─────────────────────────────────────────────
let mCenter=new T.Vector3(), mSize=1;
if(R.visual){
  const pos=new Float32Array(R.visual.positions.flat());
  const nrm=new Float32Array(R.visual.normals.flat());
  const uvs=new Float32Array(R.visual.uvs.flat());
  for(const[mk,indices]of Object.entries(R.visual.material_groups)){
    if(!indices.length)continue;
    const geo=new T.BufferGeometry();
    geo.setAttribute('position',new T.BufferAttribute(pos,3));
    geo.setAttribute('normal',new T.BufferAttribute(nrm,3));
    geo.setAttribute('uv',new T.BufferAttribute(uvs,2));
    geo.setIndex(new T.BufferAttribute(new Uint32Array(indices),1));
    L.visual.add(new T.Mesh(geo,new T.MeshStandardMaterial({color:0x888888,metalness:0.1,roughness:0.7,side:T.DoubleSide})));
    L.wireframe.add(new T.LineSegments(new T.WireframeGeometry(geo),new T.LineBasicMaterial({color:0x4fc3f7,opacity:0.12,transparent:true})));
  }
  const box=new T.Box3().setFromObject(L.visual);
  box.getCenter(mCenter);
  const sz=box.getSize(new T.Vector3());
  mSize=Math.max(sz.x,sz.y,sz.z);
}

// ── Collision Wireframes ──────────────────────────────────────────
for(const[wt,wf]of Object.entries(R.wireframes)){
  if(!wf||!wf.positions||!wf.edges)continue;
  const pts=[];
  for(const[a,b]of wf.edges){
    const pa=wf.positions[a],pb=wf.positions[b];
    if(pa&&pb){pts.push(new T.Vector3(pa[0],pa[1],pa[2]));pts.push(new T.Vector3(pb[0],pb[1],pb[2]));}
  }
  if(pts.length)L[wt].add(new T.LineSegments(new T.BufferGeometry().setFromPoints(pts),new T.LineBasicMaterial({color:WC[wt]||0x00ff00,opacity:0.6,transparent:true})));
}

// ── Memory Points ─────────────────────────────────────────────────
const mpM=[]; // meshes for raycasting
const rad=Math.max(mSize*0.018,0.004);
for(const mp of R.memory_points){
  const c=CC[mp.category]||CC.other;
  const mat=new T.MeshStandardMaterial({color:c,emissive:0x000000,emissiveIntensity:0,roughness:0.3,metalness:0.1});
  const s=new T.Mesh(new T.SphereGeometry(rad,16,12),mat);
  s.position.set(mp.position[0],mp.position[1],mp.position[2]);
  s.userData={mpIndex:mp.index,mpData:mp,origColor:c};
  L.memory.add(s); mpM.push(s);
  addLabel(mp.label,mp.position[0],mp.position[1]+rad*3,mp.position[2],CS[mp.category]||'#999',mp.index);
}

// ── Tracked objects for live editing ──────────────────────────────
const tracked={axes:{},placingBox:null,placingLabel:null};

// ── Axes ──────────────────────────────────────────────────────────
function buildAxis(nm,ax){
  const p1=new T.Vector3(...ax.points[0]),p2=new T.Vector3(...ax.points[1]);
  const dir=new T.Vector3().subVectors(p2,p1);
  const len=dir.length(); if(len<1e-9)return null;
  const line=new T.Line(new T.BufferGeometry().setFromPoints([p1,p2]),new T.LineBasicMaterial({color:0x7e57c2}));
  const al=Math.min(len*0.4,mSize*0.02);
  const arrow=new T.ArrowHelper(dir.clone().normalize(),p1,len,0x7e57c2,al,al*0.5);
  const mid=new T.Vector3().addVectors(p1,p2).multiplyScalar(0.5);
  const lbl=addLabel(nm,mid.x,mid.y+mSize*0.025,mid.z,'#7e57c2');
  L.axes.add(line); L.axes.add(arrow);
  return {line,arrow,label:lbl};
}
for(const[nm,ax]of Object.entries(R.axes)){
  const t=buildAxis(nm,ax);
  if(t) tracked.axes[nm]=t;
}

function rebuildAxis(nm){
  const old=tracked.axes[nm];
  if(old){
    L.axes.remove(old.line); L.axes.remove(old.arrow);
    // Remove label div
    const li=labels3d.indexOf(old.label);
    if(li>=0){old.label.div.remove();labels3d.splice(li,1);}
  }
  const ax=R.axes[nm]; if(!ax)return;
  const t=buildAxis(nm,ax);
  if(t) tracked.axes[nm]=t;
}

// ── Bounding Boxes ────────────────────────────────────────────────
function makeBox(mn,mx,color){
  const pts=[
    mn[0],mn[1],mn[2], mx[0],mn[1],mn[2], mx[0],mn[1],mn[2], mx[0],mn[1],mx[2],
    mx[0],mn[1],mx[2], mn[0],mn[1],mx[2], mn[0],mn[1],mx[2], mn[0],mn[1],mn[2],
    mn[0],mx[1],mn[2], mx[0],mx[1],mn[2], mx[0],mx[1],mn[2], mx[0],mx[1],mx[2],
    mx[0],mx[1],mx[2], mn[0],mx[1],mx[2], mn[0],mx[1],mx[2], mn[0],mx[1],mn[2],
    mn[0],mn[1],mn[2], mn[0],mx[1],mn[2], mx[0],mn[1],mn[2], mx[0],mx[1],mn[2],
    mx[0],mn[1],mx[2], mx[0],mx[1],mx[2], mn[0],mn[1],mx[2], mn[0],mx[1],mx[2],
  ];
  const geo=new T.BufferGeometry();
  geo.setAttribute('position',new T.BufferAttribute(new Float32Array(pts),3));
  return new T.LineSegments(geo,new T.LineBasicMaterial({color,transparent:true,opacity:0.4,depthTest:false}));
}

if(R.bbox){
  L.bbox.add(makeBox(R.bbox.min,R.bbox.max,0x4fc3f7));
}

function rebuildPlacingBox(){
  if(tracked.placingBox){L.bbox.remove(tracked.placingBox);tracked.placingBox=null;}
  if(tracked.placingLabel){
    const li=labels3d.indexOf(tracked.placingLabel);
    if(li>=0){tracked.placingLabel.div.remove();labels3d.splice(li,1);}
    tracked.placingLabel=null;
  }
  const plMin=R.memory_points.find(p=>p.selections.some(s=>s.includes('box_placing_min')));
  const plMax=R.memory_points.find(p=>p.selections.some(s=>s.includes('box_placing_max')));
  if(plMin&&plMax){
    tracked.placingBox=makeBox(plMin.position,plMax.position,0xffb74d);
    L.bbox.add(tracked.placingBox);
    tracked.placingLabel=addLabel('box_placing',plMax.position[0],plMax.position[1]+mSize*0.025,plMax.position[2],'#ffb74d');
  }
}
rebuildPlacingBox();

// ── Camera ────────────────────────────────────────────────────────
const dist=mSize*2.8;
cam.position.set(mCenter.x+dist*0.5,mCenter.y+dist*0.35,mCenter.z+dist*0.6);
cam.near=mSize*0.0005; cam.far=mSize*200; cam.updateProjectionMatrix();
ctrl.target.copy(mCenter); ctrl.update();
grid.scale.setScalar(Math.ceil(mSize*3));

// ── Drag & Drop System (Phase 2) ─────────────────────────────────
const ray=new T.Raycaster(), mouse=new T.Vector2();
let selMesh=null;
const dragPlane=new T.Plane();

const drag={
  active:false,
  mesh:null,
  mpIndex:null,
  startPos:new T.Vector3(),
  snapGrid:0.01,
  snapOn:false,
  linkedLabel:null,    // label entry from labels3d
  linkedAxis:null,     // {name, endpoint:0|1}
  isPlacing:false,     // is box_placing point
};

function snapVal(v,g){return drag.snapOn?Math.round(v/g)*g:v;}

const coordDiv=document.getElementById('coord-display');
function showCoords(pos){
  let t='X: '+pos.x.toFixed(4)+'\nY: '+pos.y.toFixed(4)+'\nZ: '+pos.z.toFixed(4);
  if(drag.snapOn) t+='\nSnap: '+drag.snapGrid.toFixed(3)+'m';
  coordDiv.textContent=t; coordDiv.style.display='block';
}
function hideCoords(){coordDiv.style.display='none';}

// Identify linked objects when selecting a point for drag
function identifyLinks(mesh){
  const mp=mesh.userData.mpData;
  drag.linkedLabel=null; drag.linkedAxis=null; drag.isPlacing=false;

  // Find label by mpIndex
  for(const lb of labels3d){
    if(lb.mpIndex===mp.index){drag.linkedLabel=lb;break;}
  }

  // Check if axis endpoint
  for(const[axName,axData]of Object.entries(R.axes)){
    for(let ep=0;ep<2;ep++){
      const ap=axData.points[ep];
      if(Math.abs(ap[0]-mp.position[0])<0.001&&Math.abs(ap[1]-mp.position[1])<0.001&&Math.abs(ap[2]-mp.position[2])<0.001){
        drag.linkedAxis={name:axName,endpoint:ep};
        break;
      }
    }
    if(drag.linkedAxis)break;
  }

  // Check if placing point
  for(const sel of mp.selections){
    if(sel.includes('box_placing')){drag.isPlacing=true;break;}
  }
}

// Update everything when a point moves
function applyMove(newPos){
  const mp=drag.mesh.userData.mpData;
  // Update recipe data
  mp.position[0]=newPos.x; mp.position[1]=newPos.y; mp.position[2]=newPos.z;
  // Update sphere
  drag.mesh.position.copy(newPos);
  // Update label
  if(drag.linkedLabel){
    drag.linkedLabel.pos.set(newPos.x,newPos.y+rad*3,newPos.z);
  }
  // Update axis geometry
  if(drag.linkedAxis){
    R.axes[drag.linkedAxis.name].points[drag.linkedAxis.endpoint]=[newPos.x,newPos.y,newPos.z];
    rebuildAxis(drag.linkedAxis.name);
  }
  // Update placing box
  if(drag.isPlacing){
    rebuildPlacingBox();
  }
  // Update sidebar coords
  const item=document.querySelector('.mp-item[data-idx="'+mp.index+'"] .mp-coords');
  if(item) item.textContent=newPos.x.toFixed(3)+', '+newPos.y.toFixed(3)+', '+newPos.z.toFixed(3);
}

// ── Pointer Events ────────────────────────────────────────────────
let _pDown=null;

// ── Hover detection: disable orbit BEFORE click when over a sphere ──
let hoverSphere=false;
ren.domElement.addEventListener('mousemove',e=>{
  if(drag.active)return;
  const r=ren.domElement.getBoundingClientRect();
  mouse.x=((e.clientX-r.left)/r.width)*2-1;
  mouse.y=-((e.clientY-r.top)/r.height)*2+1;
  ray.setFromCamera(mouse,cam);
  const h=ray.intersectObjects(mpM,false);
  if(h.length>0){
    if(!hoverSphere){hoverSphere=true;ctrl.enabled=false;ren.domElement.style.cursor='grab';}
  }else{
    if(hoverSphere){hoverSphere=false;ctrl.enabled=true;ren.domElement.style.cursor='';}
  }
});

// ── Pointer events for drag ───────────────────────────────────────
ren.domElement.addEventListener('pointerdown',e=>{
  if(e.button!==0)return;
  _pDown={x:e.clientX,y:e.clientY,time:Date.now()};

  const r=ren.domElement.getBoundingClientRect();
  mouse.x=((e.clientX-r.left)/r.width)*2-1;
  mouse.y=-((e.clientY-r.top)/r.height)*2+1;
  ray.setFromCamera(mouse,cam);
  const h=ray.intersectObjects(mpM,false);
  if(h.length>0){
    const hitMesh=h[0].object;
    selPt(hitMesh);
    identifyLinks(hitMesh);
    drag.mesh=hitMesh;
    drag.mpIndex=hitMesh.userData.mpIndex;
    drag.startPos.copy(hitMesh.position);
  }
});

ren.domElement.addEventListener('pointermove',e=>{
  if(!_pDown||!drag.mesh)return;
  const dx=e.clientX-_pDown.x, dy=e.clientY-_pDown.y;
  const dist2=dx*dx+dy*dy;

  if(!drag.active&&dist2>25){
    drag.active=true;
    ctrl.enabled=false;
    const camDir=new T.Vector3();
    cam.getWorldDirection(camDir);
    dragPlane.setFromNormalAndCoplanarPoint(camDir,drag.mesh.position);
    ren.domElement.style.cursor='grabbing';
  }

  if(!drag.active)return;

  const r=ren.domElement.getBoundingClientRect();
  mouse.x=((e.clientX-r.left)/r.width)*2-1;
  mouse.y=-((e.clientY-r.top)/r.height)*2+1;
  ray.setFromCamera(mouse,cam);
  const target=new T.Vector3();
  if(!ray.ray.intersectPlane(dragPlane,target))return;

  const g=drag.snapGrid;
  const snapped=new T.Vector3(snapVal(target.x,g),snapVal(target.y,g),snapVal(target.z,g));

  applyMove(snapped);
  showCoords(snapped);
  updateSelInfo(drag.mesh);
});

ren.domElement.addEventListener('pointerup',e=>{
  if(!_pDown)return;
  const wasDragging=drag.active;
  const dx=e.clientX-_pDown.x,dy=e.clientY-_pDown.y;
  const isClick=dx*dx+dy*dy<25;

  if(wasDragging){
    drag.active=false;
    hideCoords();
    ren.domElement.style.cursor=hoverSphere?'grab':'';
    drag.mesh=null;
    _pDown=null;
    // Re-enable orbit only if not still hovering a sphere
    if(!hoverSphere) ctrl.enabled=true;
    return;
  }

  if(isClick&&!drag.mesh){
    const r=ren.domElement.getBoundingClientRect();
    mouse.x=((e.clientX-r.left)/r.width)*2-1;
    mouse.y=-((e.clientY-r.top)/r.height)*2+1;
    ray.setFromCamera(mouse,cam);
    const h=ray.intersectObjects(mpM,false);
    if(h.length===0){desel();ctrl.enabled=true;}
  }
  drag.mesh=null;
  _pDown=null;
  if(!hoverSphere) ctrl.enabled=true;
});

// Keyboard: Shift for snap, 1/2 for grid size
document.addEventListener('keydown',e=>{
  if(e.key==='Shift'){drag.snapOn=true;if(drag.active)showCoords(drag.mesh.position);}
  if(e.key==='1'){drag.snapGrid=0.01;}
  if(e.key==='2'){drag.snapGrid=0.05;}
});
document.addEventListener('keyup',e=>{
  if(e.key==='Shift'){drag.snapOn=false;if(drag.active)showCoords(drag.mesh.position);}
});

// ── Selection ─────────────────────────────────────────────────────
function selPt(mesh){
  if(selMesh&&selMesh!==mesh){selMesh.material.emissive.setHex(0x000000);selMesh.material.emissiveIntensity=0;selMesh.scale.set(1,1,1);}
  selMesh=mesh;
  mesh.material.emissive.setHex(0xffffff); mesh.material.emissiveIntensity=0.4; mesh.scale.set(1.5,1.5,1.5);
  const mp=mesh.userData.mpData;
  document.querySelectorAll('.mp-item').forEach(el=>el.classList.remove('selected'));
  const it=document.querySelector('.mp-item[data-idx="'+mp.index+'"]');
  if(it){it.classList.add('selected');it.scrollIntoView({block:'nearest',behavior:'smooth'});}
  updateSelInfo(mesh);
}

function updateSelInfo(mesh){
  const mp=mesh.userData.mpData;
  const px=mesh.position.x, py=mesh.position.y, pz=mesh.position.z;
  const info=document.getElementById('selection-info');
  info.innerHTML='<div class="si-title">'+mp.label+'</div>'+
    '<div class="si-row"><span class="si-label">Index:</span><span class="si-val">'+mp.index+'</span></div>'+
    '<div class="si-row"><span class="si-label">Category:</span><span class="si-val">'+mp.category+'</span></div>'+
    '<div class="si-row"><span class="si-label">X:</span><span class="si-val">'+px.toFixed(4)+'</span></div>'+
    '<div class="si-row"><span class="si-label">Y:</span><span class="si-val">'+py.toFixed(4)+'</span></div>'+
    '<div class="si-row"><span class="si-label">Z:</span><span class="si-val">'+pz.toFixed(4)+'</span></div>'+
    '<div class="si-row"><span class="si-label">Selections:</span><span class="si-val">'+(mp.selections.join(', ')||'none')+'</span></div>';
}

function desel(){
  if(selMesh){selMesh.material.emissive.setHex(0x000000);selMesh.material.emissiveIntensity=0;selMesh.scale.set(1,1,1);selMesh=null;}
  document.querySelectorAll('.mp-item').forEach(el=>el.classList.remove('selected'));
  document.getElementById('selection-info').innerHTML='<div class="si-empty">Click a memory point to inspect</div>';
}

function focusPt(mp){
  const p=new T.Vector3(mp.position[0],mp.position[1],mp.position[2]);
  cam.position.set(p.x+mSize*0.3,p.y+mSize*0.2,p.z+mSize*0.3);
  ctrl.target.copy(p); ctrl.update();
}

// ── Export Recipe ─────────────────────────────────────────────────
window.exportRecipe=function(){
  const exp={memory_points:R.memory_points,axes:R.axes,bbox:R.bbox,meta:R.meta};
  const jsonStr=JSON.stringify(exp,null,2);
  const ta=document.getElementById('export-textarea');
  ta.value=jsonStr;
  document.getElementById('export-modal').classList.add('show');
};
window.closeExport=function(){
  document.getElementById('export-modal').classList.remove('show');
};
window.selectAllExport=function(){
  const ta=document.getElementById('export-textarea');
  ta.select(); ta.setSelectionRange(0,ta.value.length);
};

// ── Layer Toggles ─────────────────────────────────────────────────
window.TL=function(n){
  if(n==='labels'){labelsOn=!labelsOn;if(!labelsOn)labels3d.forEach(lb=>{lb.div.style.display='none';});
    document.getElementById('btn-labels').classList.toggle('active',labelsOn);return;}
  if(n==='grid'){grid.visible=!grid.visible;document.getElementById('btn-grid').classList.toggle('active',grid.visible);return;}
  const ly=L[n];if(!ly)return;ly.visible=!ly.visible;
  const b=document.getElementById('btn-'+n);if(b)b.classList.toggle('active',ly.visible);
};
window.ST=function(t){
  document.querySelectorAll('.tab').forEach(el=>el.classList.toggle('active',el.dataset.tab===t));
  document.querySelectorAll('.tab-content').forEach(el=>el.classList.toggle('active',el.id==='tc-'+t));
};
window.clickMP=function(i){
  const m=mpM.find(x=>x.userData.mpIndex===i);
  if(m){selPt(m);focusPt(m.userData.mpData);}
};

// ── Populate Sidebar ──────────────────────────────────────────────
let ph='';
for(const mp of R.memory_points){
  const c=CS[mp.category]||CS.other,p=mp.position;
  ph+='<div class="mp-item" data-idx="'+mp.index+'" onclick="clickMP('+mp.index+')">'+
    '<div class="mp-dot" style="background:'+c+'"></div>'+
    '<div class="mp-info"><div class="mp-name">'+mp.label+'</div>'+
    '<div class="mp-coords">'+p[0].toFixed(3)+', '+p[1].toFixed(3)+', '+p[2].toFixed(3)+'</div></div>'+
    '<span class="mp-cat">'+mp.category+'</span></div>';
}
if(!R.memory_points.length)ph='<div style="padding:16px;color:#666;font-size:13px">No memory points</div>';
document.getElementById('tc-points').innerHTML=ph;

let lh='';
for(const ld of R.lod_summary){
  let sh='';for(const s of ld.selections)sh+='<span class="lod-sel-tag">'+s+'</span>';
  lh+='<div class="lod-item"><div class="lod-type">'+ld.type+'</div>'+
    '<div class="lod-detail">'+ld.points+' pts, '+ld.faces+' faces</div>'+
    (sh?'<div class="lod-sels">'+sh+'</div>':'')+'</div>';
}
document.getElementById('tc-lods').innerHTML=lh;

const aS={};
for(const ld of R.lod_summary)for(const s of ld.selections){if(!aS[s])aS[s]=[];aS[s].push(ld.type);}
let sh='';
for(const[s,ls]of Object.entries(aS).sort())sh+='<div class="lod-item"><div class="lod-type" style="color:#81c784">'+s+'</div><div class="lod-detail">In: '+ls.join(', ')+'</div></div>';
if(!sh)sh='<div style="padding:16px;color:#666;font-size:13px">No selections</div>';
document.getElementById('tc-selections').innerHTML=sh;

let pah='';
if(R.ref_paths.textures.length){pah+='<div class="path-section">Textures</div>';
  for(const p of R.ref_paths.textures){const w=p.startsWith('P:\\');pah+='<div class="path-item'+(w?' warn':'')+'">'+p+'</div>';}}
if(R.ref_paths.materials.length){pah+='<div class="path-section">Materials</div>';
  for(const p of R.ref_paths.materials){const w=p.startsWith('P:\\');pah+='<div class="path-item'+(w?' warn':'')+'">'+p+'</div>';}}
if(!pah)pah='<div style="padding:16px;color:#666;font-size:13px">No paths</div>';
document.getElementById('tc-paths').innerHTML=pah;

// Stats
const tp=R.lod_summary.reduce((a,l)=>a+l.points,0),tf=R.lod_summary.reduce((a,l)=>a+l.faces,0);
document.getElementById('stats').innerHTML=
  '<div><span class="label">LODs: </span><span class="val">'+R.lod_summary.length+'</span></div>'+
  '<div><span class="label">Total pts: </span><span class="val">'+tp.toLocaleString()+'</span></div>'+
  '<div><span class="label">Total faces: </span><span class="val">'+tf.toLocaleString()+'</span></div>'+
  '<div><span class="label">Memory pts: </span><span class="val">'+R.memory_points.length+'</span></div>'+
  '<div><span class="label">Axes: </span><span class="val">'+Object.keys(R.axes).length+'</span></div>';

const badge=document.getElementById('mode-badge');
if(R.meta.mode==='demo'){badge.textContent='DEMO';badge.style.background='#ffb74d';}
else if(R.meta.mode==='propose'){badge.textContent='PROPOSAL';badge.style.background='#81c784';}

function __vcFrame(){
  cam.updateMatrixWorld();
  cam.updateProjectionMatrix();
  updateLabels();
}
new ResizeObserver(resize).observe(vp);
</script>
</body></html>"""

if __name__=='__main__':
    usage="Usage: p3d_inspector_viewer.py <recipe.json|--demo> [output.html]"
    if any(a in ('-h','--help') for a in sys.argv[1:]):
        print(usage); sys.exit(0)
    if len(sys.argv)<2:
        print(usage); sys.exit(1)
    if sys.argv[1]=='--demo':
        sd=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,sd)
        from p3d_inspector_extract import generate_demo_recipe
        recipe=generate_demo_recipe()
        out=sys.argv[2] if len(sys.argv)>2 else 'inspector_demo.html'
    else:
        with open(sys.argv[1], encoding='utf-8') as f: recipe=json.load(f)
        out=sys.argv[2] if len(sys.argv)>2 else 'inspector.html'
    try:
        generate_inspector_html(recipe,output_path=out)
    except ImportError as exc:
        sys.exit(f"[FAIL] {exc}")
    print(f"Inspector saved: {out}")
