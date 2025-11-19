# Docker Setup - Business Opportunity Graph

This directory contains robust Docker configuration files for running the Business Opportunity Graph application.

## Files Overview

### Core Configuration Files

- **Dockerfile** - Multi-stage build with error handling and validation
- **nginx.conf** - Production-ready nginx configuration with security headers
- **supervisord.conf** - Process manager configuration for running multiple services
- **entrypoint.sh** - Startup script with validation and health checks
- **docker-compose.yml** - Docker Compose orchestration configuration

### Helper Scripts

- **run_docker.ps1** - PowerShell script to build and run the container with comprehensive error handling

## Quick Start

### Using PowerShell Script (Recommended)

```powershell
# Build and run with defaults (port 8888)
.\docker\run_docker.ps1

# Run on a different port
.\docker\run_docker.ps1 -Port 3000

# Build without cache
.\docker\run_docker.ps1 -NoCache

# Show logs after starting
.\docker\run_docker.ps1 -ShowLogs

# Run in interactive mode
.\docker\run_docker.ps1 -Interactive

# Development mode with volume mounts
.\docker\run_docker.ps1 -Dev
```

### Using Docker Compose

```bash
# Start the application
docker-compose -f docker/docker-compose.yml up -d

# View logs
docker-compose -f docker/docker-compose.yml logs -f

# Stop the application
docker-compose -f docker/docker-compose.yml down
```

### Using Docker Commands Directly

```bash
# Build the image
docker build -t business-opportunity-graph -f docker/Dockerfile .

# Run the container
docker run -d --name business-opportunity-graph -p 8888:8080 business-opportunity-graph

# View logs
docker logs -f business-opportunity-graph
```

## Features

### Error Handling & Validation

- **Dockerfile Validation**:
  - Validates frontend build output exists
  - Validates nginx configuration before copying
  - Checks Python dependencies with `pip check`
  - Uses `set -ex` for immediate error detection

- **Entrypoint Script**:
  - Validates all required files exist before starting
  - Tests nginx configuration syntax
  - Checks directory permissions
  - Displays environment information for debugging

- **PowerShell Script**:
  - Validates Docker daemon is running
  - Checks all required files exist before building
  - Validates image was created after build
  - Waits for container health check before declaring success
  - Provides detailed error messages and troubleshooting tips

### Security Features

- Runs as non-root user (`appuser`)
- Security headers in nginx (X-Frame-Options, X-Content-Type-Options, etc.)
- Hides nginx version from headers
- Denies access to hidden files
- Minimal attack surface with multi-stage builds
- No new privileges in docker-compose

### Performance Optimizations

- Multi-stage builds to reduce final image size
- Gzip compression for static assets
- Browser caching for static resources
- Efficient layer caching with npm ci
- Cleaned apt cache and npm cache

### Monitoring & Debugging

- Health check endpoint at `/health`
- Comprehensive logging with rotation
- Supervisor process monitoring
- Colored log output for easy reading
- Interactive mode for debugging

## Configuration

### Environment Variables

Set in docker-compose.yml or when running with `docker run`:

- `TZ` - Timezone (default: UTC)
- `PYTHONUNBUFFERED` - Python output buffering (default: 1)
- `DEV_MODE` - Enable development features (set with -Dev flag)

### Ports

- Container exposes port `8080`
- Default host mapping is `8888:8080`
- Customizable via `-Port` parameter in PowerShell script

### Resource Limits

Configured in docker-compose.yml:

- CPU limit: 2 cores
- Memory limit: 2GB
- CPU reservation: 0.5 cores
- Memory reservation: 512MB

Adjust based on your system resources.

## Troubleshooting

### Container Won't Start

1. Check Docker daemon is running:
   ```powershell
   docker info
   ```

2. View container logs:
   ```bash
   docker logs business-opportunity-graph
   ```

3. Check health status:
   ```bash
   docker inspect business-opportunity-graph --format='{{.State.Health.Status}}'
   ```

### Build Failures

1. Rebuild without cache:
   ```powershell
   .\docker\run_docker.ps1 -NoCache
   ```

2. Ensure all required files exist:
   - `requirements.txt`
   - `frontend/package.json`
   - All files in `docker/` directory

3. Check Docker build logs for specific error messages

### Access Container Shell

For debugging:

```bash
docker exec -it business-opportunity-graph /bin/bash
```

### View Supervisor Status

Inside the container:

```bash
docker exec business-opportunity-graph supervisorctl status
```

## Development Mode

Use the `-Dev` flag to mount local directories and enable hot-reloading:

```powershell
.\docker\run_docker.ps1 -Dev
```

This mounts:
- `frontend/` directory (read-only)
- `data/` directory (read-only)

## Production Deployment

For production deployment:

1. Set appropriate resource limits in docker-compose.yml
2. Configure proper logging driver
3. Use environment-specific configuration files
4. Enable HTTPS with reverse proxy (nginx, Traefik, etc.)
5. Set up monitoring and alerting
6. Configure backup strategy for data volumes

## Health Checks

The application includes multiple health checks:

1. **Docker Health Check**: Curls `http://localhost:8080/`
   - Interval: 30s
   - Timeout: 10s
   - Retries: 3
   - Start period: 40s

2. **Nginx Health Endpoint**: `/health`
   - Returns "healthy" when nginx is responsive

3. **Entrypoint Validation**:
   - File existence checks
   - Nginx configuration validation
   - Permission checks

## Architecture

### Multi-Stage Build

1. **frontend-build**: Builds React frontend with validation
2. **python-base**: Installs Python dependencies and system packages
3. **runtime**: Final stage with both frontend and backend, runs with supervisor

### Process Management

Supervisor manages multiple processes:
- Nginx (serves frontend)
- Backend service (commented out, uncomment when needed)

### File Structure

```
docker/
├── Dockerfile              # Multi-stage build configuration
├── nginx.conf             # Nginx web server configuration
├── supervisord.conf       # Process manager configuration
├── entrypoint.sh          # Startup validation script
├── run_docker.ps1         # PowerShell build & run script
├── docker-compose.yml     # Docker Compose configuration
└── README.md             # This file
```

## Advanced Usage

### Custom Build Arguments

```bash
docker build \
  --build-arg BUILDKIT_INLINE_CACHE=1 \
  -t business-opportunity-graph \
  -f docker/Dockerfile \
  .
```

### Multiple Instances

Run multiple instances on different ports:

```powershell
.\docker\run_docker.ps1 -ContainerName bog-dev -Port 8001
.\docker\run_docker.ps1 -ContainerName bog-staging -Port 8002
```

### Cleanup

```bash
# Stop and remove container
docker stop business-opportunity-graph
docker rm business-opportunity-graph

# Remove image
docker rmi business-opportunity-graph

# Full cleanup
docker system prune -a
```

## Support

For issues or questions:
1. Check logs: `docker logs -f business-opportunity-graph`
2. Review error messages in the PowerShell script output
3. Verify all required files exist
4. Ensure Docker Desktop is running and up to date
