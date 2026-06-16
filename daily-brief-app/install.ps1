# Daily brief app - first-time install
# Usage: .\install.ps1

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Find-Python {
    $candidates = @(
        (Get-Command py -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source),
        (Get-Command python -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source),
        "$env:LOCALAPPDATA\Programs\Python\Python314\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "C:\Program Files\Python314\python.exe",
        "C:\Program Files\Python313\python.exe",
        "C:\Program Files\Python312\python.exe",
        "C:\Program Files\Python311\python.exe"
    ) | Where-Object { $_ -and (Test-Path $_) }

    foreach ($p in $candidates) {
        if ($p -match "WindowsApps\\python") { continue }
        $ver = & $p -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
        if ($ver -and [version]$ver -ge [version]"3.11") { return $p }
    }
    return $null
}

$py = Find-Python
if (-not $py) {
    Write-Host ""
    Write-Host "Python 3.11+ not found." -ForegroundColor Red
    Write-Host "Install from: https://www.python.org/downloads/windows/" -ForegroundColor Yellow
    Write-Host "Check 'Add python.exe to PATH', then reopen PowerShell and run .\install.ps1" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Or: winget install Python.Python.3.12" -ForegroundColor Cyan
    exit 1
}

Write-Host "Using Python: $py" -ForegroundColor Green

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Creating virtual environment..."
    & $py -m venv .venv
}

$venvPy = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
& $venvPy -m pip install --upgrade pip
& $venvPy -m pip install -r requirements.txt
& $venvPy -m playwright install chromium

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env" -ForegroundColor Green
}

# VC++ runtime required by playwright/greenlet on Windows
if (-not (Test-Path "$env:SystemRoot\System32\vcruntime140.dll")) {
    Write-Host ""
    Write-Host "WARNING: Microsoft VC++ Redistributable not found." -ForegroundColor Yellow
    Write-Host "Playwright may fail with 'DLL load failed' for greenlet." -ForegroundColor Yellow
    Write-Host "Install: winget install Microsoft.VCRedist.2015+.x64" -ForegroundColor Cyan
    Write-Host "Or download: https://aka.ms/vs/17/release/vc_redist.x64.exe" -ForegroundColor Cyan
    Write-Host ""
}

Write-Host ""
Write-Host "Done. Run: .\start.ps1" -ForegroundColor Green
