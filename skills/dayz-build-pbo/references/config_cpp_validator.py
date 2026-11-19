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
        """Verify hiddenSelections count matches textures and materials, per class"""
        # Walk the file brace by brace so every class (with or without a base class)
        # owns the arrays written directly in its body.
        text = re.sub(r'//.*?$', '', self.content, flags=re.MULTILINE)
        token = re.compile(
            r'class\s+(\w+)\s*(?::\s*\w+\s*)?\{'        # class X {  or  class X: Base {
            r'|(\w+)\[\]\s*\+?=\s*\{([^{}]*)\}'          # name[] = { ... };
            r'|[{}]'
        )
        stack = []  # one (class name or None, {array name: entries}) per open brace
        for m in token.finditer(text):
            if m.group(1):
                stack.append((m.group(1), {}))
            elif m.group(2):
                if stack:
                    entries = [e.strip().strip('"\'') for e in m.group(3).split(',') if e.strip()]
                    stack[-1][1][m.group(2)] = entries
            elif m.group(0) == '{':
                stack.append((None, {}))
            elif stack:
                class_name, arrays = stack.pop()
                if class_name:
                    self._compare_hidden_selections(class_name, arrays)

    def _compare_hidden_selections(self, class_name: str, arrays: Dict):
        """Compare the hiddenSelections arrays of one class body.

        A length mismatch is a warning, not an error: the engine accepts a shorter
        array (vanilla Flashlight, P:\\DZ\\gear\\tools\\config.cpp:278-295, has
        4 selections and 1 material).
        """
        selections = arrays.get('hiddenSelections')
        if not selections:
            return
        sel_count = len(selections)
        tex_count = len(arrays.get('hiddenSelectionsTextures', []))
        mat_count = len(arrays.get('hiddenSelectionsMaterials', []))
        if tex_count > 0 and sel_count != tex_count:
            self.warnings.append({
                'check': 'hidden_selections',
                'class': class_name,
                'message': f'Mismatch: {sel_count} selections but {tex_count} textures',
                'selections': selections[:3]  # Show first 3
            })

        if mat_count > 0 and sel_count != mat_count:
            self.warnings.append({
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
