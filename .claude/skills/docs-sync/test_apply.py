"""Tests for the canonical->wiki transforms in apply.py.

Each transform has:
  - frontmatter handling (kept fields, dropped fields, quoting)
  - body handling (preserved vs HTML-escaped vs synthesized)
  - the parser for agent <example> blocks (Context/User/Assistant + commentary drop)
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from apply import (
    escape_bare_tags_outside_fences,
    escape_mdx_curlies_outside_fences,
    escape_mdx_tags_in_body,
    html_escape,
    parse_example_block,
    render_description,
    render_example_div,
    render_frontmatter,
    split_frontmatter,
    strip_html_comments_outside_fences,
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


def test_escape_description_prose_only():
    from apply import escape_description

    out = escape_description("Packs `<mod>/gui/` sprites; uses {GUID}path & <tags> but `{x}` stays")
    assert out == (
        "Packs `<mod>/gui/` sprites; uses &#123;GUID&#125;path &amp; &lt;tags&gt; but `{x}` stays"
    )


def test_skill_overview_escapes_curly_braces():
    out = transform_skill("---\nname: s\ndescription: Uses {GUID}path refs.\n---\n# s\n")
    assert "Uses &#123;GUID&#125;path refs." in out


def test_html_escape_safety():
    assert html_escape("<example>") == "&lt;example&gt;"
    assert html_escape("a & b") == "a &amp; b"
    assert html_escape('user said "hi"') == 'user said "hi"'  # quotes left alone


# ---------- YAML frontmatter ----------

def test_split_frontmatter_folded_description():
    text = (
        "---\n"
        "name: foo\n"
        "description: >\n"
        "  Audits things and\n"
        "  reports findings.\n"
        "---\n"
        "body\n"
    )
    fm, body = split_frontmatter(text)
    assert fm["description"] == "Audits things and reports findings."
    assert body == "body\n"


def test_split_frontmatter_folded_strip_description():
    text = "---\nname: foo\ndescription: >-\n  One\n  two.\n---\nbody\n"
    assert split_frontmatter(text)[0]["description"] == "One two."


def test_split_frontmatter_invalid_yaml_raises():
    with pytest.raises(ValueError):
        split_frontmatter("---\nname: [unclosed\n---\nbody\n")


def test_transform_skill_folded_description_renders_text():
    src = "---\nname: dayz-x\ndescription: >\n  Does x with P:\\ paths.\n  Use when x.\n---\n\n# /dayz-x\n"
    out = transform_skill(src)
    assert "&gt;" not in out
    assert "Does x with P:\\ paths. Use when x." in out


# ---------- MDX curly escape ----------

def test_curly_escape_skips_inline_code_and_fences():
    body = "Prose {a} and `code {b}` here.\n```\n{c}\n```\n"
    out = escape_mdx_curlies_outside_fences(body)
    assert "Prose &#123;a&#125;" in out
    assert "`code {b}`" in out
    assert "\n{c}\n" in out


def test_curly_escape_skips_tilde_fences():
    body = "~~~\n{c}\n~~~\n{d}\n"
    assert escape_mdx_curlies_outside_fences(body) == "~~~\n{c}\n~~~\n&#123;d&#125;\n"


def test_fence_closes_only_on_same_marker():
    # A ``` line inside a ~~~ fence is code, not a closing fence.
    body = "~~~\n```\n{c}\n~~~\n{d}\n"
    out = escape_mdx_curlies_outside_fences(body)
    assert "\n{c}\n" in out and "&#123;d&#125;" in out


# ---------- HTML comment stripping ----------

def test_strip_single_line_comment_drops_line():
    assert strip_html_comments_outside_fences("a\n<!-- note -->\nb\n") == "a\nb\n"


def test_strip_multi_line_comment():
    body = "a\n<!--\nhidden {x}\nmore\n-->\nb\n"
    assert strip_html_comments_outside_fences(body) == "a\nb\n"


def test_strip_inline_comment_keeps_text():
    assert strip_html_comments_outside_fences("keep <!-- x --> this\n") == "keep  this\n"


def test_comment_inside_inline_code_span_is_kept():
    body = "such as a `<!-- MyMod types -->` header line <!-- gone -->\n"
    assert strip_html_comments_outside_fences(body) == "such as a `<!-- MyMod types -->` header line \n"


def test_strip_does_not_join_two_comments_across_text():
    body = "<!-- a --> keep\n<!-- b -->\n"
    assert strip_html_comments_outside_fences(body) == " keep\n"


def test_comments_in_backtick_and_tilde_fences_are_kept():
    body = "```\n<!-- c1 -->\n```\n~~~html\n<!--\nc2\n-->\n~~~\n<!-- gone -->\n"
    assert strip_html_comments_outside_fences(body) == (
        "```\n<!-- c1 -->\n```\n~~~html\n<!--\nc2\n-->\n~~~\n"
    )


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


def test_render_description_escapes_prose_and_examples_like_skills():
    desc = (
        "Use for `modded class X {}` & <Widget> work with {braces}.\n\n"
        "<example>\nContext: set {a} & b\n"
        'user: "Add `class Foo {}` to <config>"\n'
        'assistant: "I\'ll use x -> y {z}"\n</example>\n\n'
        "Tail {t} & <u>."
    )
    out = render_description(desc)
    # Prose: escaped outside inline code, code spans left literal.
    assert "Use for `modded class X {}` &amp; &lt;Widget&gt; work with &#123;braces&#125;." in out
    # Example turns get the same treatment.
    assert ">set &#123;a&#125; &amp; b<" in out
    assert '`class Foo {}` to &lt;config&gt;' in out
    assert "x -&gt; y &#123;z&#125;" in out
    assert "Tail &#123;t&#125; &amp; &lt;u&gt;." in out
    # The generated div markup itself is not escaped.
    assert out.count('<div class="agent-example">') == 1


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


def test_transform_agent_without_a_model_shows_inherit():
    out = transform_agent("---\nname: x\ndescription: Does x.\n---\n\nBody.\n")
    assert '<span class="badge badge--secondary">inherit</span>' in out
    assert "opus" not in out
    assert "model:" not in out


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

def test_transform_doc_plain_body_is_unchanged():
    src = "---\nname: X\ntitle: Y\n---\n\nbody `{x}` contents\n"
    assert transform_doc(src) == src


def test_transform_doc_makes_body_mdx_safe():
    src = '---\ntitle: "{keep}"\n---\n\n<!-- note -->\nUse {name} here.\n'
    out = transform_doc(src)
    assert out.startswith('---\ntitle: "{keep}"\n---\n')
    assert "<!--" not in out
    assert "Use &#123;name&#125; here." in out


# ---------- bare placeholder tags in body prose ----------

def test_bare_placeholder_tags_are_escaped_in_prose_only():
    body = (
        "Mods live in workspace/<ModName>/ and `workspace/<ModName>/`.\n"
        "Run from <skill-dir> or </Close>.\n"
        "```\nworkspace/<ModName>/\n```\n"
        "Keep <details><summary>More</summary> and <br> as HTML.\n"
        "Arrows <- and a < b stay.\n"
    )
    out = escape_bare_tags_outside_fences(body)
    assert "Mods live in workspace/&lt;ModName&gt;/ and `workspace/<ModName>/`." in out
    assert "Run from &lt;skill-dir&gt; or &lt;/Close&gt;." in out
    assert "```\nworkspace/<ModName>/\n```\n" in out
    assert "Keep <details><summary>More</summary> and <br> as HTML." in out
    assert "Arrows <- and a < b stay." in out


def test_transforms_escape_bare_tags_in_body():
    assert "workspace/&lt;ModName&gt;/" in transform_skill("---\nname: x\n---\n\nSee workspace/<ModName>/.\n")
    assert "workspace/&lt;ModName&gt;/" in transform_agent("---\nname: x\n---\n\nSee workspace/<ModName>/.\n")
    assert "workspace/&lt;ModName&gt;/" in transform_doc("See workspace/<ModName>/.\n")
