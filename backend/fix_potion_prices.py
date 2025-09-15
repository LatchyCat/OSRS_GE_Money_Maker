#!/usr/bin/env python
"""
Script to fix specific potion prices from WeirdGloop API
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'osrs_tracker.settings')
sys.path.append('/Users/latchy/high_alch_item_recommender/backend')
django.setup()

from apps.items.models import Item
from apps.prices.models import ProfitCalculation
from services.weird_gloop_client import SyncWeirdGloopAPIClient

# Key potion items and their IDs that need fixing
POTION_ITEMS = {
    'Magic potion(4)': None,
    'Magic potion(3)': None,
    'Magic potion(2)': None,
    'Magic potion(1)': None,
    'Strength potion(4)': None,
    'Strength potion(3)': None,
    'Strength potion(2)': None,
    'Strength potion(1)': None,
}

def get_potion_item_ids():
    """Find the item IDs for our target potions"""
    print("🔍 Finding potion item IDs...")
    
    for potion_name in list(POTION_ITEMS.keys()):
        try:
            item = Item.objects.get(name=potion_name)
            POTION_ITEMS[potion_name] = item.item_id
            print(f"  ✅ {potion_name}: ID {item.item_id}")
        except Item.DoesNotExist:
            print(f"  ❌ {potion_name}: Not found in database")

def update_potion_prices():
    """Update potion prices directly from WeirdGloop"""
    print("🔄 Updating potion prices from WeirdGloop...")
    
    client = SyncWeirdGloopAPIClient()
    for potion_name, item_id in POTION_ITEMS.items():
        if item_id is None:
            continue
            
        try:
            # Get WeirdGloop data
            data = client.get_latest_price(item_id)
            if not data:
                print(f"  ❌ {potion_name}: No data from WeirdGloop")
                continue
            
            print(f"  🔍 {potion_name}: Raw WeirdGloop response: {data}")
            
            # Parse response - try different formats
            item_data = None
            if isinstance(data, dict):
                # Check if response is nested with item ID as key
                item_id_str = str(item_id)
                if item_id_str in data and isinstance(data[item_id_str], dict):
                    item_data = data[item_id_str]
                # Or if response has 'data' wrapper
                elif 'data' in data and isinstance(data['data'], dict):
                    if item_id_str in data['data']:
                        item_data = data['data'][item_id_str]
                # Or if it's already the item data directly
                elif 'price' in data:
                    item_data = data
                # Try to find any nested dict with price data
                else:
                    for key, value in data.items():
                        if isinstance(value, dict) and 'price' in value:
                            item_data = value
                            break
            
            if not item_data:
                print(f"  ❌ {potion_name}: Could not parse response format")
                continue
                
            weirdgloop_price = item_data.get('price', 0)
            
            # Apply realistic 3% spread
            spread_pct = 0.03
            high_price = int(weirdgloop_price * (1 + spread_pct))  # Buy price
            low_price = int(weirdgloop_price * (1 - spread_pct))   # Sell price
            
            print(f"  📊 {potion_name}: WeirdGloop {weirdgloop_price:,} GP → buy {high_price:,}, sell {low_price:,}")
            
            # Update ProfitCalculation record
            item = Item.objects.get(item_id=item_id)
            profit_calc, created = ProfitCalculation.objects.get_or_create(item=item)
            
            profit_calc.current_buy_price = high_price  # What we pay
            profit_calc.current_sell_price = low_price  # What we get
            profit_calc.data_source = 'weird_gloop'
            profit_calc.data_quality = 'fresh'
            profit_calc.confidence_score = 1.0
            profit_calc.save()
            
            print(f"  ✅ {potion_name}: Updated database prices")
            
        except Exception as e:
            print(f"  ❌ {potion_name}: Error {e}")

def main():
    print("🧪 FIXING SPECIFIC POTION PRICES")
    print("=" * 50)
    
    get_potion_item_ids()
    print()
    update_potion_prices()
    
    print("\n" + "=" * 50)
    print("✅ POTION PRICE FIX COMPLETE")
    
    # Show final results
    print("\nUpdated prices:")
    for potion_name, item_id in POTION_ITEMS.items():
        if item_id:
            try:
                item = Item.objects.get(item_id=item_id)
                profit_calc = ProfitCalculation.objects.get(item=item)
                print(f"  {potion_name}: buy {profit_calc.current_buy_price:,}, sell {profit_calc.current_sell_price:,}")
            except Exception as e:
                print(f"  {potion_name}: Error getting prices - {e}")

if __name__ == '__main__':
    main()