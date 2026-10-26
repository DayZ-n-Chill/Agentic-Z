"""DayZ RAG indexer.

Walk vanilla DayZ source on P:\\, chunk per file type, embed via Voyage AI
(`voyage-code-3` by default, 1024-dim), store in LanceDB at
~/.claude/dayz-search-index/ for the dayz-rag MCP server.

Gates on /dayz-preflight (it reads vanilla data on P:\\). A live token and cost
estimate prints during the embed loop; see references/cost-and-free-tier.md for
the free-tier check.

Run:
    python skills/dayz-search-index/index.py --full   # first time / rebuild
    python skills/dayz-search-index/index.py --status # show manifest
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import re
import sys
import time
from array import array
from pathlib import Path
from typing import Iterator, Optional
from xml.parsers import expat

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "_shared"))
import skill_helpers as h  # noqa: E402

# .env/API-key loading and the Voyage retry rule live next to the MCP server so
# indexing and searching read the same key the same way.
sys.path.insert(0, str(_HERE.parents[1] / ".claude" / "mcp" / "dayz-rag"))
import voyage_common  # noqa: E402

INDEX_ROOT = Path.home() / ".claude" / "dayz-search-index"
TABLE_NAME = "chunks"
# The new index is written here first and only swapped into TABLE_NAME once
# the write succeeded, so a failed write never leaves the server without a table.
STAGING_TABLE_NAME = TABLE_NAME + "_staging"
P_ROOT = Path("P:\\")

# Cost-runaway backstop: refuse to embed more than this many chunks without
# --force. A vanilla build is far below it, so hitting it means the walk scope grew.
CHUNK_CEILING = 150_000

# Voyage model. Override via the VOYAGE_MODEL env var. The LanceDB table is
# fixed at EMBED_DIM, so only choose models that emit 1024-dim vectors.
DEFAULT_EMBED_MODEL = "voyage-code-3"
EMBED_DIM = 1024

# Voyage API limits per request (voyage-code-3): 128 texts max, 120k tokens max.
# We pack batches dynamically up to TOKEN_BUDGET_PER_BATCH (under the 120k cap)
# OR TEXT_LIMIT_PER_BATCH, whichever hits first.
TEXT_LIMIT_PER_BATCH = 128
# Code tokenizes denser than prose (punctuation, brackets, short identifiers):
# the Voyage tokenizer measured ~1.8 chars/token on Enforce Script. Estimating
# at 1.8 with a 75k token budget keeps real batch tokens well under the 120k cap.
TOKEN_BUDGET_PER_BATCH = 75_000
CHARS_PER_TOKEN_EST = 1.8
# Largest text sent to the embedder (~3.3k tokens at 1.8 chars/token, far under
# voyage-code-3's 32k context). Class-style files are split into windows of at
# most this size, so their text is never cut; the embed step still clips other
# chunk types to it.
EMBED_MAX_CHARS = 6000

# Approximate $ per 1M input tokens, used only for the live cost estimate and
# the manifest's cost_estimate_usd. Rates change; the authoritative source is
# https://docs.voyageai.com/docs/pricing
COST_PER_MTOKEN = {
    "voyage-code-3": 0.18,
    "voyage-4-large": 0.12,
    "voyage-4": 0.06,
    "voyage-4-lite": 0.02,
    "voyage-3-large": 0.18,
    "voyage-3.5": 0.06,
    "voyage-3.5-lite": 0.02,
}


def _rate(model: str) -> Optional[float]:
    """Estimated $ per 1M tokens for model, or None when the model isn't in the table."""
    return COST_PER_MTOKEN.get(model)

OK = "[OK]   "
WARN = "[WARN] "
FAIL = "[FAIL] "
INFO = "[INFO] "

# Default free-tier budget for the pre-build projection check. Plans differ;
# override with the VOYAGE_FREE_TIER_TOKENS env var or pass --ignore-tier-warning.
VOYAGE_FREE_TIER_BUDGET = 200_000_000
TIER_WARN_THRESHOLD = 0.80  # warn when projected usage hits 80%
USAGE_LOG_NAME = "usage.log"
# Written by /dayz-search-download to name the installed release. A local
# build replaces that index, so a successful build removes the file.
RELEASE_TAG_FILE = "release-tag.txt"


def _usage_log_path() -> Path:
    return INDEX_ROOT / USAGE_LOG_NAME


def _read_logged_usage_tokens() -> int:
    """Sum every token logged in usage.log.

    Voyage's pricing page gives the free tokens per account and names no
    monthly reset, so every logged build counts against them.

    Doesn't fail on missing file or malformed lines: those are treated as
    zero contribution. We'd rather under-warn than crash.
    """
    path = _usage_log_path()
    if not path.exists():
        return 0
    total = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            total += int(json.loads(line).get("tokens", 0))
        except (json.JSONDecodeError, ValueError, TypeError, AttributeError):
            continue
    return total


def _append_usage_entry(tokens: int, cost_usd: float, skill: str) -> None:
    """Append one JSONL entry to the usage log. Every call adds a line, so call it once per build."""
    entry = {
        "timestamp_unix": int(time.time()),
        "timestamp_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "tokens": int(tokens),
        "cost_estimated_usd": round(float(cost_usd), 4),
        "skill": skill,
    }
    path = _usage_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def _free_tier_budget() -> int:
    """The free-tier token budget: VOYAGE_FREE_TIER_TOKENS, else VOYAGE_FREE_TIER_BUDGET.

    Raises ValueError with a user-facing message when the variable is set but is
    not a positive whole number.
    """
    raw = os.environ.get("VOYAGE_FREE_TIER_TOKENS", "").strip()
    if not raw:
        return VOYAGE_FREE_TIER_BUDGET
    try:
        budget = int(raw.replace("_", "").replace(",", ""))
    except ValueError:
        budget = 0
    if budget <= 0:
        raise ValueError(
            f"VOYAGE_FREE_TIER_TOKENS must be a positive whole number of tokens "
            f"(for example 200000000), got {raw!r}. Fix or unset it."
        )
    return budget


def _key_hint(api_key: str) -> str:
    """How the key is named in output: its last 4 characters only, so transcripts never hold a usable prefix."""
    return f"ending ...{api_key[-4:]}" if len(api_key) > 8 else "set"


def _check_voyage_tier(
    estimated_tokens: int, ignore_warning: bool, model: str = DEFAULT_EMBED_MODEL
) -> bool:
    """Pre-build tier check. Returns True if the build may proceed.

    On a refusal (the user answers no, or stdin is not interactive) it prints
    one [FAIL] line to stderr saying why, and returns False.

    Uses local cumulative tracking only; Voyage doesn't expose a public
    usage API. The overage estimate uses `model`'s rate from COST_PER_MTOKEN.
    See references/cost-and-free-tier.md for caveats.
    """
    budget = _free_tier_budget()
    used = _read_logged_usage_tokens()
    projected = used + estimated_tokens
    pct_projected = projected / budget

    if pct_projected < TIER_WARN_THRESHOLD:
        return True

    pct_used = used / budget
    print()
    print(f"{WARN} Voyage free-tier projection:")
    print(f"        Logged so far:     {used:,} tokens ({pct_used*100:.1f}% of {budget/1_000_000:.0f}M)")
    print(f"        This build est:    {estimated_tokens:,} tokens")
    print(f"        Projected total:   {projected:,} tokens ({pct_projected*100:.1f}% of free tier)")
    if pct_projected > 1.0:
        rate = _rate(model)
        if rate is None:
            print(f"        Past free tier: no local rate for {model}; check Voyage pricing.")
        else:
            cost_over = ((projected - budget) / 1_000_000) * rate
            print(f"        Past free tier, estimated overage: ${cost_over:.2f}")
    print()
    print("        Caveats:")
    print("        - Counter is local. Other apps using your VOYAGE_API_KEY are NOT counted.")
    print("        - Authoritative usage at https://dash.voyageai.com")
    print("        - Voyage gives free tokens per account and names no monthly reset.")
    print()

    if ignore_warning:
        print(f"{INFO} --ignore-tier-warning passed; proceeding anyway.")
        return True

    try:
        answer = input("        Continue? [y/N]: ").strip().lower()
    except EOFError:
        # Non-interactive shell: nobody can answer, so refuse by default.
        print()
        print(
            f"{FAIL} The free-tier prompt needs an answer, but this shell is not interactive. "
            f"Re-run with --ignore-tier-warning to build anyway. No tokens consumed.",
            file=sys.stderr,
        )
        return False
    if answer in ("y", "yes"):
        return True
    print(f"{FAIL} Cancelled at the free-tier prompt. No tokens consumed.", file=sys.stderr)
    return False


def _require_deps() -> None:
    """Exit with a clear message if the indexer's Python deps are missing."""
    try:
        import lancedb  # noqa: F401
        import tqdm  # noqa: F401
        import voyageai  # noqa: F401
        import dotenv  # noqa: F401
    except ImportError as exc:
        print(
            f"{FAIL} Missing Python dependency: {exc.name}\n"
            f"        Install the indexer's requirements first:\n"
            f"            python -m pip install -r \"{_HERE / 'requirements.txt'}\"",
            file=sys.stderr,
        )
        sys.exit(1)


def _load_env_and_key() -> str:
    """Return the Voyage API key (see voyage_common.load_api_key). Exit 1 if missing."""
    try:
        return voyage_common.load_api_key()
    except RuntimeError as exc:
        print(f"{FAIL} {exc}", file=sys.stderr)
        sys.exit(1)


# --------------- chunkers ---------------
#
# Enforce Script (.c), config.cpp, and .layout all share a `class X { ... }`
# top-level block structure. One walker handles all three.

_CLASS_HEADER = (
    r"\b(?:modded\s+)?class\s+(?P<name>[A-Za-z_]\w*)"
    r"(?:\s*:\s*[A-Za-z_]\w*)?"
    r"(?:\s+extends\s+[A-Za-z_]\w*)?"
    r"\s*\{"
)
# At file scope: a comment, a string or a class header, whichever comes first.
_TOP_RE = re.compile(r'//|/\*|"|' + _CLASS_HEADER, re.IGNORECASE)
# Inside a class body: a comment, a string or a brace.
_BODY_RE = re.compile(r'//|/\*|"|[{}]')
# What is left of a gap once comments are removed; empty means nothing to index.
_COMMENTS_RE = re.compile(r"//[^\n]*|/\*.*?(?:\*/|\Z)", re.DOTALL)


def _skip_literal(text: str, i: int, escapes: bool = True) -> int:
    """Index just past the comment or string that starts at i.

    A string ends at its closing quote or at the end of its line, so a stray
    quote never swallows the rest of the file. \\" is an escape only when
    escapes is set (Enforce Script .c files); in config.cpp a backslash is a
    path separator, so "MyMod\\" ends at its quote. "" closes the string and
    opens the next one.
    """
    if text.startswith("//", i):
        j = text.find("\n", i)
        return len(text) if j < 0 else j
    if text.startswith("/*", i):
        j = text.find("*/", i + 2)
        return len(text) if j < 0 else j + 2
    j = i + 1  # a double-quoted string
    while j < len(text):
        c = text[j]
        if c == "\\" and escapes:
            j += 2
            continue
        if c in '"\n':
            return j + 1
        j += 1
    return len(text)


def _gap(text: str, a: int, b: int) -> Optional[tuple[str, int, int, str]]:
    """File-scope text between classes (global functions, enums, typedefs), or
    None when it holds only whitespace, comments and the `;` that closes a
    config.cpp class. Leading blank lines are cut."""
    body = text[a:b]
    if not _COMMENTS_RE.sub("", body).replace(";", "").strip():
        return None
    k = a + len(body) - len(body.lstrip())
    a = max(a, text.rfind("\n", a, k) + 1)
    body = text[a:b]
    start_line = text.count("\n", 0, a) + 1
    return "", start_line, start_line + body.count("\n"), body


def _walk_class_blocks(text: str, escapes: bool = True) -> Iterator[tuple[str, int, int, str]]:
    """Yield (name, start_line, end_line, body) for top-level class blocks, and
    ("", ...) for the code between them. Braces and class headers inside comments
    and strings are ignored. An unclosed class is yielded as file-scope text."""
    pos = gap_start = 0
    n = len(text)
    while pos < n:
        m = _TOP_RE.search(text, pos)
        if not m:
            break
        if m.group("name") is None:
            pos = _skip_literal(text, m.start(), escapes)
            continue
        depth, i = 1, m.end()
        while depth:
            b = _BODY_RE.search(text, i)
            if not b:
                break
            tok = b.group()
            if tok == "{":
                depth += 1
                i = b.end()
            elif tok == "}":
                depth -= 1
                i = b.end()
            else:
                i = _skip_literal(text, b.start(), escapes)
        if depth:
            break
        gap = _gap(text, gap_start, m.start())
        if gap:
            yield gap
        start_line = text.count("\n", 0, m.start()) + 1
        end_line = text.count("\n", 0, i) + 1
        yield m.group("name"), start_line, end_line, text[m.start():i]
        pos = gap_start = i
    gap = _gap(text, gap_start, n)
    if gap:
        yield gap


def file_sha256(path: Path) -> Optional[str]:
    """sha256 of the file's bytes, or None when it cannot be read."""
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _split_lines(text: str) -> list[str]:
    """text cut after each "\\n", newlines kept.

    str.splitlines also breaks at \\f, \\v, \\x1c-\\x1e, \\x85 and \\u2028, which
    would put chunk line numbers out of step with the file's real lines.
    """
    parts = text.split("\n")
    lines = [part + "\n" for part in parts[:-1]]
    if parts[-1]:
        lines.append(parts[-1])
    return lines


def _split_windows(body: str, first_line: int, max_chars: int) -> list[tuple[int, int, str]]:
    """Split body into (line_start, line_end, text) windows of at most max_chars.

    A body that fits is returned whole. Otherwise each window ends at the last
    member boundary that fits (a line that starts at brace depth 1 and is not
    itself a brace, i.e. where a method or field of the class begins); with no
    boundary in reach it ends at the last whole line that fits. A single line
    longer than max_chars is sliced, each slice keeping that line's number.
    Nothing is dropped.
    """
    if len(body) <= max_chars:
        return [(first_line, first_line + body.count("\n"), body)]
    lines = _split_lines(body)
    boundaries: set[int] = set()
    depth = 0
    for i, line in enumerate(lines):
        if i > 0 and depth == 1 and not line.lstrip().startswith(("{", "}")):
            boundaries.add(i)
        depth += line.count("{") - line.count("}")

    windows: list[tuple[int, int, str]] = []
    start = 0
    while start < len(lines):
        if len(lines[start]) > max_chars:
            line_no = first_line + start
            text = lines[start]
            windows.extend(
                (line_no, line_no, text[k : k + max_chars]) for k in range(0, len(text), max_chars)
            )
            start += 1
            continue
        size = 0
        end = start  # exclusive
        while end < len(lines) and size + len(lines[end]) <= max_chars:
            size += len(lines[end])
            end += 1
        if end < len(lines):
            cut = max((b for b in boundaries if start < b <= end), default=None)
            if cut is not None:
                end = cut
        windows.append((first_line + start, first_line + end - 1, "".join(lines[start:end])))
        start = end
    return windows


def _block_chunks(path: Path, file_type: str, max_chars: int = EMBED_MAX_CHARS) -> list[dict]:
    """Chunk a class-style file: one chunk per top-level class block, or the
    whole file if there are none. Anything over max_chars is split into
    windows (see _split_windows) that keep the class name as parent_context."""
    text = _read_text(path)
    if not text:
        return []
    blocks = list(_walk_class_blocks(text, escapes=file_type == "c")) or [("", 1, text.count("\n") + 1, text)]
    return [
        {
            "path": str(path),
            "file_type": file_type,
            "parent_context": name,
            "line_start": ws,
            "line_end": we,
            "content": window,
        }
        for name, s, _e, body in blocks
        for ws, we, window in _split_windows(body, s, max_chars)
    ]


def chunk_rvmat(path: Path, seen_hashes: set[str]) -> list[dict] | None:
    """Whole-file chunk, content-deduped via SHA-256."""
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    digest = hashlib.sha256(raw).hexdigest()
    if digest in seen_hashes:
        return None
    seen_hashes.add(digest)
    text = raw.decode("utf-8", errors="replace")
    return [
        {
            "path": str(path),
            "file_type": "rvmat",
            "parent_context": digest[:12],
            "line_start": 1,
            "line_end": text.count("\n") + 1,
            "content": text[:4000],
        }
    ]


XML_BATCH_SIZE = 50  # max top-level elements in one chunk; EMBED_MAX_CHARS also caps it


def _xml_outline(text: str) -> tuple[str, list[tuple[str, int, int]], int, int]:
    """Parse text and return (root_tag, elements, first_line, last_line).

    elements holds (name, start_line, end_line) for each top-level child, in
    document order; name is its name/Name attribute, else its tag. first_line
    and last_line bound the text worth indexing: from the line after the root
    start tag (line 1 when comments or processing instructions come before the
    root) to the last element's end line (the last line of the file when
    comments, processing instructions or text follow it). Raises
    expat.ExpatError on malformed XML.
    """
    data = text.encode("utf-8")
    # The text is already decoded, so its own encoding declaration no longer applies.
    parser = expat.ParserCreate(encoding="utf-8")
    elements: list[tuple[str, int, int]] = []
    depth = 0
    root_tag = ""
    root_line = 1
    current = ("", 0)
    before_root = False  # a comment or PI ahead of the root element
    extra_line = 0  # last line holding a comment, PI or text outside the elements

    def on_start(name, attrs):
        nonlocal depth, root_tag, root_line, current
        depth += 1
        if depth == 1:
            root_tag, root_line = name, parser.CurrentLineNumber
        elif depth == 2:
            current = (attrs.get("name") or attrs.get("Name") or name, parser.CurrentLineNumber)

    def on_end(_name):
        nonlocal depth
        if depth == 2:
            # An end tag may break before its ">" (</type\n>); an empty
            # element is reported after its "/>", so its line is already right.
            i = parser.CurrentByteIndex
            end = parser.CurrentLineNumber
            if data.startswith(b"</", i):
                end += data.count(b"\n", i, data.find(b">", i))
            elements.append((current[0], current[1], end))
        depth -= 1

    def on_extra(*_args):
        nonlocal before_root, extra_line
        if not root_tag:
            before_root = True
        elif depth <= 1:
            extra_line = parser.CurrentLineNumber

    def on_text(chars):
        if depth == 1 and chars.strip():
            on_extra()

    parser.StartElementHandler = on_start
    parser.EndElementHandler = on_end
    parser.CommentHandler = on_extra
    parser.ProcessingInstructionHandler = on_extra
    parser.CharacterDataHandler = on_text
    parser.Parse(data, True)
    total_lines = len(_split_lines(text))
    first_line = 1 if before_root else root_line + 1
    last_line = elements[-1][2] if elements else total_lines
    if extra_line > last_line:
        last_line = total_lines
    return root_tag, elements, first_line, last_line


def _window_chunks(path: Path, file_type: str, text: str, header: str = "") -> list[dict]:
    """Whole-file chunks for text with no class blocks: one chunk when it fits in
    EMBED_MAX_CHARS, else windows from _split_windows with their real line ranges.

    header (a CSV header line) is repeated at the top of every window so each
    one still names its columns; the line range is that of the window's rows.
    A header longer than EMBED_MAX_CHARS // 2 is not repeated (it would leave
    too little room for rows), so only the first window of such a file has it.
    """
    if len(text) <= EMBED_MAX_CHARS:
        windows = [(1, text.count("\n") + 1, text)]
    elif header and len(header) <= EMBED_MAX_CHARS // 2:
        body = text[len(header):]
        windows = [(ws, we, header + w) for ws, we, w in _split_windows(body, 2, EMBED_MAX_CHARS - len(header))]
    else:
        windows = _split_windows(text, 1, EMBED_MAX_CHARS)
    return [
        {
            "path": str(path),
            "file_type": file_type,
            "parent_context": "",
            "line_start": ws,
            "line_end": we,
            "content": window,
        }
        for ws, we, window in windows
    ]


def chunk_xml(path: Path, file_type: str = "xml", batch_size: int = XML_BATCH_SIZE) -> list[dict]:
    """Chunk XML by groups of top-level child elements. Caps explosion on
    types.xml-style files (many entries per chunk instead of one per entry).

    - Small files (<4KB): one whole-file chunk
    - Files with 5 or more top-level elements: each chunk is a slice of the
      file's own lines, so comments (commented-out entries included),
      processing instructions and formatting are kept as written. An element's
      slice runs from the line after the previous element up to its own end
      line, so the comments above it travel with it; comments after the last
      element go into the last chunk. Elements sharing a line stay together.
      Consecutive elements are batched until the next one would push the chunk
      past EMBED_MAX_CHARS (or past batch_size elements); a slice larger than
      EMBED_MAX_CHARS on its own is windowed with _split_windows. No text
      inside the root element is cut. The lines before the root's first child
      (XML declaration, DOCTYPE, root start tag) and the root's end tag are
      left out, unless a comment or processing instruction sits before the
      root or after the last element, in which case those lines are kept too.
    - Fewer elements, or a file that does not parse: whole-file windows (_window_chunks)
    """
    text = _read_text(path)
    if not text:
        return []
    if len(text) < 4000:
        return [
            {
                "path": str(path),
                "file_type": file_type,
                "parent_context": "",
                "line_start": 1,
                "line_end": text.count("\n") + 1,
                "content": text,
            }
        ]
    try:
        root_tag, elements, first_line, last_line = _xml_outline(text)
    except expat.ExpatError:
        return _window_chunks(path, file_type, text)
    if len(elements) < 5:
        return _window_chunks(path, file_type, text)

    lines = _split_lines(text)
    # [first name, last name, element count, line_start, line_end] per slice.
    slices: list[list] = []
    for name, start, end in elements:
        if slices and start <= slices[-1][4]:  # shares a line with the previous slice
            slices[-1][1] = name
            slices[-1][2] += 1
            slices[-1][4] = max(slices[-1][4], end)
        else:
            line_start = slices[-1][4] + 1 if slices else min(first_line, start)
            slices.append([name, name, 1, line_start, end])
    slices[-1][4] = max(slices[-1][4], last_line)

    def label(first: str, last: str, count: int) -> str:
        return f"{root_tag} > {first}" if count == 1 else f"{root_tag} > {first}..{last} ({count} items)"

    chunks: list[dict] = []

    def add(parent_context: str, line_start: int, line_end: int, content: str) -> None:
        chunks.append(
            {
                "path": str(path),
                "file_type": file_type,
                "parent_context": parent_context,
                "line_start": line_start,
                "line_end": line_end,
                "content": content,
            }
        )

    batch: list[tuple[list, str]] = []  # (slice, its text)

    def flush() -> None:
        if batch:
            first, last = batch[0][0], batch[-1][0]
            count = sum(s[2] for s, _ in batch)
            add(label(first[0], last[1], count), first[3], last[4], "".join(body for _, body in batch))
            batch.clear()

    for s in slices:
        body = "".join(lines[s[3] - 1 : s[4]])
        if len(body) > EMBED_MAX_CHARS:
            flush()
            for ws, we, window in _split_windows(body, s[3], EMBED_MAX_CHARS):
                add(label(s[0], s[1], s[2]), ws, we, window)
            continue
        if batch and (
            sum(len(b) for _, b in batch) + len(body) > EMBED_MAX_CHARS
            or sum(x[2] for x, _ in batch) + s[2] > batch_size
        ):
            flush()
        batch.append((s, body))
    flush()
    return chunks


def chunk_whole_file(path: Path, file_type: str) -> list[dict]:
    """json/csv: one chunk per file, windowed when it passes EMBED_MAX_CHARS.

    A CSV's header line is repeated at the top of each window when it is at
    most EMBED_MAX_CHARS // 2 characters (see _window_chunks).
    """
    text = _read_text(path)
    if not text:
        return []
    header = _split_lines(text)[0] if file_type == "csv" else ""
    return _window_chunks(path, file_type, text, header)


# --------------- walk config ---------------

# Top-level vanilla folders to scan under P:\. Mods, junctions to user mod
# projects, and DayZ Tools binary dirs are NOT in this list: that's the
# implicit exclusion.
VANILLA_FOLDERS = ["scripts", "gui", "dz", "core", "graphics", "languagecore"]

# File-extension -> file_type tag stored on each chunk. The chunker is
# selected by file_type in the walk loop.
EXT_TYPE_MAP = {
    ".c": "c",
    ".cpp": "cpp",
    ".hpp": "hpp",
    ".h": "h",
    ".layout": "layout",
    ".cfg": "cfg",
    ".rvmat": "rvmat",
    ".xml": "xml",
    ".json": "json",
    ".csv": "csv",
}

# Class-block chunker handles all "class X { ... }" style files.
CLASS_BLOCK_TYPES = {"c", "cpp", "hpp", "h", "layout", "cfg"}
WHOLE_FILE_TYPES = {"json", "csv"}


# --------------- Voyage embedding ---------------


def _estimate_tokens(text: str) -> int:
    """Local token estimate for one text: len / CHARS_PER_TOKEN_EST, at least 1."""
    return max(1, int(len(text) / CHARS_PER_TOKEN_EST))


def _pack_batches(texts: list[str]) -> Iterator[list[str]]:
    """Yield batches that respect both Voyage limits: max TEXT_LIMIT_PER_BATCH
    items AND max ~TOKEN_BUDGET_PER_BATCH tokens (estimated locally as
    len/CHARS_PER_TOKEN_EST). Single oversize chunks pass through alone;
    truncation=True on the API call handles the actual cap."""
    batch: list[str] = []
    batch_tokens = 0
    for t in texts:
        est = _estimate_tokens(t)
        if batch and (
            batch_tokens + est > TOKEN_BUDGET_PER_BATCH
            or len(batch) >= TEXT_LIMIT_PER_BATCH
        ):
            yield batch
            batch = []
            batch_tokens = 0
        batch.append(t)
        batch_tokens += est
    if batch:
        yield batch


EMBED_ATTEMPTS = 5

# Every embedded batch is appended here as it comes back, so a build that
# fails or is interrupted late does not pay for the finished batches again:
# the next run reuses them. A successful build deletes the file. Each record is
# a 32-byte sha256 of (model, text) followed by EMBED_DIM float32 values.
CHECKPOINT_NAME = "embed-checkpoint.bin"
_KEY_BYTES = 32
_RECORD_BYTES = _KEY_BYTES + EMBED_DIM * 4


def _checkpoint_key(model: str, text: str) -> bytes:
    """Checkpoint key for one text: a vector is reused only for the same model and the same text."""
    return hashlib.sha256(f"{model}\0{text}".encode("utf-8")).digest()


def _load_checkpoint(path: Path) -> dict[bytes, list[float]]:
    """Read the vectors saved by an earlier, unfinished build (key -> vector).

    A record cut short by a crash or Ctrl+C mid-write is dropped and the file
    truncated to its whole records, so later appends stay aligned. A missing
    or unreadable file means nothing to reuse.
    """
    try:
        data = path.read_bytes()
    except OSError:
        return {}
    whole = len(data) - len(data) % _RECORD_BYTES
    if whole != len(data):
        with contextlib.suppress(OSError), path.open("r+b") as f:
            f.truncate(whole)
    saved: dict[bytes, list[float]] = {}
    for off in range(0, whole, _RECORD_BYTES):
        vec = array("f")
        vec.frombytes(data[off + _KEY_BYTES : off + _RECORD_BYTES])
        saved[data[off : off + _KEY_BYTES]] = vec.tolist()
    return saved


class EmbedError(Exception):
    """The embed stopped for good. Carries the tokens already billed for the
    batches that succeeded, so the caller can log them before exiting.

    kind is "transient" (still failing after EMBED_ATTEMPTS), "rejected" (a
    non-transient Voyage error such as a bad key), "response" (wrong vector
    count or dimension), "checkpoint" (the checkpoint file could not be
    written) or "interrupted" (Ctrl+C).
    """

    def __init__(self, cause: BaseException, tokens_used: int, transient: bool, kind: Optional[str] = None):
        self.cause = cause
        self.tokens_used = tokens_used
        self.transient = transient
        self.kind = kind or ("transient" if transient else "rejected")
        detail = " ".join(str(cause).split()) or "no message"
        super().__init__(f"{type(cause).__name__}: {detail}")


def embed_or_fail(
    texts: list[str],
    model: str,
    api_key: str,
    saved: Optional[dict[bytes, list[float]]] = None,
    checkpoint: Optional[Path] = None,
) -> Optional[tuple[list[list[float]], int]]:
    """Run embed_all. On failure or Ctrl+C, log the tokens spent so far to
    usage.log, print one [FAIL] line and return None."""
    try:
        return embed_all(texts, model, api_key, saved, checkpoint)
    except EmbedError as exc:
        if exc.tokens_used:
            cost = round((exc.tokens_used / 1_000_000) * (_rate(model) or 0), 4)
            _append_usage_entry(exc.tokens_used, cost, "dayz-search-index")
        if exc.kind == "transient":
            what = f"Voyage embedding failed after {EMBED_ATTEMPTS} attempts ({exc})."
        elif exc.kind == "interrupted":
            what = "Embedding interrupted (Ctrl+C)."
        elif exc.kind == "response":
            what = f"Voyage returned unusable embeddings ({exc})."
        elif exc.kind == "checkpoint":
            what = f"Could not save embedded batches to {CHECKPOINT_NAME} ({exc})."
        else:
            what = f"Voyage rejected the embed request ({exc}). Check VOYAGE_API_KEY in .env and your Voyage account."
        spent = (
            f"{exc.tokens_used:,} tokens used before the stop were logged to {USAGE_LOG_NAME}"
            if exc.tokens_used
            else "No tokens were used"
        )
        resume = ""
        if checkpoint is not None and exc.kind != "checkpoint" and (exc.tokens_used or saved):
            resume = f" Embedded batches are saved in {CHECKPOINT_NAME}; re-running with --full embeds only the rest."
        print(f"{FAIL} {what} {spent}; the existing index is unchanged.{resume}", file=sys.stderr)
        return None


def embed_all(
    texts: list[str],
    model: str,
    api_key: str,
    saved: Optional[dict[bytes, list[float]]] = None,
    checkpoint: Optional[Path] = None,
) -> tuple[list[list[float]], int]:
    """Embed all texts via Voyage in dynamically-packed batches. Returns
    (vectors, tokens spent by this run).

    - Texts whose (model, text) key is in saved reuse that vector, no API call
    - Each new batch is appended to checkpoint (when given) as soon as it returns
    - Uses input_type="document" (asymmetric retrieval: matches "query" at search time)
    - truncation=True so over-context single inputs don't 400
    - Every vector must have EMBED_DIM values (the table and the MCP server's
      query vectors are 1024-dim); any other length stops the run before
      anything is saved or written
    - Retries transient Voyage errors (voyage_common.is_transient: rate limit,
      timeout, connection, server) with exponential backoff, EMBED_ATTEMPTS per batch
    - Ctrl+C raises EmbedError(kind="interrupted") carrying the tokens spent
    """
    import voyageai
    from tqdm import tqdm

    saved = saved or {}
    keys = [_checkpoint_key(model, t) for t in texts]
    vectors: list[Optional[list[float]]] = [saved.get(k) for k in keys]
    todo = [i for i, v in enumerate(vectors) if v is None]
    client = voyageai.Client(api_key=api_key)
    total_tokens = 0
    cost_per_m = _rate(model)

    pbar = tqdm(total=len(texts), initial=len(texts) - len(todo), desc="  embedding", unit="chunk")
    out = None
    try:
        if checkpoint is not None and todo:
            try:
                out = checkpoint.open("ab")
            except OSError as exc:
                raise EmbedError(exc, 0, False, "checkpoint") from exc
        done = 0
        for batch in _pack_batches([texts[i] for i in todo]):
            indices = todo[done : done + len(batch)]
            done += len(batch)
            delay = 2.0
            for attempt in range(EMBED_ATTEMPTS):
                try:
                    resp = client.embed(
                        texts=batch,
                        model=model,
                        input_type="document",
                        truncation=True,
                    )
                    break
                except Exception as exc:
                    transient = voyage_common.is_transient(exc)
                    if attempt == EMBED_ATTEMPTS - 1 or not transient:
                        raise EmbedError(exc, total_tokens, transient) from exc
                    pbar.write(f"{WARN} {exc}: retry in {delay:.0f}s (attempt {attempt + 1}/{EMBED_ATTEMPTS})")
                    time.sleep(delay)
                    delay *= 2
            total_tokens += int(resp.total_tokens or 0)
            embeddings = list(resp.embeddings or [])
            if len(embeddings) != len(batch):
                raise EmbedError(
                    ValueError(f"got {len(embeddings)} vectors for a batch of {len(batch)} texts"),
                    total_tokens, False, "response",
                )
            bad = next((len(v) for v in embeddings if len(v) != EMBED_DIM), None)
            if bad is not None:
                raise EmbedError(
                    ValueError(
                        f"{model} returned {bad}-dim vectors but the index needs {EMBED_DIM}; "
                        f"set VOYAGE_MODEL to a model with {EMBED_DIM}-dim output, such as {DEFAULT_EMBED_MODEL}"
                    ),
                    total_tokens, False, "response",
                )
            for i, vec in zip(indices, embeddings):
                vectors[i] = vec
            if out is not None:
                try:
                    out.write(b"".join(keys[i] + array("f", vec).tobytes() for i, vec in zip(indices, embeddings)))
                    out.flush()
                except OSError as exc:
                    raise EmbedError(exc, total_tokens, False, "checkpoint") from exc
            if cost_per_m is None:
                pbar.set_postfix_str(f"{total_tokens:,} tok")
            else:
                cost_so_far = (total_tokens / 1_000_000) * cost_per_m
                pbar.set_postfix_str(f"{total_tokens:,} tok / ~${cost_so_far:.3f}")
            pbar.update(len(batch))
    except KeyboardInterrupt as exc:
        raise EmbedError(exc, total_tokens, False, "interrupted") from exc
    finally:
        pbar.close()
        if out is not None:
            with contextlib.suppress(OSError):
                out.close()
    return vectors, total_tokens  # type: ignore[return-value]  # every slot is filled



def write_table(db, rows: list[dict]) -> Optional[int]:
    """Write rows to the staging table, then swap them into TABLE_NAME.

    The live table is only touched after the staging write succeeded, and the
    swap is a single LanceDB overwrite (a new table version), so a failure at
    any step leaves the previous index readable. LanceDB OSS has no
    rename_table, hence the copy from staging.

    Returns the live table's version before the swap (None when there was no
    table), for rollback_table.
    """
    previous = db.open_table(TABLE_NAME).version if TABLE_NAME in db.table_names() else None
    if STAGING_TABLE_NAME in db.table_names():
        db.drop_table(STAGING_TABLE_NAME)
    staging = db.create_table(STAGING_TABLE_NAME, data=rows)
    db.create_table(TABLE_NAME, data=staging.to_arrow(), mode="overwrite")
    # The swap is done. A failed cleanup must not raise from here: commit_index
    # would then skip both the sidecar replace and the rollback, leaving the
    # new table next to the old config.json. The next build drops the leftover.
    with contextlib.suppress(Exception):
        db.drop_table(STAGING_TABLE_NAME)
    return previous


def rollback_table(db, previous: Optional[int]) -> None:
    """Undo write_table: restore TABLE_NAME to version `previous` (an overwrite
    keeps the old version), or drop it when there was no table before."""
    if previous is None:
        if TABLE_NAME in db.table_names():
            db.drop_table(TABLE_NAME)
        return
    table = db.open_table(TABLE_NAME)
    table.checkout(previous)
    table.restore()


class RollbackError(Exception):
    """A post-embed write failed and putting the previous index back failed too."""


def commit_index(db, rows: list[dict], sidecars: dict[str, str]) -> None:
    """Swap in the new table and its sidecar files (name -> text, under
    INDEX_ROOT) all or nothing.

    Every sidecar is first written to a .tmp file, so a full disk fails before
    the live table is touched. Then the table is swapped (write_table) and each
    .tmp replaces its file with os.replace, in the dict's order. If a replace
    fails (a locked file, for example), the table goes back to its previous
    version and the files already replaced get their old contents back, so the
    MCP server never pairs a new table with an old config.json: after a
    VOYAGE_MODEL change that would embed queries with the wrong model. The
    original error is re-raised; RollbackError means the undo failed too.
    """
    tmp = {name: INDEX_ROOT / f"{name}.tmp" for name in sidecars}
    old: dict[str, Optional[bytes]] = {}
    try:
        for name, body in sidecars.items():
            tmp[name].write_text(body, encoding="utf-8")
            path = INDEX_ROOT / name
            old[name] = path.read_bytes() if path.exists() else None
        previous = write_table(db, rows)
        replaced: list[str] = []
        try:
            for name in sidecars:
                os.replace(tmp[name], INDEX_ROOT / name)
                replaced.append(name)
        except BaseException as exc:  # Ctrl+C here must roll back too
            undo_errors: list[str] = []
            try:
                rollback_table(db, previous)
            except Exception as undo:
                undo_errors.append(f"table: {type(undo).__name__}: {undo}")
            for name in replaced:
                path = INDEX_ROOT / name
                try:
                    if old[name] is None:
                        path.unlink(missing_ok=True)
                    else:
                        path.write_bytes(old[name])
                except OSError as undo:
                    undo_errors.append(f"{name}: {type(undo).__name__}: {undo}")
            if undo_errors:
                raise RollbackError(
                    f"{type(exc).__name__}: {exc}; restoring the previous index also failed "
                    f"({'; '.join(undo_errors)})"
                ) from exc
            raise
    finally:
        for path in tmp.values():
            with contextlib.suppress(OSError):
                path.unlink(missing_ok=True)


# --------------- main ---------------


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="DayZ RAG indexer")
    parser.add_argument("--full", action="store_true", help="Rebuild the index, replacing the existing one")
    parser.add_argument("--status", action="store_true", help="Print manifest and exit")
    parser.add_argument("--force", action="store_true", help=f"Override the {CHUNK_CEILING:,}-chunk cost ceiling")
    parser.add_argument("--ignore-tier-warning", action="store_true", help="Skip the Voyage free-tier prompt (CI / scripted use)")
    args = parser.parse_args(argv)

    manifest_path = INDEX_ROOT / "manifest.json"
    config_path = INDEX_ROOT / "config.json"
    db_path = INDEX_ROOT / "lancedb"

    if args.status:
        if manifest_path.exists():
            print(manifest_path.read_text(encoding="utf-8"))
            return 0
        print("No index. Run: python index.py --full", file=sys.stderr)
        return 1

    # Refuse before preflight, dependency and key checks: nothing else matters
    # if the build would be refused anyway. A table without a manifest (a
    # half-removed index) counts as an index too.
    if not args.full and (manifest_path.exists() or (db_path / f"{TABLE_NAME}.lance").exists()):
        print(f"{FAIL} An index already exists at {INDEX_ROOT}. Re-run with --full to rebuild.", file=sys.stderr)
        print(f"        Or: python index.py --status", file=sys.stderr)
        return 1

    try:
        _free_tier_budget()
    except ValueError as exc:
        print(f"{FAIL} {exc}", file=sys.stderr)
        return 1

    print("DayZ RAG indexer\n")
    h.gate_on_preflight()
    print()

    vanilla = h.preflight.find_vanilla_data()
    if vanilla:
        print(f"{OK} Vanilla data: {vanilla}")
    else:
        print(f"{WARN} vanilla data not detected: config.cpp scope will be empty")

    _require_deps()
    api_key = _load_env_and_key()
    embed_model = os.environ.get("VOYAGE_MODEL", DEFAULT_EMBED_MODEL).strip() or DEFAULT_EMBED_MODEL

    print(f"{OK} VOYAGE_API_KEY loaded ({_key_hint(api_key)})")
    print(f"{INFO} Index: {INDEX_ROOT}")
    print(f"{INFO} Embedding model: {embed_model} ({EMBED_DIM}D, via Voyage cloud)")
    cost_per_m = _rate(embed_model)
    if cost_per_m is not None:
        print(f"{INFO} Estimate rate: ${cost_per_m:.2f} per 1M tokens (Voyage pricing page is authoritative)")
    print()

    import lancedb
    from tqdm import tqdm

    # Walk + chunk
    chunks: list[dict] = []
    seen_rvmat: set[str] = set()
    rvmat_dups = 0

    print(f"Walking vanilla folders: {', '.join(VANILLA_FOLDERS)}")
    print(f"Indexed extensions: {', '.join(sorted(EXT_TYPE_MAP.keys()))}")
    print()

    # Per-folder, per-type stats for the manifest
    counts_by_folder: dict[str, dict[str, dict[str, int]]] = {}
    # Content hash of every indexed file, so the server can tell a changed file
    # from one that only got a newer mtime (a re-extracted P:\ drive).
    file_hashes: dict[str, str] = {}

    for folder in VANILLA_FOLDERS:
        root = P_ROOT / folder
        if not root.exists():
            print(f"  {folder}/  (skipped: not present)")
            counts_by_folder[folder] = {}
            continue

        # Collect candidate files by extension
        candidates: list[Path] = []
        for f in root.rglob("*"):
            try:
                if not f.is_file():
                    continue
            except OSError:
                continue
            if f.suffix.lower() in EXT_TYPE_MAP:
                candidates.append(f)

        folder_counts: dict[str, dict[str, int]] = {}
        for f in tqdm(candidates, desc=f"  {folder}/", unit="f"):
            ft = EXT_TYPE_MAP[f.suffix.lower()]
            digest = file_sha256(f)
            if digest:
                file_hashes[str(f)] = digest
            if ft == "rvmat":
                result = chunk_rvmat(f, seen_rvmat)
                if result is None:
                    rvmat_dups += 1
                    folder_counts.setdefault(ft, {"files": 0, "chunks": 0})
                    folder_counts[ft]["files"] += 1
                    continue
                produced = result
            elif ft == "xml":
                produced = chunk_xml(f, ft)
            elif ft in WHOLE_FILE_TYPES:
                produced = chunk_whole_file(f, ft)
            elif ft in CLASS_BLOCK_TYPES:
                produced = _block_chunks(f, ft)
            else:
                continue

            chunks.extend(produced)
            folder_counts.setdefault(ft, {"files": 0, "chunks": 0})
            folder_counts[ft]["files"] += 1
            folder_counts[ft]["chunks"] += len(produced)

        counts_by_folder[folder] = folder_counts
        if folder_counts:
            summary = ", ".join(
                f"{ft}={v['chunks']}c/{v['files']}f"
                for ft, v in sorted(folder_counts.items())
            )
            print(f"  {folder}/  {summary}")
        else:
            print(f"  {folder}/  (no indexed files)")

    if rvmat_dups:
        total_rvmat_files = sum(
            counts_by_folder.get(f, {}).get("rvmat", {}).get("files", 0)
            for f in counts_by_folder
        )
        dup_pct = (rvmat_dups / max(total_rvmat_files, 1)) * 100
        print(f"  rvmat dedup:    {rvmat_dups} duplicates ({dup_pct:.1f}%)")

    if not chunks:
        print(f"\n{FAIL} No chunks produced. Check P:\\ has the vanilla folders.", file=sys.stderr)
        return 1

    if len(chunks) > CHUNK_CEILING and not args.force:
        est_mtokens = sum(_estimate_tokens(c["content"][:EMBED_MAX_CHARS]) for c in chunks) / 1_000_000
        cost_note = f" (~${est_mtokens * cost_per_m:.0f} if billed)" if cost_per_m is not None else ""
        print(
            f"\n{FAIL} {len(chunks)} chunks exceeds the safety ceiling ({CHUNK_CEILING}).\n"
            f"        At ~{CHARS_PER_TOKEN_EST} chars/token that is ~{est_mtokens:.0f}M tokens{cost_note}.\n"
            f"        Either narrow the indexing scope or re-run with --force to override.",
            file=sys.stderr,
        )
        return 1

    # Drop chunks with no embeddable content: Voyage returns 400 on empty inputs.
    nonempty_chunks = [c for c in chunks if c.get("content", "").strip()]
    dropped = len(chunks) - len(nonempty_chunks)
    if dropped:
        print(f"{INFO} Dropped {dropped} empty chunks before embed")
    chunks = nonempty_chunks

    # Cap content length defensively (voyage-code-3 has 32k context but truncation=True handles it).
    texts = [(c["content"] or " ")[:EMBED_MAX_CHARS] for c in chunks]

    try:
        INDEX_ROOT.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"{FAIL} Cannot create {INDEX_ROOT} ({type(exc).__name__}: {exc}). No tokens consumed.", file=sys.stderr)
        return 1

    # Vectors saved by an earlier build that failed or was interrupted are
    # reused, so only the rest is embedded (and estimated, and billed).
    checkpoint = INDEX_ROOT / CHECKPOINT_NAME
    saved = _load_checkpoint(checkpoint)
    pending = [t for t in texts if _checkpoint_key(embed_model, t) not in saved] if saved else texts
    reused = len(texts) - len(pending)
    if reused:
        print(f"{INFO} Resuming: {reused:,} of {len(texts):,} chunks were embedded by an earlier run ({CHECKPOINT_NAME})")

    # Voyage free-tier projection check. Estimate this build's tokens from
    # local char-per-token ratio so we can warn before committing to the embed.
    estimated_tokens = sum(_estimate_tokens(t) for t in pending)
    if not _check_voyage_tier(estimated_tokens, args.ignore_tier_warning, embed_model):
        return 1  # _check_voyage_tier printed the reason

    print(f"\nEmbedding {len(pending)} chunks via Voyage ({embed_model}, document mode)...")
    started = time.time()
    embedded = embed_or_fail(texts, embed_model, api_key, saved, checkpoint)
    if embedded is None:
        return 1
    embeddings, total_tokens = embedded
    elapsed = time.time() - started
    cost_estimate_usd = round((total_tokens / 1_000_000) * (cost_per_m or 0), 4)
    # The tokens are billed now, so log them before anything below can fail:
    # the next run's tier check reads this log.
    _append_usage_entry(total_tokens, cost_estimate_usd, "dayz-search-index")

    for c, vec in zip(chunks, embeddings):
        c["vector"] = vec

    manifest = {
        "indexed_at": int(time.time()),
        "indexed_at_iso": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "embed_model": embed_model,
        "embed_dim": EMBED_DIM,
        "embed_provider": "voyage",
        "vanilla_data_root": str(vanilla) if vanilla else None,
        "vanilla_folders_scanned": VANILLA_FOLDERS,
        "extensions_indexed": sorted(EXT_TYPE_MAP.keys()),
        "counts_by_folder": counts_by_folder,
        "rvmat_duplicates_skipped": rvmat_dups,
        "total_chunks": len(chunks),
        "total_tokens": total_tokens,
        "chunks_reused_from_checkpoint": reused,
        "cost_estimate_usd": cost_estimate_usd,
        "embed_seconds": round(elapsed, 1),
    }
    # The MCP server reopens the table and rereads config.json when the
    # manifest changes, so the manifest is replaced last.
    sidecars = {
        "file_hashes.json": json.dumps(file_hashes),
        config_path.name: json.dumps({"embed_model": embed_model, "embed_provider": "voyage"}, indent=2),
        manifest_path.name: json.dumps(manifest, indent=2),
    }
    kept = f"The embeddings stay in {CHECKPOINT_NAME}, so the re-run spends no tokens on them."
    try:
        commit_index(lancedb.connect(str(db_path)), chunks, sidecars)
    except RollbackError as exc:
        print(
            f"\n{FAIL} Writing the index failed after the embed ({exc}). The index may be "
            f"inconsistent; re-run with --full before searching. {kept}",
            file=sys.stderr,
        )
        return 1
    except KeyboardInterrupt:
        # Ctrl+C can land mid table swap, where nothing can say which version is live.
        print(
            f"\n{FAIL} Interrupted (Ctrl+C) while writing the index. The index may be "
            f"inconsistent; re-run with --full before searching. {kept}",
            file=sys.stderr,
        )
        return 1
    except Exception as exc:
        print(
            f"\n{FAIL} Writing the index failed after the embed ({type(exc).__name__}: {exc}). "
            f"The previous index is unchanged; re-run with --full. {kept}",
            file=sys.stderr,
        )
        return 1

    try:
        checkpoint.unlink(missing_ok=True)
    except OSError as exc:
        print(f"{WARN} Could not remove {CHECKPOINT_NAME} ({exc}); delete it by hand.")

    # The index is now a local build, not the downloaded release.
    try:
        (INDEX_ROOT / RELEASE_TAG_FILE).unlink(missing_ok=True)
    except OSError as exc:
        print(f"{WARN} Could not remove {RELEASE_TAG_FILE} ({exc}); delete it by hand.")

    print(f"\n{OK} Index built: {len(chunks)} chunks at {INDEX_ROOT}")
    print(f"{INFO} Tokens used: {total_tokens:,}  |  Estimated cost: ${cost_estimate_usd:.4f}")
    print(f"{INFO} Embed time: {elapsed:.1f}s")
    print(f"{INFO} Restart Claude Code so the dayz-rag MCP server picks up the new index.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
