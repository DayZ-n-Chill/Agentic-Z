"""UserPromptSubmit hook: spot what the user pasted and point Claude at the right workflow.

  - DayZ log lines (crash log, RPT, script.log): triaged right here against
    dayz-gate's known errors; only the new lines are for dayz-mod-debugger.
  - A types.xml chunk (<type name=...> blocks): checked here, then merged with
    /dayz-edit-types --merge.
  - A Figma link: the Figma pipeline.
  - A GitHub link: /dayz-import-mod --source <link>. A repo link is cloned
    into workspace/<Name>/; a tree link to a subfolder is cloned into
    .imports/<owner>__<repo>__<branch>/ with workspace/<Name> linked to the
    subfolder.
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

SKILLS = Path(__file__).resolve().parents[1] / "skills"
TRIAGE = SKILLS / "dayz-gate" / "triage.py"
TYPES_EDIT = SKILLS / "dayz-edit-types" / "types_edit.py"

MAX_PROMPT = 2_000_000  # characters scanned; a bigger paste is cut
MAX_LINES = 20  # known or new lines listed in the context
MAX_CONTEXT = 9000  # characters of context added

WORKSHOP_RE = re.compile(
    r"(?i)(?:https?://)?steamcommunity\.com/(?:sharedfiles|workshop)/filedetails/?\?\S*|steam://url/CommunityFilePage/\d+"
)
# Only a repo or tree link is a mod to import. The first lookahead skips
# GitHub's own pages (github.com/orgs/..., /features/..., /trending/...). The
# second keeps the repo name whole; the third skips pull requests, issues,
# files, the wiki, settings and the like. Every segment after /tree/ is kept,
# since it may be a branch with slashes (feature/x) or a branch plus a
# subfolder (main/MyMod); import_mod.py's resolve_branch asks the remote which
# part is the branch. The lookbehind keeps subdomains such as gist. and raw.
# from matching.
GITHUB_RE = re.compile(
    r"(?i)(?<![\w.-])(?:https?://)?(?:www\.)?github\.com/"
    r"(?!(?:orgs|settings|sponsors|topics|marketplace|notifications|apps|users|features|trending|collections"
    r"|explore|enterprise|solutions|resources|customer-stories|readme|events|codespaces|search|login|about"
    r"|advisories|logout|signup|join|pricing|site|contact|new|account|dashboard|watching|stars|team"
    r"|security|sessions|password_reset|organizations|github-copilot|copilot|premium-support|education)/)"
    r"[\w.-]+/[\w.-]*[\w-](?![\w-]|\.[\w-])"
    r"(?!/(?:pulls?|issues|blob|commits?|releases|actions|compare|discussions|wiki|settings|projects"
    r"|security|tags|branches|milestones|labels)\b)"
    r"(?:/tree/[\w.-]*[\w-](?:/[\w.-]*[\w-])*)?"
)
# import_mod.py's mod name rule (dayz-new-mod's NAME_PATTERN). A link whose
# derived name fails it gets a ready --name in the suggested command.
MOD_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,63}$")
FIGMA_RE = re.compile(r"(?i)\bfigma\.com/(?:file|design|proto|board)/\S+")
TYPE_CHUNK_RE = re.compile(r"<type\s+name\s*=")
# A pasted entry, not a type named in prose: a closing </type>, a self-closing
# <type name="X"/>, or an opening tag followed by a child tag.
TYPE_ENTRY_RE = re.compile(r"</type>|<type\s+name\s*=[^<>]*(?:/>|>\s*<)")
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
    "import it with /dayz-import-mod --source {link}{name_arg}. {where} It then links P:\\<Name> and checks "
    "the standard pieces."
)
# Where import_mod.py puts each kind of link.
REPO_WHERE = "It clones the repo into workspace\\<Name>\\."
TREE_WHERE = (
    "It asks the remote (git ls-remote) which part of the tree path is the branch. If the whole path is the "
    "branch, it clones the repo into workspace\\<Name>\\. If a subfolder follows the branch, it clones the whole "
    "repo into .imports\\<owner>__<repo>__<branch>\\ and links workspace\\<Name> to that subfolder."
)
REPO_NAME_NOTE = " The --name comes from the repo, so it fits whichever part turns out to be the branch."
SCREENSHOT_CONTEXT = (
    "Agentic-Z paste-in: the prompt has a screenshot. If it shows a DayZ bug, name what is wrong on screen and "
    "route by it: a widget, menu, HUD or text problem to dayz-ui-specialist; a wrong, missing or stretched "
    "texture or material to dayz-asset-specialist; an error message or wrong behavior to dayz-script-specialist. "
    "Error text on screen can be triaged first with triage.py --text."
)


def tree_path(link: str) -> tuple[str, list[str]]:
    """The repo name and the segments after /tree/ ([] for a repo link)."""
    path = re.sub(r"(?i)^(?:https?://)?(?:www\.)?github\.com/", "", link).rstrip("/").split("/")
    repo = re.sub(r"(?i)\.git$", "", path[1])
    return repo, path[3:] if len(path) > 3 and path[2].lower() == "tree" else []


def name_arg(link: str) -> str:
    """' --name <Valid>' when a name import_mod.py could derive from the link
    fails its rule (DayZ-Expansion has a hyphen), else ''. A repo link or a
    one-segment tree link is named after the repo. A tree path of two or more
    segments is ambiguous: import_mod.py asks the remote which part is the
    branch and names the mod after the repo when the whole path is a branch
    (dev/x), or after the last segment when a subfolder follows (main/MyMod).
    The hook cannot ask, so when either name fails the rule it suggests the
    repo name cleaned to the rule, which is right for both readings."""
    repo, tree = tree_path(link)
    names = [repo] + ([tree[-1]] if len(tree) >= 2 else [])
    if all(MOD_NAME_RE.match(n) for n in names):
        return ""
    valid = re.sub(r"^[^A-Za-z]+", "", re.sub(r"[^A-Za-z0-9_]", "", repo))[:64] or "MyMod"
    return f" --name {valid}"


def github_context(link: str) -> str:
    arg = name_arg(link)
    if len(tree_path(link)[1]) >= 2:
        where = TREE_WHERE + (REPO_NAME_NOTE if arg else "")
    else:
        where = REPO_WHERE
    return GITHUB_CONTEXT.format(link=link, name_arg=arg, where=where)


def build_context(prompt: str, project: Path) -> Optional[str]:
    prompt = prompt[:MAX_PROMPT]
    parts = []
    workshop = WORKSHOP_RE.search(prompt)
    if workshop:
        parts.append(WORKSHOP_CONTEXT.format(link=workshop.group(0)))
    github = GITHUB_RE.search(prompt)
    if github:
        parts.append(github_context(github.group(0)))
    if FIGMA_RE.search(prompt):
        parts.append(FIGMA_CONTEXT)
    # The types and log detectors load other modules; one failing must not drop the rest.
    if TYPE_ENTRY_RE.search(prompt) and TYPE_CHUNK_RE.search(prompt):
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
    copy then steps aside so the project copy runs alone. It steps aside only
    when the project copy both exists and is wired in the project's settings,
    so a clone that keeps hooks/ but drops the wiring still gets the plugin copy.
    """
    project = os.environ.get("CLAUDE_PROJECT_DIR")
    if not project:
        return False
    here = Path(__file__).resolve()
    root = Path(project).resolve()
    if here.is_relative_to(root):
        return False
    if not (root / "hooks" / here.name).is_file():
        return False
    return any(_wires(root / ".claude" / name, here.name) for name in ("settings.json", "settings.local.json"))


def _wires(settings: Path, hook: str) -> bool:
    """True when a settings file has a hook command that runs the project's hooks/<hook>."""
    try:
        config = json.loads(settings.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    events = config.get("hooks") if isinstance(config, dict) else None
    for groups in (events.values() if isinstance(events, dict) else []):
        for group in groups if isinstance(groups, list) else []:
            for entry in (group.get("hooks") or []) if isinstance(group, dict) else []:
                command = str(entry.get("command") or "") if isinstance(entry, dict) else ""
                if f"hooks/{hook}" in command.replace("\\", "/") and "CLAUDE_PLUGIN_ROOT" not in command:
                    return True
    return False


def main() -> int:
    try:
        shadowed = shadowed_by_project()
    except Exception:  # a broken shadow check must not switch this copy off; run it instead
        shadowed = False
    if shadowed:
        return 0
    try:
        data = json.loads(sys.stdin.buffer.read().decode("utf-8", "replace") or "{}")
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
