# Theme and color: where UI colors come from, how to scope a recolor, and the color system

Why "change all the red" is hours of work in DayZ, the three places a UI color can come from, how to scope a theme request, what the Colorful UI mod does and does not give you, and the rules of the color system (HUD brightness, low alpha, float against integer ranges).

The Tier 2 rule for this topic is `skills/_shared/conventions/ui.md`; it holds the checked override routes (recolor one widget after `super`, or replace a whole layout) with their vanilla lines. This file adds the source author's scoping advice and color measurements on top of it. Where the two differ, the Tier 2 file wins, and the difference is called out below.

**How facts are marked here.** A `P:\` path with a line was checked on `P:\` (DayZ 1.30). "Measured in game" results are the source author's and are not yet checked here.

---

## DayZ has no central theme

DayZ has no central theme system. There is no `PrimaryAccentColor` constant that flows through every widget. A color comes from three independent places, and each needs a different override. No framework closes this gap (see "Colorful UI" below).

### The three sources of UI color

1. **`.layout` files in `P:\gui\layouts\` (227 files in DayZ 1.30).**

   Colors are baked in per widget, as `color R G B A` values written in the layout. `modded class` does not apply to a `.layout` file.

   The source describes the classic override as shipping a layout with the same name in your mod's `gui/layouts/`, which replaces the whole layout: heavy, and brittle across DayZ updates. The Tier 2 file is more exact about what that takes: a copy under your own PBO prefix replaces nothing, and you either point the script that calls `CreateWidgets` at your copy or recolor widgets after `super` (`skills/_shared/conventions/ui.md`). Since DayZ 1.30 a layout variant can change single vanilla widgets in place: `layout-variants-130.md`.

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

   The source wrote this example as `IngameHud.UpdateBleedIcon()` with a field `m_BleedIcon`. Neither name exists in `P:\scripts`, so the example is shown here with placeholder names.

3. **`Colors` and `FadeColors` constants in `P:\scripts\3_game\colors.c`.**

   These look like the obvious target for a theme override. They are not. The source states that `modded class Colors { const int X = ...; }` does nothing for compile time constants, because callers already baked in the original integer when they were compiled. The Tier 2 file lists that as reported and not yet tested in Workbench; test it before relying on it either way.

   What is checked: `COLOR_DAYZ_RED`, the constant most often named as "DayZ red", is declared as `const int COLOR_DAYZ_RED = 0xffd70d11;` at `P:\scripts\3_game\colors.c:53` and is used in exactly one place in vanilla script, `SetBannerColor(Colors.COLOR_DAYZ_RED)` at `P:\scripts\5_mission\gui\newui\mainmenu\mainmenupromo.c:157`, the main menu promo banner. So even a working override of that constant would recolor one element.

### What that means

A request like "change all the red UI to blue" is hours of work, not minutes. It takes:

- Sweeping `.layout` files for per widget color values and replacing each one.
- Finding every `SetColor(<red ARGB>)` call under `5_mission/gui/` and overriding the method around it with `modded class`.
- Leaving the `Colors` constants alone; they are a false lead.

### How to scope a theme request

When the user asks for a UI color change, ask first:

- **A single element** ("the bleeding icon", "the menu hover state"): feasible. It is one method override, one layout swap, or on 1.30 one layout variant.
- **All red to all blue** ("retheme the whole UI"): push back. Define the scope piece by piece and treat it as a batch. No framework makes it a one property edit.

Never accept "change all the red" as a one file task. Tell the user what this section says before estimating the effort.

### Colorful UI, and what "CUI" means

Corrected by the source author on 2026-07-05; the earlier recommendation was wrongly sourced.

- Reported by the source: there is no DayZ project named "Community UI Framework". In the DayZ community, CUI means **Colorful UI** by DayZ-n-Chill (`github.com/DayZ-n-Chill/DayZ-Colorful-UI`), described there as an MIT licensed "Community Edition Template" at version 2.5 (latest release reported as v2.5.1, June 2024), with a separate "Pro" variant under CC BY-NC 4.0, whose non commercial clause matters for monetized servers. These release and license details are the source's reading and were not checked for this pack.
- Its mechanism, as the source describes it, is to ship every default layout again as a file you can edit on its own ("Customize every element individually"). That is the same per layout mechanism this file calls heavy. It is not a central theme layer that spreads one color everywhere.

What follows from that:

1. Do not promise that adopting Colorful UI turns a retheme into one property edits. Nothing in the ecosystem does that.
2. Colorful UI is useful as a starting template when the goal is "reskin the whole vanilla UI": it has already done the work of shipping the layouts again.
3. For a one off recolor in an existing mod, stay scoped to the one element. On 1.30 a layout variant does that without shipping the whole layout: `layout-variants-130.md`.

Also reported by the source: Community Framework (CF) ships no MVC or UI layer (its changelog marks MVC as deprecated in 1.1 and removed in 1.3.1). The only CF UI surface worth knowing is its `NotificationSystem`, which is server aware.

---

## Color system

- **Never call `Widget.SetLV()` or `Widget.SetTextLV()` from a mod.** They are `proto static`, so they are global and not per widget; the engine comment says "Set global LV of widgets" (`P:\scripts\1_core\proto\enwidgets.c:114-117`). Vanilla uses exactly those two calls to apply the player's brightness preference: `SetHudBrightness()` is `Widget.SetLV(value); Widget.SetTextLV(value);` (`P:\scripts\3_game\dayzgame.c:3910-3914`), fed from `EDayZProfilesOptions.HUD_BRIGHTNESS` through `GetHUDBrightnessSetting()` (`P:\scripts\3_game\dayzgame.c:3916-3919`), and called from `OnInitialize()` (`P:\scripts\3_game\dayzgame.c:2109-2114`). So `SetLV(0)` at mod init does not "normalize colors". It overwrites the player's HUD brightness setting, globally, for the vanilla UI too.
- If your colors look darker than their hex values, that is the player's brightness setting doing its job. Design against it: pick colors that survive it, and check them at a HUD brightness other than zero. Do not flatten it.
- The measurement of 2026-03-24 behind the old advice was real (saturated colors barely changed; grays and pastels came out much darker), but it measured that machine's HUD brightness, not an engine constant. The documented default of `SetLV` is 0; a machine that draws dark has a negative value in its profile.
- This corrects advice the source skill gave until 2026-08-22, which said "one line fixes everything" and told mods to make the call at init. It was wrong in six places. It was found in a review of the LFHeli mod; that HUD removed both calls and its UI checks still passed. The harness that produced the first measurement is `color-test-harness.md`.
- **Low alpha is clamped to invisible by the engine.** Measured in game: 0x12 (18) drew nothing and 0x26 (38) was visible, so the threshold is somewhere above 0x12 and at or below 0x26. Stay at 0x30 (48) or more for anything that must be seen, and treat 0x13 to 0x2F as untested. Corrected on 2026-07-04: an older line said "below 0x30 is invisible", which its own "0x26 works" example contradicted.
- A layout writes colors as floats from 0.0 to 1.0. Script `ARGB()` takes integers from 0 to 255.
- Dabs `LinearColor` has about 150 named colors, HSV, `Lerp` and blend modes (`dabs-framework.md`).
- `ButtonWidget.SetColor()` works directly; a button needs no `LoadImageFile` first (seen in Dabs's `SampleMVC.c`).
- The alpha in a layout `color` on an `ImageWidget` with no texture is ignored when it is drawn; see `text-sizing-and-rendering.md` for that and for the blend settings transparent images need.
