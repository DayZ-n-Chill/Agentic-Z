# Texture path checker script

A reference `texture_path_checker.py` to adapt for a CI pipeline: it finds every quoted `.paa` and `.rvmat` in `config.cpp` and in the addon's `.rvmat` files, resolves each one from the work drive root, and warns on stray `.png` and `.dds` files and on file names whose capitalisation differs from the file on disk. In this repo `/dayz-lint` (missing files) and `/dayz-p3d-audit` do this job; the exit codes and the combined runner are in `validation-scripts.md`.

## How it resolves a path

A path in `config.cpp` or a `.rvmat` is a root path that starts with a PBO prefix. Vanilla writes `"dz\gear\tools\data\alarmclock_blue_co.paa"` (`P:\DZ\gear\tools\config.cpp:85`); a mod writes `"MyMod\data\x.paa"`. So the checker resolves each one against the work drive root, `P:\` by default, not against the addon folder: `MyMod\data\x.paa` is looked up at `P:\MyMod\data\x.paa`. A vanilla `dz\...` path is found only when vanilla data is unpacked on `P:\`.

The capitalisation check lists the folder and compares names ignoring case, because a literal glob returns the pattern's own spelling on Windows and finds nothing on a case-sensitive file system. It compares file names only, not folder names.

## Usage

```bash
python texture_path_checker.py path/to/addon/root [work_drive_root]
```

It needs the work drive mounted with the addon at `P:\<prefix>`; without it the checker exits 1 with "work drive root P:\ not found".

## The script

The code is `texture_path_checker.py`, beside this file. It needs Python 3.7 or later and only the standard library; copy it into the pipeline and adapt it there.

## Sample output

```json
{
  "addon_root": "/path/to/addon",
  "status": "FAIL",
  "errors": [
    {
      "type": "texture",
      "reference": "MyMod\\data\\textures\\body_co.paa",
      "expected_path": "P:\\MyMod\\data\\textures\\body_co.paa",
      "message": "TEXTURE file not found",
      "severity": "critical"
    }
  ],
  "warnings": [],
  "summary": {
    "total_references": 8,
    "valid_files": 7,
    "missing_files": 1,
    "format_warnings": 0
  }
}
```
