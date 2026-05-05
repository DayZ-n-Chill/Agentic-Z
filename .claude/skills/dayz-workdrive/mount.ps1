<#
.SYNOPSIS
  Mount P:\ as the DayZ work drive without opening DayZ Tools.

.DESCRIPTION
  P:\ is a folder substituted as a drive letter. This script resolves the
  work drive folder (env var, cache, settings.ini, registry, fallback) and
  mounts it via DayZ Tools' WorkDrive.exe /Mount, falling back to Windows'
  built-in subst command. Idempotent: exits OK if already mounted.

.EXAMPLE
  .\mount.ps1
  .\mount.ps1 -Path 'C:\P Drives\Vanilla'
  .\mount.ps1 -Unmount
#>
[CmdletBinding()]
param(
  [string]$Path,
  [switch]$Unmount
)

$Here       = Split-Path -Parent $PSCommandPath
$ProjectDir = if ($env:CLAUDE_PROJECT_DIR) { $env:CLAUDE_PROJECT_DIR } else { (Get-Location).Path }
$Cache      = Join-Path $ProjectDir '.claude\local-memory\dayz-work-drive.json'

function Write-Cmd  ($t) { Write-Host "[CMD]  $t" -ForegroundColor Cyan }
function Write-Info ($t) { Write-Host "[INFO] $t" }
function Write-Ok   ($t) { Write-Host "[OK]   $t" -ForegroundColor Green }
function Write-WarnLine ($t) { Write-Host "[WARN] $t" -ForegroundColor Yellow }
function Write-Fail ($t) { Write-Host "[FAIL] $t" -ForegroundColor Red }

function Test-PMounted { Test-Path 'P:\' -PathType Container }

function Get-CachedPath {
  if (-not (Test-Path $Cache)) { return $null }
  try {
    $p = (Get-Content $Cache -Raw -Encoding UTF8 | ConvertFrom-Json).work_drive_path
    if ($p -and (Test-Path $p -PathType Container)) { return $p }
  } catch { }
  return $null
}

function Set-CachedPath ($p) {
  $dir = Split-Path -Parent $Cache
  if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
  @{ work_drive_path = $p } | ConvertTo-Json | Out-File -FilePath $Cache -Encoding utf8
}

function Find-DayZTools {
  $check = { param($r) Test-Path (Join-Path $r 'Bin\AddonBuilder\AddonBuilder.exe') }

  if ($env:DAYZ_TOOLS_PATH -and (& $check $env:DAYZ_TOOLS_PATH)) { return $env:DAYZ_TOOLS_PATH }

  $regKeys = @(
    'HKLM:\SOFTWARE\WOW6432Node\bohemia interactive\dayz tools',
    'HKLM:\SOFTWARE\bohemia interactive\dayz tools',
    'HKCU:\SOFTWARE\bohemia interactive\dayz tools'
  )
  foreach ($k in $regKeys) {
    try {
      $v = (Get-ItemProperty -Path $k -ErrorAction Stop).Path
      if ($v -and (& $check $v)) { return $v }
    } catch { }
  }

  foreach ($p in @(
    'C:\Program Files (x86)\Steam\steamapps\common\DayZ Tools',
    'C:\Program Files\Steam\steamapps\common\DayZ Tools'
  )) {
    if (& $check $p) { return $p }
  }
  return $null
}

function Read-SettingsIniPath ($toolsRoot) {
  $ini = Join-Path $toolsRoot 'settings.ini'
  if (-not (Test-Path $ini)) { return $null }
  $section = ''
  foreach ($line in Get-Content $ini) {
    $t = $line.Trim()
    if ($t -match '^\[(.+)\]$') { $section = $matches[1].Trim().ToLower(); continue }
    if ($section -eq 'projectdrive' -and $t -match '^\s*path\s*=\s*(.+)$') {
      $p = $matches[1].Trim().Trim('"').Trim("'")
      if ($p) { return $p }
    }
  }
  return $null
}

function Find-WorkDrive {
  $candidates = New-Object System.Collections.Generic.List[string]

  if ($env:DAYZ_WORK_DRIVE) { $candidates.Add($env:DAYZ_WORK_DRIVE) }

  $cached = Get-CachedPath
  if ($cached) { $candidates.Add($cached) }

  $tools = Find-DayZTools
  if ($tools) {
    $iniPath = Read-SettingsIniPath $tools
    if ($iniPath) { $candidates.Add($iniPath) }
  }

  $regKeys = @(
    'HKCU:\Software\Bohemia Interactive\DayZ Tools',
    'HKLM:\SOFTWARE\WOW6432Node\bohemia interactive\dayz tools',
    'HKLM:\SOFTWARE\bohemia interactive\dayz tools'
  )
  foreach ($k in $regKeys) {
    foreach ($name in @('WorkDrive','WorkDrivePath','P_Drive','PDrive')) {
      try {
        $val = (Get-ItemProperty -Path $k -Name $name -ErrorAction Stop).$name
        if ($val) { $candidates.Add([string]$val) }
      } catch { }
    }
  }

  if ($tools) { $candidates.Add((Join-Path $tools 'Bin\WorkDrive')) }

  foreach ($c in $candidates) {
    if ($c -and (Test-Path $c -PathType Container)) { return $c }
  }
  return $null
}

function Find-WorkDriveExe {
  $tools = Find-DayZTools
  if (-not $tools) { return $null }
  $exe = Join-Path $tools 'Bin\WorkDrive\WorkDrive.exe'
  if (Test-Path $exe) { return $exe }
  return $null
}

function Invoke-Mount ($p) {
  $exe = Find-WorkDriveExe
  if ($exe) {
    Write-Cmd "`"$exe`" /Mount `"$p`""
    & $exe /Mount $p
    if ($LASTEXITCODE -eq 0) { return $true }
    Write-WarnLine "WorkDrive.exe returned $LASTEXITCODE; falling back to subst"
  } else {
    Write-WarnLine 'WorkDrive.exe not found; falling back to subst'
  }
  Write-Cmd "subst P: `"$p`""
  & subst P: $p
  return ($LASTEXITCODE -eq 0)
}

function Invoke-Unmount {
  if (-not (Test-PMounted)) {
    Write-Info 'P:\ is not currently mounted'
    return 0
  }
  $exe = Find-WorkDriveExe
  if ($exe) {
    Write-Cmd "`"$exe`" /Dismount"
    & $exe /Dismount
    if ($LASTEXITCODE -eq 0 -and -not (Test-PMounted)) {
      Write-Ok 'P:\ unmounted'
      return 0
    }
    Write-WarnLine "WorkDrive.exe /Dismount returned $LASTEXITCODE; falling back to subst /D"
  }
  Write-Cmd 'subst P: /D'
  & subst P: /D
  if ($LASTEXITCODE -ne 0) {
    Write-Fail "subst /D returned $LASTEXITCODE"
    return 1
  }
  Write-Ok 'P:\ unmounted'
  return 0
}

Write-Host "DayZ P:\ mount`n"

if ($Unmount) { exit (Invoke-Unmount) }

if (Test-PMounted) {
  Write-Ok 'P:\ already mounted'
  exit 0
}

if ($Path) {
  if (-not (Test-Path $Path -PathType Container)) {
    Write-Fail "Path does not exist or is not a directory: $Path"
    exit 1
  }
  $work = $Path
} else {
  $work = Find-WorkDrive
  if (-not $work) {
    Write-Fail 'Could not resolve a work drive folder.'
    Write-Host '       Tried: $env:DAYZ_WORK_DRIVE, cached path, settings.ini, registry, DayZ Tools\Bin\WorkDrive\.'
    Write-Host '       Pass -Path "C:\path\to\workdrive" to specify explicitly.'
    exit 1
  }
}

Write-Info "Mounting P: -> $work"
if (-not (Invoke-Mount $work)) { exit 1 }

if (-not (Test-PMounted)) {
  Write-Fail "Mount returned 0 but P:\ still isn't visible"
  exit 1
}

Set-CachedPath $work
Write-Ok "P:\ mounted -> $work"
Write-Info "Cached for future runs at $Cache"
exit 0
