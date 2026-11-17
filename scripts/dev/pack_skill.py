"""Package a skill folder into an installable .skill zip, safely on Windows.

Why this exists instead of skill-creator/scripts/package_skill.py: that script's
validator reads SKILL.md without an explicit encoding, so on Windows Python falls
back to cp1252 and dies with UnicodeDecodeError on any em-dash, arrow or accent
(verified 2026-07-27: 3 of 8 skills failed there). It also matters that the zip
entries use forward slashes -- PowerShell's CreateFromDirectory writes them with
backslashes and the installer then cannot find "<name>/SKILL.md".

Usage:
    python scripts/dev/pack_skill.py <skill-folder> [out-dir]
    python scripts/dev/pack_skill.py skills/dayz-lint

The second argument is a DIRECTORY, not a .skill file name. Without it the
package goes to output/skill-packages/ in this repo (the repo rule for one-shot
deliverables), never next to the skill folder.

Packs the WHOLE folder (SKILL.md + references/ + scripts/ + assets/ ...), because
a bare SKILL.md installs as a mutilated skill with its references missing.
docs/prompt-conventions.md ("When a .skill is packaged") says when to use it.
"""
import os
import re
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = REPO / "output" / "skill-packages"
EXCLUDE_DIRS = {"__pycache__", ".git", ".ipynb_checkpoints"}
EXCLUDE_EXT = {".pyc", ".pyo"}
DESCRIPTION_CAP = 1024


def folded_description(frontmatter: str) -> str:
    """Return the description value, joining YAML folded/literal continuations."""
    lines = frontmatter.splitlines()
    for i, line in enumerate(lines):
        m = re.match(r"^description:\s*(.*)$", line)
        if not m:
            continue
        head = m.group(1).strip()
        if head not in (">", "|", ">-", "|-", ""):
            return head
        parts = []
        for cont in lines[i + 1:]:
            if cont.strip() and not cont.startswith((" ", "\t")):
                break
            parts.append(cont.strip())
        return " ".join(p for p in parts if p)
    return ""


def validate(skill_dir: Path) -> str:
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        raise SystemExit("FAIL: no SKILL.md in %s" % skill_dir)
    text = skill_md.read_text(encoding="utf-8")  # explicit encoding = the whole point
    m = re.match(r"^---\r?\n(.*?)\r?\n---", text, re.S)
    if not m:
        raise SystemExit("FAIL: SKILL.md must start with YAML frontmatter (---)")
    fm = m.group(1)
    name = re.search(r"^name:\s*(.+)$", fm, re.M)
    if not name:
        raise SystemExit("FAIL: frontmatter has no 'name'")
    name = name.group(1).strip()
    desc = folded_description(fm)
    if not desc:
        raise SystemExit("FAIL: frontmatter has no 'description'")
    if len(desc) > DESCRIPTION_CAP:
        raise SystemExit(
            "FAIL: description is %d chars, cap is %d. Move non-triggering text "
            "(caveats, composition notes) into the body rather than truncating."
            % (len(desc), DESCRIPTION_CAP)
        )
    print("name=%s  description=%d chars (cap %d)  nulls=%d"
          % (name, len(desc), DESCRIPTION_CAP, text.count("\x00")))
    return name


def pack(skill_dir: Path, out_dir: Path) -> Path:
    name = validate(skill_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / ("%s.skill" % skill_dir.name)
    written = []
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(skill_dir):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            for fn in files:
                p = Path(root) / fn
                if p.suffix.lower() in EXCLUDE_EXT:
                    continue
                rel = p.relative_to(skill_dir).as_posix()  # forward slashes
                arc = "%s/%s" % (skill_dir.name, rel)
                zf.write(p, arcname=arc)
                written.append(arc)

    # reopen and verify -- a zip that lists fine at write time can still be wrong
    with zipfile.ZipFile(out) as zf:
        names = zf.namelist()
        bad = zf.testzip()
        if bad:
            raise SystemExit("FAIL: corrupt entry %s" % bad)
        expected = "%s/SKILL.md" % skill_dir.name
        if expected not in names:
            raise SystemExit("FAIL: %s missing from zip (entries: %s)" % (expected, names[:5]))
        if any("\\" in n for n in names):
            raise SystemExit("FAIL: backslash in zip entries -- installer will not find them")
        head = zf.read(expected).decode("utf-8")
        if not head.startswith("---"):
            raise SystemExit("FAIL: packed SKILL.md does not start with frontmatter")

    print("OK %s" % out)
    print("entries=%d  bytes=%d" % (len(names), out.stat().st_size))
    for n in sorted(names):
        print("   %s" % n)
    return out


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    skill = Path(sys.argv[1]).resolve()
    dest = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else DEFAULT_OUT_DIR
    pack(skill, dest)
