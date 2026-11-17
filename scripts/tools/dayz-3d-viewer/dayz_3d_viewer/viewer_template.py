"""Three.js viewer generator.

Two modes:
  - embedded: bakes geometry as JSON + textures as base64 into HTML.
              Uses raw BufferGeometry — no GLTFLoader, no fetch.
  - web: references an external .glb via GLTFLoader.

three.js is loaded from the jsDelivr CDN at version 0.185.1 via viewer_core.
Generated HTML therefore needs a network to render; the file itself is offline.
"""

from __future__ import annotations

import base64
import json
import os
import struct

if __package__:
    from .deps import require_dayz_py3d
    from .errors import ViewerError
    from .p3d_to_gltf import extract_lod_geometry, find_best_visual_lod
else:
    # Standalone fixture / script: no package, so no relative imports.
    # A transitive ImportError from an installed package must not land here.
    def require_dayz_py3d():
        raise RuntimeError("dayz_3d_viewer package not installed")

    class ViewerError(Exception):
        pass

    def extract_lod_geometry(*_a, **_k):
        raise RuntimeError("dayz_3d_viewer package not installed")

    def find_best_visual_lod(*_a, **_k):
        raise RuntimeError("dayz_3d_viewer package not installed")


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


if __package__:
    from . import viewer_core as _vc
else:
    _vc = _load_viewer_core()

THREE_JS_VERSION = _vc.THREE_VERSION
THREE_CDN = _vc.THREE_CDN


def _pack_f32(values) -> bytes:
    flat = []
    for item in values:
        if isinstance(item, (tuple, list)):
            flat.extend(float(part) for part in item)
        else:
            flat.append(float(item))
    return struct.pack("<%sf" % len(flat), *flat)


def _b64_f32(values) -> str:
    return base64.b64encode(_pack_f32(values)).decode("ascii")


def _b64_u32(values) -> str:
    return base64.b64encode(
        struct.pack("<%sI" % len(values), *[int(item) for item in values])
    ).decode("ascii")


def generate_viewer_html(
    model_name="DayZ Model",
    mode="embedded",
    geometry_data=None,
    glb_path=None,
    glb_url=None,
    background="#1a1a2e",
    output_path=None,
):
    if mode == "embedded" and geometry_data:
        html = _gen_embedded(geometry_data, model_name, background)
    elif mode == "web":
        url = glb_url or (os.path.basename(glb_path) if glb_path else "model.glb")
        html = _gen_web(url, model_name, background)
    else:
        raise ViewerError("embedded needs geometry_data; web needs glb_path/glb_url")
    if output_path:
        with open(output_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(html)
    return html


def extract_geometry_for_viewer(p3d_path, texture_map=None, rvmat_data=None):
    """Extract geometry from a P3D for the embedded viewer."""
    py3d = require_dayz_py3d()
    with open(p3d_path, "rb") as handle:
        p3d_file = py3d.P3D(handle)
    lod = find_best_visual_lod(p3d_file)
    if lod is None:
        raise ViewerError("No visual LOD found")
    geo = extract_lod_geometry(lod)
    if texture_map is None:
        texture_map = {}
    if rvmat_data is None:
        rvmat_data = {}

    groups = []
    for (tex_path, mat_path), indices in geo["material_groups"].items():
        if not indices:
            continue
        mat_info = {
            "name": "default",
            "color": [0.6, 0.6, 0.6],
            "metallic": 0.1,
            "roughness": 0.8,
            "emissive": [0, 0, 0],
        }
        if mat_path:
            mat_stem = os.path.splitext(
                os.path.basename(mat_path.replace("\\", "/"))
            )[0].lower()
            mat_info["name"] = mat_stem
            rvmat = rvmat_data.get(mat_stem)
            if rvmat:
                colors = rvmat.get("colors", {})
                diffuse = colors.get("diffuse")
                if diffuse and len(diffuse) >= 3:
                    mat_info["color"] = list(diffuse[:3])
                forced = colors.get("forceddiffuse")
                if forced and len(forced) >= 3 and any(value > 0.01 for value in forced[:3]):
                    mat_info["color"] = list(forced[:3])
                spec = colors.get("specular")
                spec_power = rvmat.get("specular_power")
                if spec and len(spec) >= 3:
                    mat_info["metallic"] = min(1.0, sum(spec[:3]) / 3 * 2)
                if spec_power:
                    mat_info["roughness"] = max(0.1, 1.0 - spec_power / 100.0)
                emm = colors.get("emmisive", colors.get("emissive"))
                if emm and len(emm) >= 3 and any(value > 0.1 for value in emm[:3]):
                    peak = max(emm[0], emm[1], emm[2], 1.0)
                    mat_info["emissive"] = [
                        min(1, emm[0] / peak),
                        min(1, emm[1] / peak),
                        min(1, emm[2] / peak),
                    ]
                    mat_info["color"] = mat_info["emissive"][:]
        if tex_path:
            stem = os.path.splitext(
                os.path.basename(tex_path.replace("\\", "/"))
            )[0].lower()
            png = texture_map.get(stem)
            if png and os.path.exists(png):
                with open(png, "rb") as handle:
                    mat_info["texture_b64"] = base64.b64encode(handle.read()).decode(
                        "ascii"
                    )
        groups.append({"indices": list(indices), "material": mat_info})

    return {
        "positions": geo["positions"],
        "normals": geo["normals"],
        "uvs": geo["uvs"],
        "groups": groups,
    }


def _gen_embedded(geometry_data, model_name, bg):
    pos_b64 = _b64_f32(geometry_data["positions"])
    nrm_b64 = _b64_f32(geometry_data["normals"])
    uv_b64 = _b64_f32(geometry_data["uvs"])
    groups = []
    for group in geometry_data["groups"]:
        entry = {
            "ib": _b64_u32(group["indices"]),
            "ic": len(group["indices"]),
            "m": {
                "n": group["material"].get("name", ""),
                "c": group["material"].get("color", [0.6, 0.6, 0.6]),
                "mt": group["material"].get("metallic", 0.1),
                "r": group["material"].get("roughness", 0.8),
                "e": group["material"].get("emissive", [0, 0, 0]),
            },
        }
        if group["material"].get("texture_b64"):
            entry["m"]["t"] = group["material"]["texture_b64"]
        groups.append(entry)
    vertex_count = len(geometry_data["positions"])
    triangle_count = sum(len(group["indices"]) // 3 for group in geometry_data["groups"])
    material_count = len(geometry_data["groups"])
    model_json = json.dumps(
        {"p": pos_b64, "n": nrm_b64, "u": uv_b64, "g": groups},
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    imap = _vc.importmap_script()
    imports = _vc.module_imports(("OrbitControls",), three_alias="T")
    boot = _vc.boot_js(
        three="T",
        scene="sc",
        camera="cam",
        renderer="r",
        controls="ct",
        grid="gr",
        append_to="c",
        background=json.dumps(bg),
        fov=50,
        aspect="c.clientWidth/c.clientHeight",
        near=0.001,
        far=100,
        pixel_ratio="Math.min(devicePixelRatio,2)",
        tone_mapping="ACESFilmicToneMapping",
        tone_exposure=1.2,
        orbit_auto_rotate_speed=1.5,
        grid_size=2,
        grid_divisions=20,
        grid_color1="0x333355",
        grid_color2="0x222244",
        grid_visible=False,
        resize="container",
        container_expr="c",
    )
    return f'''<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{model_name}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:{bg};overflow:hidden;font-family:'Segoe UI',system-ui,sans-serif;color:#e0e0e0}}
#c{{width:100vw;height:100vh;position:relative}}canvas{{display:block}}
#h{{position:absolute;top:0;left:0;right:0;padding:12px 16px;display:flex;justify-content:space-between;align-items:flex-start;pointer-events:none;z-index:10}}
#h>*{{pointer-events:auto}}
#mi{{background:rgba(0,0,0,.6);backdrop-filter:blur(8px);border-radius:8px;padding:10px 14px;font-size:13px;line-height:1.5}}
#mi h2{{font-size:15px;font-weight:600;margin-bottom:4px;color:#fff}}
.s{{color:#aaa}}.s span{{color:#4fc3f7}}
#ct{{background:rgba(0,0,0,.6);backdrop-filter:blur(8px);border-radius:8px;padding:10px 14px;display:flex;gap:6px;flex-wrap:wrap}}
.b{{background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.15);color:#e0e0e0;padding:6px 12px;border-radius:6px;cursor:pointer;font-size:12px;transition:all .15s}}
.b:hover{{background:rgba(255,255,255,.2);border-color:rgba(255,255,255,.3)}}
.b.a{{background:rgba(79,195,247,.3);border-color:#4fc3f7;color:#4fc3f7}}
#ld{{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);z-index:20}}
#ld .sp{{width:40px;height:40px;border:3px solid rgba(255,255,255,.1);border-top-color:#4fc3f7;border-radius:50%;animation:sp .8s linear infinite;margin:0 auto 12px}}
@keyframes sp{{to{{transform:rotate(360deg)}}}}
#ld.hd{{display:none}}
#bb{{position:absolute;bottom:12px;left:50%;transform:translateX(-50%);background:rgba(0,0,0,.5);backdrop-filter:blur(8px);border-radius:8px;padding:8px 16px;font-size:11px;color:#666;z-index:10}}
</style></head><body>
<div id="c">
<div id="h">
<div id="mi"><h2>{model_name}</h2><div class="s">Vertices: <span>{vertex_count:,}</span></div><div class="s">Triangles: <span>{triangle_count:,}</span></div><div class="s">Materials: <span>{material_count}</span></div></div>
<div id="ct">
<button class="b" onclick="tW()" id="bw">Wireframe</button>
<button class="b" onclick="tG()" id="bg2">Grid</button>
<button class="b" onclick="tR()" id="br">Auto-Rotate</button>
<button class="b" onclick="rC()">Reset View</button>
<button class="b" onclick="tB()">BG</button>
</div></div>
<div id="ld"><div class="sp"></div></div>
<div id="bb">LMB: Orbit | RMB: Pan | Scroll: Zoom</div>
</div>
{imap}
<script type="module">
{imports}

const D=a=>{{const b=atob(a),u=new Uint8Array(b.length);for(let i=0;i<b.length;i++)u[i]=b.charCodeAt(i);return u.buffer}};
const M={model_json};

const c=document.getElementById('c');
{boot}

sc.add(new T.AmbientLight(0xffffff,.5));
const dl=new T.DirectionalLight(0xffffff,1);dl.position.set(2,3,2);sc.add(dl);
const fl=new T.DirectionalLight(0x8888ff,.3);fl.position.set(-2,1,-1);sc.add(fl);
const rl=new T.DirectionalLight(0xffffcc,.2);rl.position.set(0,-1,-2);sc.add(rl);

const pos=new Float32Array(D(M.p));
const nrm=new Float32Array(D(M.n));
const uvs=new Float32Array(D(M.u));

const mg=new T.Group(),wg=new T.Group();
let wv=false;

async function build(){{
for(const g of M.g){{
const idx=new Uint32Array(D(g.ib));
const geo=new T.BufferGeometry();
geo.setAttribute('position',new T.BufferAttribute(pos,3));
geo.setAttribute('normal',new T.BufferAttribute(nrm,3));
geo.setAttribute('uv',new T.BufferAttribute(uvs,2));
geo.setIndex(new T.BufferAttribute(idx,1));

const mp={{color:new T.Color(g.m.c[0],g.m.c[1],g.m.c[2]),metalness:g.m.mt,roughness:g.m.r,side:T.DoubleSide}};
if(g.m.e&&(g.m.e[0]>0||g.m.e[1]>0||g.m.e[2]>0)){{mp.emissive=new T.Color(g.m.e[0],g.m.e[1],g.m.e[2]);mp.emissiveIntensity=2;}}

if(g.m.t){{
const tex=await new Promise(res=>{{
const img=new Image();
img.onload=()=>{{const tx=new T.Texture(img);tx.needsUpdate=true;tx.colorSpace=T.SRGBColorSpace;res(tx)}};
img.onerror=()=>res(null);
img.src='data:image/png;base64,'+g.m.t;
}});
if(tex){{mp.map=tex;mp.color=new T.Color(1,1,1);}}
}}

mg.add(new T.Mesh(geo,new T.MeshStandardMaterial(mp)));
const wGeo=new T.WireframeGeometry(geo);
wg.add(new T.LineSegments(wGeo,new T.LineBasicMaterial({{color:0x4fc3f7,opacity:.15,transparent:true}})));
}}

sc.add(mg);wg.visible=wv;sc.add(wg);

const box=new T.Box3().setFromObject(mg);
const ctr=box.getCenter(new T.Vector3());
const sz=box.getSize(new T.Vector3());
const mx=Math.max(sz.x,sz.y,sz.z);
mg.position.sub(ctr);wg.position.sub(ctr);
const d=mx*2.5;
cam.position.set(d*.6,d*.4,d*.7);
cam.near=mx*.001;cam.far=mx*100;cam.updateProjectionMatrix();
ct.target.set(0,0,0);ct.update();
gr.scale.setScalar(Math.ceil(mx*2));
document.getElementById('ld').classList.add('hd');
}}
build();

let bi=0;const bgs=["{bg}","#0d0d0d","#2d2d2d","#f0f0f0","#1a3a1a"];
window.tW=()=>{{wv=!wv;wg.visible=wv;document.getElementById('bw').classList.toggle('a',wv)}};
window.tG=()=>{{gr.visible=!gr.visible;document.getElementById('bg2').classList.toggle('a',gr.visible)}};
window.tR=()=>{{ct.autoRotate=!ct.autoRotate;document.getElementById('br').classList.toggle('a',ct.autoRotate)}};
window.rC=()=>{{const b=new T.Box3().setFromObject(mg);const s=b.getSize(new T.Vector3());const d=Math.max(s.x,s.y,s.z)*2.5;cam.position.set(d*.6,d*.4,d*.7);ct.target.set(0,0,0)}};
window.tB=()=>{{bi=(bi+1)%bgs.length;sc.background=new T.Color(bgs[bi])}};
</script></body></html>'''


def _gen_web(url, model_name, bg):
    imap = _vc.importmap_script()
    imports = _vc.module_imports(("OrbitControls", "GLTFLoader"), three_alias="T")
    boot = _vc.boot_js(
        three="T",
        scene="sc",
        camera="cam",
        renderer="r",
        controls="ct",
        grid="gr",
        append_to="c",
        background=json.dumps(bg),
        fov=50,
        aspect="c.clientWidth/c.clientHeight",
        near=0.001,
        far=100,
        pixel_ratio="Math.min(devicePixelRatio,2)",
        tone_mapping="ACESFilmicToneMapping",
        tone_exposure=1.2,
        grid_size=2,
        grid_divisions=20,
        grid_color1="0x333355",
        grid_color2="0x222244",
        grid_visible=False,
        resize="container",
        container_expr="c",
    )
    return f'''<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{model_name}</title>
<style>*{{margin:0;padding:0;box-sizing:border-box}}body{{background:{bg};overflow:hidden;font-family:system-ui;color:#e0e0e0}}#c{{width:100vw;height:100vh;position:relative}}canvas{{display:block}}#h{{position:absolute;top:0;left:0;right:0;padding:12px 16px;display:flex;justify-content:space-between;pointer-events:none;z-index:10}}#h>*{{pointer-events:auto}}#mi{{background:rgba(0,0,0,.6);backdrop-filter:blur(8px);border-radius:8px;padding:10px 14px;font-size:13px;line-height:1.5}}#mi h2{{font-size:15px;font-weight:600;color:#fff}}.s{{color:#aaa}}.s span{{color:#4fc3f7}}#ct{{background:rgba(0,0,0,.6);backdrop-filter:blur(8px);border-radius:8px;padding:10px 14px;display:flex;gap:6px}}.b{{background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.15);color:#e0e0e0;padding:6px 12px;border-radius:6px;cursor:pointer;font-size:12px}}.b:hover{{background:rgba(255,255,255,.2)}}.b.a{{background:rgba(79,195,247,.3);border-color:#4fc3f7;color:#4fc3f7}}#bb{{position:absolute;bottom:12px;left:50%;transform:translateX(-50%);background:rgba(0,0,0,.5);border-radius:8px;padding:8px 16px;font-size:11px;color:#666;z-index:10}}</style></head>
<body><div id="c"><div id="h"><div id="mi"><h2>{model_name}</h2><div class="s">Vertices: <span id="sv">-</span></div><div class="s">Triangles: <span id="st">-</span></div><div class="s">Materials: <span id="sm">-</span></div></div><div id="ct"><button class="b" onclick="tG()" id="bg2">Grid</button><button class="b" onclick="tR()" id="br">Auto-Rotate</button><button class="b" onclick="rC()">Reset</button><button class="b" onclick="tB()">BG</button></div></div><div id="bb">LMB: Orbit | RMB: Pan | Scroll: Zoom</div></div>
{imap}
<script type="module">
{imports}
const c=document.getElementById('c');
{boot}
cam.position.set(.3,.25,.4);
sc.add(new T.AmbientLight(0xffffff,.5));const dl=new T.DirectionalLight(0xffffff,1);dl.position.set(2,3,2);sc.add(dl);
let mdl;new GLTFLoader().load("{url}",g=>{{mdl=g.scene;sc.add(mdl);const b=new T.Box3().setFromObject(mdl),ctr=b.getCenter(new T.Vector3()),s=b.getSize(new T.Vector3()),mx=Math.max(s.x,s.y,s.z);mdl.position.sub(ctr);const d=mx*2.5;cam.position.set(d*.6,d*.4,d*.7);cam.near=mx*.001;cam.far=mx*100;cam.updateProjectionMatrix();ct.target.set(0,0,0);ct.update();let v=0,t=0,m=new Set();mdl.traverse(c=>{{if(c.isMesh){{v+=c.geometry.attributes.position.count;t+=c.geometry.index?c.geometry.index.count/3:c.geometry.attributes.position.count/3;m.add(c.material?.name||'x')}}}});document.getElementById('sv').textContent=v;document.getElementById('st').textContent=Math.round(t);document.getElementById('sm').textContent=m.size}});
let bi=0;const bgs=["{bg}","#0d0d0d","#2d2d2d","#f0f0f0"];
window.tG=()=>{{gr.visible=!gr.visible;document.getElementById('bg2').classList.toggle('a',gr.visible)}};
window.tR=()=>{{ct.autoRotate=!ct.autoRotate;document.getElementById('br').classList.toggle('a',ct.autoRotate)}};
window.rC=()=>{{if(mdl){{const b=new T.Box3().setFromObject(mdl),s=b.getSize(new T.Vector3()),d=Math.max(s.x,s.y,s.z)*2.5;cam.position.set(d*.6,d*.4,d*.7);ct.target.set(0,0,0)}}}};
window.tB=()=>{{bi=(bi+1)%bgs.length;sc.background=new T.Color(bgs[bi])}};
</script></body></html>'''
