"""Pure-function transforms for canonical -> wiki mirrors.

Replaces what the deprecated `docs-wiki-sync` agent used to do via LLM
intelligence: deterministic Python transforms covering every variation
the agent applied.

Three transform kinds, mirroring docs-sync's `find_canonical_targets`:

  - skill (.claude/skills/<name>/SKILL.md -> wiki/docs/skills/<name>.md)
        Trim frontmatter to just `name:`. Insert `## Overview` heading +
        the (HTML-escaped) description between frontmatter and body.

  - agent (.claude/agents/<name>.md -> wiki/docs/agents/<name>.md)
        Trim frontmatter to `name/model/color/memory`. Inject badge HTML.
        Insert `## Overview` + parsed description: prose chunks + each
        `<example>` block transformed into a styled `<div>` (Context/User/
        Assistant turns; `<commentary>` blocks dropped). Body HTML-escapes
        literal `<example>...</example>` strings (defensive against MDX
        treating them as components).

  - doc (docs/*.md, .claude/skills/_shared/*.md -> wiki/docs/<name>.md)
        Identity copy.

All functions are pure: input string in, output string out. The hooks
that wrap these (drift detect, file I/O) live in sync.py.
"""
from __future__ import annotations

import re
from typing import Iterable

# --- frontmatter -------------------------------------------------------

_FM_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


def split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Return (frontmatter dict, body). If no frontmatter, returns ({}, text).

    Frontmatter values are read raw (one-line YAML-ish). Multiline values
    that span lines via leading whitespace continuation are NOT supported,
    but agent descriptions are always single-line quoted strings with `\\n`
    escape sequences, so this is fine for our inputs.
    """
    m = _FM_PATTERN.match(text)
    if not m:
        return {}, text
    fm_block = m.group(1)
    body = text[m.end():]
    fm: dict[str, str] = {}
    for line in fm_block.splitlines():
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        fm[key.strip()] = val.strip().strip('"').strip("'")
    return fm, body


def render_frontmatter(fm: dict[str, str], keys_quoted: Iterable[str] = ()) -> str:
    """Serialize frontmatter back to YAML. `keys_quoted` are emitted with
    double-quoted values (matching how agents quote their `name`)."""
    keys_quoted_set = set(keys_quoted)
    lines = ["---"]
    for k, v in fm.items():
        if k in keys_quoted_set:
            lines.append(f'{k}: "{v}"')
        else:
            lines.append(f"{k}: {v}")
    lines.append("---")
    return "\n".join(lines) + "\n"


# --- HTML escape -------------------------------------------------------

def html_escape(text: str) -> str:
    """Escape & < > for safe embedding in MDX/Docusaurus markdown.

    NOT a full HTML escape (no ' / " escaping) — those don't trip MDX.
    """
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# --- agent description parser -----------------------------------------

# Agent descriptions are JSON-ish quoted strings with literal `\n` escapes
# (because YAML quoted-string mode). Decode those before parsing.
_DECODE_MAP = {
    "\\n": "\n",
    '\\"': '"',
    "\\\\": "\\",
}


def decode_yaml_quoted(s: str) -> str:
    """Decode the `\\n`/`\\"` escapes used inside an agent's description string.

    Agent frontmatter looks like `description: "...\\n\\n<example>...\\n</example>..."`.
    We need real newlines so the example parser can find tag boundaries.
    """
    # Use re.sub with a replacement function for stable order.
    pattern = re.compile(r"\\[n\"\\]")
    return pattern.sub(lambda m: _DECODE_MAP.get(m.group(0), m.group(0)), s)


_EXAMPLE_BLOCK = re.compile(r"<example>(.*?)</example>", re.DOTALL)
_CONTEXT_LINE = re.compile(r"^\s*Context:\s*(.+?)\s*$", re.MULTILINE)
_USER_LINE = re.compile(r"^\s*user:\s*(.+?)\s*$", re.MULTILINE | re.DOTALL)
_ASSISTANT_LINE = re.compile(r"^\s*assistant:\s*(.+?)\s*$", re.MULTILINE | re.DOTALL)
_COMMENTARY_BLOCK = re.compile(r"<commentary>.*?</commentary>", re.DOTALL)


def _normalize_turn_text(text: str) -> str:
    """Collapse whitespace, strip outer quotes preserved from `user:` / `assistant:`."""
    text = _COMMENTARY_BLOCK.sub("", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_example_block(block_inner: str) -> dict[str, str]:
    """Extract Context / user / assistant content from one <example>...</example> body.

    Returns a dict with keys 'context', 'user', 'assistant' (any may be empty
    string if not present). Commentary is silently dropped.
    """
    out = {"context": "", "user": "", "assistant": ""}

    block = _COMMENTARY_BLOCK.sub("", block_inner)

    if (m := _CONTEXT_LINE.search(block)):
        out["context"] = _normalize_turn_text(m.group(1))

    # `user:` and `assistant:` lines greedily eat to the next "label:" line or
    # end of block. We use a more careful pattern: capture until the next
    # known-label line or end.
    label_split = re.compile(
        r"^\s*(Context|user|assistant):\s*(.*?)(?=^\s*(?:Context|user|assistant):|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    for m in label_split.finditer(block):
        label = m.group(1).lower()
        content = m.group(2).strip()
        if label == "context":
            out["context"] = _normalize_turn_text(content)
        elif label == "user":
            out["user"] = _normalize_turn_text(content)
        elif label == "assistant":
            out["assistant"] = _normalize_turn_text(content)

    return out


def render_example_div(example: dict[str, str]) -> str:
    """Render one parsed example as the agent-example div block."""
    lines = ['<div class="agent-example">']
    lines.append('<div class="agent-example__title">Example</div>')
    for label, key in (("Context", "context"), ("User", "user"), ("Assistant", "assistant")):
        content = example.get(key, "").strip()
        if not content:
            continue
        lines.append('<div class="agent-example__turn">')
        lines.append(f'<div class="agent-example__label">{label}</div>')
        lines.append(f'<div class="agent-example__content">{content}</div>')
        lines.append('</div>')
    lines.append('</div>')
    return "\n".join(lines)


def render_description(description_raw: str) -> str:
    """Turn an agent description (decoded) into the body content for the
    Overview section: prose + zero-or-more example divs.
    """
    decoded = decode_yaml_quoted(description_raw)
    parts: list[str] = []
    last_end = 0
    for m in _EXAMPLE_BLOCK.finditer(decoded):
        prose = decoded[last_end:m.start()].strip()
        if prose:
            parts.append(prose)
        ex = parse_example_block(m.group(1))
        parts.append(render_example_div(ex))
        last_end = m.end()
    tail = decoded[last_end:].strip()
    if tail:
        parts.append(tail)
    return "\n\n".join(parts)


# --- body MDX-safety pass ---------------------------------------------

# Specific tag names that MDX tries to parse as components even inside
# inline code. Escape them defensively wherever they appear in the body.
_MDX_TAG_PATTERN = re.compile(r"<(/?(?:example|commentary))>")


def escape_mdx_tags_in_body(body: str) -> str:
    """Escape literal <example>/<commentary> tags so MDX doesn't choke."""
    return _MDX_TAG_PATTERN.sub(lambda m: f"&lt;{m.group(1)}&gt;", body)


_HTML_COMMENT_PATTERN = re.compile(r"<!--.*?-->")


def strip_html_comments_outside_fences(body: str) -> str:
    """Remove `<!-- ... -->` comments outside fenced code blocks.

    MDX has no HTML comments — a literal `<!--` fails compilation with
    "Unexpected character `!` before name". Canonical skills carry
    single-line marker comments (e.g. `<!-- skill-dir-note -->`) that are
    metadata for agents, not wiki content, so they're dropped rather than
    converted. Comments inside fences are displayed code and are kept.
    """
    out: list[str] = []
    in_fence = False
    for line in body.splitlines(keepends=True):
        stripped = line.lstrip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            out.append(line)
            continue
        if in_fence:
            out.append(line)
            continue
        cleaned = _HTML_COMMENT_PATTERN.sub("", line)
        if cleaned.strip() == "" and line.strip() != "":
            continue  # line was only a comment — drop it entirely
        out.append(cleaned)
    return "".join(out)


def escape_mdx_curlies_outside_fences(body: str) -> str:
    """Escape { and } to HTML entities outside fenced code blocks.

    MDX parses `{expr}` as a JavaScript expression even when the curly
    braces appear in plain prose OR inline code (`code` spans). Fenced
    code blocks (```...```) are preserved as-is by MDX, so we only
    escape outside them. The HTML entities render visually as { and }
    in the output (browsers decode entities inside <code> too) but
    don't trip MDX's expression parser.

    Triggered by skills like dayz-particles that document GUID syntax
    like {HEXGUID}path/to/file.emat in prose and tables.
    """
    out: list[str] = []
    in_fence = False
    for line in body.splitlines(keepends=True):
        stripped = line.lstrip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            out.append(line)
            continue
        if in_fence:
            out.append(line)
            continue
        out.append(line.replace("{", "&#123;").replace("}", "&#125;"))
    return "".join(out)


# --- transforms --------------------------------------------------------

_SKILL_FM_KEEP = ("name",)
_AGENT_FM_KEEP = ("name", "model", "color", "memory")
_AGENT_FM_QUOTED = ("name",)


def transform_skill(canonical_text: str) -> str:
    fm, body = split_frontmatter(canonical_text)
    description = fm.get("description", "")
    trimmed_fm = {k: fm[k] for k in _SKILL_FM_KEEP if k in fm}

    overview = ""
    if description:
        overview = f"\n## Overview\n\n{html_escape(description)}\n\n"

    safe_body = escape_mdx_curlies_outside_fences(strip_html_comments_outside_fences(body))
    return render_frontmatter(trimmed_fm) + overview + safe_body.lstrip("\n")


def transform_agent(canonical_text: str) -> str:
    fm, body = split_frontmatter(canonical_text)
    description = fm.get("description", "")
    model = fm.get("model", "opus")
    color = fm.get("color", "")
    trimmed_fm = {k: fm[k] for k in _AGENT_FM_KEEP if k in fm}

    badges = (
        '<p class="agent-badges">'
        '<span class="badge badge--primary">Agent</span>'
        f'<span class="badge badge--secondary">{model}</span>'
        + (f'<span class="agent-color-badge agent-color-badge--{color}">{color}</span>' if color else "")
        + "</p>"
    )

    overview_body = render_description(description) if description else ""
    overview = ""
    if overview_body:
        overview = f"\n{badges}\n\n## Overview\n\n{overview_body}\n\n"
    else:
        overview = f"\n{badges}\n\n"

    safe_body = escape_mdx_curlies_outside_fences(
        escape_mdx_tags_in_body(strip_html_comments_outside_fences(body))
    )

    return render_frontmatter(trimmed_fm, keys_quoted=_AGENT_FM_QUOTED) + overview + safe_body.lstrip("\n")


def transform_doc(canonical_text: str) -> str:
    """Doc files (docs/*.md, _shared/*.md) get an identity copy."""
    return canonical_text
