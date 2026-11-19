# Widget name collisions

Why two layouts that share widget names make one of them unreachable by name, how to find the overlap before it costs a session, and why renaming one root is usually the whole fix. All of it was measured in game on 1.29 with a mod panel and a test copy of its layout.

## Widget names are a contract

`FindAnyWidget` (`P:\scripts\1_core\proto\enwidgets.c:169`) finds a widget by name and returns one match. So does any test tool that resolves widgets by name. A test or debug copy of a layout that keeps the original names collides with it:

| Layout | Widgets |
|---|---|
| Production panel | 185 |
| Test copy | 213 |
| Names in both | 124, among them the root, the main panel, the header and every button and edit box |
| Names only in the test copy | 89 |

- Only the 89 names unique to the test copy could be reached; none of the 124 shared ones could.
- Scoping by an ancestor did not help: the test copy's close button sat under a root, a panel and a header that all collided too.
- The production root only has to exist. A view created once at mission init and hidden keeps its tree, and its names, for the whole session (`checklist-and-troubleshooting.md`, "Script rules"), so the collision is permanent once both exist.
- Before the copy opened, a name resolved silently to the production widget, whose handler did nothing because its view was closed. After it opened, every shared name came back ambiguous. A widget that reports `visible 1` with its hierarchy invisible is a root that was created and hidden; that tells you which of the two you got.

Rule: a test or debug variant prefixes every name (`TEST_`, `Dbg_`), or it cannot be addressed. Count the shared names before you approve one:

```python
import io
import re

def names(path):
    text = io.open(path, encoding="utf-8", errors="replace").read()
    header = re.findall(r'^\s*\w+WidgetClass\s+(\w+)\s*\{', text, re.M)
    props = re.findall(r'^\s*Name\s+"([^"]+)"', text, re.M)
    return set(header) | set(props)

print(sorted(names(PROD) & names(TEST)))   # must be empty
```

A 1.30 layout variant is a different thing: a file at the vanilla path that the engine applies on top of the vanilla layout (`layout-variants.md`).

## Renaming the root is usually enough

A test tool that resolves a name inside a scope counts matches under that scope only. So when the copy's root is unique, its whole tree can be addressed again by scoping to that root, even though every other name still collides. Tested with two sibling subtrees, each holding a child of the same name but a different size: with no scope the name was ambiguous, and each scope returned its own child at its own size. The different sizes are what show it picked the right one, not just one.

In that panel the fix was one line: the test copy's `FrameWidgetClass` root got a `TEST_` prefix. Check first that the root name is safe to change:

1. Search the name in the whole mod, `.layout`, `.c` and `config.cpp`, and count the hits.
2. Make sure it is not a Dabs `Binding_Name` and not a member field. If it is neither, the change is one line.
3. After the edit the layout parses, the widget count and brace balance are unchanged, and the production file is untouched.
4. The new name is declared once and appears nowhere in the production layout.

The game reads a `.layout` from the PBO, so a rename is live only after the next build; only `$profile:` is read from disk on each load (`hot-iteration.md`).

## Why not rename everything

Prefixing every widget looks like the obvious fix and is the expensive one on a live Dabs MVC view, which has three naming systems that overlap:

| System | Count in that panel | Renaming the widget breaks it when |
|---|---|---|
| Widget name in the `.layout` | 227 | It is the thing being renamed |
| Member field filled by `LoadWidgetsAsVariables` (member `X` matches widget `X`) | 139 | You do not rename the member too |
| `Binding_Name` of a `ViewBinding` | 15 | You rename the member, because it names a controller property, not a widget |

The last two pull opposite ways: renaming members repairs the automatic binding and breaks `Binding_Name`; leaving them kills the automatic binding. Every failure is a silent null, and only another in game session after a rebuild finds them. When a name comes back ambiguous, first ask whether one ancestor can be made unique. A full prefix is still right for a new layout, where it costs nothing.
