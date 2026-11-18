# persistence-contracts

Offline Python models of the three DayZ save contracts and their tests. They model behaviour; they do not read a mod or a save file. Use them to check a persistence design against the rules in `skills/_shared/persistence/` before writing Enforce Script, and as a test bed when a rule in that pack changes.

| Module | What it models | Pack file it follows |
|---|---|---|
| `persistence_router.py` | The four questions that pick exactly one contract: entity stream, Community Framework ModStorage or a file | `where-to-save.md` |
| `persistence_stream.py` | An entity stream with `super` first, the variable width base data and a load that fails closed | `save-load-contract.md` |
| `persistence_cf.py` | Community Framework framing: framework version, mod count, one framed block per mod, an unloaded mod's block kept | `cf-modstorage.md` |
| `persistence_sidecar.py` | A file with its own header, the temp, verify, backup and replace sequence, injected I/O failures, and the reader that classifies the seven migration inputs | `sidecar-files.md`, `migration-matrix.md` |
| `persistence_checklist.py` | The checklist a format change proposal must pass (old saves, the old reader, the no-change alternative first) | `where-to-save.md`, "Hard stops" |

## Run

Stdlib only for the models; the tests need pytest. Each test imports its model by module name from this folder.

```powershell
python -m pytest -q scripts/tools/persistence-contracts
```

The models need no `P:\` drive, no DayZ Tools and no game, so there is no preflight gate.
