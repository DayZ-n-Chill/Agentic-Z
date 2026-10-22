---
name: dayz-ask
description: "Answers a plain English question about vanilla DayZ with checked path:line citations. Use when the user asks how vanilla does something, where it lives, or what a vanilla class or config value does."
argument-hint: "\"<question>\" [--top-k N] [--file-type T] [--folder F] [--grep] [--json]"
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-ask

A script finds and checks the evidence. You read it and write the answer. Every claim in the answer cites a line the script read from disk. The script runs the RAG search, checks every hit against the file on `P:\`, and falls back to a keyword Grep of the vanilla folders when there is no `VOYAGE_API_KEY` or index.

Follow `.claude/skills/_shared/dayz-conventions.md`. Format the answer per `.claude/skills/_shared/answer-formatting.md`.

## How to run

```cmd
python "<skill-dir>\ask.py" "<question>" [--json]
```

| Argument | Notes |
|---|---|
| `"<question>"` | The user's question in their words. |
| `--top-k N` | Search hits, or Grep files, to keep (1 to 25, default 5). |
| `--file-type T` | Only one file type: `c`, `cpp`, `hpp`, `h`, `layout`, `cfg`, `rvmat`, `xml`, `json` or `csv`. Use `cpp` for `config.cpp` questions and `c` for script questions. |
| `--folder F` | Vanilla folder for the Grep fallback: `scripts`, `dz`, `gui`, `core`, `graphics` or `languagecore`. Repeat it for more than one. The default is `scripts` and `dz`. |
| `--grep` | Skip RAG and use the Grep fallback. |
| `--json` | Print the report as JSON after the verdict line. |

## What the script does

1. Runs `search_dayz_source` from the `dayz-rag` server when the index is built and `VOYAGE_API_KEY` is set. Each run is a new process, so the dayz-rag server's in-memory cache does not carry over between `/dayz-ask` runs; the MCP tool `search_dayz_source` in a session does reuse it.
2. Reads every hit's lines from `P:\`. A hit is `verified` when the cited lines still hold the indexed text, or `moved` when the text now sits at other lines, in which case the citation points at the new lines. A hit whose text is gone is dropped and listed under `dropped`.
3. Falls back to Grep when there is no key, no index, the search fails, or no hit survives the check. It splits the question into search terms, scans the vanilla folders, and ranks files by how many of the rarer terms they hold. Grep citations are lines read from disk, so they count as checked.

## Output and exit codes

The first line is the verdict: `EVIDENCE` (exit 0), `NONE` (exit 1, nothing found) or `ERROR` (exit 2: empty question, bad argument, or `P:\` not mounted). Notes follow, then each citation with the lines read from disk:

```
EVIDENCE 2 citation(s) via rag
[1] P:\scripts\4_world\classes\bleedingsources\bleedingsource.c:7-203  verified  distance=0.708  BleedingSource
    | class BleedingSource
    | ...
```

`via` is `rag`, `grep`, or `rag+grep` when RAG gave no surviving hit (none returned, or all dropped). An excerpt shows at most 60 lines.

With `--json`, the report holds `verdict`, `question`, `mode`, `notes`, `citations` and `dropped`. Each citation has `cite` (`path:line_start-line_end`), `path`, `line_start`, `line_end`, `status`, `source` (`rag` or `grep`) and `excerpt`; RAG citations add `distance` and `context`, Grep citations add `match_line` and `terms_in_file`.

## Writing the answer

- Answer only from the excerpts. When the answer needs lines past an excerpt, read them with `get_dayz_file` or `Read` first.
- Cite every claim as `path:line_start-line_end`, using the `cite` value or a narrower range inside it.
- Lead with the answer in a sentence or two, then the supporting citations.
- Grep results match words, not meaning. Use only the citations that answer the question and ignore the rest.
- If the evidence does not answer the question, say so, and suggest a narrower question or a `--file-type` or `--folder`. Do not fill the gap from memory.
- Pass on each note that names a fix: a missing key, a missing index, or dropped hits that call for `/dayz-search-index --full`.

## Limits

- It reads vanilla files only, never your mod.
- Grep ranks by words, so a question about behaviour can return lines that only share a word with it. The RAG search ranks by meaning.
- It checks that `P:\` is mounted itself and does not run `/dayz-preflight`, since it only reads files. Mount the drive with `/dayz-workdrive`.
