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

```python
#!/usr/bin/env python3
"""
DayZ texture and material path validator
Checks: .paa, .rvmat file existence, file name capitalization, format compatibility
"""
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Optional

class TexturePathChecker:
    def __init__(self, addon_root: str, work_root: str = 'P:\\'):
        self.addon_root = Path(addon_root)
        if not self.addon_root.exists():
            raise FileNotFoundError(f"{addon_root} not found")

        # Config and .rvmat paths start with the PBO prefix, so they resolve from the
        # work drive root (P:\), where the addon sits at P:\<prefix>.
        self.work_root = Path(work_root)
        if not self.work_root.exists():
            raise FileNotFoundError(f"work drive root {work_root} not found")

        self.config_cpp = self.addon_root / 'config.cpp'
        if not self.config_cpp.exists():
            raise FileNotFoundError(f"config.cpp not found in {addon_root}")

        self.errors: List[Dict] = []
        self.warnings: List[Dict] = []
        self.valid_refs: List[Dict] = []

    def validate(self) -> Dict:
        """Run validation"""
        texture_refs = self._extract_texture_references()
        rvmat_refs = self._extract_rvmat_references()

        # Check existence for all refs
        for ref_type, refs in [('texture', texture_refs), ('material', rvmat_refs)]:
            self._verify_files(ref_type, refs)

        # Check for format issues
        self._check_format_issues()

        return self.report()

    def _extract_texture_references(self) -> Set[str]:
        """Extract all .paa references from config.cpp"""
        refs = set()

        if not self.config_cpp.exists():
            return refs

        content = self.config_cpp.read_text(encoding='utf-8-sig')

        # Pattern: "path/file.paa" or 'path/file.paa'
        pattern = r'''["']([^"']*\.paa)["']'''
        matches = re.findall(pattern, content, re.IGNORECASE)

        for match in matches:
            refs.add(match)

        return refs

    def _extract_rvmat_references(self) -> Set[str]:
        """Extract all .rvmat references from config.cpp and existing .rvmat files"""
        refs = set()

        # From config.cpp
        if self.config_cpp.exists():
            content = self.config_cpp.read_text(encoding='utf-8-sig')
            pattern = r'''["']([^"']*\.rvmat)["']'''
            matches = re.findall(pattern, content, re.IGNORECASE)
            refs.update(matches)

        # From .rvmat files (they may reference textures)
        for rvmat_file in self.addon_root.rglob('*.rvmat'):
            try:
                rvmat_content = rvmat_file.read_text(encoding='utf-8-sig', errors='ignore')
                pattern = r'''["']([^"']*\.rvmat)["']'''
                matches = re.findall(pattern, rvmat_content, re.IGNORECASE)
                refs.update(matches)

                # Also extract texture refs from .rvmat
                pattern = r'''["']([^"']*\.paa)["']'''
                matches = re.findall(pattern, rvmat_content, re.IGNORECASE)
                refs.update(matches)
            except Exception as e:
                self.warnings.append({
                    'file': str(rvmat_file.relative_to(self.addon_root)),
                    'message': f'Could not read .rvmat file: {e}'
                })

        return refs

    def _resolve(self, ref: str) -> Path:
        """Resolve a prefixed root path such as MyMod\\data\\x.paa against the work drive root"""
        return self.work_root / ref.replace('\\', '/').lstrip('/')

    def _verify_files(self, ref_type: str, refs: Set[str]):
        """Check if referenced files exist"""
        for ref in sorted(refs):
            file_path = self._resolve(ref)

            if file_path.exists():
                self.valid_refs.append({
                    'type': ref_type,
                    'path': ref,
                    'status': 'found'
                })
            else:
                self.errors.append({
                    'type': ref_type,
                    'reference': ref,
                    'expected_path': str(file_path),
                    'message': f'{ref_type.upper()} file not found',
                    'severity': 'critical'
                })

    def _check_format_issues(self):
        """Check for format-related issues"""
        # Check for .png files (should be .paa)
        for png_file in self.addon_root.rglob('*.png'):
            self.warnings.append({
                'file': str(png_file.relative_to(self.addon_root)),
                'message': 'PNG file found (should be converted to PAA for DayZ)',
                'severity': 'high'
            })

        # Check for .dds files (should be .paa)
        for dds_file in self.addon_root.rglob('*.dds'):
            self.warnings.append({
                'file': str(dds_file.relative_to(self.addon_root)),
                'message': 'DDS file found (convert to PAA for DayZ compatibility)',
                'severity': 'high'
            })

        # Check for capitalization mismatches in the file name. List the folder and
        # compare names case-insensitively: a literal glob returns the pattern's own
        # spelling on Windows and finds nothing on a case-sensitive file system.
        if self.config_cpp.exists():
            content = self.config_cpp.read_text(encoding='utf-8-sig')
            refs = re.findall(r'''["']([^"']*(?:\.paa|\.rvmat))["']''', content, re.IGNORECASE)

            for ref in refs:
                file_path = self._resolve(ref)
                parent = file_path.parent
                if not parent.is_dir():
                    continue
                for actual in parent.iterdir():
                    if actual.name.lower() == file_path.name.lower() and actual.name != file_path.name:
                        self.warnings.append({
                            'reference': ref,
                            'message': f'Capitalization mismatch: referenced as "{ref}" but file is "{actual.name}"',
                            'severity': 'high'
                        })

    def report(self) -> Dict:
        """Generate validation report"""
        return {
            'addon_root': str(self.addon_root),
            'status': 'PASS' if not self.errors else 'FAIL',
            'errors': self.errors,
            'warnings': self.warnings,
            'summary': {
                'total_references': len(self.valid_refs) + len(self.errors),
                'valid_files': len(self.valid_refs),
                'missing_files': len(self.errors),
                'format_warnings': len([w for w in self.warnings if 'PNG' in w.get('message', '') or 'DDS' in w.get('message', '')])
            }
        }


def main():
    if len(sys.argv) < 2:
        print("Usage: python texture_path_checker.py <path/to/addon/root> [work_drive_root]")
        sys.exit(1)

    addon_root = sys.argv[1]
    work_root = sys.argv[2] if len(sys.argv) > 2 else 'P:\\'

    try:
        checker = TexturePathChecker(addon_root, work_root)
        report = checker.validate()
        print(json.dumps(report, indent=2))

        if len(report['errors']) > 0:
            sys.exit(1)
        elif len(report['warnings']) > 0:
            sys.exit(2)
        else:
            sys.exit(0)
    except Exception as e:
        print(json.dumps({
            'error': str(e),
            'addon_root': addon_root
        }, indent=2))
        sys.exit(1)


if __name__ == '__main__':
    main()
```

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
