# /dayz-init Onboarding Wizard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `/dayz-init` skill: a single-command onboarding wizard that, on first run, asks for intent and provisions a DayZ mod end-to-end, and on every run after, opens a mission-control hub for the cached project.

**Architecture:** New skill at `.claude/skills/dayz-init/`, structured as one entry-point Python file (`init.py`) plus focused helper modules: prompts, detection, env check, intent, plan, state, hub. Each module has a single responsibility. The skill orchestrates existing slash skills via `subprocess` rather than re-implementing them. Recovery is **state-based** (read disk markers and a small `.agentic-z/state.json`) rather than plan-based.

**Tech Stack:** Python 3.8+, stdlib only (`argparse`, `subprocess`, `json`, `pathlib`). Tests use `unittest` matching the existing `agentic-z-update/test_update.py` pattern.

**Spec:** [`docs/superpowers/specs/2026-05-06-dayz-init-onboarding-design.md`](../specs/2026-05-06-dayz-init-onboarding-design.md)

---

## File structure

| File | Responsibility |
|---|---|
| `.claude/skills/dayz-init/SKILL.md` | Frontmatter (`name`, `description`) + "How to run" docs. |
| `.claude/skills/dayz-init/init.py` | Entry point. Parses args, decides wizard-vs-hub, orchestrates. |
| `.claude/skills/dayz-init/prompts.py` | Input utilities: `ask_text`, `ask_yes_no`, `ask_select`. |
| `.claude/skills/dayz-init/detect.py` | Detection helpers: `cwd()`, `mod_name_from_cwd()`, `mod_name_from_config_cpp()`, `is_mod_dir()`. |
| `.claude/skills/dayz-init/env_check.py` | Detect prereqs (`P:\`, DayZ Tools, vanilla data, Python, junctions). Returns categorized results: ok / autofixable / hard-stop. |
| `.claude/skills/dayz-init/intent.py` | Run the intent prompt phase, return an `Intent` dataclass. |
| `.claude/skills/dayz-init/plan.py` | Build a `Plan` from `Intent` + env state, render it, execute it (calls subprocess for each step). |
| `.claude/skills/dayz-init/state.py` | Read/write `<project>/.agentic-z/state.json`. Detect "setup complete" from disk markers. |
| `.claude/skills/dayz-init/hub.py` | Hub status block + flat menu + action dispatch. |
| `.claude/skills/dayz-init/test_prompts.py` | Tests for `prompts.py`. |
| `.claude/skills/dayz-init/test_detect.py` | Tests for `detect.py`. |
| `.claude/skills/dayz-init/test_env_check.py` | Tests for `env_check.py`. |
| `.claude/skills/dayz-init/test_state.py` | Tests for `state.py`. |
| `.claude/skills/dayz-init/test_plan.py` | Tests for `plan.py` rendering. |
| `.claude/skills/dayz-build-pbo/build.py` | **Modify**: when no project cached, error pointing at `/dayz-init`. |
| `.claude/skills/dayz-launch-test/launch.py` | **Modify**: when no project cached or no server staged, error pointing at `/dayz-init`. |
| `.claude/skills/dayz-add-server/add_server.py` | **Modify**: when no project cached, error pointing at `/dayz-init`. |
| `README.md` | **Modify**: rewrite quickstart to lead with `/dayz-init`. |
| `.claude-plugin/plugin.json` (or marketplace.json) | **Modify**: description mentions `/dayz-init` as entry. |

---

## Task 1: Skill scaffolding

**Files:**
- Create: `.claude/skills/dayz-init/SKILL.md`
- Create: `.claude/skills/dayz-init/init.py`

- [ ] **Step 1: Create SKILL.md**

```markdown
---
name: dayz-init
description: Front door for all DayZ work in Agentic-Z. First run is a setup wizard (env check, intent prompts, plan, execute). Every run after drops you into a mission-control hub for the cached project. Wraps the existing /dayz-* skills, never replaces them.
---

# /dayz-init

Single command for everything onboarding-related. First run scaffolds (or imports) a mod, junctions `P:\<Mod>\`, caches the project root, optionally stages a test server, optionally builds a PBO, optionally launches the diag client. Every run after that drops into a hub showing project state with a flat action menu.

Follow `.claude/skills/_shared/dayz-conventions.md`.

## How to run

```cmd
python .claude\skills\dayz-init\init.py
```

No arguments. The wizard asks for everything it needs.

## What it does (first run)

1. Environment phase: detects `P:\` mount, DayZ Tools, vanilla data, Python, `P:\Mods\` junction. Auto-fixes what it can. Hard-stops with steam:// links for what it cannot.
2. Intent phase: prompts new vs import, mod name (default = cwd basename or CfgPatches class), project path (default = cwd), opt-in for server stage / PBO build / diag launch, RAG setup if no Voyage key.
3. Plan phase: prints every action it is about to take, asks one Y/N to continue.
4. Execute phase: runs each step, streams output, halts on first failure with a state-preserving exit.
5. Drops into the hub.

## What it does (subsequent runs)

Detects existing setup from disk markers and the state file. Drops directly into the hub: project status block plus a flat 10-action menu (build & launch, stop diag, tail log, open in workbench, etc.).

## State file

`<project>/.agentic-z/state.json`. Tracks RAG decision, last build status, intent choices that disk inspection cannot derive. Setup completion is derived from disk, not the state file.
```

- [ ] **Step 2: Create init.py stub**

```python
"""Entry point for /dayz-init.

First run: setup wizard. Every run after: mission-control hub.
"""
from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    """Stub. Real orchestration arrives in later tasks."""
    print("dayz-init: not yet implemented")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

- [ ] **Step 3: Verify it runs**

Run: `python .claude/skills/dayz-init/init.py`
Expected output: `dayz-init: not yet implemented`
Exit code: 0

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/dayz-init/
git commit -m "feat(dayz-init): scaffold skill (SKILL.md + init.py stub)"
```

---

## Task 2: prompts.py with three input primitives

**Files:**
- Create: `.claude/skills/dayz-init/prompts.py`
- Create: `.claude/skills/dayz-init/test_prompts.py`

- [ ] **Step 1: Write the failing tests**

Create `.claude/skills/dayz-init/test_prompts.py`:

```python
"""Tests for prompts.py."""
import io
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prompts import ask_text, ask_yes_no, ask_select  # noqa: E402


class TestAskText(unittest.TestCase):
    def test_returns_user_input(self):
        with patch("builtins.input", return_value="MyMod"):
            self.assertEqual(ask_text("Mod name?"), "MyMod")

    def test_returns_default_on_empty(self):
        with patch("builtins.input", return_value=""):
            self.assertEqual(ask_text("Mod name?", default="Foo"), "Foo")

    def test_returns_input_when_default_provided(self):
        with patch("builtins.input", return_value="Bar"):
            self.assertEqual(ask_text("Mod name?", default="Foo"), "Bar")


class TestAskYesNo(unittest.TestCase):
    def test_y_is_yes(self):
        with patch("builtins.input", return_value="y"):
            self.assertTrue(ask_yes_no("ok?", default=False))

    def test_n_is_no(self):
        with patch("builtins.input", return_value="n"):
            self.assertFalse(ask_yes_no("ok?", default=True))

    def test_empty_uses_default_true(self):
        with patch("builtins.input", return_value=""):
            self.assertTrue(ask_yes_no("ok?", default=True))

    def test_empty_uses_default_false(self):
        with patch("builtins.input", return_value=""):
            self.assertFalse(ask_yes_no("ok?", default=False))


class TestAskSelect(unittest.TestCase):
    def test_picks_by_number(self):
        with patch("builtins.input", return_value="2"):
            self.assertEqual(
                ask_select("pick", ["alpha", "beta", "gamma"]), "beta"
            )

    def test_default_on_empty(self):
        with patch("builtins.input", return_value=""):
            self.assertEqual(
                ask_select("pick", ["alpha", "beta"], default="beta"), "beta"
            )

    def test_rejects_out_of_range_then_accepts_valid(self):
        with patch("builtins.input", side_effect=["9", "1"]):
            self.assertEqual(
                ask_select("pick", ["alpha", "beta"]), "alpha"
            )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests, expect ImportError**

Run: `python .claude/skills/dayz-init/test_prompts.py`
Expected: `ImportError: cannot import name 'ask_text' from 'prompts'`

- [ ] **Step 3: Implement prompts.py**

Create `.claude/skills/dayz-init/prompts.py`:

```python
"""Input prompt utilities for /dayz-init.

Three primitives the wizard uses: free-text, yes/no, select-from-list.
All print to stdout, read via builtins.input, and respect a default value.
"""
from __future__ import annotations

from typing import Sequence


def ask_text(question: str, default: str | None = None) -> str:
    """Prompt for free-text input. Empty input returns default if provided."""
    suffix = f" [{default}]" if default else ""
    while True:
        answer = input(f"{question}{suffix} ").strip()
        if answer:
            return answer
        if default is not None:
            return default
        print("(value required)")


def ask_yes_no(question: str, default: bool = True) -> bool:
    """Prompt for yes/no. Default shown via [Y/n] or [y/N]."""
    hint = "[Y/n]" if default else "[y/N]"
    while True:
        answer = input(f"{question} {hint} ").strip().lower()
        if not answer:
            return default
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("(answer y or n)")


def ask_select(
    question: str,
    options: Sequence[str],
    default: str | None = None,
) -> str:
    """Prompt for one-of-many. User types the 1-indexed number or accepts default."""
    if not options:
        raise ValueError("ask_select requires at least one option")
    print(question)
    for i, option in enumerate(options, start=1):
        marker = " (default)" if option == default else ""
        print(f"  {i}. {option}{marker}")
    while True:
        answer = input("> ").strip()
        if not answer and default is not None:
            return default
        if answer.isdigit():
            idx = int(answer)
            if 1 <= idx <= len(options):
                return options[idx - 1]
        print(f"(enter 1-{len(options)})")
```

- [ ] **Step 4: Run the tests, expect PASS**

Run: `python .claude/skills/dayz-init/test_prompts.py`
Expected: `OK` (10 tests passed)

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/dayz-init/prompts.py .claude/skills/dayz-init/test_prompts.py
git commit -m "feat(dayz-init): add prompts module (ask_text, ask_yes_no, ask_select)"
```

---

## Task 3: detect.py for cwd, mod name, and mod-dir heuristics

**Files:**
- Create: `.claude/skills/dayz-init/detect.py`
- Create: `.claude/skills/dayz-init/test_detect.py`

- [ ] **Step 1: Write the failing tests**

Create `.claude/skills/dayz-init/test_detect.py`:

```python
"""Tests for detect.py."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from detect import (  # noqa: E402
    cwd,
    mod_name_from_cwd,
    mod_name_from_config_cpp,
    is_mod_dir,
)


class TestCwd(unittest.TestCase):
    def test_returns_path_object(self):
        self.assertIsInstance(cwd(), Path)

    def test_is_absolute(self):
        self.assertTrue(cwd().is_absolute())


class TestModNameFromCwd(unittest.TestCase):
    def test_returns_basename(self):
        with tempfile.TemporaryDirectory() as d:
            mod_dir = Path(d) / "MyTestMod"
            mod_dir.mkdir()
            self.assertEqual(mod_name_from_cwd(mod_dir), "MyTestMod")


class TestModNameFromConfigCpp(unittest.TestCase):
    def test_extracts_first_cfgpatches_class(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = Path(d) / "config.cpp"
            cfg.write_text(
                'class CfgPatches {\n'
                '    class MyAwesomeMod {\n'
                '        units[] = {};\n'
                '    };\n'
                '};\n'
            )
            self.assertEqual(mod_name_from_config_cpp(Path(d)), "MyAwesomeMod")

    def test_returns_none_when_no_config(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(mod_name_from_config_cpp(Path(d)))

    def test_returns_none_when_config_has_no_cfgpatches(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = Path(d) / "config.cpp"
            cfg.write_text("// empty")
            self.assertIsNone(mod_name_from_config_cpp(Path(d)))


class TestIsModDir(unittest.TestCase):
    def test_true_when_config_cpp_exists(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "config.cpp").write_text("")
            self.assertTrue(is_mod_dir(Path(d)))

    def test_true_when_pboprefix_exists(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "$PBOPREFIX$").write_text("MyMod")
            self.assertTrue(is_mod_dir(Path(d)))

    def test_false_when_neither(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertFalse(is_mod_dir(Path(d)))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests, expect ImportError**

Run: `python .claude/skills/dayz-init/test_detect.py`
Expected: ImportError on detect module.

- [ ] **Step 3: Implement detect.py**

Create `.claude/skills/dayz-init/detect.py`:

```python
"""Detection helpers for /dayz-init.

cwd, mod name from disk, mod-dir heuristic. Pure functions over Paths;
no I/O side effects beyond reading.
"""
from __future__ import annotations

import os
import re
from pathlib import Path


_CFGPATCHES_CLASS_RE = re.compile(
    r"class\s+CfgPatches\s*\{[^}]*?class\s+(\w+)",
    re.DOTALL,
)


def cwd() -> Path:
    """Current working directory as an absolute Path."""
    return Path(os.getcwd()).resolve()


def mod_name_from_cwd(path: Path | None = None) -> str:
    """Default mod name from a directory's basename."""
    return (path or cwd()).name


def mod_name_from_config_cpp(mod_dir: Path) -> str | None:
    """Extract first CfgPatches class name from <mod_dir>/config.cpp.

    Returns None if config.cpp is missing or has no CfgPatches block.
    """
    cfg = mod_dir / "config.cpp"
    if not cfg.is_file():
        return None
    text = cfg.read_text(encoding="utf-8", errors="replace")
    match = _CFGPATCHES_CLASS_RE.search(text)
    return match.group(1) if match else None


def is_mod_dir(path: Path) -> bool:
    """Heuristic: does this directory look like a DayZ mod?

    Yes if it has either config.cpp or $PBOPREFIX$ at the top.
    """
    return (path / "config.cpp").is_file() or (path / "$PBOPREFIX$").is_file()
```

- [ ] **Step 4: Run the tests, expect PASS**

Run: `python .claude/skills/dayz-init/test_detect.py`
Expected: `OK` (9 tests passed)

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/dayz-init/detect.py .claude/skills/dayz-init/test_detect.py
git commit -m "feat(dayz-init): add detect module (cwd, mod-name-from-config, is-mod-dir)"
```

---

## Task 4: env_check.py — detect prereqs, classify, suggest fixes

**Files:**
- Create: `.claude/skills/dayz-init/env_check.py`
- Create: `.claude/skills/dayz-init/test_env_check.py`

- [ ] **Step 1: Write the failing tests**

Create `.claude/skills/dayz-init/test_env_check.py`:

```python
"""Tests for env_check.py."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from env_check import (  # noqa: E402
    EnvIssue,
    Severity,
    check_python,
    check_p_drive,
    check_dayz_tools,
    classify,
)


class TestCheckPython(unittest.TestCase):
    def test_current_python_is_ok(self):
        # Whatever python is running this test is by definition >=3.8
        issue = check_python()
        self.assertIsNone(issue)


class TestCheckPDrive(unittest.TestCase):
    def test_returns_autofix_when_unmounted(self):
        with patch("env_check._p_drive_mounted", return_value=False):
            issue = check_p_drive()
            self.assertIsNotNone(issue)
            self.assertEqual(issue.severity, Severity.AUTOFIX)
            self.assertIn("P:\\", issue.message)


class TestCheckDayzTools(unittest.TestCase):
    def test_returns_hard_stop_when_missing(self):
        with patch("env_check._dayz_tools_installed", return_value=False):
            issue = check_dayz_tools()
            self.assertIsNotNone(issue)
            self.assertEqual(issue.severity, Severity.HARD_STOP)
            self.assertIn("steam://", issue.fix_link)


class TestClassify(unittest.TestCase):
    def test_groups_issues_by_severity(self):
        issues = [
            EnvIssue("p", Severity.AUTOFIX, "P: missing"),
            EnvIssue("tools", Severity.HARD_STOP, "Tools missing", fix_link="steam://x"),
        ]
        autofix, hard_stop = classify(issues)
        self.assertEqual(len(autofix), 1)
        self.assertEqual(len(hard_stop), 1)
        self.assertEqual(autofix[0].name, "p")
        self.assertEqual(hard_stop[0].name, "tools")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests, expect ImportError**

Run: `python .claude/skills/dayz-init/test_env_check.py`
Expected: ImportError.

- [ ] **Step 3: Implement env_check.py**

Create `.claude/skills/dayz-init/env_check.py`:

```python
"""Environment detection for /dayz-init.

Categorizes each prereq as: OK (nothing to do), AUTOFIX (we can fix it),
HARD_STOP (user has to act). Returns EnvIssue objects with optional
steam:// links and human-readable messages.
"""
from __future__ import annotations

import os
import shutil
import sys
import winreg
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class Severity(Enum):
    AUTOFIX = "autofix"
    HARD_STOP = "hard_stop"


@dataclass
class EnvIssue:
    name: str
    severity: Severity
    message: str
    fix_link: str | None = None


def check_python() -> EnvIssue | None:
    """Confirm Python 3.8+. Currently running interpreter == answer."""
    if sys.version_info < (3, 8):
        return EnvIssue(
            name="python",
            severity=Severity.HARD_STOP,
            message=f"Python 3.8+ required, found {sys.version.split()[0]}",
            fix_link="https://www.python.org/downloads/",
        )
    return None


def _p_drive_mounted() -> bool:
    return Path("P:\\").exists()


def check_p_drive() -> EnvIssue | None:
    if _p_drive_mounted():
        return None
    return EnvIssue(
        name="p_drive",
        severity=Severity.AUTOFIX,
        message="P:\\ is not mounted (will mount via subst)",
    )


def _dayz_tools_installed() -> bool:
    """Check Steam app 830640 install via registry. Returns False on any error."""
    try:
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\WOW6432Node\Bohemia Interactive\DayZ Tools",
        ):
            return True
    except OSError:
        return False


def check_dayz_tools() -> EnvIssue | None:
    if _dayz_tools_installed():
        return None
    return EnvIssue(
        name="dayz_tools",
        severity=Severity.HARD_STOP,
        message="DayZ Tools is not installed (Steam, free)",
        fix_link="steam://install/830640",
    )


def check_vanilla_data() -> EnvIssue | None:
    """Vanilla data extracted to P:\\ implies P:\\scripts\\3_Game exists."""
    marker = Path("P:\\scripts\\3_Game")
    if marker.is_dir():
        return None
    return EnvIssue(
        name="vanilla_data",
        severity=Severity.HARD_STOP,
        message=(
            "Vanilla data is not extracted to P:\\.\n"
            "  Open DayZ Tools, then: Tools menu, Extract Game Data."
        ),
    )


def check_mods_junction() -> EnvIssue | None:
    """P:\\Mods\\ should junction to <DayZ install>\\!Workshop\\."""
    if Path("P:\\Mods").exists():
        return None
    return EnvIssue(
        name="mods_junction",
        severity=Severity.AUTOFIX,
        message="P:\\Mods\\ junction to !Workshop missing (will create)",
    )


def run_all() -> list[EnvIssue]:
    """Run every check, return non-None issues in declaration order."""
    checks = [
        check_python,
        check_p_drive,
        check_dayz_tools,
        check_vanilla_data,
        check_mods_junction,
    ]
    return [issue for check in checks if (issue := check()) is not None]


def classify(
    issues: list[EnvIssue],
) -> tuple[list[EnvIssue], list[EnvIssue]]:
    """Split issues into (autofixable, hard_stop) preserving order within each."""
    autofix = [i for i in issues if i.severity == Severity.AUTOFIX]
    hard_stop = [i for i in issues if i.severity == Severity.HARD_STOP]
    return autofix, hard_stop
```

- [ ] **Step 4: Run the tests, expect PASS**

Run: `python .claude/skills/dayz-init/test_env_check.py`
Expected: `OK` (4 tests passed)

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/dayz-init/env_check.py .claude/skills/dayz-init/test_env_check.py
git commit -m "feat(dayz-init): add env_check (python, P:\, DayZ Tools, vanilla data, junction)"
```

---

## Task 5: state.py — disk-derived setup state + state.json reads/writes

**Files:**
- Create: `.claude/skills/dayz-init/state.py`
- Create: `.claude/skills/dayz-init/test_state.py`

- [ ] **Step 1: Write the failing tests**

Create `.claude/skills/dayz-init/test_state.py`:

```python
"""Tests for state.py."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from state import (  # noqa: E402
    cached_project_root,
    write_cached_project_root,
    is_setup_complete,
    read_state,
    write_state,
)


class TestCachedProjectRoot(unittest.TestCase):
    def test_returns_none_when_cache_missing(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(cached_project_root(home=Path(d)))

    def test_returns_path_when_cache_present(self):
        with tempfile.TemporaryDirectory() as home:
            write_cached_project_root(Path("G:/repos/MyMod"), home=Path(home))
            result = cached_project_root(home=Path(home))
            self.assertEqual(result, Path("G:/repos/MyMod"))


class TestIsSetupComplete(unittest.TestCase):
    def test_false_for_empty_dir(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertFalse(is_setup_complete(Path(d)))

    def test_true_when_required_markers_present(self):
        with tempfile.TemporaryDirectory() as d:
            project = Path(d)
            (project / "$PBOPREFIX$").write_text("MyMod")
            (project / "config.cpp").write_text("class CfgPatches {};")
            (project / ".agentic-z").mkdir()
            (project / ".agentic-z" / "state.json").write_text("{}")
            self.assertTrue(is_setup_complete(project))


class TestReadWriteState(unittest.TestCase):
    def test_read_returns_empty_dict_when_missing(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(read_state(Path(d)), {})

    def test_write_then_read_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            project = Path(d)
            write_state(project, {"rag": "skip", "last_build": "ok"})
            self.assertEqual(
                read_state(project),
                {"rag": "skip", "last_build": "ok"},
            )

    def test_write_creates_agentic_z_dir(self):
        with tempfile.TemporaryDirectory() as d:
            project = Path(d)
            write_state(project, {})
            self.assertTrue((project / ".agentic-z").is_dir())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests, expect ImportError**

Run: `python .claude/skills/dayz-init/test_state.py`
Expected: ImportError.

- [ ] **Step 3: Implement state.py**

Create `.claude/skills/dayz-init/state.py`:

```python
"""State management for /dayz-init.

Two stores:
  1. ~/.claude/local-memory/dayz-current-project.txt  - the cached project path
  2. <project>/.agentic-z/state.json                  - per-project wizard state

Setup completion is derived from disk markers, not the state file.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

CACHE_RELATIVE = Path(".claude/local-memory/dayz-current-project.txt")
STATE_DIR_NAME = ".agentic-z"
STATE_FILE_NAME = "state.json"


def _claude_home(home: Path | None = None) -> Path:
    if home is not None:
        return home
    return Path.home() / ".claude" / "local-memory"


def cached_project_root(home: Path | None = None) -> Path | None:
    """Read the project-root cache. Returns None if file missing or empty."""
    cache = _claude_home(home) / "dayz-current-project.txt"
    if not cache.is_file():
        return None
    text = cache.read_text(encoding="utf-8").strip()
    return Path(text) if text else None


def write_cached_project_root(path: Path, home: Path | None = None) -> None:
    """Write the project-root cache, creating parent dirs as needed."""
    cache = _claude_home(home) / "dayz-current-project.txt"
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(str(path), encoding="utf-8")


def is_setup_complete(project: Path) -> bool:
    """Required markers for hub mode: scaffolded mod + state file."""
    has_pboprefix = (project / "$PBOPREFIX$").is_file()
    has_config = (project / "config.cpp").is_file()
    has_state = (project / STATE_DIR_NAME / STATE_FILE_NAME).is_file()
    return has_pboprefix and has_config and has_state


def _state_path(project: Path) -> Path:
    return project / STATE_DIR_NAME / STATE_FILE_NAME


def read_state(project: Path) -> dict:
    """Load <project>/.agentic-z/state.json. Empty dict if missing."""
    path = _state_path(project)
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def write_state(project: Path, data: dict) -> None:
    """Write JSON state, creating .agentic-z/ if needed."""
    path = _state_path(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
```

- [ ] **Step 4: Run the tests, expect PASS**

Run: `python .claude/skills/dayz-init/test_state.py`
Expected: `OK` (7 tests passed)

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/dayz-init/state.py .claude/skills/dayz-init/test_state.py
git commit -m "feat(dayz-init): add state module (project cache + per-project state.json)"
```

---

## Task 6: intent.py — collect Intent dataclass via prompts

**Files:**
- Create: `.claude/skills/dayz-init/intent.py`

- [ ] **Step 1: Implement intent.py**

(No new test file. The prompt orchestration is thin glue over already-tested primitives; we test it via the integration smoke test in Task 8.)

Create `.claude/skills/dayz-init/intent.py`:

```python
"""Intent prompts for /dayz-init.

Asks the user every "decision" needed by the wizard. Returns an Intent
dataclass that plan.py turns into a concrete sequence of actions.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from prompts import ask_text, ask_yes_no, ask_select
from detect import (
    cwd,
    is_mod_dir,
    mod_name_from_config_cpp,
    mod_name_from_cwd,
)


KNOWN_MAPS = ["chernarus", "livonia", "sakhal", "namalsk"]


@dataclass
class Intent:
    is_new: bool             # True = new mod, False = import existing
    mod_name: str
    project_path: Path
    add_server: bool
    server_map: str | None   # None when add_server is False
    build_pbo: bool
    launch_diag: bool
    rag_choice: str          # "skip" | "paste" | "pull"


def gather_intent() -> Intent:
    """Run the intent prompt phase from start to finish."""
    print("\n── Intent ──")

    intent_choice = ask_select(
        "What are you doing?",
        ["starting a new mod", "importing an existing repo"],
        default="starting a new mod",
    )
    is_new = intent_choice == "starting a new mod"

    starting_dir = cwd()
    if is_new:
        default_name = mod_name_from_cwd(starting_dir)
    else:
        default_name = (
            mod_name_from_config_cpp(starting_dir)
            or mod_name_from_cwd(starting_dir)
        )

    mod_name = ask_text("Mod name?", default=default_name)
    project_path = Path(
        ask_text("Project path?", default=str(starting_dir))
    ).resolve()

    add_server = ask_yes_no("Set up a test server?", default=True)
    server_map: str | None = None
    if add_server:
        server_map = ask_select(
            "Map?",
            KNOWN_MAPS,
            default="chernarus",
        )

    build_pbo = ask_yes_no("Build PBO now?", default=False)
    launch_diag = ask_yes_no("Launch DayZ now?", default=False)
    if launch_diag and not build_pbo:
        # Launch implies build; auto-include
        print("(launch implies build, including PBO build in plan)")
        build_pbo = True

    rag_choice = "skip"
    if not os.environ.get("VOYAGE_API_KEY"):
        rag_choice = ask_select(
            "RAG setup?",
            ["skip", "paste Voyage key", "pull prebuilt index"],
            default="skip",
        )
        # Normalize to short codes for plan.py
        rag_choice = {
            "skip": "skip",
            "paste Voyage key": "paste",
            "pull prebuilt index": "pull",
        }[rag_choice]

    return Intent(
        is_new=is_new,
        mod_name=mod_name,
        project_path=project_path,
        add_server=add_server,
        server_map=server_map,
        build_pbo=build_pbo,
        launch_diag=launch_diag,
        rag_choice=rag_choice,
    )
```

- [ ] **Step 2: Smoke-import to verify syntax**

Run: `python -c "from importlib import import_module; import sys; sys.path.insert(0, '.claude/skills/dayz-init'); import intent; print('ok')"`
Expected output: `ok`

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/dayz-init/intent.py
git commit -m "feat(dayz-init): add intent module (Intent dataclass + gather_intent)"
```

---

## Task 7: plan.py — render and execute the plan

**Files:**
- Create: `.claude/skills/dayz-init/plan.py`
- Create: `.claude/skills/dayz-init/test_plan.py`

- [ ] **Step 1: Write the failing tests (rendering only)**

Create `.claude/skills/dayz-init/test_plan.py`:

```python
"""Tests for plan.py rendering. Execution is integration-tested separately."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from intent import Intent  # noqa: E402
from plan import build_steps, render_plan, Step  # noqa: E402
from env_check import EnvIssue, Severity  # noqa: E402


def _intent(**overrides) -> Intent:
    base = dict(
        is_new=True,
        mod_name="MyMod",
        project_path=Path("G:/repos/MyMod"),
        add_server=True,
        server_map="chernarus",
        build_pbo=False,
        launch_diag=False,
        rag_choice="skip",
    )
    base.update(overrides)
    return Intent(**base)


class TestBuildSteps(unittest.TestCase):
    def test_required_steps_always_present(self):
        steps = build_steps(_intent(add_server=False), autofix_issues=[])
        kinds = [s.kind for s in steps]
        self.assertIn("scaffold", kinds)
        self.assertIn("junction_mod", kinds)
        self.assertIn("cache_project", kinds)

    def test_server_step_only_when_opted_in(self):
        without = build_steps(_intent(add_server=False), autofix_issues=[])
        with_srv = build_steps(_intent(add_server=True), autofix_issues=[])
        self.assertNotIn("stage_server", [s.kind for s in without])
        self.assertIn("stage_server", [s.kind for s in with_srv])

    def test_build_step_only_when_opted_in(self):
        without = build_steps(_intent(build_pbo=False), autofix_issues=[])
        with_b = build_steps(_intent(build_pbo=True), autofix_issues=[])
        self.assertNotIn("build_pbo", [s.kind for s in without])
        self.assertIn("build_pbo", [s.kind for s in with_b])

    def test_launch_step_only_when_opted_in(self):
        without = build_steps(_intent(launch_diag=False), autofix_issues=[])
        with_l = build_steps(
            _intent(launch_diag=True, build_pbo=True), autofix_issues=[]
        )
        self.assertNotIn("launch_diag", [s.kind for s in without])
        self.assertIn("launch_diag", [s.kind for s in with_l])

    def test_autofix_steps_prepended(self):
        issues = [
            EnvIssue("p_drive", Severity.AUTOFIX, "P: missing"),
            EnvIssue("mods_junction", Severity.AUTOFIX, "junction missing"),
        ]
        steps = build_steps(_intent(), autofix_issues=issues)
        # Autofix steps come before required steps
        first_two_kinds = [s.kind for s in steps[:2]]
        self.assertEqual(
            first_two_kinds, ["autofix:p_drive", "autofix:mods_junction"]
        )

    def test_import_uses_import_step_not_scaffold(self):
        steps = build_steps(_intent(is_new=False), autofix_issues=[])
        kinds = [s.kind for s in steps]
        self.assertIn("import_mod", kinds)
        self.assertNotIn("scaffold", kinds)


class TestRenderPlan(unittest.TestCase):
    def test_render_includes_each_step_label(self):
        steps = [
            Step(kind="scaffold", label="Scaffold MyMod at G:/repos/MyMod"),
            Step(kind="cache_project", label="Cache project root"),
        ]
        text = render_plan(steps)
        self.assertIn("Scaffold MyMod", text)
        self.assertIn("Cache project root", text)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests, expect ImportError**

Run: `python .claude/skills/dayz-init/test_plan.py`
Expected: ImportError on plan module.

- [ ] **Step 3: Implement plan.py**

Create `.claude/skills/dayz-init/plan.py`:

```python
"""Plan building, rendering, and execution for /dayz-init.

A Plan is a list of Steps. Each Step has a `kind` (string identifying which
skill to invoke), a human-readable label for the plan render, and optional
extra args.

Execution wraps each step in a try/except. On failure, returns the index
of the failing step so the caller can show "stopped at step N/M".
"""
from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from env_check import EnvIssue
from intent import Intent

REPO_ROOT = Path(__file__).resolve().parents[3]


@dataclass
class Step:
    kind: str
    label: str
    args: list[str] = field(default_factory=list)


def build_steps(intent: Intent, autofix_issues: list[EnvIssue]) -> list[Step]:
    """Compose the full ordered list of steps from intent + env state."""
    steps: list[Step] = []

    # Autofix env issues first.
    for issue in autofix_issues:
        steps.append(
            Step(
                kind=f"autofix:{issue.name}",
                label=issue.message,
            )
        )

    # Required: scaffold OR import.
    if intent.is_new:
        steps.append(
            Step(
                kind="scaffold",
                label=f"Scaffold {intent.mod_name} at {intent.project_path}",
                args=[intent.mod_name, str(intent.project_path)],
            )
        )
    else:
        steps.append(
            Step(
                kind="import_mod",
                label=f"Import existing mod at {intent.project_path}",
                args=[str(intent.project_path)],
            )
        )

    # Required: junction P:\<Mod>\.
    steps.append(
        Step(
            kind="junction_mod",
            label=f"Junction P:\\{intent.mod_name}\\",
            args=[intent.mod_name, str(intent.project_path)],
        )
    )

    # Required: cache project root.
    steps.append(
        Step(
            kind="cache_project",
            label="Cache project root",
            args=[str(intent.project_path)],
        )
    )

    # Optional: server stage.
    if intent.add_server and intent.server_map:
        steps.append(
            Step(
                kind="stage_server",
                label=f"Stage {intent.server_map} server",
                args=[intent.server_map],
            )
        )

    # Optional: PBO build.
    if intent.build_pbo:
        steps.append(
            Step(
                kind="build_pbo",
                label=f"Build {intent.mod_name}.pbo",
                args=[intent.mod_name],
            )
        )

    # Optional: launch diag.
    if intent.launch_diag and intent.server_map:
        steps.append(
            Step(
                kind="launch_diag",
                label=(
                    f"Launch DayZDiag with {intent.mod_name} loaded "
                    f"on {intent.server_map}"
                ),
                args=[intent.mod_name, intent.server_map],
            )
        )

    return steps


def render_plan(steps: list[Step]) -> str:
    """Pretty-print the plan for the consent gate."""
    lines = ["── Plan ──"]
    for step in steps:
        lines.append(f"  • {step.label}")
    return "\n".join(lines)


def execute(steps: list[Step]) -> int:
    """Run each step in order. Return the 1-indexed failing step, or 0 on success."""
    for i, step in enumerate(steps, start=1):
        print(f"[{i}/{len(steps)}] {step.label}")
        try:
            _dispatch(step)
        except Exception as exc:
            print(f"  failed: {exc}")
            return i
        print("  ok")
    return 0


def _dispatch(step: Step) -> None:
    """Map a step kind to the existing skill that performs it."""
    if step.kind.startswith("autofix:"):
        which = step.kind.split(":", 1)[1]
        if which == "p_drive":
            _run("dayz-workdrive", "workdrive.py")
        elif which == "mods_junction":
            _create_mods_junction()
        else:
            raise RuntimeError(f"Unknown autofix kind: {which}")
        return

    if step.kind == "scaffold":
        _run("dayz-new-mod", "new_mod.py", *step.args)
    elif step.kind == "import_mod":
        _run("dayz-import-mod", "import_mod.py", "--source", *step.args)
    elif step.kind == "junction_mod":
        _create_mod_junction(*step.args)
    elif step.kind == "cache_project":
        from state import write_cached_project_root  # local import
        write_cached_project_root(Path(step.args[0]))
    elif step.kind == "stage_server":
        _run("dayz-add-server", "add_server.py", *step.args)
    elif step.kind == "build_pbo":
        _run("dayz-build-pbo", "build.py", *step.args)
    elif step.kind == "launch_diag":
        mod_name, server_map = step.args
        _run("dayz-launch-test", "launch.py", mod_name, "--server", server_map)
    else:
        raise RuntimeError(f"Unknown step kind: {step.kind}")


def _run(skill_name: str, entry_filename: str, *args: str) -> None:
    """Invoke an existing skill via subprocess. Raises on non-zero exit."""
    skill_path = REPO_ROOT / ".claude" / "skills" / skill_name / entry_filename
    cmd = [sys.executable, str(skill_path), *args]
    subprocess.run(cmd, check=True)


def _create_mods_junction() -> None:
    """Best-effort junction P:\\Mods\\ to <DayZ install>\\!Workshop\\."""
    # Implementation intentionally calls dayz-workdrive's helper via subprocess
    # so the logic stays in one place. We re-use it here.
    _run("dayz-workdrive", "workdrive.py", "--ensure-mods-junction")


def _create_mod_junction(mod_name: str, project_path: str) -> None:
    """Create P:\\<ModName>\\ junction to <project_path>."""
    target = f"P:\\{mod_name}"
    subprocess.run(
        ["cmd", "/c", "mklink", "/J", target, project_path],
        check=True,
    )
```

- [ ] **Step 4: Run the tests, expect PASS**

Run: `python .claude/skills/dayz-init/test_plan.py`
Expected: `OK` (7 tests passed)

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/dayz-init/plan.py .claude/skills/dayz-init/test_plan.py
git commit -m "feat(dayz-init): add plan module (build/render/execute)"
```

---

## Task 8: init.py wiring — wizard mode end-to-end

**Files:**
- Modify: `.claude/skills/dayz-init/init.py:1-15`

- [ ] **Step 1: Wire the wizard pipeline**

Replace `init.py` contents:

```python
"""Entry point for /dayz-init.

First run: setup wizard (env -> intent -> plan -> execute -> hub).
Subsequent runs: hub mode (added in Task 12).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from detect import cwd  # noqa: E402
from env_check import run_all, classify, Severity  # noqa: E402
from intent import gather_intent  # noqa: E402
from plan import build_steps, render_plan, execute  # noqa: E402
from prompts import ask_yes_no  # noqa: E402
from state import (  # noqa: E402
    cached_project_root,
    is_setup_complete,
    write_state,
)


def run_wizard() -> int:
    print("/dayz-init")
    print()
    print("── Environment ──")
    issues = run_all()
    autofix, hard_stop = classify(issues)

    if hard_stop:
        print("\nCan't proceed. Need to fix:\n")
        for issue in hard_stop:
            print(f"  • {issue.message}")
            if issue.fix_link:
                print(f"    {issue.fix_link}")
        print("\nWhen done, re-run: /dayz-init")
        print("(I'll pick up where I left off.)")
        return 2

    if not issues:
        print("✓ Environment ready.")
    else:
        for issue in autofix:
            print(f"! {issue.message}")

    intent = gather_intent()
    steps = build_steps(intent, autofix)

    print()
    print(render_plan(steps))
    print()
    if not ask_yes_no("Continue?", default=True):
        print("Aborted. Re-run /dayz-init when ready.")
        return 1

    print("\n── Execute ──")
    failed_at = execute(steps)
    if failed_at:
        print(f"\nStopped at step {failed_at}/{len(steps)}.")
        print("Re-run /dayz-init to drop into the hub and retry.")
        return 1

    write_state(
        intent.project_path,
        {
            "rag_choice": intent.rag_choice,
            "last_intent": {
                "mod_name": intent.mod_name,
                "is_new": intent.is_new,
                "server_map": intent.server_map,
            },
        },
    )

    print("\n✓ Setup complete.")
    print("(Hub mode arrives in Task 12. For now, re-run /dayz-init.)")
    return 0


def main(argv: list[str] | None = None) -> int:
    project = cached_project_root()
    if project is not None and is_setup_complete(project):
        # Hub mode arrives in Task 12. For now, message and exit.
        print(f"Project '{project.name}' is set up. Hub mode coming in Task 12.")
        return 0
    return run_wizard()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

- [ ] **Step 2: Smoke-import to confirm syntax**

Run: `python -c "import sys; sys.path.insert(0, '.claude/skills/dayz-init'); import init"`
Expected: no error.

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/dayz-init/init.py
git commit -m "feat(dayz-init): wire wizard pipeline (env, intent, plan, execute, state)"
```

---

## Task 9: Manual smoke test of the wizard

This task does not write code; it validates Tasks 1-8 against a real environment.

- [ ] **Step 1: Verify a clean test directory exists**

Pick (or create) an empty directory outside the agentic-z repo to be `MyTestMod`'s project path. Note the absolute path.

- [ ] **Step 2: Run the wizard with stdin pointed at the test directory**

```cmd
cd <empty test dir>
python <agentic-z>\.claude\skills\dayz-init\init.py
```

- [ ] **Step 3: Walk the prompts**

Expected sequence (defaults shown in brackets):

1. Environment block reports no hard-stops.
2. `What are you doing?` — pick `starting a new mod`.
3. `Mod name?` — confirm or override the cwd-basename default.
4. `Project path?` — confirm cwd default.
5. `Set up a test server?` — `Y`.
6. `Map?` — confirm `chernarus`.
7. `Build PBO now?` — `n`.
8. `Launch DayZ now?` — `n`.
9. `RAG setup?` — `skip`.
10. Plan block shows scaffold, junction, cache, stage server.
11. `Continue?` — `Y`.
12. Each step prints `[i/N]`, `ok`. Final line: `✓ Setup complete.`

- [ ] **Step 4: Verify on disk**

```cmd
dir "<test dir>"
```

Expected: `config.cpp`, `$PBOPREFIX$`, `scripts\`, `data\`, `.agentic-z\state.json`.

```cmd
dir P:\<ModName>
```

Expected: junction listing showing the test dir.

```cmd
type %USERPROFILE%\.claude\local-memory\dayz-current-project.txt
```

Expected: the absolute path of the test dir.

- [ ] **Step 5: Re-run and verify the placeholder hub message**

```cmd
python <agentic-z>\.claude\skills\dayz-init\init.py
```

Expected: `Project '<ModName>' is set up. Hub mode coming in Task 12.`

- [ ] **Step 6: Commit nothing; just record the smoke-test pass in your task log**

If anything in steps 3-5 misbehaved, fix it in the relevant module and re-run before moving to Task 10.

---

## Task 10: hub.py — status block + flat menu

**Files:**
- Create: `.claude/skills/dayz-init/hub.py`

- [ ] **Step 1: Implement hub.py**

Create `.claude/skills/dayz-init/hub.py`:

```python
"""Mission-control hub for /dayz-init.

Runs every time /dayz-init is invoked after setup is complete. Renders
project status, a flat menu of actions, and dispatches the user's pick
to existing skills via subprocess.
"""
from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from prompts import ask_select, ask_yes_no
from state import read_state


REPO_ROOT = Path(__file__).resolve().parents[3]


@dataclass
class Status:
    project: Path
    pbo_path: Path | None       # P:\Mods\@<Mod>\Addons\<Mod>.pbo, if exists
    pbo_age_minutes: int | None
    server_instance: str | None  # "chernarus" or None
    diag_running: bool
    rag_on: bool
    audit_recent: bool


def gather_status(project: Path) -> Status:
    state = read_state(project)
    mod_name = project.name
    pbo = Path(f"P:\\Mods\\@{mod_name}\\Addons\\{mod_name}.pbo")
    pbo_path = pbo if pbo.is_file() else None
    pbo_age = (
        int((datetime.now(timezone.utc).timestamp() - pbo.stat().st_mtime) / 60)
        if pbo_path
        else None
    )
    server_dir = project / ".server"
    server_instance: str | None = None
    if server_dir.is_dir():
        instances = [p.name for p in server_dir.iterdir() if p.is_dir()]
        server_instance = instances[0] if instances else None

    return Status(
        project=project,
        pbo_path=pbo_path,
        pbo_age_minutes=pbo_age,
        server_instance=server_instance,
        diag_running=_diag_running(),
        rag_on=bool(os.environ.get("VOYAGE_API_KEY"))
        and state.get("rag_choice") in ("paste", "pull"),
        audit_recent=False,  # populated when /dayz-mod-reviewer is integrated
    )


def render_status(status: Status) -> str:
    mod_name = status.project.name
    lines = [f"── /dayz-init  •  {mod_name} ──"]
    lines.append(f"Path:    {status.project}")
    if status.pbo_path:
        lines.append(f"PBO:     built {status.pbo_age_minutes}m ago")
    else:
        lines.append("PBO:     not built yet")
    if status.server_instance:
        running_tag = "running" if status.diag_running else "staged (not running)"
        lines.append(f"Server:  {status.server_instance}, {running_tag}")
    else:
        lines.append("Server:  not configured")
    lines.append(f"Diag:    {'running' if status.diag_running else 'not running'}")
    lines.append(f"RAG:     {'on' if status.rag_on else 'skipped'}")
    return "\n".join(lines)


def _diag_running() -> bool:
    try:
        out = subprocess.check_output(
            ["tasklist", "/FI", "IMAGENAME eq DayZDiag_x64.exe"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        return "DayZDiag_x64.exe" in out
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def _run_skill(skill_name: str, entry_filename: str, *args: str) -> int:
    path = REPO_ROOT / ".claude" / "skills" / skill_name / entry_filename
    return subprocess.run([sys.executable, str(path), *args]).returncode


def _action_build_and_launch(status: Status) -> None:
    if status.server_instance is None:
        if ask_yes_no("No server configured. Set one up first?", default=True):
            from prompts import ask_select  # local
            chosen = ask_select(
                "Map?",
                ["chernarus", "livonia", "sakhal", "namalsk"],
                default="chernarus",
            )
            _run_skill("dayz-add-server", "add_server.py", chosen)
            status.server_instance = chosen
        else:
            return
    mod_name = status.project.name
    if _run_skill("dayz-build-pbo", "build.py", mod_name) != 0:
        print("(build failed; see output above)")
        return
    _run_skill(
        "dayz-launch-test",
        "launch.py",
        mod_name,
        "--server",
        status.server_instance,
    )


def _action_stop_diag(_: Status) -> None:
    if not ask_yes_no("Stop the diag client?", default=True):
        return
    _run_skill("dayz-stop-test", "stop_test.py")


def _action_tail_log(status: Status) -> None:
    if not status.server_instance:
        print("(no server to tail)")
        return
    log = (
        status.project
        / ".server"
        / status.server_instance
        / "server-profiles"
        / "script.log"
    )
    if not log.is_file():
        print(f"(log not found: {log})")
        return
    print(f"Tailing {log}. Ctrl-C to return to the hub.")
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "Get-Content", "-Wait", str(log)]
        )
    except KeyboardInterrupt:
        pass


def _action_workbench(status: Status) -> None:
    _run_skill(
        "dayz-launch-workbench", "launch_workbench.py", "--mod", status.project.name
    )


def _action_objbuilder(status: Status) -> None:
    _run_skill(
        "dayz-launch-objectbuilder",
        "launch_objectbuilder.py",
        "--mod",
        status.project.name,
    )


def _action_quit(_: Status) -> None:
    raise SystemExit(0)


# Order is the order shown in the hub menu.
ACTIONS: list[tuple[str, Callable[[Status], None]]] = [
    ("build & launch", _action_build_and_launch),
    ("stop diag", _action_stop_diag),
    ("tail server log", _action_tail_log),
    ("open in workbench", _action_workbench),
    ("open in objectbuilder", _action_objbuilder),
    ("quit", _action_quit),
]


def run_hub(project: Path) -> int:
    while True:
        status = gather_status(project)
        print()
        print(render_status(status))
        print()
        labels = [label for label, _ in ACTIONS]
        choice = ask_select("? what now", labels, default=labels[0])
        for label, action in ACTIONS:
            if label == choice:
                try:
                    action(status)
                except SystemExit:
                    return 0
                break
```

- [ ] **Step 2: Smoke-import**

Run: `python -c "import sys; sys.path.insert(0, '.claude/skills/dayz-init'); import hub"`
Expected: no error.

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/dayz-init/hub.py
git commit -m "feat(dayz-init): add hub module (status + 6-action menu)"
```

---

## Task 11: Add the rest of the hub actions (init another, switch project, run reviewer, set voyage key, add test server)

**Files:**
- Modify: `.claude/skills/dayz-init/hub.py:115-152`

- [ ] **Step 1: Add the missing actions**

Inside `hub.py`, add these helper functions before the `ACTIONS` list:

```python
def _action_init_another(_: Status) -> None:
    if not ask_yes_no(
        "This will replace the cached project. Continue?", default=False
    ):
        return
    # Re-running init.py with cleared cache forces wizard mode.
    from state import write_cached_project_root
    cache = Path.home() / ".claude" / "local-memory" / "dayz-current-project.txt"
    if cache.is_file():
        cache.unlink()
    print("Cache cleared. Re-run /dayz-init to set up another mod.")
    raise SystemExit(0)


def _action_switch_project(_: Status) -> None:
    candidates = _discover_managed_projects()
    if not candidates:
        print("(no agentic-z-managed projects found under P:\\Mods\\@*)")
        return
    chosen = ask_select(
        "Switch to which project?",
        [str(p) for p in candidates],
        default=str(candidates[0]),
    )
    from state import write_cached_project_root
    write_cached_project_root(Path(chosen))
    print(f"Switched to {chosen}. Re-run /dayz-init.")
    raise SystemExit(0)


def _discover_managed_projects() -> list[Path]:
    """Scan P:\\Mods\\@*\\.agentic-z-scaffold for project paths."""
    mods_root = Path("P:\\Mods")
    if not mods_root.is_dir():
        return []
    out: list[Path] = []
    for at_dir in mods_root.glob("@*"):
        marker = at_dir / ".agentic-z-scaffold"
        if marker.is_file():
            text = marker.read_text(encoding="utf-8").strip()
            if text:
                out.append(Path(text))
    return out


def _action_reviewer(status: Status) -> None:
    """Print guidance for invoking the reviewer agent via the Claude Code chat.

    The reviewer is an Agent, not a slash skill. Agents are dispatched via the
    Agent tool from the Claude Code conversation, not via Python subprocess.
    So this hub action just tells the user how to ask Claude to run it.
    """
    print()
    print(f"To audit {status.project.name}, ask Claude in this session:")
    print(f"  > run dayz-mod-reviewer on {status.project}")
    print("Then come back to /dayz-init for the next action.")


def _action_set_voyage_key(_: Status) -> None:
    from prompts import ask_text
    key = ask_text("Paste your Voyage API key (pa-...):")
    if not key.startswith("pa-"):
        print("(skipped; key does not start with 'pa-')")
        return
    env_path = REPO_ROOT / ".env"
    existing = ""
    if env_path.is_file():
        existing = env_path.read_text(encoding="utf-8")
    if "VOYAGE_API_KEY=" in existing:
        print("(VOYAGE_API_KEY already in .env; not overwriting)")
        return
    with open(env_path, "a", encoding="utf-8") as f:
        f.write(f"\nVOYAGE_API_KEY={key}\n")
    print(f"Wrote VOYAGE_API_KEY to {env_path}")
    if ask_yes_no("Pull the prebuilt RAG index now?", default=True):
        _run_skill("dayz-search-download", "download.py")


def _action_add_test_server(status: Status) -> None:
    if status.server_instance is not None:
        print(f"(server '{status.server_instance}' already configured)")
        return
    chosen = ask_select(
        "Map?",
        ["chernarus", "livonia", "sakhal", "namalsk"],
        default="chernarus",
    )
    _run_skill("dayz-add-server", "add_server.py", chosen)
```

Replace the `ACTIONS` list at the bottom of the file:

```python
ACTIONS: list[tuple[str, Callable[[Status], None]]] = [
    ("build & launch", _action_build_and_launch),
    ("stop diag", _action_stop_diag),
    ("tail server log", _action_tail_log),
    ("open in workbench", _action_workbench),
    ("open in objectbuilder", _action_objbuilder),
    ("run mod reviewer", _action_reviewer),
    ("set voyage key", _action_set_voyage_key),
    ("add test server", _action_add_test_server),
    ("init another mod", _action_init_another),
    ("switch project", _action_switch_project),
    ("quit", _action_quit),
]
```

- [ ] **Step 2: Smoke-import**

Run: `python -c "import sys; sys.path.insert(0, '.claude/skills/dayz-init'); import hub; print(len(hub.ACTIONS))"`
Expected: `11`

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/dayz-init/hub.py
git commit -m "feat(dayz-init): add 5 more hub actions (init/switch/reviewer/voyage/add-server)"
```

---

## Task 12: Wire hub into init.py

**Files:**
- Modify: `.claude/skills/dayz-init/init.py:78-84`

- [ ] **Step 1: Replace the placeholder hub message with the real hub call**

In `init.py`, find the block:

```python
def main(argv: list[str] | None = None) -> int:
    project = cached_project_root()
    if project is not None and is_setup_complete(project):
        # Hub mode arrives in Task 12. For now, message and exit.
        print(f"Project '{project.name}' is set up. Hub mode coming in Task 12.")
        return 0
    return run_wizard()
```

Replace with:

```python
def main(argv: list[str] | None = None) -> int:
    project = cached_project_root()
    if project is not None and is_setup_complete(project):
        from hub import run_hub
        return run_hub(project)
    rc = run_wizard()
    if rc == 0:
        # Wizard finished. Drop into the hub for the same project.
        project = cached_project_root()
        if project is not None and is_setup_complete(project):
            from hub import run_hub
            return run_hub(project)
    return rc
```

- [ ] **Step 2: Smoke-import**

Run: `python -c "import sys; sys.path.insert(0, '.claude/skills/dayz-init'); import init"`
Expected: no error.

- [ ] **Step 3: Manual run on the test directory from Task 9**

```cmd
cd <test dir>
python <agentic-z>\.claude\skills\dayz-init\init.py
```

Expected: status block, then `? what now` menu with 11 options. Pick `quit` to exit. Re-running enters the hub directly.

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/dayz-init/init.py
git commit -m "feat(dayz-init): wire hub into init.py (post-wizard + re-run paths)"
```

---

## Task 13: Gate /dayz-build-pbo with /dayz-init pointer

**Files:**
- Modify: `.claude/skills/dayz-build-pbo/build.py` (around the cached-project-root lookup; exact line varies)

- [ ] **Step 1: Locate the cached-project lookup**

Run: `grep -n "dayz-current-project.txt\|cached_project_root\|local-memory" .claude/skills/dayz-build-pbo/build.py`

Identify the line where the script bails out if the cache is missing.

- [ ] **Step 2: Replace the bail-out message**

Wherever the script currently does something like:

```python
if not cache.is_file():
    print("error: no project cached")
    sys.exit(1)
```

Replace with:

```python
if not cache.is_file():
    print(
        "error: no project cached.\n"
        "  Run /dayz-init to set up your DayZ environment and project."
    )
    sys.exit(2)
```

(Use exit code `2` for "missing prereq" so callers can distinguish from real failures.)

- [ ] **Step 3: Verify by running with no project cached**

```cmd
del %USERPROFILE%\.claude\local-memory\dayz-current-project.txt
python .claude\skills\dayz-build-pbo\build.py SomeMod
```

Expected output includes `Run /dayz-init` line. Exit code 2.

- [ ] **Step 4: Restore your test cache (so subsequent tasks can run)**

Re-run `/dayz-init` on your test directory (or write the cache file back manually).

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/dayz-build-pbo/build.py
git commit -m "feat(dayz-build-pbo): point at /dayz-init when no project is cached"
```

---

## Task 14: Gate /dayz-launch-test and /dayz-add-server the same way

**Files:**
- Modify: `.claude/skills/dayz-launch-test/launch.py`
- Modify: `.claude/skills/dayz-add-server/add_server.py`

- [ ] **Step 1: Apply the same pattern as Task 13 to launch.py**

Find the cached-project-lookup bail in `.claude/skills/dayz-launch-test/launch.py`. Replace the message with the `/dayz-init` pointer (same text as Task 13). Use exit code 2.

- [ ] **Step 2: Apply the same pattern to add_server.py**

Find the cached-project-lookup bail in `.claude/skills/dayz-add-server/add_server.py`. Replace the message with the `/dayz-init` pointer. Exit code 2.

- [ ] **Step 3: Verify both with no cache**

```cmd
del %USERPROFILE%\.claude\local-memory\dayz-current-project.txt
python .claude\skills\dayz-launch-test\launch.py SomeMod
python .claude\skills\dayz-add-server\add_server.py chernarus
```

Both should print the `/dayz-init` pointer and exit 2.

- [ ] **Step 4: Restore your test cache**

Same as Task 13 step 4.

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/dayz-launch-test/launch.py .claude/skills/dayz-add-server/add_server.py
git commit -m "feat(dayz-{launch-test,add-server}): point at /dayz-init when no project cached"
```

---

## Task 15: README rewrite — quickstart leads with /dayz-init

**Files:**
- Modify: `README.md` (the "Quick start" section, currently lines 7-39)

- [ ] **Step 1: Read the current Quick start block**

Run: `grep -n "Quick start\|Then, from your mod\|/dayz-preflight\|/dayz-set-project" README.md`

Confirm the section spans roughly lines 7-39.

- [ ] **Step 2: Replace the Quick start block**

Find:

```markdown
## Quick start

**Install via Claude Code plugin:**

```text
/plugin marketplace add DayZ-n-Chill/Agentic-Z
/plugin install agentic-z@dayz-n-chill
```

Skills appear with the `agentic-z:` prefix (`/agentic-z:dayz-build-pbo`). The `dayz-rag` MCP server registers automatically.

Then, from your mod project in Claude Code:

```text
/dayz-preflight                                      # verify env (P:\ mounted, Tools installed, vanilla data extracted)
/dayz-set-project C:\Users\you\repos\MyMod           # point skills at your mod repo
/dayz-new-mod MyMod                                  # scaffold mod skeleton + P:\MyMod\ junction
/dayz-add-server chernarus                           # set up a test server instance under <project>/.server/
/dayz-build-pbo MyMod                               # pack and deploy to P:\Mods\@MyMod\Addons\
/dayz-launch-test MyMod --server chernarus          # local diag server + client, mod loaded
```

Or use `/dayz-import-mod --source <path>` to register an existing mod repo instead of scaffolding a new one.
```

Replace with:

```markdown
## Quick start

**Install via Claude Code plugin:**

```text
/plugin marketplace add DayZ-n-Chill/Agentic-Z
/plugin install agentic-z@dayz-n-chill
```

Skills appear with the `agentic-z:` prefix (`/agentic-z:dayz-build-pbo`). The `dayz-rag` MCP server registers automatically.

Then, from your mod project in Claude Code:

```text
/dayz-init
```

That's it. The wizard asks what you're doing (new mod or import), where to scaffold, what map to test on, and whether to build/launch. It auto-fixes what it can (`P:\` mount, junctions) and surfaces steam:// links for the rest. Every run after the first drops you into a mission-control hub for the cached project.

Power users can still call individual skills directly: `/dayz-preflight`, `/dayz-build-pbo`, `/dayz-launch-test`, etc. See the full slash-command list further down.
```

- [ ] **Step 3: Verify the rewrite**

Run: `grep -A3 "Quick start" README.md`

Confirm the new block reads cleanly and shows `/dayz-init` as the only post-install command.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs(readme): lead Quick start with /dayz-init wizard"
```

---

## Task 16: Plugin marketplace description mentions /dayz-init

**Files:**
- Modify: `.claude-plugin/plugin.json` OR `marketplace.json` (whichever exists at repo root or under `.claude-plugin/`)

- [ ] **Step 1: Locate the manifest**

Run: `find .claude-plugin -maxdepth 2 -name "*.json" 2>nul` or `dir .claude-plugin\*.json /s`

If neither exists, check the repo root: `dir *.json`.

- [ ] **Step 2: Open the manifest and find the description field**

Look for keys like `description`, `summary`, `tagline`, or similar.

- [ ] **Step 3: Update the description**

Existing description likely focuses on the agent stack. Append or rewrite to mention the entry command. Example replacement:

```json
"description": "AI agent stack for DayZ modding. After install, run /dayz-init for a guided setup wizard that takes you from empty repo to mod-loaded-in-DayZ. Includes 11 specialist agents, 25 slash skills, and a local RAG over vanilla source plus the Bohemia community wiki."
```

If multiple description fields exist (short + long), update both consistently.

- [ ] **Step 4: Commit**

```bash
git add .claude-plugin/plugin.json
git commit -m "docs(plugin): mention /dayz-init as entry point in marketplace description"
```

(Adjust the path in the `git add` command to match the actual filename you found in step 1.)

---

## Task 17: Final integration smoke + sync-skills

This task validates the end-to-end experience as a future user would see it.

- [ ] **Step 1: Sync the new skill to all agent CLIs**

```cmd
python .claude\skills\sync-skills\sync.py
```

Expected: prints lines linking `dayz-init` into Claude Code, Codex, and Gemini home dirs.

- [ ] **Step 2: Confirm slash discovery**

In a fresh Claude Code session, type `/dayz-` and confirm `/dayz-init` appears in the autocomplete list.

- [ ] **Step 3: Run the wizard cold against a fresh empty directory**

(Same procedure as Task 9 step 2, but with a brand new directory and no prior cache.)

Expected behavior:
- env block reports any real prereqs missing on this machine
- wizard completes without error
- hub appears with the rich status block

- [ ] **Step 4: Run the gated skills with the cache wiped**

```cmd
del %USERPROFILE%\.claude\local-memory\dayz-current-project.txt
python .claude\skills\dayz-build-pbo\build.py Foo
python .claude\skills\dayz-launch-test\launch.py Foo
python .claude\skills\dayz-add-server\add_server.py chernarus
```

All three should print the `/dayz-init` pointer line and exit 2.

- [ ] **Step 5: Commit any sync-skills artefacts**

```bash
git add -A
git commit -m "chore(sync-skills): regenerate links after adding /dayz-init"
```

(Skip if there are no changes.)

- [ ] **Step 6: Push the branch**

```bash
git push -u origin feature/dayz-init-wizard
```

---

## Summary

After Task 17, the branch contains:

- A new `dayz-init` skill (10 files: SKILL.md, init.py, 6 helper modules, 4 test files).
- 3 modified existing skills with `/dayz-init` pointers (`dayz-build-pbo`, `dayz-launch-test`, `dayz-add-server`).
- A rewritten README quickstart.
- An updated plugin marketplace description.

The wizard handles new and import paths, opt-in server / build / launch, env autofix, hard-prereq exit, mid-execution failure, and re-run resume. The hub provides 11 actions, all wrapping existing skills.

Out of scope for this branch (per the spec):
- Per-skill output formatting polish.
- Agent-definition changes.
- Any RAG or wiki work.
- Website changes.

Future follow-ups:
- Decide whether to rename `/dayz-init` after dogfooding.
- Decide what (if anything) goes in the state file beyond `rag_choice` and `last_intent`.
- Confirm `switch project`'s P:\Mods\@*\ scan stays fast at scale.
