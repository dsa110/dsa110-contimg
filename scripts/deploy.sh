#!/bin/bash
# DSA-110 Pipeline Deployment Script
# Production deployment automation

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
DEPLOYMENT_ENV="${1:-production}"
CONFIG_PATH="${2:-$PROJECT_DIR/config}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Error handling
error_exit() {
    log_error "$1"
    exit 1
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if running as root (not recommended for production)
    if [[ $EUID -eq 0 ]]; then
        log_warning "Running as root is not recommended for production deployment"
    fi
    
    # Check required commands based on deployment type
    local required_commands=("docker")
    
    if [[ "$DEPLOYMENT_ENV" == "docker-compose" ]]; then
        required_commands+=("docker-compose")
    elif [[ "$DEPLOYMENT_ENV" == "kubernetes" ]]; then
        required_commands+=("kubectl" "helm")
    elif [[ "$DEPLOYMENT_ENV" == "systemd" ]]; then
        required_commands+=("systemctl")
    fi
    
    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            error_exit "Required command '$cmd' not found"
        fi
    done
    
    # Check Docker daemon
    if ! docker info &> /dev/null; then
        error_exit "Docker daemon is not running"
    fi
    
    # Check Kubernetes cluster (if deploying to K8s)
    if [[ "$DEPLOYMENT_ENV" == "kubernetes" ]]; then
        if ! kubectl cluster-info &> /dev/null; then
            error_exit "Kubernetes cluster is not accessible"
        fi
    fi
    
    log_success "Prerequisites check passed"
}

# Create necessary directories
create_directories() {
    log_info "Creating necessary directories..."
    
    local directories=(
        "$PROJECT_DIR/data/hdf5"
        "$PROJECT_DIR/data/ms"
        "$PROJECT_DIR/data/images"
        "$PROJECT_DIR/data/mosaics"
        "$PROJECT_DIR/data/photometry"
        "$PROJECT_DIR/output"
        "$PROJECT_DIR/logs"
        "$PROJECT_DIR/config"
        "$PROJECT_DIR/backups"
    )
    
    for dir in "${directories[@]}"; do
        mkdir -p "$dir"
        chmod 755 "$dir"
    done
    
    log_success "Directories created"
}

# Generate configuration files
generate_config() {
    log_info "Generating configuration files..."
    
    # Generate production config if it doesn't exist
    if [[ ! -f "$CONFIG_PATH/production_config.yaml" ]]; then
        log_info "Generating production configuration..."
        /opt/miniforge/envs/dsa_contimg/bin/python -c "
import sys
sys.path.insert(0, '$PROJECT_DIR')
from core.config.production_config import ProductionConfig
config = ProductionConfig()
config.save_to_file('$CONFIG_PATH/production_config.yaml')
print('Production configuration generated')
"
    fi
    
    # Generate pipeline config if it doesn't exist
    if [[ ! -f "$CONFIG_PATH/pipeline_config.yaml" ]]; then
        log_info "Generating pipeline configuration..."
        cat > "$CONFIG_PATH/pipeline_config.yaml" << 'EOF'
# DSA-110 Pipeline Configuration
pipeline:
  name: "DSA-110 Continuum Imaging Pipeline"
  version: "1.0.0"
  environment: "production"

# Data paths
paths:
  data_dir: "/app/data"
  output_dir: "/app/output"
  log_dir: "/app/logs"
  config_dir: "/app/config"

# Pipeline stages
stages:
  data_ingestion:
    enabled: true
    max_concurrent: 2
    block_duration_hours: 1.0
    
  calibration:
    enabled: true
    max_concurrent: 2
    sky_model_path: "/app/config/sky_models"
    
  imaging:
    enabled: true
    max_concurrent: 1
    cell_size: "3arcsec"
    image_size: [2400, 2400]
    
  mosaicking:
    enabled: true
    max_concurrent: 1
    mosaic_type: "optimal"
    
  photometry:
    enabled: true
    max_concurrent: 2
    aperture_radius: 3.0

# Error handling
error_handling:
  max_retries: 3
  retry_delay: 1.0
  circuit_breaker:
    failure_threshold: 5
    recovery_timeout: 60.0

# Monitoring
monitoring:
  enabled: true
  health_check_interval: 30
  metrics_port: 8080
  dashboard_port: 8081

# Redis configuration
redis:
  host: "dsa110-redis"
  port: 6379
  db: 0
  password: ""

# Logging
logging:
  level: "INFO"
  format: "json"
  file: "/app/logs/pipeline.log"
  max_size: "100MB"
  backup_count: 5
EOF
    fi
    
    log_success "Configuration files generated"
}

# Build Docker images
build_images() {
    log_info "Building Docker images..."
    
    cd "$PROJECT_DIR"
    
    # Build main pipeline image
    log_info "Building pipeline image..."
    docker build -t dsa110-contimg:latest -f Dockerfile .
    
    # Build additional images if needed
    if [[ -f "Dockerfile.monitoring" ]]; then
        log_info "Building monitoring image..."
        docker build -t dsa110-monitoring:latest -f Dockerfile.monitoring .
    fi
    
    log_success "Docker images built"
}

# Deploy with Docker Compose
deploy_docker_compose() {
    log_info "Deploying with Docker Compose..."
    
    cd "$PROJECT_DIR"
    
    # Stop existing services
    log_info "Stopping existing services..."
    docker-compose down --remove-orphans || true
    
    # Start services
    log_info "Starting services..."
    docker-compose up -d
    
    # Wait for services to be healthy
    log_info "Waiting for services to be healthy..."
    local max_attempts=30
    local attempt=0
    
    while [[ $attempt -lt $max_attempts ]]; do
        if docker-compose ps | grep -q "Up (healthy)"; then
            log_success "Services are healthy"
            break
        fi
        
        if [[ $attempt -eq $((max_attempts - 1)) ]]; then
            log_error "Services failed to become healthy"
            docker-compose logs
            exit 1
        fi
        
        sleep 10
        ((attempt++))
    done
    
    log_success "Docker Compose deployment completed"
}

# Deploy to Kubernetes
deploy_kubernetes() {
    log_info "Deploying to Kubernetes..."
    
    cd "$PROJECT_DIR"
    
    # Apply Kubernetes manifests
    log_info "Applying Kubernetes manifests..."
    kubectl apply -f k8s/namespace.yaml
    kubectl apply -f k8s/configmap.yaml
    kubectl apply -f k8s/redis.yaml
    kubectl apply -f k8s/pipeline.yaml
    
    # Wait for deployments to be ready
    log_info "Waiting for deployments to be ready..."
    kubectl wait --for=condition=available --timeout=300s deployment/dsa110-pipeline -n dsa110-pipeline
    kubectl wait --for=condition=available --timeout=300s deployment/dsa110-redis -n dsa110-pipeline
    
    # Check pod status
    log_info "Checking pod status..."
    kubectl get pods -n dsa110-pipeline
    
    log_success "Kubernetes deployment completed"
}

# Deploy with systemd
deploy_systemd() {
    log_info "Deploying with systemd..."
    
    # Install systemd services
    log_info "Installing systemd services..."
    sudo cp "$PROJECT_DIR/systemd/dsa110-redis.service" /etc/systemd/system/
    sudo cp "$PROJECT_DIR/systemd/dsa110-pipeline.service" /etc/systemd/system/
    
    # Reload systemd
    sudo systemctl daemon-reload
    
    # Enable and start services
    log_info "Starting services..."
    sudo systemctl enable dsa110-redis.service
    sudo systemctl enable dsa110-pipeline.service
    
    sudo systemctl start dsa110-redis.service
    sleep 10
    sudo systemctl start dsa110-pipeline.service
    
    # Check service status
    log_info "Checking service status..."
    sudo systemctl status dsa110-redis.service
    sudo systemctl status dsa110-pipeline.service
    
    log_success "Systemd deployment completed"
}

# Setup monitoring
setup_monitoring() {
    log_info "Setting up monitoring..."
    
    # Install Prometheus (if not already installed)
    if ! command -v prometheus &> /dev/null; then
        log_info "Installing Prometheus..."
        # Add Prometheus installation logic here
    fi
    
    # Install Grafana (if not already installed)
    if ! command -v grafana-server &> /dev/null; then
        log_info "Installing Grafana..."
        # Add Grafana installation logic here
    fi
    
    # Configure log rotation
    log_info "Configuring log rotation..."
    sudo tee /etc/logrotate.d/dsa110-pipeline > /dev/null << 'EOF'
/app/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 dsa110 dsa110
    postrotate
        systemctl reload dsa110-pipeline.service
    endscript
}
EOF
    
    log_success "Monitoring setup completed"
}

# Setup backup
setup_backup() {
    log_info "Setting up backup system..."
    
    # Create backup script
    cat > "$PROJECT_DIR/scripts/backup.sh" << 'EOF'
#!/bin/bash
# DSA-110 Pipeline Backup Script

BACKUP_DIR="/opt/dsa110-pipeline/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="dsa110_backup_$DATE.tar.gz"

# Create backup
tar -czf "$BACKUP_DIR/$BACKUP_FILE" \
    --exclude="*.log" \
    --exclude="*.tmp" \
    /app/data \
    /app/output \
    /app/config

# Keep only last 30 days of backups
find "$BACKUP_DIR" -name "dsa110_backup_*.tar.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_FILE"
EOF
    
    chmod +x "$PROJECT_DIR/scripts/backup.sh"
    
    # Setup cron job for daily backups
    log_info "Setting up daily backup cron job..."
    (crontab -l 2>/dev/null; echo "0 2 * * * $PROJECT_DIR/scripts/backup.sh") | crontab -
    
    log_success "Backup system setup completed"
}

# Main deployment function
main() {
    log_info "Starting DSA-110 Pipeline deployment..."
    log_info "Deployment environment: $DEPLOYMENT_ENV"
    
    check_prerequisites
    create_directories
    generate_config
    build_images
    
    case "$DEPLOYMENT_ENV" in
        "docker-compose")
            deploy_docker_compose
            ;;
        "kubernetes")
            deploy_kubernetes
            ;;
        "systemd")
            deploy_systemd
            ;;
        *)
            error_exit "Unknown deployment environment: $DEPLOYMENT_ENV"
            ;;
    esac
    
    setup_monitoring
    setup_backup
    
    log_success "DSA-110 Pipeline deployment completed successfully!"
    log_info "Pipeline is available at: http://localhost:8080"
    log_info "Monitoring dashboard: http://localhost:8081"
    log_info "Health check: http://localhost:8080/health"
}

# Run main function
main "$@"
