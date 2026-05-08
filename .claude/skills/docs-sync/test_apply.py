"""Tests for the canonical->wiki transforms in apply.py.

Each transform has:
  - frontmatter handling (kept fields, dropped fields, quoting)
  - body handling (preserved vs HTML-escaped vs synthesized)
  - the parser for agent <example> blocks (Context/User/Assistant + commentary drop)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from apply import (
    decode_yaml_quoted,
    escape_mdx_tags_in_body,
    html_escape,
    parse_example_block,
    render_description,
    render_example_div,
    render_frontmatter,
    split_frontmatter,
    transform_agent,
    transform_doc,
    transform_skill,
)


# ---------- helpers ----------

def test_split_frontmatter_basic():
    # The blank line between closing --- and body content is consumed by the
    # frontmatter regex (\\s*\\n? after the closing fence). Body starts at
    # the first content character. Renderers add their own spacing back.
    text = "---\nname: foo\ndescription: bar\n---\n\nbody here\n"
    fm, body = split_frontmatter(text)
    assert fm == {"name": "foo", "description": "bar"}
    assert body == "body here\n"


def test_split_frontmatter_quoted_values():
    text = '---\nname: "foo"\ndescription: "with \\"quotes\\""\n---\nbody\n'
    fm, body = split_frontmatter(text)
    assert fm["name"] == "foo"
    # The simple parser strips outer quotes; embedded escaped quotes are
    # preserved-as-text inside (we don't fully decode here).
    assert body == "body\n"


def test_split_frontmatter_no_frontmatter():
    text = "no frontmatter here\n"
    fm, body = split_frontmatter(text)
    assert fm == {}
    assert body == text


def test_render_frontmatter_quoting():
    out = render_frontmatter({"name": "x", "model": "opus"}, keys_quoted={"name"})
    assert out == '---\nname: "x"\nmodel: opus\n---\n'


def test_html_escape_safety():
    assert html_escape("<example>") == "&lt;example&gt;"
    assert html_escape("a & b") == "a &amp; b"
    assert html_escape('user said "hi"') == 'user said "hi"'  # quotes left alone


# ---------- yaml-quoted decode ----------

def test_decode_yaml_quoted_newlines():
    assert decode_yaml_quoted("line1\\nline2") == "line1\nline2"


def test_decode_yaml_quoted_quote_escape():
    assert decode_yaml_quoted('he said \\"hi\\"') == 'he said "hi"'


def test_decode_yaml_quoted_backslash():
    assert decode_yaml_quoted("path C:\\\\foo") == "path C:\\foo"


# ---------- example block parser ----------

def test_parse_example_block_full():
    inner = (
        "\nContext: User wants foo.\n"
        'user: "Make it foo"\n'
        'assistant: "Doing foo now"\n'
    )
    out = parse_example_block(inner)
    assert out == {
        "context": "User wants foo.",
        "user": '"Make it foo"',
        "assistant": '"Doing foo now"',
    }


def test_parse_example_block_drops_commentary():
    inner = (
        "Context: c\n"
        'user: "u"\n'
        'assistant: "a"\n'
        "<commentary>this should NOT show up</commentary>\n"
    )
    out = parse_example_block(inner)
    assert "this should NOT" not in (out["context"] + out["user"] + out["assistant"])


def test_parse_example_block_collapses_whitespace():
    inner = (
        "Context: c\n"
        'user: "line1\n\nline2  with  spaces"\n'
        'assistant: "ok"\n'
    )
    out = parse_example_block(inner)
    assert out["user"] == '"line1 line2 with spaces"'


def test_render_example_div_full():
    ex = {"context": "ctx", "user": "u", "assistant": "a"}
    rendered = render_example_div(ex)
    assert '<div class="agent-example">' in rendered
    assert '<div class="agent-example__title">Example</div>' in rendered
    assert '<div class="agent-example__label">Context</div>' in rendered
    assert '<div class="agent-example__content">ctx</div>' in rendered
    assert '<div class="agent-example__label">User</div>' in rendered
    assert '<div class="agent-example__label">Assistant</div>' in rendered


def test_render_example_div_skips_empty_turns():
    # If only context and user are present, assistant turn must not render
    ex = {"context": "c", "user": "u", "assistant": ""}
    rendered = render_example_div(ex)
    assert 'Assistant' not in rendered


# ---------- description renderer (prose + examples) ----------

def test_render_description_pure_prose():
    out = render_description("Just some prose.")
    assert out == "Just some prose."


def test_render_description_prose_then_examples():
    desc = (
        "Use this agent for stuff. Examples:\n\n"
        '<example>\nContext: c1\nuser: "u1"\nassistant: "a1"\n</example>\n\n'
        '<example>\nContext: c2\nuser: "u2"\nassistant: "a2"\n</example>'
    )
    out = render_description(desc)
    # Prose comes first
    assert out.startswith("Use this agent for stuff. Examples:")
    # Two divs follow
    assert out.count('<div class="agent-example">') == 2
    # Content from both examples is in there
    assert ">c1<" in out
    assert ">c2<" in out


def test_render_description_yaml_quoted_input():
    """Agent files store description as a YAML quoted string with \\n escapes;
    render_description must decode those before parsing examples."""
    desc_raw = 'Lead-in.\\n\\n<example>\\nContext: ctx\\nuser: "u"\\nassistant: "a"\\n</example>'
    out = render_description(desc_raw)
    assert out.startswith("Lead-in.")
    assert '<div class="agent-example">' in out
    assert ">ctx<" in out


# ---------- MDX tag escape in body ----------

def test_escape_mdx_tags_in_body_only_targets_mdx_problem_tags():
    body = (
        "Plain `<ModName>` is fine.\n"
        "But `<example>...</example>` confuses MDX.\n"
        "And `<commentary>` too.\n"
    )
    out = escape_mdx_tags_in_body(body)
    # ModName tag NOT touched (it's not an MDX-problem tag)
    assert "`<ModName>`" in out
    # example/commentary tags escaped
    assert "&lt;example&gt;" in out
    assert "&lt;/example&gt;" in out
    assert "&lt;commentary&gt;" in out


# ---------- transform_skill ----------

def test_transform_skill_trims_description_and_inserts_overview():
    src = (
        "---\n"
        "name: dayz-foo\n"
        "description: A skill that does foo with <args>\n"
        "---\n\n"
        "# /dayz-foo\n\n"
        "Body content here.\n"
    )
    out = transform_skill(src)
    # Frontmatter has name only
    assert "name: dayz-foo" in out
    assert "description:" not in out.split("---", 2)[1]  # not in FM section
    # Overview inserted with HTML-escaped description
    assert "## Overview" in out
    assert "&lt;args&gt;" in out
    # Original body preserved
    assert "# /dayz-foo" in out
    assert "Body content here." in out


def test_transform_skill_no_description():
    src = "---\nname: dayz-x\n---\n\n# /dayz-x\n\nbody\n"
    out = transform_skill(src)
    assert "## Overview" not in out
    assert "name: dayz-x" in out


# ---------- transform_agent ----------

def test_transform_agent_trims_frontmatter_and_injects_badges():
    src = (
        "---\n"
        'name: "test-agent"\n'
        "description: One-liner.\n"
        "model: opus\n"
        "color: red\n"
        "memory: project\n"
        "tools: Read, Glob\n"
        "permissionMode: acceptEdits\n"
        "maxTurns: 50\n"
        "---\n\n"
        "## NAME\n\ntest-agent\n"
    )
    out = transform_agent(src)
    # Kept
    assert 'name: "test-agent"' in out
    assert "model: opus" in out
    assert "color: red" in out
    assert "memory: project" in out
    # Dropped
    fm_section = out.split("---", 2)[1]
    assert "description" not in fm_section
    assert "tools" not in fm_section
    assert "permissionMode" not in fm_section
    assert "maxTurns" not in fm_section
    # Badge HTML inserted
    assert '<p class="agent-badges">' in out
    assert "Agent</span>" in out
    assert "opus</span>" in out
    assert "agent-color-badge--red" in out
    # Overview present
    assert "## Overview" in out
    assert "One-liner." in out
    # Body preserved
    assert "## NAME" in out


def test_transform_agent_with_examples():
    src = (
        "---\n"
        'name: "ex-agent"\n'
        'description: "Lead.\\n\\n<example>\\nContext: c\\nuser: \\"u\\"\\nassistant: \\"a\\"\\n</example>"\n'
        "model: opus\n"
        "color: blue\n"
        "memory: project\n"
        "---\n\n"
        "## NAME\n\nex-agent\n"
    )
    out = transform_agent(src)
    assert "Lead." in out
    assert '<div class="agent-example">' in out
    assert ">c<" in out


def test_transform_agent_escapes_mdx_tags_in_body():
    src = (
        "---\n"
        'name: "x"\n'
        "description: x\n"
        "model: opus\n"
        "color: green\n"
        "memory: project\n"
        "---\n\n"
        "Body says: `<example>...</example>` should be escaped.\n"
    )
    out = transform_agent(src)
    assert "&lt;example&gt;" in out


# ---------- transform_doc ----------

def test_transform_doc_is_identity():
    src = "---\nname: X\ntitle: Y\n---\n\nbody contents\n"
    assert transform_doc(src) == src
