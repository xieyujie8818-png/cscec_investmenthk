# Daily brief app - start server
# Usage: .\start.ps1

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$venvPy = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
    Write-Host "Not installed yet. Run: .\install.ps1" -ForegroundColor Red
    exit 1
}

$port = 8765
if (Test-Path ".env") {
    Get-Content ".env" | ForEach-Object {
        if ($_ -match '^\s*PORT\s*=\s*(\d+)') { $port = $Matches[1] }
    }
}

$url = "http://127.0.0.1:$port"
Write-Host ""
Write-Host "Starting daily brief server..." -ForegroundColor Green
Write-Host "Open in browser: $url" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop" -ForegroundColor Gray
Write-Host ""

Start-Job -ScriptBlock {
    param($u)
    Start-Sleep -Seconds 3
    Start-Process $u
} -ArgumentList $url | Out-Null

& $venvPy -m app.main
