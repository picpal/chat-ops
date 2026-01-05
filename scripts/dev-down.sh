#!/bin/bash

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOCKER_DIR="$PROJECT_ROOT/infra/docker"

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}Stopping ChatOps Environment${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# Parse arguments
CLEAN=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --clean)
            CLEAN=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: ./dev-down.sh [--clean]"
            exit 1
            ;;
    esac
done

cd "$DOCKER_DIR"

if $CLEAN; then
    echo -e "${YELLOW}Stopping and removing all containers and volumes...${NC}"
    docker compose down -v --remove-orphans
    echo -e "${GREEN}✓ All containers and volumes removed${NC}"
else
    echo -e "${GREEN}Stopping containers...${NC}"
    docker compose down --remove-orphans
    echo -e "${GREEN}✓ Containers stopped (volumes preserved)${NC}"
fi

# Kill local development servers if running
echo ""
echo -e "${GREEN}Killing local development servers...${NC}"
lsof -ti:8080 | xargs kill -9 2>/dev/null || true
lsof -ti:8000 | xargs kill -9 2>/dev/null || true

echo ""
echo -e "${GREEN}✓ Environment stopped${NC}"
echo ""
echo -e "${BLUE}================================${NC}"
