# GENERATED FILE - DO NOT EDIT.
# Source: skills/_shared/viewer_core.py
# source-sha256: 7C59F1CC5DCAF8CF33CE54D17D17BFC8272EA12899ED2F6AC0665B431F2D153D
# Regenerate: python tools/sync_generated.py sync --root .
"""Emit the shared Three.js viewer scaffold (ESM + importmap, three 0.185.1).

This module is a string emitter. Generators splice the returned HTML/JS into
their templates. It does not render, does not vendor three.js, and does not
add gizmos/panels the generators did not already have.

How generators find this file
-----------------------------
There is no install step and no machine-absolute path. Each generator carries
a private copy of the bounded locator below (they cannot import this module
until they have found it). The candidate list depends on the caller's layout,
not a fixed four-name probe at every ancestor:

- under ``skills/``: never the file next to the caller. Canonical is
  ``<dir>/skills/_shared/viewer_core.py`` (and ``<dir>/_shared/viewer_core.py``).
- ``dayz_3d_viewer`` package: ``viewer_core.py`` next to the caller.
- workspace ``patched/``: ``viewer_core.py`` at the search boundary
  (``out/viewer_core.py``), never a homonym inside ``patched/``.
- standalone (none of the above): ``viewer_core.py`` next to the caller.

The walk stops at the first search boundary: a directory that contains
``skills/``, ``dayz_3d_viewer/``, ``.git``, or the workspace ``patched/``
folder the caller lives in. A standalone caller is not walked past its
own directory. A homonym above the root is never opened.

A candidate is inspected with ``ast.parse`` (no execution). Comments and
string literals do not count. Only a module-level assignment of
``VIEWER_CORE_CONTRACT`` / ``THREE_VERSION`` and ``def`` of the four public
functions make it eligible to load. That covers the five pack locations and
``out/patched/*.py`` -> ``out/viewer_core.py``.
"""

from __future__ import annotations

import ast
import importlib.util
import os

VIEWER_CORE_CONTRACT = "dayz-viewer-core/1"
THREE_VERSION = "0.185.1"
THREE_CDN = "https://cdn.jsdelivr.net/npm/three@%s" % THREE_VERSION

ADDON_PATHS = {
    "OrbitControls": "three/addons/controls/OrbitControls.js",
    "TransformControls": "three/addons/controls/TransformControls.js",
    "GLTFLoader": "three/addons/loaders/GLTFLoader.js",
    "CSS2DRenderer": "three/addons/renderers/CSS2DRenderer.js",
    "BufferGeometryUtils": "three/addons/utils/BufferGeometryUtils.js",
}

# r185 BufferGeometryUtils.js exports free functions, not a ``BufferGeometryUtils``
# binding. Named ``import { BufferGeometryUtils }`` is a SyntaxError; star-import
# the module namespace instead.
ADDON_NAMESPACE = frozenset({"BufferGeometryUtils"})

_CONTRACT_API = ("importmap_script", "module_imports", "boot_js", "loop_js")


def _path_is_under(child, parent):
    child = os.path.normcase(os.path.abspath(child))
    parent = os.path.normcase(os.path.abspath(parent))
    try:
        return os.path.commonpath([child, parent]) == parent
    except ValueError:
        return False


def _is_search_boundary(directory, start_dir):
    if os.path.isdir(os.path.join(directory, "skills")):
        return True
    if os.path.isdir(os.path.join(directory, "dayz_3d_viewer")):
        return True
    if os.path.isdir(os.path.join(directory, ".git")):
        return True
    patched = os.path.join(directory, "patched")
    if os.path.isdir(patched) and _path_is_under(start_dir, patched):
        return True
    return False


def _layout_kind(start_dir):
    """Classify the caller so the candidate list is not a fixed probe.

    ``package``     — ``dayz_3d_viewer/`` (core lives next to the module).
    ``skills``      — any ancestor named ``skills`` (core is ``_shared``, never adjacent).
    ``workspace``   — any ancestor named ``patched`` (core is at the boundary).
    ``standalone``  — none of the above (core next to the caller; do not walk parents).
    """
    start_dir = os.path.abspath(start_dir)
    if os.path.normcase(os.path.basename(start_dir)) == os.path.normcase("dayz_3d_viewer"):
        return "package"
    directory = start_dir
    seen = set()
    while directory not in seen:
        seen.add(directory)
        name = os.path.normcase(os.path.basename(directory))
        if name == os.path.normcase("skills"):
            return "skills"
        if name == os.path.normcase("patched"):
            return "workspace"
        parent = os.path.dirname(directory)
        if parent == directory:
            break
        directory = parent
    return "standalone"


def _source_looks_like_viewer_core(path):
    """True if *path* defines the contract at module level. Does not execute it."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            src = fh.read()
    except OSError:
        return False
    try:
        tree = ast.parse(src, filename=path)
    except (SyntaxError, ValueError):
        return False
    assigned = {}
    funcs = set()
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    assigned[target.id] = node.value.value
        elif (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and isinstance(node.value, ast.Constant)
        ):
            assigned[node.target.id] = node.value.value
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            funcs.add(node.name)
    if assigned.get("VIEWER_CORE_CONTRACT") != VIEWER_CORE_CONTRACT:
        return False
    if assigned.get("THREE_VERSION") != THREE_VERSION:
        return False
    return all(name in funcs for name in _CONTRACT_API)


def _candidate_core_paths(directory, start_dir, layout):
    paths = []
    if directory == start_dir and layout in ("package", "standalone"):
        paths.append(os.path.join(directory, "viewer_core.py"))
    paths.append(os.path.join(directory, "_shared", "viewer_core.py"))
    paths.append(os.path.join(directory, "skills", "_shared", "viewer_core.py"))
    paths.append(os.path.join(directory, "dayz_3d_viewer", "viewer_core.py"))
    if directory != start_dir and _is_search_boundary(directory, start_dir):
        paths.append(os.path.join(directory, "viewer_core.py"))
    return paths


def _exec_viewer_core(path):
    spec = importlib.util.spec_from_file_location("viewer_core", path)
    if spec is None or spec.loader is None:
        raise ImportError("cannot load viewer_core from %s" % path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if getattr(mod, "VIEWER_CORE_CONTRACT", None) != VIEWER_CORE_CONTRACT:
        raise ImportError("viewer_core contract mismatch at %s" % path)
    if getattr(mod, "THREE_VERSION", None) != THREE_VERSION:
        raise ImportError("viewer_core THREE_VERSION mismatch at %s" % path)
    for name in _CONTRACT_API:
        if not callable(getattr(mod, name, None)):
            raise ImportError("viewer_core missing %s at %s" % (name, path))
    return mod


def load_viewer_core(start_file):
    """Load this module given the calling generator's ``__file__``.

    Walks ``start_file``'s directory and its parents using a layout-dependent
    candidate list, and stops at the pack/workspace root. A decoy above that
    root is not loaded. A homonym next to a skill script is not a candidate.
    Candidates are parsed, not executed, before loading. Invalid candidates
    are skipped (same decision as the six private locators). No sys.path
    mutation with machine-absolute paths.
    """
    start_dir = os.path.dirname(os.path.abspath(start_file))
    layout = _layout_kind(start_dir)
    directory = start_dir
    seen = set()
    while directory not in seen:
        seen.add(directory)
        for path in _candidate_core_paths(directory, start_dir, layout):
            if os.path.isfile(path) and _source_looks_like_viewer_core(path):
                try:
                    return _exec_viewer_core(path)
                except ImportError:
                    continue
        if layout == "standalone" or _is_search_boundary(directory, start_dir):
            break
        parent = os.path.dirname(directory)
        if parent == directory:
            break
        directory = parent
    raise ImportError(
        "viewer_core.py not found within pack/workspace root walking parents of %s"
        % os.path.abspath(start_file)
    )


def importmap_script(version=THREE_VERSION):
    """Return the ``<script type="importmap">`` tag for jsDelivr.

    Maps ``three`` -> ``build/three.module.js`` and ``three/addons/`` ->
    ``examples/jsm/``. CDN imports work from file://; local module imports do not.
    """
    cdn = "https://cdn.jsdelivr.net/npm/three@%s" % version
    return (
        '<script type="importmap">{"imports":{'
        '"three":"%s/build/three.module.js",'
        '"three/addons/":"%s/examples/jsm/"'
        "}}</script>" % (cdn, cdn)
    )


def module_imports(addons=(), three_alias="THREE"):
    """JS import lines for a ``<script type="module">`` body.

    ``addons`` is an iterable of keys in ``ADDON_PATHS``
    (OrbitControls, TransformControls, GLTFLoader, ...).
    ``three_alias`` is the local namespace name (``THREE`` or ``T``).
    """
    lines = ["import * as %s from 'three';" % three_alias]
    for name in addons:
        if name not in ADDON_PATHS:
            raise KeyError("unknown three addon %r (known: %s)" % (name, sorted(ADDON_PATHS)))
        path = ADDON_PATHS[name]
        if name in ADDON_NAMESPACE:
            lines.append("import * as %s from '%s';" % (name, path))
        else:
            lines.append("import { %s } from '%s';" % (name, path))
    return "\n".join(lines)


def _js(value):
    """Emit a JS expression. Strings pass through (already JS); bool/num/None convert."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return value
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, int):
        return str(value)
    raise TypeError("cannot emit %r as JS" % (value,))


def renderer_js(
    var="renderer",
    three="THREE",
    canvas_expr=None,
    antialias=True,
    preserve_drawing_buffer=False,
    pixel_ratio="devicePixelRatio",
    tone_mapping=None,
    tone_exposure=None,
    append_to=None,
    insert_before=None,
):
    """JS that constructs a WebGLRenderer.

    ``canvas_expr``: JS expression for an existing canvas (e.g. ``cv`` or
    ``document.getElementById('c')``). Omit to let three create the canvas.
    ``append_to`` / ``insert_before``: JS element expressions used only when
    no canvas is supplied.
    ``tone_mapping``: suffix of a three constant, e.g. ``ACESFilmicToneMapping``.
    ``pixel_ratio``: JS expression, or None to skip setPixelRatio.
    """
    opts = ["antialias:" + _js(antialias)]
    if canvas_expr:
        opts.append("canvas:" + canvas_expr)
    if preserve_drawing_buffer:
        opts.append("preserveDrawingBuffer:true")
    lines = ["const %s=new %s.WebGLRenderer({%s});" % (var, three, ",".join(opts))]
    if pixel_ratio is not None:
        lines.append("%s.setPixelRatio(%s);" % (var, _js(pixel_ratio)))
    if tone_mapping:
        lines.append("%s.toneMapping=%s.%s;" % (var, three, tone_mapping))
        if tone_exposure is not None:
            lines.append("%s.toneMappingExposure=%s;" % (var, _js(tone_exposure)))
    if append_to:
        lines.append("%s.appendChild(%s.domElement);" % (append_to, var))
    if insert_before:
        # insert_before is (parent_expr, sibling_expr)
        parent, sibling = insert_before
        lines.append("%s.insertBefore(%s.domElement,%s);" % (parent, var, sibling))
    return "\n".join(lines)


def camera_js(var="camera", three="THREE", fov=50, aspect=1, near=0.01, far=100):
    """JS that constructs a PerspectiveCamera."""
    return "const %s=new %s.PerspectiveCamera(%s,%s,%s,%s);" % (
        var,
        three,
        _js(fov),
        _js(aspect),
        _js(near),
        _js(far),
    )


def scene_js(var="scene", three="THREE", background="0x1a1a2e"):
    """JS that constructs a Scene with a solid background color."""
    return "const %s=new %s.Scene(); %s.background=new %s.Color(%s);" % (
        var,
        three,
        var,
        three,
        _js(background),
    )


def orbit_js(
    var="controls",
    camera="camera",
    renderer="renderer",
    damping=True,
    damping_factor=0.08,
    auto_rotate_speed=None,
):
    """JS that constructs OrbitControls. Requires OrbitControls in module scope."""
    lines = ["const %s=new OrbitControls(%s,%s.domElement);" % (var, camera, renderer)]
    if damping:
        lines.append("%s.enableDamping=true;" % var)
        lines.append("%s.dampingFactor=%s;" % (var, _js(damping_factor)))
    if auto_rotate_speed is not None:
        lines.append("%s.autoRotate=false;" % var)
        lines.append("%s.autoRotateSpeed=%s;" % (var, _js(auto_rotate_speed)))
    return "\n".join(lines)


def grid_js(
    var="grid",
    three="THREE",
    scene="scene",
    size=2,
    divisions=20,
    color1="0x445566",
    color2="0x2c333d",
    visible=True,
    add_to_scene=True,
):
    """JS that constructs a GridHelper and optionally adds it to the scene."""
    lines = [
        "const %s=new %s.GridHelper(%s,%s,%s,%s);"
        % (var, three, _js(size), _js(divisions), _js(color1), _js(color2))
    ]
    if not visible:
        lines.append("%s.visible=false;" % var)
    if add_to_scene:
        lines.append("%s.add(%s);" % (scene, var))
    return "\n".join(lines)


def transform_controls_js(
    var="giz",
    camera="cam",
    renderer="ren",
    scene="scene",
    add_helper=True,
):
    """JS that constructs TransformControls.

    In 0.185.1 TransformControls extends Controls, not Object3D. Adding the
    controls object itself to the scene is a no-op plus a console error.
    The visible gizmo is ``controls.getHelper()``. attach/detach/setMode/
    setSpace/setSize and the dragging-changed / objectChange events remain.
    """
    lines = ["const %s=new TransformControls(%s,%s.domElement);" % (var, camera, renderer)]
    if add_helper:
        lines.append("%s.add(%s.getHelper());" % (scene, var))
    return "\n".join(lines)


def axes_js(var="axes", three="THREE", scene="scene", size=1, add_to_scene=True):
    """JS that constructs an AxesHelper. Off by default in boot_js (parity)."""
    lines = ["const %s=new %s.AxesHelper(%s);" % (var, three, _js(size))]
    if add_to_scene:
        lines.append("%s.add(%s);" % (scene, var))
    return "\n".join(lines)


def resize_js(
    fn="resize",
    camera="camera",
    renderer="renderer",
    mode="window",
    canvas_expr=None,
    container_expr=None,
    update_style=None,
    pixel_ratio=None,
    listen=True,
    call_now=True,
):
    """JS resize handler.

    mode:
      ``window``    — innerWidth / innerHeight
      ``parent``    — canvas parent getBoundingClientRect (needs canvas_expr)
      ``container`` — container_expr.clientWidth / clientHeight
    ``update_style`` is the third arg to setSize. Default false for parent
    (CSS-sized canvas) and true for the other modes.
    """
    if mode == "window":
        body = [
            "const w=window.innerWidth,h=window.innerHeight;",
        ]
        size_args = "w,h"
    elif mode == "parent":
        if not canvas_expr:
            raise ValueError("resize mode 'parent' needs canvas_expr")
        body = [
            "const r=%s.parentElement.getBoundingClientRect();" % canvas_expr,
            "const w=r.width,h=r.height;",
        ]
        size_args = "w,h"
    elif mode == "container":
        if not container_expr:
            raise ValueError("resize mode 'container' needs container_expr")
        body = [
            "const w=%s.clientWidth,h=%s.clientHeight;" % (container_expr, container_expr),
        ]
        size_args = "w,h"
    else:
        raise ValueError("unknown resize mode %r" % mode)

    if update_style is None:
        update_style = False if mode == "parent" else True
    if update_style is False:
        size_call = "%s.setSize(%s,false);" % (renderer, size_args)
    else:
        size_call = "%s.setSize(%s);" % (renderer, size_args)

    body.append("%s.aspect=w/h; %s.updateProjectionMatrix();" % (camera, camera))
    body.append(size_call)
    if pixel_ratio is not None:
        body.append("%s.setPixelRatio(%s);" % (renderer, _js(pixel_ratio)))

    lines = ["function %s(){" % fn]
    lines.extend("  " + ln for ln in body)
    lines.append("}")
    if listen:
        lines.append("window.addEventListener('resize',%s);" % fn)
    if call_now:
        lines.append("%s();" % fn)
    return "\n".join(lines)


def loop_js(
    renderer="renderer",
    scene="scene",
    camera="camera",
    controls=None,
    frame_hook=None,
    post_controls_hook=None,
):
    """JS that starts ``renderer.setAnimationLoop``.

    ``controls``, if set, is updated each frame (OrbitControls damping).
    ``frame_hook`` is an optional JS function name called as ``fn(ts)``
    *before* ``controls.update()`` (timeline / pose work that should see
    the pre-damping camera, matching original build_viewer).
    ``post_controls_hook`` is called *after* ``controls.update()`` and
    *before* ``render()`` so overlay labels project with the same camera
    the canvas uses (proxy, p3d_inspector, weapon_grip).
    """
    body = []
    if frame_hook:
        body.append("if(typeof %s==='function') %s(ts);" % (frame_hook, frame_hook))
    if controls:
        body.append("%s.update();" % controls)
    if post_controls_hook:
        body.append(
            "if(typeof %s==='function') %s(ts);" % (post_controls_hook, post_controls_hook)
        )
    body.append("%s.render(%s,%s);" % (renderer, scene, camera))
    inner = "".join(body)
    return "%s.setAnimationLoop(function(ts){%s});" % (renderer, inner)


def export_to_window(names):
    """Assign module-scope names onto ``window`` so HTML onclick= still works."""
    return "\n".join("window.%s=%s;" % (n, n) for n in names)


def boot_js(
    three="THREE",
    scene="scene",
    camera="camera",
    renderer="renderer",
    controls=None,
    grid=None,
    axes=None,
    canvas_expr=None,
    antialias=True,
    preserve_drawing_buffer=False,
    pixel_ratio="devicePixelRatio",
    tone_mapping=None,
    tone_exposure=None,
    append_to=None,
    insert_before=None,
    container_expr=None,
    background="0x1a1a2e",
    fov=50,
    aspect=1,
    near=0.01,
    far=100,
    orbit_damping=True,
    orbit_damping_factor=0.08,
    orbit_auto_rotate_speed=None,
    grid_size=2,
    grid_divisions=20,
    grid_color1="0x445566",
    grid_color2="0x2c333d",
    grid_visible=True,
    axes_size=1,
    resize="window",
    resize_fn="resize",
    resize_update_style=None,
    resize_pixel_ratio=None,
    resize_listen=True,
    resize_call_now=True,
    loop=True,
    frame_hook=None,
    post_controls_hook=None,
):
    """Concatenate renderer + camera + scene + optional orbit/grid/axes + resize + loop.

    Lights are NOT included: each viewer keeps its own (they affect what is shown).
    Axes are omitted unless ``axes`` is a variable name (adding a world gizmo
    would change the picture).
    """
    parts = [
        scene_js(var=scene, three=three, background=background),
        camera_js(var=camera, three=three, fov=fov, aspect=aspect, near=near, far=far),
        renderer_js(
            var=renderer,
            three=three,
            canvas_expr=canvas_expr,
            antialias=antialias,
            preserve_drawing_buffer=preserve_drawing_buffer,
            pixel_ratio=pixel_ratio,
            tone_mapping=tone_mapping,
            tone_exposure=tone_exposure,
            append_to=append_to,
            insert_before=insert_before,
        ),
    ]
    if controls:
        parts.append(
            orbit_js(
                var=controls,
                camera=camera,
                renderer=renderer,
                damping=orbit_damping,
                damping_factor=orbit_damping_factor,
                auto_rotate_speed=orbit_auto_rotate_speed,
            )
        )
    if grid:
        parts.append(
            grid_js(
                var=grid,
                three=three,
                scene=scene,
                size=grid_size,
                divisions=grid_divisions,
                color1=grid_color1,
                color2=grid_color2,
                visible=grid_visible,
            )
        )
    if axes:
        parts.append(axes_js(var=axes, three=three, scene=scene, size=axes_size))
    if resize:
        parts.append(
            resize_js(
                fn=resize_fn,
                camera=camera,
                renderer=renderer,
                mode=resize,
                canvas_expr=canvas_expr,
                container_expr=container_expr or append_to,
                update_style=resize_update_style,
                pixel_ratio=resize_pixel_ratio,
                listen=resize_listen,
                call_now=resize_call_now,
            )
        )
    if loop:
        parts.append(
            loop_js(
                renderer=renderer,
                scene=scene,
                camera=camera,
                controls=controls,
                frame_hook=frame_hook,
                post_controls_hook=post_controls_hook,
            )
        )
    # Version handshake for the headless gate: report the revision of the module that
    # was actually imported. A URL or a source comment can be spoofed; this cannot.
    parts.append("window.__THREE_REVISION=%s.REVISION;" % three)
    return "\n".join(parts)
