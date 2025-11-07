# Windows bootstrap for the Franchise Planner
#
# Purpose: Make previewing the Streamlit front end a one‑step operation.
# - Creates a virtual environment with a compatible Python (prefer 3.11/3.10)
# - Installs minimal packages for the UI (fast) or full requirements
# - Generates exports
# - Launches Streamlit in a new window
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts\windows_start.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\windows_start.ps1 -Port 8502 -Full
#
param(
  [int]$Port = 8501,
  [switch]$Full
)

$ErrorActionPreference = 'Stop'

function Get-PythonExe {
  # Prefer x64 CPython with versions that have wide wheel support
  $candidates = @('py -3.11-64','py -3.10-64','py -3.11','py -3.10','python')
  foreach ($c in $candidates) {
    try {
      $ver = cmd /c "$c --version" 2>&1
      if ($LASTEXITCODE -eq 0 -and $ver) { return $c }
    } catch {}
  }
  throw 'No suitable Python found. Please install Python 3.11 (x64) from https://www.python.org/downloads/windows/ and try again.'
}

function Get-VenvInfo($venvPy) {
  if (-not (Test-Path $venvPy)) { return $null }
  $info = & $venvPy - << 'PY'
import platform, sys, json
print(json.dumps({
  "version": f"{sys.version_info.major}.{sys.version_info.minor}",
  "machine": platform.machine().lower(),
}))
PY
  try { return ($info | ConvertFrom-Json) } catch { return $null }
}

function Run($cmd) {
  Write-Host "`n$ $cmd" -ForegroundColor Cyan
  cmd /c $cmd
  if ($LASTEXITCODE -ne 0) { throw "Command failed: $cmd" }
}

# Resolve repo root
$REPO = Split-Path -Parent $MyInvocation.MyCommand.Path | Split-Path -Parent
Set-Location $REPO

$py = Get-PythonExe
Write-Host "Using Python: $py" -ForegroundColor Green

if (Test-Path .venv) {
  $venvPy = ".\.venv\Scripts\python.exe"
  $vi = Get-VenvInfo $venvPy
  if ($vi -and ($vi.version -notin @('3.11','3.10') -or $vi.machine -like '*arm*')) {
    Write-Host "Existing .venv uses Python $($vi.version) on $($vi.machine). Recreating with a compatible 3.11/3.10 x64..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force .venv
  }
}

if (-not (Test-Path .venv)) {
  Run "$py -m venv .venv"
}

$venvPy = ".\.venv\Scripts\python.exe"

# Upgrade pip
Run "$venvPy -m pip install -U pip"

if ($Full) {
  Write-Host "Installing full requirements (may take a while)..." -ForegroundColor Yellow
  Run "$venvPy -m pip install -r requirements.txt"
} else {
  Write-Host "Installing minimal UI deps (fast path)..." -ForegroundColor Yellow
  Run "$venvPy -m pip install pandas numpy streamlit pydeck"
}

# Generate exports
Run "$venvPy -m scripts.cleanse --verbose"

# Launch Streamlit in a new window
$args = "-m streamlit run services\app.py --server.port $Port"
Start-Process -FilePath $venvPy -ArgumentList $args -WindowStyle Normal
Write-Host "`nOpen http://localhost:$Port in your browser." -ForegroundColor Green
