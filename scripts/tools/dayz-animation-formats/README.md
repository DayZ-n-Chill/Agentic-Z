# dayz-animation-formats

Dependency-free, strict readers and writers for two animation interchange
formats used in DayZ asset pipelines:

- SEAnim version 1;
- unbinarized `RTM_0101`, optionally preceded by one `RTM_MDAT` block.

This tool does not read or write DayZ `.anm`/BMTR files. It does not claim that
an interchange file is accepted by the game: conversion with the appropriate
DayZ tools and a final DayZ/DayZDiag check remain separate gates.

## Install

From the repository root:

```powershell
python -m pip install -e tools/dayz-animation-formats
```

Python 3.9 or newer is required. The runtime has no third-party dependencies.

## Inspect from the command line

```powershell
python -m dayz_animation_formats inspect animation.seanim
python -m dayz_animation_formats inspect animation.rtm --output summary.json
```

The command detects a format only from its exact leading signature. A valid
file returns exit `0` and one deterministic `animation-inspect-v1` JSON
document. Invalid, truncated or unsupported data returns exit `2` and:

```json
{"error":{"code":"ANIM_FORMAT_UNSUPPORTED","message":"unsupported animation format","offset":0}}
```

Expected format errors are written to stdout, not stderr. Output contains no
timestamp or physical input path.

## Library API

```python
from dayz_animation_formats import (
    read_rtm,
    read_rtm_bytes,
    read_seanim,
    read_seanim_bytes,
    write_rtm,
    write_rtm_bytes,
    write_seanim,
    write_seanim_bytes,
)

document = read_rtm("input.rtm")
written_bytes = write_rtm("roundtrip.rtm", document)
```

All readers return plain dictionaries and lists. All writers validate the
complete semantic document before returning bytes or writing a file.
`AnimationFormatError` exposes stable `code`, `message` and optional byte
`offset` fields.

## Supported SEAnim contract

- exact magic `SEAnim`, version `1` and header size `28`;
- animation types `ABSOLUTE=0`, `ADDITIVE=1`, `RELATIVE=2`, `DELTA=3`;
- position, rotation and scale keys;
- float32 or high-precision float64 scalar storage;
- per-bone modifiers, notes and the loop flag;
- bounded counts, strict UTF-8/NUL strings and exact end-of-stream.

Unknown flags, duplicate names or indices, out-of-range frames, non-finite
scalars, truncation and trailing bytes are rejected.

## Supported RTM contract

- one `RTM_0101` animation block;
- optionally, one zero-padded `RTM_MDAT` block immediately before it;
- at least one frame and one bone;
- finite motion, phase and 4x4 affine transform values;
- a fixed bone order in every frame;
- UTF-8 bone payloads of at most 31 bytes plus NUL in each 32-byte field;
- exact end-of-stream.

BMTR, duplicate/out-of-order blocks, unknown blocks, silent string truncation
and trailing bytes are rejected.

## Independent fixtures and license boundary

The fixtures in `tests/fixtures/` contain first-party literal animation data:

| Fixture | Size | SHA-256 | Independent oracle |
|---|---:|---|---|
| `seanim-v1-full.seanim` | 288 | `75af1c6ab01ae715e6cea01e6897b804586687ccf7a234c21be6bef871288b29` | SE2Dev `io_anim_seanim` at `dffe313b635ce8940264201f25db9e68f4486d7e` |
| `rtm-0101-mdat.rtm` | 258 | `37aa63f705d874c79b94721027d376a7cab347fc94691ad419e1172c5597c3f8` | Arma 3 Object Builder 2.5.1 |

SE2Dev is MIT-licensed and is attributed in the repository notices. Arma 3
Object Builder is GPL-3.0-or-later and is used only as an external oracle; no
A3OB or BisDLL source is included or imported by this package.

The local RTM writer was also read successfully by A3OB 2.5.1 under Blender
5.1.1, preserving the expected motion, bones, phases, metadata and matrices.

## Test

```powershell
python -m pytest -q tools/dayz-animation-formats/tests
```
