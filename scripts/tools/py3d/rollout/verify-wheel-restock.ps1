<#
.SYNOPSIS
Proves the rollout restocks the wheel its own manifest pins.

.DESCRIPTION
Builds synthetic skill roots under a temporary directory and runs the rollout against
them. Never touches an installed skill tree.

The wheel name is read from wheel-manifest.json, never derived: deriving it is the
defect this gate exists to catch.

.PARAMETER BaselineScript
A pre-fix copy of the rollout. When supplied, the negative control runs and REQUIRES
that copy to fail - a gate that cannot fail is not a gate. When omitted the negative
control is reported as skipped, not as passed.
#>
[CmdletBinding()]
param(
    [string]$ApplyScript = "",
    [string]$BaselineScript = "",
    [string]$FixtureRoot = ""
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$Py3dRoot = [IO.Path]::GetFullPath((Join-Path $Root ".."))
$FixedScript = Join-Path $Root "apply-s2-rollout.ps1"
$OrigScript = $BaselineScript
$Manifest = Get-Content -Raw (Join-Path $Root "wheel-manifest.json") | ConvertFrom-Json
$PinnedName = [string]$Manifest.filename
$PinnedSha = ([string]$Manifest.sha256).ToLowerInvariant()
$DistWheel = Join-Path (Join-Path $Py3dRoot "dist") $PinnedName
$StaleName = "py3d-1.4.0-py3-none-any.whl"
# An earlier pin under the py3d_dayz name; never a version that gets pinned.
$PreviousName = "py3d_dayz-0.0.0-py3-none-any.whl"
$PatchPath = Join-Path $Root "patches\dayz-proxy-align__SKILL.md.patch"
if ([string]::IsNullOrWhiteSpace($FixtureRoot)) {
    # Never inside the working tree: stray fixtures make the pack gate BUILD-DIRTY.
    $FixtureRoot = Join-Path $env:TEMP "py3d-rollout-verify"
}

$RunNegative = -not [string]::IsNullOrWhiteSpace($OrigScript)
if ([string]::IsNullOrWhiteSpace($ApplyScript)) {
    $ApplyScript = $FixedScript
}
$ApplyScript = [IO.Path]::GetFullPath($ApplyScript)

if (-not (Test-Path -LiteralPath $DistWheel -PathType Leaf)) {
    Write-Host ("SKIPPED: the pinned wheel is not built at " + $DistWheel)
    Write-Host "Build it with rollout\build-wheel.ps1 first. This gate did NOT run."
    exit 2
}

$script:Log = New-Object System.Collections.Generic.List[string]
function Write-Log([string]$Message) {
    Write-Host $Message
    $script:Log.Add($Message)
}

function Write-LfFile([string]$Path, [string]$Text) {
    $normalized = $Text -replace "`r`n", "`n"
    $normalized = $normalized -replace "`r", "`n"
    $utf8 = New-Object System.Text.UTF8Encoding $false
    [IO.File]::WriteAllText($Path, $normalized, $utf8)
}

function Get-FileSha256Lower([string]$Path) {
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

function Ensure-SourceVersionMarkers {
    # The rollout reads the version markers from its own parent, so they are the
    # repository's real ones. Nothing is written here: fabricating them would put
    # untracked files inside the working tree and, worse, would let this gate pass
    # against a source version the manifest was never pinned to.
    $core = Join-Path $Py3dRoot "py3d\__init__.py"
    $setup = Join-Path $Py3dRoot "setup.py"
    foreach ($marker in @($core, $setup)) {
        if (-not (Test-Path -LiteralPath $marker -PathType Leaf)) {
            Write-Host ("SKIPPED: missing py3d version marker " + $marker)
            exit 2
        }
    }
    $declared = [string]$Manifest.source_version
    $coreText = [IO.File]::ReadAllText($core)
    if ($coreText -notmatch ('(?m)^__version__\s*=\s*"' + [regex]::Escape($declared) + '"\s*$')) {
        Write-Host ("SKIPPED: py3d source is not at the pinned version " + $declared)
        Write-Host "This gate did NOT run; rebuild or re-pin before trusting it."
        exit 2
    }
}

function New-BeforeSkillMd([string]$Path) {
    $lines = New-Object System.Collections.Generic.List[string]
    $i = 1
    while ($i -le 44) {
        $lines.Add("PAD LINE $i") | Out-Null
        $i++
    }
    $hunk1 = @(
        '## Dependencies',
        '',
        '```bash',
        '# py3d DayZ fork >= 1.2.0 (wheel vendorizada en esta skill - D2=B).',
        '# NUNCA `pip install py3d` (PyPI = point-cloud lib) NI git+upstream (sin guards).',
        'pip install --break-system-packages "$SKILL_DIR"/wheels/py3d-*-py3-none-any.whl 2>/dev/null \',
        '  || pip install --break-system-packages $(ls /sessions/*/mnt/*/_tools/py3d/dist/py3d-*-py3-none-any.whl 2>/dev/null | sort -V | tail -1)',
        'python3 -c "import py3d; assert getattr(py3d,''IS_DAYZ_FORK'',False) and tuple(map(int,py3d.__version__.split(''.'')))>=(1,2,0), (py3d.__version__, py3d.__file__)"',
        'pip install numpy --break-system-packages',
        '```',
        ''
    )
    foreach ($line in $hunk1) { $lines.Add($line) | Out-Null }
    $lines.Add("BETWEEN 56") | Out-Null
    $lines.Add("BETWEEN 57") | Out-Null
    $hunk2 = @(
        'or set `DAYZ_ODOL_BACKEND_ROOT`. The host model itself must be **MLOD** (binarized hosts:',
        'run external-odol-backend first).',
        '',
        '## Scripts',
        '',
        '| Script | Purpose |'
    )
    foreach ($line in $hunk2) { $lines.Add($line) | Out-Null }
    Write-LfFile $Path (($lines.ToArray() -join "`n") + "`n")
}

function Convert-SkillMdToAlreadyApplied([string]$Path) {
    $text = [IO.File]::ReadAllText($Path)
    $text = $text.Replace(
        "py3d DayZ fork >= 1.2.0",
        "py3d DayZ fork >= 1.4.0"
    )
    $text = $text.Replace(">=(1,2,0)", ">=(1,4,0)")
    $insert = @(
        '## py3d 1.4.0 lifecycle (batch / non-visual)',
        '',
        'For deterministic automation, the vendored fork now owns the complete',
        'add/inspect/align/remove lifecycle:',
        '',
        '```python',
        'import py3d',
        '',
        'with open("host.p3d", "rb") as handle:',
        '    model = py3d.P3D(handle)',
        'lod = model.lods[0]',
        '',
        'name = lod.add_proxy(',
        '    r"\dz\characters\proxies\vests", 1,',
        '    origin=(0.0, 1.1, 0.0),',
        '    rotation=((1, 0, 0), (0, 1, 0), (0, 0, 1)),',
        '    space="engine",',
        ')',
        'descriptor = {',
        '    item["name"]: item for item in lod.get_proxies(strict=True)',
        '}[name]',
        'lod.align_proxy(',
        '    name,',
        '    origin=(0.0, 1.15, 0.02),',
        '    rotation=descriptor["engine_frame"],',
        '    space="engine",',
        ')',
        '# lod.remove_proxy(name)',
        'model.save("host_aligned.p3d")',
        '```',
        '',
        'The legacy default remains `space="raw"`. In 1.4.0 the explicit conversion is',
        '`engine_frame = P'' × raw_frame`, with',
        '`P'' = ((-1,0,0),(0,0,1),(0,1,0))`; the same involutive matrix converts back.',
        'Use `space="engine"` when the matrix describes the pose expected in DayZ.',
        '',
        'All mutators are fail-closed: path, index, anchor, rotation, scale, canonical',
        'proxy anatomy and exclusive ownership are validated before mutation.',
        '`get_proxies(strict=True)` rejects malformed proxy selections. `align_proxy`',
        'preserves point/face/selection identities; `remove_proxy` deletes exactly its',
        'selection, face and three points, remaps surviving point indices and sharp',
        'edges, and intentionally leaves the normal pool unchanged.',
        ''
    ) -join "`n"
    $needle = "run external-odol-backend first).`n`n## Scripts"
    if ($text.IndexOf($needle) -lt 0) {
        throw "cannot locate insertion point for already-applied SKILL.md"
    }
    $text = $text.Replace(
        $needle,
        ("run external-odol-backend first).`n`n" + $insert + "`n## Scripts")
    )
    Write-LfFile $Path $text
}

function Assert-FixtureAlreadyApplied([string]$TargetRoot) {
    Push-Location -LiteralPath $TargetRoot
    try {
        $previous = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        $out = & git -c core.autocrlf=false -c core.eol=lf apply --reverse --check -- $PatchPath 2>&1
        $code = $LASTEXITCODE
        $ErrorActionPreference = $previous
        if ($code -ne 0) {
            throw "fixture reverse-check failed (exit $code): $out"
        }
    } finally {
        Pop-Location
    }
}

function Initialize-TargetRoot {
    param(
        [string]$TargetRoot,
        [string]$Scenario
    )
    if (Test-Path -LiteralPath $TargetRoot) {
        Remove-Item -LiteralPath $TargetRoot -Recurse -Force
    }
    $skillDir = Join-Path $TargetRoot "dayz-proxy-align"
    $wheelsDir = Join-Path $skillDir "wheels"
    New-Item -ItemType Directory -Force -Path $skillDir | Out-Null
    $skillMd = Join-Path $skillDir "SKILL.md"
    New-BeforeSkillMd $skillMd

    Push-Location -LiteralPath $TargetRoot
    try {
        $previous = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        $gitOut = & git -c core.autocrlf=false -c core.eol=lf apply -- $PatchPath 2>&1
        $gitCode = $LASTEXITCODE
        $ErrorActionPreference = $previous
    } finally {
        Pop-Location
    }
    if ($gitCode -ne 0) {
        Convert-SkillMdToAlreadyApplied $skillMd
    }
    $reverseOk = $false
    try {
        Assert-FixtureAlreadyApplied $TargetRoot
        $reverseOk = $true
    } catch {
        $reverseOk = $false
    }
    if (-not $reverseOk) {
        New-BeforeSkillMd $skillMd
        Convert-SkillMdToAlreadyApplied $skillMd
        Assert-FixtureAlreadyApplied $TargetRoot
    }

    New-Item -ItemType Directory -Force -Path $wheelsDir | Out-Null
    if ($Scenario -eq "pinned") {
        Copy-Item -LiteralPath $DistWheel -Destination (Join-Path $wheelsDir $PinnedName)
    } elseif ($Scenario -eq "stale") {
        Write-LfFile (Join-Path $wheelsDir $StaleName) "stale-legacy-py3d-1.4.0-wheel`n"
    } elseif ($Scenario -eq "previous") {
        Copy-Item -LiteralPath $DistWheel -Destination (Join-Path $wheelsDir $PinnedName)
        Write-LfFile (Join-Path $wheelsDir $PreviousName) "earlier-py3d_dayz-pin`n"
    }
}

function Invoke-ApplyRollout {
    param(
        [string]$Script,
        [string]$Target,
        [string]$Backup
    )
    if (Test-Path -LiteralPath $Backup) {
        Remove-Item -LiteralPath $Backup -Recurse -Force
    }
    New-Item -ItemType Directory -Force -Path $Backup | Out-Null
    # powershell.exe -File refuses any extension other than .ps1, so the pristine
    # baseline - deliberately kept as .ps1.orig so it cannot be run by accident -
    # has to be materialised under a runnable name first. Without this the
    # negative control fails on the extension and proves nothing.
    # The copy must sit BESIDE the original: the rollout resolves its manifest
    # and patches relative to its own location, so a copy parked anywhere else
    # dies with "tracked wheel manifest is missing" instead of exercising it.
    $ScriptToRun = $Script
    $Materialised = $false
    if ([IO.Path]::GetExtension($Script) -ne ".ps1") {
        $ScriptToRun = Join-Path ([IO.Path]::GetDirectoryName($Script)) "_under-test.ps1"
        Copy-Item -LiteralPath $Script -Destination $ScriptToRun -Force
        $Materialised = $true
    }
    $argList = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", $ScriptToRun,
        "-TargetSkillRoot", $Target,
        "-BackupRoot", $Backup
    )
    # PS 5.1 wraps a native command's stderr in an ErrorRecord, so under the
    # script-wide "Stop" preference the child's own failure becomes a terminating
    # error here and never reaches the caller. The negative control NEEDS that
    # failure as data, so stderr is demoted for the duration of the call only.
    $previous = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        $output = & powershell.exe @argList 2>&1 | Out-String
        $exit = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previous
        if ($Materialised) {
            Remove-Item -LiteralPath $ScriptToRun -Force -ErrorAction SilentlyContinue
        }
    }
    return [pscustomobject]@{
        ExitCode = $exit
        Output = $output
    }
}

function Assert-PinnedWheel([string]$TargetRoot) {
    $wheelPath = Join-Path $TargetRoot "dayz-proxy-align\wheels\$PinnedName"
    if (-not (Test-Path -LiteralPath $wheelPath -PathType Leaf)) {
        throw "pinned wheel missing: $wheelPath"
    }
    $hash = Get-FileSha256Lower $wheelPath
    if ($hash -ne $PinnedSha) {
        throw "pinned wheel hash mismatch: $hash"
    }
}

function Assert-NoPinnedWheel([string]$TargetRoot) {
    $wheelPath = Join-Path $TargetRoot "dayz-proxy-align\wheels\$PinnedName"
    if (Test-Path -LiteralPath $wheelPath -PathType Leaf) {
        throw "original script restocked the pinned wheel; negative control is invalid"
    }
}

function Assert-NoStaleWheel([string]$TargetRoot) {
    $stalePath = Join-Path $TargetRoot "dayz-proxy-align\wheels\$StaleName"
    if (Test-Path -LiteralPath $stalePath -PathType Leaf) {
        throw "stale wheel was not removed: $stalePath"
    }
}

function Assert-OnlyPinnedWheel([string]$TargetRoot) {
    $wheelsDir = Join-Path $TargetRoot "dayz-proxy-align\wheels"
    $names = @(Get-ChildItem -LiteralPath $wheelsDir -File | ForEach-Object { $_.Name })
    if ($names.Count -ne 1 -or $names[0] -ne $PinnedName) {
        throw ("wheels directory is not the pinned wheel alone: " + ($names -join ", "))
    }
}

if (-not (Test-Path -LiteralPath $DistWheel -PathType Leaf)) {
    throw "missing dist wheel: $DistWheel"
}
$distHash = Get-FileSha256Lower $DistWheel
if ($distHash -ne $PinnedSha) {
    throw "dist wheel hash mismatch: $distHash"
}
if ($RunNegative) {
    if (-not (Test-Path -LiteralPath $OrigScript -PathType Leaf)) {
        throw "missing baseline copy: $OrigScript"
    }
    $origText = [IO.File]::ReadAllText($OrigScript)
    if ($origText -notmatch '\$ExpectedWheelName = "py3d-\$SourceVersion-py3-none-any\.whl"') {
        throw "orig copy is not the unfixed script"
    }
}
Get-Command git -ErrorAction Stop | Out-Null

Ensure-SourceVersionMarkers
New-Item -ItemType Directory -Force -Path $FixtureRoot | Out-Null

$failed = $false

Write-Log "======== TEST A: empty wheels -> restock pinned ========"
Write-Log ("ApplyScript=" + $ApplyScript)
try {
    $targetA = Join-Path $FixtureRoot "target-a"
    $backupA = Join-Path $FixtureRoot "backup-a"
    Initialize-TargetRoot -TargetRoot $targetA -Scenario "empty"
    $resultA = Invoke-ApplyRollout -Script $ApplyScript -Target $targetA -Backup $backupA
    Write-Log $resultA.Output
    Write-Log ("EXIT=" + $resultA.ExitCode)
    if ($resultA.ExitCode -ne 0) {
        throw "rollout exit $($resultA.ExitCode)"
    }
    Assert-PinnedWheel $targetA
    if ($resultA.Output -notmatch "wheel replaced: dayz-proxy-align") {
        throw "missing wheel-replaced marker"
    }
    Write-Log "TEST A: PASS"
} catch {
    Write-Log ("TEST A: FAIL " + $_)
    $failed = $true
}

Write-Log "======== TEST B: pinned already present -> idempotent ========"
Write-Log ("ApplyScript=" + $ApplyScript)
try {
    $targetB = Join-Path $FixtureRoot "target-b"
    $backupB = Join-Path $FixtureRoot "backup-b"
    Initialize-TargetRoot -TargetRoot $targetB -Scenario "pinned"
    $resultB = Invoke-ApplyRollout -Script $ApplyScript -Target $targetB -Backup $backupB
    Write-Log $resultB.Output
    Write-Log ("EXIT=" + $resultB.ExitCode)
    if ($resultB.ExitCode -ne 0) {
        throw "rollout exit $($resultB.ExitCode)"
    }
    Assert-PinnedWheel $targetB
    if ($resultB.Output -notmatch "wheel already exact: dayz-proxy-align") {
        throw "missing already-exact marker"
    }
    if ($resultB.Output -notmatch "applied changes: 0") {
        throw "run was not idempotent"
    }
    Write-Log "TEST B: PASS"
} catch {
    Write-Log ("TEST B: FAIL " + $_)
    $failed = $true
}

Write-Log "======== TEST C: stale py3d-1.4.0 wheel -> removed and replaced ========"
Write-Log ("ApplyScript=" + $ApplyScript)
try {
    $targetC = Join-Path $FixtureRoot "target-c"
    $backupC = Join-Path $FixtureRoot "backup-c"
    Initialize-TargetRoot -TargetRoot $targetC -Scenario "stale"
    $resultC = Invoke-ApplyRollout -Script $ApplyScript -Target $targetC -Backup $backupC
    Write-Log $resultC.Output
    Write-Log ("EXIT=" + $resultC.ExitCode)
    if ($resultC.ExitCode -ne 0) {
        throw "rollout exit $($resultC.ExitCode)"
    }
    Assert-NoStaleWheel $targetC
    Assert-PinnedWheel $targetC
    if ($resultC.Output -notmatch "wheel replaced: dayz-proxy-align") {
        throw "missing wheel-replaced marker"
    }
    Write-Log "TEST C: PASS"
} catch {
    Write-Log ("TEST C: FAIL " + $_)
    $failed = $true
}

Write-Log "======== TEST E: earlier py3d_dayz pin beside the pinned wheel -> removed ========"
Write-Log ("ApplyScript=" + $ApplyScript)
try {
    $targetE = Join-Path $FixtureRoot "target-e"
    $backupE = Join-Path $FixtureRoot "backup-e"
    Initialize-TargetRoot -TargetRoot $targetE -Scenario "previous"
    $resultE = Invoke-ApplyRollout -Script $ApplyScript -Target $targetE -Backup $backupE
    Write-Log $resultE.Output
    Write-Log ("EXIT=" + $resultE.ExitCode)
    if ($resultE.ExitCode -ne 0) {
        throw "rollout exit $($resultE.ExitCode)"
    }
    Assert-PinnedWheel $targetE
    Assert-OnlyPinnedWheel $targetE
    $backups = @(Get-ChildItem -LiteralPath $backupE -Recurse -File -Filter $PreviousName)
    if ($backups.Count -ne 1) {
        throw "earlier py3d_dayz wheel has no single backup: $($backups.Count)"
    }
    Write-Log "TEST E: PASS"
} catch {
    Write-Log ("TEST E: FAIL " + $_)
    $failed = $true
}

if (-not $RunNegative) {
    Write-Log "TEST D: SKIPPED (no -BaselineScript given; the negative control did not run)"
}
if ($RunNegative) {
    Write-Log "======== TEST D: NEGATIVE CONTROL against apply-s2-rollout.ps1.orig ========"
    Write-Log ("ApplyScript=" + $OrigScript)
    try {
        $targetD = Join-Path $FixtureRoot "target-d"
        $backupD = Join-Path $FixtureRoot "backup-d"
        Initialize-TargetRoot -TargetRoot $targetD -Scenario "empty"
        $resultD = Invoke-ApplyRollout -Script $OrigScript -Target $targetD -Backup $backupD
        Write-Log $resultD.Output
        Write-Log ("EXIT=" + $resultD.ExitCode)
        if ($resultD.ExitCode -eq 0) {
            throw "original script unexpectedly succeeded"
        }
        if ($resultD.Output -notmatch "tracked wheel filename does not match source version") {
            throw "original script failed for an unexpected reason"
        }
        Assert-NoPinnedWheel $targetD
        Write-Log "TEST D: PASS (original failed as required)"
    } catch {
        Write-Log ("TEST D: FAIL " + $_)
        $failed = $true
    }
}

$transcript = Join-Path $FixtureRoot "_verify_last_run.txt"
$utf8 = New-Object System.Text.UTF8Encoding $false
[IO.File]::WriteAllText($transcript, (($script:Log.ToArray() -join "`n") + "`n"), $utf8)

if ($failed) {
    throw "VERIFY failed; see _verify_last_run.txt"
}
Write-Log "ALL GATES PASSED"
[IO.File]::WriteAllText($transcript, (($script:Log.ToArray() -join "`n") + "`n"), $utf8)
