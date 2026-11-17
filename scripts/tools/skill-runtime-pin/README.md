# skill-runtime-pin

Stdlib pin of a **complete repo commit** into a new task-local root, plus one
derived discovery adapter. It is not a universal launcher, not a catalog
quarantine, and it does not run Cursor or Codex.

The capture is every git blob of the named commit, byte-identical, with path /
blob / SHA-256 / size in a manifest. The only extra skill file is:

`<probe-root>/.agents/skills/<skill>-<short-commit>/SKILL.md`

That adapter is **DERIVED**: `name` matches its folder, it points at the
captured `skills/<skill>/SKILL.md`, and it holds a task-local canary. The
captured original is never rewritten. The nonce lives in that adapter and in a
receipt **outside** `<probe-root>`. Assembled consumer prompts do not include it.

## Contract

- Default skill: `dayz-mod-workflow`. `--skill` must be a single hyphenated
  name that exists as `skills/<skill>/SKILL.md` in the commit.
- Source worktree must be clean. The commit is read through `git ls-tree` /
  `git cat-file`, not the working tree.
- Rejected: dirty source, symlink (`120000`), gitlink/submodule (`160000`),
  path traversal, blob/size/hash mismatch, existing task-root, overlap with
  the source tree.
- Runtime inputs and outputs stay under the new task-local root. The source
  tree is not overwritten.
- `verify` enumerates `<probe-root>` without following links, ignores only
  `.git/**`, and requires the physical file set to be exactly capture blobs +
  the derived adapter. Extra files, symlinks and reparse points fail
  `verify` and therefore `assemble` / `inspect-prompt` / `grade`.
- Catalog identity is an exact canonical path. `inspect-prompt` resolves
  Codex `Skill roots` aliases (`rN/...`) and does not accept another root
  that merely shares a suffix or a copied SHA-256.
- Cursor has no exclusive-catalog flag. Codex `--ignore-user-config` does not
  isolate `$HOME/.agents`. Homogeneous global copies are not disabled. The pin
  is the versioned alias plus a later probe that must show the nonce **and**
  consumption of the original captured `SKILL.md`.
- Lazy reads are accepted only for that original, its `references/` in the
  capture, and the derived adapter itself. Reading only the adapter does not
  count as consuming the original. Zero tool calls are valid only when the host injected that original
  body (exact probe path + hash match). A nonce with neither is a false pass.

## Commands

Run from the repo root, without installing a package:

```powershell
python scripts/tools/skill-runtime-pin/runtime_pin.py materialize --source <source-repo> --commit <sha> --task-root <new-task-root>
python scripts/tools/skill-runtime-pin/runtime_pin.py verify --task-root <task-root>
python scripts/tools/skill-runtime-pin/runtime_pin.py assemble --task-root <task-root> --consumer all
python scripts/tools/skill-runtime-pin/runtime_pin.py inspect-prompt --task-root <task-root> --prompt-input <prompt-input.txt>
python scripts/tools/skill-runtime-pin/runtime_pin.py grade --task-root <task-root> --transcript <transcript.json>
```

For `materialize`, `--task-root` must not exist. It is created as:

```
<task-root>/probe/          # capture + derived adapter (consumer cwd)
<task-root>/manifest.json  # commit, tree, per-file blob/SHA-256/bytes, before/after
<task-root>/receipt.json    # oracle: nonce, original hash/path (never inside probe/)
```

`assemble` later adds `<task-root>/commands.json` with the same `program` and
`argv` arrays it prints.

Exit `0` is `PASS`, `1` is `FAIL` or a refused pin, `2` is usage. Reports are
JSON on stdout. A missing or unreadable `--transcript` or `--prompt-input`, a
transcript that is not JSON, or a transcript whose `tool_reads` is not a list or
whose `injected_bodies` is not a list of objects is a `FAIL` report with code
`TRANSCRIPT-INVALID` or `PROMPT-INPUT-INVALID`.

## Operator sequence

`assemble` emits `program` and `argv` arrays. It does not launch Cursor or
Codex. A live probe is a **new** process: exec that program with that argv list,
cwd the probe root from `assemble`. Do not attach to a session that is already
running.

1. `materialize` the named `--commit` into a new `--task-root`.
2. `verify` that capture.
3. `assemble --consumer all` (or `codex` / `cursor`) and keep the arrays.
4. `inspect-prompt` against the **raw** Codex `codex debug prompt-input`
   dump (`assemble` records that inspect argv). Walk decoded JSON strings;
   do not regex only the escaped file text.
5. Launch the new consumer process. Keep the **complete** stdout JSONL.
   Do not truncate it to the last line.
6. Normalize a grade transcript from those raw streams: `stdout` is the
   final assistant text only; `tool_reads` are successful tool reads actually
   present in the stream. Cursor `result.result` aggregates commentary;
   the final assistant goes to that normalized `stdout`. Do not invent an
   `injected_bodies` entry that was not observed.
7. `grade` that transcript.

A real run that returns the canary without an original `SKILL.md` read (or
an observed injection of that captured file hash) **fails**
`NONCE-WITHOUT-ORIGINAL`. Do not retry until green, and do not treat one
canary as proof the pin is universally reliable. This document does not
claim the owner's isolated consumer matrix is done.

## Assembled consumers — `[DESIGN]` until the owner runs them

`assemble` writes structured `program` and `argv` arrays. It does not
build a PowerShell `-Command`, does not JSON-escape into a shell string, and
does not launch a model, touch auth, or read a global config. A caller execs
the program with that argv list.

Codex (`program` is `codex`; `argv` includes `codex` as argv[0]):

```
codex debug prompt-input runtime-catalog-probe
codex exec --json --ephemeral -s read-only -C <probe-root> -m gpt-5.6-sol $<alias> <prompt>
```

The Codex CLI does not emit `system/init` or a served-model event in this
pin. `assemble` records `requested_model` via `-m` / argv and sets
`limits.codex_emits_system_init` and `limits.served_model_observed` to
false. Do not invent those events.

`inspect-prompt` must see exactly one catalog entry for the alias, at the
derived adapter path. A `codex debug prompt-input` dump is a JSON array of
messages: walk every JSON string, then parse `Skill roots` and skill
`(file: rN/...)` lines **inside that decoded string**. Roots apply only to
entries from the same string. Regexes must not run only on the raw file
with escaped `\n`. A dump that names `r10/<alias>/SKILL.md` after a
`Skill roots` map is resolved against that root. A different absolute root
with the same suffix is not the adapter. Global `dayz-mod-workflow` hits
may remain; they are a different name.

Cursor (`program` is `%LOCALAPPDATA%\cursor-agent\cursor-agent.cmd`; `argv`
is flags then `-p` and the short prompt last):

```
cursor-agent.cmd --mode ask --trust --workspace <probe-root> --output-format stream-json --model cursor-grok-4.6-xhigh -p /<alias> <prompt>
```

The `flags` object repeats those fields for the caller. No exclusive-root
flag is claimed. The adapter is not a byte-identical pin of the original
`SKILL.md`. Identity of the consumed version is nonce + observed read (or
injection) of the captured original.

## Probe transcript

`grade` grades a **normalized reception** of a real log. It is not an
attestation and not a universal launcher. Keep the raw JSONL; the
transcript is a derived object. `stdout.strip()` must equal the
receipt canary and nothing else.

Cursor:

```json
{
  "schema_version": 1,
  "consumer": "cursor",
  "exit_code": 0,
  "stdout": "CANARY:<nonce>",
  "argv": ["--mode", "ask", "--trust", "--workspace", "<probe-root>", "--output-format", "stream-json", "--model", "cursor-grok-4.6-xhigh", "-p", "/<alias> <prompt>"],
  "tool_reads": ["skills/dayz-mod-workflow/SKILL.md"],
  "injected_bodies": [],
  "system_init": {
    "type": "system",
    "subtype": "init",
    "model": "Cursor Grok 4.6 Extra High"
  }
}
```

Codex uses `consumer: "codex"`, the assembled Codex argv (including `-m
gpt-5.6-sol`), and must omit `system_init` / `served_model`. Requested model
is the argv value; served-model is recorded as not observed.

Cursor argv keeps the requested model id `cursor-grok-4.6-xhigh`. The
served event is the raw stream object `{ "type": "system", "subtype":
"init", "model": "Cursor Grok 4.6 Extra High", ... }`. A closed map from
that observed label to the requested id is the only accepted served
model. Do not rewrite the event to `type: system/init` or replace the
label with the argv slug to force a PASS. Extra fields such as
`session_id` may be present. Another served label fails.

`injected_bodies` items are `{ "path": "...", "sha256": "..." }` with a
path that is exactly the captured original inside the probe. A zero-read
transcript passes only when that injected body is the original captured
file hash. Returning the canary after reading only the adapter is
`NONCE-WITHOUT-ORIGINAL`. A canary substring, a missing `exit_code`, or a
foreign absolute path with a copied hash is a failed grade.

## Tests

```powershell
python -m pytest -q -p no:cacheprovider scripts/tools/skill-runtime-pin
python -m pytest -q -p no:cacheprovider scripts/dev/knowledge-pack/tests/packctl/test_packctl_runtime_pin.py
```

The tests need `git` on PATH and build their fixture repositories in a
temporary folder.
