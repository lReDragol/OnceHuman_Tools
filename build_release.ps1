$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot

$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Python executable not found: $python"
}

$releaseDir = Join-Path $repoRoot "dist\releases"
$workRoot = Join-Path $repoRoot "build\pyinstaller"
$specRoot = Join-Path $repoRoot "build\specs"

New-Item -ItemType Directory -Path $releaseDir -Force | Out-Null
New-Item -ItemType Directory -Path $workRoot -Force | Out-Null
New-Item -ItemType Directory -Path $specRoot -Force | Out-Null

function Invoke-Build {
    param(
        [string]$Name,
        [string]$EntryScript,
        [string]$IconPath,
        [string[]]$ExtraArgs = @()
    )

    $workPath = Join-Path $workRoot $Name
    if (Test-Path $workPath) {
        Remove-Item $workPath -Recurse -Force
    }

    $outputFile = Join-Path $releaseDir "$Name.exe"
    if (Test-Path $outputFile) {
        Remove-Item $outputFile -Force
    }

    $args = @(
        "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        "--name", $Name,
        "--distpath", $releaseDir,
        "--workpath", $workPath,
        "--specpath", $specRoot,
        "--paths", $repoRoot,
        "--additional-hooks-dir", $repoRoot,
        "--icon", (Join-Path $repoRoot $IconPath)
    ) + $ExtraArgs + @((Join-Path $repoRoot $EntryScript))

    Write-Host "Building $Name..."
    & $python @args
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller build failed for $Name"
    }
}

Invoke-Build `
    -Name "OnceHumanTools_V4.5" `
    -EntryScript "main.py" `
    -IconPath "data\icons\icon.ico" `
    -ExtraArgs @(
        "--add-data", "$(Join-Path $repoRoot 'data');data",
        "--add-data", "$(Join-Path $repoRoot 'translations.json');."
    )

Invoke-Build `
    -Name "BotFishPortable_V4" `
    -EntryScript "onli_fish_bot\main.py" `
    -IconPath "data\icons\fish.ico" `
    -ExtraArgs @(
        "--exclude-module", "PyQt5",
        "--add-data", "$(Join-Path $repoRoot 'data\icons\fish.ico');data\icons"
    )

Invoke-Build `
    -Name "OnceHumanCalcPortable_V2.5" `
    -EntryScript "portable_calc_v2\main.py" `
    -IconPath "data\icons\icon.ico" `
    -ExtraArgs @(
        "--add-data", "$(Join-Path $repoRoot 'data');data",
        "--add-data", "$(Join-Path $repoRoot 'translations.json');."
    )

Write-Host ""
Write-Host "Release files:"
Get-ChildItem $releaseDir -Filter *.exe | Select-Object Name, Length, LastWriteTime
