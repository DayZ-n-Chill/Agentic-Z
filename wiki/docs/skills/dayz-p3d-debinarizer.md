---
name: dayz-p3d-debinarizer
---

# DayZ P3D Debinarizer

Converts binarized DayZ .p3d files (ODOL format) to editable MLOD format for Object Builder.

## Preflight gate

Per the L2 rule (`.claude/skills/_shared/dayz-conventions.md`), every DayZ skill that does work gates on `/dayz-preflight` first. Debinarizing pulls .p3d files from anywhere, but the moment you target `P:\` paths an unmounted P-drive silently fails. Run `/dayz-preflight` before this skill.

## Quick Start

```cmd
:: Install dependencies (REQUIRED). This is a Windows workspace; python-lzo and py3d
:: have prebuilt wheels available, no native compiler needed.
pip install python-lzo
pip install git+https://github.com/KoffeinFlummi/py3d.git

:: Run conversion
cd <skill-path>\scripts
python odol_to_mlod.py input.p3d output_mlod.p3d
```

## Architecture

```
scripts/
├── odol_to_mlod.py    # Main converter: ODOL → MLOD (entry point)
├── odol_reader.py     # ODOL v28-73 parser with DayZ v54 support
├── bis_reader.py      # Binary reader (LZO/LZSS, compressed arrays, condensed arrays)
├── math_types.py      # Vector3P, Matrix3P, Matrix4P
├── lzo_decompress.py  # LZO1X decompressor (BI variant, no -16384 in M4)
└── lzss_decompress.py # LZSS decompressor with checksum validation
```

## Workflow

### Step 1: Check the file

```python
import struct
data = open('input.p3d', 'rb').read()
sig = data[:4]
if sig == b'ODOL':
    print("Clean ODOL file")
elif sig == b'MLOD':
    print("Already MLOD — no conversion needed")
else:
    # Search for ODOL signature (may be inside a container)
    idx = data.find(b'ODOL')
    if idx > 0:
        print(f"ODOL found at offset {idx} — container file (e.g. Fire Packer)")
    else:
        print("Not a P3D file")
```

### Step 2: Parse ODOL

```python
from odol_reader import ODOL
odol = ODOL.from_file('input.p3d')  # Auto-detects ODOL offset
print(f'{odol}')  # Shows version, LOD count, mass
for i, lod in enumerate(odol.lods):
    print(f'  LOD {i}: {lod}')
```

### Step 3: Convert to MLOD

```python
from odol_to_mlod import convert_odol_to_mlod
import py3d

mlod = convert_odol_to_mlod(odol)
with open('output_mlod.p3d', 'wb') as f:
    mlod.write(f)
```

### Step 4: Verify

```python
with open('output_mlod.p3d', 'rb') as f:
    verify = py3d.P3D(f)
print(f'{len(verify.lods)} LODs read back OK')
```

## Fire Packer Container Handling

Fire Packer prepends data to the .p3d but does NOT update LOD addresses. Detection and fix:

```python
data = open('protected.p3d', 'rb').read()
odol_offset = data.find(b'ODOL')  # e.g. 420400

if odol_offset > 0:
    # LOD addresses need odol_offset added
    # The ODOL._seek_odol() method handles finding the signature automatically
    # But LOD addresses must be adjusted manually for container files
    
    # After parsing header, adjust each LOD start/end address:
    lod_starts = [reader.read_uint32() + odol_offset for _ in range(n_lods)]
    lod_ends = [reader.read_uint32() + odol_offset for _ in range(n_lods)]
```

**Detection signs of Fire Packer:**
- File starts with zeros (not 'ODOL')
- ODOL signature found at large offset (>1000)
- pbo.json in same PBO contains `"obfuscated": "true"` headers
- Text `"============Fire Packer============"` in PBO headers

## DayZ vs Arma 3 Differences (CRITICAL)

Read `references/format_notes.md` for full details. Summary of 4 key differences:

### 1. ModelInfo — 3 extra fields (v54)
- `allowAnimation` (bool) after `canBeOccluded`
- `forceNotAlpha` as uint32 (not bool) — 3 bytes extra
- `disableCover` (bool) before `animated`

### 2. No hasAnims byte — robust detection required
DayZ v54 sometimes omits the `hasAnims` byte AND can also place Animations
data directly after ModelInfo with no preamble at all (observed on
`dz/gear/containers/55galDrum.p3d` — barrel model, where the byte after
ModelInfo is `0x02` = `n_animations`, not a hasAnims flag).

The simple peek heuristic is NOT enough. `odol_reader.py::ODOL._read` tries
every plausible interpretation and validates by checking that the resulting
LOD address table is internally consistent (every `lod_start[i]` and
`lod_end[i]` inside file bounds, `lod_end >= lod_start`, `permanent[i]`
in `{0, 1}`):

| Candidate | Reads from `saved` | Validates |
|---|---|---|
| **A** | hasAnims byte = 0, LOD addrs at saved+1 | LOD table at saved+1 |
| **B** | hasAnims byte = 1, Animations from saved+1 | LOD table at end of Animations |
| **C** | NO hasAnims byte, Animations directly at saved | LOD table at end of Animations |
| **D** | LOD addrs directly at saved (no anims at all) | LOD table at saved |

Priority: B (canonical Arma 3) > C (DayZ no-byte anims) > A (no-anims byte=0) > D (raw).

### 3. EmbeddedMaterial v20 — 25 extra floats + 1 extra uint32
After `pixelShader`, before `vertexShader`:
- 25 floats (100 bytes) of DayZ PBR extended data
- 1 extra uint32 (typically value 1)

### 4. BI LZO variant — no -16384 in M4 matches
Standard LZO1X subtracts 16384 in M4 match offset calculation.
BI's variant does NOT. Our `lzo_decompress.py` implements BI's variant.

### 5. LZO trailing EOF marker (consumed-bytes correction)
The pure-Python LZO core can exit at `op == expected_size` mid-instruction
without consuming the 3-byte EOF marker `\x11\x00\x00` that some BI streams
append after the final literal run. The `decompress_lzo` public entry point
peeks for that marker after the core returns and adds 3 to `consumed`
when present. Without this, the off-by-3 contaminates the next field in
the parent stream — e.g. on `55galDrum.p3d` LOD 2 UV0 it caused
`n_uv_sets` to be misread as `16777233`, then `n_vertices=16M`, then LZO
failure on the next compressed block.

## Compression System

Read `references/format_notes.md` Section 2 for full details.

- **1024 rule** (v < 64): arrays >= 1024 bytes are compressed; smaller are raw
- **Compression flag** (v >= 64): explicit bool before each compressible block
- **LZO** (v >= 44): LZO1X variant (BI-specific, no -16384 in M4)
- **LZSS** (v < 44): LZSS with checksum validation
- **Condensed arrays**: DefaultFill pattern (1 value for all) or compressed array

## Known Limitations

1. **LOD 0 of very large models** may fail on LZO blocks >400KB (edge case in decompressor)
2. **Named selections** from bone-based reconstruction not implemented (ODOL sections + vertex weights work)
3. **Face winding** is reversed during conversion (ODOL→MLOD) — may need manual flip in Object Builder
4. **UV coordinates** use the first UV set only; additional UV sets are dropped
5. **Proxy geometry** appears as named selections (correct behavior for MLOD)
6. **Mass distribution** is uniform across Geometry LOD points (not weighted by original)

## Dependencies

| Package | Purpose | Install |
|---------|---------|---------|
| py3d (KoffeinFlummi) | MLOD P3D writing | `pip install git+https://github.com/KoffeinFlummi/py3d.git` |
| python-lzo | Native LZO fallback | `apt-get install liblzo2-dev && pip install python-lzo` |

**Note:** python-lzo is optional but recommended for reliability. The skill includes a pure-Python LZO decompressor that works for most cases.

## Version Support

| Version | Game | Status |
|---------|------|--------|
| v54 | DayZ Standalone | ✅ Full support |
| v28-53 | Arma 2/3 | ⚠️ Partial (no DayZ-specific fields) |
| v55-73 | Arma 3 latest | ⚠️ Untested |
| v7 | OFP | ❌ Not supported |
