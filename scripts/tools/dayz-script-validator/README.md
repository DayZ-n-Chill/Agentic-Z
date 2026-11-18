# dayz-script-validator

Offline linter for DayZ Enforce Script, `.layout`, `config.cpp`, `inputs.xml`
and `.rvmat` files. It turns silent compile/runtime failures into a JSON
report before a PBO is packed.

This is the OFFLINE layer. It does not launch DayZ. The in-game check is
`/dayz-gate ingame`, which reads `script.log` and the RPT.

It is a rule linter, not a compiler: a PASS means no rule fired, not that the
script compiles. The engine compile is the only full syntax gate.

## Install

```powershell
python -m pip install -e scripts/tools/dayz-script-validator
```

Python 3.9 or newer is required. No third-party dependencies.

## Invoke

From the repo root, without installing:

```powershell
python scripts/tools/dayz-script-validator/scripts/script_validator.py <addon_root>
python scripts/tools/dayz-script-validator/scripts/ui_reconcile.py <addon_root>
```

After `pip install -e`:

```powershell
python -m dayz_script_validator <addon_root>
```

Exit `0` = PASS, `1` = FAIL, `2` = WARN. Findings are JSON on stdout.

## Rules

`RULES.md` next to this file describes the rules that read more than one
file, the compile errors read from one file, and the `--game-root` check of
which build the vanilla tree is: the evidence behind each rule and what
each one leaves unjudged.

## Where the cited docs live

Rule messages and code comments cite skill docs by the file name they had
when the rule was written. The skills those docs belong to are in this repo
under:

| Cited as | Skill folder |
|---|---|
| `SKILL.md rule N`, `enforce-script-reference SKILL.md`, `pitfalls-advanced.md`, `networking.md`, `memory-management.md` | `skills/_shared/enscript/depth/`. The numbered rules are now named sections of `hard-rules.md` and `action-and-input-rules.md`, and the line numbers predate the split into topic files, so find the cited rule by its subject; the folder `README.md` indexes the files |
| UI pack `README.md`, `layout-format.md` | `skills/_shared/ui/` |
| error catalog and debug protocol | `skills/dayz-launch-test/references/` |
| `dayz-p3d-audit/SKILL.md` | `skills/dayz-p3d-audit/` |

A `file:line` in a message is the line the rule was written against. When
the file or the line no longer matches, look the passage up in that skill
folder by its rule number or its heading.

## Tests

From the repo root (pytest is the only dependency):

```powershell
python -m pytest -q scripts/tools/dayz-script-validator
```

The suite is plain `unittest`, so `python -m unittest discover tests` from
`scripts/tools/dayz-script-validator/` runs it too. The five `--game-root`
tests that read a PBO are skipped when
`scripts/tools/dayz-vehicle-proxy-contract/` is not in the checkout.

## Vanilla control

Bohemia's vanilla script tree compiles and ships, so a linter finding on
it is a false positive by construction. This control runs the validator
over that tree and fails if the findings differ from a measured baseline.

The vanilla tree is Bohemia's and is not redistributed. Without a local
copy the control SKIPs (exit 2) instead of pretending the tree was clean.

A full run on DayZ 1.30 takes about six minutes (the baseline run on
1.30.164289 took 341 seconds). It is a gate, not a unit
test: do not put it in the pytest run.

```powershell
python scripts/tools/dayz-script-validator/scripts/vanilla_control.py
```

`--vanilla-root` defaults to `DAYZ_VANILLA_ROOT`, then `P:\scripts` if that
path exists. The control passes the tree as its own vanilla root, so
`ES-UNDEFINED-CLASS-REF` runs instead of skipping, and vanilla's empty
`requiredAddons[]` is not read as "dependencies unknown": a false positive of
that rule fails the control rather than hiding in a SKIP. `--baseline` defaults to
`tests/baselines/vanilla_control_baseline.json` next to this tool, not the
cwd. `--update` rewrites the baseline on purpose after a DayZ patch or an
accepted change; it prints what moved. Exit 0 is PASS, 1 is FAIL, 2 is
SKIP (no tree, no baseline, unreadable, or a local
`scripts/tools/dayz-script-validator/scripts/shared/vanilla_index.json` that
the validator loads: the baseline
measures the validator without one, so move that file away first).

Every baseline entry carries the reason it is tolerated. `--update` keeps
the reasons already written and cannot invent the missing ones, so it names
every entry left without a note: an allowlist entry nobody triaged is a
finding hiding behind a gate.
