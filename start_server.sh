#!/bin/bash

# Django development server startup script
# Run from the project root to start the server

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the script directory (project root)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"

echo -e "${BLUE}🚀 OSRS High Alch Tracker - Django Server Startup${NC}"
echo "=================================================="

# Check if backend directory exists
if [ ! -d "$BACKEND_DIR" ]; then
    echo -e "${RED}❌ Error: Backend directory not found!${NC}"
    echo "Expected: $BACKEND_DIR"
    exit 1
fi

# Check if manage.py exists
if [ ! -f "$BACKEND_DIR/manage.py" ]; then
    echo -e "${RED}❌ Error: manage.py not found in backend directory!${NC}"
    echo "Expected: $BACKEND_DIR/manage.py"
    exit 1
fi

# Change to backend directory
cd "$BACKEND_DIR"
echo -e "${GREEN}📁 Changed directory to: $BACKEND_DIR${NC}"

# Check for virtual environment
if [ -d "$PROJECT_ROOT/venv" ]; then
    echo -e "${YELLOW}🔍 Virtual environment detected at ./venv${NC}"
    if [ -z "$VIRTUAL_ENV" ]; then
        echo -e "${YELLOW}💡 Virtual environment not activated. Consider running:${NC}"
        echo -e "${YELLOW}   source venv/bin/activate${NC}"
    else
        echo -e "${GREEN}✅ Virtual environment is active: $VIRTUAL_ENV${NC}"
    fi
fi

# Check if requirements are installed
if [ -f "$PROJECT_ROOT/backend/requirements.txt" ]; then
    echo -e "${BLUE}📦 Checking dependencies...${NC}"
    if ! python -c "import django" 2>/dev/null; then
        echo -e "${YELLOW}⚠️  Django not found. Install dependencies with:${NC}"
        echo -e "${YELLOW}   pip install -r requirements.txt${NC}"
    else
        echo -e "${GREEN}✅ Django is available${NC}"
    fi
fi

# Check database migrations
echo -e "${BLUE}🔍 Checking migrations...${NC}"
if python manage.py showmigrations --plan 2>/dev/null | grep -q "\[ \]"; then
    echo -e "${YELLOW}⚠️  Unapplied migrations detected. Run:${NC}"
    echo -e "${YELLOW}   python manage.py migrate${NC}"
else
    echo -e "${GREEN}✅ Migrations are up to date${NC}"
fi

# Start the server
echo ""
echo -e "${GREEN}🚀 Starting Django development server...${NC}"
echo -e "${BLUE}📋 Server will be available at: http://localhost:8000${NC}"
echo -e "${BLUE}🔧 Admin interface: http://localhost:8000/admin${NC}"
echo -e "${BLUE}📚 API docs: http://localhost:8000/api/v1/planning/${NC}"
echo -e "${YELLOW}🛑 Press Ctrl+C to stop the server${NC}"
echo "=================================================="

# Run the development server
python manage.py runserver 0.0.0.0:8000