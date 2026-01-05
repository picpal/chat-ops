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
echo -e "${BLUE}ChatOps Development Environment${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# Check if docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker is not running${NC}"
    exit 1
fi

# Parse arguments
FULL_STACK=false
POSTGRES_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --full)
            FULL_STACK=true
            shift
            ;;
        --postgres)
            POSTGRES_ONLY=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: ./dev-up.sh [--full|--postgres]"
            exit 1
            ;;
    esac
done

cd "$DOCKER_DIR"

# Copy .env if not exists
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        echo -e "${YELLOW}Created .env from .env.example${NC}"
        echo -e "${YELLOW}Please update OPENAI_API_KEY in .env${NC}"
    fi
fi

if $POSTGRES_ONLY; then
    echo -e "${GREEN}Starting PostgreSQL only...${NC}"
    docker compose up -d postgres
    
    echo ""
    echo -e "${GREEN}✓ PostgreSQL started on localhost:5432${NC}"
    echo ""
    echo "Run services manually:"
    echo "  Core API:       cd services/core-api && ./gradlew bootRun"
    echo "  AI Orchestrator: cd services/ai-orchestrator && python3 -m uvicorn app.main:app --reload --port 8000"
    
elif $FULL_STACK; then
    echo -e "${GREEN}Starting full stack with Docker...${NC}"
    docker compose up -d --build
    
    echo ""
    echo -e "${GREEN}✓ All services started${NC}"
    echo ""
    echo "Endpoints:"
    echo "  Nginx (main):     http://localhost"
    echo "  Core API:         http://localhost:8080"
    echo "  AI Orchestrator:  http://localhost:8000"
    echo "  PostgreSQL:       localhost:5432"
    
else
    # Default: PostgreSQL only + instructions for local dev
    echo -e "${GREEN}Starting PostgreSQL...${NC}"
    docker compose up -d postgres
    
    # Wait for PostgreSQL to be ready
    echo -e "${YELLOW}Waiting for PostgreSQL...${NC}"
    until docker compose exec -T postgres pg_isready -U chatops_user -d chatops > /dev/null 2>&1; do
        sleep 1
    done
    
    echo ""
    echo -e "${GREEN}✓ PostgreSQL is ready on localhost:5432${NC}"
    echo ""
    echo "To run services locally:"
    echo ""
    echo "  1. Core API (Terminal 1):"
    echo "     cd services/core-api && ./gradlew bootRun"
    echo ""
    echo "  2. AI Orchestrator (Terminal 2):"
    echo "     cd services/ai-orchestrator"
    echo "     export DATABASE_URL=postgresql://chatops_user:chatops_pass@localhost:5432/chatops"
    echo "     python3 -m uvicorn app.main:app --reload --port 8000"
    echo ""
    echo "  3. Seed documents (Optional):"
    echo "     python3 scripts/seed-documents.py"
fi

echo ""
echo -e "${BLUE}================================${NC}"
