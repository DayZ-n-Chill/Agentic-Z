# Config validator script

A reference `config_cpp_validator.py` to adapt for a CI pipeline: it checks brace balance, semicolons, `CfgPatches`, the `hiddenSelections` arrays per class, duplicate class names and parent classes with regex heuristics, and prints JSON. In this repo `/dayz-lint` parses `config.cpp` properly and is the gate `/dayz-build-pbo` runs; the exit codes and the combined runner are in `validation-scripts.md`.

## What it checks and where it falls short

| Check | Level | Notes |
|---|---|---|
| Brace balance | Error | Counts `{` and `}` and reports a line where the depth goes negative. |
| Semicolons | Warning | Flags a line with `=` that does not end in `;`, `{` or `}`. Vanilla writes `hiddenSelections[]=` with the brace on the next line (`P:\DZ\gear\tools\config.cpp:79`), so a correct config can exit 2. |
| `CfgPatches` | Error; missing members a warning | Looks for `units`, `weapons`, `requiredVersion` and `requiredAddons` anywhere in the `CfgPatches` body, not per patch. |
| `hiddenSelections` | Warning | Walks the file brace by brace so each class owns the arrays in its body. A length mismatch is a warning because the engine accepts a shorter array: vanilla `Flashlight` has 4 selections and 1 material (`P:\DZ\gear\tools\config.cpp:278` to `:295`). |
| Duplicate classes | Warning | Any class name seen twice in the file, nested classes included, so it also flags two `class Front` blocks under different parents. |
| Parent classes | Warning | Compares each parent with a short list of known bases. Check the list against the vanilla configs under `P:\DZ` before extending it. |

It does not check the 1.30 rule that a member defined twice in one class stops binarize (`dayz-1-30-pbo-build.md`).

## Usage

```bash
python config_cpp_validator.py path/to/config.cpp
python config_cpp_validator.py config.cpp | jq '.summary'
```

## The script

The code is `config_cpp_validator.py`, beside this file. It needs Python 3.7 or later and only the standard library; copy it into the pipeline and adapt it there.

## Sample output

```json
{
  "file": "config.cpp",
  "status": "FAIL",
  "errors": [
    {
      "check": "brace_balance",
      "message": "Unbalanced braces: 45 open, 44 close",
      "severity": "critical"
    }
  ],
  "warnings": [],
  "info": {
    "file": "config.cpp",
    "size": 15234,
    "line_count": 287,
    "patches": ["MyMod_MainClass"],
    "patch_count": 1
  },
  "summary": {
    "error_count": 1,
    "warning_count": 0,
    "total_issues": 1
  }
}
```
