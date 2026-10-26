"""Check the React wiki against the repository it describes.

The wiki lives in its own private repository (DayZ-n-Chill/Agentic-Z-Wiki). It is
found at $AGENTIC_Z_WIKI when that is set (an empty value means "no wiki"), else
at a wiki/ folder in this repo, else at a clone named Agentic-Z-Wiki next to this
repo. With no wiki there is nothing to check: --check says so and exits 0, and the
Stop hook stays silent. Problems still name wiki files as wiki/src/..., meaning
src/... in the wiki repository.

Pure-Python, deterministic checks; no model calls. Three checks:
  names   Every agent (agents/*.md) is named in the guide's "## Agents"
          tables and every skill (skills/*/SKILL.md and .claude/skills/*/SKILL.md) in skills-table.md,
          and those tables name nothing that does not exist.
  claims  Each count claim in the CLAIMS table below (an exact piece of text in
          one wiki file, with the place of each number marked) is found in its
          file, and every number in it equals the repository fact it names.
          Numbers anywhere else in the wiki are never read. A claim whose text
          is no longer in its file is reported, so reworded text is never
          skipped silently; update CLAIMS when the wiki wording changes.
  grades  The "Quality by version" tables in guide.md and team.md list every
          graded item exactly once, with its latest grade in the last column.
The claims check skips sections that wiki/src/content.js hides (its HIDDEN set);
the names and grades checks read their tables wherever they sit.

Modes:
  --check (default)    Report each problem as wiki-file:line with the expected
                       value. Exit 1 when there is any. With --quiet (how the
                       Stop hook runs it) print nothing when in sync, else one
                       {"systemMessage": ...} JSON line, and always exit 0.
  --apply              Rewrite the wrong numbers in matched claims in place
                       (apply.py). Nothing
                       else is written; problems it cannot fix stay reported
                       and the exit code is 1.
  --apply --dry-run    Print what --apply would change; write nothing.
  --map                Print what each check compares, with the current
                       repository values.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "skills" / "_shared"))
import skill_helpers as h  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]

WIKI_ENV = "AGENTIC_Z_WIKI"
WIKI_REPO = "DayZ-n-Chill/Agentic-Z-Wiki"
WIKI_PREFIX = "wiki/"  # problems name wiki files as wiki/<path in the wiki repo>


def wiki_dir() -> Path | None:
    """The wiki checkout, or None when there is none to check."""
    if WIKI_ENV in os.environ:
        value = os.environ[WIKI_ENV]
        return Path(value) if value and (Path(value) / "src").is_dir() else None
    for candidate in (REPO_ROOT / "wiki", REPO_ROOT.parent / "Agentic-Z-Wiki"):
        if (candidate / "src").is_dir():
            return candidate
    return None


def source_path(rel: str) -> Path:
    """Where a source lives: wiki/... in the wiki checkout, anything else in this repo."""
    if rel.startswith(WIKI_PREFIX):
        wiki = wiki_dir()
        if wiki is None:
            raise SourceError(f"cannot read {rel}: no wiki checkout (clone {WIKI_REPO} next to this repo)")
        return wiki / rel[len(WIKI_PREFIX):]
    return REPO_ROOT / rel

# Where the grade files live, relative to the repo root. Both are required
# sources. The one place to change when they move.
GRADES_DIR = "docs/grades"
GRADE_FILES = ("final_grades.json", "final_grades_shared.json")

GUIDE = "wiki/src/content/guide.md"
TEAM = "wiki/src/content/team.md"
SKILLS_TABLE = "wiki/src/content/skills-table.md"
CONTENT_JS = "wiki/src/content.js"
APP_JSX = "wiki/src/App.jsx"
RULES_CORE = "skills/_shared/dayz-conventions.md"
RULES_TOPICS = "skills/_shared/conventions"
AGENTS_DIR = "agents"
EVAL_QUESTIONS = "evals/questions"
HOOKS_DIR = "hooks"

GRADE_TABLE_HEADING = "Quality by version"
AGENTS_HEADING = "Agents"

# Grade-file item names the wiki writes differently, after item_key() normalising.
ITEM_ALIASES = {"grading method note": "method note"}

# Batch-name prefixes (before the first "-") the grade counts are split by.
GRADE_KINDS = ("agents", "skills", "shared")

# Numbers a claim may write as a word ("three hooks", "five topic files");
# NUMBER_WORDS[n] spells n. Larger numbers are written and rewritten as digits.
NUMBER_WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
                "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen",
                "eighteen", "nineteen", "twenty"]


@dataclass(frozen=True)
class Claim:
    """One count the wiki states: the exact text in `file`, with {N} where each
    checked number sits, and the fact (a Facts.counts key) each {N} must equal."""
    file: str
    text: str
    facts: tuple[str, ...]
    # The sentence says every graded item is A+. When one is not, no number makes
    # it true, so the check asks for a hand edit instead of rewriting a number.
    all_aplus: bool = False


# Every count claim the visible wiki makes. Only these numbers are checked or
# rewritten. When the wiki rewords one, the check reports it as not found;
# change its text here to match.
_GRADED = ("aplus_agents", "graded_agents", "aplus_skills", "graded_skills", "aplus_shared", "graded_shared")
_RULES = ("core_lines", "topic_files", "topic_min", "topic_max")
CLAIMS = [
    Claim(GUIDE, "Agentic-Z includes {N} agents, {N} skills and {N} hooks.", ("agents", "skills", "hooks")),
    Claim(GUIDE, "Agentic-Z has {N} agents.", ("agents",)),
    Claim(GUIDE, "The {N} agents, the {N} skills, and the reference files", ("agents", "skills")),
    Claim(GUIDE, "Answer tests (evals) check {N} of the {N} agents", ("eval_agents", "agents")),
    Claim(GUIDE, "The final grades cover {N} items, and {N} are at A+: {N} of the {N} agents, "
                 "{N} of the {N} skills and {N} of the {N} shared items.", ("graded_total", "graded_aplus") + _GRADED),
    Claim(GUIDE, "The {N} shared items are neither agents nor skills", ("graded_shared",)),
    Claim(GUIDE, "Answer tests cover {N} of the {N} agents.", ("eval_agents", "agents")),
    Claim(GUIDE, "The {N} agents, one .md file each", ("agents",)),
    Claim(GUIDE, "The {N} skills, one folder each with its SKILL.md", ("skills",)),
    Claim(GUIDE, "The {N} DayZ rules topic files", ("topic_files",)),
    Claim(GUIDE, "The {N} hooks: edit check", ("hooks",)),
    Claim(GUIDE, "The {N} agents that use RAG search also send text off the machine", ("rag_agents",)),
    Claim(TEAM, "the {N} agents and {N} skills that work together", ("agents", "skills")),
    Claim(TEAM, "The final grades cover {N} items, and {N} are at A+: {N} of the {N} agents, "
                "{N} of the {N} skills and {N} of the {N} shared items.", ("graded_total", "graded_aplus") + _GRADED),
    Claim(TEAM, "The {N} shared items are neither agents nor skills", ("graded_shared",)),
    Claim(TEAM, "split into a {N}-line core and {N} topic files of {N} to {N} lines", _RULES),
    Claim(TEAM, "Agentic-Z provides {N} slash commands", ("skills",)),
    Claim(TEAM, "| Agent memory | {N} of the {N} agents", ("memory_agents", "agents")),
    Claim(APP_JSX, "['{N}', 'agents'],", ("agents",)),
    Claim(APP_JSX, "['{N}', 'skills'],", ("skills",)),
    Claim(APP_JSX, "['{N}', 'hooks'],", ("hooks",)),
    Claim(APP_JSX, "['{N}', 'items graded A+'],", ("graded_aplus",)),
]

# A number in a claim: digits or a number word, as a whole word.
NUMBER = r"\b(\d+|(?i:" + "|".join(sorted(NUMBER_WORDS, key=len, reverse=True)) + r"))\b"


def claim_regex(claim: Claim) -> re.Pattern:
    """The claim's text, matched literally, with a number group at each {N}."""
    return re.compile(NUMBER.join(re.escape(part) for part in claim.text.split("{N}")))


class SourceError(Exception):
    """A file the checks need is missing or cannot be parsed."""


@dataclass
class Problem:
    file: str
    line: int
    message: str
    # (start, end, replacement) within that line's text when --apply can fix it.
    fix: tuple[int, int, str] | None = None
    # The text the check saw in that span, so --apply can tell the file changed since.
    old: str | None = None

    def __str__(self) -> str:
        tag = " [fixable]" if self.fix else ""
        where = f"{self.file}:{self.line}" if self.line else self.file  # line 0: about a whole file or folder
        return f"{where}: {self.message}{tag}"


@dataclass
class Facts:
    agents: list[str]
    memory_agents: list[str]
    skills: list[str]
    eval_agents: list[str]
    # kind ("agents", "skills", "shared") -> {item: latest grade}
    grades: dict[str, dict[str, str]]
    # item -> grade file it came from
    grade_source: dict[str, str]
    core_lines: int
    topic_lines: dict[str, int]
    counts: dict[str, tuple[int, str]] = field(default_factory=dict)


def hook_notice(message: str) -> None:
    """Print a message for the Stop hook (--quiet) as hook JSON output.

    Claude Code sends a command hook's plain stdout on exit 0 to the debug log,
    not the transcript; a `systemMessage` field is what it shows the user.
    """
    print(json.dumps({"systemMessage": message}))


def slugify(text: str) -> str:
    """Python port of slugify() in wiki/src/content.js."""
    s = re.sub(r"[^\w\s-]", "", text.lower().replace("`", ""), flags=re.ASCII).strip()
    return re.sub(r"\s+", "-", s)


def line_count(path: Path) -> int:
    """Lines as `wc -l` counts them (newline characters). A file that cannot be read is a SourceError."""
    try:
        return path.read_bytes().count(b"\n")
    except OSError as e:
        raise SourceError(f"cannot read {path.relative_to(REPO_ROOT).as_posix()}: {e.strerror or e}") from e


def read(rel: str) -> str:
    path = source_path(rel)
    try:
        return path.read_text(encoding="utf-8")
    except OSError as e:
        raise SourceError(f"cannot read {rel}: {e.strerror or e}") from e
    except UnicodeDecodeError as e:
        raise SourceError(f"cannot read {rel}: not valid UTF-8 ({e.reason} at byte {e.start})") from e


# ---------------------------------------------------------------- repo facts

def frontmatter(path: Path) -> str:
    """The YAML frontmatter of an agent file (between the first two --- lines), or "" when it has none."""
    text = read(path.relative_to(REPO_ROOT).as_posix())
    m = re.match(r"---\r?\n(.*?)\r?\n---", text, re.DOTALL)
    return m.group(1) if m else ""


def load_grades() -> tuple[dict[str, dict[str, str]], dict[str, str]]:
    """Latest grade per distinct item, by kind. A later entry for an item wins. A missing grade file is a SourceError."""
    grades: dict[str, dict[str, str]] = {}
    source: dict[str, str] = {}
    for name in GRADE_FILES:
        rel = f"{GRADES_DIR}/{name}"
        try:
            entries = json.loads(read(rel))
        except json.JSONDecodeError as e:
            raise SourceError(f"{rel} is not valid JSON: {e}") from e
        if not isinstance(entries, list):
            raise SourceError(f"{rel} must hold a JSON list of grade entries")
        for i, entry in enumerate(entries, 1):
            if not isinstance(entry, dict) or not all(isinstance(entry.get(k), str) for k in ("batch", "item", "grade")):
                raise SourceError(f"{rel} entry {i} needs string fields batch, item and grade")
            kind = entry["batch"].split("-", 1)[0]
            grades.setdefault(kind, {})[entry["item"]] = entry["grade"]
            source[entry["item"]] = rel
    return grades, source


def source_dir(rel: str) -> Path:
    """A source folder the counts come from. A missing one is a SourceError, never a count of 0."""
    path = REPO_ROOT / rel
    if not path.is_dir():
        raise SourceError(f"cannot read {rel}/: folder is missing")
    return path


def source_files(rel: str, pattern: str) -> list[Path]:
    """The files a count comes from. A missing folder or one with no matching file is a SourceError, never a count of 0."""
    files = sorted(source_dir(rel).glob(pattern))
    if not files:
        raise SourceError(f"cannot read {rel}/: no {pattern} files")
    return files


def gather_facts() -> Facts:
    agent_files = source_files(AGENTS_DIR, "*.md")
    agents = sorted(p.stem for p in agent_files)
    memory_agents = sorted(p.stem for p in agent_files if re.search(r"^memory:", frontmatter(p), re.M))
    rag_agents = [p for p in agent_files if re.search(r"^tools:.*mcp__dayz-rag__", frontmatter(p), re.M)]
    hooks = [p for p in source_files(HOOKS_DIR, "*.py") if not p.name.startswith("test_")]
    if not hooks:
        raise SourceError(f"cannot read {HOOKS_DIR}/: no hook scripts (only test_*.py files)")
    skills = sorted(p.parent.name for d in (REPO_ROOT / "skills", REPO_ROOT / ".claude" / "skills")
                    for p in d.glob("*/SKILL.md") if not p.parent.name.startswith("_"))
    eval_agents = sorted(p.stem for p in source_files(EVAL_QUESTIONS, "*.json") if p.stem in agents)
    grades, source = load_grades()
    core = REPO_ROOT / RULES_CORE
    if not core.is_file():
        raise SourceError(f"cannot read {RULES_CORE}")
    topics = {p.name: line_count(p) for p in source_files(RULES_TOPICS, "*.md")}
    for kind, items in grades.items():
        if kind not in GRADE_KINDS:
            rel = source[next(iter(items))]
            raise SourceError(f"{rel} has a batch starting {kind!r}; the grade counts only know batches "
                              f"starting {', '.join(GRADE_KINDS)}, so its items would be left out")
    facts = Facts(agents, memory_agents, skills, eval_agents, grades, source, line_count(core), topics)

    graded = {k: grades.get(k, {}) for k in GRADE_KINDS}
    aplus = {k: sum(g == "A+" for g in v.values()) for k, v in graded.items()}
    g = f"{GRADES_DIR}/{GRADE_FILES[0]}"
    gs = f"{GRADES_DIR}/{GRADE_FILES[1]}"
    facts.counts = {
        "agents": (len(agents), "agent files in agents/"),
        "skills": (len(skills), "skill folders with a SKILL.md in skills/ and .claude/skills/"),
        "hooks": (len(hooks), f"hook scripts in {HOOKS_DIR}/ (not test_*.py)"),
        "eval_agents": (len(eval_agents), "agents with a question file in evals/questions/"),
        "memory_agents": (len(memory_agents), "agents with a memory: line in their frontmatter"),
        "rag_agents": (len(rag_agents), "agents whose frontmatter tools: line lists a mcp__dayz-rag__ tool"),
        "graded_agents": (len(graded["agents"]), f"distinct agents in {g}"),
        "graded_skills": (len(graded["skills"]), f"distinct skills in {g}"),
        "graded_shared": (len(graded["shared"]), f"distinct items in {gs}"),
        "graded_total": (sum(len(v) for v in graded.values()), "distinct items in both grade files"),
        "aplus_agents": (aplus["agents"], f"agents whose latest grade in {g} is A+"),
        "aplus_skills": (aplus["skills"], f"skills whose latest grade in {g} is A+"),
        "aplus_shared": (aplus["shared"], f"items whose latest grade in {gs} is A+"),
        "graded_aplus": (sum(aplus.values()), "distinct graded items whose latest grade is A+"),
        "core_lines": (facts.core_lines, f"wc -l {RULES_CORE}"),
        "topic_files": (len(topics), f"topic files in {RULES_TOPICS}/"),
        "topic_min": (min(topics.values()), f"shortest topic file in {RULES_TOPICS}/ (wc -l)"),
        "topic_max": (max(topics.values()), f"longest topic file in {RULES_TOPICS}/ (wc -l)"),
    }
    return facts


# ---------------------------------------------------------------- wiki parsing

@dataclass
class Doc:
    rel: str
    lines: list[str]
    visible: list[bool]
    # (level, title, line index) for every ## / ### heading outside code fences
    headings: list[tuple[int, str, int]]

    def section(self, title: str) -> tuple[int, int] | None:
        """Line index range of the body under heading `title` (to the next heading of the same or higher level)."""
        for n, (level, t, i) in enumerate(self.headings):
            if t == title:
                end = next((j for lv, _, j in self.headings[n + 1:] if lv <= level), len(self.lines))
                return i, end
        return None


def hidden_slugs() -> set[str]:
    """Slugs of the sections content.js hides. A missing HIDDEN set is a SourceError, so hidden sections are never checked by accident."""
    m = re.search(r"const HIDDEN = new Set\(\[(.*?)\]\)", read(CONTENT_JS), re.DOTALL)
    if m is None:
        raise SourceError(f"cannot read {CONTENT_JS}: no `const HIDDEN = new Set([...])` listing the hidden sections")
    return set(re.findall(r"['\"]([^'\"]+)['\"]", m.group(1)))


def load_doc(rel: str, hidden: set[str]) -> Doc:
    lines = read(rel).split("\n")
    visible, headings = [], []
    in_fence, shown = False, True
    for i, line in enumerate(lines):
        if line.startswith("```"):
            in_fence = not in_fence
        m = None if in_fence else re.match(r"(#{2,3}) (.+)", line)
        if m:
            headings.append((len(m.group(1)), m.group(2).strip(), i))
            if len(m.group(1)) == 2:
                shown = slugify(m.group(2).strip()) not in hidden
        visible.append(shown)
    return Doc(rel, lines, visible, headings)


def table_rows(doc: Doc, start: int, end: int):
    """(line index, cells) for every body row of the markdown tables in a range."""
    for i in range(start, end):
        line = doc.lines[i].strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", line.strip("|"))]
        if set("".join(cells)) <= set("-: "):
            continue  # separator row
        yield i, cells


def item_key(label: str) -> str:
    """Normalise a grade-table label: no backticks, escapes, 'Pack:' prefix or trailing '(...)'."""
    s = label.replace("`", "").replace("\\_", "_").strip()
    s = re.sub(r"^Pack:\s*", "", s)
    s = s.split(" (", 1)[0].strip().lower()
    return ITEM_ALIASES.get(s, s)


# ---------------------------------------------------------------- checks

def check_names(facts: Facts, guide: Doc, skills_doc: Doc) -> list[Problem]:
    problems: list[Problem] = []

    def compare(doc: Doc, anchor: int, named: dict[str, list[int]], real: list[str], what: str, where: str):
        for name in sorted(set(real) - set(named)):
            problems.append(Problem(doc.rel, anchor + 1, f"{what} `{name}` exists but is not listed in {where}"))
        for name, rows in sorted(named.items()):
            if name not in real:
                problems.append(Problem(doc.rel, rows[0] + 1, f"names {what} `{name}`, which does not exist"))
            elif len(rows) > 1:
                problems.append(Problem(doc.rel, rows[1] + 1, f"{what} `{name}` is listed {len(rows)} times (first at line {rows[0] + 1})"))

    span = guide.section(AGENTS_HEADING)
    if span is None:
        problems.append(Problem(guide.rel, 1, f'no "## {AGENTS_HEADING}" section to check the agent list against'))
    else:
        named: dict[str, list[int]] = {}
        for i, cells in table_rows(guide, *span):
            if cells[0] == "Agent":
                continue
            for name in re.findall(r"`([\w-]+)`", cells[0]):
                named.setdefault(name, []).append(i)
        compare(guide, span[0], named, facts.agents, "agent", f'the "## {AGENTS_HEADING}" tables')

    named = {}
    for i, cells in table_rows(skills_doc, 0, len(skills_doc.lines)):
        m = re.fullmatch(r"`?/([\w-]+)`?", cells[0])
        if m:
            named.setdefault(m.group(1), []).append(i)
    compare(skills_doc, 0, named, facts.skills, "skill", "the skills table")
    return problems


def check_grade_table(facts: Facts, doc: Doc) -> list[Problem]:
    span = doc.section(GRADE_TABLE_HEADING)
    if span is None:
        return [Problem(doc.rel, 1, f'no "{GRADE_TABLE_HEADING}" section with the grade table')]
    graded: dict[str, tuple[str, str]] = {}
    problems: list[Problem] = []
    for kind in facts.grades.values():
        for item, grade in kind.items():
            key = item_key(item)
            if key in graded:
                # One would drop out of the check unseen, and its row would read as a duplicate.
                problems.append(Problem(doc.rel, span[0] + 1, f"graded items {graded[key][0]!r} and {item!r} have the same "
                                        f"row label {key!r} once backticks, a 'Pack:' prefix and a trailing '(...)' are dropped; "
                                        "rename one in the grade files so each can be checked"))
            else:
                graded[key] = (item, grade)
    seen: dict[str, int] = {}
    for i, cells in table_rows(doc, *span):
        if cells[0] == "Item" or not any(cells[1:]):
            continue  # header or category row
        key = item_key(cells[0])
        if key in seen:
            problems.append(Problem(doc.rel, i + 1, f"{cells[0]} appears again (first at line {seen[key] + 1}); each graded item belongs in one row"))
            continue
        seen[key] = i
        if key not in graded:
            problems.append(Problem(doc.rel, i + 1, f"{cells[0]} is not in the grade files ({GRADES_DIR}/)"))
            continue
        item, grade = graded[key]
        if cells[-1] != grade:
            problems.append(Problem(doc.rel, i + 1, f"final grade of {cells[0]} is {cells[-1]!r}, expected {grade!r} (latest in {facts.grade_source[item]})"))
    for key, (item, _) in graded.items():
        if key not in seen:
            problems.append(Problem(doc.rel, span[0] + 1, f"graded item {item!r} ({facts.grade_source[item]}) has no row in this table"))
    return problems


def _number(token: str) -> int:
    return int(token) if token.isdigit() else NUMBER_WORDS.index(token.lower())


def _spell(value: int, like: str) -> str:
    """value written the way `like` is: digits, or a word with the same capital."""
    if like.isdigit() or value >= len(NUMBER_WORDS):
        return str(value)
    word = NUMBER_WORDS[value]
    return word.capitalize() if like[:1].isupper() else word


def check_claims(facts: Facts, docs: dict[str, Doc]) -> list[Problem]:
    """Every claim in CLAIMS is found in a visible line of its file, and each number in it is right."""
    problems: list[Problem] = []
    for claim in CLAIMS:
        doc = docs[claim.file]
        found = False
        for i, line in enumerate(doc.lines):
            if not doc.visible[i]:
                continue  # hidden sections are never shown to readers
            for m in claim_regex(claim).finditer(line):
                found = True
                aplus, total = facts.counts["graded_aplus"][0], facts.counts["graded_total"][0]
                # A sentence that must be reworded keeps its numbers reported, but
                # unfixed: rewriting one would only make the false sentence look right.
                reword = claim.all_aplus and aplus != total
                if reword:
                    problems.append(Problem(doc.rel, i + 1, f"says every graded item is A+, but {aplus} of {total} are; "
                                            "reword this sentence"))
                for group, name in enumerate(claim.facts, 1):
                    token = m.group(group)
                    expected, why = facts.counts[name]
                    if _number(token) != expected:
                        fix = None if reword else (m.start(group), m.end(group), _spell(expected, token))
                        problems.append(Problem(doc.rel, i + 1, f"says {token}, expected {expected} ({why})", fix, token))
        if not found:
            shown = claim.text.replace("{N}", "N")
            problems.append(Problem(doc.rel, 0, f'claim not found: "{shown}"; update the CLAIMS table in sync.py'))
    return problems


def run_checks() -> tuple[Facts, list[Problem]]:
    """All problems, in file and line order. Raises SourceError when a source cannot be read."""
    facts = gather_facts()
    hidden = hidden_slugs()
    guide, team, skills_doc = (load_doc(rel, hidden) for rel in (GUIDE, TEAM, SKILLS_TABLE))
    app_lines = read(APP_JSX).split("\n")
    app = Doc(APP_JSX, app_lines, [True] * len(app_lines), [])
    problems = (check_names(facts, guide, skills_doc)
                + check_claims(facts, {GUIDE: guide, TEAM: team, APP_JSX: app})
                + check_grade_table(facts, guide)
                + check_grade_table(facts, team))
    problems.sort(key=lambda p: (p.file, p.line, p.fix[0] if p.fix else -1))
    return facts, problems


# ---------------------------------------------------------------- modes

def report(problems: list[Problem], quiet: bool) -> int:
    fixable = sum(p.fix is not None for p in problems)
    if quiet:
        if problems:
            hook_notice(f"docs-sync: {len(problems)} wiki problem(s), {fixable} fixable with --apply. Run /docs-sync.")
        return 0
    if not problems:
        print("[OK] The wiki matches the source.")
        return 0
    for p in problems:
        print(p)
    print(f"\n{len(problems)} problem(s); {fixable} fixable with --apply, the rest need a hand edit.")
    return 1


def print_map(facts: Facts) -> int:
    c = facts.counts
    print("names   guide.md \"## Agents\" tables  <->  agents/*.md "
          f"({c['agents'][0]}); none missing, none unknown, none twice")
    print(f"names   skills-table.md rows         <->  skills/*/SKILL.md + .claude/skills/*/SKILL.md ({c['skills'][0]})")
    print(f"claims  each found in a section {CONTENT_JS} does not hide; N is digits or a word up to twenty:")
    for claim in CLAIMS:
        values = ", ".join(f"{name}={c[name][0]}" for name in claim.facts)
        print(f"          {claim.file}: \"{claim.text.replace('{N}', 'N')}\"  ({values})")
    print("        the facts:")
    for name, (value, why) in c.items():
        print(f"          {name:<14} = {value:<4} {why}")
    print(f"grades  \"{GRADE_TABLE_HEADING}\" tables in guide.md and team.md  <->  {GRADES_DIR}/"
          f"{' + '.join(GRADE_FILES)} ({c['graded_total'][0]} items): one row each, last column = latest grade")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Check the React wiki (its own repository) against this repository.")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="Report problems (default)")
    mode.add_argument("--apply", action="store_true", help="Rewrite wrong numbers in matched claims in place")
    mode.add_argument("--map", action="store_true", help="Print what each check compares")
    p.add_argument("--quiet", action="store_true", help="Stop hook mode (check only): silent when in sync, otherwise one JSON systemMessage line; always exit 0")
    p.add_argument("--dry-run", action="store_true", help="With --apply: print the changes without writing")
    args = p.parse_args(argv)
    if args.dry_run and not args.apply:
        p.error("--dry-run only works with --apply")
    if args.quiet and (args.apply or args.map):
        p.error("--quiet only works with --check")
    if wiki_dir() is None:
        # Public clones and CI have no wiki: nothing to check is not a failure.
        if not args.quiet:
            print(f"{h.WARN}no wiki to check: clone {WIKI_REPO} next to this repo, or set {WIKI_ENV}")
        return 0

    try:
        facts, problems = run_checks()
    except SourceError as e:
        if args.quiet:
            hook_notice(f"docs-sync: check skipped: {e}")
            return 0
        print(f"{h.FAIL}{e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        # Ctrl+C during the check, before --apply could write anything.
        if args.quiet:
            return 0
        print(f"{h.FAIL}stopped; nothing was written", file=sys.stderr)
        return 1
    except Exception as e:
        # The Stop hook must never print a traceback or block; any other failure skips the check too.
        if args.quiet:
            hook_notice(f"docs-sync: check skipped: {type(e).__name__}: {e}")
            return 0
        print(f"{h.FAIL}check failed: {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    if args.map:
        return print_map(facts)
    if args.apply:
        apply = h.load_module("docs_sync_apply", Path(__file__).parent / "apply.py")
        try:
            apply.apply_fixes(REPO_ROOT, problems, dry_run=args.dry_run, resolve=source_path)
        except apply.ReadError as e:
            print(f"{h.FAIL}{e}", file=sys.stderr)
            return 1
        except OSError as e:
            print(f"{h.FAIL}could not write the wiki: {e}", file=sys.stderr)
            # apply.py notes each file it could not put back; say which ones.
            for note in getattr(e, "__notes__", []):
                print(f"{h.FAIL}{note}", file=sys.stderr)
            return 1
        except KeyboardInterrupt as e:
            # apply.Stopped says what state the wiki was left in; a plain Ctrl+C
            # came before any write.
            print(f"{h.FAIL}{e if isinstance(e, apply.Stopped) else 'stopped; nothing was written'}", file=sys.stderr)
            return 1
        remaining = [pr for pr in problems if pr.fix is None]
        if remaining:
            print(f"\n{len(remaining)} problem(s) need a hand edit:")
            for pr in remaining:
                print(pr)
            return 1
        return 0
    return report(problems, args.quiet)


if __name__ == "__main__":
    sys.exit(main())
