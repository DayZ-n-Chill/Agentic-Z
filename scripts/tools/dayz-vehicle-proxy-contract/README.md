# dayz-vehicle-proxy-contract

Offline auditor for the DayZ vehicle proxy contract: host-to-proxy graph,
source-to-assembly geometric fit, engine properties, animation overlaps and
deployed-PBO byte closure. It turns silent proxy misalignment and stale PBO
payloads into a JSON report before a build is launched.

The PBO closure check compares the bytes of the source MLOD host and proxy
`.p3d` files with the matching uncompressed PBO entries. The manifest's
`deployed_pbo` must therefore be packed without binarizing (pack only).
A binarized build, such as the default `/dayz-build-pbo` run through
AddonBuilder, stores those `.p3d` files as ODOL, so every host and proxy entry
reports `PBO-HASH-MISMATCH` and `audit` exits 1 even when the build is fresh
and correct.

This is an offline check. It does not launch DayZ. The in-game check is
`/dayz-gate ingame`, which reads `script.log` and the RPT.

Its fail-closed PBO reader, `scripts/vehicle_proxy/pbo.py`, is also the reader
of [`scripts/tools/dayz-pbo-diff`](../dayz-pbo-diff/README.md), through `digest_pbo`.

## Install

```powershell
python -m pip install -e scripts/tools/dayz-vehicle-proxy-contract
```

Python 3.10 or newer is required. Runtime dependencies: `numpy`, `scipy`,
`matplotlib`, and the py3d copy in `scripts/tools/py3d` (import name `py3d`).
`pip install` brings in the first three; py3d is not a declared dependency, so
install it with `python -m pip install -e scripts/tools/py3d` or put
`scripts/tools/py3d` on `PYTHONPATH`.

`CfgConvert` is not bundled. The manifest must point at a real converter
binary (or a test shim). There is no default machine path.

## Invoke

From the repo root, without installing:

```powershell
python scripts/tools/dayz-vehicle-proxy-contract/scripts/vehicle_proxy_contract.py audit --manifest <manifest.json> --out <outdir>
python scripts/tools/dayz-vehicle-proxy-contract/scripts/vehicle_proxy_contract.py preview --manifest <manifest.json> --out <outdir>
python scripts/tools/dayz-vehicle-proxy-contract/scripts/vehicle_proxy_contract.py repair --manifest <manifest.json> --staging <abs-staging-dir> --operation <set-autocenter-zero|yaw180|affine-fit>
python scripts/tools/dayz-vehicle-proxy-contract/scripts/vehicle_proxy_contract.py self-test
```

After `pip install -e`:

```powershell
python -m dayz_vehicle_proxy_contract audit --manifest <manifest.json> --out <outdir>
```

`audit` writes `report.json`, `summary.txt` and `lod-overview.json` into a
new `--out` directory. `preview` adds diagnostic PNG scatter plots under
`preview/`. `repair` stages copies under a new absolute `--staging` root
outside the addon; it never overwrites the source tree.

## Exit codes

| Code | Meaning |
|---|---|
| `0` | PASS — audit/preview clean, or `self-test` controls all true |
| `1` | FAIL — reported contract findings, or repair left unresolved defects / staged a partial plan |
| `2` | `self-test` ran but a negative control did not discriminate |
| `3` | `self-test` positive control failed, or its result schema was invalid, or it raised |
| `4` | input / internal error (bad manifest, missing source hash match, raced output, invalid MLOD). No partial report is published |
| `64` | usage error (unknown command or missing required flags) |

Findings are JSON on disk for `audit`/`preview`. stderr carries `usage error:`,
`input error:` or `internal error:` for the non-zero input path.

## Tests

```powershell
python -m pytest tests -q
```

Run from `scripts/tools/dayz-vehicle-proxy-contract/`, or point pytest at that
`tests/` directory from the repo root. Test files resolve `scripts/` from
their own path, not from the current working directory.

## What a green run does not guarantee

A green run predicts that the declared proxy graph, the source-to-P3D fit,
the required properties and the deployed PBO bytes match the manifest
contract. It does **not** predict that the vehicle behaves in the engine.
The PBO byte match only holds for a pack-only PBO; binarized `.p3d` entries
always mismatch their MLOD sources.

Out of scope, deliberately:

- In-game look, animation, IK, damage zones, get-in points or physics.
- Runtime confirmation of deferred host-axis findings (`P3D-AXIS-SELECTION-DEFERRED`
  is a warning; steering/damper motion has to be checked in game).
- That `CfgConvert` XML equals what the engine will play.
- That a staged repair is packed, binarized or deployed.
- That preview PNGs are a visual likeness of the vehicle. They are sampled
  point-cloud scatter plots for fit diagnosis.

Behaviour has to be checked in game.
