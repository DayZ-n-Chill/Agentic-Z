#!/usr/bin/env python3
# Source: bzed/dayz-dev-plugin 6112ac5, contributed to this Pack under its MIT licence by its author.
"""Build the compressed DayZ script API index from the vanilla script sources.

usage: build-api-index.py <dayz-sources>/scripts api [--build "1.30 build 25963285"]
       build-api-index.py <mod-extract-dir> api --mod expansion --build "DayZ-Expansion-Bundle 1.9.80"

Writes <out-dir>/dayz-api.txt.xz (read it with scripts/dayz-api.py): one block per class (modded parts merged), member
signatures without bodies, first line of //! doc comments. Format is described in
the header of the generated file.

With --mod NAME the first argument is the output of extract-dayz-sources.sh for a mod (every PBO of the mod, scripts
in <pbo prefix>/{1_Core..5_Mission}) and the result is <out-dir>/mod-NAME.txt.xz. Each script module (PBO) gets a short
id; file references become @L:id|path, and "#M id prefix pbo" header lines say where it came from.
"""
import re, sys, os, argparse, lzma

MODS = {'static', 'override', 'proto', 'native', 'private', 'protected', 'event',
        'const', 'external', 'volatile', 'sealed', 'owned', 'autoptr', 'ref',
        'notnull', 'local', 'reference', 'abstract', 'final', 'out', 'inout'}
DROP = {'autoptr', 'ref', 'owned', 'external', 'volatile', 'local', 'reference', 'event'}
LAYERS = {'1_Core': '1', '2_GameLib': '2', '3_Game': '3', '4_World': '4', '5_Mission': '5'}
DOC_MAX = 90
# Defines of a stable dedicated server (script log "Module: ... defines:"), used to pick the active base of
# classes declared as `#ifdef X class A extends B #else class A extends C #endif`. These are the Linux server's;
# a Windows server defines PLATFORM_WINDOWS instead (it only matters where a base depends on the platform).
# After a new DayZ release, replace DAYZ_1_30 with that release's version define.
ACTIVE = {'DAYZ_1_30', 'SERVER', 'PLATFORM_LINUX', 'RELEASE', 'FEATURE_CURSOR',
          'FEATURE_NETWORK_RECONCILIATION', 'FEATURE_NETWORK_RECONCILATION'}
VARIANT = re.compile(r'#if(n?)def\s+(\w+)\s*\r?\n(?:\s*//[^\n]*\n)*\s*(?:modded\s+)?class\s+(\w+)\s*(?:extends|:)\s*([\w.]+)\s*\r?\n'
                     r'#else\s*\r?\n\s*(?:modded\s+)?class\s+\3\s*(?:extends|:)\s*([\w.]+)\s*\r?\n#endif')


def scan(src):
    """Remove comments/preprocessor lines; keep //! and /*! docs as \x01text\x02 markers."""
    out, i, n, bol = [], 0, len(src), True
    while i < n:
        c = src[i]
        if bol and c in ' \t':
            out.append(c); i += 1; continue
        if bol and c == '#':
            while i < n and src[i] != '\n':
                i += 1
            continue
        bol = c == '\n'
        if c == '"':
            j = i + 1
            while j < n and src[j] != '"':
                j += 2 if src[j] == '\\' else 1
            out.append(src[i:j + 1]); i = j + 1; continue
        if c == '/' and src.startswith('//', i):
            j = src.find('\n', i)
            j = n if j < 0 else j
            if src.startswith('//!', i) and not src.startswith('//!<', i):
                out.append('\x01' + src[i + 3:j].strip() + '\x02')
            i = j; continue
        if c == '/' and src.startswith('/*', i):
            j = src.find('*/', i + 2)
            j = n if j < 0 else j
            if src.startswith('/*!', i) or src.startswith('/**', i):
                text = re.sub(r'\s+', ' ', re.sub(r'\n\s*\*+', '\n', src[i + 3:j])).strip()
                text = re.sub(r'[@\\](?:brief|class)\s*', '', text)
                text = re.split(r'(?<=[.!?])\s|[@\\](?:code|param|return|see|details|note)\b', text)[0].strip()
                if re.search(r'©|\(c\)\s*\d{4}|[Cc]opyright|[Ll]icense', text) or text.endswith('.c'):   # file header, not a doc
                    text = ''
                out.append('\x01' + text + '\x02')
            out.append('\n' * src.count('\n', i, j))
            i = j + 2; continue
        out.append(c); i += 1
    return ''.join(out)


def split(text):
    """Yield (header, body|None) statements at brace depth 0 of text."""
    i, n, start = 0, len(text), 0
    while i < n:
        c = text[i]
        if c == '\x01':
            i = text.index('\x02', i)
        elif c == '"':
            i += 1
            while i < n and text[i] != '"':
                i += 2 if text[i] == '\\' else 1
        elif c == ';':
            h = text[start:i]
            if h.strip():
                yield h, None
            start = i + 1
        elif c == '{':
            j, d = i + 1, 1
            while j < n and d:
                ch = text[j]
                if ch == '\x01':
                    j = text.index('\x02', j)
                elif ch == '"':
                    j += 1
                    while j < n and text[j] != '"':
                        j += 2 if text[j] == '\\' else 1
                elif ch == '{':
                    d += 1
                elif ch == '}':
                    d -= 1
                j += 1
            h = text[start:i]
            body = text[i + 1:j - 1]
            hn = re.sub(r'\x01.*?\x02', ' ', h, flags=re.S)
            if '=' in hn and '(' not in hn.split('=')[0]:   # initializer list: part of a field
                k = text.find(';', j)
                k = n if k < 0 else k
                yield h + '=' + text[i:k], None
                i, start = k, k + 1
            else:
                yield h, body
                i = j
                if text[i:i + 1] == ';':
                    i += 1
                start = i
                continue
        i += 1


def clean(h):
    docs = re.findall(r'\x01(.*?)\x02', h, re.S)
    h = re.sub(r'\x01.*?\x02', ' ', h, flags=re.S)
    obsolete = bool(re.search(r'\[\s*Obsolete', h))
    h = re.sub(r'^\s*(\[[^\]]*\]\s*)+', '', h)           # leading attributes
    h = re.sub(r'\s+', ' ', h).strip()
    return h, (docs[-1].strip() if docs else ''), obsolete


def short(s):
    s = re.sub(r'\s*,\s*', ',', s)
    s = re.sub(r'\s*=\s*', '=', s)
    s = re.sub(r'\s*([<>])\s*', r'\1', s)
    s = re.sub(r'\b(autoptr|ref|owned|notnull|reference)\s+', '', s)
    return s.strip()


def member(h, doc, obs):
    """Return (kind, name, line) for a class member header, or None."""
    h, doc2, obs2 = clean(h)
    doc, obs = doc2 or doc, obs or obs2
    if not h:
        return None
    base = h.split('=', 1)[0]
    if '(' in base:
        pre, rest = h.split('(', 1)
        params = rest.rsplit(')', 1)[0]
        toks = re.findall(r'~?[\w.]+(?:<[^>]*>)?(?:\[\])?|\S', pre)
        if not toks:
            return None
        name = toks[-1]
        mods, ret = [], []
        for t in toks[:-1]:
            if t in MODS:
                if t not in DROP:
                    mods.append('native' if t == 'proto' else t)
            else:
                ret.append(t)
        mods = [m for k, m in enumerate(mods) if m not in mods[:k] and not (m == 'native' and 'native' in mods[:k])]
        if 'native' in mods:
            mods = [m for m in mods if m != 'native'] + ['native']
        line = ' '.join(mods + [short(' '.join(ret)) or 'void', name]) if False else None
        sig = (' '.join(mods) + ' ' if mods else '') + (short(' '.join(ret)) + ' ' if ret else '') + name + '(' + short(params) + ')'
        key = re.sub(r'\b(override|static)\s+', '', sig)
        kind = 'm'
    else:
        toks = [t for t in re.findall(r'[^\s=]+(?:<[^>]*>)?', base)]
        decl = short(h)
        if not re.match(r'(static )?(private |protected )*const\b', decl):
            decl = decl.split('=', 1)[0]
        decl = re.sub(r'\b(autoptr|ref|owned)\s+', '', decl)
        sig = decl
        name = re.sub(r'\[.*', '', base.split()[-1]) if base.split() else decl
        key = sig
        kind = 'f'
    if obs:
        sig = 'OBSOLETE ' + sig
    if doc and doc[0] not in '@}{':
        doc = doc[:DOC_MAX]
        sig += ' #' + doc
    if not re.search(r'\w', sig):
        return None
    return kind, name, sig, key


HDR = re.compile(r'^(?:(modded|sealed|abstract)\s+)*(class|enum|struct)\s+(\w+)\s*(<[^>]*>)?\s*(?:(?:extends|:)\s*([\w.]+(?:<[^>]*>)?))?\s*$')


def class_variants(raw):
    """{class: (active base, other base)} for classes declared with different bases under #ifdef/#else."""
    stack, seen = [], {}
    for line in raw.splitlines():
        t = line.strip()
        m = re.match(r'#if(n?)def\s+(\w+)', t)
        if m:
            stack.append([(m.group(2) in ACTIVE) != bool(m.group(1)), True]); continue
        if t.startswith('#else') and stack:
            stack[-1][1] = False; continue
        if t.startswith('#endif') and stack:
            stack.pop(); continue
        m = re.match(r'(?:modded\s+)?class\s+(\w+)\s*(?:extends|:)\s*([\w.]+)', t)
        if m and stack:
            active = all(c if first else not c for c, first in stack)
            seen.setdefault(m.group(1), []).append((m.group(2), active))
    out = {}
    for cls, v in seen.items():
        act = [b for b, a in v if a]
        oth = [b for b, a in v if not a and b not in act]
        if act and oth:
            out[cls] = (act[0], oth[0])
    return out


def parse_file(path, layer, rel, classes, enums, globs):   # rel: file token, e.g. 4:Entities/X.c or 3:Core|Entities/X.c
    raw = open(path, encoding='utf-8', errors='replace').read()
    variants = class_variants(raw)
    text = scan(raw)
    for h, body in split(text):
        hc, doc, obs = clean(h)
        alt = []
        if hc.count('class ') > 1:   # #ifdef/#else header variants: keep the last, remember the other bases
            alt = re.findall(r'class\s+\w+\s*(?:extends|:)\s*([\w.]+)', hc)[:-1]
            hc = re.sub(r'^.*\b((?:modded\s+)?class\s+\w+)', r'\1', hc)
        m = HDR.match(re.sub(r'\b(modded|sealed|abstract)\b', lambda x: x.group(0), hc))
        if m and body is not None:
            kind, name = m.group(2), m.group(3)
            modded = 'modded' in hc.split(' class')[0].split(' enum')[0].split()
            tparams = re.sub(r'\s*Class\s+|\s*typename\s+', '', (m.group(4) or '')[1:-1]).replace(' ', '')
            base = m.group(5)
            if name in variants:
                base, other = variants[name]
                alt = [other]
            if kind == 'enum':
                e = enums.setdefault(name, {'base': base, 'items': [], 'files': []})
                e['files'].append(rel)
                val = -1
                for item in body.split(','):
                    item, d, _ = clean(item.replace(';', ' '))
                    if not item:
                        continue
                    nm, _, v = item.partition('=')
                    nm, v = nm.strip(), v.strip()
                    if v:
                        try:
                            val = int(v, 0)
                            v = str(val)
                        except ValueError:
                            val = None
                    elif isinstance(val, int):
                        val += 1
                        v = str(val)
                    e['items'].append(nm + ('=' + v if v else '') + (' #' + d[:DOC_MAX] if d else ''))
                continue
            c = classes.setdefault(name, {'base': None, 'tp': '', 'members': {}, 'files': [], 'doc': ''})
            if not modded:
                c['plain'] = True
            if base and not c['base']:
                c['base'] = base
            if tparams and not c['tp']:
                c['tp'] = tparams
            if doc and not c['doc'] and doc[0] not in '@}{':
                c['doc'] = doc[:DOC_MAX]
            if rel not in c['files']:
                c['files'].append(rel)
            c.setdefault('alt', [])
            c['alt'] += [x for x in alt if x not in c['alt']]
            for mh, mb in split(body):
                r = member(mh, '', False)
                if r and not re.match(r'(?:\w+ )*?private\b', r[2]):   # unreachable from mods
                    k, nm, sig, key = r
                    c['members'].setdefault(key, (k, nm, sig))
            continue
        if m and body is None and m.group(2) == 'class':   # forward / empty class
            c = classes.setdefault(m.group(3), {'base': None, 'tp': '', 'members': {}, 'files': [], 'doc': doc[:DOC_MAX]})
            c['plain'] = True
            if rel not in c['files']:
                c['files'].append(rel)
            continue
        if hc.startswith('typedef'):
            globs['typedef'].append(short(hc[7:].strip()) + (' #' + doc[:DOC_MAX] if doc else ''))
            continue
        if not hc:
            continue
        r = member(h, '', False)
        if r:
            k, nm, sig, key = r
            globs['fn' if k == 'm' else 'var'].append(sig)


def module_ids(root):
    """{module dir (relative to root): short id} for every dir that has a layer dir (1_Core..5_Mission) as a child."""
    mods = []
    for dp, dn, fn in os.walk(root):
        dn.sort()
        if any(d in LAYERS for d in dn):
            mods.append(os.path.relpath(dp, root))
            dn[:] = [d for d in dn if d not in LAYERS]
    ids, used = {}, set()
    for m in sorted(mods):
        parts = [x for x in m.split(os.sep) if x != '.']
        if parts and parts[-1].lower() == 'scripts':
            parts = parts[:-1] or parts
        if len(parts) > 1:
            parts = parts[1:]
        i = '/'.join(parts) or 'scripts'
        while i in used:
            i += '_'
        used.add(i)
        ids[m] = i
    return ids


def collect_defines(root, pbos):
    """{pbo prefix: [names]} from CfgMods `defines[]` in every config.cpp and from active `#define NAME` lines in .c files."""
    out = {}
    prefixes = sorted(pbos, key=len, reverse=True)
    for dp, dn, fn in os.walk(root):
        dn.sort()
        rel = os.path.relpath(dp, root).replace(os.sep, '/')
        pre = next((x for x in prefixes if rel == x or rel.startswith(x + '/')), rel.split('/')[0])
        for f in sorted(fn):
            if f != 'config.cpp' and not f.endswith('.c'):
                continue
            t = open(os.path.join(dp, f), encoding='utf-8', errors='replace').read()
            names = []
            if f == 'config.cpp':
                for m in re.finditer(r'\bdefines\[\]\s*=\s*\{([^}]*)\}', t):
                    names += re.findall(r'"([^"]+)"', m.group(1))
            else:
                names = re.findall(r'^[ \t]*#define[ \t]+(\w+)', t, re.M)
            for n in names:
                if n not in out.setdefault(pre, []):
                    out[pre].append(n)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('scripts'); ap.add_argument('out')
    ap.add_argument('--build', default='')
    ap.add_argument('--mod', default=None, help='index a mod extraction instead of the vanilla scripts; writes mod-NAME.txt.xz')
    a = ap.parse_args()
    # None = no --mod; a given value, the empty string too, must pass the name check (never fall back to vanilla).
    if a.mod is not None:
        if not re.fullmatch(r'[A-Za-z0-9_.-]+', a.mod) or a.mod in ('.', '..'):
            ap.error("--mod must match [A-Za-z0-9_.-]+ and must not be . or ..")
    if os.path.islink(a.out) and not os.path.isdir(a.out):
        ap.error("--out is a non-directory or broken symlink; refusing")
    _out_dir = os.path.realpath(a.out)
    _target = os.path.join(a.out, 'mod-' + a.mod + '.txt.xz' if a.mod else 'dayz-api.txt.xz')
    if os.path.islink(_target):
        ap.error("output path is a symlink; refusing")
    if os.path.lexists(_target):
        _resolved = os.path.realpath(_target)
        if os.path.commonpath([_out_dir, _resolved]) != _out_dir:
            ap.error("output path resolves outside --out; refusing")
    classes, enums, globs = {}, {}, {'typedef': [], 'fn': [], 'var': []}
    ids = module_ids(a.scripts) if a.mod else {'.': ''}
    pbos = {}
    if a.mod and os.path.exists(os.path.join(a.scripts, 'pbo-map.tsv')):
        for l in open(os.path.join(a.scripts, 'pbo-map.tsv')):
            pre, _, pbo = l.rstrip('\n').partition('\t')
            pbos[pre.replace('\\', '/')] = pbo
    for layer in sorted(LAYERS):
        for mod in sorted(ids):
            root = os.path.join(a.scripts, mod, layer)
            for dp, dn, fn in os.walk(root):
                dn.sort()
                for f in sorted(fn):
                    if not f.endswith('.c'):
                        continue
                    p = os.path.join(dp, f)
                    rel = LAYERS[layer] + ':' + (ids[mod] + '|' if ids[mod] else '') + os.path.relpath(p, root)
                    parse_file(p, layer, rel, classes, enums, globs)
    lines = [
        '# ' + ('Script API index of the mod ' + a.mod if a.mod else 'DayZ script API index') + ', ' + (a.build or 'unknown build') + '. Generated by scripts/build-api-index.py from the ' + ('extracted mod PBOs' if a.mod else 'vanilla scripts') + '.',
        '# ' + ('Copyright of the indexed mod scripts belongs to their authors and is subject to the mod\'s own license; only declarations are kept.' if a.mod else
              'Copyright (c) Bohemia Interactive a.s. All rights reserved. Declarations extracted from the DayZ scripts; not covered by the licence of the tool that built this index.'),
        '# ' + ('Each script module (PBO) is listed in a "#M id prefix pbo" line; the pbo is relative to the mod directory. A file @L:id|path is inner path = layer dir + path inside that pbo.' if a.mod else
              'All scripts are in dta/scripts.pbo; inner path = layer dir + path, e.g. 4:Entities/X.c -> 4_World\\Entities\\X.c (see dayz-api.py src).'),
        '# Bodies stripped. "#text" = first line of the //! doc comment. Layers: 1=1_Core 2=2_GameLib 3=3_Game 4=4_World 5=5_Mission.',
        '# CLASS Name<T> : Base @L:path ... (files that declare it, first = main declaration, L = layer 1..5; modded parts merged; a trailing [modded] means every declaration is `modded class`, the class itself lives in vanilla or another mod). Members: [static|override|private|protected|native] ret Name(params) | type field. Overridden methods are listed by name only on an "override:" line (signature is in the base class); use `dayz-api.py class X --inherited` to walk bases.',
        '# "native" = implemented in the engine (proto native). ENUM Name: value list. TYPEDEF/FN/VAR sections at the end hold top-level declarations.' + (' DEFINES lists the #ifdef defines per PBO prefix (from config.cpp defines[] and #define lines).' if a.mod else '')]
    if a.mod:
        for m in sorted(ids, key=lambda m: ids[m]):
            pre = m.replace(os.sep, '/')
            lines.append('#M ' + ids[m] + ' ' + pre + ' ' + pbos.get(pre, '?'))
    lines.append('')
    for name in sorted(classes):
        c = classes[name]
        files = c['files']
        # compress file list: first file full, rest as paths too (short enough); modded classes list every layer
        h = 'CLASS ' + name + (('<' + c['tp'] + '>') if c['tp'] else '') + (' : ' + short(c['base']) if c['base'] else '') + ' @' + ' @'.join(files) + ('' if c.get('plain') else ' [modded]')
        lines.append(h)
        if c.get('alt'):
            lines.append(' #base is ' + short(c['base']) + ' on a stable server, ' + ' or '.join(c['alt']) + ' when its #ifdef define (e.g. FEATURE_NETWORK_RECONCILIATION) is off')
        if c['doc']:
            lines.append(' #' + c['doc'])
        ovr = []
        for k, nm, sig in sorted(c['members'].values(), key=lambda t: (t[0] == 'm', t[1].lower())):
            if re.match(r'(protected |private )?override ', sig):
                if nm not in ovr:
                    ovr.append(nm)
                continue
            lines.append(' ' + sig)
        if ovr:
            lines.append(' override: ' + ' '.join(ovr))
    for name in sorted(enums):
        e = enums[name]
        lines.append('ENUM ' + name + (' : ' + e['base'] if e['base'] else '') + ' @' + ' @'.join(e['files']))
        lines.append(' ' + ' '.join(i.replace(' ', '_', 0) for i in e['items']) if all('#' not in i for i in e['items']) else '\n'.join(' ' + i for i in e['items']))
    for sec in ('typedef', 'fn', 'var'):
        lines.append(sec.upper())
        lines.extend(' ' + s for s in sorted(set(globs[sec])))
    if a.mod:
        lines.append('DEFINES')   # compile-time defines: usable in #ifdef, set by CfgMods defines[] or a #define in a script file
        for pre, names in sorted(collect_defines(a.scripts, pbos).items()):
            lines.append(' ' + pre + ': ' + ' '.join(names))
    lines = [l for l in lines if l.strip() or l == '']
    os.makedirs(a.out, exist_ok=True)
    out = os.path.join(a.out, 'mod-' + a.mod + '.txt.xz' if a.mod else 'dayz-api.txt.xz')
    if os.path.islink(out):
        ap.error("output path is a symlink; refusing")
    with lzma.open(out, 'wt', encoding='utf-8', preset=9 | lzma.PRESET_EXTREME) as f:
        f.write('\n'.join(lines) + '\n')
    print(out, os.path.getsize(out), 'bytes', len(classes), 'classes', len(enums), 'enums')


if __name__ == '__main__':
    main()
