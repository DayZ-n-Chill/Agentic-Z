# Theme and color: scoping a recolor, the method override shape, and the color system

How to scope a recolor or theme request, the shape of a method override that changes a color set in script, what is known about UI theme mods, and the rules of the color system (HUD brightness, low alpha, float against integer ranges).

The three places a DayZ UI color comes from (layout files, `SetColor` literals in script, the `Colors` constants), the checked override route for each, and the rule to ask for scope first are Tier 2: `skills/_shared/conventions/ui.md`, "UI scripting realities". Read that first; this file does not repeat it, and where the two differ the Tier 2 file wins. On 1.30 a layout variant changes single vanilla widgets in place: `layout-variants.md`.

**How facts are marked here.** A `P:\` path with a line was checked on `P:\` (DayZ 1.30). "Measured in game" results were read off a running client and are not yet repeated on 1.30.

---

## Overriding a color set in script

A color written as a literal in a `SetColor` call (for example `w.SetColor(0xFFFFEC44)` at `P:\scripts\5_mission\gui\actionmenu.c:74`) is changed by overriding the method that makes the call. You cannot override the literal itself.

```c
// Illustration only: these names are made up to show the shape.
// Vanilla:
class SomeHudClass
{
    void UpdateSomeIcon()
    {
        m_SomeIcon.SetColor(0xFFD70D11);  // baked in at compile time
    }
}

// Override the method, not the literal:
modded class SomeHudClass
{
    override void UpdateSomeIcon()
    {
        m_SomeIcon.SetColor(0xFF0D11D7);
    }
}
```

Find the real method by searching `P:\scripts\5_mission\gui\` for the `SetColor` call that sets the color you want to change.

## How to scope a theme request

- **A single element** ("the bleeding icon", "the menu hover state"): feasible. It is one method override, one layout swap, or on 1.30 one layout variant.
- **All red to all blue** ("retheme the whole UI"): push back. Define the scope piece by piece and treat it as a batch: sweep the `.layout` files per widget, override every method under `5_mission/gui/` that calls `SetColor` with the old color, and leave the `Colors` constants alone (a false lead, see Tier 2). No framework has been confirmed to make it a one property edit.

Never accept "change all the red" as a one file task. Tell the user this before estimating the effort.

## UI theme mods (unverified)

Third-party mods, not vanilla. This repo has not checked any UI theme mod's source or API, so everything here is unverified, the same status Tier 2 gives CUI.

- What "CUI" names is itself unconfirmed. Tier 2 expands it as Community UI Framework. It is also used as short for **Colorful UI**, a mod template said to come in a free community edition and a separate paid variant whose terms forbid commercial use, which matters for monetized servers; read the terms of the edition you pick.
- Colorful UI is said to work by shipping every default layout again as a file you can edit on its own. If so, that is the same per layout mechanism Tier 2 calls heavy, not a central theme layer. Check its files before you rely on either reading.
- Do not promise that adopting either turns a retheme into one property edits until its source shows a central theme API that does it. Colorful UI may be useful as a starting template when the goal is "reskin the whole vanilla UI", if it does ship the layouts again as described.
- Community Framework (CF) ships no MVC or UI layer (its changelog marks MVC as deprecated in 1.1 and removed in 1.3.1; not yet checked against the CF files). The only CF UI surface worth knowing is its `NotificationSystem`, which is server aware (`skills/_shared/enscript/integrations/community_framework.md`).

---

## Color system

- **HUD brightness.** The rule never to call `Widget.SetLV()` or `Widget.SetTextLV()` from a mod is Tier 2 (`skills/_shared/conventions/ui.md`, "Layout and widget rules"). What follows from it: the engine comment gives both a range of -15 to 0, default 0, lower is less bright (`P:\scripts\1_core\proto\enwidgets.c:114-117`), and vanilla feeds them the player's `EDayZProfilesOptions.HUD_BRIGHTNESS` (`P:\scripts\3_game\dayzgame.c:3910-3919`). If your colors look darker than their hex values, that is the player's setting doing its job: pick colors that survive it and check them at a HUD brightness below zero. A machine that draws dark has a negative value in its profile; the harness that first measured the darkening is `color-test-harness.md`.
- **3D previews have their own knob.** `Widget.SetObjectLighting(float)` (range 0 to 1, default 1, `P:\scripts\1_core\proto\enwidgets.c:118-119`) lights item and player previews; it is separate from `SetLV`.
- **Low alpha is clamped to invisible by the engine.** Measured in game: 0x12 (18) drew nothing and 0x26 (38) was visible, so the threshold is somewhere above 0x12 and at or below 0x26. Stay at 0x30 (48) or more for anything that must be seen, and treat 0x13 to 0x2F as untested.
- A layout writes colors as floats from 0.0 to 1.0. Script `ARGB()` takes integers from 0 to 255.
- `ImageWidget.SetColor()` tints the texture (it multiplies); it does not repaint pixels, so an already colored image gets darker, not recolored. Author recolorable art white or grey and tint it with `SetColor`. Not checked on `P:\`.
- `ButtonWidget.SetColor()` works directly; a button needs no `LoadImageFile` first (Dabs Framework's `SampleMVC.c` does it).
- Dabs `LinearColor` has about 150 named colors, HSV, `Lerp` and blend modes (`dabs-mvc-internals.md`).
- The alpha in a layout `color` on an `ImageWidget` with no texture is ignored when it is drawn; see `text-sizing-and-rendering.md` for that and for the blend settings transparent images need.
