#!/usr/bin/env python3
"""
Django development server startup script.
Run from the project root to start the server.
"""

import os
import sys
import subprocess
from pathlib import Path


def main():
    """Start the Django development server."""
    
    # Get the project root directory
    project_root = Path(__file__).parent
    backend_dir = project_root / "backend"
    
    # Verify backend directory exists
    if not backend_dir.exists():
        print("❌ Error: Backend directory not found!")
        print(f"Expected: {backend_dir}")
        sys.exit(1)
    
    # Verify manage.py exists
    manage_py = backend_dir / "manage.py"
    if not manage_py.exists():
        print("❌ Error: manage.py not found in backend directory!")
        print(f"Expected: {manage_py}")
        sys.exit(1)
    
    # Change to backend directory
    os.chdir(backend_dir)
    print(f"📁 Changed directory to: {backend_dir}")
    
    # Check if virtual environment should be activated
    venv_path = project_root / "venv"
    if venv_path.exists():
        print("🔍 Virtual environment detected at ./venv")
        print("💡 Make sure to activate it first: source venv/bin/activate")
    
    # Print startup information
    print("\n🚀 Starting Django development server...")
    print("📋 Server will be available at: http://localhost:8000")
    print("🛑 Press Ctrl+C to stop the server")
    print("-" * 50)
    
    try:
        # Run Django development server
        subprocess.run([
            sys.executable, "manage.py", "runserver", "0.0.0.0:8000"
        ], check=True)
    
    except KeyboardInterrupt:
        print("\n\n🛑 Server stopped by user")
    
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error starting server: {e}")
        print("\n🔧 Common solutions:")
        print("  1. Install dependencies: pip install -r requirements.txt")
        print("  2. Run migrations: python manage.py migrate")
        print("  3. Check database connection")
        sys.exit(1)
    
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()