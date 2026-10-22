"""UserPromptSubmit hook: spot what the user pasted and point Claude at the right workflow.

  - DayZ log lines (crash log, RPT, script.log): triaged right here against
    dayz-gate's known errors; only the new lines are for dayz-mod-debugger.
  - A types.xml chunk (<type name=...> blocks): checked here, then merged with
    /dayz-edit-types --merge.
  - A Figma link: the Figma pipeline.
  - A GitHub link: /dayz-import-mod --source <link> clones it into workspace/.
  - A Steam Workshop link: refused (packed, binarized, often protected content).
  - A screenshot: a short rule picks the ui, asset or script specialist.

The hook only adds context; it never blocks a prompt. Cheap regexes run
first, and the triage and types modules are loaded only when a paste needs
them. Any error exits silently, so a hook bug never gets in the way.
Output format: https://code.claude.com/docs/en/hooks#userpromptsubmit
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
from pathlib import Path
from typing import Optional

SKILLS = Path(__file__).resolve().parents[1] / ".claude" / "skills"
TRIAGE = SKILLS / "dayz-gate" / "triage.py"
TYPES_EDIT = SKILLS / "dayz-edit-types" / "types_edit.py"

MAX_PROMPT = 2_000_000  # characters scanned; a bigger paste is cut
MAX_LINES = 20  # known or new lines listed in the context
MAX_CONTEXT = 9000  # characters of context added

WORKSHOP_RE = re.compile(
    r"(?i)(?:https?://)?steamcommunity\.com/(?:sharedfiles|workshop)/filedetails/?\?\S*|steam://url/CommunityFilePage/\d+"
)
# Only a repo or tree link is a mod to import. The first lookahead keeps the
# repo name whole; the second skips pull requests, issues, files and the like.
GITHUB_RE = re.compile(
    r"(?i)(?:https?://)?(?:www\.)?github\.com/[\w.-]+/[\w.-]*[\w-](?![\w-]|\.[\w-])"
    r"(?!/(?:pulls?|issues|blob|commits?|releases|actions|compare|discussions)\b)"
    r"(?:/tree/[\w.-]*[\w-])?"
)
FIGMA_RE = re.compile(r"(?i)\bfigma\.com/(?:file|design|proto|board)/\S+")
TYPE_CHUNK_RE = re.compile(r"<type\s+name\s*=")
IMAGE_RE = re.compile(r"\[Image #\d+\]")
SCREENSHOT_FILE_RE = re.compile(r"(?i)\bscreen\s*shot.*\.(?:png|jpe?g|bmp|webp)\b|\.(?:png|jpe?g|bmp|webp)\b.*\bscreen\s*shot")
# Error lines the engine writes; the same families triage.py classifies.
LOG_RE = re.compile(
    r"(?i)access violation|unhandled exception|exception code|\bSCRIPT\s+\(E\)|can't compile \"\w+\" script module"
    r"|NULL pointer to instance|\.c\(\d+\):|cannot load texture|cannot open object|\bNo entry '|0x00020005"
    r"|mission script has no main function|^\[FAIL\]",
    re.MULTILINE,
)


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def log_context(prompt: str, project: Path) -> str:
    triage = _load("agentic_z_paste_triage", TRIAGE)
    learned = triage.learned_path(project)
    known = triage.load_known(triage.KNOWN_ERRORS, learned if learned.is_file() else None)
    results = triage.triage_text(prompt, known)
    if not results:
        return ""
    known_rows = [r for r in results if r["status"] == "known"]
    new_rows = [r for r in results if r["status"] == "new"]
    out = [f"Agentic-Z paste-in: the prompt holds DayZ log lines. Triage (dayz-gate triage.py) found "
           f"{len(known_rows)} known and {len(new_rows)} new error(s)."]
    for r in known_rows[:MAX_LINES]:
        out.append(f"- known {r['id']} (owner {r['owner_agent']}, seen {r['count']}x): {r['text'][:300]}")
        out.append(f"  meaning: {r['meaning']} fix: {r['fix']}")
    for r in new_rows[:MAX_LINES]:
        out.append(f"- new (line {r['line']}, seen {r['count']}x): {r['text'][:300]}")
    if len(known_rows) > MAX_LINES or len(new_rows) > MAX_LINES:
        out.append(f"(more lines than listed; run triage.py --stdin --json on the paste for all of them)")
    if known_rows:
        out.append("Give the user the cause and fix of each known error and hand the fix to its owner.")
    if new_rows:
        out.append("Dispatch dayz-mod-debugger with only the new lines above and the log around them. "
                   "Do not send it the known ones.")
    else:
        out.append("Every error line is a known error, so dayz-mod-debugger is not needed.")
    return "\n".join(out)


def types_context(prompt: str) -> str:
    te = _load("agentic_z_paste_types", TYPES_EDIT)
    starts = [i for i in (prompt.find("<?xml"), prompt.find("<types"), TYPE_CHUNK_RE.search(prompt).start()) if i >= 0]
    start = min(starts)
    # End at the last closing tag, not the last '>': prose after the paste may hold one ("merge -> chernarus").
    ends = [prompt.rfind(tag) + len(tag) for tag in ("</types>", "</type>") if tag in prompt]
    if not ends:  # only self-closing entries: <type name="X"/>
        last = list(TYPE_CHUNK_RE.finditer(prompt))[-1].start()
        close = prompt.find("/>", last)
        ends = [close + 2 if close >= 0 else len(prompt)]
    end = max(ends)
    try:
        chunk = te.parse_chunk(prompt[start:end])
    except Exception as e:  # ParseError, or text around the chunk
        return ("Agentic-Z paste-in: the prompt holds types.xml <type> entries, but they do not parse as XML "
                f"({e}). Show the user the problem, or save just the <type> blocks and run /dayz-edit-types "
                "<types.xml> --merge <chunk> --dry-run, which reports the same.")
    problems = []
    for el in chunk:
        errors, _warnings = te.validate_type(el)
        problems += [f"{el.get('name') or '(no name)'}: {e}" for e in errors]
    out = [f"Agentic-Z paste-in: the prompt holds {len(chunk)} types.xml <type> entr"
           f"{'y' if len(chunk) == 1 else 'ies'}."]
    if problems:
        out.append("These must be fixed before a merge (the merge refuses the whole chunk otherwise):")
        out += [f"- {p}" for p in problems[:MAX_LINES]]
    out.append("Merge them with /dayz-edit-types: save the chunk to a file and run types_edit.py <types.xml> "
               "--merge <chunk> --dry-run, show the user the result, then run it without --dry-run. It checks "
               "every entry, backs the file up and merges in one write. If the target file is not named, ask "
               "which mission (usually .server/<instance>/mission/db/types.xml).")
    return "\n".join(out)


FIGMA_CONTEXT = (
    "Agentic-Z paste-in: the prompt holds a Figma link. Run the Figma pipeline in order: figma-node-normalizer, "
    "then figma-to-dayz-layout, then dayz-layout-validator in gate mode. Do not write the .layout by hand."
)
WORKSHOP_CONTEXT = (
    "Agentic-Z paste-in: the prompt holds a Steam Workshop link ({link}). Do not download, unpack or import it. "
    "Tell the user that a Workshop item holds the packed mod (PBOs with binarized models and configs, often "
    "signed or protected by its author), so there is no source in it to work on; /dayz-import-mod refuses it. "
    "If the mod is theirs, import its source folder or GitHub repo instead; if not, they should ask the author "
    "for the source and permission."
)
GITHUB_CONTEXT = (
    "Agentic-Z paste-in: the prompt holds a GitHub link ({link}). If it is a DayZ mod the user wants to work on, "
    "import it with /dayz-import-mod --source {link} (clones it into workspace\\, links P:\\ and checks the "
    "standard pieces)."
)
SCREENSHOT_CONTEXT = (
    "Agentic-Z paste-in: the prompt has a screenshot. If it shows a DayZ bug, name what is wrong on screen and "
    "route by it: a widget, menu, HUD or text problem to dayz-ui-specialist; a wrong, missing or stretched "
    "texture or material to dayz-asset-specialist; an error message or wrong behavior to dayz-script-specialist. "
    "Error text on screen can be triaged first with triage.py --text."
)


def build_context(prompt: str, project: Path) -> Optional[str]:
    prompt = prompt[:MAX_PROMPT]
    parts = []
    workshop = WORKSHOP_RE.search(prompt)
    if workshop:
        parts.append(WORKSHOP_CONTEXT.format(link=workshop.group(0)))
    github = GITHUB_RE.search(prompt)
    if github:
        parts.append(GITHUB_CONTEXT.format(link=github.group(0)))
    if FIGMA_RE.search(prompt):
        parts.append(FIGMA_CONTEXT)
    # The types and log detectors load other modules; one failing must not drop the rest.
    if TYPE_CHUNK_RE.search(prompt):
        try:
            parts.append(types_context(prompt))
        except Exception:
            pass
    if LOG_RE.search(prompt):
        try:
            parts.append(log_context(prompt, project))
        except Exception:
            pass
    if IMAGE_RE.search(prompt) or SCREENSHOT_FILE_RE.search(prompt):
        parts.append(SCREENSHOT_CONTEXT)
    text = "\n\n".join(p for p in parts if p)
    return text[:MAX_CONTEXT] or None


def shadowed_by_project() -> bool:
    """True when this is the plugin copy and the project has its own copy of the hook.

    A clone with the agentic-z plugin enabled wires each hook twice: once from
    .claude/settings.json and once from the plugin's hooks.json. The plugin
    copy then steps aside so the project copy runs alone.
    """
    project = os.environ.get("CLAUDE_PROJECT_DIR")
    if not project:
        return False
    here = Path(__file__).resolve()
    root = Path(project).resolve()
    if here.is_relative_to(root):
        return False
    return (root / "hooks" / here.name).is_file()


def main() -> int:
    if shadowed_by_project():
        return 0
    try:
        data = json.loads(sys.stdin.read() or "{}")
        prompt = data.get("prompt") or ""
        project = Path(os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or os.getcwd())
        context = build_context(prompt, project) if prompt else None
    except Exception:  # never stand between the user and their prompt
        return 0
    if context:
        print(json.dumps({
            "hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": context}
        }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
