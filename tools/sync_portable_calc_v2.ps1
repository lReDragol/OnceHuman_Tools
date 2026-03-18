$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path | Split-Path -Parent
$portableRoot = Join-Path $repoRoot "portable_calc_v2"

function Copy-File {
    param(
        [string]$Source,
        [string]$Destination
    )

    if (-not (Test-Path $Source)) {
        throw "Missing source file: $Source"
    }

    $parent = Split-Path -Parent $Destination
    if ($parent) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }

    Copy-Item $Source $Destination -Force
}

function Mirror-Directory {
    param(
        [string]$Source,
        [string]$Destination
    )

    if (-not (Test-Path $Source)) {
        throw "Missing source directory: $Source"
    }

    New-Item -ItemType Directory -Path $Destination -Force | Out-Null

    & robocopy $Source $Destination /MIR /NFL /NDL /NJH /NJS /NP | Out-Null
    if ($LASTEXITCODE -ge 8) {
        throw "robocopy failed for $Source -> $Destination with exit code $LASTEXITCODE"
    }
}

Copy-File (Join-Path $repoRoot "config.py") (Join-Path $portableRoot "config.py")
Copy-File (Join-Path $repoRoot "translations.json") (Join-Path $portableRoot "translations.json")
Copy-File (Join-Path $repoRoot "data\menu\calc_and_mod_tab.py") (Join-Path $portableRoot "data\menu\calc_and_mod_tab.py")
Copy-File (Join-Path $repoRoot "data\file\ru.ttf") (Join-Path $portableRoot "data\file\ru.ttf")
Copy-File (Join-Path $repoRoot "data\icons\target_image.png") (Join-Path $portableRoot "data\icons\target_image.png")
Copy-File (Join-Path $repoRoot "data\icons\icon.ico") (Join-Path $portableRoot "data\icons\icon.ico")

Mirror-Directory (Join-Path $repoRoot "data\menu\calc") (Join-Path $portableRoot "data\menu\calc")
Mirror-Directory (Join-Path $repoRoot "data\icons\armor") (Join-Path $portableRoot "data\icons\armor")
Mirror-Directory (Join-Path $repoRoot "data\icons\attachments") (Join-Path $portableRoot "data\icons\attachments")
Mirror-Directory (Join-Path $repoRoot "data\icons\deviations") (Join-Path $portableRoot "data\icons\deviations")
Mirror-Directory (Join-Path $repoRoot "data\icons\menu_weapon_icons") (Join-Path $portableRoot "data\icons\menu_weapon_icons")
Mirror-Directory (Join-Path $repoRoot "data\icons\mods") (Join-Path $portableRoot "data\icons\mods")
Mirror-Directory (Join-Path $repoRoot "data\icons\statuses") (Join-Path $portableRoot "data\icons\statuses")
Mirror-Directory (Join-Path $repoRoot "data\icons\weapons") (Join-Path $portableRoot "data\icons\weapons")

Write-Host "portable_calc_v2 synchronized successfully."
