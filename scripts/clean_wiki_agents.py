"""Regenerate wiki/docs/agents/*.md mirrors from the canonical .claude/agents/*.md.

The canonical agent definitions stuff their description, examples, and
commentary into the YAML frontmatter as a JSON-escaped multiline string with
embedded <example>...<commentary>...</commentary>...</example> tags. The
previous mirror logic produced garbled output (backslash line endings, raw
escaped tags, leaked memory-protocol prose). This script does a clean pass:

  - Reads the canonical source.
  - Parses frontmatter properly with PyYAML (falls back to manual parse).
  - Builds an "Overview" section from the description (un-escaping \\n).
  - Renders each <example> block as a styled blockquote with bold speaker labels.
  - Renders <commentary> as an italic note line.
  - Keeps the body content but cuts the agent-runtime memory-protocol section.
  - Cleans frontmatter to drop the long description (it's now in the Overview).

Idempotent: re-running produces the same output.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CANONICAL_DIR = REPO / ".claude" / "agents"
WIKI_DIR = REPO / "wiki" / "docs" / "agents"

EXAMPLE_RE = re.compile(r"<example>\s*(.*?)\s*</example>", re.DOTALL)
COMMENTARY_RE = re.compile(r"<commentary>\s*(.*?)\s*</commentary>", re.DOTALL)


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Naive frontmatter split. Returns (fields, body)."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    fm = text[3:end].strip()
    body = text[end + 4 :].lstrip("\n")
    fields: dict[str, str] = {}
    current_key: str | None = None
    current_lines: list[str] = []
    for line in fm.splitlines():
        m = re.match(r'^([a-zA-Z_][\w-]*)\s*:\s*(.*)$', line)
        if m and not line.startswith(" "):
            if current_key:
                fields[current_key] = "\n".join(current_lines).strip()
            current_key = m.group(1)
            current_lines = [m.group(2)]
        else:
            current_lines.append(line)
    if current_key:
        fields[current_key] = "\n".join(current_lines).strip()
    # Strip surrounding quotes from values
    for k, v in fields.items():
        v = v.strip()
        if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
            v = v[1:-1]
        fields[k] = v
    return fields, body


def unescape_description(s: str) -> str:
    """Convert YAML-escape sequences (\\\\n in the file) to real newlines.

    The canonical agent files store the description as a YAML double-quoted
    string with literal \\n backslash-escape pairs (so the YAML reader sees
    \\n meaning a real newline). When we read the file as raw text without
    YAML parsing, we see the literal pair `\\n` (three chars: \\, \\, n).
    """
    # Some agent files store \\n (3 chars: \, \, n), others store just \n
    # (2 chars: \, n). Handle both. Do 3-char pattern first so it can't be
    # partially eaten by the 2-char pattern.
    return (
        s.replace(r"\\n", "\n")  # \\n (3 chars) → newline
        .replace(r"\n", "\n")    # \n (2 chars) → newline
        .replace(r'\"', '"')     # \" (2 chars) → "
    )


def render_example(body: str) -> str:
    """Turn the inside of an <example> block into a styled markdown chunk."""
    body = body.strip()
    commentary = ""
    m = COMMENTARY_RE.search(body)
    if m:
        commentary = m.group(1).strip()
        body = COMMENTARY_RE.sub("", body).strip()

    quote_lines: list[str] = []
    for line in body.splitlines():
        line = line.rstrip()
        if not line.strip():
            continue
        if line.lower().startswith("context:"):
            line = "**Context:** " + line.split(":", 1)[1].strip()
        elif line.lower().startswith("user:"):
            line = "**User:** " + line.split(":", 1)[1].strip()
        elif line.lower().startswith("assistant:"):
            line = "**Assistant:** " + line.split(":", 1)[1].strip()
        quote_lines.append(f"> {line}")

    out = ["> **Example**", ">"] + quote_lines
    if commentary:
        out.append("")
        out.append(f"*{commentary}*")
    return "\n".join(out)


def description_to_markdown(description: str) -> str:
    """Strip <example> tags from description, render examples as MD blockquotes.

    The description may also contain backticked references to <example> /
    <commentary> tags as part of describing the agent's behavior. Those must
    be preserved as literal code spans, not consumed by the example regex.
    """
    description = unescape_description(description)

    # Protect backticked references so the regex doesn't eat them.
    sentinels = [
        ("`<example>`", "\x00BTKEX_OPEN\x00"),
        ("`</example>`", "\x00BTKEX_CLOSE\x00"),
        ("`<commentary>`", "\x00BTKCM_OPEN\x00"),
        ("`</commentary>`", "\x00BTKCM_CLOSE\x00"),
    ]
    for needle, sentinel in sentinels:
        description = description.replace(needle, sentinel)

    examples: list[str] = []

    def _collect(m: re.Match) -> str:
        examples.append(render_example(m.group(1)))
        return "<<<EXAMPLE_PLACEHOLDER>>>"

    intro = EXAMPLE_RE.sub(_collect, description).strip()
    # Trim a trailing "Examples:" or similar from the intro
    intro = re.sub(r"\n*Examples?:\s*$", "", intro, flags=re.IGNORECASE).strip()
    intro = intro.replace("<<<EXAMPLE_PLACEHOLDER>>>", "").strip()
    intro = re.sub(r"\n{3,}", "\n\n", intro).strip()

    parts: list[str] = []
    if intro:
        parts.append(intro)
    parts.extend(examples)
    out = "\n\n".join(parts)

    # Restore backticked tag references.
    for needle, sentinel in sentinels:
        out = out.replace(sentinel, needle)

    # Safety net: any stray un-backticked <example> / <commentary> tag that
    # survived (because of a malformed source) gets backticked here so MDX
    # doesn't try to parse it as JSX and fail the build.
    out = re.sub(r"</?example>", lambda m: f"`{m.group(0)}`", out)
    out = re.sub(r"</?commentary>", lambda m: f"`{m.group(0)}`", out)

    return out


def strip_memory_protocol(body: str) -> str:
    """Cut the agent-runtime memory protocol from the body."""
    body = re.sub(
        r"\n\*\*Update your agent memory\*\*.*\Z", "", body, flags=re.DOTALL
    )
    body = re.sub(r"\n#\s+Persistent Agent Memory\b.*\Z", "", body, flags=re.DOTALL)
    return body.rstrip() + "\n"


def build_badges(model: str, color: str) -> str:
    """Render a row of badges (plain HTML so it works in .md files).
    Uses Docusaurus's built-in `badge` Infima classes plus a per-color span."""
    if not model and not color:
        return ""
    parts = ['<p class="agent-badges">']
    parts.append('<span class="badge badge--primary">Agent</span>')
    if model:
        parts.append(f'<span class="badge badge--secondary">{model}</span>')
    if color:
        parts.append(f'<span class="agent-color-badge agent-color-badge--{color}">{color}</span>')
    parts.append("</p>")
    return "".join(parts)


def build_wiki_doc(canonical_path: Path) -> str:
    raw = canonical_path.read_text(encoding="utf-8")
    fields, body = parse_frontmatter(raw)
    description = fields.pop("description", "")

    model = fields.get("model", "")
    color = fields.get("color", "")

    # Compose new frontmatter — drop the long description, keep meta
    fm_lines = ["---"]
    for key in ("name", "model", "color", "memory"):
        if key in fields and fields[key]:
            fm_lines.append(f'{key}: "{fields[key]}"' if key == "name" else f"{key}: {fields[key]}")
    fm_lines.append("---")
    fm = "\n".join(fm_lines)

    badges = build_badges(model, color)
    overview_md = description_to_markdown(description) if description else ""
    body_clean = strip_memory_protocol(body)

    chunks = [fm, ""]
    if badges:
        chunks.append(badges)
        chunks.append("")
    if overview_md:
        chunks.append("## Overview")
        chunks.append("")
        chunks.append(overview_md)
        chunks.append("")
    chunks.append(body_clean.strip())
    chunks.append("")
    return "\n".join(chunks)


def main() -> int:
    if not CANONICAL_DIR.exists() or not WIKI_DIR.exists():
        print(f"[ERR]\tmissing dirs: canonical={CANONICAL_DIR}, wiki={WIKI_DIR}")
        return 1

    changed = 0
    for canonical in sorted(CANONICAL_DIR.glob("*.md")):
        wiki = WIKI_DIR / canonical.name
        if not wiki.exists():
            print(f"[SKIP]\t{canonical.name} (no wiki mirror)")
            continue
        new = build_wiki_doc(canonical)
        old = wiki.read_text(encoding="utf-8")
        if new != old:
            wiki.write_text(new, encoding="utf-8")
            print(f"[REGEN]\t{canonical.name}")
            changed += 1
        else:
            print(f"[OK]\t{canonical.name} (already clean)")

    print(f"\nDone. {changed} files updated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
