[CmdletBinding()]
param(
    [string]$Python = "python",
    [string]$OutputDirectory = "",
    [switch]$UpdateManifest
)

$ErrorActionPreference = "Stop"
$SourceDateEpoch = 1784937600
$SourceRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$ManifestPath = Join-Path $PSScriptRoot "wheel-manifest.json"
if ([string]::IsNullOrWhiteSpace($OutputDirectory)) {
    $OutputDirectory = Join-Path $PSScriptRoot "..\dist"
}
$TemporaryBase = [IO.Path]::GetFullPath([IO.Path]::GetTempPath())
$TemporaryRoot = Join-Path $TemporaryBase (
    "py3d-wheel-r21-" + [Guid]::NewGuid().ToString("N")
)

function Get-SingleWheel([string]$Stage) {
    New-Item -ItemType Directory -Path $Stage | Out-Null
    & $Python -m pip wheel --no-deps --no-cache-dir $SourceRoot --wheel-dir $Stage |
        ForEach-Object { Write-Host $_ }
    if ($LASTEXITCODE -ne 0) {
        throw "pip wheel failed with exit code $LASTEXITCODE"
    }
    $Wheels = @(Get-ChildItem -LiteralPath $Stage -File -Filter "*.whl")
    if ($Wheels.Count -ne 1) {
        throw "expected exactly one wheel in staging, found $($Wheels.Count)"
    }
    return $Wheels[0]
}

function Get-SourceVersion {
    $Core = [IO.File]::ReadAllText(
        (Join-Path $SourceRoot "py3d\__init__.py")
    )
    $Setup = [IO.File]::ReadAllText((Join-Path $SourceRoot "setup.py"))
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

function Get-DistributionName {
    # Read the distribution name rather than assuming it. It is py3d-dayz, not
    # py3d, because py3d on PyPI belongs to an unrelated library -- and PEP 427
    # normalises the hyphen to an underscore in the wheel filename. Hardcoding
    # either form makes this check a liability the day the name changes again.
    $ProjectFile = Join-Path $SourceRoot "pyproject.toml"
    if (Test-Path -LiteralPath $ProjectFile) {
        $Project = [IO.File]::ReadAllText($ProjectFile)
        $NameMatch = [regex]::Match(
            $Project, '(?m)^\s*name\s*=\s*"(?<name>[A-Za-z0-9._-]+)"\s*$'
        )
        if ($NameMatch.Success) {
            return $NameMatch.Groups["name"].Value -replace "[-.]+", "_"
        }
    }
    # No declared name: setuptools falls back to the source directory.
    return (Split-Path -Leaf $SourceRoot) -replace "[-.]+", "_"
}

function Get-BuildRequirements {
    $PyprojectPath = Join-Path $SourceRoot "pyproject.toml"
    if (-not (Test-Path -LiteralPath $PyprojectPath -PathType Leaf)) {
        throw "py3d pyproject.toml is missing"
    }
    $Pyproject = [IO.File]::ReadAllText($PyprojectPath)
    $BuildSystem = [regex]::Match(
        $Pyproject,
        '(?ms)^\[build-system\]\s*(?<body>.*?)(?=^\[|\z)'
    )
    if (-not $BuildSystem.Success) {
        throw "py3d pyproject.toml has no build-system table"
    }
    $Requires = [regex]::Match(
        $BuildSystem.Groups["body"].Value,
        '(?m)^\s*requires\s*=\s*\[(?<items>[^\]]*)\]\s*$'
    )
    if (-not $Requires.Success) {
        throw "py3d build requirements could not be resolved"
    }
    $Items = $Requires.Groups["items"].Value
    $RequirementMatches = [regex]::Matches(
        $Items,
        '"(?<requirement>[^"]+)"'
    )
    $Requirements = @(
        $RequirementMatches | ForEach-Object {
            $_.Groups["requirement"].Value
        }
    )
    if ($Requirements.Count -eq 0) {
        throw "py3d build requirements are empty"
    }
    $Remainder = [regex]::Replace($Items, '"[^"]+"\s*,?', '')
    if (-not [string]::IsNullOrWhiteSpace($Remainder)) {
        throw "py3d build requirements use unsupported TOML syntax"
    }
    foreach ($Requirement in $Requirements) {
        if ($Requirement -notmatch '^[A-Za-z0-9][A-Za-z0-9._-]*==[A-Za-z0-9][A-Za-z0-9._+-]*$') {
            throw "py3d build requirement is not exactly pinned: $Requirement"
        }
    }
    return $Requirements
}

function Get-PythonVersion {
    $VersionOutput = @(
        & $Python -c "import platform; print(platform.python_version())"
    )
    if ($LASTEXITCODE -ne 0) {
        throw "python version query failed with exit code $LASTEXITCODE"
    }
    $PythonVersion = ($VersionOutput -join "").Trim()
    if ($PythonVersion -notmatch '^\d+\.\d+\.\d+$') {
        throw "python version query returned an invalid value"
    }
    return $PythonVersion
}

function Read-PinnedManifest([string[]]$PinnedBuildRequires) {
    if (-not (Test-Path -LiteralPath $ManifestPath -PathType Leaf)) {
        if (-not $UpdateManifest) {
            throw "tracked wheel manifest is missing; use -UpdateManifest to seal it"
        }
        return $null
    }
    try {
        $Manifest = Get-Content -LiteralPath $ManifestPath -Raw |
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
    if ($Manifest.source_date_epoch -ne $SourceDateEpoch) {
        throw "tracked wheel manifest uses the wrong SOURCE_DATE_EPOCH"
    }
    if ($Manifest.sha256 -notmatch "^[0-9a-f]{64}$") {
        throw "tracked wheel manifest SHA-256 is invalid"
    }
    if ($Manifest.python_version -notmatch '^\d+\.\d+\.\d+$') {
        throw "tracked wheel manifest Python version is invalid"
    }
    $ManifestBuildRequires = @($Manifest.build_requires)
    $InvalidBuildRequires = @(
        $ManifestBuildRequires | Where-Object {
            $_ -isnot [string] -or [string]::IsNullOrWhiteSpace($_)
        }
    )
    if (
        $ManifestBuildRequires.Count -eq 0 -or
        $InvalidBuildRequires.Count -gt 0
    ) {
        throw "tracked wheel manifest build requirements are invalid"
    }
    if (
        [string]::Join("`n", $ManifestBuildRequires) -ne
        [string]::Join("`n", $PinnedBuildRequires)
    ) {
        throw "tracked wheel manifest build requirements do not match pyproject.toml"
    }
    return $Manifest
}

$BuildRequires = @(Get-BuildRequirements)
$PinnedManifest = Read-PinnedManifest $BuildRequires
$PythonVersion = Get-PythonVersion
$HadEpoch = Test-Path Env:SOURCE_DATE_EPOCH
$PreviousEpoch = $env:SOURCE_DATE_EPOCH
try {
    New-Item -ItemType Directory -Path $TemporaryRoot | Out-Null
    $env:SOURCE_DATE_EPOCH = [string]$SourceDateEpoch
    $WheelA = Get-SingleWheel (Join-Path $TemporaryRoot "first")
    $WheelB = Get-SingleWheel (Join-Path $TemporaryRoot "second")

    if ($WheelA.Name -ne $WheelB.Name) {
        throw "repeated builds produced different wheel filenames"
    }
    $HashA = (Get-FileHash -Algorithm SHA256 -LiteralPath $WheelA.FullName).Hash.ToLowerInvariant()
    $HashB = (Get-FileHash -Algorithm SHA256 -LiteralPath $WheelB.FullName).Hash.ToLowerInvariant()
    if ($HashA -ne $HashB) {
        throw "repeated builds are not reproducible: $HashA vs $HashB"
    }

    $Version = Get-SourceVersion
    $ExpectedName = "$(Get-DistributionName)-$Version-py3-none-any.whl"
    if ($WheelA.Name -ne $ExpectedName) {
        throw "wheel filename '$($WheelA.Name)' does not match '$ExpectedName'"
    }

    if (
        $null -ne $PinnedManifest -and
        $HashA -ne $PinnedManifest.sha256 -and
        -not $UpdateManifest
    ) {
        $ExpectedHash = $PinnedManifest.sha256
        Write-Host "expected=$ExpectedHash actual=$HashA"
        throw "The reproducible build does not match the pinned wheel identity."
    }

    if (-not $UpdateManifest) {
        Write-Host "py3d wheel reproducible and pinned: $($WheelA.Name)"
        Write-Host "SHA-256: $HashA"
        Write-Host "Manifest: $ManifestPath"
        return
    }

    New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null
    $ResolvedOutput = (Resolve-Path -LiteralPath $OutputDirectory).Path
    $Destination = Join-Path $ResolvedOutput $WheelA.Name
    Copy-Item -LiteralPath $WheelA.FullName -Destination $Destination -Force
    $CopiedHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $Destination).Hash.ToLowerInvariant()
    if ($CopiedHash -ne $HashA) {
        throw "copied wheel hash does not match the reproducible build"
    }

    $Manifest = [ordered]@{
        schema_version = "py3d-wheel-manifest-v2"
        filename = $WheelA.Name
        sha256 = $HashA
        source_date_epoch = $SourceDateEpoch
        source_version = $Version
        python_version = $PythonVersion
        build_requires = $BuildRequires
    }
    $ManifestText = (
        ($Manifest | ConvertTo-Json -Depth 3) -replace "`r`n", "`n"
    ) + "`n"
    [IO.File]::WriteAllText(
        $ManifestPath,
        $ManifestText,
        (New-Object Text.UTF8Encoding($false))
    )

    Write-Host "py3d wheel reproducible: $($WheelA.Name)"
    Write-Host "SHA-256: $HashA"
    Write-Host "Manifest: $ManifestPath"
} finally {
    if ($HadEpoch) {
        $env:SOURCE_DATE_EPOCH = $PreviousEpoch
    } else {
        Remove-Item Env:SOURCE_DATE_EPOCH -ErrorAction SilentlyContinue
    }
    $NormalizedBase = $TemporaryBase.TrimEnd("\") + "\"
    $NormalizedTask = [IO.Path]::GetFullPath($TemporaryRoot).TrimEnd("\") + "\"
    if (-not $NormalizedTask.StartsWith(
        $NormalizedBase,
        [StringComparison]::OrdinalIgnoreCase
    )) {
        throw "refusing to remove temporary path outside the temp root"
    }
    if (Test-Path -LiteralPath $TemporaryRoot) {
        Remove-Item -LiteralPath $TemporaryRoot -Recurse -Force
    }
}
