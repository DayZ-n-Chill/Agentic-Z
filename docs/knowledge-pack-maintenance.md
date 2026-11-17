# packctl: how its gates and promotions work

`packctl` is the validation, packaging and promotion CLI in `scripts/dev/knowledge-pack/`. It is standard library only and it is not a step in making a mod. This page holds its commands, the ways it fails without saying much, and the rules that go with it. The contribution rules in the root `CONTRIBUTING.md` win where the two differ.

## What each folder is

| Folder (under `scripts/dev/knowledge-pack/`) | What it is |
|---|---|
| `packctl/` | The validation, gating, packaging and promotion CLI. Standard library only. |
| `sources/` | Schemas for the optional inputs `claims.json` (the claim registry) and `link-allowlist.json`, and `local-roots.example.json`, the template for the untracked `local-roots.json` that names per-machine roots. |
| `promotions/` | The schema of a promotion map (`promotion-map.schema.json`) and the template for the untracked local-target contract (`local-targets.example.json`). |
| `examples/end-to-end/` | A worked example that chains the tools on a synthetic MLOD (`python scripts/dev/knowledge-pack/examples/end-to-end/run.py`). |
| `tests/packctl/` | The suite for `packctl`. |

## Gates

Install the CLI once. Without the install, `python -m packctl` resolves only while `scripts/dev/knowledge-pack` is the current folder or on `PYTHONPATH`:

```text
pip install -e scripts/dev/knowledge-pack
```

It is standard library only, so the install adds no dependency: it adds an importable module and a `packctl` entry point. The gates are offline and deterministic. Run them from the repository root, and write reports outside the repository:

```text
python -m packctl validate --root . --report <reports>/validate.json
python -m packctl gate --root . --report-dir <reports>
python -m pytest -q scripts/dev/knowledge-pack
```

- `validate` checks skill frontmatter, sealed and generated copies, conflict markers, claim markers, links and privacy (secrets and machine paths).
- `gate` adds Python compilation of every tracked `.py` file, the external Agent Skills validator, the test suites (the py3d tests, and each `skills/<skill>/tests` and `scripts/tools/<tool>/tests` folder in its own pytest process), the eval cases in `evals/cases/` and a reproducible build.
- `build` (`--root`, `--output <zip>`, `--report`) produces the release archive of what git tracks, plus a manifest, and refuses to run from a dirty tree (`BUILD-DIRTY`). A release is built from a committed state or it is not a release.
- `python -m packctl test-folders --root . --tree skills --tree tools --report-dir <reports>` runs only the test folders, one pytest process each. `--tree tools` means `scripts/tools/`.
- A test that needs Blender, DayZ or the `P:` drive skips where they are absent. A folder fails the gate when a test fails or does not run (deselected, kept out of collection, or in a `test_*.py` module that yields no test).

Three things that fail without saying much:

- **The gate's report directory must sit outside the repository.** `gate` builds the release twice to prove reproducibility, so writing reports into the tree would contaminate the input it is measuring. It refuses with `GATE-REPORT-IN-ROOT`, and refuses before writing a report, so the only symptom is a silent exit 1.
- **The gate needs the external Agent Skills validator**, pinned through `PACK_SKILLS_REF_ROOT` (a checkout or the executable itself). It is on PyPI as `skills-ref` (the pinned version is `skills-ref==0.1.1`); the console script is named `agentskills`. Without it the `skills_ref` check fails closed with `SKILLS-REF-NOT-CONFIGURED`; it is not skipped. Reproducible install: `python -m venv <root>`, then `<root>/Scripts/pip install skills-ref==0.1.1`, then set `PACK_SKILLS_REF_ROOT=<root>`.
- **Two test modules with the same file name stop a root-level `pytest` run.** The gate runs each `tests` folder in its own process, but the repo's own test command (`python -m pytest -q .claude skills scripts/dev hooks scripts/tools`) collects everything in one, and two files with the same basename in different folders abort that collection with "import file mismatch" before a single test runs. Give every test module a unique name.

### The linter's vanilla control

Before committing any change under `scripts/tools/dayz-script-validator/` (a new rule, a touched detector, a touched parser), run the vanilla control:

```text
python scripts/tools/dayz-script-validator/scripts/vanilla_control.py
```

Bohemia's tree compiles and ships, so a new finding on it is a false positive by construction. A green control does not authorize the change: it proves the rule is silent on correct code, not that it catches anything. Without a local vanilla tree the control SKIPs (exit 2). A full run on DayZ 1.30 takes two to four minutes. It is not a step in making a mod.

## Rules for a change the gates will judge

1. **Discover before generating.** Search the current skills and packs, the vanilla scripts and the official documentation before creating a competing rule or tool.
2. **Register executable claims.** A claim marker in a file under `skills/` (`[EXACT][CLAIM-ID]` or `claim: CLAIM-ID`) needs an entry in the claim registry, `scripts/dev/knowledge-pack/sources/claims.json`, that names the same file, a line range holding the marker and a verification level. `validate` reports a marker without an entry and an entry without its marker. The registry is optional and this repo has none, so no claim is registered here and `validate` would report any marker.
3. **Label examples.** `[EXACT]` only for content verified against the cited vanilla file; `[DESIGN]` for pseudocode or a proposal that still needs implementation-specific verification.
4. **Test the smallest contract first.** Positive and negative fixtures before implementation, then the gate.
5. **Check privacy.** Never commit secrets, personal identities, machine-specific absolute paths, private PBOs, third-party mod content or Bohemia game data. Cite a vanilla file by `path:line`; do not copy it in.
6. **Promote only a green commit, and edit at the source.** For any skill listed in a promotion map, the repository is the editable source: edit the skill there and land a commit with `packctl validate` green. The installed user tree and plugin trees are promotion targets. A hand edit there is what `PROMOTION-TARGET-UNEXPLAINED` exists to catch, and it blocks the next promotion for every session. Skills absent from the map are unaffected. `packctl` enforces this direction with an executable gate and nothing enforces the other; a document without a gate loses to a gate.

More rules:

- Physical roots belong only in ignored local configuration (`scripts/dev/knowledge-pack/sources/local-roots.json`, which names each root by an id and an environment variable). Versioned files use the root ids, never a machine path.
- Keep each change traceable to a criterion (`docs/knowledge-pack-product-spec.md`) and avoid adjacent refactors. Update the compatibility matrix (`docs/compatibility-matrix.md`) when the change affects it.
- A release candidate must build twice to a byte-identical ZIP before promotion. A release is created only after the gate passes from a clean commit and two clean builds produce the same SHA-256.
- Copying skills in from a working store is by union, never a wipe of the destination.
- **The source game of a ripped vehicle is called `rip`.** Importing vehicle geometry out of a commercial racing game is a technique `skills/rip-vehicle-import/` documents; the publisher's name and its engine's name are not part of the technique and are not written. Write `rip`, `rip-import`, `source-game`. A check for the name needs the pattern `(?i:\bforza)(?![dnr])`: case-insensitive on the name, with a case-sensitive `[dnr]` exclusion so the Spanish words `forzado`, `forzar` and `forzando` do not match while a compound such as `ForzaDayZ` still does. The simpler `\bForza(?![a-z])` is wrong: being case-sensitive it never sees a lowercase slug.

## Promoting governed skills

Skills listed in a promotion map are governed: they have one editable source. Skills present in a user tree but absent from the map are not governed and keep their own authority; they are not added silently. This repo ships the schema of the map (`scripts/dev/knowledge-pack/promotions/promotion-map.schema.json`) and no map: write one against the schema and name it with `--promotion-map`.

- **Isolate the change.** Each skill change gets its own branch and git worktree. Do not share a dirty index across concurrent edits of governed skills.
- **Review, validate, then commit.** Run `python -m packctl validate --root <repo> --report <report-outside-the-repo>` on that worktree and commit. Promotion reads a clean commit; a dirty tree fails `promote --check` with `PROMOTION-DIRTY`. Confirm the current flags with `python -m packctl promote --help`.

### First promotion into empty destinations (schema 2 bootstrap)

A first promotion uses `--bootstrap`, not `--check`. `--bootstrap` is mutually exclusive with `--check`, `--apply` and `--recover`.

1. Copy `scripts/dev/knowledge-pack/promotions/local-targets.example.json` to a gitignored contract (`scripts/dev/knowledge-pack/promotions/local-targets.json` is ignored). Keep `schema_version` at `2`.
2. Set `installation_id` to a new canonical lowercase UUID v4 (version nibble `4`; variant `8`, `9`, `a` or `b`; `uuid.UUID(value)` must round-trip to the same string). Do not reuse an id that already has a receipt.
3. Create `backup_root` and each `targets.*.path` as existing empty directories you own. Routed artifact destinations may be absent or empty. `--bootstrap` rejects non-empty backups (`PROMOTION-BACKUP-NONEMPTY`) and non-empty or type-mismatched artifact destinations (`PROMOTION-TARGET-NONEMPTY`, `PROMOTION-TARGET-TYPE-MISMATCH`). Linked parents fail closed.
4. `--bootstrap` requires `--plan` and a version 2 local-target contract. It also requires zero receipts for that `installation_id` (`PROMOTION-INSTALLATION-EXISTS` otherwise).

```text
python -m packctl promote --bootstrap --root <repo> --promotion-map <promotion-map.json> --local-targets <local-targets.json> --plan <plan.json>
```

Inspect the written plan before applying it: `schema_version` `2`, the same `installation_id`, `bootstrap` true, the full map, and each operation's `after_digest`. Then apply that same plan of that same commit:

```text
python -m packctl promote --apply --plan <plan.json>
```

`--apply` takes the plan; it does not take a second copy of the map. After the apply, read the new receipt that it writes under `promotions/receipts/` and confirm the destination bytes match each `after_digest`. Then commit the receipt.

### Later promotions

Run `python -m packctl promote --check` with `--promotion-map` and `--local-targets` set to explicit paths, inspect the plan, then `--apply` with `--plan` from a green check of that same commit. Read the receipt, confirm the bytes and commit the receipt, as above. `--bootstrap` is only the genesis of an installation with no receipts for that UUID.

`--recover` (requires `--transaction-root`) restores a failed or interrupted apply to the preimage recorded in that transaction. It is not a rollback to a previous skill version.

### Session pin

A promotion that overwrites a live skill target does not freeze sessions already running, and it does not rewrite context an agent has already loaded. Per session, record the source commit and consume a copy of the whole governed skill tree taken from an immutable snapshot of that commit. A hash without those files is not a pin, and a copy does not make an agent load it. `scripts/tools/skill-runtime-pin` is the tool for this (`docs/knowledge-pack-tools.md`).

### Version rollback

`packctl promote` walks the full promotion map. There is no per-artifact selector, so a version rollback is a full-map `--check` then `--apply` of an older commit, recorded as a new commit. Keep the installation's receipts and the same `installation_id`. Do not `git reset` the promotion history or delete receipts to pretend an apply did not happen. Inspect every destination in the plan: destinations whose planned `after_digest` equals their current bytes must keep that digest. Do not claim a per-skill rollback.

## Local files that stay out of version control

The root `.gitignore` keeps these out of git:

```text
scripts/dev/knowledge-pack/sources/local-roots.json
scripts/dev/knowledge-pack/promotions/local-targets.json
scripts/dev/knowledge-pack/promotions/plans/
scripts/dev/knowledge-pack/promotions/journals/
scripts/dev/knowledge-pack/promotions/backups/
scripts/dev/knowledge-pack/examples/end-to-end/work/
skills/*/scripts/agent_calls.jsonl
*.egg-info/
```

`*.egg-info/` is what `pip install -e` writes next to a package's source. Reports, release ZIPs and build output have no ignore rule: write them outside the repository.

Line endings matter to the checks that hash bytes. The root `.gitattributes` marks `*.p3d` as binary and keeps `skills/_shared/viewer_core.py` LF, `scripts/tools/.gitattributes` keeps the two files it names LF, and `scripts/dev/knowledge-pack/.gitattributes` checks out everything under that folder with LF, because the `packctl` tests hash those files byte for byte.
