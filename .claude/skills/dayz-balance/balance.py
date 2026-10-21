"""dayz-balance: compare a mod's item stats with similar vanilla items and flag outliers.

  balance.py <ModName> [--json] [--ratio 1.5] [--min-peers 3]
  balance.py --mod-dir <folder> [--json] [--vanilla-root P:\\]

Reads every config.cpp in the mod and every config.cpp under P:\\DZ\\ (the
unpacked vanilla data). For each mod item (scope = 2 in CfgVehicles,
CfgWeapons or CfgMagazines; any CfgAmmo class that does not set scope = 0)
it finds the nearest vanilla ancestor, takes the vanilla items under that
ancestor as peers, and compares
each stat the mod sets itself: weight, health (hitpoints), damage dealt,
protection (armor multipliers and the Protection class), cargo capacity and
maximum quantity. A value outside the peers' range and at least --ratio times
away from their median is an outlier.

The first output line is the verdict: PASS (exit 0, no outliers), FLAG
(exit 1, at least one outlier) or ERROR (exit 2: bad arguments, no project,
no mod folder, no vanilla data, or a config.cpp that does not parse). The
script only measures; deciding whether an outlier is intended is the AI's
and the user's call. See SKILL.md.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import Optional

HERE = Path(__file__).resolve().parent
SKILLS_DIR = HERE.parent
REPO = SKILLS_DIR.parents[1]
sys.path.insert(0, str(SKILLS_DIR / "_shared"))
import skill_helpers as h  # noqa: E402

# The config grammar of the PostToolUse syntax hook, shared with /dayz-lint.
sys.path.insert(0, str(REPO / "hooks"))
import edit_check  # noqa: E402

P_DRIVE = Path("P:\\")
SECTIONS = ("cfgvehicles", "cfgweapons", "cfgmagazines", "cfgammo")
DAMAGE_TYPES = ("Health", "Blood", "Shock")
# Widen the peer group at most this many parents above the nearest vanilla ancestor,
# so a vest is never measured against every Inventory_Base item.
MAX_WIDEN = 2
PEER_SAMPLE = 5


class BalanceError(Exception):
    """Balance cannot run (exit 2); not a verdict on the mod."""


# --- config tree --------------------------------------------------------------

class Node:
    """A class in config.cpp: its parent name, nested classes and properties."""

    def __init__(self, name: str, parent: Optional[str], line: int, file: Optional[Path]):
        self.name = name
        self.parent = parent
        self.line = line
        self.file = file
        self.classes: dict[str, Node] = {}
        # lower name -> (values, line); scalars are one value lists
        self.props: dict[str, tuple[list, int]] = {}

    def merge(self, other: "Node") -> None:
        """Apply a later definition of the same class on top of this one."""
        if other.parent:
            self.parent = other.parent
        self.props.update(other.props)
        for key, child in other.classes.items():
            if key in self.classes:
                self.classes[key].merge(child)
            else:
                self.classes[key] = child


def parse_config(text: str, file: Optional[Path] = None) -> Node:
    """Build the class tree. Raises edit_check.TokenizeError on text that does not tokenize."""
    toks = edit_check.tokenize(text)
    root = Node("", None, 0, file)
    stack = [root]
    i, n = 0, len(toks)

    def punct(k: int, value: str) -> bool:
        return k < n and toks[k].kind == "punct" and toks[k].text == value

    while i < n:
        tok = toks[i]
        if punct(i, "}"):
            if len(stack) > 1:
                stack.pop()
            i += 1
        elif tok.kind == "ident" and tok.text == "class" and i + 1 < n:
            name = toks[i + 1]
            parent = None
            j = i + 2
            if punct(j, ":") and j + 1 < n:
                parent = toks[j + 1].text
                j += 2
            if punct(j, "{"):
                node = Node(name.text, parent, name.line, file)
                key = name.text.lower()
                if key in stack[-1].classes:
                    stack[-1].classes[key].merge(node)
                    node = stack[-1].classes[key]
                else:
                    stack[-1].classes[key] = node
                stack.append(node)
            i = j + 1
        elif tok.kind == "ident" and (punct(i + 1, "=") or (punct(i + 1, "[") and punct(i + 2, "]"))):
            j = i + (4 if punct(i + 1, "[") else 2)
            values: list = []
            depth = 0
            while j < n:
                t = toks[j]
                if punct(j, "{"):
                    depth += 1
                elif punct(j, "}"):
                    depth -= 1
                    if depth <= 0:
                        j += 1
                        break
                elif punct(j, ";") and depth == 0:
                    break
                elif t.kind == "num":
                    values.append(_number(t.text, negative=punct(j - 1, "-")))
                elif t.kind in ("str", "ident"):
                    values.append(t.text)
                j += 1
            stack[-1].props[tok.text.lower()] = (values, tok.line)
            i = j
        else:
            i += 1
    return root


def _number(text: str, negative: bool) -> float:
    value = float(text)
    return -value if negative else value


# --- class index --------------------------------------------------------------

class Index:
    """Every class of the four item sections, by section and lower name."""

    def __init__(self) -> None:
        self.sections: dict[str, dict[str, Node]] = {s: {} for s in SECTIONS}

    def add(self, root: Node) -> None:
        for section in SECTIONS:
            body = root.classes.get(section)
            if body is None:
                continue
            table = self.sections[section]
            for key, node in body.classes.items():
                if key in table:
                    table[key].merge(node)
                else:
                    table[key] = node

    def get(self, section: str, name: Optional[str]) -> Optional[Node]:
        return self.sections[section].get(name.lower()) if name else None


def load_vanilla(vanilla_root: Path) -> Index:
    dz = vanilla_root / "DZ"
    if not dz.is_dir():
        raise BalanceError(f"no vanilla data at {dz}: mount P: with /dayz-workdrive, or pass --vanilla-root")
    index = Index()
    for path in sorted(dz.rglob("config.cpp")):
        try:
            index.add(parse_config(path.read_text(encoding="utf-8", errors="replace"), path))
        except edit_check.TokenizeError:
            continue  # a vanilla file we cannot read is one less source of peers
    return index


def load_mod(mod_dir: Path) -> Index:
    configs = sorted(mod_dir.rglob("config.cpp"))
    if not configs:
        raise BalanceError(f"{mod_dir} has no config.cpp, so there are no item stats to compare")
    index = Index()
    for path in configs:
        text = path.read_text(encoding="utf-8", errors="replace")
        problems = edit_check.check_config(text)
        if problems:
            raise BalanceError(f"{path} does not parse (line {problems[0].line}: {problems[0].message}); run /dayz-lint and fix it first")
        index.add(parse_config(text, path))
    return index


# --- stats --------------------------------------------------------------------

class Resolver:
    """Looks up a property through a class and its parents, mod classes first."""

    def __init__(self, mod: Index, vanilla: Index):
        self.mod = mod
        self.vanilla = vanilla

    def chain(self, section: str, node: Node, mod_first: bool) -> list[tuple[Node, bool]]:
        """The class and its ancestors as (node, is_mod) pairs."""
        out: list[tuple[Node, bool]] = []
        seen = set()
        is_mod = mod_first
        while node is not None and id(node) not in seen:
            seen.add(id(node))
            out.append((node, is_mod))
            parent = node.parent
            if is_mod:
                # The engine merges a mod class into the vanilla class of the same name, so
                # that class comes next and supplies what the mod does not restate, like scope.
                twin = self.vanilla.get(section, node.name)
                if twin is not None and id(twin) not in seen:
                    seen.add(id(twin))
                    out.append((twin, False))
                    if parent and parent.lower() == node.name.lower():
                        parent = twin.parent  # class Foo: Foo
            nxt = self.mod.get(section, parent) if mod_first else None
            # A mod class that reuses its parent's name (class Foo: Foo) points at vanilla.
            if nxt is None or nxt is node:
                nxt, is_mod = self.vanilla.get(section, parent), False
            else:
                is_mod = True
            node = nxt
        return out

    @staticmethod
    def find(chain: list[tuple[Node, bool]], path: tuple[str, ...]) -> Optional[tuple[list, int, Node, bool]]:
        for node, is_mod in chain:
            cur = node
            for part in path[:-1]:
                cur = cur.classes.get(part.lower())
                if cur is None:
                    break
            else:
                hit = cur.props.get(path[-1].lower())
                if hit is not None:
                    return hit[0], hit[1], node, is_mod
        return None

    @staticmethod
    def subclass_names(chain: list[tuple[Node, bool]], path: tuple[str, ...]) -> list[str]:
        names: dict[str, str] = {}
        for node, _ in chain:
            cur = node
            for part in path:
                cur = cur.classes.get(part.lower())
                if cur is None:
                    break
            else:
                for key, child in cur.classes.items():
                    names.setdefault(key, child.name)
        return list(names.values())

    @staticmethod
    def prop_names(chain: list[tuple[Node, bool]], path: tuple[str, ...]) -> list[str]:
        names: dict[str, str] = {}
        for node, _ in chain:
            cur = node
            for part in path:
                cur = cur.classes.get(part.lower())
                if cur is None:
                    break
            else:
                for key in cur.props:
                    names.setdefault(key, key)
        return list(names.values())

    def stats(self, section: str, node: Node, mod_first: bool) -> dict[str, dict]:
        """stat key -> {value, line, file, from_mod} for every stat the class has."""
        chain = self.chain(section, node, mod_first)
        wanted: list[tuple[str, tuple[str, ...]]] = [
            ("weight", ("weight",)),
            ("health", ("DamageSystem", "GlobalHealth", "Health", "hitpoints")),
            ("capacity", ("itemsCargoSize",)),
            ("quantity", ("varQuantityMax",)),
        ]
        for kind in DAMAGE_TYPES:
            wanted.append((f"damage.{kind.lower()}", ("DamageApplied", kind, "damage")))
        for armor in self.subclass_names(chain, ("DamageSystem", "GlobalArmor")):
            for kind in DAMAGE_TYPES:
                wanted.append((f"protection.{armor.lower()}.{kind.lower()}", ("DamageSystem", "GlobalArmor", armor, kind, "damage")))
        for key in self.prop_names(chain, ("Protection",)):
            wanted.append((f"protection.{key}", ("Protection", key)))

        out: dict[str, dict] = {}
        for key, path in wanted:
            hit = self.find(chain, path)
            if hit is None:
                continue
            values, line, owner, is_mod = hit
            nums = [v for v in values if isinstance(v, float)]
            if key == "capacity":
                if len(nums) != 2:
                    continue
                value = nums[0] * nums[1]
            elif len(nums) == 1 and len(values) == 1:
                value = nums[0]
            else:
                continue
            out[key] = {"value": value, "line": line, "file": owner.file, "from_mod": is_mod}
        return out

    def scope(self, section: str, node: Node, mod_first: bool) -> Optional[float]:
        hit = self.find(self.chain(section, node, mod_first), ("scope",))
        if hit is None:
            return None
        nums = [v for v in hit[0] if isinstance(v, float)]
        return nums[0] if nums else None


# --- peers and outliers -------------------------------------------------------

class Balance:
    def __init__(self, mod: Index, vanilla: Index, ratio: float, min_peers: int):
        self.mod = mod
        self.vanilla = vanilla
        self.ratio = ratio
        self.min_peers = min_peers
        self.r = Resolver(mod, vanilla)
        self._children: dict[str, dict[str, list[str]]] = {}
        self._stats: dict[tuple[str, str], dict] = {}

    def children(self, section: str) -> dict[str, list[str]]:
        if section not in self._children:
            table: dict[str, list[str]] = {}
            for key, node in self.vanilla.sections[section].items():
                if node.parent:
                    table.setdefault(node.parent.lower(), []).append(key)
            self._children[section] = table
        return self._children[section]

    def vanilla_stats(self, section: str, key: str) -> dict:
        if (section, key) not in self._stats:
            node = self.vanilla.sections[section][key]
            self._stats[(section, key)] = self.r.stats(section, node, mod_first=False)
        return self._stats[(section, key)]

    def is_item(self, section: str, node: Node, mod_first: bool) -> bool:
        if section == "cfgammo":
            # Vanilla ammo is scope 1 (P:\DZ\weapons\projectiles) or inherits scope 0 (melee
            # damage classes in P:\DZ\weapons\melee), so only a class that sets scope 0 itself is a base.
            own = node.props.get("scope")
            return own is None or own[0] != [0.0]
        return self.r.scope(section, node, mod_first) == 2

    def descendants(self, section: str, key: str) -> list[str]:
        """The vanilla items at or under a vanilla class, minus classes the mod redefines."""
        table = self.children(section)
        out, todo, seen = [], [key], set()
        while todo:
            cur = todo.pop()
            if cur in seen:
                continue
            seen.add(cur)
            node = self.vanilla.sections[section].get(cur)
            if node is not None and cur not in self.mod.sections[section] and self.is_item(section, node, mod_first=False):
                out.append(cur)
            todo.extend(table.get(cur, []))
        return sorted(out)

    def ancestors(self, section: str, node: Node) -> list[Node]:
        """Vanilla classes above a mod class, nearest first."""
        return [n for n, is_mod in self.r.chain(section, node, mod_first=True)[1:] if not is_mod]

    def check_item(self, section: str, node: Node) -> tuple[list[dict], Optional[str]]:
        """Outliers for one mod item, or a note saying why it was not compared."""
        own = {k: v for k, v in self.r.stats(section, node, mod_first=True).items() if v["from_mod"]}
        if not own:
            return [], "sets none of the compared stats"
        ancestors = self.ancestors(section, node)
        if not ancestors:
            return [], f"has no vanilla parent (parent {node.parent or 'none'})"
        findings = []
        compared = 0
        for stat, mine in own.items():
            group = self.peer_values(section, ancestors, stat)
            if group is None:
                continue
            compared += 1
            base, peers = group
            values = [v for _, v in peers]
            finding = self.judge(mine["value"], values)
            if finding is None:
                continue
            findings.append({
                "item": node.name,
                "section": section,
                "stat": stat,
                "value": mine["value"],
                "file": mine["file"],
                "line": mine["line"],
                "peer_base": base,
                "peer_count": len(values),
                "median": finding["median"],
                "min": min(values),
                "max": max(values),
                "direction": finding["direction"],
                "meaning": meaning(stat, finding["direction"]),
                "ratio": finding["ratio"],
                "peers": [{"class": name, "value": v} for name, v in sorted(peers, key=lambda p: abs(p[1] - finding["median"]))[:PEER_SAMPLE]],
            })
        if compared == 0:
            return [], f"has fewer than {self.min_peers} vanilla peers with the same stats"
        return findings, None

    def peer_values(self, section: str, ancestors: list[Node], stat: str) -> Optional[tuple[str, list[tuple[str, float]]]]:
        for base in ancestors[: MAX_WIDEN + 1]:
            peers = []
            for key in self.descendants(section, base.name.lower()):
                hit = self.vanilla_stats(section, key).get(stat)
                if hit is not None:
                    peers.append((self.vanilla.sections[section][key].name, hit["value"]))
            if len(peers) >= self.min_peers:
                return base.name, peers
        return None

    def judge(self, value: float, values: list[float]) -> Optional[dict]:
        median = statistics.median(values)
        lo, hi = min(values), max(values)
        if value > hi and (median <= 0 or value >= median * self.ratio):
            direction = "high"
        elif value < lo and median > 0 and value <= median / self.ratio:
            direction = "low"
        else:
            return None
        ratio = round(value / median, 2) if median else None
        return {"median": median, "direction": direction, "ratio": ratio}


def meaning(stat: str, direction: str) -> str:
    """What a high or low value means for the player."""
    if stat.startswith("protection."):
        if stat.count(".") >= 2:
            # GlobalArmor values (protection.<kind>.<type>) are damage multipliers:
            # lower lets less damage through.
            return "less protection than vanilla" if direction == "high" else "more protection than vanilla"
        # Protection class values (protection.<name>, such as biological on masks)
        # are coverage: higher keeps more out. The best vanilla mask has biological=1.
        return "more protection than vanilla" if direction == "high" else "less protection than vanilla"
    words = {
        "weight": ("heavier", "lighter"),
        "health": ("tougher", "more fragile"),
        "capacity": ("holds more", "holds less"),
        "quantity": ("holds more", "holds less"),
    }
    high, low = words.get(stat.split(".")[0], ("hits harder", "hits softer"))
    return f"{high if direction == 'high' else low} than vanilla"


# --- report -------------------------------------------------------------------

def balance_mod(
    mod: str,
    mod_dir: Path,
    vanilla_root: Optional[Path] = None,
    display_root: Optional[Path] = None,
    ratio: float = 1.5,
    min_peers: int = 3,
) -> dict:
    """Compare one mod's items with vanilla and return the report."""
    if not mod_dir.is_dir():
        raise BalanceError(f"{mod_dir} not found")
    if ratio <= 1:
        raise BalanceError("--ratio must be greater than 1")
    if min_peers < 1:
        raise BalanceError("--min-peers must be at least 1")
    mod_index = load_mod(mod_dir)
    vanilla = load_vanilla(vanilla_root or P_DRIVE)
    bal = Balance(mod_index, vanilla, ratio, min_peers)
    display_root = display_root or mod_dir.parent

    def rel(path: Optional[Path]) -> Optional[str]:
        if path is None:
            return None
        try:
            return path.relative_to(display_root).as_posix()
        except ValueError:
            return path.as_posix()

    findings, skipped, items = [], [], 0
    for section in SECTIONS:
        for node in mod_index.sections[section].values():
            if not bal.is_item(section, node, mod_first=True):
                continue
            items += 1
            found, note = bal.check_item(section, node)
            for f in found:
                f["file"] = rel(f["file"])
            findings += found
            if note:
                skipped.append({"item": node.name, "section": section, "file": rel(node.file), "line": node.line, "reason": note})
    findings.sort(key=lambda f: (f["file"] or "", f["line"], f["stat"]))
    return {
        "verdict": "FLAG" if findings else "PASS",
        "mod": mod,
        "mod_dir": str(mod_dir),
        "ratio": ratio,
        "min_peers": min_peers,
        "items": items,
        "outliers": len(findings),
        "findings": findings,
        "skipped": skipped,
    }


def _fmt(value: float) -> str:
    return f"{value:g}"


def render_text(report: dict) -> str:
    out = []
    for f in report["findings"]:
        times = f"{f['ratio']:g}x the" if f["ratio"] is not None else "above the"
        out.append(
            f"- {f['file']}:{f['line']}  {f['item']} {f['stat']} = {_fmt(f['value'])}: {f['meaning']}, "
            f"{times} median {_fmt(f['median'])} of {f['peer_count']} vanilla items under {f['peer_base']} "
            f"(range {_fmt(f['min'])} to {_fmt(f['max'])})"
        )
        out.append("    closest: " + ", ".join(f"{p['class']} {_fmt(p['value'])}" for p in f["peers"]))
    for s in report["skipped"]:
        out.append(f"  not compared: {s['item']} {s['reason']}")
    out.append(f"  {report['outliers']} outlier(s) in {report['items']} item(s)")
    return "\n".join(out)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Compare a DayZ mod's item stats with similar vanilla items and flag outliers.")
    parser.add_argument("mod", nargs="?", help="Mod name under workspace/ in the project cached by /dayz-init.")
    parser.add_argument("--mod-dir", type=Path, help="Check this folder instead (its name is the mod name).")
    parser.add_argument("--vanilla-root", type=Path, default=P_DRIVE, help="Folder that holds the unpacked DZ\\ data (default P:\\).")
    parser.add_argument("--ratio", type=float, default=1.5, help="How many times away from the vanilla median counts as an outlier (default 1.5).")
    parser.add_argument("--min-peers", type=int, default=3, help="Fewest vanilla items needed to compare a stat (default 3).")
    parser.add_argument("--json", action="store_true", help="Print the report as JSON after the verdict line.")
    try:
        args = parser.parse_args(argv)
        if not args.mod and not args.mod_dir:
            parser.error("give a <ModName> or --mod-dir")
    except SystemExit as e:
        return 0 if e.code == 0 else 2

    try:
        if args.mod_dir:
            mod_dir = args.mod_dir.resolve()
            report = balance_mod(args.mod or mod_dir.name, mod_dir, args.vanilla_root, Path.cwd(), args.ratio, args.min_peers)
        else:
            project_dir = h.resolve_project_dir()
            report = balance_mod(args.mod, project_dir / "workspace" / args.mod, args.vanilla_root, project_dir, args.ratio, args.min_peers)
    except SystemExit:  # resolve_project_dir already printed why on stderr
        return _error("no usable project: run /dayz-init, or pass --mod-dir", args.json)
    except (BalanceError, OSError, ValueError) as e:
        return _error(str(e), args.json)
    print(report["verdict"])
    print(json.dumps(report, indent=2) if args.json else render_text(report))
    return 0 if report["verdict"] == "PASS" else 1


def _error(message: str, as_json: bool) -> int:
    print("ERROR")
    print(json.dumps({"verdict": "ERROR", "error": message}, indent=2) if as_json else f"  {message}")
    return 2


if __name__ == "__main__":
    sys.stdout.reconfigure(errors="replace")
    sys.exit(main())
