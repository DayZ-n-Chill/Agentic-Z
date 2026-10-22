"""Pure-function transforms for canonical -> wiki mirrors.

Three transform kinds, mirroring docs-sync's `find_canonical_targets`:

  - skill (.claude/skills/<name>/SKILL.md -> wiki/docs/skills/<name>.md)
        Trim frontmatter to just `name:`. Insert `## Overview` heading +
        the description between frontmatter and body, with &, <, >, { and }
        escaped in prose but not inside inline code.

  - agent (.claude/agents/<name>.md -> wiki/docs/agents/<name>.md)
        Trim frontmatter to `name/model/color/memory`. Inject badge HTML.
        Insert `## Overview` + parsed description: prose chunks + each
        `<example>` block transformed into a styled `<div>` (Context/User/
        Assistant turns; `<commentary>` blocks dropped). Prose and example
        text are escaped like skill descriptions. Body HTML-escapes
        literal `<example>...</example>` strings (defensive against MDX
        treating them as components).

  - doc (docs/dayz-modding.md, docs/model-routing.md and
        .claude/skills/_shared/dayz-conventions.md -> wiki/docs/<name>.md;
        .claude/skills/_shared/conventions/*.md -> wiki/docs/conventions/<name>.md)
        Frontmatter copied verbatim; body gets the same MDX-safety pass as
        skills (HTML comments dropped, curly braces escaped outside code).

Frontmatter is parsed with PyYAML, so folded (`>`, `>-`), literal and
quoted descriptions all come out as plain text.

All functions are pure: input string in, output string out. The hooks
that wrap these (drift detect, file I/O) live in sync.py.
"""
from __future__ import annotations

import re
from typing import Iterable

import yaml

# --- frontmatter -------------------------------------------------------

_FM_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


def split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Return (frontmatter dict, body). If no frontmatter, returns ({}, text).

    Values are parsed as YAML and stringified. Raises ValueError when the
    frontmatter is not a valid YAML mapping.
    """
    m = _FM_PATTERN.match(text)
    if not m:
        return {}, text
    try:
        data = yaml.safe_load(m.group(1))
    except yaml.YAMLError as e:
        raise ValueError(f"invalid YAML frontmatter: {e}") from e
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ValueError("frontmatter is not a YAML mapping")
    fm = {str(k): "" if v is None else str(v).strip() for k, v in data.items()}
    return fm, text[m.end():]


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

_EXAMPLE_BLOCK = re.compile(r"<example>(.*?)</example>", re.DOTALL)
_COMMENTARY_BLOCK = re.compile(r"<commentary>.*?</commentary>", re.DOTALL)


def _normalize_turn_text(text: str) -> str:
    """Drop commentary and collapse whitespace."""
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

    # Each label captures until the next known-label line or end of block.
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
        lines.append(f'<div class="agent-example__content">{escape_description(content)}</div>')
        lines.append('</div>')
    lines.append('</div>')
    return "\n".join(lines)


def render_description(decoded: str) -> str:
    """Turn an agent description (already YAML-decoded) into the body content
    for the Overview section: prose + zero-or-more example divs. Prose and
    example text get the same escaping as skill descriptions.
    """
    parts: list[str] = []
    last_end = 0
    for m in _EXAMPLE_BLOCK.finditer(decoded):
        prose = decoded[last_end:m.start()].strip()
        if prose:
            parts.append(escape_description(prose))
        ex = parse_example_block(m.group(1))
        parts.append(render_example_div(ex))
        last_end = m.end()
    tail = decoded[last_end:].strip()
    if tail:
        parts.append(escape_description(tail))
    return "\n\n".join(parts)


# --- body MDX-safety pass ---------------------------------------------

# Specific tag names that MDX tries to parse as components even inside
# inline code. Escape them defensively wherever they appear in the body.
_MDX_TAG_PATTERN = re.compile(r"<(/?(?:example|commentary))>")


def escape_mdx_tags_in_body(body: str) -> str:
    """Escape literal <example>/<commentary> tags so MDX doesn't choke."""
    return _MDX_TAG_PATTERN.sub(lambda m: f"&lt;{m.group(1)}&gt;", body)


_FENCE_OPEN = re.compile(r"(`{3,}|~{3,})")
# (?:(?!-->).)*? stops at the first -->, so a match never spans two comments.
_HTML_COMMENT_LINES = re.compile(
    r"^[ \t]*<!--(?:(?!-->).)*?-->[ \t]*(?:\r?\n|\Z)", re.DOTALL | re.MULTILINE
)
_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)


def _split_fences(body: str) -> list[tuple[str, bool]]:
    """Split body into (text, is_fenced_code) runs.

    Fences open with three or more backticks or tildes; a fence closes only on
    a line of the same character at least as long, as in CommonMark. Fence
    lines themselves belong to the code run. An unclosed fence runs to the end.
    """
    runs: list[tuple[str, bool]] = []
    buf: list[str] = []
    fence: str | None = None
    for line in body.splitlines(keepends=True):
        stripped = line.lstrip()
        if fence is None:
            m = _FENCE_OPEN.match(stripped)
            if m:
                if buf:
                    runs.append(("".join(buf), False))
                buf, fence = [line], m.group(1)
                continue
        else:
            closing = stripped.rstrip()
            if closing and set(closing) == {fence[0]} and len(closing) >= len(fence):
                buf.append(line)
                runs.append(("".join(buf), True))
                buf, fence = [], None
                continue
        buf.append(line)
    if buf:
        runs.append(("".join(buf), fence is not None))
    return runs


def _map_prose(body: str, fn) -> str:
    """Apply fn to every run of body outside fenced code."""
    return "".join(text if code else fn(text) for text, code in _split_fences(body))


def _strip_comments(prose: str) -> str:
    # Lines that hold only a comment (one line or several) are dropped whole;
    # comments sharing a line with text are cut out of it.
    return _HTML_COMMENT.sub("", _HTML_COMMENT_LINES.sub("", prose))


def strip_html_comments_outside_fences(body: str) -> str:
    """Remove `<!-- ... -->` comments, including multi-line ones, outside fenced code.

    MDX has no HTML comments — a literal `<!--` fails compilation with
    "Unexpected character `!` before name". Canonical skills carry marker
    comments (e.g. `<!-- skill-dir-note -->`) that are metadata for agents,
    not wiki content, so they're dropped rather than converted. Comments
    inside ``` or ~~~ fences are displayed code and are kept.
    """
    return _map_prose(body, _strip_comments)


_CODE_SPAN = re.compile(r"(`+).*?\1")


def _outside_code_spans(text: str, fn) -> str:
    """Apply fn to the prose parts of text, leaving inline code spans untouched."""
    out: list[str] = []
    last = 0
    for m in _CODE_SPAN.finditer(text):
        out.append(fn(text[last:m.start()]))
        out.append(m.group(0))
        last = m.end()
    out.append(fn(text[last:]))
    return "".join(out)


def _curlies(text: str) -> str:
    return text.replace("{", "&#123;").replace("}", "&#125;")


def _escape_curlies(text: str) -> str:
    """Escape { and } in prose, leaving inline code spans untouched."""
    return _outside_code_spans(text, _curlies)


def escape_description(text: str) -> str:
    """MDX-safe skill description: &, <, >, { and } escaped in prose only.

    Inline code is literal in MDX 3, so an entity there would show as raw text.
    """
    return _outside_code_spans(text, lambda s: _curlies(html_escape(s)))


def escape_mdx_curlies_outside_fences(body: str) -> str:
    """Escape { and } to HTML entities outside fenced code and inline code.

    MDX parses `{expr}` in prose as a JavaScript expression. Code (fenced
    blocks and inline spans) is literal in MDX 3, and an entity written
    there would render as the raw text `&#123;`, so code is left alone.
    """
    return _map_prose(body, lambda prose: "".join(
        _escape_curlies(line) for line in prose.splitlines(keepends=True)
    ))


# Real HTML tags that wiki bodies may use on purpose; MDX renders these.
_HTML_TAG_ALLOW = frozenset({
    "a", "b", "br", "code", "details", "div", "em", "hr", "i", "img", "kbd",
    "li", "ol", "p", "pre", "span", "strong", "sub", "summary", "sup", "table",
    "tbody", "td", "th", "thead", "tr", "ul",
})
# `<` then an optional `/` and a name, up to an optional `>` on the same line.
_BARE_TAG = re.compile(r"<(/?)([A-Za-z][\w.:-]*)([^<>\n]*)(>?)")


def _bare_tags(text: str) -> str:
    def sub(m: re.Match) -> str:
        if m.group(2).lower() in _HTML_TAG_ALLOW:
            return m.group(0)
        return f"&lt;{m.group(1)}{m.group(2)}{m.group(3)}{'&gt;' if m.group(4) else ''}"
    return _BARE_TAG.sub(sub, text)


def escape_bare_tags_outside_fences(body: str) -> str:
    """Escape placeholder tags like `<ModName>` in prose outside fenced and inline code.

    MDX reads `<Name>` in prose as a JSX tag, and an unclosed one breaks the
    wiki build. Real HTML tags in the allowlist are kept; code is literal in
    MDX 3, so it is left alone.
    """
    return _map_prose(body, lambda prose: "".join(
        _outside_code_spans(line, _bare_tags) for line in prose.splitlines(keepends=True)
    ))


def _mdx_safe_body(body: str) -> str:
    return escape_mdx_curlies_outside_fences(escape_bare_tags_outside_fences(body))


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
        overview = f"\n## Overview\n\n{escape_description(description)}\n\n"

    safe_body = _mdx_safe_body(strip_html_comments_outside_fences(body))
    return render_frontmatter(trimmed_fm) + overview + safe_body.lstrip("\n")


def transform_agent(canonical_text: str) -> str:
    fm, body = split_frontmatter(canonical_text)
    description = fm.get("description", "")
    # An agent with no model field inherits the caller's model in Claude Code.
    model = fm.get("model", "inherit")
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

    safe_body = _mdx_safe_body(escape_mdx_tags_in_body(strip_html_comments_outside_fences(body)))

    return render_frontmatter(trimmed_fm, keys_quoted=_AGENT_FM_QUOTED) + overview + safe_body.lstrip("\n")


def transform_doc(canonical_text: str) -> str:
    """Doc files (docs/*.md, _shared/*.md): frontmatter verbatim, MDX-safe body."""
    m = _FM_PATTERN.match(canonical_text)
    head, body = (canonical_text[:m.end()], canonical_text[m.end():]) if m else ("", canonical_text)
    return head + _mdx_safe_body(strip_html_comments_outside_fences(body))
