#!/usr/bin/env python3
"""
Quick SQLite setup for immediate testing.
Temporarily switches from PostgreSQL to SQLite and runs migrations.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path


def backup_settings():
    """Backup original settings file."""
    project_root = Path(__file__).parent
    settings_file = project_root / "backend" / "osrs_tracker" / "settings.py"
    backup_file = project_root / "backend" / "osrs_tracker" / "settings_postgresql_backup.py"
    
    if settings_file.exists() and not backup_file.exists():
        shutil.copy2(settings_file, backup_file)
        print("✅ Backed up original PostgreSQL settings")
        return True
    return True


def switch_to_sqlite():
    """Switch database configuration to SQLite."""
    project_root = Path(__file__).parent
    settings_file = project_root / "backend" / "osrs_tracker" / "settings.py"
    
    if not settings_file.exists():
        print(f"❌ Settings file not found: {settings_file}")
        return False
    
    # Read current settings
    with open(settings_file, 'r') as f:
        content = f.read()
    
    # Replace PostgreSQL config with SQLite
    postgresql_config = '''DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME", default="osrs_tracker"),
        "USER": config("DB_USER", default="postgres"),
        "PASSWORD": config("DB_PASSWORD", default=""),
        "HOST": config("DB_HOST", default="localhost"),
        "PORT": config("DB_PORT", default="5432"),
    }
}'''

    sqlite_config = '''DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}'''

    if postgresql_config in content:
        content = content.replace(postgresql_config, sqlite_config)
        
        # Write updated settings
        with open(settings_file, 'w') as f:
            f.write(content)
        
        print("✅ Switched to SQLite database configuration")
        return True
    else:
        print("⚠️ PostgreSQL config not found in expected format")
        print("📝 You may need to manually edit settings.py")
        return False


def run_migrations():
    """Run Django migrations."""
    project_root = Path(__file__).parent
    backend_dir = project_root / "backend"
    
    if not backend_dir.exists():
        print(f"❌ Backend directory not found: {backend_dir}")
        return False
    
    # Change to backend directory
    original_dir = os.getcwd()
    os.chdir(backend_dir)
    
    try:
        print("🔄 Creating migrations...")
        result = subprocess.run(
            [sys.executable, "manage.py", "makemigrations"],
            capture_output=True, text=True
        )
        
        if result.returncode != 0:
            print(f"❌ Makemigrations failed: {result.stderr}")
            return False
        
        print("🔄 Applying migrations...")
        result = subprocess.run(
            [sys.executable, "manage.py", "migrate"],
            capture_output=True, text=True
        )
        
        if result.returncode != 0:
            print(f"❌ Migrate failed: {result.stderr}")
            return False
        
        print("✅ Migrations completed successfully")
        return True
        
    finally:
        os.chdir(original_dir)


def main():
    """Main setup function."""
    print("⚡ Quick SQLite Setup for OSRS High Alch Tracker")
    print("=" * 50)
    print("This will temporarily switch to SQLite for immediate testing.")
    print("You can switch back to PostgreSQL later using setup_database.py")
    print("")
    
    # Step 1: Backup settings
    if not backup_settings():
        print("❌ Failed to backup settings")
        sys.exit(1)
    
    # Step 2: Switch to SQLite
    if not switch_to_sqlite():
        print("❌ Failed to switch to SQLite")
        sys.exit(1)
    
    # Step 3: Run migrations
    if not run_migrations():
        print("❌ Failed to run migrations")
        sys.exit(1)
    
    print("")
    print("=" * 50)
    print("✅ Quick setup completed!")
    print("")
    print("🚀 You can now start the server:")
    print("   python start_server.py")
    print("")
    print("📋 Server URLs:")
    print("   Main app: http://localhost:8000")
    print("   Admin: http://localhost:8000/admin")
    print("   API: http://localhost:8000/api/v1/planning/")
    print("")
    print("🔄 To switch back to PostgreSQL later:")
    print("   1. Run: python setup_database.py")
    print("   2. Restore: cp backend/osrs_tracker/settings_postgresql_backup.py backend/osrs_tracker/settings.py")


if __name__ == "__main__":
    main()