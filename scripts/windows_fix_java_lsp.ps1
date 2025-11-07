# Windows fixer for Oracle Java SE Language Server (NetBeans-based)
#
# What this does (safe by default):
# - Verifies a suitable JDK is present (17 or 21 preferred)
# - Optionally sets JAVA_HOME for the current user
# - Stops VS Code, clears the Oracle Java extension caches
# - Optionally reinstalls the Oracle extension
# - Restarts VS Code and prints the final step to trigger tool download
#
# Usage examples:
#   powershell -ExecutionPolicy Bypass -File scripts\windows_fix_java_lsp.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\windows_fix_java_lsp.ps1 -SetUserJavaHome -JavaHome "C:\Program Files\Java\jdk-17"
#   powershell -ExecutionPolicy Bypass -File scripts\windows_fix_java_lsp.ps1 -ReinstallExtension
#
param(
  [switch]$SetUserJavaHome,
  [string]$JavaHome = "",
  [switch]$ReinstallExtension
)

$ErrorActionPreference = 'Stop'

function Info($msg) { Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Warn($msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Ok($msg) { Write-Host "[OK]  $msg" -ForegroundColor Green }
function Run($cmd, [switch]$IgnoreExit) {
  Info "$cmd"
  cmd /c $cmd
  if (-not $IgnoreExit -and $LASTEXITCODE -ne 0) { throw "Command failed: $cmd" }
}

function Get-JavaVersion() {
  try {
    $out = & java -version 2>&1
    return $out -join "\n"
  } catch { return $null }
}

function Test-JavaHomePath($path) {
  if (-not $path) { return $false }
  $javaExe = Join-Path $path 'bin\java.exe'
  return (Test-Path $javaExe)
}

# 1) Verify JDK
$ver = Get-JavaVersion
if ($ver) {
  Ok "java -version:`n$ver"
} else {
  Warn "java not found on PATH. Install JDK 17 or 21 (Adoptium/Oracle) and/or set JAVA_HOME."
}

if ($SetUserJavaHome) {
  if (-not (Test-JavaHomePath $JavaHome)) {
    throw "JAVA_HOME path invalid or missing java.exe in bin: $JavaHome"
  }
  [Environment]::SetEnvironmentVariable('JAVA_HOME', $JavaHome, 'User')
  # Ensure %JAVA_HOME%\bin appears in the User PATH (append if missing)
  $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
  if ($userPath -notmatch '%JAVA_HOME%\\bin') {
    $newPath = ($userPath.TrimEnd(';') + ';%JAVA_HOME%\bin')
    [Environment]::SetEnvironmentVariable('Path', $newPath, 'User')
    Ok "Set JAVA_HOME and appended %JAVA_HOME%\\bin to user PATH. A new terminal is required to pick this up."
  } else {
    Ok "Set JAVA_HOME. User PATH already contains %JAVA_HOME%\\bin."
  }
}

# 2) Stop VS Code if running
try {
  $procs = Get-Process -Name 'Code','Code - Insiders' -ErrorAction SilentlyContinue
  if ($procs) {
    Warn "Stopping VS Code processes..."
    $procs | Stop-Process -Force
  }
} catch {}

# 3) Clear Oracle Java extension caches
$globalStorage = Join-Path $env:APPDATA 'Code\User\globalStorage\oracle.oracle-java'
if (Test-Path $globalStorage) {
  Warn "Clearing globalStorage: $globalStorage"
  Remove-Item -Recurse -Force $globalStorage
}

$workspaceRoot = Join-Path $env:APPDATA 'Code\User\workspaceStorage'
if (Test-Path $workspaceRoot) {
  Get-ChildItem -Path $workspaceRoot -Directory | ForEach-Object {
    $oracleSub = Join-Path $_.FullName 'Oracle.oracle-java'
    if (Test-Path $oracleSub) {
      Warn "Clearing workspace folder: $oracleSub"
      Remove-Item -Recurse -Force $oracleSub
    }
  }
}

# 4) Optional: reinstall the extension
function Get-CodeCmd() {
  $candidates = @('code','code-insiders')
  foreach ($c in $candidates) {
    try { cmd /c "$c --version" *> $null; if ($LASTEXITCODE -eq 0) { return $c } } catch {}
  }
  return $null
}

$codeCmd = Get-CodeCmd
if (-not $codeCmd) {
  Warn "VS Code CLI (code) not found on PATH. You can still start Code from Start Menu and run the command manually."
}

if ($ReinstallExtension -and $codeCmd) {
  Run "$codeCmd --uninstall-extension oracle.oracle-java" -IgnoreExit
  Run "$codeCmd --install-extension oracle.oracle-java"
}

# 5) Restart VS Code and print final instructions
if ($codeCmd) {
  Info "Launching VS Code..."
  Run "$codeCmd ." -IgnoreExit
}

Write-Host "`nNext steps:" -ForegroundColor Magenta
Write-Host "  1) In VS Code, open Command Palette (Ctrl+Shift+P)." -ForegroundColor Magenta
Write-Host "  2) Run: 'Oracle Java: Download Tools'." -ForegroundColor Magenta
Write-Host "  3) Verify 'Oracle Java' Output shows NetBeans LSP starting without errors." -ForegroundColor Magenta
Write-Host "If it still fails: ensure JAVA_HOME points to a JDK (not JRE) and antivirus isn't blocking extension files." -ForegroundColor Magenta

