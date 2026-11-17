#!/usr/bin/env python3
"""DayZ weapon grip / hands / ADS viewer + validator.

Compares a custom weapon .p3d (MLOD) against a known-good vanilla reference
(MLOD, debinarize first if ODOL) in the SAME model space, and renders an
interactive Three.js viewer focused on how the player will hold and aim it:

  - both meshes overlaid (ref as translucent ghost);
  - memory points of both, with a vanilla-pattern checklist (presence + count);
  - bore line (konec hlavne -> usti hlavne), ADS line (eye -> usti hlavne),
    angular deviations vs the reference;
  - estimated hand zones derived from the REFERENCE weapon (the .anm IK the
    custom weapon inherits is authored against the reference geometry), so
    grip/handguard overlap can be judged visually;
  - world origin axes (the frame the engine anchors to RightHand_Dummy /
    Weapon_Root via the player .anm).

Weapon .p3d files carry NO hand memory points: hands come from the player-side
.anm via the weapon's ASI. Hand zones drawn here are estimates from reference
memory points/proxies and are labeled as such.

Usage:
  python weapon_grip_viewer.py --weapon W.p3d --ref REF.p3d --out viewer.html \
      [--ref-label "AKM vanilla"] [--report report.json]

Both files must be MLOD and already in final model space (offsets applied).

Needs the DayZ fork of py3d (scripts/tools/py3d in this repo) and
viewer_core.py from skills/_shared. Offline tool: it reads the two .p3d files
it is given by path and needs neither P:\\, DayZ Tools nor the game, so it does
not gate on /dayz-preflight.
"""
import argparse, json, math, os


def _load_viewer_core():
    """Bounded locator; same rules as viewer_core.load_viewer_core."""
    import ast as _ast
    import importlib.util as _ilu
    here = os.path.dirname(os.path.abspath(__file__))

    def _under(child, parent):
        child = os.path.normcase(os.path.abspath(child))
        parent = os.path.normcase(os.path.abspath(parent))
        try:
            return os.path.commonpath([child, parent]) == parent
        except ValueError:
            return False

    def _boundary(d):
        if os.path.isdir(os.path.join(d, "skills")):
            return True
        if os.path.isdir(os.path.join(d, "dayz_3d_viewer")):
            return True
        if os.path.isdir(os.path.join(d, ".git")):
            return True
        patched = os.path.join(d, "patched")
        return os.path.isdir(patched) and _under(here, patched)

    def _layout():
        if os.path.normcase(os.path.basename(here)) == os.path.normcase("dayz_3d_viewer"):
            return "package"
        d = here
        seen_l = set()
        while d not in seen_l:
            seen_l.add(d)
            name = os.path.normcase(os.path.basename(d))
            if name == os.path.normcase("skills"):
                return "skills"
            if name == os.path.normcase("patched"):
                return "workspace"
            parent = os.path.dirname(d)
            if parent == d:
                break
            d = parent
        return "standalone"

    def _looks(path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                src = fh.read()
        except OSError:
            return False
        try:
            tree = _ast.parse(src, filename=path)
        except (SyntaxError, ValueError):
            return False
        assigned = {}
        funcs = set()
        for node in tree.body:
            if isinstance(node, _ast.Assign) and isinstance(node.value, _ast.Constant):
                for target in node.targets:
                    if isinstance(target, _ast.Name):
                        assigned[target.id] = node.value.value
            elif (
                isinstance(node, _ast.AnnAssign)
                and isinstance(node.target, _ast.Name)
                and isinstance(node.value, _ast.Constant)
            ):
                assigned[node.target.id] = node.value.value
            elif isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
                funcs.add(node.name)
        return (
            assigned.get("VIEWER_CORE_CONTRACT") == "dayz-viewer-core/1"
            and assigned.get("THREE_VERSION") == "0.185.1"
            and {"importmap_script", "module_imports", "boot_js", "loop_js"} <= funcs
        )

    def _cands(d, kind):
        out = []
        if d == here and kind in ("package", "standalone"):
            out.append(os.path.join(d, "viewer_core.py"))
        out.append(os.path.join(d, "_shared", "viewer_core.py"))
        out.append(os.path.join(d, "skills", "_shared", "viewer_core.py"))
        out.append(os.path.join(d, "dayz_3d_viewer", "viewer_core.py"))
        if d != here and _boundary(d):
            out.append(os.path.join(d, "viewer_core.py"))
        return out

    kind = _layout()
    d = here
    seen = set()
    while d not in seen:
        seen.add(d)
        for path in _cands(d, kind):
            if os.path.isfile(path) and _looks(path):
                spec = _ilu.spec_from_file_location("viewer_core", path)
                if spec is None or spec.loader is None:
                    continue
                mod = _ilu.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if getattr(mod, "VIEWER_CORE_CONTRACT", None) != "dayz-viewer-core/1":
                    continue
                if getattr(mod, "THREE_VERSION", None) != "0.185.1":
                    continue
                if not all(
                    callable(getattr(mod, n, None))
                    for n in ("importmap_script", "module_imports", "boot_js", "loop_js")
                ):
                    continue
                return mod
        if kind == "standalone" or _boundary(d):
            break
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    raise ImportError(
        "viewer_core.py not found within pack/workspace root walking parents of %s"
        % os.path.abspath(__file__)
    )


vc = _load_viewer_core()

MEMORY_LO, MEMORY_HI = 9e14, 2e15

# Vanilla rifle memory-point pattern. Counts measured by the source project on
# a debinarized dz\weapons\firearms\akm\akm.p3d (memory LOD); not checked on
# P:\ here. What 'weapon back' is for is not documented; having it matches
# vanilla.
REQUIRED = [
    ("eye", 1), ("usti hlavne", 1), ("konec hlavne", 1),
    ("nabojnicestart", 1), ("nabojniceend", 1),
    ("bolt_axis", 2), ("trigger_axis", 2), ("magazine_axis", 2), ("recoil", 2),
    ("weapon back", 1), ("ce_center", 1), ("ce_radius", 1), ("invview", 1),
    ("boundingbox_min", 1), ("boundingbox_max", 1),
]

def read_p3d(path):
    import py3d
    with open(path, "rb") as f:
        return py3d.P3D(f)

def lod0_geo(model):
    lod = min((l for l in model.lods if l.points and l.resolution < 1e4),
              key=lambda x: x.resolution)
    pos = [[round(c, 5) for c in p.coords] for p in lod.points]
    # Strip proxy triangles (long degenerate faces that spike the render)
    sels = lod.selections
    items = sels.items() if isinstance(sels, dict) else [(s.name, s) for s in sels]
    proxy_faces = set()
    for name, s in items:
        if name.startswith("proxy:") or "\\" in name:
            proxy_faces.update(id(fc) for fc in s.faces.keys())
    faces = []
    for face in lod.faces:
        if id(face) in proxy_faces:
            continue
        vi = [v.point_index for v in face.vertices]
        if len(vi) == 3:
            faces.append(vi)
        elif len(vi) == 4:
            faces.append([vi[0], vi[1], vi[2]]); faces.append([vi[0], vi[2], vi[3]])
        else:
            for k in range(1, len(vi) - 1):
                faces.append([vi[0], vi[k], vi[k + 1]])
    return pos, faces

def memory_points(model):
    out = {}
    for lod in model.lods:
        if MEMORY_LO < lod.resolution < MEMORY_HI:
            sels = lod.selections
            items = sels.items() if isinstance(sels, dict) else [(s.name, s) for s in sels]
            for name, s in items:
                out[name] = [[round(c, 5) for c in k.coords] for k in s.points.keys()]
    return out

def sub(a, b): return [a[0]-b[0], a[1]-b[1], a[2]-b[2]]
def norm(v):
    l = math.sqrt(sum(c*c for c in v)) or 1.0
    return [c/l for c in v]
def angle_deg(a, b):
    a, b = norm(a), norm(b)
    d = max(-1.0, min(1.0, sum(x*y for x, y in zip(a, b))))
    return math.degrees(math.acos(d))
def mid(pts):
    n = len(pts)
    return [sum(p[i] for p in pts)/n for i in range(3)]

def bore_metrics(mp):
    """Bore line and eye metrics for one weapon. Returns None pieces if points missing."""
    m = {}
    usti = mp.get("usti hlavne", [None])[0]
    konec = mp.get("konec hlavne", [None])[0]
    eye = mp.get("eye", [None])[0]
    m["usti"], m["konec"], m["eye"] = usti, konec, eye
    if usti and konec:
        d = norm(sub(usti, konec))
        m["bore_dir"] = d
        # tilt out of the horizontal plane (Y up in model space)
        m["bore_tilt_deg"] = round(math.degrees(math.asin(max(-1, min(1, d[1])))), 2)
        if eye:
            # bore line extended to eye.x (param along x dominates for rifles)
            t = (eye[0] - konec[0]) / (usti[0] - konec[0]) if usti[0] != konec[0] else 0.0
            on_bore = [konec[i] + t * (usti[i] - konec[i]) for i in range(3)]
            m["eye_height_over_bore"] = round(eye[1] - on_bore[1], 4)
            m["eye_lateral_off_bore"] = round(eye[2] - on_bore[2], 4)
            m["ads_dir"] = norm(sub(usti, eye))
            m["ads_vs_bore_deg"] = round(angle_deg(m["ads_dir"], d), 2)
    return m

def axis_dir(mp, name):
    pts = mp.get(name)
    if pts and len(pts) >= 2:
        return norm(sub(pts[1], pts[0]))
    return None

def analyze(w_mp, r_mp):
    checks, metrics = [], {}
    for name, count in REQUIRED:
        have = len(w_mp.get(name, []))
        if have == 0:
            st, msg = "missing", "missing (vanilla: %d pt%s)" % (count, "s" if count > 1 else "")
        elif have != count:
            st, msg = "warn", "%d pts (vanilla: %d)" % (have, count)
        else:
            st, msg = "ok", "%d pt%s" % (have, "s" if have > 1 else "")
        checks.append({"name": name, "status": st, "msg": msg})
    wb, rb = bore_metrics(w_mp), bore_metrics(r_mp)
    metrics["weapon"], metrics["ref"] = wb, rb
    findings = []
    if wb.get("bore_dir") and rb.get("bore_dir"):
        dv = round(angle_deg(wb["bore_dir"], rb["bore_dir"]), 2)
        metrics["bore_delta_vs_ref_deg"] = dv
        if dv > 1.5:
            findings.append({"status": "warn", "msg":
                "konec->usti line is %.2f deg off the reference (konec off the barrel axis?)" % dv})
    if wb.get("bore_tilt_deg") is not None and abs(wb["bore_tilt_deg"]) > 1.5:
        findings.append({"status": "warn", "msg":
            "bore tilted %.2f deg from the horizontal plane (vanilla AKM: 0.0)" % wb["bore_tilt_deg"]})
    if wb.get("eye_height_over_bore") is not None and rb.get("eye_height_over_bore") is not None:
        d = wb["eye_height_over_bore"] - rb["eye_height_over_bore"]
        metrics["eye_height_delta_vs_ref"] = round(d, 4)
        if abs(d) > 0.02:
            findings.append({"status": "warn", "msg":
                "eye sits %.1f cm %s over the bore than the reference (iron sights / ADS camera)" %
                (abs(d) * 100, "higher" if d > 0 else "lower")})
    for ax in ("bolt_axis", "trigger_axis", "magazine_axis", "recoil"):
        wd, rd = axis_dir(w_mp, ax), axis_dir(r_mp, ax)
        if wd and rd:
            dv = round(min(angle_deg(wd, rd), angle_deg(wd, [-c for c in rd])), 2)
            if dv > 5:
                findings.append({"status": "warn", "msg":
                    "%s is %.1f deg off the reference's orientation" % (ax, dv)})
    we = [w_mp.get("nabojnicestart", [None])[0], w_mp.get("nabojniceend", [None])[0]]
    re_ = [r_mp.get("nabojnicestart", [None])[0], r_mp.get("nabojniceend", [None])[0]]
    if all(we) and all(re_):
        dv = round(angle_deg(sub(we[1], we[0]), sub(re_[1], re_[0])), 2)
        if dv > 25:
            findings.append({"status": "warn", "msg":
                "case ejection direction is %.0f deg off the reference" % dv})
    return checks, metrics, findings

def hand_zones(r_mp, r_proxies):
    """Estimated hand zones FROM THE REFERENCE weapon (its .anm is what the
    custom weapon inherits). Approximations, labeled as such in the UI."""
    zones = []
    trig = r_mp.get("trigger_axis")
    if trig:
        m = mid(trig)
        zones.append({"name": "Right hand (grip) ~", "pos": [m[0]+0.035, m[1]-0.05, m[2]],
                      "r": 0.05})
    hg = None
    for name, pts in r_proxies.items():
        if "handguard" in name.lower() or "foregrip" in name.lower():
            hg = pts[0]; break
    if hg is None:
        usti = r_mp.get("usti hlavne", [None])[0]
        konec = r_mp.get("konec hlavne", [None])[0]
        if usti and konec:
            hg = [konec[i] + 0.55*(usti[i]-konec[i]) for i in range(3)]
            hg[1] -= 0.035
    if hg:
        zones.append({"name": "Left hand (handguard) ~", "pos": list(hg), "r": 0.05})
    return zones

def split_mp(mp):
    """Separate plain memory points from proxy selections."""
    pts, proxies = {}, {}
    for name, coords in mp.items():
        if name.startswith("proxy:") or "\\" in name:
            proxies[name] = coords
        else:
            pts[name] = coords
    return pts, proxies

HTML = r"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Grip check — __MODEL__</title>
<style>
  html,body{margin:0;height:100%;background:#1a1d21;color:#dfe3e8;font:13px/1.4 system-ui,sans-serif;overflow:hidden}
  #wrap{display:flex;height:100vh}
  #side{width:320px;background:#23272e;border-right:1px solid #333;display:flex;flex-direction:column}
  #side h1{font-size:14px;margin:0;padding:12px;border-bottom:1px solid #333;color:#fff}
  #side h1 small{display:block;color:#8b93a0;font-weight:400;font-size:11px;margin-top:3px}
  #list{flex:1;overflow:auto;font-variant-numeric:tabular-nums}
  .sec{padding:7px 12px;background:#1e2228;color:#9aa3b0;font-size:11px;text-transform:uppercase;letter-spacing:.05em;border-bottom:1px solid #2b2f37}
  .row{padding:6px 12px;border-bottom:1px solid #2b2f37;display:flex;gap:8px;align-items:baseline;cursor:default}
  .row:hover{background:#2b313a}
  .st{width:14px;flex:none;font-weight:700}
  .ok .st{color:#5fd38a}.warn .st{color:#ffb454}.missing .st{color:#ff6b6b}
  .row .nm{font-weight:600;white-space:nowrap}
  .row .ms{color:#8b93a0;font-size:11px;margin-left:auto;text-align:right}
  #foot{padding:10px 12px;border-top:1px solid #333;font-size:11px;color:#8b93a0}
  #main{flex:1;position:relative}
  #cv{display:block;width:100%;height:100%}
  #bar{position:absolute;top:10px;left:10px;display:flex;gap:6px;flex-wrap:wrap;max-width:78%}
  button{background:#2f3742;color:#dfe3e8;border:1px solid #444;border-radius:5px;padding:6px 10px;cursor:pointer;font-size:12px}
  button:hover{background:#3a4350}
  button.on{background:#3f6bd6;border-color:#3f6bd6;color:#fff}
  .lbl{position:absolute;transform:translate(-50%,-120%);background:rgba(0,0,0,.65);padding:1px 5px;border-radius:3px;font-size:10px;pointer-events:none;white-space:nowrap}
  #read{position:absolute;bottom:10px;left:10px;background:rgba(20,22,26,.9);border:1px solid #333;border-radius:6px;padding:10px;min-width:280px;font-variant-numeric:tabular-nums;font-size:12px}
  #read b{color:#fff} #read .g{color:#8b93a0}
</style></head><body>
<div id="wrap">
  <div id="side">
    <h1>Grip check<small>__MODEL__ · ghost = __REFLABEL__</small></h1>
    <div id="list"></div>
    <div id="foot">Hands = zones ESTIMATED from the reference (the real hands come from the player's .anm, not the .p3d)</div>
  </div>
  <div id="main">
    <canvas id="cv"></canvas>
    <div id="bar">
      <button id="bW" class="on">Weapon</button>
      <button id="bG" class="on">Ref ghost</button>
      <button id="bP" class="on">Weapon points</button>
      <button id="bPR">Ref points</button>
      <button id="bL" class="on">Bore/ADS</button>
      <button id="bH" class="on">Hands</button>
      <button id="bO" class="on">Origin</button>
      <button id="bWire">Wireframe</button>
      <button id="bGrid" class="on">Grid</button>
      <button id="bLbl" class="on">Labels</button>
    </div>
    <div id="read"></div>
  </div>
</div>
__VC_IMPORTMAP__
<script type="module">
__VC_IMPORTS__
const R = __DATA__;
const cv = document.getElementById('cv');
const bb=R.bbox, ctr=[(bb.min[0]+bb.max[0])/2,(bb.min[1]+bb.max[1])/2,(bb.min[2]+bb.max[2])/2];
const span=Math.max(bb.max[0]-bb.min[0],bb.max[1]-bb.min[1],bb.max[2]-bb.min[2])||1;
__VC_BOOT__
cam.position.set(ctr[0]+span*0.35, ctr[1]+span*0.28, ctr[2]+span*0.95);
orbit.target.set(ctr[0],ctr[1],ctr[2]);
scene.add(new T.AmbientLight(0xffffff,0.55));
const k=new T.DirectionalLight(0xffffff,0.8); k.position.set(2,4,3); scene.add(k);
const f2=new T.DirectionalLight(0x88aaff,0.4); f2.position.set(-3,2,-2); scene.add(f2);
grid.position.set(ctr[0],bb.min[1],ctr[2]);

function mesh(geo, mat){
  const g=new T.BufferGeometry();
  g.setAttribute('position', new T.BufferAttribute(new Float32Array(geo.positions.flat()),3));
  g.setIndex(geo.faces.flat()); g.computeVertexNormals();
  return new T.Mesh(g, mat);
}
const wMesh = mesh(R.weapon, new T.MeshStandardMaterial({color:0xb8c0cc,roughness:0.85,side:T.DoubleSide}));
scene.add(wMesh);
const wWire = new T.LineSegments(new T.WireframeGeometry(wMesh.geometry), new T.LineBasicMaterial({color:0x556070}));
wWire.visible=false; scene.add(wWire);
const gMesh = mesh(R.ref, new T.MeshStandardMaterial({color:0x4fa3ff,transparent:true,opacity:0.32,side:T.DoubleSide,depthWrite:false}));
scene.add(gMesh);

/* overlays: MeshBasicMaterial (unlit), so scene lighting cannot dim or hide them */
const lblLayer=document.getElementById('main');
const labels=[];
function label(txt,obj,color){
  const d=document.createElement('div'); d.className='lbl'; d.textContent=txt;
  if(color) d.style.color=color;
  lblLayer.appendChild(d); labels.push({el:d,obj:obj});
  return d;
}
const STC={ok:0x35e08a, warn:0xffb454, missing:0xff5d5d};
const wPts=new T.Group(), rPts=new T.Group(), lines=new T.Group(), hands=new T.Group();
scene.add(wPts); scene.add(rPts); scene.add(lines); scene.add(hands);
rPts.visible=false;
const stByName={}; R.checks.forEach(c=>stByName[c.name]=c.status);
const rad=Math.max(span*0.006,0.004);
for(const [name,pts] of Object.entries(R.weapon_mp)){
  const col=STC[stByName[name]||'ok']||0x35e08a;
  pts.forEach((p,i)=>{
    const s=new T.Mesh(new T.SphereGeometry(rad,12,10), new T.MeshBasicMaterial({color:col}));
    s.position.set(p[0],p[1],p[2]); wPts.add(s);
    if(i===0) label(name,s,'#'+new T.Color(col).getHexString());
  });
  if(pts.length===2){
    const g=new T.BufferGeometry().setFromPoints(pts.map(p=>new T.Vector3(...p)));
    wPts.add(new T.Line(g,new T.LineBasicMaterial({color:col})));
  }
}
for(const [name,pts] of Object.entries(R.ref_mp)){
  pts.forEach((p,i)=>{
    const s=new T.Mesh(new T.SphereGeometry(rad*0.9,8,8), new T.MeshBasicMaterial({color:0x4fa3ff,wireframe:true}));
    s.position.set(p[0],p[1],p[2]); rPts.add(s);
    if(i===0){const l=label(name,s,'#7fc4ff'); l.style.opacity=0.7;}
  });
}
/* missing points: hollow red marker at the REF position (where vanilla puts it) */
R.checks.filter(c=>c.status==='missing').forEach(c=>{
  (R.ref_mp[c.name]||[]).forEach(p=>{
    const s=new T.Mesh(new T.SphereGeometry(rad*1.3,8,8), new T.MeshBasicMaterial({color:0xff5d5d,wireframe:true}));
    s.position.set(p[0],p[1],p[2]); wPts.add(s);
    label(c.name+' (MISSING)',s,'#ff8080');
  });
});
function line(a,b,color,dashed){
  const g=new T.BufferGeometry().setFromPoints([new T.Vector3(...a),new T.Vector3(...b)]);
  const m=dashed?new T.LineDashedMaterial({color:color,dashSize:0.02,gapSize:0.012}):new T.LineBasicMaterial({color:color});
  const l=new T.Line(g,m); if(dashed)l.computeLineDistances();
  lines.add(l); return l;
}
const MW=R.metrics.weapon, MR=R.metrics.ref;
function ext(a,d,t){return [a[0]+d[0]*t,a[1]+d[1]*t,a[2]+d[2]*t];}
if(MW.konec&&MW.usti){ line(MW.konec, ext(MW.usti,MW.bore_dir,0.15), 0xffe000); label('weapon bore',{position:new T.Vector3(...MW.usti)},'#ffe000'); }
if(MR.konec&&MR.usti){ line(MR.konec, ext(MR.usti,MR.bore_dir,0.15), 0x33bbff, true); }
if(MW.eye&&MW.usti){ line(MW.eye, ext(MW.usti,MW.ads_dir,0.1), 0xff5bd6, true); label('ADS',{position:new T.Vector3(...MW.eye)},'#ff5bd6'); }
R.hands.forEach(h=>{
  const s=new T.Mesh(new T.SphereGeometry(h.r,16,12), new T.MeshBasicMaterial({color:0x00ff66,transparent:true,opacity:0.28,depthWrite:false}));
  s.position.set(h.pos[0],h.pos[1],h.pos[2]); hands.add(s);
  const c=new T.Mesh(new T.SphereGeometry(0.006,8,8), new T.MeshBasicMaterial({color:0x00ff66}));
  c.position.copy(s.position); hands.add(c);
  label(h.name,s,'#7dffb0');
});
const org=new T.AxesHelper(0.12); scene.add(org);
label('origin (hand anchor)',{position:new T.Vector3(0,0,0)},'#ccc');

/* side panel */
const list=document.getElementById('list');
function sec(t){const d=document.createElement('div');d.className='sec';d.textContent=t;list.appendChild(d);}
function row(cls,nm,ms){
  const d=document.createElement('div');d.className='row '+cls;
  d.innerHTML='<span class="st">'+(cls==='ok'?'✓':cls==='warn'?'⚠':'✗')+'</span><span class="nm">'+nm+'</span><span class="ms">'+ms+'</span>';
  list.appendChild(d);
}
sec('Memory point checklist (vanilla pattern)');
R.checks.forEach(c=>row(c.status,c.name,c.msg));
sec('Findings');
if(R.findings.length===0) row('ok','nothing unusual','');
R.findings.forEach(f=>row(f.status,'',f.msg));
sec('Metrics');
function met(n,v){row('ok',n,v);}
if(R.metrics.bore_delta_vs_ref_deg!==undefined) met('bore vs ref', R.metrics.bore_delta_vs_ref_deg+' deg');
if(MW.bore_tilt_deg!==undefined) met('bore tilt (weapon)', MW.bore_tilt_deg+' deg');
if(MW.eye_height_over_bore!==undefined) met('eye over bore (weapon)', (MW.eye_height_over_bore*100).toFixed(1)+' cm');
if(MR.eye_height_over_bore!==undefined) met('eye over bore (ref)', (MR.eye_height_over_bore*100).toFixed(1)+' cm');
if(MW.ads_vs_bore_deg!==undefined) met('ADS vs bore (weapon)', MW.ads_vs_bore_deg+' deg');

const read=document.getElementById('read');
read.innerHTML='<b>'+R.model+'</b> vs <b>'+R.ref_label+'</b><br><span class="g">'+
  R.checks.filter(c=>c.status==='ok').length+' ok · '+
  R.checks.filter(c=>c.status==='warn').length+' warn · '+
  R.checks.filter(c=>c.status==='missing').length+' missing · '+
  R.findings.length+' findings</span>';

function bindToggle(id,fn,init){
  const b=document.getElementById(id);
  let on=init===undefined?true:init;
  const apply=()=>{b.classList.toggle('on',on);fn(on);};
  b.onclick=()=>{on=!on;apply();}; apply();
}
bindToggle('bW',v=>wMesh.visible=v);
bindToggle('bG',v=>gMesh.visible=v);
bindToggle('bP',v=>wPts.visible=v);
bindToggle('bPR',v=>rPts.visible=v,false);
bindToggle('bL',v=>lines.visible=v);
bindToggle('bH',v=>hands.visible=v);
bindToggle('bO',v=>org.visible=v);
bindToggle('bWire',v=>{wWire.visible=v;},false);
bindToggle('bGrid',v=>grid.visible=v);
bindToggle('bLbl',v=>labels.forEach(l=>l.el.style.display=v?'block':'none'));

const wp=new T.Vector3();
function __vcFrame(){
  labels.forEach(l=>{
    if(l.el.style.display==='none')return;
    const o=l.obj; (o.getWorldPosition?o.getWorldPosition(wp):wp.copy(o.position));
    wp.project(cam);
    const r=cv.getBoundingClientRect();
    l.el.style.left=((wp.x*0.5+0.5)*r.width)+'px';
    l.el.style.top=((-wp.y*0.5+0.5)*r.height)+'px';
    l.el.style.opacity=(wp.z<1)?l.el.style.opacity||1:0;
  });
}
</script></body></html>
"""

def _fill_html(data):
    html = (HTML.replace("__DATA__", json.dumps(data))
                .replace("__MODEL__", data["model"])
                .replace("__REFLABEL__", data["ref_label"]))
    html = html.replace("__VC_IMPORTMAP__", vc.importmap_script())
    html = html.replace("__VC_IMPORTS__", vc.module_imports(("OrbitControls",), three_alias="T"))
    html = html.replace("__VC_BOOT__", vc.boot_js(
        three="T",
        scene="scene",
        camera="cam",
        renderer="ren",
        controls="orbit",
        grid="grid",
        canvas_expr="cv",
        background="0x1a1d21",
        fov=50,
        near=0.005,
        far=100,
        grid_size=2,
        grid_divisions=20,
        grid_color1="0x445566",
        grid_color2="0x2c333d",
        resize="parent",
        post_controls_hook="__vcFrame",
    ))
    return html


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weapon")
    ap.add_argument("--ref")
    ap.add_argument("--out", required=True)
    ap.add_argument("--ref-label", default=None)
    ap.add_argument("--report", default=None)
    ap.add_argument("--data", default=None, help="prebuilt JSON fixture (skip .p3d)")
    a = ap.parse_args()

    if a.data:
        with open(a.data, encoding="utf-8") as f:
            data = json.load(f)
        html = _fill_html(data)
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(html)
        with open(a.out, encoding="utf-8") as f:
            back = f.read()
        assert back == html, "read-after-write mismatch"
        assert back.rstrip().endswith("</html>"), "HTML truncated"
        print("viewer -> %s (%d bytes) [from --data]" % (a.out, len(html)))
        return

    if not a.weapon or not a.ref:
        ap.error("--weapon and --ref are required unless --data is set")

    w, r = read_p3d(a.weapon), read_p3d(a.ref)
    w_pos, w_faces = lod0_geo(w)
    r_pos, r_faces = lod0_geo(r)
    w_mp_all, r_mp_all = memory_points(w), memory_points(r)
    w_mp, w_prox = split_mp(w_mp_all)
    r_mp, r_prox = split_mp(r_mp_all)
    checks, metrics, findings = analyze(w_mp, r_mp)
    hands = hand_zones(r_mp, r_prox)

    xs = [p[0] for p in w_pos]; ys = [p[1] for p in w_pos]; zs = [p[2] for p in w_pos]
    data = {
        "model": os.path.basename(a.weapon),
        "ref_label": a.ref_label or os.path.basename(a.ref),
        "bbox": {"min": [min(xs), min(ys), min(zs)], "max": [max(xs), max(ys), max(zs)]},
        "weapon": {"positions": w_pos, "faces": w_faces},
        "ref": {"positions": r_pos, "faces": r_faces},
        "weapon_mp": w_mp, "ref_mp": r_mp,
        "checks": checks, "metrics": metrics, "findings": findings, "hands": hands,
    }
    html = _fill_html(data)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(html)
    with open(a.out, encoding="utf-8") as f:
        back = f.read()
    assert back == html, "read-after-write mismatch"
    assert back.rstrip().endswith("</html>"), "HTML truncated"

    print("== Grip check: %s vs %s" % (data["model"], data["ref_label"]))
    for c in checks:
        print("  [%-7s] %-18s %s" % (c["status"], c["name"], c["msg"]))
    for f_ in findings:
        print("  [%-7s] %s" % (f_["status"], f_["msg"]))
    for k_ in ("bore_delta_vs_ref_deg", "eye_height_delta_vs_ref"):
        if k_ in metrics:
            print("  %s = %s" % (k_, metrics[k_]))
    if a.report:
        rep = {"checks": checks, "metrics": metrics, "findings": findings}
        with open(a.report, "w") as f:
            json.dump(rep, f, indent=1)
        print("report -> %s" % a.report)
    print("viewer -> %s (%d bytes)" % (a.out, len(html)))

if __name__ == "__main__":
    main()
