#!/usr/bin/env python3
"""
Test script for RuneScape Wiki API client.
"""

import os
import sys
import django
from pathlib import Path

# Add the project directory to the Python path
sys.path.append(str(Path(__file__).resolve().parent))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'osrs_tracker.settings')
django.setup()

from services.api_client import SyncRuneScapeWikiClient
import json

def test_api_client():
    """Test the RuneScape Wiki API client."""
    print("🧪 Testing RuneScape Wiki API Client...")
    
    client = SyncRuneScapeWikiClient()
    
    # Test 1: Health check
    print("\n1. Testing API health check...")
    try:
        is_healthy = client.health_check()
        print(f"   API Health: {'✅ Healthy' if is_healthy else '❌ Unhealthy'}")
    except Exception as e:
        print(f"   ❌ Health check failed: {e}")
        return
    
    # Test 2: Get latest prices for a specific item (Cannonball - ID 2)
    print("\n2. Testing latest price fetch for item 2 (Cannonball)...")
    try:
        data = client.get_latest_prices(item_id=2)
        if 'data' in data and '2' in data['data']:
            item_data = data['data']['2']
            print(f"   ✅ Cannonball prices:")
            print(f"      High: {item_data.get('high')}gp at {item_data.get('highTime')}")
            print(f"      Low: {item_data.get('low')}gp at {item_data.get('lowTime')}")
        else:
            print("   ❌ No price data found")
    except Exception as e:
        print(f"   ❌ Price fetch failed: {e}")
    
    # Test 3: Get item mapping (first 3 items)
    print("\n3. Testing item mapping fetch (first 3 items)...")
    try:
        mapping = client.get_item_mapping()
        if isinstance(mapping, list) and len(mapping) > 0:
            print(f"   ✅ Found {len(mapping)} items in mapping")
            for i, item in enumerate(mapping[:3]):
                print(f"      {i+1}. {item.get('name')} (ID: {item.get('id')}) - High Alch: {item.get('highalch')}gp")
        else:
            print("   ❌ Invalid mapping data")
    except Exception as e:
        print(f"   ❌ Mapping fetch failed: {e}")
    
    print("\n✅ API client test completed!")

if __name__ == "__main__":
    test_api_client()