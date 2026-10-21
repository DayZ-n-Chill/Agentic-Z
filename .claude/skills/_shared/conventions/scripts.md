# DayZ script conventions (Tier 2 topic)

Part of Tier 2. Enforce Script layout and the `modded class` rule; code style itself is in `.claude/skills/_shared/enscript-style.md`. Read it together with the core rules in `.claude/skills/_shared/dayz-conventions.md`, which still apply.

## Script conventions

- Enforce Script (DayZ's C#-like language), styled per `enscript-style.md`.
- Folder modules:
  - `scripts/3_Game/`: base game logic
  - `scripts/4_World/`: world-level logic
  - `scripts/5_Mission/`: mission / server scripts
- Use `modded class Foo { ... }` for non-destructive overrides, with NO `extends` clause. `modded class Foo extends Foo` compiles but is a silent no-op.
