#!/usr/bin/env python3
"""
Safe restart script for OSRS High Alch backend.

This script provides a safe way to restart the Django server with 
auto-sync disabled to prevent runaway processes.
"""

import os
import sys
import subprocess
import signal
import time

def safe_restart():
    """Safely restart Django with auto-sync disabled."""
    
    print("🚀 SAFE DJANGO RESTART")
    print("=" * 40)
    
    # Step 1: Stop any running Django processes
    print("1. 🛑 Stopping Django processes...")
    try:
        result = subprocess.run(['pgrep', '-f', 'python.*manage.py.*runserver'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            pids = [pid.strip() for pid in result.stdout.strip().split('\n') if pid.strip()]
            print(f"   Found processes: {pids}")
            
            for pid in pids:
                try:
                    subprocess.run(['kill', '-TERM', pid], check=True)
                    print(f"   ✅ Sent SIGTERM to {pid}")
                except subprocess.CalledProcessError:
                    try:
                        subprocess.run(['kill', '-KILL', pid], check=True)  
                        print(f"   ⚠️  Force killed {pid}")
                    except subprocess.CalledProcessError:
                        print(f"   ❌ Could not kill {pid}")
            
            # Wait for processes to stop
            print("   ⏳ Waiting 3s for processes to stop...")
            time.sleep(3)
        else:
            print("   ✅ No Django processes found")
    except Exception as e:
        print(f"   ⚠️  Error stopping processes: {e}")
    
    # Step 2: Set safe environment
    print("\n2. 🔧 Setting safe environment...")
    os.environ['DISABLE_AUTO_SYNC'] = 'true'
    print("   ✅ Set DISABLE_AUTO_SYNC=true")
    
    # Step 3: Start Django server
    print("\n3. 🚀 Starting Django server...")
    print("   Command: python manage.py runserver")
    print("   Environment: DISABLE_AUTO_SYNC=true")
    print("\n   Press Ctrl+C to stop the server")
    print("   " + "=" * 38)
    
    try:
        # Start server with safe environment
        env = os.environ.copy()
        env['DISABLE_AUTO_SYNC'] = 'true'
        subprocess.run(['python', 'manage.py', 'runserver'], env=env)
    except KeyboardInterrupt:
        print("\n\n🛑 Server stopped by user")
    except Exception as e:
        print(f"\n\n❌ Error starting server: {e}")
    
    print("\n📋 MANUAL SYNC COMMANDS (if needed):")
    print("   # Sync 50 items only:")
    print("   python manage.py sync_items_and_prices --limit 50 --max-requests 100")
    print("\n   # Test sync (no API calls):")
    print("   python manage.py sync_items_and_prices --dry-run")
    print("\n   # Full sync with safety limits:")  
    print("   python manage.py sync_items_and_prices --max-requests 200 --request-delay 3.0")

if __name__ == "__main__":
    safe_restart()