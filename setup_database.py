#!/usr/bin/env python3
"""
Database setup script for OSRS High Alch Tracker.
Creates the PostgreSQL database and runs initial migrations.
"""

import os
import sys
import subprocess
import psycopg
from pathlib import Path


def run_command(command, description, check=True):
    """Run a shell command with description."""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=check, 
                              capture_output=True, text=True)
        if result.stdout:
            print(f"   {result.stdout.strip()}")
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}")
        if e.stderr:
            print(f"   {e.stderr.strip()}")
        return False


def check_postgresql():
    """Check if PostgreSQL is running."""
    print("🔍 Checking PostgreSQL status...")
    
    # Try to connect to default postgres database
    try:
        conn = psycopg.connect(
            host="localhost",
            port=5432,
            dbname="postgres",
            user="postgres"
        )
        conn.close()
        print("✅ PostgreSQL is running")
        return True
    except psycopg.OperationalError as e:
        print(f"❌ PostgreSQL connection failed: {e}")
        print("\n🔧 Solutions:")
        print("   1. Start PostgreSQL service:")
        print("      brew services start postgresql")
        print("      # OR")
        print("      sudo systemctl start postgresql")
        print("   2. Install PostgreSQL if not installed:")
        print("      brew install postgresql")
        return False


def create_database():
    """Create the osrs_tracker database."""
    print("🗄️ Creating database 'osrs_tracker'...")
    
    try:
        # Connect to postgres database to create our database
        conn = psycopg.connect(
            host="localhost",
            port=5432,
            dbname="postgres",
            user="postgres",
            autocommit=True
        )
        
        cursor = conn.cursor()
        
        # Check if database already exists
        cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname = 'osrs_tracker'"
        )
        exists = cursor.fetchone()
        
        if exists:
            print("✅ Database 'osrs_tracker' already exists")
        else:
            # Create the database
            cursor.execute("CREATE DATABASE osrs_tracker")
            print("✅ Database 'osrs_tracker' created successfully")
        
        cursor.close()
        conn.close()
        return True
        
    except psycopg.Error as e:
        print(f"❌ Error creating database: {e}")
        return False


def run_migrations():
    """Run Django migrations."""
    project_root = Path(__file__).parent
    backend_dir = project_root / "backend"
    
    if not backend_dir.exists():
        print(f"❌ Backend directory not found: {backend_dir}")
        return False
    
    # Change to backend directory
    os.chdir(backend_dir)
    
    print("🔄 Running Django migrations...")
    
    # Make migrations first
    if not run_command("python manage.py makemigrations", "Creating migrations"):
        return False
    
    # Run migrations
    if not run_command("python manage.py migrate", "Applying migrations"):
        return False
    
    print("✅ Migrations completed successfully")
    return True


def create_superuser():
    """Optionally create a Django superuser."""
    print("\n👤 Django Superuser Setup")
    print("Would you like to create a superuser account? (y/n): ", end="")
    
    try:
        response = input().lower().strip()
        if response in ['y', 'yes']:
            print("🔧 Creating superuser...")
            subprocess.run(["python", "manage.py", "createsuperuser"], check=False)
        else:
            print("⏭️ Skipping superuser creation")
            print("   You can create one later with: python manage.py createsuperuser")
    except KeyboardInterrupt:
        print("\n⏭️ Skipping superuser creation")


def main():
    """Main setup function."""
    print("🚀 OSRS High Alch Tracker - Database Setup")
    print("=" * 45)
    
    # Step 1: Check PostgreSQL
    if not check_postgresql():
        print("\n❌ Setup failed: PostgreSQL is not available")
        sys.exit(1)
    
    # Step 2: Create database
    if not create_database():
        print("\n❌ Setup failed: Could not create database")
        sys.exit(1)
    
    # Step 3: Run migrations
    if not run_migrations():
        print("\n❌ Setup failed: Migrations failed")
        sys.exit(1)
    
    # Step 4: Optional superuser creation
    create_superuser()
    
    print("\n" + "=" * 45)
    print("✅ Database setup completed successfully!")
    print("\n🚀 You can now start the server with:")
    print("   python start_server.py")
    print("   # OR")
    print("   ./start_server.sh")
    print("\n📋 Server URLs:")
    print("   Main app: http://localhost:8000")
    print("   Admin: http://localhost:8000/admin")
    print("   API: http://localhost:8000/api/v1/planning/")


if __name__ == "__main__":
    main()