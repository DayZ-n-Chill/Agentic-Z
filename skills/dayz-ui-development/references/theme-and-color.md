# Theme and color: where UI colors come from, how to scope a recolor, and the color system

Why "change all the red" is hours of work in DayZ, the three places a UI color can come from, how to scope a theme request, what is and is not known about CUI and the Colorful UI mod, and the rules of the color system (HUD brightness, low alpha, float against integer ranges).

The Tier 2 rule for this topic is `skills/_shared/conventions/ui.md`; it holds the checked override routes (recolor one widget after `super`, or replace a whole layout) with their vanilla lines. This file adds scoping advice and color measurements on top of it. Where the two differ, the Tier 2 file wins.

**How facts are marked here.** A `P:\` path with a line was checked on `P:\` (DayZ 1.30). "Measured in game" results were read off a running client and are not yet repeated on 1.30.

---

## DayZ has no central theme

DayZ has no central theme system. There is no `PrimaryAccentColor` constant that flows through every widget. A color comes from three independent places, and each needs a different override. No framework has been confirmed to close this gap (see "CUI and Colorful UI" below).

### The three sources of UI color

1. **`.layout` files in `P:\gui\layouts\` (227 files in DayZ 1.30).**

   Colors are baked in per widget, as `color R G B A` values written in the layout. `modded class` does not apply to a `.layout` file.

   The classic override is to ship your own copy of the whole layout: heavy, and brittle across DayZ updates. A copy under your own PBO prefix replaces nothing by itself; you either point the script that calls `CreateWidgets` at your copy or recolor widgets after `super` (`skills/_shared/conventions/ui.md`). Since DayZ 1.30 a layout variant can change single vanilla widgets in place: `layout-variants-130.md`.

2. **ARGB literals written in script under `P:\scripts\5_mission\gui\`.**

   Script calls `SetColor` with a hex literal, for example `w.SetColor(0xFFFFEC44)` at `P:\scripts\5_mission\gui\actionmenu.c:74`. To change that color, override the method that makes the call with `modded class`. You cannot override the literal.

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

   The names in the example are placeholders. Find the real method by searching `P:\scripts\5_mission\gui\` for the `SetColor` call that sets the color you want to change.

3. **`Colors` and `FadeColors` constants in `P:\scripts\3_game\colors.c`.**

   These look like the obvious target for a theme override. They are not. `modded class Colors { const int X = ...; }` is expected to do nothing for compile time constants, because callers already baked in the original integer when they were compiled. That is not yet tested in Workbench (the Tier 2 file marks it the same way); test it before relying on it either way.

   What is checked: `COLOR_DAYZ_RED`, the constant most often named as "DayZ red", is declared as `const int COLOR_DAYZ_RED = 0xffd70d11;` at `P:\scripts\3_game\colors.c:53` and is used in exactly one place in vanilla script, `SetBannerColor(Colors.COLOR_DAYZ_RED)` at `P:\scripts\5_mission\gui\newui\mainmenu\mainmenupromo.c:157`, the main menu promo banner. So even a working override of that constant would recolor one element.

### What that means

A request like "change all the red UI to blue" is hours of work, not minutes. It takes:

- Sweeping `.layout` files for per widget color values and replacing each one.
- Finding every `SetColor(<red ARGB>)` call under `5_mission/gui/` and overriding the method around it with `modded class`.
- Leaving the `Colors` constants alone; they are a false lead.

### How to scope a theme request

When the user asks for a UI color change, ask first:

- **A single element** ("the bleeding icon", "the menu hover state"): feasible. It is one method override, one layout swap, or on 1.30 one layout variant.
- **All red to all blue** ("retheme the whole UI"): push back. Define the scope piece by piece and treat it as a batch. No framework has been confirmed to make it a one property edit.

Never accept "change all the red" as a one file task. Tell the user what this section says before estimating the effort.

### CUI and Colorful UI (unverified)

Third-party mods, not vanilla. This repo has not checked any UI framework's source or API, so everything in this section is unverified, the same status the Tier 2 file gives it: CUI is reported to offer the theme layer the engine lacks, and you confirm the API in the framework's own source before you build on it or recommend it.

- What "CUI" names is itself unconfirmed. The Tier 2 file expands it as Community UI Framework. It is also used as short for **Colorful UI**, a mod template said to come in a free community edition and a separate "Pro" variant whose terms forbid commercial use, which matters for monetized servers; read the terms of the edition you pick before you build on it.
- Colorful UI is said to work by shipping every default layout again as a file you can edit on its own. If so, that is the same per layout mechanism this file calls heavy, not a central theme layer that spreads one color everywhere. Check its files before you rely on either reading.

What follows from that:

1. Do not promise that adopting CUI or Colorful UI turns a retheme into one property edits until its source shows a central theme API that does it.
2. Colorful UI may be useful as a starting template when the goal is "reskin the whole vanilla UI", if it does ship the layouts again as described.
3. For a one off recolor in an existing mod, stay scoped to the one element. On 1.30 a layout variant does that without shipping the whole layout: `layout-variants-130.md`.

Community Framework (CF) ships no MVC or UI layer (its changelog marks MVC as deprecated in 1.1 and removed in 1.3.1; not yet checked against the CF files). The only CF UI surface worth knowing is its `NotificationSystem`, which is server aware.

---

## Color system

- **Never call `Widget.SetLV()` or `Widget.SetTextLV()` from a mod.** They are `proto static`, so they are global and not per widget; the engine comment says "Set global LV of widgets" (`P:\scripts\1_core\proto\enwidgets.c:114-117`). Vanilla uses exactly those two calls to apply the player's brightness preference: `SetHudBrightness()` is `Widget.SetLV(value); Widget.SetTextLV(value);` (`P:\scripts\3_game\dayzgame.c:3910-3914`), fed from `EDayZProfilesOptions.HUD_BRIGHTNESS` through `GetHUDBrightnessSetting()` (`P:\scripts\3_game\dayzgame.c:3916-3919`), and called from `OnInitialize()` (`P:\scripts\3_game\dayzgame.c:2109-2114`). So `SetLV(0)` at mod init does not "normalize colors". It overwrites the player's HUD brightness setting, globally, for the vanilla UI too.
- If your colors look darker than their hex values, that is the player's brightness setting doing its job. Design against it: pick colors that survive it, and check them at a HUD brightness other than zero. Do not flatten it.
- The measurement of 2026-03-24 behind the old advice was real (saturated colors barely changed; grays and pastels came out much darker), but it measured that machine's HUD brightness, not an engine constant. The documented default of `SetLV` is 0; a machine that draws dark has a negative value in its profile.
- Advice that "one line fixes everything", telling mods to call `SetLV(0)` at init, is wrong. A helicopter HUD that removed both calls still passed all its UI checks. The harness that produced the first measurement is `color-test-harness.md`.
- **Low alpha is clamped to invisible by the engine.** Measured in game: 0x12 (18) drew nothing and 0x26 (38) was visible, so the threshold is somewhere above 0x12 and at or below 0x26. Stay at 0x30 (48) or more for anything that must be seen, and treat 0x13 to 0x2F as untested. Corrected on 2026-07-04: an older line said "below 0x30 is invisible", which its own "0x26 works" example contradicted.
- A layout writes colors as floats from 0.0 to 1.0. Script `ARGB()` takes integers from 0 to 255.
- Dabs `LinearColor` has about 150 named colors, HSV, `Lerp` and blend modes (`dabs-framework.md`).
- `ButtonWidget.SetColor()` works directly; a button needs no `LoadImageFile` first (Dabs Framework's `SampleMVC.c` does it).
- The alpha in a layout `color` on an `ImageWidget` with no texture is ignored when it is drawn; see `text-sizing-and-rendering.md` for that and for the blend settings transparent images need.
