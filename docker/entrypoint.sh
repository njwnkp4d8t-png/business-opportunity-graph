#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to validate required files
validate_files() {
    log_info "Validating required files..."

    local errors=0

    # Check nginx HTML files
    if [ ! -f "/usr/share/nginx/html/index.html" ]; then
        log_error "Frontend index.html not found at /usr/share/nginx/html/index.html"
        errors=$((errors + 1))
    fi

    # Check nginx config
    if [ ! -f "/etc/nginx/conf.d/default.conf" ]; then
        log_error "Nginx configuration not found at /etc/nginx/conf.d/default.conf"
        errors=$((errors + 1))
    fi

    # Validate nginx configuration
    if command -v nginx &> /dev/null; then
        if nginx -t 2>&1 | grep -q "test is successful"; then
            log_info "Nginx configuration is valid"
        else
            log_error "Nginx configuration test failed"
            nginx -t
            errors=$((errors + 1))
        fi
    fi

    # Check supervisor config
    if [ ! -f "/etc/supervisor/conf.d/supervisord.conf" ]; then
        log_error "Supervisor configuration not found"
        errors=$((errors + 1))
    fi

    if [ $errors -gt 0 ]; then
        log_error "Validation failed with $errors error(s)"
        return 1
    fi

    log_info "All required files validated successfully"
    return 0
}

# Function to create required directories
setup_directories() {
    log_info "Setting up directories..."

    mkdir -p /var/log/nginx
    mkdir -p /var/log/supervisor
    mkdir -p /var/run/supervisor
    mkdir -p /run

    log_info "Directories created successfully"
}

# Function to check permissions
check_permissions() {
    log_info "Checking directory permissions..."

    local dirs=(
        "/var/log/nginx"
        "/var/log/supervisor"
        "/var/run/supervisor"
        "/usr/share/nginx/html"
        "/app"
    )

    for dir in "${dirs[@]}"; do
        if [ ! -w "$dir" ]; then
            log_warn "Directory $dir is not writable"
        fi
    done
}

# Function to display environment info
display_env_info() {
    log_info "Container environment information:"
    echo "  User: $(whoami)"
    echo "  Working directory: $(pwd)"
    echo "  Python version: $(python --version 2>&1)"
    echo "  Node available: $(command -v node &> /dev/null && echo 'Yes' || echo 'No')"
    echo "  Nginx version: $(nginx -v 2>&1 | cut -d'/' -f2 || echo 'unknown')"
}

# Function to handle shutdown
shutdown() {
    log_info "Received shutdown signal, gracefully stopping services..."

    if [ -f "/var/run/supervisor/supervisord.pid" ]; then
        supervisorctl stop all
    fi

    log_info "Services stopped successfully"
    exit 0
}

# Trap SIGTERM and SIGINT
trap shutdown SIGTERM SIGINT

# Main execution
main() {
    log_info "Starting Business Opportunity Graph application..."

    # Setup
    setup_directories

    # Validate
    if ! validate_files; then
        log_error "Validation failed, cannot start application"
        exit 1
    fi

    # Check permissions
    check_permissions

    # Display environment info
    display_env_info

    log_info "Starting supervisor to manage services..."

    # Execute the command passed to the container
    exec "$@"
}

# Run main function
main
