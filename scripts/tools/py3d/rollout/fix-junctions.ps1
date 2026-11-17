# fix-junctions.ps1 - Re-points the junctions under ~\.agents\skills to the real LocalCache path
# Context: junctions created from inside the Claude app (Store-packaged) point at
# %APPDATA%\Claude\... - that path only exists INSIDE the app, where it is
# virtualized. For host processes (Codex CLI, PowerShell) the junctions dangle.
# This script re-points them to the equivalent physical path under
# %LOCALAPPDATA%\Packages\<Claude>\LocalCache\Roaming\Claude\...
# Scope: ALL junctions under ~\.agents\skills with that target pattern.
# Safety: junctions are removed with 'cmd /c rmdir' (it only deletes the reparse point,
# NEVER the target's contents). PowerShell 5.1+, ASCII only.
# The wheel smoke check is version-agnostic (py3d-*.whl).

$ErrorActionPreference = 'Continue'
$rootB = Join-Path $env:USERPROFILE '.agents\skills'
$VIRT  = (Join-Path $env:APPDATA 'Claude') + '\'

# Auto-detect the real root
$REAL = $null
Get-ChildItem "$env:LOCALAPPDATA\Packages" -Directory -ErrorAction SilentlyContinue |
  Where-Object { $_.Name -match 'Claude|Anthropic' } |
  ForEach-Object {
    $cand = Join-Path $_.FullName 'LocalCache\Roaming\Claude'
    if (-not $REAL -and (Test-Path -LiteralPath $cand)) { $REAL = $cand + '\' }
  }
if (-not $REAL) { Write-Host "[FAIL] LocalCache\Roaming\Claude not found in any package" -ForegroundColor Red; exit 1 }
Write-Host "[INFO] real root: $REAL"

$fixed = 0; $skipped = 0; $broken = 0; $untouched = 0
Get-ChildItem -LiteralPath $rootB -Directory -Force | ForEach-Object {
  $p = $_.FullName
  if ($_.LinkType -ne 'Junction') { $untouched++; return }
  $tg = ($_.Target | Select-Object -First 1)
  if (-not $tg -or -not $tg.StartsWith($VIRT)) {
    if (Test-Path -LiteralPath (Join-Path $p '.')) { $untouched++ } else { Write-Host "[WARN] junction with another dangling target: $($_.Name) -> $tg"; $broken++ }
    return
  }
  $newTarget = $REAL + $tg.Substring($VIRT.Length)
  if (-not (Test-Path -LiteralPath $newTarget)) {
    Write-Host "[SKIP] $($_.Name): real target does not exist ($newTarget)" -ForegroundColor Yellow
    $skipped++; return
  }
  cmd /c rmdir "$p" | Out-Null
  if (Test-Path -LiteralPath $p) { Write-Host "[FAIL] could not remove junction: $p" -ForegroundColor Red; $broken++; return }
  New-Item -ItemType Junction -Path $p -Target $newTarget | Out-Null
  $okRead = $false
  try { $null = Get-ChildItem -LiteralPath $p -ErrorAction Stop | Select-Object -First 1; $okRead = $true } catch {}
  if ($okRead) { Write-Host "[OK]   re-pointed: $($_.Name)"; $fixed++ }
  else { Write-Host "[FAIL] re-pointed but unreadable: $($_.Name)" -ForegroundColor Red; $broken++ }
}

Write-Host "`n=== SMOKE: the rollout skills are readable from the host + wheel present ==="
$skills = @('dayz-model-pipeline','dayz-3d-viewer','dayz-p3d-inspector',
            'dayz-p3d-audit','dayz-pbo-build','dayz-proxy-align','dayz-animation-pipeline')
$smokeFail = 0
foreach ($s in $skills) {
  $sk = Join-Path $rootB "$s\SKILL.md"
  $whDir = Join-Path $rootB "$s\wheels"
  $r = $false; try { $null = Get-Content -LiteralPath $sk -TotalCount 1 -ErrorAction Stop; $r = $true } catch {}
  $w = (Test-Path -LiteralPath $whDir) -and (@(Get-ChildItem -LiteralPath $whDir -Filter 'py3d-*.whl' -ErrorAction SilentlyContinue).Count -ge 1)
  if ($r -and $w) { Write-Host "[OK]   $s (SKILL.md readable, wheel present)" }
  else { Write-Host "[FAIL] $s (readable=$r wheel=$w)" -ForegroundColor Red; $smokeFail++ }
}

Write-Host "`n========================================"
Write-Host ("junctions re-pointed: {0} | skipped (no real target): {1} | untouched: {2} | broken: {3} | smoke fails: {4}" -f $fixed, $skipped, $untouched, $broken, $smokeFail)
if (($broken + $smokeFail) -eq 0) { Write-Host "RESULT: ALL PASSED"; exit 0 } else { Write-Host "RESULT: review the FAILs" -ForegroundColor Red; exit 1 }
