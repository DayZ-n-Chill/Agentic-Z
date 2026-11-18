#!/usr/bin/env python3
"""
Alignment viewer, step 2: build the HTML page from align_data.json.

Usage:
    python alignment_viewer_build.py --data <folder>\\align_data.json
        [--out <page.html>] [--title "Clothing alignment viewer"] [--viewer-core <viewer_core.py>]

The page shows the worn mesh with one colored region per bone selection, the
reference mesh as a green wireframe, and six sliders per region (rotation
around the region pivot and an offset, both masked by the region weights).
Left regions mirror onto their right twins. "Generate adjustments JSON" writes
what apply_alignment_json.py reads.

three.js comes from the shared viewer core (viewer_core.py), which loads it
from a CDN when the page opens, so the page needs a network connection. The
core is looked for at skills/_shared/viewer_core.py, then inside
scripts/tools/dayz-3d-viewer/dayz_3d_viewer/; --viewer-core names another copy.

Offline: reads one JSON and writes one HTML file.
"""
import argparse
import html
import importlib.util
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
VIEWER_CORE_CANDIDATES = (
    REPO / "skills" / "_shared" / "viewer_core.py",
    REPO / "scripts" / "tools" / "dayz-3d-viewer" / "dayz_3d_viewer" / "viewer_core.py",
)
VIEWER_CORE_CONTRACT = "dayz-viewer-core/1"
THREE_VERSION = "0.185.1"
VIEWER_CORE_FUNCTIONS = ("importmap_script", "module_imports", "boot_js", "resize_js", "loop_js")

HTML_HEAD = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>__TITLE__</title>
<style>
body{margin:0;font-family:Segoe UI,Arial,sans-serif;background:#1a1a2e;color:#ddd;overflow:hidden}
#c{position:absolute;top:0;left:0;right:0;bottom:0}
#panel{position:absolute;top:0;right:0;width:340px;max-height:100vh;overflow-y:auto;background:rgba(22,22,40,.95);padding:12px;box-sizing:border-box;font-size:12px}
h2{font-size:14px;margin:4px 0 8px;color:#8cf}
h3{font-size:12px;margin:10px 0 4px;padding:3px 6px;border-radius:3px}
.rowg{display:grid;grid-template-columns:110px 1fr 44px;gap:4px;align-items:center;margin:2px 0}
input[type=range]{width:100%}
button{background:#2a6df4;color:#fff;border:0;border-radius:4px;padding:6px 10px;margin:3px 2px;cursor:pointer;font-size:12px}
button.sec{background:#444}
#json{width:100%;height:90px;background:#111;color:#9f9;border:1px solid #333;font-family:monospace;font-size:10px}
.hint{color:#999;font-size:11px;margin:6px 0}
label.chk{display:block;margin:4px 0}
</style></head><body>
<canvas id="c"></canvas>
<div id="panel">
<h2>__TITLE__</h2>
<div class="hint">Green wireframe = the vanilla reference garment (where clothing should sit on the body). Adjust each region until the plates hug the reference. DayZ axes: X = the character's left, Y = up, -Z = front.</div>
<div>
<button class="sec" onclick="setView(0)">Front</button>
<button class="sec" onclick="setView(1)">Back</button>
<button class="sec" onclick="setView(2)">Left</button>
<button class="sec" onclick="setView(3)">Right</button>
</div>
<label class="chk"><input type="checkbox" id="ghost" checked onchange="ghostMesh.visible=this.checked"> Show vanilla reference</label>
<label class="chk"><input type="checkbox" id="mirror" checked> Mirror left / right adjustments</label>
<div id="controls"></div>
<button onclick="exportJson()">Generate adjustments JSON</button>
<button class="sec" onclick="resetAll()">Reset</button>
<textarea id="json" readonly placeholder="Press Generate adjustments JSON, then copy the content"></textarea>
<button onclick="copyJson()">Copy to clipboard</button>
</div>
"""

HTML_JS = """<script type="module">
__VC_IMPORTS__
const DATA = __DATA__;
const REGIONS = DATA.armor.regions;
const KNOWN_COLORS = {leftarm:[0.25,0.5,1], rightarm:[1,0.35,0.3], leftforearm:[0.3,0.9,1], rightforearm:[1,0.7,0.3]};
const PALETTE = [[0.6,0.4,1],[1,0.5,0.8],[0.4,0.9,0.5],[0.9,0.9,0.3],[0.5,0.8,0.8],[0.9,0.6,0.5]];
const KNOWN_LABELS = {leftarm:"Left shoulder/arm (blue)", rightarm:"Right shoulder/arm (red)", leftforearm:"Left forearm (cyan)", rightforearm:"Right forearm (orange)"};
const REGION_COLORS = {}, LABELS = {}, MIRROR_OF = {};
let spare = 0;
REGIONS.forEach(r=>{
  REGION_COLORS[r] = KNOWN_COLORS[r] || PALETTE[spare++ % PALETTE.length];
  LABELS[r] = KNOWN_LABELS[r] || r;
  if (r.startsWith("left") && REGIONS.includes("right" + r.slice(4))) MIRROR_OF[r] = "right" + r.slice(4);
});

__VC_BOOT__
scene.add(new THREE.AmbientLight(0xffffff, .55));
const dl = new THREE.DirectionalLight(0xffffff, .8); dl.position.set(2,3,2); scene.add(dl);
const dl2 = new THREE.DirectionalLight(0x8899ff, .3); dl2.position.set(-2,1,-2); scene.add(dl2);

const TARGET = new THREE.Vector3(0, 1.15, 0);
let theta = Math.PI, phi = 1.35, dist = 2.2;
function applyCam(){
  camera.position.set(TARGET.x + dist*Math.sin(phi)*Math.sin(theta), TARGET.y + dist*Math.cos(phi), TARGET.z + dist*Math.sin(phi)*Math.cos(theta));
  camera.lookAt(TARGET);
}
function setView(i){ theta = [Math.PI, 0, Math.PI/2, -Math.PI/2][i]; phi = 1.45; applyCam(); }
let drag = false, px=0, py=0;
const cv = document.getElementById("c");
cv.addEventListener("mousedown", e=>{drag=true;px=e.clientX;py=e.clientY});
window.addEventListener("mouseup", ()=>drag=false);
window.addEventListener("mousemove", e=>{ if(!drag) return; theta -= (e.clientX-px)*0.008; phi = Math.max(0.15, Math.min(2.9, phi + (e.clientY-py)*0.006)); px=e.clientX; py=e.clientY; applyCam(); });
cv.addEventListener("wheel", e=>{ dist = Math.max(0.4, Math.min(8, dist * (1 + Math.sign(e.deltaY)*0.1))); applyCam(); e.preventDefault(); }, {passive:false});

const basePos = new Float32Array(DATA.armor.positions);
const livePos = new Float32Array(basePos);
const ageo = new THREE.BufferGeometry();
ageo.setAttribute("position", new THREE.BufferAttribute(livePos, 3));
ageo.setIndex(DATA.armor.indices);
const colors = new Float32Array(basePos.length);
for (let i=0;i<basePos.length/3;i++){ colors[3*i]=0.62; colors[3*i+1]=0.6; colors[3*i+2]=0.55; }
REGIONS.forEach((r,ri)=>{ const col=REGION_COLORS[r], w=DATA.armor.weights[ri];
  for(let i=0;i<w.length;i++){ if(w[i]>0){ colors[3*i]=col[0]; colors[3*i+1]=col[1]; colors[3*i+2]=col[2]; } } });
ageo.setAttribute("color", new THREE.BufferAttribute(colors, 3));
ageo.computeVertexNormals();
const armor = new THREE.Mesh(ageo, new THREE.MeshLambertMaterial({vertexColors:true, side:THREE.DoubleSide}));
scene.add(armor);

const ggeo = new THREE.BufferGeometry();
ggeo.setAttribute("position", new THREE.BufferAttribute(new Float32Array(DATA.ghost.positions), 3));
ggeo.setIndex(DATA.ghost.indices);
const ghostMesh = new THREE.Mesh(ggeo, new THREE.MeshBasicMaterial({color:0x33ff77, wireframe:true, transparent:true, opacity:0.22}));
scene.add(ghostMesh);

const params = {};
REGIONS.forEach(r=>{ params[r] = {rx:0, ry:0, rz:0, ox:0, oy:0, oz:0}; });

const SLIDERS = [["rx","rot X (raise/lower)",-45,45,0.5,"deg"],["ry","rot Y (twist)",-45,45,0.5,"deg"],["rz","rot Z (open/close)",-45,45,0.5,"deg"],["ox","move X",-0.15,0.15,0.005,"m"],["oy","move Y",-0.15,0.15,0.005,"m"],["oz","move Z",-0.15,0.15,0.005,"m"]];
const ctrl = document.getElementById("controls");
REGIONS.forEach(r=>{
  const col = REGION_COLORS[r];
  const h = document.createElement("h3");
  h.textContent = LABELS[r];
  h.style.background = "rgba(" + Math.round(col[0]*255) + "," + Math.round(col[1]*255) + "," + Math.round(col[2]*255) + ",0.25)";
  ctrl.appendChild(h);
  SLIDERS.forEach(function(s){
    const k=s[0], label=s[1], mn=s[2], mx=s[3], st=s[4], unit=s[5];
    const row = document.createElement("div"); row.className="rowg";
    const lab = document.createElement("span"); lab.textContent = label;
    const inp = document.createElement("input"); inp.type="range"; inp.min=mn; inp.max=mx; inp.step=st; inp.value=0;
    inp.id = r+"_"+k;
    const val = document.createElement("span"); val.textContent = "0"; val.id = r+"_"+k+"_v";
    inp.addEventListener("input", function(){
      params[r][k] = parseFloat(inp.value);
      val.textContent = inp.value + (unit==="deg" ? "\\u00b0" : "");
      if (document.getElementById("mirror").checked && MIRROR_OF[r]){
        const m = MIRROR_OF[r];
        const table = {rx:[1,"rx"], ry:[-1,"ry"], rz:[-1,"rz"], ox:[-1,"ox"], oy:[1,"oy"], oz:[1,"oz"]};
        const mk = table[k];
        params[m][mk[1]] = mk[0]*params[r][k];
        const mi = document.getElementById(m+"_"+mk[1]);
        mi.value = params[m][mk[1]];
        document.getElementById(m+"_"+mk[1]+"_v").textContent = String(params[m][mk[1]]) + (unit==="deg" ? "\\u00b0" : "");
      }
      recompute();
    });
    row.appendChild(lab); row.appendChild(inp); row.appendChild(val);
    ctrl.appendChild(row);
  });
});

const _e = new THREE.Euler(), _m = new THREE.Matrix4(), _v = new THREE.Vector3(), _pv = new THREE.Vector3();
function recompute(){
  livePos.set(basePos);
  REGIONS.forEach(function(r, ri){
    const p = params[r];
    if (!p.rx && !p.ry && !p.rz && !p.ox && !p.oy && !p.oz) return;
    const piv = DATA.armor.pivots[r]; if(!piv) return;
    _pv.set(piv[0], piv[1], piv[2]);
    _e.set(p.rx*Math.PI/180, p.ry*Math.PI/180, p.rz*Math.PI/180, "XYZ");
    _m.makeRotationFromEuler(_e);
    const w = DATA.armor.weights[ri];
    for (let i=0;i<w.length;i++){
      const wi = w[i]; if (wi<=0) continue;
      _v.set(basePos[3*i], basePos[3*i+1], basePos[3*i+2]).sub(_pv).applyMatrix4(_m).add(_pv);
      _v.x += p.ox; _v.y += p.oy; _v.z += p.oz;
      livePos[3*i]   += wi*(_v.x - livePos[3*i]);
      livePos[3*i+1] += wi*(_v.y - livePos[3*i+1]);
      livePos[3*i+2] += wi*(_v.z - livePos[3*i+2]);
    }
  });
  ageo.attributes.position.needsUpdate = true;
  ageo.computeVertexNormals();
}
function resetAll(){
  REGIONS.forEach(function(r){
    const p = params[r];
    for (const k in p) p[k] = 0;
    SLIDERS.forEach(function(s){
      document.getElementById(r+"_"+s[0]).value = 0;
      document.getElementById(r+"_"+s[0]+"_v").textContent = "0";
    });
  });
  recompute();
}
function exportJson(){
  const out = {};
  REGIONS.forEach(function(r){
    const p = params[r];
    if (p.rx||p.ry||p.rz||p.ox||p.oy||p.oz){
      out[r] = {pivot: DATA.armor.pivots[r], rot_deg:[p.rx,p.ry,p.rz], offset:[p.ox,p.oy,p.oz]};
    }
  });
  document.getElementById("json").value = JSON.stringify(out, null, 1);
}
function copyJson(){ const t=document.getElementById("json"); t.select(); document.execCommand("copy"); }

__VC_RESIZE__
applyCam();
__VC_LOOP__
window.setView=setView; window.exportJson=exportJson; window.resetAll=resetAll; window.copyJson=copyJson; window.ghostMesh=ghostMesh;
window.basePos=basePos; window.livePos=livePos;
</script></body></html>"""


def load_viewer_core(path=None):
    """Load viewer_core.py from path or the two repo locations and check it is the version this page was written for."""
    candidates = [Path(path)] if path else list(VIEWER_CORE_CANDIDATES)
    for candidate in candidates:
        if not candidate.is_file():
            continue
        spec = importlib.util.spec_from_file_location("viewer_core", candidate)
        if spec is None or spec.loader is None:
            continue
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if getattr(module, "VIEWER_CORE_CONTRACT", None) != VIEWER_CORE_CONTRACT:
            continue
        if getattr(module, "THREE_VERSION", None) != THREE_VERSION:
            continue
        if not all(callable(getattr(module, name, None)) for name in VIEWER_CORE_FUNCTIONS):
            continue
        return module
    raise ImportError(
        "viewer_core.py (contract %s, three %s) not found; looked at: %s"
        % (VIEWER_CORE_CONTRACT, THREE_VERSION, ", ".join(str(c) for c in candidates))
    )


def build_html(data_json, title, vc):
    """The full page: data_json is the text of align_data.json, vc the loaded viewer core."""
    head = HTML_HEAD.replace("__TITLE__", html.escape(title))
    body = (
        HTML_JS.replace("__DATA__", data_json)
        .replace("__VC_IMPORTS__", vc.module_imports(three_alias="THREE"))
        .replace("__VC_BOOT__", vc.boot_js(
            three="THREE",
            scene="scene",
            camera="camera",
            renderer="renderer",
            controls=None,
            grid="grid",
            canvas_expr='document.getElementById("c")',
            background="0x1a1a2e",
            fov=50,
            near=0.01,
            far=100,
            pixel_ratio="window.devicePixelRatio",
            grid_size=2,
            grid_divisions=20,
            grid_color1="0x333344",
            grid_color2="0x222233",
            resize=False,
            loop=False,
        ))
        .replace("__VC_RESIZE__", vc.resize_js(
            fn="doResize",
            camera="camera",
            renderer="renderer",
            mode="window",
            update_style=False,
            listen=True,
            call_now=True,
        ))
        .replace("__VC_LOOP__", vc.loop_js(
            renderer="renderer",
            scene="scene",
            camera="camera",
            controls=None,
        ))
    )
    page = head + vc.importmap_script() + "\n" + body
    assert "__DATA__" not in page and "__VC_" not in page and "__TITLE__" not in page
    assert page.count('id="controls"') == 1
    return page


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build the alignment viewer page from align_data.json.")
    parser.add_argument("--data", required=True, help="align_data.json written by alignment_viewer_extract.py")
    parser.add_argument("--out", help="output .html (default: alignment_viewer.html next to the data file)")
    parser.add_argument("--title", default="Clothing alignment viewer")
    parser.add_argument("--viewer-core", help="path of viewer_core.py when it is not at a repo location")
    args = parser.parse_args(argv)

    try:
        vc = load_viewer_core(args.viewer_core)
    except ImportError as exc:
        print("[FAIL]  %s" % exc, file=sys.stderr)
        return 2
    with open(args.data, encoding="utf-8") as f:
        data_json = f.read()
    out_path = args.out or os.path.join(os.path.dirname(os.path.abspath(args.data)), "alignment_viewer.html")
    page = build_html(data_json, args.title, vc)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(page)
    print("viewer written: %s (%.1f MB)" % (out_path, os.path.getsize(out_path) / 1048576.0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
