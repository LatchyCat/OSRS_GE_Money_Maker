#!/bin/bash

# Database setup script for OSRS High Alch Tracker
# Creates PostgreSQL database and runs migrations

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"

echo -e "${BLUE}🚀 OSRS High Alch Tracker - Database Setup${NC}"
echo "============================================="

# Function to check if PostgreSQL is running
check_postgresql() {
    echo -e "${BLUE}🔍 Checking PostgreSQL status...${NC}"
    
    if pg_isready -h localhost -p 5432 >/dev/null 2>&1; then
        echo -e "${GREEN}✅ PostgreSQL is running${NC}"
        return 0
    else
        echo -e "${RED}❌ PostgreSQL is not running${NC}"
        echo -e "${YELLOW}🔧 Solutions:${NC}"
        echo -e "${YELLOW}   1. Start PostgreSQL service:${NC}"
        echo -e "${YELLOW}      brew services start postgresql${NC}"
        echo -e "${YELLOW}      # OR${NC}"
        echo -e "${YELLOW}      sudo systemctl start postgresql${NC}"
        echo -e "${YELLOW}   2. Install PostgreSQL if not installed:${NC}"
        echo -e "${YELLOW}      brew install postgresql${NC}"
        return 1
    fi
}

# Function to create database
create_database() {
    echo -e "${BLUE}🗄️ Creating database 'osrs_tracker'...${NC}"
    
    # Check if database exists
    if psql -h localhost -U postgres -lqt | cut -d \| -f 1 | grep -qw osrs_tracker; then
        echo -e "${GREEN}✅ Database 'osrs_tracker' already exists${NC}"
        return 0
    fi
    
    # Create database
    if createdb -h localhost -U postgres osrs_tracker; then
        echo -e "${GREEN}✅ Database 'osrs_tracker' created successfully${NC}"
        return 0
    else
        echo -e "${RED}❌ Failed to create database${NC}"
        echo -e "${YELLOW}💡 You may need to set a password for postgres user${NC}"
        return 1
    fi
}

# Function to run migrations
run_migrations() {
    echo -e "${BLUE}🔄 Running Django migrations...${NC}"
    
    # Change to backend directory
    cd "$BACKEND_DIR"
    
    # Make migrations
    echo -e "${BLUE}🔧 Creating migrations...${NC}"
    if python manage.py makemigrations; then
        echo -e "${GREEN}✅ Migrations created${NC}"
    else
        echo -e "${RED}❌ Failed to create migrations${NC}"
        return 1
    fi
    
    # Apply migrations
    echo -e "${BLUE}🔧 Applying migrations...${NC}"
    if python manage.py migrate; then
        echo -e "${GREEN}✅ Migrations applied successfully${NC}"
        return 0
    else
        echo -e "${RED}❌ Failed to apply migrations${NC}"
        return 1
    fi
}

# Function to create superuser
create_superuser() {
    echo ""
    echo -e "${BLUE}👤 Django Superuser Setup${NC}"
    echo -n "Would you like to create a superuser account? (y/n): "
    read -r response
    
    if [[ "$response" =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}🔧 Creating superuser...${NC}"
        python manage.py createsuperuser
    else
        echo -e "${YELLOW}⏭️ Skipping superuser creation${NC}"
        echo -e "${YELLOW}   You can create one later with: python manage.py createsuperuser${NC}"
    fi
}

# Main execution
main() {
    # Step 1: Check PostgreSQL
    if ! check_postgresql; then
        echo -e "\n${RED}❌ Setup failed: PostgreSQL is not available${NC}"
        exit 1
    fi
    
    # Step 2: Create database
    if ! create_database; then
        echo -e "\n${RED}❌ Setup failed: Could not create database${NC}"
        exit 1
    fi
    
    # Step 3: Run migrations
    if ! run_migrations; then
        echo -e "\n${RED}❌ Setup failed: Migrations failed${NC}"
        exit 1
    fi
    
    # Step 4: Optional superuser creation
    create_superuser
    
    echo ""
    echo "============================================="
    echo -e "${GREEN}✅ Database setup completed successfully!${NC}"
    echo ""
    echo -e "${BLUE}🚀 You can now start the server with:${NC}"
    echo -e "${BLUE}   python start_server.py${NC}"
    echo -e "${BLUE}   # OR${NC}"
    echo -e "${BLUE}   ./start_server.sh${NC}"
    echo ""
    echo -e "${BLUE}📋 Server URLs:${NC}"
    echo -e "${BLUE}   Main app: http://localhost:8000${NC}"
    echo -e "${BLUE}   Admin: http://localhost:8000/admin${NC}"
    echo -e "${BLUE}   API: http://localhost:8000/api/v1/planning/${NC}"
}

main "$@"