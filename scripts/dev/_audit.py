"""One-off bug-hunt audit of the develop branch state."""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

# Force UTF-8 so this script doesn't crash on box-drawing or curly chars
# in scanned files when run under cp1252 default Windows console.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

REPO = Path(__file__).resolve().parents[2]


def _norm(rel: str) -> Path:
    """Resolve a './.claude/...' style path from plugin.json relative to REPO."""
    return REPO / Path(rel.removeprefix("./"))


def section(title: str) -> None:
    print(f"\n=== {title} ===")


def check_plugin_skills():
    section("plugin.json skills exist on disk")
    data = json.loads((REPO / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    missing = []
    for skill_path in data.get("skills", []):
        p = _norm(skill_path)
        if not p.is_dir():
            missing.append(skill_path)
        elif not (p / "SKILL.md").exists():
            missing.append(f"{skill_path} (no SKILL.md)")
    print("OK" if not missing else "MISSING:")
    for m in missing:
        print(f"  {m}")


def check_plugin_agents():
    section("plugin.json agents exist on disk")
    data = json.loads((REPO / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    missing = []
    for agent_path in data.get("agents", []):
        p = _norm(agent_path)
        if not p.is_file():
            missing.append(agent_path)
    print("OK" if not missing else "MISSING:")
    for m in missing:
        print(f"  {m}")


def check_plugin_mcp():
    section("plugin.json mcp server paths")
    data = json.loads((REPO / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    for name, cfg in data.get("mcpServers", {}).items():
        for arg in cfg.get("args", []):
            if "CLAUDE_PLUGIN_ROOT" in arg:
                rel = re.sub(r"\$\{CLAUDE_PLUGIN_ROOT\}/", "", arg)
                p = REPO / Path(rel)
                print(f"  {name}: {rel}  exists={p.exists()}")


def check_settings_hooks():
    section("settings.json hooks point at real files")
    data = json.loads((REPO / ".claude" / "settings.json").read_text(encoding="utf-8"))
    for hook_type, entries in data.get("hooks", {}).items():
        for entry in entries:
            for h in entry.get("hooks", []):
                cmd = h.get("command", "")
                for m in re.finditer(r'\$CLAUDE_PROJECT_DIR[/\\]([^\s"\']+)', cmd):
                    rel = m.group(1).rstrip('"\'')
                    p = REPO / Path(rel)
                    print(f"  {hook_type}: {rel}  exists={p.exists()}")


def check_unregistered_skills():
    section("skills on disk but NOT in plugin.json")
    data = json.loads((REPO / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    registered = set()
    for s in data.get("skills", []):
        registered.add(s.removeprefix("./").replace("\\", "/").rstrip("/"))
    on_disk = set()
    for p in (REPO / ".claude" / "skills").iterdir():
        if p.is_dir() and not p.name.startswith("_"):
            on_disk.add(f".claude/skills/{p.name}")
    not_registered = on_disk - registered
    print("(intentional template-author skills won't be in plugin.json)")
    for s in sorted(not_registered):
        print(f"  {s}")


def check_dead_skill_refs_in_docs():
    section("docs reference SLASH-COMMANDS that no longer exist")
    on_disk_skills = set(p.name for p in (REPO / ".claude" / "skills").iterdir() if p.is_dir())
    # Agents share the `/<name>` slug pattern with skills (e.g.
    # `/dayz-mod-debugger` is an agent, not a skill). Treat both as
    # "exists" so we don't false-positive on agent mentions.
    on_disk_agents = set(p.stem for p in (REPO / ".claude" / "agents").glob("*.md"))
    on_disk = on_disk_skills | on_disk_agents

    # Names that look like `/dayz-foo` but are NOT skills/agents. Add
    # known false-positives here to keep the report actionable.
    KNOWN_NON_SKILLS = {
        # MCP server name (referenced as /dayz-rag in URLs/configs)
        "dayz-rag",
        # Doc filenames (referenced as /dayz-modding etc. in markdown links)
        "dayz-modding",
        "dayz-conventions",
        # Cache / config filenames in .claude/local-memory/
        "dayz-active-scope",
        "dayz-author",
        "dayz-client-display",
        "dayz-current-project",
        "dayz-wiki-cookie",
        "dayz-work-drive",
        # Inline example agent names used in agent descriptions
        "dayz-script-wrap",
    }

    # Tighter heuristic: only match `/dayz-foo` (the slash-command form),
    # which is unambiguously a skill reference vs. a file basename.
    slash_pattern = re.compile(r"/(dayz-[a-z][a-z0-9-]+|sync-skills|agentic-z-update|clean-repo|docs-sync)\b")
    user_docs = list(REPO.glob("README.md")) + list(REPO.glob("CONTRIBUTING.md")) + \
                list((REPO / "docs").rglob("*.md")) + list((REPO / ".claude" / "skills").rglob("SKILL.md")) + \
                list((REPO / ".claude" / "agents").glob("*.md"))
    seen = {}
    for doc in user_docs:
        s = str(doc)
        if "superpowers/plans" in s or "superpowers/specs" in s or "release-notes" in s:
            continue  # historical
        try:
            text = doc.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for m in slash_pattern.finditer(text):
            name = m.group(1)
            if name in on_disk or name in KNOWN_NON_SKILLS:
                continue
            seen.setdefault(name, set()).add(str(doc.relative_to(REPO)))

    if not seen:
        print("OK")
    else:
        print("DEAD SLASH REFS (skill is referenced as /name but no .claude/skills/name/ folder):")
        for name, files in sorted(seen.items()):
            print(f"  /{name}:")
            for f in sorted(files):
                print(f"    - {f}")


def check_workspace_path_refs():
    section("stale workspace/<X>/ assumptions in user-facing files")
    # The wizard architecture caches an arbitrary project path; some skills
    # may still hardcode workspace/ as an assumption rather than a default.
    pattern = re.compile(r"workspace/<")
    user_facing = list(REPO.glob("README.md")) + list(REPO.glob("CONTRIBUTING.md")) + \
                  list((REPO / ".claude" / "skills").rglob("SKILL.md")) + \
                  list((REPO / ".claude" / "agents").glob("*.md"))
    hits = []
    for f in user_facing:
        text = f.read_text(encoding="utf-8", errors="replace")
        for line_num, line in enumerate(text.splitlines(), 1):
            if pattern.search(line):
                hits.append((str(f.relative_to(REPO)), line_num, line.strip()[:120]))
    if not hits:
        print("OK")
    else:
        print(f"({len(hits)} mentions; not necessarily bugs, but worth eyeballing)")
        for f, n, snippet in hits[:15]:
            print(f"  {f}:{n}  {snippet}")


def check_unregistered_agents():
    section("agents on disk vs plugin.json")
    data = json.loads((REPO / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    registered = set(a.removeprefix("./") for a in data.get("agents", []))
    on_disk = set(f".claude/agents/{p.name}" for p in (REPO / ".claude" / "agents").glob("*.md"))
    missing = on_disk - registered
    ghost = registered - on_disk
    if missing:
        print("On disk but NOT in plugin.json:")
        for a in sorted(missing):
            print(f"  {a}")
    if ghost:
        print("Ghost in plugin.json (not on disk):")
        for a in sorted(ghost):
            print(f"  {a}")
    if not (missing or ghost):
        print("OK")


def main():
    check_plugin_skills()
    check_plugin_agents()
    check_plugin_mcp()
    check_settings_hooks()
    check_unregistered_skills()
    check_unregistered_agents()
    check_dead_skill_refs_in_docs()


if __name__ == "__main__":
    main()
