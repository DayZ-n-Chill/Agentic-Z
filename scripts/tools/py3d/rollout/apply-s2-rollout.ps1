[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$TargetSkillRoot,

    [Parameter(Mandatory = $true)]
    [string]$BackupRoot,

    [switch]$NoWrite,

    # Restock the vendored wheel without reading the patch payload. Wheel
    # correctness depends only on wheel-manifest.json and tools/py3d/dist;
    # binding it to a prose preimage made every skill edit abort the restock.
    [switch]$WheelOnly
)

$ErrorActionPreference = "Stop"
$RolloutRoot = [IO.Path]::GetFullPath($PSScriptRoot)
$Py3dRoot = [IO.Path]::GetFullPath((Join-Path $RolloutRoot ".."))
$PreimageManifestPath = Join-Path $RolloutRoot "preimage-manifest.json"
$WheelManifestPath = Join-Path $RolloutRoot "wheel-manifest.json"
$WheelRoot = Join-Path $Py3dRoot "dist"
$TargetRoot = (Resolve-Path -LiteralPath $TargetSkillRoot).Path
$BackupBase = [IO.Path]::GetFullPath($BackupRoot)

# Candidate set. A skill is restocked only where it ALREADY vendors a wheels/
# directory: this script restocks, it never decides that a skill starts
# vendoring. Three candidates install py3d editable instead.
$WheelSkillNames = @(
    "dayz-model-pipeline",
    "dayz-3d-viewer",
    "dayz-p3d-inspector",
    "dayz-p3d-audit",
    "dayz-pbo-build",
    "dayz-proxy-align",
    "dayz-animation-pipeline"
)

function Get-FileSha256([string]$Path) {
    return (
        Get-FileHash -Algorithm SHA256 -LiteralPath $Path
    ).Hash.ToLowerInvariant()
}

function Get-RootPrefix([string]$Path) {
    $Full = [IO.Path]::GetFullPath($Path)
    $Trimmed = $Full.TrimEnd(
        [IO.Path]::DirectorySeparatorChar,
        [IO.Path]::AltDirectorySeparatorChar
    )
    return $Trimmed + [IO.Path]::DirectorySeparatorChar
}

function Test-IsAtOrUnderRoot([string]$Path, [string]$Root) {
    $Candidate = [IO.Path]::GetFullPath($Path)
    $RootFull = [IO.Path]::GetFullPath($Root)
    if ($Candidate.Equals(
        $RootFull,
        [StringComparison]::OrdinalIgnoreCase
    )) {
        return $true
    }
    return $Candidate.StartsWith(
        (Get-RootPrefix $RootFull),
        [StringComparison]::OrdinalIgnoreCase
    )
}

function Assert-UnderRoot(
    [string]$Path,
    [string]$Root,
    [string]$Label
) {
    $Candidate = [IO.Path]::GetFullPath($Path)
    $RootFull = [IO.Path]::GetFullPath($Root)
    if (
        -not (Test-IsAtOrUnderRoot $Candidate $RootFull) -or
        $Candidate.Equals($RootFull, [StringComparison]::OrdinalIgnoreCase)
    ) {
        throw "$Label resolves outside its explicit root: $Candidate"
    }
}

function Assert-SafeRelativePath([string]$Relative, [string]$Label) {
    if (
        [string]::IsNullOrWhiteSpace($Relative) -or
        [IO.Path]::IsPathRooted($Relative)
    ) {
        throw "$Label must be a non-empty relative path"
    }
    $Normalized = $Relative.Replace("\", "/")
    $Segments = @($Normalized.Split("/"))
    foreach ($Segment in $Segments) {
        if (
            [string]::IsNullOrWhiteSpace($Segment) -or
            $Segment -eq "." -or
            $Segment -eq ".." -or
            $Segment.Contains(":")
        ) {
            throw "$Label contains an unsafe path segment: $Relative"
        }
    }
    return $Normalized
}

function Assert-ExactFields(
    [object]$Object,
    [string[]]$Expected,
    [string]$Label
) {
    $Actual = @($Object.PSObject.Properties.Name | Sort-Object)
    $ExpectedSorted = @($Expected | Sort-Object)
    if (@(Compare-Object $ExpectedSorted $Actual).Count -ne 0) {
        throw "$Label fields are invalid"
    }
}

function Get-SourceVersion {
    $Core = [IO.File]::ReadAllText(
        (Join-Path $Py3dRoot "py3d\__init__.py")
    )
    $Setup = [IO.File]::ReadAllText((Join-Path $Py3dRoot "setup.py"))
    $CoreMatch = [regex]::Match(
        $Core, '(?m)^__version__\s*=\s*"(?<version>\d+\.\d+\.\d+)"\s*$'
    )
    $SetupMatch = [regex]::Match(
        $Setup, '(?m)^\s*version\s*=\s*"(?<version>\d+\.\d+\.\d+)",\s*$'
    )
    if (-not $CoreMatch.Success -or -not $SetupMatch.Success) {
        throw "could not resolve both py3d version markers"
    }
    $CoreVersion = $CoreMatch.Groups["version"].Value
    $SetupVersion = $SetupMatch.Groups["version"].Value
    if ($CoreVersion -ne $SetupVersion) {
        throw "py3d version markers disagree: $CoreVersion vs $SetupVersion"
    }
    return $CoreVersion
}

function Get-SkillWheelFiles(
    [string]$WheelsDirectory,
    [string]$PinnedFileName
) {
    if (-not (Test-Path -LiteralPath $WheelsDirectory -PathType Container)) {
        return @()
    }
    # Both distribution names count: py3d-* up to 1.4.0 and py3d_dayz-* since
    # the rename. A py3d_dayz wheel of an earlier pin left out here would stay
    # next to the new one, and the skills' installer, which wants exactly one
    # py3d_dayz-*-py3-none-any.whl, would refuse the directory.
    return @(
        Get-ChildItem -LiteralPath $WheelsDirectory -File |
            Where-Object {
                $_.Name -eq $PinnedFileName -or
                $_.Name -like "py3d-*.whl" -or
                $_.Name -like "py3d_dayz-*.whl"
            }
    )
}

function Invoke-GitApply([string[]]$Arguments) {
    $PreviousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        # Preimage hashes contract LF-only bytes, independent of host Git config.
        $Output = @(& git -c core.autocrlf=false -c core.eol=lf @Arguments 2>&1)
        $ExitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $PreviousPreference
    }
    return [pscustomobject]@{
        ExitCode = $ExitCode
        Output = $Output
    }
}

if (-not (Test-Path -LiteralPath $TargetRoot -PathType Container)) {
    throw "target skill root is not a directory"
}
if (Test-IsAtOrUnderRoot $BackupBase $TargetRoot) {
    throw "BackupRoot must be outside TargetSkillRoot"
}
if (
    (Test-Path -LiteralPath $BackupBase) -and
    -not (Test-Path -LiteralPath $BackupBase -PathType Container)
) {
    throw "BackupRoot exists but is not a directory"
}
if (-not (Test-Path -LiteralPath $WheelManifestPath -PathType Leaf)) {
    throw "tracked wheel manifest is missing"
}
if (
    -not $WheelOnly -and
    -not (Test-Path -LiteralPath $PreimageManifestPath -PathType Leaf)
) {
    throw "tracked preimage manifest is missing"
}

$ManifestPath = $WheelManifestPath
try {
    $Manifest = Get-Content -LiteralPath $ManifestPath -Raw -Encoding UTF8 |
        ConvertFrom-Json
} catch {
    throw "tracked wheel manifest is not valid JSON"
}
$ExpectedFields = @(
    "build_requires",
    "filename",
    "python_version",
    "schema_version",
    "sha256",
    "source_date_epoch",
    "source_version"
)
$ActualFields = @($Manifest.PSObject.Properties.Name | Sort-Object)
if (Compare-Object $ExpectedFields $ActualFields) {
    throw "tracked wheel manifest fields are invalid"
}
if ($Manifest.schema_version -ne "py3d-wheel-manifest-v2") {
    throw "tracked wheel manifest schema is unsupported"
}
if ($Manifest.source_date_epoch -ne 1784937600) {
    throw "tracked wheel manifest uses the wrong SOURCE_DATE_EPOCH"
}
if ($Manifest.sha256 -notmatch "^[0-9a-f]{64}$") {
    throw "tracked wheel manifest SHA-256 is invalid"
}
if ($Manifest.python_version -notmatch '^\d+\.\d+\.\d+$') {
    throw "tracked wheel manifest Python version is invalid"
}
$BuildRequires = @($Manifest.build_requires)
$InvalidBuildRequires = @(
    $BuildRequires | Where-Object {
        $_ -isnot [string] -or [string]::IsNullOrWhiteSpace($_)
    }
)
if ($BuildRequires.Count -eq 0 -or $InvalidBuildRequires.Count -gt 0) {
    throw "tracked wheel manifest build requirements are invalid"
}
$WheelManifest = $Manifest

$SourceVersion = Get-SourceVersion
if ($WheelManifest.source_version -ne $SourceVersion) {
    throw "tracked wheel manifest version does not match source"
}
# Manifest filename is the only source of the wheel name. Deriving
# "py3d-<ver>-py3-none-any.whl" misses the pinned py3d_dayz rename.
$ExpectedWheelName = [string]$WheelManifest.filename
if (
    [string]::IsNullOrWhiteSpace($ExpectedWheelName) -or
    $ExpectedWheelName -notlike ("*-" + $SourceVersion + "-*.whl")
) {
    throw "tracked wheel filename does not match source version"
}
$WheelPath = Join-Path $WheelRoot $WheelManifest.filename

$ManifestEntries = New-Object System.Collections.Generic.List[object]
if ($WheelOnly) {
    Write-Host "[INFO] wheel-only run: the patch preimage is not read"
} else {
    try {
        $PreimageManifest = Get-Content -LiteralPath $PreimageManifestPath -Raw -Encoding UTF8 |
            ConvertFrom-Json
    } catch {
        throw "tracked preimage manifest is not valid JSON"
    }

    $ExpectedPreimageFields = @("entries", "schema_version", "snapshot_id")
    Assert-ExactFields (
        $PreimageManifest
    ) $ExpectedPreimageFields "tracked preimage manifest"
    if ($PreimageManifest.schema_version -ne "py3d-rollout-preimage-v1") {
        throw "tracked preimage manifest schema is unsupported"
    }
    if ([string]::IsNullOrWhiteSpace($PreimageManifest.snapshot_id)) {
        throw "tracked preimage manifest snapshot id is invalid"
    }
    $RawEntries = @($PreimageManifest.entries)
    if ($RawEntries.Count -eq 0) {
        throw "tracked preimage manifest has no entries"
    }

    $SeenRelatives = @{}
    foreach ($RawEntry in $RawEntries) {
        $Status = $RawEntry.status
        if ($Status -eq "patched") {
            $ExpectedEntryFields = @(
                "patch_path",
                "preimage_sha256",
                "relative_path",
                "status"
            )
        } elseif ($Status -eq "not_applicable") {
            $ExpectedEntryFields = @(
                "preimage_sha256",
                "reason",
                "relative_path",
                "status"
            )
        } else {
            throw "tracked preimage manifest entry status is invalid"
        }
        Assert-ExactFields $RawEntry $ExpectedEntryFields (
            "tracked preimage manifest entry"
        )

        $Relative = Assert-SafeRelativePath (
            $RawEntry.relative_path
        ) "preimage relative_path"
        $RelativeKey = $Relative.ToLowerInvariant()
        if ($SeenRelatives.ContainsKey($RelativeKey)) {
            throw "tracked preimage manifest has duplicate path: $Relative"
        }
        $SeenRelatives[$RelativeKey] = $true
        if (
            $RawEntry.preimage_sha256 -isnot [string] -or
            $RawEntry.preimage_sha256 -notmatch "^[0-9a-f]{64}$"
        ) {
            throw "tracked preimage SHA-256 is invalid: $Relative"
        }
        $SkillName = ($Relative -split "/", 2)[0]
        $Destination = Join-Path $TargetRoot $Relative
        Assert-UnderRoot $Destination $TargetRoot "patch destination"

        $PatchPath = $null
        $Reason = $null
        if ($Status -eq "patched") {
            $PatchRelative = Assert-SafeRelativePath (
                $RawEntry.patch_path
            ) "preimage patch_path"
            $PatchPath = Join-Path $RolloutRoot $PatchRelative
            Assert-UnderRoot $PatchPath $RolloutRoot "rollout patch"
            if (-not (Test-Path -LiteralPath $PatchPath -PathType Leaf)) {
                throw "rollout patch is missing: $PatchRelative"
            }
            $PatchHeader = @(Get-Content -LiteralPath $PatchPath -TotalCount 2)
            if (
                $PatchHeader.Count -ne 2 -or
                $PatchHeader[0] -ne "--- a/$Relative" -or
                $PatchHeader[1] -ne "+++ b/$Relative"
            ) {
                throw "rollout patch headers do not match target: $PatchRelative"
            }
        } else {
            $Reason = $RawEntry.reason
            if ([string]::IsNullOrWhiteSpace($Reason)) {
                throw "not_applicable entry requires a reason: $Relative"
            }
        }
        $ManifestEntries.Add([pscustomobject]@{
            Relative = $Relative
            SkillName = $SkillName
            Status = $Status
            PreimageSha256 = $RawEntry.preimage_sha256
            PatchPath = $PatchPath
            Reason = $Reason
            Destination = $Destination
        })
    }
}

Get-Command git -ErrorAction Stop | Out-Null
$PatchPlans = New-Object System.Collections.Generic.List[object]
$WheelPlans = New-Object System.Collections.Generic.List[object]
$PreflightFailures = 0
$PresentEntryCount = 0

Push-Location -LiteralPath $TargetRoot
try {
    foreach ($Entry in $ManifestEntries) {
        $SkillDirectory = Join-Path $TargetRoot $Entry.SkillName
        if (-not (Test-Path -LiteralPath $SkillDirectory -PathType Container)) {
            Write-Host "[SKIP] absent skill: $($Entry.SkillName)"
            continue
        }
        $PresentEntryCount++
        if (-not (Test-Path -LiteralPath $Entry.Destination -PathType Leaf)) {
            Write-Host "[FAIL] patch target missing: $($Entry.Relative)"
            $PreflightFailures++
            continue
        }

        if ($Entry.Status -eq "not_applicable") {
            $Observed = Get-FileSha256 $Entry.Destination
            if ($Observed -ne $Entry.PreimageSha256) {
                Write-Host (
                    "[FAIL] preimage mismatch: $($Entry.Relative) " +
                    "expected=$($Entry.PreimageSha256) observed=$Observed"
                )
                $PreflightFailures++
            } else {
                Write-Host (
                    "[OK] not applicable: $($Entry.Relative) - " +
                    $Entry.Reason
                )
            }
            continue
        }

        $ReverseCheck = Invoke-GitApply -Arguments @(
            "apply", "--reverse", "--check", $Entry.PatchPath
        )
        if ($ReverseCheck.ExitCode -eq 0) {
            Write-Host "[OK] already applied: $($Entry.Relative)"
            continue
        }

        $Observed = Get-FileSha256 $Entry.Destination
        if ($Observed -ne $Entry.PreimageSha256) {
            Write-Host (
                "[FAIL] preimage mismatch: $($Entry.Relative) " +
                "expected=$($Entry.PreimageSha256) observed=$Observed"
            )
            $PreflightFailures++
            continue
        }

        $ForwardCheck = Invoke-GitApply -Arguments @(
            "apply", "--check", $Entry.PatchPath
        )
        if ($ForwardCheck.ExitCode -ne 0) {
            $ForwardCheck.Output | ForEach-Object { Write-Host $_ }
            Write-Host "[FAIL] patch does not apply: $($Entry.Relative)"
            $PreflightFailures++
            continue
        }

        $PatchPlans.Add([pscustomobject]@{
            Entry = $Entry
            Destination = $Entry.Destination
            PatchPath = $Entry.PatchPath
        })
        if ($NoWrite) {
            Write-Host "[PLAN] patch: $($Entry.Relative)"
        }
    }
} finally {
    Pop-Location
}

$PresentWheelSkills = @(
    $WheelSkillNames | Where-Object {
        Test-Path -LiteralPath (Join-Path $TargetRoot $_) -PathType Container
    }
)
if ($PresentEntryCount -eq 0 -and $PresentWheelSkills.Count -eq 0) {
    throw "target root contains none of the py3d rollout skills"
}
foreach ($SkillName in $PresentWheelSkills) {
    $WheelsDirectory = Join-Path (Join-Path $TargetRoot $SkillName) "wheels"
    Assert-UnderRoot $WheelsDirectory $TargetRoot "wheel directory"
    if (-not (Test-Path -LiteralPath $WheelsDirectory -PathType Container)) {
        Write-Host "[SKIP] not vendored: $SkillName"
        continue
    }
    $Existing = @(
        Get-SkillWheelFiles $WheelsDirectory $WheelManifest.filename
    )

    $Pinned = @($Existing | Where-Object { $_.Name -eq $WheelManifest.filename })
    $PinnedExact = $false
    if ($Pinned.Count -gt 0) {
        $Observed = Get-FileSha256 $Pinned[0].FullName
        if ($Observed -ne $WheelManifest.sha256) {
            Write-Host (
                "[FAIL] wheel hash mismatch: $SkillName " +
                "expected=$($WheelManifest.sha256) observed=$Observed"
            )
            $PreflightFailures++
            continue
        }
        $PinnedExact = $true
    }

    $Stale = @($Existing | Where-Object { $_.Name -ne $WheelManifest.filename })
    if ($PinnedExact -and $Stale.Count -eq 0) {
        Write-Host "[OK] wheel already exact: $SkillName"
        continue
    }

    $ExistingStates = New-Object System.Collections.Generic.List[object]
    foreach ($Wheel in $Existing) {
        Assert-UnderRoot $Wheel.FullName $TargetRoot "existing wheel"
        $ExistingStates.Add([pscustomobject]@{
            Name = $Wheel.Name
            FullName = $Wheel.FullName
            Sha256 = Get-FileSha256 $Wheel.FullName
        })
    }
    $StaleStates = @(
        $ExistingStates | Where-Object { $_.Name -ne $WheelManifest.filename }
    )
    $WheelPlans.Add([pscustomobject]@{
        SkillName = $SkillName
        WheelsDirectory = $WheelsDirectory
        Destination = Join-Path $WheelsDirectory $WheelManifest.filename
        PinnedExact = $PinnedExact
        Existing = $ExistingStates.ToArray()
        Stale = $StaleStates
    })
    if ($NoWrite) {
        Write-Host "[PLAN] wheel: $SkillName"
    }
}

if ($WheelPlans.Count -gt 0) {
    if (-not (Test-Path -LiteralPath $WheelPath -PathType Leaf)) {
        Write-Host (
            "[FAIL] tracked wheel is missing from tools/py3d/dist: " +
            $WheelManifest.filename
        )
        $PreflightFailures++
    } else {
        $SourceWheelHash = Get-FileSha256 $WheelPath
        if ($SourceWheelHash -ne $WheelManifest.sha256) {
            Write-Host (
                "[FAIL] tracked wheel hash mismatch: " +
                "expected=$($WheelManifest.sha256) observed=$SourceWheelHash"
            )
            $PreflightFailures++
        }
    }
}

if ($PreflightFailures -gt 0) {
    throw (
        "rollout preflight failed for $PreflightFailures item(s); " +
        "no target files were written"
    )
}

$Changes = $PatchPlans.Count + $WheelPlans.Count
if ($NoWrite) {
    Write-Host "NO-WRITE verification complete; planned changes: $Changes"
    return
}
if ($Changes -eq 0) {
    Write-Host "Rollout complete; applied changes: 0"
    return
}

$Stamp = Get-Date -Format "yyyyMMdd-HHmmssfff"
$BackupRunRoot = Join-Path $BackupBase (
    "py3d-$SourceVersion-$Stamp"
)
if (Test-IsAtOrUnderRoot $BackupRunRoot $TargetRoot) {
    throw "BackupRoot must be outside TargetSkillRoot"
}
New-Item -ItemType Directory -Force -Path $BackupRunRoot | Out-Null
$BackupRunRoot = (Resolve-Path -LiteralPath $BackupRunRoot).Path
Assert-UnderRoot $BackupRunRoot $BackupBase "backup run"
if (Test-IsAtOrUnderRoot $BackupRunRoot $TargetRoot) {
    throw "BackupRoot must be outside TargetSkillRoot"
}
# Materialize and verify every backup before the first target mutation.
foreach ($Plan in $PatchPlans) {
    $BackupPath = Join-Path $BackupRunRoot $Plan.Entry.Relative
    Assert-UnderRoot $BackupPath $BackupRunRoot "patch backup"
    New-Item -ItemType Directory -Force -Path (
        Split-Path -Parent $BackupPath
    ) | Out-Null
    Copy-Item -LiteralPath $Plan.Destination -Destination $BackupPath
    $BackupHash = Get-FileSha256 $BackupPath
    if ($BackupHash -ne $Plan.Entry.PreimageSha256) {
        throw "patch backup verification failed: $($Plan.Entry.Relative)"
    }
}
foreach ($Plan in $WheelPlans) {
    foreach ($WheelState in $Plan.Stale) {
        $BackupPath = Join-Path $BackupRunRoot (
            "$($Plan.SkillName)/wheels/$($WheelState.Name)"
        )
        Assert-UnderRoot $BackupPath $BackupRunRoot "wheel backup"
        New-Item -ItemType Directory -Force -Path (
            Split-Path -Parent $BackupPath
        ) | Out-Null
        Copy-Item -LiteralPath $WheelState.FullName -Destination $BackupPath
        $BackupHash = Get-FileSha256 $BackupPath
        if ($BackupHash -ne $WheelState.Sha256) {
            throw "wheel backup verification failed: $($Plan.SkillName)"
        }
    }
}

# Repeat CAS after backup I/O and before any patch or removal.
foreach ($Plan in $PatchPlans) {
    $Observed = Get-FileSha256 $Plan.Destination
    if ($Observed -ne $Plan.Entry.PreimageSha256) {
        throw (
            "preimage changed after preflight: $($Plan.Entry.Relative) " +
            "expected=$($Plan.Entry.PreimageSha256) observed=$Observed"
        )
    }
}
foreach ($Plan in $WheelPlans) {
    $Current = @(
        Get-SkillWheelFiles $Plan.WheelsDirectory $WheelManifest.filename
    )
    if ($Current.Count -ne $Plan.Existing.Count) {
        throw "wheel set changed after preflight: $($Plan.SkillName)"
    }
    foreach ($ExpectedWheel in $Plan.Existing) {
        $CurrentWheel = @(
            $Current | Where-Object { $_.Name -eq $ExpectedWheel.Name }
        )
        if (
            $CurrentWheel.Count -ne 1 -or
            (Get-FileSha256 $CurrentWheel[0].FullName) -ne $ExpectedWheel.Sha256
        ) {
            throw "wheel set changed after preflight: $($Plan.SkillName)"
        }
    }
}
if ($WheelPlans.Count -gt 0) {
    $SourceWheelHash = Get-FileSha256 $WheelPath
    if ($SourceWheelHash -ne $WheelManifest.sha256) {
        throw "tracked wheel changed after preflight"
    }
}

if ($PatchPlans.Count -gt 0) {
    Push-Location -LiteralPath $TargetRoot
    try {
        $ApplyArguments = New-Object System.Collections.Generic.List[string]
        $ApplyArguments.Add("apply")
        foreach ($Plan in $PatchPlans) {
            $ApplyArguments.Add($Plan.PatchPath)
        }
        $Apply = Invoke-GitApply -Arguments ($ApplyArguments.ToArray())
        if ($Apply.ExitCode -ne 0) {
            $Apply.Output | ForEach-Object { Write-Host $_ }
            throw "patch application failed after clean preflight"
        }
        foreach ($Plan in $PatchPlans) {
            $ReverseCheck = Invoke-GitApply -Arguments @(
                "apply", "--reverse", "--check", $Plan.PatchPath
            )
            if ($ReverseCheck.ExitCode -ne 0) {
                throw "patch readback failed: $($Plan.Entry.Relative)"
            }
            Write-Host "[OK] patch applied: $($Plan.Entry.Relative)"
        }
    } finally {
        Pop-Location
    }
}

foreach ($Plan in $WheelPlans) {
    foreach ($WheelState in $Plan.Stale) {
        Remove-Item -LiteralPath $WheelState.FullName -Force
    }
    if (-not $Plan.PinnedExact) {
        New-Item -ItemType Directory -Force -Path (
            $Plan.WheelsDirectory
        ) | Out-Null
        Copy-Item -LiteralPath $WheelPath -Destination (
            $Plan.Destination
        )
    }

    $Readback = @(
        Get-SkillWheelFiles $Plan.WheelsDirectory $WheelManifest.filename
    )
    if (
        $Readback.Count -ne 1 -or
        $Readback[0].Name -ne $WheelManifest.filename -or
        (Get-FileSha256 $Readback[0].FullName) -ne $WheelManifest.sha256
    ) {
        throw "wheel readback failed: $($Plan.SkillName)"
    }
    Write-Host "[OK] wheel replaced: $($Plan.SkillName)"
}

Write-Host "Rollout complete; applied changes: $Changes"
Write-Host "Backups: $BackupRunRoot"
