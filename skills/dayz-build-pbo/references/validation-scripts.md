# DayZ PBO Validation Scripts Reference

Four reference validators as code blocks (config.cpp, texture paths, stringtable, `.p3d` LODs), with their JSON
output, exit codes and CI use. They are shapes to adapt, not bundled scripts.

Not yet checked on `P:\`: this is reference code, not a statement about vanilla data.

| Validator | Status | Use in this repo |
|---|---|---|
| `config_cpp_validator.py` | Regex heuristics: brace count, semicolons, `CfgPatches`, `hiddenSelections`, duplicates | `/dayz-lint` parses `config.cpp` and is the gate `/dayz-build-pbo` runs. |
| `texture_path_checker.py` | Resolves every quoted `.paa`/`.rvmat` against the addon root only, so a vanilla `dz\...` path is reported missing | `/dayz-lint` (missing files) and `/dayz-p3d-audit`. |
| `stringtable_validator.py` | **Broken for DayZ**: parses `stringtable.xml` (section 3) | None yet; port it to CSV before use. |
| `p3d_lod_checker.py` | Does not run as written: it imports `P3D` and calls `P3d.read(path)`, py3d's `P3D` takes an open file (`P3D(f)`), and nothing ever sets the resolution LOD flag | `/dayz-p3d-audit`. |

Each script outputs JSON and returns exit code 0 (PASS), 1 (FAIL) or 2 (WARN).

**Prerequisites:**
- Python 3.7+
- py3d (optional, for .p3d validation): this repo's DayZ py3d, 1.6.0 or later, via `pip install -e scripts/tools/py3d` (never `pip install py3d`: on PyPI that name is an unrelated point-cloud library)
- Standard library only for other validators

---

## 1. config_cpp_validator.py

Parses config.cpp files and validates syntax, structure, and class hierarchy.

**Usage:**
```bash
python config_cpp_validator.py path/to/config.cpp
```

**Output:** JSON with errors, warnings, and parsed structure.

```python
#!/usr/bin/env python3
"""
DayZ config.cpp validator
Checks: brace balance, semicolons, CfgPatches, hiddenSelections matching
"""
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional

class ConfigCppValidator:
    def __init__(self, filepath: str):
        self.filepath = Path(filepath)
        if not self.filepath.exists():
            raise FileNotFoundError(f"{filepath} not found")
        self.content = self.filepath.read_text(encoding='utf-8-sig')
        self.lines = self.content.split('\n')

        self.errors: List[Dict] = []
        self.warnings: List[Dict] = []
        self.info: Dict = {
            'file': str(self.filepath),
            'size': len(self.content),
            'line_count': len(self.lines)
        }

    def validate(self) -> Dict:
        """Run all validation checks"""
        self._check_braces()
        self._check_semicolons()
        self._check_cfg_patches()
        self._check_hidden_selections()
        self._check_duplicates()
        self._check_inheritance()

        return self.report()

    def _check_braces(self):
        """Verify balanced braces"""
        open_count = self.content.count('{')
        close_count = self.content.count('}')

        if open_count != close_count:
            self.errors.append({
                'check': 'brace_balance',
                'message': f'Unbalanced braces: {open_count} open, {close_count} close',
                'severity': 'critical'
            })

        # Find unclosed braces line-by-line
        depth = 0
        for idx, line in enumerate(self.lines, 1):
            depth += line.count('{') - line.count('}')
            if depth < 0:
                self.errors.append({
                    'check': 'brace_balance',
                    'line': idx,
                    'message': 'Extra closing brace',
                    'content': line.strip()
                })

    def _check_semicolons(self):
        """Check for missing semicolons after properties"""
        # Remove comments and strings
        content_no_comment = re.sub(r'//.*?$', '', self.content, flags=re.MULTILINE)

        # Pattern: property = value without ;
        # Look for lines that assign but don't end with ; or {
        for idx, line in enumerate(self.lines, 1):
            # Skip comment lines and empty
            if line.strip().startswith('//') or not line.strip():
                continue

            # Check for assignments without semicolon
            if '=' in line and not line.rstrip().endswith((';', '{', '}')):
                # But allow { on same line
                if '{' not in line:
                    self.warnings.append({
                        'check': 'semicolon',
                        'line': idx,
                        'message': 'Possible missing semicolon after property',
                        'content': line.strip()
                    })

    def _check_cfg_patches(self):
        """Verify CfgPatches section exists and is valid"""
        if 'CfgPatches' not in self.content:
            self.errors.append({
                'check': 'cfg_patches',
                'message': 'CfgPatches class not found (required)',
                'severity': 'critical'
            })
            return

        # Find CfgPatches section
        pattern = r'class\s+CfgPatches\s*\{(.+?)\n\s*\};'
        match = re.search(pattern, self.content, re.DOTALL)
        if not match:
            self.errors.append({
                'check': 'cfg_patches',
                'message': 'CfgPatches found but malformed (unclosed brace)',
                'severity': 'critical'
            })
            return

        patches_content = match.group(1)

        # Look for patch subclasses
        patches = re.findall(r'class\s+(\w+)\s*\{', patches_content)
        if not patches:
            self.errors.append({
                'check': 'cfg_patches',
                'message': 'No patch classes defined in CfgPatches',
                'severity': 'critical'
            })
            return

        # Check each patch for required properties
        required_props = ['units', 'weapons', 'requiredVersion', 'requiredAddons']
        for patch in patches:
            for prop in required_props:
                if prop not in patches_content:
                    self.warnings.append({
                        'check': 'cfg_patches',
                        'patch': patch,
                        'message': f'Missing property: {prop}[]',
                        'severity': 'high'
                    })

        self.info['patches'] = patches
        self.info['patch_count'] = len(patches)

    def _check_hidden_selections(self):
        """Verify hiddenSelections count matches textures and materials"""
        # Find all class definitions with hiddenSelections
        class_pattern = r'class\s+(\w+)\s*\{([^}]*?hiddenSelections[^}]*?)\}'

        for match in re.finditer(class_pattern, self.content, re.DOTALL):
            class_name = match.group(1)
            class_body = match.group(2)

            # Count selections
            sel_match = re.search(r'hiddenSelections\[\]\s*=\s*\{([^}]*?)\}', class_body)
            if not sel_match:
                continue

            selections = [s.strip().strip('"\'') for s in sel_match.group(1).split(',') if s.strip()]
            sel_count = len(selections)

            # Count textures
            tex_match = re.search(r'hiddenSelectionsTextures\[\]\s*=\s*\{([^}]*?)\}', class_body)
            tex_count = len(tex_match.group(1).split(',')) if tex_match else 0

            # Count materials
            mat_match = re.search(r'hiddenSelectionsMaterials\[\]\s*=\s*\{([^}]*?)\}', class_body)
            mat_count = len(mat_match.group(1).split(',')) if mat_match else 0

            # Check matching
            if sel_count > 0 and tex_count > 0 and sel_count != tex_count:
                self.errors.append({
                    'check': 'hidden_selections',
                    'class': class_name,
                    'message': f'Mismatch: {sel_count} selections but {tex_count} textures',
                    'selections': selections[:3]  # Show first 3
                })

            if sel_count > 0 and mat_count > 0 and sel_count != mat_count:
                self.errors.append({
                    'check': 'hidden_selections',
                    'class': class_name,
                    'message': f'Mismatch: {sel_count} selections but {mat_count} materials'
                })

    def _check_duplicates(self):
        """Check for duplicate class definitions"""
        class_pattern = r'class\s+(\w+)\s*(?:\s*:\s*\w+)?\s*\{'
        classes = re.findall(class_pattern, self.content)

        seen = {}
        for idx, cls in enumerate(classes):
            if cls in seen:
                self.warnings.append({
                    'check': 'duplicates',
                    'class': cls,
                    'message': f'Class "{cls}" defined multiple times',
                    'first_occurrence': seen[cls],
                    'current_occurrence': idx
                })
            else:
                seen[cls] = idx

    def _check_inheritance(self):
        """Verify parent classes are likely to exist"""
        # Extract inheritance declarations
        inherit_pattern = r'class\s+\w+\s*:\s*(\w+)\s*\{'
        parents = re.findall(inherit_pattern, self.content)

        # Known DayZ base classes (partial list)
        # verify against P:\dz vanilla configs before extending
        known_bases = {
            'ItemBase', 'Inventory_Base', 'Container_Base', 'Clothing_Base',
            'House', 'Land_', 'Weapon_Base', 'Rifle_Base',
            'Pistol_Base', 'Magazine_Base', 'ItemOptics_Base', 'CarScript'
        }

        for parent in set(parents):
            # Check if parent matches known base or starts with known prefix
            is_known = any(parent == kb or parent.startswith(kb) for kb in known_bases)
            if not is_known and parent != 'ClassName':
                self.warnings.append({
                    'check': 'inheritance',
                    'parent_class': parent,
                    'message': f'Parent class "{parent}" not recognized (may not exist)',
                    'severity': 'medium'
                })

    def report(self) -> Dict:
        """Generate validation report"""
        return {
            'file': str(self.filepath.name),
            'status': 'PASS' if not self.errors else 'FAIL',
            'errors': self.errors,
            'warnings': self.warnings,
            'info': self.info,
            'summary': {
                'error_count': len(self.errors),
                'warning_count': len(self.warnings),
                'total_issues': len(self.errors) + len(self.warnings)
            }
        }


def main():
    if len(sys.argv) < 2:
        print("Usage: python config_cpp_validator.py <path/to/config.cpp>")
        sys.exit(1)

    filepath = sys.argv[1]

    try:
        validator = ConfigCppValidator(filepath)
        report = validator.validate()
        print(json.dumps(report, indent=2))

        # Exit with appropriate code
        if report['summary']['error_count'] > 0:
            sys.exit(1)
        elif report['summary']['warning_count'] > 0:
            sys.exit(2)
        else:
            sys.exit(0)
    except Exception as e:
        print(json.dumps({
            'error': str(e),
            'file': filepath
        }, indent=2))
        sys.exit(1)


if __name__ == '__main__':
    main()
```

---

## 2. texture_path_checker.py

Verifies all texture and material references exist relative to addon root.

**Usage:**
```bash
python texture_path_checker.py path/to/addon/root
```

**Output:** JSON with missing files, format warnings, and path validation.

```python
#!/usr/bin/env python3
"""
DayZ texture and material path validator
Checks: .paa, .rvmat file existence, path capitalization, format compatibility
"""
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Optional

class TexturePathChecker:
    def __init__(self, addon_root: str):
        self.addon_root = Path(addon_root)
        if not self.addon_root.exists():
            raise FileNotFoundError(f"{addon_root} not found")

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

    def _verify_files(self, ref_type: str, refs: Set[str]):
        """Check if referenced files exist"""
        for ref in sorted(refs):
            # Normalize path (convert forward slashes to backslashes on Windows, etc.)
            file_path = self.addon_root / ref.replace('\\', '/')

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
                    'expected_path': str(file_path.relative_to(self.addon_root)),
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

        # Check for capitalization mismatches
        if self.config_cpp.exists():
            content = self.config_cpp.read_text(encoding='utf-8-sig')
            refs = re.findall(r'''["']([^"']*(?:\.paa|\.rvmat))["']''', content, re.IGNORECASE)

            for ref in refs:
                file_path = self.addon_root / ref.replace('\\', '/')

                # Check if file exists with different capitalization
                try:
                    parent = file_path.parent
                    if parent.exists():
                        actual_files = list(parent.glob(file_path.name))
                        if actual_files and actual_files[0].name != file_path.name:
                            self.warnings.append({
                                'reference': ref,
                                'message': f'Capitalization mismatch: referenced as "{ref}" but file is "{actual_files[0].name}"',
                                'severity': 'high'
                            })
                except:
                    pass

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
        print("Usage: python texture_path_checker.py <path/to/addon/root>")
        sys.exit(1)

    addon_root = sys.argv[1]

    try:
        checker = TexturePathChecker(addon_root)
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

---

## 3. stringtable_validator.py

> **BROKEN FOR DAYZ — do not run as-is.** The script below parses
> `stringtable.xml`, which is the Arma 3 form. DayZ uses `stringtable.csv`: measured on a DayZ
> mod project tree there are **zero** XML stringtables and 38 CSV ones, and the two deployed PBOs
> checked carry `stringtable.csv` and no XML. Run against a
> DayZ addon it reports "stringtable not found" for every mod that has a perfectly good one.
> It is kept here as the shape to port, not as a tool: the rewrite reads the CSV, takes
> column 1 minus the leading `#` as the key set, and checks `.layout` files for `#STR_`
> alongside `.c` and `config.cpp`. Not rewritten yet because it has not been run against a
> real addon, and shipping an untested validator is the same mistake twice.

Validates stringtable completeness and checks all #STR_ references are covered.

**Usage:**
```bash
python stringtable_validator.py path/to/addon/root
```

**Output:** JSON with missing keys, orphaned entries, and language coverage.

```python
#!/usr/bin/env python3
"""
DayZ stringtable.xml validator
Checks: #STR_ key coverage, orphaned entries, language completeness, XML syntax
"""
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Set

class StringtableValidator:
    def __init__(self, addon_root: str):
        self.addon_root = Path(addon_root)
        if not self.addon_root.exists():
            raise FileNotFoundError(f"{addon_root} not found")

        self.stringtable = self.addon_root / 'stringtable.xml'
        self.errors: List[Dict] = []
        self.warnings: List[Dict] = []

    def validate(self) -> Dict:
        """Run validation"""
        # Extract all #STR_ references from code
        code_refs = self._extract_code_references()

        if not code_refs:
            return {
                'addon_root': str(self.addon_root),
                'status': 'PASS',
                'message': 'No #STR_ references found in code',
                'errors': [],
                'warnings': [],
                'summary': {'total_references': 0}
            }

        # Check stringtable existence
        if not self.stringtable.exists():
            self.errors.append({
                'check': 'stringtable_exists',
                'message': f'stringtable.xml not found, but {len(code_refs)} #STR_ references found',
                'references_found': list(sorted(code_refs))[:5]  # Show first 5
            })
            return self.report(code_refs, set())

        # Parse stringtable
        stringtable_keys = self._parse_stringtable()
        if stringtable_keys is None:
            return self.report(code_refs, set())

        # Check for missing keys
        missing = code_refs - stringtable_keys
        for key in sorted(missing):
            self.errors.append({
                'check': 'missing_key',
                'key': key,
                'message': f'Key "{key}" referenced in code but not in stringtable.xml'
            })

        # Check for orphaned keys (defined but not used)
        orphaned = stringtable_keys - code_refs
        for key in sorted(orphaned):
            self.warnings.append({
                'check': 'orphaned_key',
                'key': key,
                'message': f'Key "{key}" defined in stringtable but never referenced'
            })

        return self.report(code_refs, stringtable_keys)

    def _extract_code_references(self) -> Set[str]:
        """Extract all #STR_ references from .c, .cpp, and config.cpp"""
        refs = set()
        pattern = r'#STR_([A-Za-z0-9_]+)'

        # Search all script files
        for ext in ['*.c', '*.cpp']:
            for file in self.addon_root.rglob(ext):
                try:
                    content = file.read_text(encoding='utf-8-sig', errors='ignore')
                    matches = re.findall(pattern, content)
                    refs.update([f'STR_{m}' for m in matches])
                except:
                    pass

        return refs

    def _parse_stringtable(self) -> Set[str]:
        """Parse stringtable.xml and extract keys"""
        try:
            tree = ET.parse(str(self.stringtable))
            root = tree.getroot()

            keys = set()
            for key_elem in root.findall('.//Key'):
                key_id = key_elem.get('ID')
                if key_id:
                    keys.add(key_id)

            return keys
        except ET.ParseError as e:
            self.errors.append({
                'check': 'xml_syntax',
                'message': f'stringtable.xml parse error: {e}',
                'severity': 'critical'
            })
            return None
        except Exception as e:
            self.errors.append({
                'check': 'xml_read',
                'message': f'Error reading stringtable.xml: {e}'
            })
            return None

    def report(self, code_refs: Set[str], stringtable_keys: Set[str]) -> Dict:
        """Generate validation report"""
        return {
            'addon_root': str(self.addon_root),
            'status': 'PASS' if not self.errors else 'FAIL',
            'errors': self.errors,
            'warnings': self.warnings,
            'summary': {
                'total_references': len(code_refs),
                'stringtable_keys': len(stringtable_keys),
                'missing_keys': len([e for e in self.errors if e.get('check') == 'missing_key']),
                'orphaned_keys': len([w for w in self.warnings if w.get('check') == 'orphaned_key'])
            }
        }


def main():
    if len(sys.argv) < 2:
        print("Usage: python stringtable_validator.py <path/to/addon/root>")
        sys.exit(1)

    addon_root = sys.argv[1]

    try:
        validator = StringtableValidator(addon_root)
        report = validator.validate()
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

---

## 4. p3d_lod_checker.py

Validates .p3d LOD structure using py3d (optional). Requires py3d library.

**Usage:**
```bash
python p3d_lod_checker.py path/to/addon/root
pip install -e scripts/tools/py3d  # this repo's DayZ py3d, 1.6.0 or later (if not installed)
```

**Output:** JSON with LOD types, vertex counts, named selections, memory points.

```python
#!/usr/bin/env python3
"""
DayZ .p3d LOD structure validator
Checks: LOD types (Resolution, Geometry, Memory), vertex budgets, named selections,
memory points, geometry mass
Requires: the repo's DayZ py3d >= 1.6.0 (`pip install -e scripts/tools/py3d`; never pip install py3d from PyPI)
"""
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Try to import py3d, provide helpful error if missing
try:
    from py3d import P3D
    HAS_PY3D = True
except ImportError:
    HAS_PY3D = False


class P3dLodChecker:
    def __init__(self, addon_root: str):
        self.addon_root = Path(addon_root)
        if not self.addon_root.exists():
            raise FileNotFoundError(f"{addon_root} not found")

        if not HAS_PY3D:
            raise ImportError("DayZ py3d not installed. Install it with: pip install -e scripts/tools/py3d")

        self.errors: List[Dict] = []
        self.warnings: List[Dict] = []
        self.models_checked = 0

    def validate(self) -> Dict:
        """Find and validate all .p3d files"""
        p3d_files = list(self.addon_root.rglob('*.p3d'))

        if not p3d_files:
            return {
                'addon_root': str(self.addon_root),
                'status': 'PASS',
                'message': 'No .p3d files found',
                'models_checked': 0,
                'errors': [],
                'warnings': []
            }

        results = {}
        for p3d_file in sorted(p3d_files):
            rel_path = p3d_file.relative_to(self.addon_root)
            results[str(rel_path)] = self._check_model(p3d_file)
            self.models_checked += 1

        return self.report(results)

    def _check_model(self, p3d_file: Path) -> Dict:
        """Validate single .p3d file"""
        try:
            model = P3d.read(str(p3d_file))
        except Exception as e:
            self.errors.append({
                'file': str(p3d_file.relative_to(self.addon_root)),
                'message': f'Could not read .p3d: {e}'
            })
            return {'status': 'ERROR', 'message': str(e)}

        lod_info = {'status': 'PASS', 'lods': {}}
        lods_present = {'resolution': False, 'geometry': False, 'memory': False}
        all_named_sels = None
        all_memory_points = set()

        # Check each LOD
        for lod_idx, lod in enumerate(model.lods):
            lod_data = {
                'type': lod.type,
                'index': lod_idx,
                'resolution': getattr(lod, 'resolution', None),
                'vertex_count': len(lod.vertices) if hasattr(lod, 'vertices') else 0
            }

            # Track LOD types by numeric resolution (lod.resolution is a float, not a string —
            # DayZ canonical ids: geometry 1e13, memory 1e15, view 6e15, fire 7e15)
            res = lod_data['resolution']
            if res is not None:
                if abs(res - 1.0e13) < 1e11:
                    lods_present['geometry'] = True
                elif abs(res - 1.0e15) < 5e13:
                    lods_present['memory'] = True
                elif abs(res - 6.0e15) < 5e13:
                    lods_present['view_geometry'] = True
                elif abs(res - 7.0e15) < 5e13:
                    lods_present['fire_geometry'] = True

            # Named selections
            if hasattr(lod, 'named_selections'):
                lod_data['named_selections'] = list(lod.named_selections.keys())
                if all_named_sels is None:
                    all_named_sels = set(lod.named_selections.keys())
                else:
                    # Track consistency
                    if set(lod.named_selections.keys()) != all_named_sels:
                        self.warnings.append({
                            'file': str(p3d_file.relative_to(self.addon_root)),
                            'lod': lod_idx,
                            'message': 'Named selections differ from LOD 0',
                            'lod_selections': list(lod.named_selections.keys())[:3]
                        })

            # Memory points
            if hasattr(lod, 'memory_points'):
                lod_data['memory_points'] = list(lod.memory_points.keys())
                all_memory_points.update(lod.memory_points.keys())

            # Vertex budget warnings
            if lod_idx == 0 and lod_data['vertex_count'] > 3000:
                self.warnings.append({
                    'file': str(p3d_file.relative_to(self.addon_root)),
                    'lod': 0,
                    'message': f'LOD0 has {lod_data["vertex_count"]} vertices (high for small items)',
                    'severity': 'medium'
                })

            # Geometry LOD checks
            if 'geometry' in str(lod.type).lower():
                if hasattr(lod, 'components'):
                    components = lod.components
                    for comp_idx, comp in enumerate(components):
                        if hasattr(comp, 'mass') and comp.mass <= 0:
                            self.warnings.append({
                                'file': str(p3d_file.relative_to(self.addon_root)),
                                'lod': lod_idx,
                                'component': comp_idx,
                                'message': f'Geometry component has zero/negative mass',
                                'mass': getattr(comp, 'mass', 'N/A')
                            })

            # Memory LOD checks
            if 'memory' in str(lod.type).lower():
                if not all_memory_points or 'ce_center' not in all_memory_points:
                    self.errors.append({
                        'file': str(p3d_file.relative_to(self.addon_root)),
                        'lod': lod_idx,
                        'message': 'Memory LOD missing ce_center point (the centre used for actions and the vicinity list)',
                        'severity': 'critical'
                    })

                if not all_memory_points or not any(p.startswith('ce_') for p in all_memory_points):
                    self.warnings.append({
                        'file': str(p3d_file.relative_to(self.addon_root)),
                        'lod': lod_idx,
                        'message': 'No collision points (ce_*) found in Memory LOD',
                        'severity': 'high'
                    })

            lod_info['lods'][f'lod_{lod_idx}'] = lod_data

        # Check LOD requirements
        if not lods_present['resolution']:
            self.errors.append({
                'file': str(p3d_file.relative_to(self.addon_root)),
                'message': 'Missing Resolution LOD (required)',
                'severity': 'critical'
            })
            lod_info['status'] = 'FAIL'

        if not lods_present['geometry']:
            self.warnings.append({
                'file': str(p3d_file.relative_to(self.addon_root)),
                'message': 'Missing Geometry LOD (recommended)',
                'severity': 'high'
            })

        if not lods_present['memory']:
            self.errors.append({
                'file': str(p3d_file.relative_to(self.addon_root)),
                'message': 'Missing Memory LOD (required)',
                'severity': 'critical'
            })
            lod_info['status'] = 'FAIL'

        lod_info['lod_types'] = lods_present
        return lod_info

    def report(self, results: Dict) -> Dict:
        """Generate validation report"""
        model_status = {k: v.get('status', 'UNKNOWN') for k, v in results.items() if isinstance(v, dict)}
        fail_count = sum(1 for s in model_status.values() if s == 'FAIL')

        return {
            'addon_root': str(self.addon_root),
            'status': 'FAIL' if fail_count > 0 or self.errors else ('WARN' if self.warnings else 'PASS'),
            'models_checked': self.models_checked,
            'models': results,
            'errors': self.errors,
            'warnings': self.warnings,
            'summary': {
                'total_errors': len(self.errors),
                'total_warnings': len(self.warnings),
                'models_with_errors': fail_count
            }
        }


def main():
    if len(sys.argv) < 2:
        print("Usage: python p3d_lod_checker.py <path/to/addon/root>")
        print()
        print("Note: Requires the repo's DayZ py3d (>= 1.6.0). Install with:")
        print("  pip install -e scripts/tools/py3d")
        sys.exit(1)

    addon_root = sys.argv[1]

    try:
        checker = P3dLodChecker(addon_root)
        report = checker.validate()
        print(json.dumps(report, indent=2))

        if len(report['errors']) > 0:
            sys.exit(1)
        elif len(report['warnings']) > 0:
            sys.exit(2)
        else:
            sys.exit(0)
    except ImportError as e:
        print(json.dumps({
            'error': str(e),
            'hint': 'Install the DayZ py3d with pip install -e scripts/tools/py3d (never pip install py3d from PyPI)'
        }, indent=2))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({
            'error': str(e),
            'addon_root': addon_root
        }, indent=2))
        sys.exit(1)


if __name__ == '__main__':
    main()
```

---

## Integration Example: Combined Validator Script

**run_all_validations.py** – Runs all four validators and produces a unified report:

```bash
python run_all_validations.py /path/to/addon
```

Example implementation:

```python
#!/usr/bin/env python3
"""
Run all validators and produce unified report
"""
import subprocess
import json
import sys
from pathlib import Path

def run_validator(script: str, addon_root: str) -> dict:
    """Run a validator script and return JSON result"""
    try:
        result = subprocess.run(
            [sys.executable, script, addon_root],
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

    validators = [
        'config_cpp_validator.py',
        'texture_path_checker.py',
        'stringtable_validator.py',
        'p3d_lod_checker.py'
    ]

    results = {}
    total_errors = 0
    total_warnings = 0

    for validator in validators:
        name = validator.replace('_', ' ').replace('.py', '').title()
        results[name] = run_validator(validator, addon_root)

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

---

## Output Examples

### config_cpp_validator.py output:
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

### texture_path_checker.py output:
```json
{
  "addon_root": "/path/to/addon",
  "status": "FAIL",
  "errors": [
    {
      "type": "texture",
      "reference": "data/textures/body_co.paa",
      "expected_path": "data/textures/body_co.paa",
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

---

## Exit codes

The validators use only the Python standard library (py3d is optional).

All scripts return:
- Exit code 0: PASS (no errors)
- Exit code 1: FAIL (errors found)
- Exit code 2: WARN (warnings only)

This allows easy CI/CD integration with conditional build steps.

---

## Integration with CI/CD

For automated builds, run validation before packing. Note: the validators are
reference code blocks in this file — adapt them to your
pipeline; there is no bundled `validate.py`.

**Example build script (after extracting a validator from the reference):**
```batch
@echo off
echo Validating addon...
python config_cpp_validator.py "P:\MyMod\config.cpp"
if %ERRORLEVEL% NEQ 0 (
    echo Validation failed, skipping pack
    exit /b 1
)
echo Validation passed, packing...
AddonBuilder.exe P:\MyMod P:\Mods\@MyMod\Addons -prefix=MyMod -temp=P:\temp\MyMod -include=include.lst -clear
```

`include.lst` is the include list beside this skill's `build.py`; without `-include`, the binarizing pass drops
`.c` and `.csv` files (`post-build-gates.md`).

The reference validators return exit code 0 on PASS, 1 on FAIL, 2 on WARN.

---

## Reference Scripts

The standalone validators above can be integrated into build pipelines.

Quick uses:

```bash
python config_cpp_validator.py config.cpp | jq '.summary'
python run_all_validations.py . && echo "Ready for AddonBuilder"
```

GitHub Actions step:

```yaml
- name: Validate DayZ addon
  run: |
    python config_cpp_validator.py config.cpp || exit 1
    python texture_path_checker.py . || exit 1
    echo "Validation passed, ready for build"
```

- `config_cpp_validator.py` – Parse and check config.cpp syntax
- `texture_path_checker.py` – Verify texture existence
- `stringtable_validator.py` – Check string key coverage. **Broken for DayZ**: it
  parses `stringtable.xml`. Do not run as-is; see section 3.
- `p3d_lod_checker.py` – Validate .p3d LOD structure

Each outputs machine-readable JSON for CI/CD integration.
