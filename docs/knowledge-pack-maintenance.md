# Knowledge Pack machinery: how its gates and promotions work

The DayZ Modding Knowledge Pack came with its own validation, packaging and promotion tooling (`packctl`) and contribution rules. The tooling now lives under `scripts/dev/knowledge-pack/`. This page keeps the rules and commands that went with it, so the tooling can still be understood and run. It describes how the Knowledge Pack's own repository was maintained; Agentic-Z's contribution rules are in the root `CONTRIBUTING.md` and win where the two differ.

In the Knowledge Pack's repository the commands below ran from the repository root and `skills/`, `tools/`, `sources/`, `promotions/` and `evals/` sat at the top level. Here `packctl`, `sources/`, `promotions/`, `decisions/`, `examples/end-to-end/` and the `packctl` tests sit under `scripts/dev/knowledge-pack/`, and the tools under `scripts/tools/`. Paths below are written for this repo. What was run during the import: the `packctl` test suite passes from this repo's root (`python -m pytest -q scripts/dev/knowledge-pack`; tests that need the original pack tree skip unless the environment variable `KP_SOURCE_ROOT` points at a checkout of it), and `python -m packctl validate --root <checkout of the original pack>` returned PASS. `validate`, `gate` and `build` are not meant to pass with `--root` set to this repo, because they expect the Knowledge Pack's own layout (`sources/source-map.json`, `tools/` and so on at the root).

## What each folder is

| Folder (under `scripts/dev/knowledge-pack/`) | What it is |
|---|---|
| `packctl/` | The validation, gating and packaging CLI. Standard library only. |
| `sources/` | Provenance: every distributed file's origin, licence and hash (`source-map.json`), and the executable-claim records (`claims.json`). |
| `promotions/` | The routing contract for promoting pack content into installed skill trees (`promotion-map.json`, receipts). |
| `decisions/` | Decision records. |
| `examples/end-to-end/` | A worked example that chains the tools on a synthetic MLOD. |
| `tests/packctl/` | The suite for `packctl`. |

## Gates

Install the CLI once. Without the install, `python -m packctl` resolves only while the shell stands in the folder that holds `packctl/`:

```text
pip install -e scripts/dev/knowledge-pack
```

It is standard library only, so the install adds no dependency: it adds an importable module and a `packctl` entry point. The gates are offline and deterministic.

```text
python -m packctl validate --root . --report reports/validate.json
python -m packctl gate --root . --report-dir ../pack-gate-reports
python -m pytest -q tests/packctl
```

- `validate` checks provenance, privacy, links and claim ranges.
- `gate` adds skill validation, Python compilation, the test suites (`tests/packctl`, the py3d tests, and each `skills/<skill>/tests` and tool `tests` folder in its own pytest process), the `.layout` corpus and a reproducible build. It is the one that had to be green before publishing.
- `build` produces the release archive and refuses to run from a dirty tree. A release is built from a committed state or it is not a release.
- `python -m packctl test-folders --root . --tree skills --tree tools --report-dir ../pack-test-reports` runs only the test folders, one pytest process each.
- A test that needs Blender, DayZ or the `P:` drive skips where they are absent. A folder fails the gate when a test fails or does not run (deselected, kept out of collection, or in a `test_*.py` module that yields no test).

Three things that fail without saying much:

- **The gate's report directory must sit outside the repository.** `gate` builds the release twice to prove reproducibility, so writing reports into the tree would contaminate the input it is measuring. It refuses with `GATE-REPORT-IN-ROOT`, and refuses before writing a report, so the only symptom is a silent exit 1.
- **The gate needs the external Agent Skills validator**, pinned through `PACK_SKILLS_REF_ROOT` (a checkout or the executable itself). It is on PyPI as `skills-ref` (the pinned version is `skills-ref==0.1.1`); the console script is named `agentskills`. Without it the `skills_ref` check fails closed; it is not skipped. Reproducible install: `python -m venv <root>`, then `<root>/Scripts/pip install skills-ref==0.1.1`, then set `PACK_SKILLS_REF_ROOT=<root>`.
- **In the Knowledge Pack's repository, `pytest` could not run from the root.** The suites were per tool by design and two shared test-module basenames (`test_cli.py`, `_support.py`), so a root-level collection aborted before a single test ran. Agentic-Z's test command collects from the root, so the imported suites had to be made to coexist.

### The linter's vanilla control

Before committing any change under `scripts/tools/dayz-script-validator/` (a new rule, a touched detector, a touched parser), run the vanilla control:

```text
python scripts/tools/dayz-script-validator/scripts/vanilla_control.py
```

Bohemia's tree compiles and ships, so a new finding on it is a false positive by construction. A green control does not authorize the change: it proves the rule is silent on correct code, not that it catches anything. Without a local vanilla tree the control SKIPs (exit 2). A full run on DayZ 1.30 takes two to four minutes. It is not a step in making a mod.

## Contribution workflow the pack required

1. **Discover before generating.** Search the current pack, vanilla scripts, official documentation and relevant upstream projects before creating a competing rule or tool.
2. **Map the source.** Add or update the entry in `sources/source-map.json`. Pin revisions and hashes; never use modification time as authority.
3. **Register executable claims.** A new API, signature, command, schema field or engine claim needs a `claim_id` in `sources/claims.json`, with exact evidence and verification level.
4. **Label examples.** `[EXACT]` only for content verified against the cited source; `[DESIGN]` for pseudocode or a proposal that still needs implementation-specific verification.
5. **Test the smallest contract first.** Positive and negative fixtures before implementation, then the gate.
6. **Check licensing and privacy.** No third-party payload until its licence is known and compatible. Never commit secrets, personal identities, machine-specific absolute paths, private PBOs or proprietary game data. GPL, DPL-ND, CC-NC, proprietary Workshop content and Bohemia game data may be cited or studied, but were not accepted as payload.
7. **Promote only a green commit, and edit at the source.** For any skill listed in `promotions/promotion-map.json`, the repository is the editable source: edit the skill, reseal `sources/source-map.json`, and land a commit with `packctl validate` green. The installed user tree and plugin trees are promotion targets. A hand edit there is what `PROMOTION-TARGET-UNEXPLAINED` exists to catch, and it blocks the next promotion for every session. Skills absent from the map are unaffected. (Direction fixed 2026-09-04: `packctl` enforces this direction with executable gates, `SOURCE-HASH-MISMATCH` and `PROMOTION-TARGET-UNEXPLAINED`, and nothing enforced the other; a document without a gate loses to a gate.)

More rules from the same guide:

- Use public aliases such as `VANILLA`, `VAULT` and `SKILL_SOURCE` in versioned files. Physical roots belong only in ignored local configuration.
- Keep each change traceable to a product criterion (`docs/knowledge-pack-product-spec.md`) and avoid adjacent refactors. Update the changelog, the compatibility matrix and durable evidence when the change affects them.
- A release candidate must build twice to a byte-identical ZIP before promotion. A release was created only after the gate passed from a clean commit and two clean builds produced the same SHA-256.
- Harvest from a working store is by union, never a wipe of the destination.
- **The source game of a ripped vehicle is called `rip`.** Importing vehicle geometry out of a commercial racing game is a technique the pack documents; the publisher's name and its engine's name are not part of the technique and are not written. Write `rip`, `rip-import`, `source-game`. The pack checked this with the pattern `(?i:\bforza)(?![dnr])`: case-insensitive on the name, with a case-sensitive `[dnr]` exclusion so the Spanish words `forzado`, `forzar` and `forzando` do not match while a compound such as `ForzaDayZ` still does. The simpler `\bForza(?![a-z])` is wrong: being case-sensitive it never sees a lowercase slug. One deliberate exception: the three publish receipts under `tests/packctl/fixtures/receipt_history/` record `skill/forza-to-dayz` as an artifact id. A receipt states what was published on a given day under the name it had; rewriting it would falsify the record and break the fixtures that assert on it.

## Promoting governed skills

Skills listed in `promotions/promotion-map.json` are governed: they have one editable source. Skills present in a user tree but absent from the map are not governed and keep their own authority; they are not added silently.

- **Isolate the change.** Each skill change gets its own branch and git worktree. Do not share a dirty index across concurrent edits of governed skills.
- **Review, validate, then commit.** Run `python -m packctl validate --root <repo> --report <report-outside-the-repo>` on that worktree and commit. Promotion reads a clean commit; a dirty tree fails `promote --check` with `PROMOTION-DIRTY`. Confirm the current flags with `python -m packctl promote --help`.

### First promotion into empty destinations (schema 2 bootstrap)

A first promotion uses `--bootstrap`, not `--check`. `--bootstrap` is mutually exclusive with `--check`, `--apply` and `--recover`.

1. Copy `promotions/local-targets.example.json` to a gitignored contract (default path `promotions/local-targets.json`). Keep `schema_version` at `2`.
2. Set `installation_id` to a new canonical lowercase UUID v4 (version nibble `4`; variant `8`, `9`, `a` or `b`; `uuid.UUID(value)` must round-trip to the same string). Do not reuse an id that already has a receipt.
3. Create `backup_root` and each `targets.*.path` as existing empty directories you own. Routed artifact destinations may be absent or empty. `--bootstrap` rejects non-empty backups (`PROMOTION-BACKUP-NONEMPTY`) and non-empty or type-mismatched artifact destinations (`PROMOTION-TARGET-NONEMPTY`, `PROMOTION-TARGET-TYPE-MISMATCH`). Linked parents fail closed.
4. `--bootstrap` requires `--plan` and a version 2 local-target contract. It also requires zero receipts for that `installation_id` (`PROMOTION-INSTALLATION-EXISTS` otherwise). Historical version 1 receipts for other installations are not in that set.

```text
python -m packctl promote --bootstrap --root <repo> --promotion-map promotions/promotion-map.json --local-targets <local-targets.json> --plan <plan.json>
```

Inspect the written plan before applying it: `schema_version` `2`, the same `installation_id`, `bootstrap` true, the full map, and each operation's `after_digest`. Then apply that same plan of that same commit:

```text
python -m packctl promote --apply --plan <plan.json>
```

`--apply` takes the plan; it does not take a second copy of the map. After the apply, read the new receipt under `promotions/receipts/` and confirm the destination bytes match each `after_digest`. Register that receipt (and any other new tracked file) in `sources/source-map.json` and land a commit. There is no `packctl reseal` command; the owner writes the source-map entry.

### Later promotions

Run `python -m packctl promote --check` with `--promotion-map` and `--local-targets` set to explicit paths, inspect the plan, then `--apply` with `--plan` from a green check of that same commit. Read the receipt, confirm the bytes, register the receipt and commit, as above. `--bootstrap` is only the genesis of an installation with no receipts for that UUID.

`--recover` (requires `--transaction-root`) restores a failed or interrupted apply to the preimage recorded in that transaction. It is not a rollback to a previous skill version.

### Session pin

A promotion that overwrites a live skill target does not freeze sessions already running, and it does not rewrite context an agent has already loaded. Per session, record the source commit and consume a copy of the whole governed skill tree taken from an immutable snapshot of that commit. A hash without those files is not a pin, and a copy does not make an agent load it. `scripts/tools/skill-runtime-pin` is the tool for this (`docs/knowledge-pack-tools.md`).

### Version rollback

`packctl promote` walks the full promotion map. There is no per-artifact selector, so a version rollback is a full-map `--check` then `--apply` of an older commit, recorded as a new commit. Keep the installation's receipts and the same `installation_id`. Do not `git reset` the promotion history or delete receipts to pretend an apply did not happen. Inspect every destination in the plan: destinations whose planned `after_digest` equals their current bytes must keep that digest. Do not claim a per-skill rollback.

## Local files the machinery expects to be ignored

The Knowledge Pack's `.gitignore` kept these out of version control (paths as in its repository; here they fall under `scripts/dev/knowledge-pack/` except the last):

```text
sources/local-roots.json
promotions/local-targets.json
promotions/plans/
promotions/journals/
promotions/backups/
dist/
reports/
build/
*.egg-info/
examples/end-to-end/work/
skills/*/scripts/agent_calls.jsonl
```

Its `.gitattributes` stored all text with LF line endings (`* text eol=lf`) and marked `*.p3d`, `*.rtm` and `*.seanim` as binary, so git never rewrites the model and animation fixtures.
