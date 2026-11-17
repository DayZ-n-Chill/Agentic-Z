# dayz-model-preflight

Read-only, contract-driven pre-export checks for DayZ MLOD models. The tool
combines:

- exact expected dimensions and tolerances;
- required non-empty named selections for bones;
- the DayZ py3d fork's own model findings;
- complete source-to-target face lineage and winding evidence.

It deliberately does not guess intended scale, skeleton membership or face
lineage from geometry. Those facts must be supplied by the caller.

## Requirements and install

The DayZ py3d fork `>=1.6.0` is mandatory. The unrelated package named `py3d`
on PyPI is not compatible.

```powershell
python -m pip install -e tools/py3d
python -m pip install -e tools/dayz-model-preflight
```

At runtime the imported module must expose `IS_DAYZ_FORK is True` and a
semantic version of at least `1.6.0`.

## Command line

```powershell
python -m dayz_model_preflight check target.p3d --contract preflight.json
python -m dayz_model_preflight check target.p3d --contract preflight.json --json result.json
```

The deterministic `dayz-model-preflight-result-v1` document is emitted to
stdout unless `--json` is used. The output contains hashes and logical roles,
not timestamps or physical paths.

| Exit | Verdict | Meaning |
|---:|---|---|
| `0` | `PASS` | Contract and models are valid; no error finding exists. |
| `1` | `FAIL` | Evidence is valid but the target violates it. |
| `2` | `INVALID` | Input, dependency, transform or lineage evidence is missing/unsupported. |

An output file is replaced atomically only after a complete result exists.
The target, source and contract are never modified.

## Contract v1

`source_model` is resolved relative to the contract file and must remain
inside that directory. This minimal example assumes both referenced LODs
contain exactly the single mapped face:

```json
{
  "schema_version": "dayz-model-preflight-v1",
  "scale": {
    "lod_index": 0,
    "expected_dimensions_m": [1.0, 2.0, 0.5],
    "tolerance_m": [0.001, 0.001, 0.001]
  },
  "bones": {
    "requirements": [
      {"lod_index": 0, "selections": ["pelvis"]}
    ]
  },
  "winding": {
    "source_model": "source.p3d",
    "transform": [
      [1.0, 0.0, 0.0, 0.0],
      [0.0, 1.0, 0.0, 0.0],
      [0.0, 0.0, 1.0, 0.0],
      [0.0, 0.0, 0.0, 1.0]
    ],
    "position_tolerance_m": 0.000001,
    "faces": [
      {
        "source": {"lod_index": 0, "face_index": 0},
        "target": {"lod_index": 0, "face_index": 0}
      }
    ]
  }
}
```

`tolerance_m` may be one positive scalar or three positive axis tolerances.
Every named bone selection must exist and contain a point or face.

The full affine 4x4 matrix maps source positions to target positions. Its last
row must be `[0,0,0,1]`; the upper 3x3 must be finite and non-singular.
Positive determinant requires cyclic order preservation and negative
determinant requires reversal.

Contract v1 requires one-to-one mappings of equal polygon arity and complete
coverage of every face in each referenced source and target LOD. It rejects
triangle-to-quad mappings, one-to-many splits, duplicate or uncovered faces,
out-of-range addresses, geometric mismatch and mixed winding. It never
repairs geometry.

## Library API

```python
from dayz_model_preflight import PreflightError, run_preflight

result = run_preflight("target.p3d", "preflight.json")
```

`run_preflight(model_path, contract_path)` always returns the result document;
ordinary invalid inputs become an `INVALID` verdict rather than escaping as an
exception.

## Stable finding codes

- dependency/input: `PREFLIGHT_PY3D_UNAVAILABLE`,
  `PREFLIGHT_CONTRACT_INVALID`, `PREFLIGHT_MODEL_UNREADABLE`,
  `PREFLIGHT_OUTPUT_UNWRITABLE`;
- model/contract mismatch: `PREFLIGHT_LOD_MISSING`,
  `PREFLIGHT_SCALE_MISMATCH`, `PREFLIGHT_BONE_SELECTION_MISSING`,
  `PREFLIGHT_BONE_SELECTION_EMPTY`;
- composed py3d results: `PREFLIGHT_PY3D_ERROR`,
  `PREFLIGHT_PY3D_WARNING`;
- lineage/winding: `PREFLIGHT_WINDING_EVIDENCE_MISSING`,
  `PREFLIGHT_WINDING_UNSUPPORTED_SPLIT`,
  `PREFLIGHT_WINDING_TRANSFORM_INVALID`,
  `PREFLIGHT_WINDING_GEOMETRY_MISMATCH`,
  `PREFLIGHT_WINDING_RELATION_MISMATCH`.

## Test

```powershell
python -m pytest -q tools/dayz-model-preflight/tests
```
