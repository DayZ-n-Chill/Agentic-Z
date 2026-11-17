# Authoring lessons

Rules for people and agents who write skills, helper scripts and tests in this repo. Each one comes from a defect that shipped in a skill, a script or a test and was then fixed. None is a DayZ game fact; the game facts are in `skills/_shared/knowledge/`.

## Python on Windows

- **A Windows path inside a plain Python string can stop the file from parsing.** `C:\Users` in a normal string reads as a `\U` escape and Python refuses the file with `truncated \UXXXXXXXX escape`. A `\v` in `DZ\vehicles` silently becomes a vertical tab. Write any string that carries a Windows path, or a placeholder a path will replace, as a raw string.
- **`Path.is_junction` is new in Python 3.12.** On 3.10 and 3.11 a directory junction looks like a plain directory unless the code reads the reparse tag from `os.lstat`. `Path.exists()` follows a junction (a junction whose target is gone reads as absent), `Path.is_symlink()` does not see one, and `shutil.rmtree` refuses one: unlink a junction instead.
- **Do not decode `cmd.exe` output as UTF-8.** `cmd /c mklink /J` writes its message in the console's OEM code page (cp850 on a Spanish-locale host), and decoding it as UTF-8 raises in the reader thread. Keep the output as bytes and read the return code.
- **Read text files with an explicit encoding.** A packager that opened `SKILL.md` with the default encoding died on the first em-dash or accent under cp1252.
- **A script that swaps Windows paths inside a TOML file edits TOML escapes, not path bytes.** Parse the rewritten file with `tomllib` and compare the decoded path with the intended one before using it.

## Shell quoting

- **PowerShell double quotes eat a backtick and the letter after it.** Skill text written through a double-quoted PowerShell string lost the first letter of `requiredAddons`, `nullptr`, `null`, `try`, `throw`, `for` and `break`. Use single quotes, a here-string, or write the file with the Write tool.
- **Never glob-expand data.** A tag list or a file list read from a config is split as data, not passed unquoted to the shell.

## Tests

- **Two test files with the same name in different folders abort a single pytest run** under the default import mode ("import file mismatch", exit 2), so nothing in either folder runs. Give test files unique names, or run each folder in its own process.
- **A test module that imports an optional dependency at the top is a collection error, not a skip.** One `import bpy` kept 40 unrelated tests beside it from running. Skip with `pytest.importorskip` (numpy, Pillow, `bpy`) so the folder still runs on a machine with only pytest.
- **A check that only records its result always passes under pytest.** A test whose `check()` helper stored failures instead of asserting gave "9 passed" with a real failure inside. Assert, and prove the test can fail by mutating the code under test once.
- **A gate that runs only when no error is present can hide that it never ran.** One gate reported `SKIPPED` with no reason for weeks. A skipped check prints why.
- **Blender exits 0 on an uncaught Python exception** unless it is started with `--python-exit-code 1`. Blender's bundled Python has no pytest.
- **A privacy or path check must cover the flattened form too.** A check for machine paths that looked for path separators missed the same path written as one dash-joined name.

## Skill files

- **An unquoted `: ` inside a YAML `description` parses as a nested mapping.** Two skill descriptions were invalid YAML and the skill validator in use at the time passed them. Quote any description that holds a colon followed by a space.
- **Do not ship a live `.mcp.json` as an example.** Agents auto-start the servers it declares, and a failed launch on every session is worse than no config. Name the example `.mcp.example.json`.
- **When a fact is corrected, grep every file that states it.** The largest group of fixes on record is one rule corrected at its source and left wrong at its call sites.

## Git

- **`git ls-files` lists a path in conflict once per index stage** (up to three times) in the middle of a merge. Deduplicate before counting or compiling the list.
- **A squash merge can commit conflict markers.** A check for lines that start with seven `<` or `>` characters catches them; `=======` counts only between the two, so a Markdown heading underline does not trip it.
