#!/usr/bin/env python3
# Source: bzed/dayz-dev-plugin 6112ac5, contributed to this Pack under its MIT licence by its author.
"""Look up the DayZ script API from compressed indexes (dayz-api.txt.xz, mod-*.txt.xz) you built locally.

  dayz-api.py class NAME [--inherited]   members of a class (--inherited: also every base class)
  dayz-api.py find REGEX [-c CLASS]      member lines matching REGEX (case-insensitive), with their class
  dayz-api.py sub NAME [--all]           classes extending NAME (--all: transitively)
  dayz-api.py enum NAME                  enum values; `find` also searches enum values and top-level declarations
  dayz-api.py src NAME                   source files declaring a class/enum, with ready `dayzmake cat` commands
  dayz-api.py chain NAME                 base class chain
  dayz-api.py defines [REGEX]            #ifdef defines of the indexed mods (e.g. EXPANSIONMODMARKET, CF_MODULES)

Vanilla (dayz-api.txt.xz) is always searched. Add mods with -m/--mod: expansion (the whole Expansion bundle), cf, cot,
dabs, or `-m all`; several with a comma (`-m cf,expansion`). Results of a mod are tagged [mod]; a mod's `modded class X`
parts show up under their own tag next to the vanilla class (`class X -m expansion --mods-only` prints just those). Output is capped at --max lines (default 120).
Run `dayz-api.py class X` before relying on a method.
"""
import argparse, glob, lzma, os, re, sys

# The indexes hold Bohemia's (and mod authors') declarations, so this Pack does not ship them: build them with
# extract-dayz-sources.sh and build-api-index.py into $DAYZ_API_DIR (default ~/.cache/dayz-api).
API = os.environ.get('DAYZ_API_DIR') or os.path.join(os.path.expanduser('~'), '.cache', 'dayz-api')
LAYER = {'1': '1_Core', '2': '2_GameLib', '3': '3_Game', '4': '4_World', '5': '5_Mission'}


def available():
    return sorted(re.match(r'mod-(.+)\.txt\.xz', os.path.basename(p)).group(1) for p in glob.glob(os.path.join(API, 'mod-*.txt.xz')))


def load(mods):
    """Return ({(kind, name): [block, ...]}, {mod: {'title', 'modules': {id: (prefix, pbo)}}}); block = {head, lines, mod}."""
    blocks, info = {}, {}
    for mod in ['vanilla'] + mods:
        path = os.path.join(API, 'dayz-api.txt.xz' if mod == 'vanilla' else f'mod-{mod}.txt.xz')
        cur, inf = None, info.setdefault(mod, {'title': '', 'modules': {}})
        with lzma.open(path, 'rt', encoding='utf-8') as f:
            for line in f:
                line = line.rstrip('\n')
                if line.startswith('#'):
                    if line.startswith('#M '):
                        i, prefix, pbo = line[3:].split(' ', 2)
                        inf['modules'][i] = (prefix, pbo)
                    elif not inf['title']:
                        inf['title'] = re.sub(r'^Script API index of the mod \w+, ', '', line[2:].split('. Generated')[0])
                elif line.startswith(('CLASS ', 'ENUM ')):
                    kind, rest = line.split(' ', 1)
                    name = re.match(r'\w+', rest).group(0)
                    cur = {'head': line, 'lines': [], 'mod': mod}
                    blocks.setdefault((kind, name), []).append(cur)
                elif line in ('TYPEDEF', 'FN', 'VAR', 'DEFINES'):
                    cur = {'head': line, 'lines': [], 'mod': mod}
                    blocks.setdefault(('TOP', line), []).append(cur)
                elif cur is not None and line:
                    cur['lines'].append(line)
    return blocks, info


def base_of(blocks):
    for b in blocks:
        m = re.search(r' : ([\w.]+)', b['head'])
        if m:
            return m.group(1)


def files_of(head):
    """[(layer, module id or '', path)] of a CLASS/ENUM header."""
    return [(l, m or '', p) for l, m, p in re.findall(r' @(\d):(?:([^\s|]+)\|)?(\S+)', head)]


def brief(b, multi):
    """Header without the file list: layers, and the mod modules that declare it (use `src` for the files)."""
    h = b['head']
    fl = files_of(h)
    if fl:
        mods = sorted({m for _, m, _ in fl if m})
        h = h.split(' @')[0] + ' @' + ','.join(sorted({l for l, _, _ in fl})) + (' {' + ','.join(mods) + '}' if mods else '')
        h += ' [modded]' if b['head'].endswith(' [modded]') else ''
    return (f"[{b['mod']}] " if multi else '') + h


def emit(lines, cap):
    for n, l in enumerate(lines):
        if n >= cap:
            print(f'... {len(lines) - cap} more lines (raise --max or narrow the query)')
            return
        print(l)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=['class', 'find', 'sub', 'enum', 'chain', 'src', 'defines'])
    ap.add_argument('arg', nargs='?', default='')
    ap.add_argument('-m', '--mod', default='', help='mods to include: ' + ','.join(available()) + ', all')
    ap.add_argument('--mods-only', action='store_true', help='class/enum: print only the mods\' parts (e.g. what Expansion adds to PlayerBase)')
    ap.add_argument('--inherited', action='store_true')
    ap.add_argument('--all', action='store_true')
    ap.add_argument('-c', '--cls')
    ap.add_argument('--max', type=int, default=120)
    a = ap.parse_args()
    if a.cmd != 'defines' and not a.arg:
        ap.error(f'{a.cmd} needs an argument')
    mods = available() if a.mod == 'all' else [m for m in a.mod.split(',') if m]
    for m in mods:
        if m not in available():
            sys.exit(f'unknown mod {m!r}; available: {", ".join(available())}')
    if a.cmd == 'defines':
        mods = mods or available()
    if not os.path.isfile(os.path.join(API, 'dayz-api.txt.xz')):
        sys.exit(f"no index in {API}: extract the scripts with extract-dayz-sources.sh <DayZ install> <dir>, then run\n"
                 f"  build-api-index.py <dir>/scripts {API}   (or set DAYZ_API_DIR)")
    blocks, info = load(mods)
    multi = len(info) > 1
    out = []
    hint = '' if mods else '  (searched vanilla only; add -m expansion,cf,cot,dabs or -m all for the mods)'
    if a.cmd == 'class':
        name, seen = a.arg, set()
        while name and name not in seen and ('CLASS', name) in blocks:
            seen.add(name)
            bl = blocks[('CLASS', name)]
            for b in bl:
                if a.mods_only and b['mod'] == 'vanilla':
                    continue
                out.append(brief(b, multi))
                out.extend(b['lines'])
            if not a.inherited:
                break
            name = base_of(bl)
        if not out:
            sys.exit(f'no class {a.arg!r}; try: dayz-api.py find {a.arg}{hint}')
    elif a.cmd == 'src':
        bl = blocks.get(('CLASS', a.arg)) or blocks.get(('ENUM', a.arg))
        if not bl:
            sys.exit(f'no class or enum {a.arg!r}{hint}')
        for b in bl:
            if b['mod'] == 'vanilla':
                out.append('pbo: <DayZ install>/dta/scripts.pbo  (print one file: dayzmake cat <pbo> \'<path>\')')
            else:
                out.append(f"[{b['mod']}] pbo: <mod dir>/<pbo> as listed; mod dir = steamapps/workshop/content/221100/<id> ({info[b['mod']]['title']})")
            for l, mid, pth in files_of(b['head']):
                inner = LAYER[l] + '\\' + pth.replace('/', '\\')
                if b['mod'] == 'vanilla':
                    out.append(inner)
                else:
                    prefix, pbo = info[b['mod']]['modules'].get(mid, ('?', '?'))
                    out.append(f"{pbo}  {inner}")
    elif a.cmd == 'chain':
        name, seen = a.arg, []
        while name and name not in seen and ('CLASS', name) in blocks:
            seen.append(name)
            name = base_of(blocks[('CLASS', name)])
        out.append(' > '.join(seen + ([name] if name and name not in seen else [])))
    elif a.cmd == 'sub':
        kids = {}
        for (k, n), bl in blocks.items():
            if k == 'CLASS' and base_of(bl):
                kids.setdefault(base_of(bl), set()).add(n)
        todo, found = [a.arg], []
        while todo:
            for k in sorted(kids.get(todo.pop(0), [])):
                found.append(k)
                if a.all:
                    todo.append(k)
        out.append(' '.join(found) or f'no subclasses of {a.arg}{hint}')
    elif a.cmd == 'enum':
        bl = blocks.get(('ENUM', a.arg))
        if not bl:
            sys.exit(f'no enum {a.arg!r}{hint}')
        for b in bl:
            out.append(brief(b, multi))
            out.extend(b['lines'])
    elif a.cmd == 'defines':
        rx = re.compile(a.arg or '.', re.I)
        for b in blocks.get(('TOP', 'DEFINES'), []):
            for l in b['lines']:
                pre, _, names = l.strip().partition(': ')
                hit = [n for n in names.split() if rx.search(n)]
                if hit:
                    out.append(f"[{b['mod']}] {pre}: {' '.join(hit)}")
        if not out:
            out.append('no matching define')
    else:
        rx = re.compile(a.arg, re.I)
        for (k, n), bl in sorted(blocks.items()):
            if a.cls and n != a.cls:
                continue
            for b in bl:
                if k == 'TOP' and n == 'DEFINES':
                    continue
                if k == 'CLASS' and rx.search(n):
                    out.append(brief(b, multi))
                tag = f"[{b['mod']}] " if multi else ''
                for l in b['lines']:
                    if rx.search(l):
                        out.append(f'{tag}{n}: {l.strip()}' if k != 'TOP' else f'{tag}{n.lower()}: {l.strip()}')
        if not out:
            out.append('no match' + hint)
    emit(out, a.max)


if __name__ == '__main__':
    main()
