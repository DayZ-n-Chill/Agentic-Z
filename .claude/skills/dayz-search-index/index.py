"""DayZ RAG indexer.

Walk vanilla DayZ source on P:\\, chunk per file type, embed via Voyage AI
(`voyage-code-3` by default, 1024-dim), store in LanceDB at
~/.claude/dayz-search-index/ for the dayz-rag MCP server.

Gates on /dayz-preflight (it reads vanilla data on P:\\). A live token and cost
estimate prints during the embed loop; see reference/cost-and-free-tier.md for
the free-tier check.

Run:
    python .claude/skills/dayz-search-index/index.py --full   # first time / rebuild
    python .claude/skills/dayz-search-index/index.py --status # show manifest
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterator, Optional
from xml.parsers import expat

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "_shared"))
import skill_helpers as h  # noqa: E402

# .env/API-key loading and the Voyage retry rule live next to the MCP server so
# indexing and searching read the same key the same way.
sys.path.insert(0, str(_HERE.parents[1] / "mcp" / "dayz-rag"))
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


def _usage_log_path() -> Path:
    return INDEX_ROOT / USAGE_LOG_NAME


def _read_monthly_usage_tokens() -> int:
    """Sum tokens used in the current calendar month from usage.log (UTC).

    Doesn't fail on missing file or malformed lines — those are treated as
    zero contribution. We'd rather under-warn than crash.
    """
    path = _usage_log_path()
    if not path.exists():
        return 0
    now = time.gmtime()
    total = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
            ts = time.gmtime(int(entry.get("timestamp_unix", 0)))
            if ts.tm_year == now.tm_year and ts.tm_mon == now.tm_mon:
                total += int(entry.get("tokens", 0))
        except (json.JSONDecodeError, ValueError, TypeError):
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


def _check_voyage_tier(
    estimated_tokens: int, ignore_warning: bool, model: str = DEFAULT_EMBED_MODEL
) -> bool:
    """Pre-build tier check. Returns True if user wants to proceed.

    Uses local cumulative tracking only; Voyage doesn't expose a public
    usage API. The overage estimate uses `model`'s rate from COST_PER_MTOKEN.
    See reference/cost-and-free-tier.md for caveats.
    """
    budget = int(os.environ.get("VOYAGE_FREE_TIER_TOKENS", VOYAGE_FREE_TIER_BUDGET))
    used = _read_monthly_usage_tokens()
    projected = used + estimated_tokens
    pct_projected = projected / budget if budget > 0 else 0

    if pct_projected < TIER_WARN_THRESHOLD:
        return True

    pct_used = used / budget if budget > 0 else 0
    print()
    print(f"{WARN} Voyage free-tier projection:")
    print(f"        This month so far: {used:,} tokens ({pct_used*100:.1f}% of {budget/1_000_000:.0f}M)")
    print(f"        This build est:    {estimated_tokens:,} tokens")
    print(f"        Projected total:   {projected:,} tokens ({pct_projected*100:.1f}% of free tier)")
    if pct_projected > 1.0:
        rate = _rate(model)
        if rate is None:
            print(f"        Past free tier — no local rate for {model}; check Voyage pricing.")
        else:
            cost_over = ((projected - budget) / 1_000_000) * rate
            print(f"        Past free tier — estimated overage: ${cost_over:.2f}")
    print()
    print("        Caveats:")
    print("        - Counter is local. Other apps using your VOYAGE_API_KEY are NOT counted.")
    print("        - Authoritative usage at https://dash.voyageai.com")
    print("        - Free tier resets monthly per Voyage's billing cycle.")
    print()

    if ignore_warning:
        print(f"{INFO} --ignore-tier-warning passed; proceeding anyway.")
        return True

    try:
        answer = input("        Continue? [y/N]: ").strip().lower()
    except EOFError:
        # Non-interactive shell: refuse by default.
        print(f"{FAIL} Non-interactive shell. Pass --ignore-tier-warning to override.")
        return False
    return answer in ("y", "yes")


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
            f"            pip install -r \"{_HERE / 'requirements.txt'}\"",
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

_CLASS_HEADER_RE = re.compile(
    r"(?:modded\s+)?class\s+(?P<name>[A-Za-z_]\w*)"
    r"(?:\s*:\s*[A-Za-z_]\w*)?"
    r"(?:\s+extends\s+[A-Za-z_]\w*)?"
    r"\s*\{",
    re.IGNORECASE,
)


def _walk_class_blocks(text: str) -> Iterator[tuple[str, int, int, str]]:
    """Yield (name, start_line, end_line, body) for top-level class blocks."""
    pos = 0
    n = len(text)
    while pos < n:
        m = _CLASS_HEADER_RE.search(text, pos)
        if not m:
            return
        name = m.group("name")
        brace_start = m.end() - 1
        depth = 1
        i = brace_start + 1
        while i < n and depth > 0:
            c = text[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
            i += 1
        if depth != 0:
            return
        block_start = m.start()
        block_end = i
        start_line = text.count("\n", 0, block_start) + 1
        end_line = text.count("\n", 0, block_end) + 1
        yield name, start_line, end_line, text[block_start:block_end]
        pos = block_end


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


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
    lines = body.splitlines(keepends=True)
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
    blocks = list(_walk_class_blocks(text)) or [("", 1, text.count("\n") + 1, text)]
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


XML_BATCH_SIZE = 50  # max top-level elements grouped into one chunk


def _xml_child_line_spans(text: str) -> list[tuple[int, int]]:
    """(start_line, end_line) of each top-level child element, in document order.

    end_line is the line of the closing tag (or of the start tag for a
    self-closing element). Raises expat.ExpatError on malformed XML.
    """
    parser = expat.ParserCreate()
    spans: list[tuple[int, int]] = []
    depth = 0
    start = 0

    def on_start(_name, _attrs):
        nonlocal depth, start
        depth += 1
        if depth == 2:
            start = parser.CurrentLineNumber

    def on_end(_name):
        nonlocal depth
        if depth == 2:
            spans.append((start, parser.CurrentLineNumber))
        depth -= 1

    parser.StartElementHandler = on_start
    parser.EndElementHandler = on_end
    parser.Parse(text, True)
    return spans


def chunk_xml(path: Path, file_type: str = "xml", batch_size: int = XML_BATCH_SIZE) -> list[dict]:
    """Chunk XML by groups of top-level child elements. Caps explosion on
    types.xml-style files (one chunk per ~50 entries instead of per entry).

    - Small files (<4KB): one whole-file chunk
    - Files with many children: batched 50 per chunk by default, each chunk
      carrying the real line range of its first and last element
    - Parse errors: fall back to whole-file truncated
    """
    text = _read_text(path)
    if not text:
        return []
    total_lines = text.count("\n") + 1
    if len(text) < 4000:
        return [
            {
                "path": str(path),
                "file_type": file_type,
                "parent_context": "",
                "line_start": 1,
                "line_end": total_lines,
                "content": text[:8000],
            }
        ]
    try:
        root = ET.fromstring(text)
        children = list(root)
        try:
            spans = _xml_child_line_spans(text)
        except expat.ExpatError:
            spans = []
        if len(spans) != len(children):  # never mislabel lines; fall back to the whole file
            spans = [(1, total_lines)] * len(children)
        if len(children) >= 5:
            chunks = []
            for i in range(0, len(children), batch_size):
                batch = children[i : i + batch_size]
                batch_spans = spans[i : i + batch_size]
                snippets = [ET.tostring(c, encoding="unicode") for c in batch]
                first_name = batch[0].get("name") or batch[0].get("Name") or batch[0].tag
                last_name = batch[-1].get("name") or batch[-1].get("Name") or batch[-1].tag
                if len(batch) == 1:
                    parent_context = f"{root.tag} > {first_name}"
                else:
                    parent_context = f"{root.tag} > {first_name}..{last_name} ({len(batch)} items)"
                chunks.append(
                    {
                        "path": str(path),
                        "file_type": file_type,
                        "parent_context": parent_context,
                        "line_start": batch_spans[0][0],
                        "line_end": batch_spans[-1][1],
                        "content": ("\n".join(snippets))[:8000],
                    }
                )
            return chunks
    except ET.ParseError:
        pass
    return [
        {
            "path": str(path),
            "file_type": file_type,
            "parent_context": "",
            "line_start": 1,
            "line_end": total_lines,
            "content": text[:8000],
        }
    ]


def chunk_whole_file(path: Path, file_type: str) -> list[dict]:
    """One chunk per file. Used for json/csv/small text."""
    text = _read_text(path)
    if not text:
        return []
    return [
        {
            "path": str(path),
            "file_type": file_type,
            "parent_context": "",
            "line_start": 1,
            "line_end": text.count("\n") + 1,
            "content": text[:8000],
        }
    ]


# --------------- walk config ---------------

# Top-level vanilla folders to scan under P:\. Mods, junctions to user mod
# projects, and DayZ Tools binary dirs are NOT in this list — that's the
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
    len/CHARS_PER_TOKEN_EST). Single oversize chunks pass through alone —
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


class EmbedError(Exception):
    """An embed batch failed for good. Carries the tokens already billed for the
    batches that succeeded, so the caller can log them before exiting."""

    def __init__(self, cause: Exception, tokens_used: int, transient: bool):
        self.cause = cause
        self.tokens_used = tokens_used
        self.transient = transient
        detail = " ".join(str(cause).split()) or "no message"
        super().__init__(f"{type(cause).__name__}: {detail}")


def embed_or_fail(texts: list[str], model: str, api_key: str) -> Optional[tuple[list[list[float]], int]]:
    """Run embed_all. On failure, log the tokens spent so far to usage.log,
    print one [FAIL] line and return None."""
    try:
        return embed_all(texts, model, api_key)
    except EmbedError as exc:
        if exc.tokens_used:
            cost = round((exc.tokens_used / 1_000_000) * (_rate(model) or 0), 4)
            _append_usage_entry(exc.tokens_used, cost, "dayz-search-index")
        if exc.transient:
            what = f"Voyage embedding failed after {EMBED_ATTEMPTS} attempts ({exc})."
        else:
            what = f"Voyage rejected the embed request ({exc}). Check VOYAGE_API_KEY in .env and your Voyage account."
        spent = (
            f"{exc.tokens_used:,} tokens used before the failure were logged to {USAGE_LOG_NAME}"
            if exc.tokens_used
            else "No tokens were used"
        )
        print(f"{FAIL} {what} {spent}; the existing index is unchanged.", file=sys.stderr)
        return None


def embed_all(texts: list[str], model: str, api_key: str) -> tuple[list[list[float]], int]:
    """Embed all texts via Voyage in dynamically-packed batches. Returns
    (vectors, total_tokens).

    - Uses input_type="document" (asymmetric retrieval — matches "query" at search time)
    - truncation=True so over-context single inputs don't 400
    - Retries transient Voyage errors (voyage_common.is_transient: rate limit,
      timeout, connection, server) with exponential backoff, EMBED_ATTEMPTS per batch
    """
    import voyageai
    from tqdm import tqdm

    client = voyageai.Client(api_key=api_key)
    vectors: list[list[float]] = []
    total_tokens = 0
    cost_per_m = _rate(model)

    pbar = tqdm(total=len(texts), desc="  embedding", unit="chunk")
    for batch in _pack_batches(texts):
        delay = 2.0
        for attempt in range(EMBED_ATTEMPTS):
            try:
                resp = client.embed(
                    texts=batch,
                    model=model,
                    input_type="document",
                    truncation=True,
                )
                vectors.extend(resp.embeddings)
                total_tokens += int(resp.total_tokens or 0)
                break
            except Exception as exc:
                transient = voyage_common.is_transient(exc)
                if attempt == EMBED_ATTEMPTS - 1 or not transient:
                    pbar.close()
                    raise EmbedError(exc, total_tokens, transient) from exc
                pbar.write(f"{WARN} {exc} — retry in {delay:.0f}s (attempt {attempt + 1}/{EMBED_ATTEMPTS})")
                time.sleep(delay)
                delay *= 2
        if cost_per_m is None:
            pbar.set_postfix_str(f"{total_tokens:,} tok")
        else:
            cost_so_far = (total_tokens / 1_000_000) * cost_per_m
            pbar.set_postfix_str(f"{total_tokens:,} tok / ~${cost_so_far:.3f}")
        pbar.update(len(batch))

    pbar.close()
    return vectors, total_tokens



def write_table(db, rows: list[dict]) -> None:
    """Write rows to the staging table, then swap them into TABLE_NAME.

    The live table is only touched after the staging write succeeded, and the
    swap is a single LanceDB overwrite (a new table version), so a failure at
    any step leaves the previous index readable. LanceDB OSS has no
    rename_table, hence the copy from staging.
    """
    if STAGING_TABLE_NAME in db.table_names():
        db.drop_table(STAGING_TABLE_NAME)
    staging = db.create_table(STAGING_TABLE_NAME, data=rows)
    db.create_table(TABLE_NAME, data=staging.to_arrow(), mode="overwrite")
    db.drop_table(STAGING_TABLE_NAME)


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

    print("DayZ RAG indexer\n")
    h.gate_on_preflight()
    print()

    vanilla = h.preflight.find_vanilla_data()
    if vanilla:
        print(f"{OK} Vanilla data: {vanilla}")
    else:
        print(f"{WARN} vanilla data not detected — config.cpp scope will be empty")

    _require_deps()
    api_key = _load_env_and_key()
    embed_model = os.environ.get("VOYAGE_MODEL", DEFAULT_EMBED_MODEL).strip() or DEFAULT_EMBED_MODEL

    print(f"{OK} VOYAGE_API_KEY loaded ({api_key[:6]}...{api_key[-4:]})")
    print(f"{INFO} Index: {INDEX_ROOT}")
    print(f"{INFO} Embedding model: {embed_model} ({EMBED_DIM}D, via Voyage cloud)")
    cost_per_m = _rate(embed_model)
    if cost_per_m is not None:
        print(f"{INFO} Estimate rate: ${cost_per_m:.2f} per 1M tokens (Voyage pricing page is authoritative)")
    print()

    if manifest_path.exists() and not args.full:
        print(f"{FAIL} Index already exists. Re-run with --full to rebuild.", file=sys.stderr)
        print(f"        Or: python index.py --status", file=sys.stderr)
        return 1

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

    for folder in VANILLA_FOLDERS:
        root = P_ROOT / folder
        if not root.exists():
            print(f"  {folder}/  (skipped — not present)")
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

    # Drop chunks with no embeddable content — Voyage returns 400 on empty inputs.
    nonempty_chunks = [c for c in chunks if c.get("content", "").strip()]
    dropped = len(chunks) - len(nonempty_chunks)
    if dropped:
        print(f"{INFO} Dropped {dropped} empty chunks before embed")
    chunks = nonempty_chunks

    # Cap content length defensively (voyage-code-3 has 32k context but truncation=True handles it).
    texts = [(c["content"] or " ")[:EMBED_MAX_CHARS] for c in chunks]

    # Voyage free-tier projection check. Estimate this build's tokens from
    # local char-per-token ratio so we can warn before committing to the embed.
    estimated_tokens = sum(_estimate_tokens(t) for t in texts)
    if not _check_voyage_tier(estimated_tokens, args.ignore_tier_warning, embed_model):
        print(f"{FAIL} Cancelled by user. No tokens consumed.", file=sys.stderr)
        return 1

    print(f"\nEmbedding {len(chunks)} chunks via Voyage ({embed_model}, document mode)...")
    started = time.time()
    embedded = embed_or_fail(texts, embed_model, api_key)
    if embedded is None:
        return 1
    embeddings, total_tokens = embedded
    elapsed = time.time() - started

    if len(embeddings) != len(chunks):
        print(
            f"\n{FAIL} Embedding count mismatch: got {len(embeddings)} for {len(chunks)} chunks.",
            file=sys.stderr,
        )
        return 1
    for c, vec in zip(chunks, embeddings):
        c["vector"] = vec

    cost_estimate_usd = round((total_tokens / 1_000_000) * (cost_per_m or 0), 4)

    INDEX_ROOT.mkdir(parents=True, exist_ok=True)
    write_table(lancedb.connect(str(db_path)), chunks)

    # Manifest
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
        "cost_estimate_usd": cost_estimate_usd,
        "embed_seconds": round(elapsed, 1),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    config_path.write_text(
        json.dumps({"embed_model": embed_model, "embed_provider": "voyage"}, indent=2),
        encoding="utf-8",
    )

    # Track this run in the local Voyage usage log so the next run's
    # tier check has accurate cumulative numbers.
    _append_usage_entry(total_tokens, cost_estimate_usd, "dayz-search-index")

    print(f"\n{OK} Index built: {len(chunks)} chunks at {INDEX_ROOT}")
    print(f"{INFO} Tokens used: {total_tokens:,}  |  Estimated cost: ${cost_estimate_usd:.4f}")
    print(f"{INFO} Embed time: {elapsed:.1f}s")
    print(f"{INFO} Restart Claude Code so the dayz-rag MCP server picks up the new index.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
