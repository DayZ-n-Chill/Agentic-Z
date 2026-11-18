# Validator scripts for a CI pipeline

Which reference validators exist for a build pipeline outside this repo's own gates, which of them work, how their exit codes gate a build, and how to run them in CI. They are code to adapt, not bundled scripts; in this repo `/dayz-lint` and `/dayz-p3d-audit` are the gates.

## What there is

| Validator | State | Use in this repo instead |
|---|---|---|
| `config_cpp_validator.py` (`config-validator-script.md`) | Works; regex heuristics for braces, semicolons, `CfgPatches`, `hiddenSelections` and duplicates | `/dayz-lint` parses `config.cpp` and is the gate `/dayz-build-pbo` runs. |
| `texture_path_checker.py` (`texture-path-checker-script.md`) | Works; resolves every quoted `.paa` and `.rvmat` from the work drive root and warns on capitalisation | `/dayz-lint` (missing files) and `/dayz-p3d-audit`. |
| A stringtable validator | Not written for DayZ; the plan is below | None yet. |
| A `.p3d` LOD checker | Not written; the plan is below | `/dayz-p3d-audit`. |

Each validator prints JSON and exits 0 for pass, 1 for fail and 2 for warnings only. Gate on exit 1 alone: `config_cpp_validator.py` warns on every vanilla-style array line whose brace sits on the next line, such as `hiddenSelections[]=` (`P:\DZ\gear\tools\config.cpp:79`), so a correct config can exit 2.

They need Python 3.7 or later and only the standard library. A `.p3d` check also needs this repo's DayZ py3d, 1.6.0 or later, installed with `pip install -e scripts/tools/py3d`. Never `pip install py3d`: on PyPI that name is an unrelated point cloud library.

## The stringtable validator to write

The imported version parsed `stringtable.xml`, the Arma 3 form, so against a DayZ addon it reported "stringtable not found" for every mod with a good `stringtable.csv`. It is not kept. A DayZ version:

- reads `stringtable.csv` at the addon root, and takes column 1 of every data row as the key set (the key has no leading `#`);
- collects `#STR_` references from `.c` and `.cpp` files, `config.cpp` and every `.layout`;
- fails on a referenced key that is missing, on a CSV with fewer than the seven reference columns, and on a row whose column count differs from the header's;
- warns on keys never referenced and on empty language cells.

The rules behind each line are in `stringtable-and-script-checks.md`. Run a new validator against a real addon before trusting it.

## The LOD checker to write

The imported `p3d_lod_checker.py` did not run as written: it imported `P3D` and called `P3d.read(path)`, while py3d's `P3D` takes an open file (`P3D(f)`), and nothing ever set its resolution LOD flag. It is not kept; `/dayz-p3d-audit` does this job. A rewrite would classify LODs by their numeric resolution, a float: Geometry `1e13`, Memory `1e15`, View Geometry `6e15`, Fire Geometry `7e15`. The checks themselves are listed in `asset-checks.md`, "LODs".

## Running them together

`run_all_validations.py` runs the config and texture validators from its own folder and merges their reports. A validator that crashes or cannot start returns `{'error': ...}` with no `errors` list; it checked nothing, so it counts as a failure.

```python
#!/usr/bin/env python3
"""
Run all validators and produce unified report
"""
import subprocess
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

def run_validator(script: str, target: str) -> dict:
    """Run a validator script and return JSON result"""
    try:
        result = subprocess.run(
            [sys.executable, str(HERE / script), target],
            capture_output=True,
            text=True,
            timeout=30
        )
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {'error': f'Invalid JSON output from {script}', 'stderr': result.stderr}
    except subprocess.TimeoutExpired:
        return {'error': f'{script} timed out'}
    except Exception as e:
        return {'error': str(e)}

if __name__ == '__main__':
    addon_root = sys.argv[1] if len(sys.argv) > 1 else '.'

    # config_cpp_validator.py takes the config.cpp file; the others take the addon root.
    # There is no stringtable or LOD validator yet; check models with /dayz-p3d-audit.
    validators = [
        ('config_cpp_validator.py', str(Path(addon_root) / 'config.cpp')),
        ('texture_path_checker.py', addon_root)
    ]

    results = {}
    total_errors = 0
    total_warnings = 0

    for validator, target in validators:
        name = validator.replace('_', ' ').replace('.py', '').title()
        results[name] = run_validator(validator, target)

        # A validator that crashed or could not start returns {'error': ...} with no
        # 'errors' list; it checked nothing, so it counts as a failure.
        if 'error' in results[name]:
            total_errors += 1
        if 'errors' in results[name]:
            total_errors += len(results[name]['errors'])
        if 'warnings' in results[name]:
            total_warnings += len(results[name]['warnings'])

    report = {
        'addon_root': addon_root,
        'validators': results,
        'summary': {
            'total_errors': total_errors,
            'total_warnings': total_warnings,
            'status': 'FAIL' if total_errors > 0 else ('WARN' if total_warnings > 0 else 'PASS')
        }
    }

    print(json.dumps(report, indent=2))
    sys.exit(1 if total_errors > 0 else 2 if total_warnings > 0 else 0)
```

```bash
python run_all_validations.py /path/to/addon
python run_all_validations.py .; [ $? -ne 1 ] && echo "Ready for AddonBuilder"
```

## In a build script

Extract the validators from their files first; there is no bundled `validate.py`.

```bat
@echo off
echo Validating addon...
python config_cpp_validator.py "P:\MyMod\config.cpp"
rem Exit 2 means warnings only and does not block the pack.
if %ERRORLEVEL% EQU 1 (
    echo Validation failed, skipping pack
    exit /b 1
)
echo Validation passed, packing...
AddonBuilder.exe P:\MyMod P:\Mods\@MyMod\Addons -prefix=MyMod -temp=P:\temp\MyMod -include=include.lst -clear
```

`include.lst` is the include list beside this skill's `build.py`; without `-include`, the binarizing pass drops `.c` and `.csv` files (`post-build-gates.md`).

## In GitHub Actions

`texture_path_checker.py` resolves paths from the work drive, so the step needs a self-hosted Windows runner with `P:\` mounted, the addon at `P:\<prefix>` and vanilla data unpacked. A GitHub-hosted runner has no `P:\`, and the checker exits 1 with "work drive root P:\ not found".

```yaml
- name: Validate DayZ addon
  # Needs the work drive: a self-hosted Windows runner with P:\ mounted.
  working-directory: P:\MyMod
  shell: bash
  run: |
    # Exit 2 means warnings only; fail the step on exit 1 alone.
    rc=0; python config_cpp_validator.py config.cpp || rc=$?
    [ "$rc" -eq 1 ] && exit 1
    rc=0; python texture_path_checker.py . 'P:\' || rc=$?
    [ "$rc" -eq 1 ] && exit 1
    echo "Validation passed, ready for build"
```
