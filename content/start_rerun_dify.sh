#!/bin/bash

# Script to start/restart Dify server with CODE_MAX_OBJECT_ARRAY_LENGTH=1000
# This removes the 30-element limit on array[object] outputs in code nodes

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIFY_DIR="${SCRIPT_DIR}/dify"
DIFY_DOCKER_DIR="${DIFY_DIR}/docker"
DIFY_REPO_URL="https://github.com/langgenius/dify.git"
AUTH_DIR="${SCRIPT_DIR}/dify_auth"
PASSWORD_FILE="${AUTH_DIR}/.htpasswd"

# Check if authentication is enabled
ENABLE_AUTH="${ENABLE_AUTH:-false}"
if [ "$ENABLE_AUTH" = "true" ] || [ "$ENABLE_AUTH" = "1" ]; then
    ENABLE_AUTH="true"
else
    ENABLE_AUTH="false"
fi

# Function to detect docker-compose command
detect_docker_compose() {
    if command -v docker-compose &> /dev/null; then
        echo "docker-compose"
    elif docker compose version &> /dev/null; then
        echo "docker compose"
    else
        echo ""
    fi
}

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed or not in PATH${NC}"
    exit 1
fi

# Detect docker-compose command
DOCKER_COMPOSE_CMD=$(detect_docker_compose)
if [ -z "$DOCKER_COMPOSE_CMD" ]; then
    echo -e "${RED}Error: docker-compose command not found${NC}"
    echo "Please install docker-compose or ensure Docker Compose plugin is available"
    exit 1
fi

echo -e "${BLUE}Checking Dify repository...${NC}"

# Check if dify directory exists
if [ ! -d "${DIFY_DIR}" ]; then
    echo -e "${YELLOW}Dify repository not found. Cloning from ${DIFY_REPO_URL}...${NC}"
    echo ""
    
    # Clone the repository
    git clone "${DIFY_REPO_URL}" "${DIFY_DIR}"
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}Error: Failed to clone Dify repository${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✓ Dify repository cloned successfully${NC}"
    echo ""
else
    echo -e "${GREEN}✓ Dify repository found at ${DIFY_DIR}${NC}"
    
    # Check if it's a git repository and update if needed
    if [ -d "${DIFY_DIR}/.git" ]; then
        echo -e "${BLUE}Updating Dify repository...${NC}"
        cd "${DIFY_DIR}"
        git fetch origin 2>/dev/null || true
        echo -e "${GREEN}✓ Repository checked${NC}"
        echo ""
    fi
fi

# Check if docker-compose.yaml exists
if [ ! -f "${DIFY_DOCKER_DIR}/docker-compose.yaml" ]; then
    echo -e "${RED}Error: docker-compose.yaml not found at ${DIFY_DOCKER_DIR}${NC}"
    echo "The repository may not be complete. Please check the clone."
    exit 1
fi

# Check authentication setup if enabled
if [ "$ENABLE_AUTH" = "true" ]; then
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}Checking Authentication Setup${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    
    if [ ! -f "${PASSWORD_FILE}" ]; then
        echo -e "${RED}Error: Authentication is enabled but password file not found${NC}"
        echo "Password file expected at: ${PASSWORD_FILE}"
        echo ""
        echo "Please run the authentication setup script first:"
        echo "  ./setup_dify_auth.sh"
        echo ""
        echo "Or disable authentication by setting:"
        echo "  export ENABLE_AUTH=false"
        echo ""
        exit 1
    fi
    
    echo -e "${GREEN}✓ Authentication enabled${NC}"
    echo -e "${GREEN}✓ Password file found at ${PASSWORD_FILE}${NC}"
    echo ""
fi

echo -e "${GREEN}Starting Dify server with CODE_MAX_OBJECT_ARRAY_LENGTH=1000 and CODE_MAX_STRING_LENGTH=200000000${NC}"
echo -e "${GREEN}Dify will be accessible on port: ${EXPOSE_NGINX_PORT}${NC}"
echo -e "${BLUE}Access URL: http://localhost:${EXPOSE_NGINX_PORT}${NC}"
if [ "$ENABLE_AUTH" = "true" ]; then
    echo -e "${GREEN}HTTP Basic Authentication: ENABLED${NC}"
fi
echo ""

# Export the environment variables
export CODE_MAX_OBJECT_ARRAY_LENGTH=1000
export CODE_MAX_STRING_LENGTH=200000000
export TEMPLATE_TRANSFORM_MAX_LENGTH=2000000

# Set Dify port (default: 8001 to avoid conflict with port 80 and 8080)
export EXPOSE_NGINX_PORT=${DIFY_PORT:-8001}

# Disable HTTPS port to avoid conflict with system nginx on port 443
# Set to a high unused port instead of 443
export EXPOSE_NGINX_SSL_PORT=${DIFY_SSL_PORT:-8443}

# Change to the docker-compose directory
cd "${DIFY_DOCKER_DIR}"

# Setup authentication if enabled
if [ "$ENABLE_AUTH" = "true" ]; then
    echo -e "${BLUE}Setting up authentication...${NC}"
    
    # Create docker-compose override file for authentication
    # Calculate relative path from DIFY_DOCKER_DIR to AUTH_DIR
    OVERRIDE_FILE="${DIFY_DOCKER_DIR}/docker-compose.override.yml"
    RELATIVE_AUTH_DIR=$(realpath --relative-to="${DIFY_DOCKER_DIR}" "${AUTH_DIR}" 2>/dev/null || echo "../dify_auth")
    
    # Create override file with correct paths
    cat > "${OVERRIDE_FILE}" <<EOF
# Docker Compose override for HTTP Basic Authentication
# This file is auto-generated when ENABLE_AUTH=true

version: '3'

services:
  nginx:
    volumes:
      # Mount password file for authentication
      - ${AUTH_DIR}/.htpasswd:/etc/nginx/auth/.htpasswd:ro
      # Mount nginx auth configuration
      - ${AUTH_DIR}/nginx_auth.conf:/etc/nginx/conf.d/auth.conf:ro
    environment:
      - NGINX_AUTH_ENABLED=true
EOF
    
    echo -e "${GREEN}✓ Docker Compose override file configured${NC}"
    echo ""
fi

# Check if containers are already running
if $DOCKER_COMPOSE_CMD ps 2>/dev/null | grep -q "Up"; then
    echo -e "${YELLOW}Dify containers are already running. Restarting...${NC}"
    echo ""
    
    # Stop existing containers
    echo "Stopping existing containers..."
    $DOCKER_COMPOSE_CMD down
    
    echo ""
    echo -e "${GREEN}Containers stopped. Starting with new configuration...${NC}"
    echo ""
fi

# Start the services
echo "Starting Dify services..."
echo "Using: $DOCKER_COMPOSE_CMD"
echo "Environment variables:"
echo "  CODE_MAX_OBJECT_ARRAY_LENGTH=${CODE_MAX_OBJECT_ARRAY_LENGTH}"
echo "  CODE_MAX_STRING_LENGTH=${CODE_MAX_STRING_LENGTH}"
echo "  TEMPLATE_TRANSFORM_MAX_LENGTH=${TEMPLATE_TRANSFORM_MAX_LENGTH}"
echo ""

# Start docker-compose with the environment variables
CODE_MAX_OBJECT_ARRAY_LENGTH=${CODE_MAX_OBJECT_ARRAY_LENGTH} \
CODE_MAX_STRING_LENGTH=${CODE_MAX_STRING_LENGTH} \
TEMPLATE_TRANSFORM_MAX_LENGTH=${TEMPLATE_TRANSFORM_MAX_LENGTH} \
$DOCKER_COMPOSE_CMD up -d

echo ""
echo -e "${BLUE}Waiting for services to be ready...${NC}"

# Function to check if API is ready
check_api_ready() {
    # Try to connect to API health endpoint via nginx
    local max_attempts=60
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        # Check if API container is running and healthy
        if $DOCKER_COMPOSE_CMD exec -T api curl -s -f http://localhost:5001/health >/dev/null 2>&1; then
            return 0
        fi
        
        # Also check via nginx
        if curl -s -f http://localhost/api/health >/dev/null 2>&1; then
            return 0
        fi
        
        if [ $((attempt % 10)) -eq 0 ]; then
            echo -e "${YELLOW}Still waiting for API to be ready... (${attempt}/${max_attempts})${NC}"
        fi
        
        sleep 2
        attempt=$((attempt + 1))
    done
    
    return 1
}

# Wait for API to be ready
if check_api_ready; then
    echo -e "${GREEN}✓ API is ready${NC}"
else
    echo -e "${YELLOW}⚠ API health check timeout, but containers are running${NC}"
    echo "The API might still be initializing. Check logs if issues persist."
fi

# Configure nginx authentication if enabled
if [ "$ENABLE_AUTH" = "true" ]; then
    echo ""
    echo -e "${BLUE}Configuring nginx authentication...${NC}"
    
    # Wait a bit for nginx to be ready
    sleep 5
    
    # Run the nginx configuration script
    if [ -f "${SCRIPT_DIR}/configure_nginx_auth.sh" ]; then
        bash "${SCRIPT_DIR}/configure_nginx_auth.sh" || {
            echo -e "${YELLOW}⚠ Could not configure nginx authentication automatically${NC}"
            echo "You can run ./configure_nginx_auth.sh manually after services are up"
        }
    else
        echo -e "${YELLOW}⚠ Configuration script not found, authentication may not be active${NC}"
    fi
fi

# Check if services started successfully
if $DOCKER_COMPOSE_CMD ps 2>/dev/null | grep -q "Up"; then
    echo ""
    echo -e "${GREEN}✓ Dify server started successfully!${NC}"
    echo ""
    echo "Services status:"
    $DOCKER_COMPOSE_CMD ps
    echo ""
    echo -e "${GREEN}CODE_MAX_OBJECT_ARRAY_LENGTH is set to: ${CODE_MAX_OBJECT_ARRAY_LENGTH}${NC}"
    echo -e "${GREEN}CODE_MAX_STRING_LENGTH is set to: ${CODE_MAX_STRING_LENGTH}${NC}"
    echo -e "${GREEN}TEMPLATE_TRANSFORM_MAX_LENGTH is set to: ${TEMPLATE_TRANSFORM_MAX_LENGTH}${NC}"
    echo -e "${GREEN}Dify is accessible on port: ${EXPOSE_NGINX_PORT}${NC}"
    echo -e "${BLUE}Access URL: http://localhost:${EXPOSE_NGINX_PORT}${NC}"
    if [ "$ENABLE_AUTH" = "true" ]; then
        echo -e "${GREEN}HTTP Basic Authentication: ENABLED${NC}"
        echo -e "${YELLOW}⚠ All access to Dify requires username and password${NC}"
    fi
    echo ""
    echo -e "${BLUE}Note: If you see 502 errors, wait a bit longer for all services to fully initialize.${NC}"
    echo "This can take 30-60 seconds after containers start."
    echo ""
    echo "To view logs, run:"
    echo "  cd ${DIFY_DOCKER_DIR} && $DOCKER_COMPOSE_CMD logs -f api"
    echo ""
    echo "To check API health, run:"
    echo "  curl http://localhost:${EXPOSE_NGINX_PORT}/api/health"
    echo ""
    echo "To stop the server, run:"
    echo "  cd ${DIFY_DOCKER_DIR} && $DOCKER_COMPOSE_CMD down"
else
    echo ""
    echo -e "${RED}✗ Failed to start Dify server${NC}"
    echo ""
    echo "Check logs with:"
    echo "  cd ${DIFY_DOCKER_DIR} && $DOCKER_COMPOSE_CMD logs"
    exit 1
fi

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Starting Marp Flask Service${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

MARP_SERVICE_DIR="${SCRIPT_DIR}/services/marp-flask-service"
MARP_CONTAINER_NAME="marp-flask-service"
MARP_PORT=5004

# Check if Marp service directory exists
if [ ! -d "${MARP_SERVICE_DIR}" ]; then
    echo -e "${RED}Error: Marp service directory not found at ${MARP_SERVICE_DIR}${NC}"
    exit 1
fi

# Check if Marp container is already running
if docker ps --format '{{.Names}}' | grep -q "^${MARP_CONTAINER_NAME}$"; then
    echo -e "${YELLOW}Marp service container is already running. Restarting...${NC}"
    docker stop ${MARP_CONTAINER_NAME}
    docker rm ${MARP_CONTAINER_NAME}
fi

# Remove stopped container if it exists
if docker ps -a --format '{{.Names}}' | grep -q "^${MARP_CONTAINER_NAME}$"; then
    echo "Removing stopped Marp container..."
    docker rm ${MARP_CONTAINER_NAME}
fi

# Build the Marp service image
echo "Building Marp service Docker image..."
cd "${MARP_SERVICE_DIR}"
docker build -t ${MARP_CONTAINER_NAME}:latest .

if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Failed to build Marp service image${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Marp service image built successfully${NC}"
echo ""

# Determine the Dify network name
# Check if we're using docker compose (project name might be "docker" or "dify")
DIFY_NETWORK="docker_default"
if docker network inspect ${DIFY_NETWORK} >/dev/null 2>&1; then
    echo -e "${GREEN}Using Dify network: ${DIFY_NETWORK}${NC}"
elif docker network inspect dify_default >/dev/null 2>&1; then
    DIFY_NETWORK="dify_default"
    echo -e "${GREEN}Using Dify network: ${DIFY_NETWORK}${NC}"
else
    # Try to find the network from running Dify containers
    DIFY_API_NETWORK=$(docker inspect $(docker ps --filter "name=api" --format "{{.Names}}" | head -1) --format '{{range $net, $conf := .NetworkSettings.Networks}}{{$net}}{{end}}' 2>/dev/null | head -1)
    if [ -n "$DIFY_API_NETWORK" ]; then
        DIFY_NETWORK="$DIFY_API_NETWORK"
        echo -e "${GREEN}Detected Dify network: ${DIFY_NETWORK}${NC}"
    else
        echo -e "${YELLOW}Warning: Could not detect Dify network, using docker_default${NC}"
        DIFY_NETWORK="docker_default"
    fi
fi

# Start the Marp service container
echo "Starting Marp service container..."
docker run -d \
    --name ${MARP_CONTAINER_NAME} \
    --network ${DIFY_NETWORK} \
    --restart unless-stopped \
    -p ${MARP_PORT}:5004 \
    -v "${MARP_SERVICE_DIR}/data:/app/data" \
    ${MARP_CONTAINER_NAME}:latest

if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Failed to start Marp service container${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}Waiting for Marp service to be ready...${NC}"

# Function to check if Marp service is ready
check_marp_ready() {
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s -f http://localhost:${MARP_PORT}/health >/dev/null 2>&1; then
            return 0
        fi
        
        if [ $((attempt % 10)) -eq 0 ]; then
            echo -e "${YELLOW}Still waiting for Marp service... (${attempt}/${max_attempts})${NC}"
        fi
        
        sleep 2
        attempt=$((attempt + 1))
    done
    
    return 1
}

# Wait for Marp service to be ready
if check_marp_ready; then
    echo -e "${GREEN}✓ Marp service is ready${NC}"
else
    echo -e "${YELLOW}⚠ Marp service health check timeout${NC}"
    echo "The service might still be initializing. Check logs if issues persist."
fi

echo ""
echo -e "${GREEN}✓ Marp Flask service started successfully!${NC}"
echo ""
echo "Marp service details:"
echo "  - Container: ${MARP_CONTAINER_NAME}"
echo "  - Port: ${MARP_PORT}"
echo "  - Network: ${DIFY_NETWORK}"
echo "  - Health endpoint: http://localhost:${MARP_PORT}/health"
echo "  - Convert endpoint: http://localhost:${MARP_PORT}/convert"
echo "  - Internal endpoint (from Dify): http://${MARP_CONTAINER_NAME}:5004/convert"
echo ""
echo "To view Marp service logs:"
echo "  docker logs -f ${MARP_CONTAINER_NAME}"
echo ""
echo "To stop Marp service:"
echo "  docker stop ${MARP_CONTAINER_NAME}"
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}All services started successfully!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

