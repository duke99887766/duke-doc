[CmdletBinding()]
param(
    [string]$TargetRoot
)

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$sourceRoot = Join-Path $repoRoot 'skills'

if (-not (Test-Path -LiteralPath $sourceRoot -PathType Container)) {
    throw "Skills source directory not found: $sourceRoot"
}

if ([string]::IsNullOrWhiteSpace($TargetRoot)) {
    if (-not [string]::IsNullOrWhiteSpace($env:CODEX_HOME)) {
        $TargetRoot = Join-Path $env:CODEX_HOME 'skills'
    }
    else {
        $TargetRoot = Join-Path $env:USERPROFILE '.codex\skills'
    }
}

$targetRootFull = [IO.Path]::GetFullPath($TargetRoot)
New-Item -ItemType Directory -Path $targetRootFull -Force | Out-Null

$skillNames = @(
    'duke-doc',
    'duke-interview-requirement',
    'duke-write-acceptance',
    'duke-write-spec',
    'duke-review-spec',
    'duke-check-implementation',
    'duke-capture-web-research'
)

foreach ($skillName in $skillNames) {
    $sourceSkill = Join-Path $sourceRoot $skillName
    if (-not (Test-Path -LiteralPath $sourceSkill -PathType Container)) {
        throw "Skill directory not found: $sourceSkill"
    }

    $targetSkill = Join-Path $targetRootFull $skillName
    New-Item -ItemType Directory -Path $targetSkill -Force | Out-Null

    Get-ChildItem -LiteralPath $sourceSkill -Force | ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination $targetSkill -Recurse -Force
    }

    Write-Output "Installed: $skillName"
}

Write-Output "Target: $targetRootFull"
