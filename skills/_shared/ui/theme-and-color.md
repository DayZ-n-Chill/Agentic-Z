# Theme and color

How to scope a recolor or retheme request, how to override a color that script sets, what is known about UI theme mods, and the rules of the color system: HUD brightness, low alpha and the two color ranges.

The three places a UI color comes from (layout files, `SetColor` literals in script, the `Colors` constants), the override route for each, and the rule to ask for scope first are Tier 2: `skills/_shared/conventions/ui.md`, "UI scripting realities". Read that first; where the two differ, it wins. On 1.30 a layout variant changes single vanilla widgets in place (`layout-variants.md`).

## Overriding a color set in script

A color written as a literal in a `SetColor` call (`w.SetColor(0xFFFFEC44)` at `P:\scripts\5_mission\gui\actionmenu.c:74`) changes only by overriding the method that makes the call; the literal itself cannot be overridden. The names below are made up to show the shape:

```c
// vanilla
class SomeHudClass
{
    void UpdateSomeIcon()
    {
        m_SomeIcon.SetColor(0xFFD70D11);
    }
}

// your mod
modded class SomeHudClass
{
    override void UpdateSomeIcon()
    {
        m_SomeIcon.SetColor(0xFF0D11D7);
    }
}
```

Find the real method by searching `P:\scripts\5_mission\gui\` for the `SetColor` call that sets the color you want.

## Scoping a theme request

- One element ("the bleeding icon", "the menu hover color") is feasible: one method override, one layout swap, or on 1.30 one layout variant.
- "Make all the red blue" is a batch, not a setting. Scope it piece by piece: go through the `.layout` files widget by widget, override every method under `5_mission/gui/` that calls `SetColor` with the old color, and leave the `Colors` constants alone (a false lead, see Tier 2). No framework is confirmed to make it one edit.

Never accept "change all the red" as a one file task, and tell the user so before estimating.

## UI theme mods

These are third party mods, and this repo has not checked their source, so all of this is unverified.

- What "CUI" names is unclear. Tier 2 reads it as Community UI Framework; it is also short for Colorful UI, a template said to come as a free community edition and a paid edition whose terms forbid commercial use. Read the terms of the edition you pick before using it on a monetised server.
- Colorful UI is said to ship every default layout again as a file you edit on its own. If so, it is the same per layout route Tier 2 calls heavy, not a central theme layer. It may still be a useful start for "reskin the whole vanilla UI".
- Do not promise that either turns a retheme into a few property edits until its source shows a central theme API.
- Community Framework ships no MVC or UI layer (its changelog marks MVC deprecated in 1.1 and removed in 1.3.1; not checked against the CF files). Its only UI piece worth knowing is the server aware `NotificationSystem` (`skills/_shared/enscript/integrations/community_framework.md`).

## The color system

- HUD brightness. Never call `Widget.SetLV()` or `Widget.SetTextLV()` from a mod (Tier 2, "Layout and widget rules"). Both take -15 to 0, default 0, lower is darker (`P:\scripts\1_core\proto\enwidgets.c:114` to `:117`), and vanilla feeds them the player's `EDayZProfilesOptions.HUD_BRIGHTNESS`: `SetHudBrightness` calls both with the same value and `GetHUDBrightnessSetting` reads the option (`P:\scripts\3_game\dayzgame.c:3910` to `:3919`). Colors darker than their hex values are that setting doing its job: pick colors that survive it and check them at a brightness below zero. Saturated colors barely change; greys and pastels darken most. `color-test-harness.md` is a panel for checking this.
- 3D previews have their own knob, `Widget.SetObjectLighting(float)`, 0 to 1, default 1 (`P:\scripts\1_core\proto\enwidgets.c:119`), separate from `SetLV`.
- Low alpha draws nothing. Measured in game: `0x12` (18) was invisible and `0x26` (38) visible. Keep anything that must be seen at `0x30` (48) or more; `0x13` to `0x2F` is untested.
- A layout writes colors as floats from 0 to 1; script `ARGB()` takes integers from 0 to 255.
- `ImageWidget.SetColor()` multiplies the texture, so a colored image gets darker, not recolored. Author art you will tint in white or grey (not checked on `P:\`).
- `ButtonWidget.SetColor()` needs no `LoadImageFile` first when the button's style draws `WhitePixel`, as `Colorable` does (`styles-format.md`).
- Dabs `LinearColor` has about 150 named colors, HSV, `Lerp` and blend modes (`dabs-observables-and-animation.md`).
- The alpha of a layout `color` on an `ImageWidget` with no texture is ignored, and transparent images need blend settings (`text-sizing-and-rendering.md`).
