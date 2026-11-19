# Iterating a layout without repacking

How to change a `.layout` on disk and see it in the running client within seconds: which paths the game reads again, the reload loop, its four traps, and what the preview can't show. What the preview taught about text and stringtables is in `preview-text-and-stringtables.md`.

Everything here is measured in game on DayZ 1.29, not read from source; the engine calls it uses are cited on `P:\`.

## Only `$profile:` is read again

A path under an addon prefix is served by the PBO and only by the PBO:

| Tried | Result |
|---|---|
| A loose `.c` on the work drive `P:\` | The PBO's copy wins |
| A loose `.layout` at a path the PBO also holds | The PBO's copy wins |
| A loose `.layout` at a path the PBO does not hold | Invisible: `FileExist` returns 0 |

In the same test `FileExist` returned 1 for a file that exists only inside the PBO, so the 0 is a real absence. The same rule rules out adding assets hot: dropping a texture or model into a running game's mod folder does nothing, because the engine doesn't watch the addon prefix.

`$profile:` is the exception. It resolves to the client's `-profiles=` folder, an ordinary writable folder outside any PBO, and the engine reads it on demand.

Measured with a 1920x1080 client:

| Question | Answer |
|---|---|
| Does a `.layout` written from outside the game load? | Yes, from `$profile:` |
| Do the engine's rects match an offline prediction? | Within 4.15e-05 px over three widgets |
| Is the file read again on every load, or parsed once? | Read again: the same path with different contents gives different rects |
| Does a missing path kill the client? | Not when guarded (the first trap below) |
| Does unloading leave anything? | No; after `Unlink()` a lookup by name finds nothing |
| Does a `.paa` in `$profile:` draw like the PBO's copy? | Yes, means within 1/255 and standard deviations within 0.8, with a positive and a negative control in the same frame |

Test the reread with two files that predict different shapes, never the same file twice, or a cached parse passes. Because textures load too, a hot layout can carry its own images, not just boxes and text.

## The loop

1. Write the `.layout` into the client's profile folder from outside the game.
2. Reload it in the running client.
3. Capture a frame and read back the engine rects.
4. Compare with the offline prediction, and look at the frame.
5. Edit and repeat. No repack, no restart.

The reload runs on the client, from a small diag script in your own mod:

```c
WorkspaceWidget workspace = GetGame().GetWorkspace();
if (m_Preview)
{
    m_Preview.Unlink();
    m_Preview = null;
}
if (!FileExist(path))
    return;
m_Preview = workspace.CreateWidgets(path);
```

`Unlink()` is at `P:\scripts\1_core\proto\enwidgets.c:173`, `FileExist` at `P:\scripts\1_core\proto\ensystem.c:397` and `CreateWidgets(string layout, Widget parentWidget = NULL, bool immedUpdate = true)` at `enwidgets.c:181`. Leave `immedUpdate` at its default: the rects are then right within the same call, with no frame of waiting (measured).

## The four traps

- `CreateWidgets` on a missing file kills the client inside the native call. No exception and no null return; the process dies. `FileExist` resolves virtual paths, as the test above shows, so it is a real guard. Guard every load at run time.
- A second `CreateWidgets` adds a tree; it does not replace the first. Clicks then land on the hidden older copy, and a rect snapshot no longer describes the screen. `Unlink()` the old root before every load. To prove only one exists, unload and check the name is gone.
- A UI texture that does not resolve paints a flat white box (255, 255, 255, standard deviation 0) and the RPT says nothing about it. If a design comes out white, suspect the texture path before the color or the style.
- Right rects prove nothing about what is drawn. A panel reported the exact right rectangle and painted nothing, because its style's `Normal` state had an empty `Center` image; every automated check passed. End each loop with a frame, and for a mechanical verdict put a positive and a negative control in the same frame.

A special case of the white box: a `{GUID}Gui/...edds` reference that works in a vanilla layout can draw solid white from a mod layout, even with the GUID and path copied exactly from the vanilla `.meta`, and logs nothing useful. Whether GUID resolution depends on where the layout comes from is not settled, so don't blame the asset from this symptom alone. Use a registered imageset through `LoadImageFile("set:... image:...")` or rich text, or ship your own `.paa` referenced by the addon's packed prefix; the second route drew correctly.

## What the preview can't show

The preview shows appearance, not behaviour. Nothing attaches a script class to its root, so its buttons have no handlers. It also takes no input: a click, from a script or from a real mouse with the inventory open, does nothing, although the preview draws above the inventory. Draw order and input are separate, and `CreateWidgets` gives only the first, because nothing calls `SetActiveWindow` on the new root (`enwidgets.c:695`). Focus, hover and wheel scrolling can't be seen in this loop at all. Use the real menu for those.

A test that clicks, sets text or reads the tree usually finds widgets by name through `FindAnyWidget`, which ignores which tree a name came from. A preview with widgets named `BtnYes` or `Title` collides with whatever else is loaded; give hot layouts a prefix of their own.

Not yet measured: whether a custom font or an imageset resolves from `$profile:`. Vanilla fonts and imagesets work because they come from the game's own PBOs.
