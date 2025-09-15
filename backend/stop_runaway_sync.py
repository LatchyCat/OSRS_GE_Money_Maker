#!/usr/bin/env python3
"""
Emergency script to stop runaway sync processes.

This script helps stop the runaway background sync by:
1. Setting environment variable to disable auto-sync
2. Providing instructions for manual restart
"""

import os
import sys
import subprocess
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def stop_runaway_sync():
    """Stop runaway sync processes and provide restart instructions."""
    
    print("🚨 EMERGENCY SYNC STOPPER")
    print("=" * 50)
    
    # Check if Django server is running
    try:
        result = subprocess.run(['pgrep', '-f', 'python.*manage.py.*runserver'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            pids = result.stdout.strip().split('\n')
            print(f"🔍 Found Django server processes: {pids}")
            
            # Ask user if they want to kill the processes
            response = input("❓ Kill Django server processes? (y/N): ")
            if response.lower() in ('y', 'yes'):
                for pid in pids:
                    if pid.strip():
                        try:
                            subprocess.run(['kill', pid.strip()], check=True)
                            print(f"✅ Killed process {pid.strip()}")
                        except subprocess.CalledProcessError as e:
                            print(f"❌ Failed to kill process {pid.strip()}: {e}")
        else:
            print("✅ No Django server processes found running")
            
    except Exception as e:
        print(f"⚠️  Could not check for running processes: {e}")
    
    print("\n📋 RESTART INSTRUCTIONS:")
    print("1. Set environment variable to disable auto-sync:")
    print("   export DISABLE_AUTO_SYNC=true")
    print("\n2. Start Django server normally:")
    print("   python manage.py runserver")
    print("\n3. To manually sync with safety limits:")
    print("   python manage.py sync_items_and_prices --limit 50 --prices-only")
    print("\n4. To re-enable auto-sync later:")
    print("   unset DISABLE_AUTO_SYNC")
    print("   (or set DISABLE_AUTO_SYNC=false)")
    
    print("\n🔧 ENVIRONMENT SETUP:")
    current_env = os.environ.get('DISABLE_AUTO_SYNC', 'not set')
    print(f"   Current DISABLE_AUTO_SYNC: {current_env}")
    
    if current_env.lower() not in ('true', '1', 'yes'):
        response = input("❓ Set DISABLE_AUTO_SYNC=true in current shell? (y/N): ")
        if response.lower() in ('y', 'yes'):
            os.environ['DISABLE_AUTO_SYNC'] = 'true'
            print("✅ Set DISABLE_AUTO_SYNC=true for this session")
            print("⚠️  Remember to export it in your shell: export DISABLE_AUTO_SYNC=true")

if __name__ == "__main__":
    stop_runaway_sync()