#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}Starting AI Job Application Agent...${NC}"

# Get the script's directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( dirname "$SCRIPT_DIR" )"

# Check if .env exists in project root
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    echo -e "${RED}Warning: No .env file found in project root.${NC}"
    echo "Please:"
    echo "  1. cd $PROJECT_ROOT"
    echo "  2. cp .env.example .env"
    echo "  3. Edit .env and configure your environment variables"
    exit 1
fi

# Function to start Docker Desktop (macOS/Linux)
start_docker() {
    local max_wait=60  # Maximum wait time in seconds
    local elapsed=0

    echo -e "${YELLOW}Docker is not running. Attempting to start Docker Desktop...${NC}"

    # Detect OS and start Docker accordingly
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if [ -d "/Applications/Docker.app" ]; then
            open -a Docker
            echo -e "${BLUE}Starting Docker Desktop...${NC}"
        else
            echo -e "${RED}Error: Docker Desktop not found in /Applications/${NC}"
            echo "Please install Docker Desktop from https://www.docker.com/products/docker-desktop"
            exit 1
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux - try to start Docker daemon
        if command -v systemctl &> /dev/null; then
            echo -e "${BLUE}Starting Docker daemon with systemctl...${NC}"
            sudo systemctl start docker
        else
            echo -e "${RED}Error: Unable to start Docker automatically on this Linux system.${NC}"
            echo "Please start Docker manually and try again."
            exit 1
        fi
    else
        echo -e "${RED}Error: Unsupported operating system.${NC}"
        echo "Please start Docker manually and try again."
        exit 1
    fi

    # Wait for Docker to be ready
    echo -e "${BLUE}Waiting for Docker to be ready...${NC}"
    while ! docker info > /dev/null 2>&1; do
        if [ $elapsed -ge $max_wait ]; then
            echo -e "${RED}Error: Docker failed to start within ${max_wait} seconds.${NC}"
            echo "Please start Docker Desktop manually and try again."
            exit 1
        fi
        printf "."
        sleep 2
        elapsed=$((elapsed + 2))
    done
    echo ""
    echo -e "${GREEN}Docker is now running!${NC}"
}

# Check if Docker is running, start it if not
if ! docker info > /dev/null 2>&1; then
    start_docker
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Error: docker-compose is not installed.${NC}"
    echo "Please install Docker Compose and try again."
    exit 1
fi

# Function to cleanup on exit
cleanup() {
    echo -e "\n${BLUE}Shutting down services...${NC}"
    cd "$PROJECT_ROOT"
    docker-compose down
    echo -e "${GREEN}Services stopped successfully.${NC}"
    exit 0
}

# Trap EXIT, INT, and TERM signals
trap cleanup EXIT INT TERM

# Navigate to project root
cd "$PROJECT_ROOT"

# Start services with Docker Compose
echo -e "${GREEN}Starting Docker containers...${NC}"
docker-compose up --build

# Note: docker-compose up will run in the foreground and show logs
# Press Ctrl+C to stop all services
