"""DayZ RAG indexer.

Walk vanilla DayZ source on P:\\, chunk per file type, embed via Voyage AI
(`voyage-code-3` by default — code-tuned, 1024-dim), store in LanceDB at
~/.claude/dayz-search-index/.

Cost reality: a full vanilla rebuild is ~5-20M tokens. Voyage gives 200M tokens
free per Series-4 model. You'd have to rebuild ~10x before paying anything.
Live token + $ telemetry prints during the embed loop so there are no surprises.

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
import subprocess
import sys
import time
from pathlib import Path
from typing import Iterator

# Reuse preflight resolvers
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "dayz-preflight"))
from preflight import find_vanilla_data  # noqa: E402

INDEX_ROOT = Path.home() / ".claude" / "dayz-search-index"
TABLE_NAME = "chunks"

# Voyage model. Override via VOYAGE_MODEL env var (e.g. "voyage-4-lite" for
# cheaper, "voyage-4-large" for top general quality). All current Series-4
# models output 1024-dim embeddings.
DEFAULT_EMBED_MODEL = "voyage-code-3"
EMBED_DIM = 1024

# Voyage API limits per request (voyage-code-3): 128 texts max, 120k tokens max.
# We pack batches dynamically up to TOKEN_BUDGET_PER_BATCH (under the 120k cap)
# OR TEXT_LIMIT_PER_BATCH, whichever hits first. CHARS_PER_TOKEN_EST is a
# conservative local estimate (real code ratio is ~3.5-4 chars/token).
TEXT_LIMIT_PER_BATCH = 128
# Code tokenizes denser than prose (punctuation, brackets, short identifiers).
# Empirically Voyage tokenizer hit ~1.8 chars/token on Enforce Script. Using
# 1.8 with a 75k token budget keeps real batch tokens well under the 120k cap
# even with surprise-heavy content.
TOKEN_BUDGET_PER_BATCH = 75_000
CHARS_PER_TOKEN_EST = 1.8
EMBED_MAX_CHARS = 6000  # voyage-code-3 has 32k context — plenty of headroom

# Rough $ per 1M input tokens, used for the live cost estimate. Source:
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

OK = "[OK]   "
WARN = "[WARN] "
FAIL = "[FAIL] "
INFO = "[INFO] "


def _ensure_deps() -> None:
    """Install lancedb + tqdm + voyageai + python-dotenv if missing. Re-execs after install."""
    try:
        import lancedb  # noqa: F401
        import tqdm  # noqa: F401
        import voyageai  # noqa: F401
        import dotenv  # noqa: F401
        return
    except ImportError:
        pass
    req = _HERE / "requirements.txt"
    print(f"{INFO} Installing index dependencies (one-time)...")
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", str(req)],
        check=True,
    )
    print(f"{INFO} Restarting indexer to pick up newly installed deps...", flush=True)
    result = subprocess.run([sys.executable, *sys.argv], check=False)
    sys.exit(result.returncode)


def _load_env_and_key() -> str:
    """Find repo .env, load it, return the Voyage API key. Hard-fail if missing."""
    from dotenv import find_dotenv, load_dotenv
    env_path = find_dotenv(usecwd=True)
    if env_path:
        load_dotenv(env_path)
    key = os.environ.get("VOYAGE_API_KEY", "").strip()
    # Accept `export VOYAGE_API_KEY="..."` form too — strip leading "export "
    # if a literal value with that prefix snuck in.
    if key.startswith("export "):
        key = key.split("=", 1)[-1].strip().strip('"').strip("'")
    if not key:
        print(
            f"{FAIL} VOYAGE_API_KEY not set.\n"
            f"        Add it to .env at the repo root:\n"
            f"            VOYAGE_API_KEY=pa-xxxxxxxx\n"
            f"        Get a key at: https://dash.voyageai.com",
            file=sys.stderr,
        )
        sys.exit(1)
    return key


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


def _block_chunks(path: Path, file_type: str, max_chars: int = 8000) -> list[dict]:
    """Chunk a class-style file. Falls back to whole-file if no class blocks."""
    text = _read_text(path)
    if not text:
        return []
    blocks = list(_walk_class_blocks(text))
    if blocks:
        return [
            {
                "path": str(path),
                "file_type": file_type,
                "parent_context": name,
                "line_start": s,
                "line_end": e,
                "content": body[:max_chars],
            }
            for name, s, e, body in blocks
        ]
    return [
        {
            "path": str(path),
            "file_type": file_type,
            "parent_context": "",
            "line_start": 1,
            "line_end": text.count("\n") + 1,
            "content": text[:max_chars],
        }
    ]


def chunk_rvmat(path: Path, seen_hashes: set[str]) -> list[dict] | None:
    """Whole-file chunk, content-deduped via SHA-256."""
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    h = hashlib.sha256(raw).hexdigest()
    if h in seen_hashes:
        return None
    seen_hashes.add(h)
    text = raw.decode("utf-8", errors="replace")
    return [
        {
            "path": str(path),
            "file_type": "rvmat",
            "parent_context": h[:12],
            "line_start": 1,
            "line_end": text.count("\n") + 1,
            "content": text[:4000],
        }
    ]


XML_BATCH_SIZE = 50  # max top-level elements grouped into one chunk


def chunk_xml(path: Path, file_type: str = "xml", batch_size: int = XML_BATCH_SIZE) -> list[dict]:
    """Chunk XML by groups of top-level child elements. Caps explosion on
    types.xml-style files (one chunk per ~50 entries instead of per entry).

    - Small files (<4KB): one whole-file chunk
    - Files with many children: batched 50 per chunk by default
    - Parse errors: fall back to whole-file truncated
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
                "content": text[:8000],
            }
        ]
    try:
        import xml.etree.ElementTree as ET
        root = ET.fromstring(text)
        children = list(root)
        if len(children) >= 5:
            chunks = []
            for i in range(0, len(children), batch_size):
                batch = children[i : i + batch_size]
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
                        "line_start": 1,
                        "line_end": 1,
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
            "line_end": text.count("\n") + 1,
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


def _pack_batches(texts: list[str]) -> Iterator[list[str]]:
    """Yield batches that respect both Voyage limits: max TEXT_LIMIT_PER_BATCH
    items AND max ~TOKEN_BUDGET_PER_BATCH tokens (estimated locally as
    len/CHARS_PER_TOKEN_EST). Single oversize chunks pass through alone —
    truncation=True on the API call handles the actual cap."""
    batch: list[str] = []
    batch_tokens = 0
    for t in texts:
        est = max(1, len(t) // CHARS_PER_TOKEN_EST)
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


def _embed_all(texts: list[str], model: str, api_key: str) -> tuple[list[list[float]], int]:
    """Embed all texts via Voyage in dynamically-packed batches. Returns
    (vectors, total_tokens).

    - Uses input_type="document" (asymmetric retrieval — matches "query" at search time)
    - truncation=True so over-context single inputs don't 400
    - Retries on 429 / transient errors with exponential backoff
    """
    import voyageai
    from tqdm import tqdm

    client = voyageai.Client(api_key=api_key)
    vectors: list[list[float]] = []
    total_tokens = 0
    cost_per_m = COST_PER_MTOKEN.get(model, 0.18)

    pbar = tqdm(total=len(texts), desc="  embedding", unit="chunk")
    for batch in _pack_batches(texts):
        delay = 2.0
        for attempt in range(5):
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
            except Exception as exc:  # voyageai.error.RateLimitError + transient network
                msg = str(exc).lower()
                is_rate_limit = "rate" in msg or "429" in msg or "quota" in msg
                if attempt == 4 or not (is_rate_limit or "timeout" in msg or "connection" in msg):
                    pbar.close()
                    raise
                pbar.write(f"{WARN} {exc} — retry in {delay:.0f}s (attempt {attempt + 1}/5)")
                time.sleep(delay)
                delay *= 2
        cost_so_far = (total_tokens / 1_000_000) * cost_per_m
        pbar.set_postfix_str(f"{total_tokens:,} tok / ~${cost_so_far:.3f}")
        pbar.update(len(batch))

    pbar.close()
    return vectors, total_tokens


# --------------- main ---------------


def main() -> int:
    parser = argparse.ArgumentParser(description="DayZ RAG indexer")
    parser.add_argument("--full", action="store_true", help="Drop existing index and rebuild")
    parser.add_argument("--status", action="store_true", help="Print manifest and exit")
    parser.add_argument("--force", action="store_true", help="Override the chunk-count safety ceiling (only if you know your RAM headroom is fine)")
    args = parser.parse_args()

    INDEX_ROOT.mkdir(parents=True, exist_ok=True)
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

    if not Path(r"P:\\").exists():
        print(f"{FAIL} P:\\ not mounted. Run /dayz-preflight first.", file=sys.stderr)
        return 1
    print(f"{OK} P:\\ mounted")

    vanilla = find_vanilla_data()
    if vanilla:
        print(f"{OK} Vanilla data: {vanilla}")
    else:
        print(f"{WARN} vanilla data not detected — config.cpp scope will be empty")

    _ensure_deps()
    api_key = _load_env_and_key()
    embed_model = os.environ.get("VOYAGE_MODEL", DEFAULT_EMBED_MODEL).strip() or DEFAULT_EMBED_MODEL

    print(f"{OK} VOYAGE_API_KEY loaded ({api_key[:6]}...{api_key[-4:]})")
    print(f"{INFO} Index: {INDEX_ROOT}")
    print(f"{INFO} Embedding model: {embed_model} (1024D, via Voyage cloud)")
    cost_per_m = COST_PER_MTOKEN.get(embed_model)
    if cost_per_m is not None:
        print(f"{INFO} Pricing: ${cost_per_m:.2f} per 1M tokens (Series-4 includes 200M free)")
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
        root = Path(r"P:\\") / folder
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

    # Cost-runaway safety: refuse to embed more than CHUNK_CEILING without --force.
    # At ~1500 tokens/chunk avg, 150k chunks ≈ 225M tokens — past the 200M free tier.
    CHUNK_CEILING = 150_000
    if len(chunks) > CHUNK_CEILING and not args.force:
        print(
            f"\n{FAIL} {len(chunks)} chunks exceeds the safety ceiling ({CHUNK_CEILING}).\n"
            f"        At ~1500 tokens/chunk this is ~{len(chunks) * 1500 / 1_000_000:.0f}M tokens —\n"
            f"        likely past the 200M Voyage free tier (~${len(chunks) * 1500 / 1_000_000 * (cost_per_m or 0.18):.0f} if billed).\n"
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

    print(f"\nEmbedding {len(chunks)} chunks via Voyage ({embed_model}, document mode)...")
    started = time.time()
    embeddings, total_tokens = _embed_all(texts, embed_model, api_key)
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

    # Write to LanceDB
    db = lancedb.connect(str(db_path))
    if TABLE_NAME in db.table_names():
        db.drop_table(TABLE_NAME)
    db.create_table(TABLE_NAME, data=chunks)

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

    print(f"\n{OK} Index built: {len(chunks)} chunks at {INDEX_ROOT}")
    print(f"{INFO} Tokens used: {total_tokens:,}  |  Estimated cost: ${cost_estimate_usd:.4f}")
    print(f"{INFO} Embed time: {elapsed:.1f}s")
    print(f"{INFO} Restart Claude Code so the dayz-rag MCP server picks up the new index.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
