<#
.SYNOPSIS
  Build and run the Business Opportunity Knowledge Graph Docker image.

.DESCRIPTION
  - Validates required files and directories exist
  - Stops and removes any existing container with the same name
  - Rebuilds the image from the current working tree
  - Starts a new container with the requested port mapping
  - Provides options for logging, interactive mode, and development

  Default behavior is to run the React frontend on http://localhost:8888.
  You can change the port or image/container names using parameters.

.PARAMETER ImageName
  Name for the Docker image (default: business-opportunity-graph)

.PARAMETER ContainerName
  Name for the Docker container (default: business-opportunity-graph)

.PARAMETER Port
  Host port to map to container port 8080 (default: 8888)

.PARAMETER NoCache
  Build the image without using cache

.PARAMETER ShowLogs
  Show container logs after starting (uses docker logs -f)

.PARAMETER Interactive
  Run container in interactive mode instead of detached

.PARAMETER Dev
  Mount local directories as volumes for development

.EXAMPLE
  .\run_docker.ps1
  Builds and runs with defaults

.EXAMPLE
  .\run_docker.ps1 -Port 3000 -ShowLogs
  Runs on port 3000 and shows logs

.EXAMPLE
  .\run_docker.ps1 -NoCache -Interactive
  Rebuilds without cache and runs interactively
#>

param(
  [string]$ImageName = "business-opportunity-graph",
  [string]$ContainerName = "business-opportunity-graph",
  [int]$Port = 8888,
  [switch]$NoCache,
  [switch]$ShowLogs,
  [switch]$Interactive,
  [switch]$Dev
)

$ErrorActionPreference = "Stop"

# Color functions
function Write-Info {
    param([string]$Message)
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "==> $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "==> $Message" -ForegroundColor Yellow
}

function Write-Failure {
    param([string]$Message)
    Write-Host "==> $Message" -ForegroundColor Red
}

function Invoke-Checked {
  param(
    [string]$Description,
    [scriptblock]$Command
  )

  Write-Info $Description
  & $Command
  if ($LASTEXITCODE -ne 0) {
    throw "Step failed: $Description (exit code $LASTEXITCODE)"
  }
}

function Test-DockerDaemon {
  Write-Info "Checking Docker daemon status..."

  try {
    $null = docker info 2>&1
    if ($LASTEXITCODE -ne 0) {
      throw "Docker daemon is not running"
    }
    Write-Success "Docker daemon is running"
  }
  catch {
    throw "Docker daemon is not accessible. Please start Docker Desktop."
  }
}

function Test-RequiredFiles {
  Write-Info "Validating required files..."

  $requiredFiles = @(
    "docker\Dockerfile",
    "docker\nginx.conf",
    "docker\supervisord.conf",
    "docker\entrypoint.sh",
    "requirements.txt",
    "frontend\package.json"
  )

  $missingFiles = @()

  foreach ($file in $requiredFiles) {
    $fullPath = Join-Path $repoRoot $file
    if (-not (Test-Path $fullPath)) {
      $missingFiles += $file
      Write-Failure "Missing required file: $file"
    }
  }

  if ($missingFiles.Count -gt 0) {
    throw "Cannot build Docker image. Missing $($missingFiles.Count) required file(s)."
  }

  Write-Success "All required files found"
}

function Test-DockerignoreExists {
  $dockerignorePath = Join-Path $repoRoot ".dockerignore"
  if (-not (Test-Path $dockerignorePath)) {
    Write-Warning ".dockerignore file not found. Build context may include unnecessary files."
    Write-Warning "Consider creating a .dockerignore file to reduce build time and image size."
  }
}

function Stop-ExistingContainer {
  param(
    [string]$Name
  )

  Write-Info "Checking for existing container '$Name'..."

  $existing = docker ps -aq --filter "name=^$Name$" 2>$null
  if ($LASTEXITCODE -ne 0) {
    throw "Failed to query Docker for existing containers."
  }

  if (-not $existing) {
    Write-Info "No existing container found"
    return
  }

  Write-Warning "Found existing container '$Name' ($existing). Stopping and removing..."

  docker stop $existing 2>&1 | Out-Null
  if ($LASTEXITCODE -ne 0) {
    Write-Warning "Failed to stop container '$Name' gracefully"
  }

  docker rm $existing 2>&1 | Out-Null
  if ($LASTEXITCODE -ne 0) {
    throw "Failed to remove container '$Name'."
  }

  Write-Success "Existing container removed"
}

function Build-DockerImage {
  param(
    [string]$Name,
    [bool]$UseNoCache
  )

  $buildArgs = @(
    "build"
    "--pull"
    "-t", $Name
    "-f", (Join-Path $dockerDir "Dockerfile")
    "."
  )

  if ($UseNoCache) {
    $buildArgs += "--no-cache"
    Write-Info "Building with --no-cache (this may take longer)"
  }

  Invoke-Checked "Building image '$Name'" {
    docker @buildArgs
  }

  # Verify image was created
  $imageExists = docker images -q $Name 2>$null
  if (-not $imageExists) {
    throw "Image build completed but image '$Name' not found"
  }

  Write-Success "Image '$Name' built successfully"
}

function Start-Container {
  param(
    [string]$Name,
    [string]$Image,
    [int]$HostPort,
    [bool]$IsInteractive,
    [bool]$IsDev
  )

  $runArgs = @(
    "run"
    "--name", $Name
    "-p", "${HostPort}:8080"
  )

  # Add development volumes if requested
  if ($IsDev) {
    Write-Warning "Running in development mode with volume mounts"
    $runArgs += "-v", "$($repoRoot)\frontend:/app/frontend:ro"
    $runArgs += "-v", "$($repoRoot)\data:/app/data:ro"
    $runArgs += "-e", "DEV_MODE=true"
  }

  # Add environment variables
  $runArgs += "-e", "TZ=UTC"

  # Interactive or detached mode
  if ($IsInteractive) {
    Write-Info "Starting container '$Name' in interactive mode on port $HostPort"
    $runArgs += "-it"
  }
  else {
    Write-Info "Starting container '$Name' in detached mode on port $HostPort"
    $runArgs += "-d"
  }

  # Add image name as last argument
  $runArgs += $Image

  Invoke-Checked "Starting container '$Name'" {
    docker @runArgs
  }

  # Wait for container to be healthy
  if (-not $IsInteractive) {
    Write-Info "Waiting for container to be healthy (max 60 seconds)..."
    $timeout = 60
    $elapsed = 0

    while ($elapsed -lt $timeout) {
      Start-Sleep -Seconds 2
      $elapsed += 2

      $health = docker inspect --format='{{.State.Health.Status}}' $Name 2>$null
      if ($health -eq "healthy") {
        Write-Success "Container is healthy"
        break
      }
      elseif ($health -eq "unhealthy") {
        Write-Failure "Container health check failed"
        Write-Info "Showing container logs:"
        docker logs $Name
        throw "Container failed health check"
      }

      Write-Host "." -NoNewline
    }

    if ($elapsed -ge $timeout) {
      Write-Warning "Health check timed out, but container may still be starting"
    }
  }
}

function Show-ContainerLogs {
  param([string]$Name)

  Write-Info "Showing logs for container '$Name' (Ctrl+C to exit)..."
  Write-Host ""
  docker logs -f $Name
}

function Show-Summary {
  param(
    [string]$Name,
    [int]$HostPort
  )

  Write-Host ""
  Write-Host "========================================" -ForegroundColor Cyan
  Write-Success "Container '$Name' is running successfully!"
  Write-Host ""
  Write-Host "  Frontend URL: " -NoNewline
  Write-Host "http://localhost:$HostPort" -ForegroundColor Green
  Write-Host "  Health check: " -NoNewline
  Write-Host "http://localhost:$HostPort/health" -ForegroundColor Green
  Write-Host ""
  Write-Info "Useful commands:"
  Write-Host "  View logs:    docker logs -f $Name"
  Write-Host "  Stop:         docker stop $Name"
  Write-Host "  Restart:      docker restart $Name"
  Write-Host "  Shell access: docker exec -it $Name /bin/bash"
  Write-Host "========================================" -ForegroundColor Cyan
  Write-Host ""
}

# Main execution
try {
  Write-Host ""
  Write-Host "Business Opportunity Graph - Docker Build & Run" -ForegroundColor Magenta
  Write-Host "================================================" -ForegroundColor Magenta
  Write-Host ""

  # Validate environment
  if (-not $PSScriptRoot) {
    throw "PSScriptRoot is not set. Run this script from PowerShell, not from within another host."
  }

  # Resolve repository root (parent of the docker/ folder)
  $dockerDir = $PSScriptRoot
  $repoRoot = Split-Path $dockerDir -Parent
  Set-Location $repoRoot

  Write-Info "Repository root: $repoRoot"

  # Check Docker CLI exists
  if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker CLI not found. Install Docker Desktop and ensure 'docker' is on PATH."
  }

  # Check Docker daemon
  Test-DockerDaemon

  # Validate required files
  Test-RequiredFiles

  # Check for .dockerignore
  Test-DockerignoreExists

  # Stop existing container
  Stop-ExistingContainer -Name $ContainerName

  # Build image
  Build-DockerImage -Name $ImageName -UseNoCache $NoCache

  # Start container
  Start-Container -Name $ContainerName -Image $ImageName -HostPort $Port -IsInteractive $Interactive -IsDev $Dev

  # Show summary if not in interactive mode
  if (-not $Interactive) {
    Show-Summary -Name $ContainerName -HostPort $Port

    # Show logs if requested
    if ($ShowLogs) {
      Show-ContainerLogs -Name $ContainerName
    }
  }

  exit 0
}
catch {
  Write-Host ""
  Write-Failure "ERROR: $_"
  Write-Host ""
  Write-Info "Troubleshooting tips:"
  Write-Host "  1. Ensure Docker Desktop is running"
  Write-Host "  2. Check that all required files exist"
  Write-Host "  3. Try running with -NoCache to rebuild from scratch"
  Write-Host "  4. Check Docker logs: docker logs $ContainerName"
  Write-Host ""
  exit 1
}
