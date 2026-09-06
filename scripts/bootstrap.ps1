<#
.SYNOPSIS
  One time setup for the CTI Documentation Sync workbench on Windows.
#>
[CmdletBinding()]
param([string]$Python = "python")

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

Write-Host "CTI Documentation Sync setup"
Write-Host "============================"

& $Python --version
Write-Host ""

if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment .venv"
    & $Python -m venv .venv
}
$py = Join-Path $repo ".venv\Scripts\python.exe"

Write-Host "Installing dependencies"
& $py -m pip install --upgrade pip --quiet
& $py -m pip install -r requirements.txt --quiet
Write-Host "  done"
Write-Host ""

if (-not (Test-Path "cti.config.json")) {
    Copy-Item "cti.config.example.json" "cti.config.json"
    Write-Host "Created cti.config.json from the example."
}

Write-Host "Checking configured folders"
& $py -c @"
import sys
sys.path.insert(0, 'scripts')
from cti_paths import load_config, _expand
cfg = load_config()
ok = True
for key in ('deliverables', 'documentation'):
    p = _expand(cfg[key])
    mark = 'OK   ' if p.is_dir() else 'MISS '
    if not p.is_dir():
        ok = False
    print(f'  {mark} {key}: {p}')
sys.exit(0 if ok else 1)
"@
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Edit cti.config.json so both folders point at the real locations, then run this again." -ForegroundColor Yellow
} else {
    Write-Host ""
    Write-Host "Both folders resolved." -ForegroundColor Green
}

Write-Host ""
$agent = Get-Command "cursor-agent" -ErrorAction SilentlyContinue
if ($agent) {
    Write-Host "Cursor CLI found at $($agent.Source)" -ForegroundColor Green
} else {
    Write-Host "Cursor CLI not on PATH. For scheduled runs install it with:" -ForegroundColor Yellow
    Write-Host "  irm 'https://cursor.com/install?win32=true' | iex"
    Write-Host "Interactive use inside the Cursor editor does not need it."
}

Write-Host ""
Write-Host "Running preflight"
Write-Host ""
& $py (Join-Path $repo "scripts\doctor.py")

Write-Host ""
Write-Host "Next:"
Write-Host "  Open this folder in Cursor and paste into the Agent chat:"
Write-Host ""
Write-Host "    Set up this repository on my machine. Run the cti-setup skill and"
Write-Host "    walk me through it. I am at the keyboard, so ask me rather than"
Write-Host "    guessing, especially about where my CTI folders actually live."
Write-Host ""
Write-Host "  Or continue by hand:"
Write-Host "    .\scripts\run_doc_sync.ps1 -Force -DryRun    read only trial run"
Write-Host "    .\scripts\register_schedule.ps1 -At 07:30    monthly schedule"
