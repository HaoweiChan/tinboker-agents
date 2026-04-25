#!/bin/bash

# Script to start/restart Marp Flask Service independently
# This service converts Marp markdown to PowerPoint (PPTX)

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MARP_SERVICE_DIR="${SCRIPT_DIR}/services/marp-flask-service"
MARP_CONTAINER_NAME="marp-flask-service"
MARP_PORT=5004

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Starting Marp Flask Service${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed or not in PATH${NC}"
    exit 1
fi

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
    echo ""
fi

# Remove stopped container if it exists
if docker ps -a --format '{{.Names}}' | grep -q "^${MARP_CONTAINER_NAME}$"; then
    echo "Removing stopped Marp container..."
    docker rm ${MARP_CONTAINER_NAME}
    echo ""
fi

# Build the Marp service image
echo "Building Marp service Docker image..."
echo "This may take a few minutes on first run..."
cd "${MARP_SERVICE_DIR}"
docker build -t ${MARP_CONTAINER_NAME}:latest .

if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Failed to build Marp service image${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Marp service image built successfully${NC}"
echo ""

# Determine the Dify network name
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
        
        if [ $((attempt % 5)) -eq 0 ]; then
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
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✓ Marp Flask service started successfully!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Marp service details:"
echo "  - Container: ${MARP_CONTAINER_NAME}"
echo "  - Port: ${MARP_PORT}"
echo "  - Network: ${DIFY_NETWORK}"
echo "  - Health endpoint: http://localhost:${MARP_PORT}/health"
echo "  - Convert endpoint: http://localhost:${MARP_PORT}/convert"
echo "  - Internal endpoint (from Dify): http://${MARP_CONTAINER_NAME}:5004/convert"
echo ""
echo "Useful commands:"
echo "  View logs:        docker logs -f ${MARP_CONTAINER_NAME}"
echo "  Stop service:     docker stop ${MARP_CONTAINER_NAME}"
echo "  Restart service:  docker restart ${MARP_CONTAINER_NAME}"
echo "  Check status:     docker ps | grep ${MARP_CONTAINER_NAME}"
echo "  Test health:      curl http://localhost:${MARP_PORT}/health"
echo ""

