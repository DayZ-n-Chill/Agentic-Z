# /dayz-gate visual: the shots file

The shots file lists the screenshots `/dayz-gate visual` takes and compares. Its default place is `output/<ModName>-plan/visual-shots.json`, or pass `--shots FILE`.

```json
{
  "mod": "MyVest",
  "threshold": 0.01,
  "shots": [
    {"id": "hud-icon", "feature": "The vest icon shows on the HUD", "at": 20},
    {"id": "hud-clock", "feature": "The HUD with the clock left out", "at": 25, "threshold": 0.02, "ignore": [[1700, 20, 200, 40]]}
  ]
}
```

| Key | Notes |
|---|---|
| `id` | Letters, digits, `_`, `.` or `-` with no spaces. It names the capture, baseline and diff files. |
| `feature` | Says in words what the shot shows. |
| `at` | Seconds after the client joins the mission, 0 or more. |
| `threshold` | Optional. The share of pixels, 0 to 1, that may change. File level is the default for every shot. |
| `ignore` | Optional. Areas to leave out, each `[x, y, width, height]` in capture pixels: clocks, chat, anything that changes on its own. |
