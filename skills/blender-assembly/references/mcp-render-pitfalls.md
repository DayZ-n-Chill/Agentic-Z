# Render pitfalls when driving Blender over MCP

Two traps that make a render over the Blender MCP disagree with the mesh data: a render depsgraph that keeps serving the mesh from before an in-place edit, and a scene that silently changes between calls. It is Blender tool behaviour, measured by the source author (added 2026-06-11, verified 2026-06-10); nothing here is a statement about the game.

## The render depsgraph goes stale after in-place mesh edits

When the host Blender is driven over MCP, `obj.data.transform()` and other low-level in-place writes to a datablock do update the data, which you can verify by reading the vertices. The render depsgraph, though, keeps serving a frozen copy of that datablock: every `render.render()` shows the mesh from before the edit.

- `data.update()`, `update_tag()`, `view_layer.update()` and `evaluated_depsgraph_get().update()` do not clear it.
- A `mesh.copy()` inherits the stale cache.
- New objects render fine.

**Fix.** Write the edited geometry to a new mesh datablock with `bm.to_mesh(new_mesh)`, link it on a new object, and remove the old object and mesh.

**Cost of not knowing.** Phantom renders that contradict your measurements. On the A6_MK47 model this nearly led to diagnosing a correct orientation as wrong.

**Diagnosis: the marker-sphere test.** Add primitive spheres at known coordinates and render. Markers in the right place with a stale mesh means this cache, not your math.

## The scene can change between calls

`bpy.context.scene` can silently go back to the user's scene between MCP calls. Pin `bpy.context.window.scene`, and pass `scene=` to `render.render()` on every call, or you render (and screenshot) the wrong scene.
