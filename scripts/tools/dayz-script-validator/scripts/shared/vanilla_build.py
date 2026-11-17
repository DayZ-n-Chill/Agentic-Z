"""Whether the vanilla tree is the scripts of the game the addon runs on.

The rules that read the vanilla tree judge an addon against that tree, not
against the game. Pipeline inbox fb-20261103-150432-9f93: a gate read the
1.30.164014 Exp extract while the game was 1.30.164200, and a call to
vector.Cross, which only the extract declares, passed; the game refused it.

The game compiles its own dta/scripts.pbo, so the tree is compared with that
archive by content, file by file (.c only). A folder carries no build number,
and the PBO header's version or the exe's version only name a build: they do
not say which build a folder was extracted from. Read-only. The PBO is read
with the Pack's fail-closed reader,
tools/dayz-vehicle-proxy-contract/scripts/vehicle_proxy/pbo.py, which refuses
a compressed entry: what it cannot read is reported as not compared, never as
a match.
"""

import hashlib
import os
import pathlib
import sys


GAME_ROOT_ENV = "DAYZ_GAME_ROOT"
VANILLA_ROOT_BUILD_RULE_ID = "VANILLA-ROOT-BUILD-MISMATCH"

_READER_ROOT = (
    pathlib.Path(__file__).resolve().parents[3]
    / "dayz-vehicle-proxy-contract" / "scripts"
)
_EXAMPLES = 5

VANILLA_ROOT_BUILD_MESSAGE = (
    "[WARN] the vanilla tree {root} is not the scripts of the game at {game}: "
    "of the {files} .c files of {pbo} (PBO header version {version}), {differ} "
    "differ from the tree and {missing} are not in it, and the tree has "
    "{extra} .c files the game does not ({examples}). The rules that read the "
    "vanilla tree judge the addon against the tree, so a method or a class "
    "that only the tree declares passes, and the game refuses it (pipeline "
    "inbox fb-20261103-150432-9f93: vector.Cross). Extract that scripts.pbo "
    "and pass it as --vanilla-root."
)


def resolve_game_root(explicit=None):
    """The --game-root argument, else DAYZ_GAME_ROOT, else None."""
    return explicit or os.environ.get(GAME_ROOT_ENV) or None


def _scripts_pbo(game_root):
    path = pathlib.Path(game_root)
    if path.is_file():
        return path
    return path / "dta" / "scripts.pbo"


def _reader():
    """(PboFormatError, digest_pbo) of the Pack's reader, or None."""
    if str(_READER_ROOT) not in sys.path:
        sys.path.insert(0, str(_READER_ROOT))
    try:
        from vehicle_proxy.pbo import PboFormatError, digest_pbo
    except ImportError:
        return None
    return PboFormatError, digest_pbo


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _skip(reason):
    return {
        "rule_id": VANILLA_ROOT_BUILD_RULE_ID,
        "status": "SKIP",
        "reason": reason,
    }


def compare_vanilla_build(vanilla_root, game_root):
    """Return (warnings, skipped, info) for --game-root.

    info is None when nothing was compared; otherwise it holds the counts
    and `matches`. The PBO's entry names are relative to its prefix, the
    folder the vanilla tree stands for; names compare without case.
    """
    if vanilla_root is None:
        return [], [_skip(
            "no vanilla tree to compare with the game's scripts at %s" % game_root
        )], None
    pbo = _scripts_pbo(game_root)
    if not pbo.is_file():
        return [], [_skip(
            "no dta/scripts.pbo under %s, so the vanilla tree is not compared "
            "with the game's scripts" % game_root
        )], None
    reader = _reader()
    if reader is None:
        return [], [_skip(
            "the Pack's PBO reader is not at %s, so the vanilla tree is not "
            "compared with %s" % (_READER_ROOT, pbo)
        )], None
    pbo_format_error, digest_pbo = reader
    try:
        digest = digest_pbo(pbo)
    except pbo_format_error as error:
        return [], [_skip(
            "%s was not read (%s), so the vanilla tree is not compared with it"
            % (pbo, error)
        )], None

    game = {}
    for entry, sha256 in digest.entries:
        name = entry.name.replace("\\", "/")
        if name.lower().endswith(".c"):
            game[name.casefold()] = (name, sha256)
    root = pathlib.Path(vanilla_root)
    tree = {}
    for path in sorted(root.rglob("*.c")):
        if path.is_file():
            tree[path.relative_to(root).as_posix().casefold()] = path
    differ = []
    missing = []
    for key, (name, sha256) in sorted(game.items()):
        path = tree.get(key)
        if path is None:
            missing.append(name)
        elif _sha256(path) != sha256:
            differ.append(name)
    extra = sorted(
        tree[key].relative_to(root).as_posix() for key in tree if key not in game
    )
    version = dict(digest.properties).get("version")
    info = {
        "scripts_pbo": str(pbo),
        "pbo_version": version,
        "files": len(game),
        "differ": len(differ),
        "missing": len(missing),
        "extra": len(extra),
        "matches": not (differ or missing or extra),
    }
    if info["matches"]:
        return [], [], info
    examples = (differ + missing + extra)[:_EXAMPLES]
    message = VANILLA_ROOT_BUILD_MESSAGE.format(
        root=vanilla_root, game=game_root, files=len(game), pbo=pbo,
        version=version or "unknown", differ=len(differ), missing=len(missing),
        extra=len(extra),
        examples="first: " + ", ".join(examples),
    )
    warning = {
        "check": VANILLA_ROOT_BUILD_RULE_ID,
        "file": str(vanilla_root),
        "line": None,
        "message": message,
        "severity": "WARN",
        "rule_id": VANILLA_ROOT_BUILD_RULE_ID,
    }
    return [warning], [], info
