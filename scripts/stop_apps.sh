#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}Stopping AI Job Application Agent...${NC}"

# Get the script's directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( dirname "$SCRIPT_DIR" )"

# Navigate to project root
cd "$PROJECT_ROOT"

# Stop Docker containers
echo -e "${GREEN}Stopping Docker containers...${NC}"
docker-compose down 2>/dev/null

# Kill any running start.sh processes
echo -e "${GREEN}Killing start.sh processes...${NC}"
pkill -f "scripts/start.sh" 2>/dev/null

# Kill processes on port 8000 (API server)
echo -e "${GREEN}Killing processes on port 8000...${NC}"
lsof -ti:8000 | xargs kill -9 2>/dev/null

echo -e "${GREEN}✓ Services stopped successfully!${NC}"
