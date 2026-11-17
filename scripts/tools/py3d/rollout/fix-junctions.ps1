# fix-junctions.ps1 - Re-apunta las junctions de ~\.agents\skills al path real LocalCache
# Contexto (2026-06-07): la migracion plugin-canonical 2026-06-05 creo junctions con target
# <claude-appdata>\... - ese path solo existe DENTRO de la app Claude
# (Store-virtualizada). Para procesos host (Codex CLI, PowerShell) las junctions cuelgan.
# Este script las re-apunta al path fisico equivalente bajo
# %LOCALAPPDATA%\Packages\<Claude>\LocalCache\Roaming\Claude\...
# Alcance aprobado por the author: TODAS las junctions rotas con ese patron de target.
# Seguridad: las junctions se eliminan con 'cmd /c rmdir' (solo borra el reparse point,
# NUNCA el contenido del target). PowerShell 5.1+, ASCII only.
# S3 2026-06-07: smoke de wheel version-agnostic (py3d-*.whl, antes pineaba 1.2.0).

$ErrorActionPreference = 'Continue'
$rootB = 'C:\Users\<you>\.agents\skills'
$VIRT  = '<claude-appdata>\'

# Autodetectar la raiz real (mismo metodo que apply-s2-rollout v2)
$REAL = $null
Get-ChildItem "$env:LOCALAPPDATA\Packages" -Directory -ErrorAction SilentlyContinue |
  Where-Object { $_.Name -match 'Claude|Anthropic' } |
  ForEach-Object {
    $cand = Join-Path $_.FullName 'LocalCache\Roaming\Claude'
    if (-not $REAL -and (Test-Path -LiteralPath $cand)) { $REAL = $cand + '\' }
  }
if (-not $REAL) { Write-Host "[FAIL] no se encontro LocalCache\Roaming\Claude en ningun paquete" -ForegroundColor Red; exit 1 }
Write-Host "[INFO] raiz real: $REAL"

$fixed = 0; $skipped = 0; $broken = 0; $untouched = 0
Get-ChildItem -LiteralPath $rootB -Directory -Force | ForEach-Object {
  $p = $_.FullName
  if ($_.LinkType -ne 'Junction') { $untouched++; return }
  $tg = ($_.Target | Select-Object -First 1)
  if (-not $tg -or -not $tg.StartsWith($VIRT)) {
    if (Test-Path -LiteralPath (Join-Path $p '.')) { $untouched++ } else { Write-Host "[WARN] junction con otro target colgante: $($_.Name) -> $tg"; $broken++ }
    return
  }
  $newTarget = $REAL + $tg.Substring($VIRT.Length)
  if (-not (Test-Path -LiteralPath $newTarget)) {
    Write-Host "[SKIP] $($_.Name): target real no existe ($newTarget)" -ForegroundColor Yellow
    $skipped++; return
  }
  cmd /c rmdir "$p" | Out-Null
  if (Test-Path -LiteralPath $p) { Write-Host "[FAIL] no se pudo eliminar junction: $p" -ForegroundColor Red; $broken++; return }
  New-Item -ItemType Junction -Path $p -Target $newTarget | Out-Null
  $okRead = $false
  try { $null = Get-ChildItem -LiteralPath $p -ErrorAction Stop | Select-Object -First 1; $okRead = $true } catch {}
  if ($okRead) { Write-Host "[OK]   re-apuntada: $($_.Name)"; $fixed++ }
  else { Write-Host "[FAIL] re-apuntada pero ilegible: $($_.Name)" -ForegroundColor Red; $broken++ }
}

Write-Host "`n=== SMOKE: las 8 del rollout legibles desde host + wheel presente ==="
$skills = @('dayz-model-pipeline','dayz-3d-viewer','dayz-p3d-inspector',
            'dayz-p3d-audit','dayz-pbo-build','dayz-proxy-align','dayz-animation-pipeline')
$smokeFail = 0
foreach ($s in $skills) {
  $sk = Join-Path $rootB "$s\SKILL.md"
  $whDir = Join-Path $rootB "$s\wheels"
  $r = $false; try { $null = Get-Content -LiteralPath $sk -TotalCount 1 -ErrorAction Stop; $r = $true } catch {}
  $w = (Test-Path -LiteralPath $whDir) -and (@(Get-ChildItem -LiteralPath $whDir -Filter 'py3d-*.whl' -ErrorAction SilentlyContinue).Count -ge 1)
  if ($r -and $w) { Write-Host "[OK]   $s (SKILL.md legible, wheel presente)" }
  else { Write-Host "[FAIL] $s (legible=$r wheel=$w)" -ForegroundColor Red; $smokeFail++ }
}

Write-Host "`n========================================"
Write-Host ("junctions re-apuntadas: {0} | skip (sin target real): {1} | sin tocar: {2} | rotas: {3} | smoke fails: {4}" -f $fixed, $skipped, $untouched, $broken, $smokeFail)
if (($broken + $smokeFail) -eq 0) { Write-Host "RESULTADO: ALL PASSED"; exit 0 } else { Write-Host "RESULTADO: revisar FAILs" -ForegroundColor Red; exit 1 }
