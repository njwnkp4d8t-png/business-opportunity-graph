# Windows All‑in‑One starter (optional Java LSP fix + app launch)
#
# Purpose: One command to (optionally) fix the Oracle Java SE Language Server
# and then bring up the Streamlit app with fresh exports.
#
# Usage examples:
#   powershell -ExecutionPolicy Bypass -File scripts\windows_all_in_one.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\windows_all_in_one.ps1 -Port 8502 -Full
#   powershell -ExecutionPolicy Bypass -File scripts\windows_all_in_one.ps1 -FixJava -SetUserJavaHome -JavaHome "C:\\Program Files\\Java\\jdk-17"
#
param(
  [switch]$FixJava,
  [switch]$SetUserJavaHome,
  [string]$JavaHome = "",
  [switch]$ReinstallJavaExtension,
  [int]$Port = 8501,
  [switch]$Full,
  [switch]$Rebuild
)

$ErrorActionPreference = 'Stop'

function Info($msg) { Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function RunPS1($path, $args) {
  if (-not (Test-Path $path)) { throw "Script not found: $path" }
  $cmd = "powershell -ExecutionPolicy Bypass -File `"$path`" $args"
  Info $cmd
  cmd /c $cmd
  if ($LASTEXITCODE -ne 0) { throw "Command failed: $cmd" }
}

$REPO = Split-Path -Parent $MyInvocation.MyCommand.Path | Split-Path -Parent
Set-Location $REPO

if ($FixJava) {
  $fix = Join-Path $REPO 'scripts\windows_fix_java_lsp.ps1'
  $fixArgs = @()
  if ($SetUserJavaHome) { $fixArgs += '-SetUserJavaHome' }
  if ($JavaHome) { $fixArgs += @('-JavaHome', '"' + $JavaHome + '"') }
  if ($ReinstallJavaExtension) { $fixArgs += '-ReinstallExtension' }
  RunPS1 $fix ($fixArgs -join ' ')
}

$start = Join-Path $REPO 'scripts\windows_start.ps1'
$startArgs = @('-Port', $Port)
if ($Full) { $startArgs += '-Full' }
if ($Rebuild) { $startArgs += '-Rebuild' }
RunPS1 $start ($startArgs -join ' ')

Write-Host "`nAll done. Open http://localhost:$Port if the browser doesn’t pop up automatically." -ForegroundColor Green
