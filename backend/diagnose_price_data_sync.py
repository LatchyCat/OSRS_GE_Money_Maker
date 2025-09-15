#!/usr/bin/env python
"""
Synchronous diagnostic script to check database stored prices.
"""

import os
import sys
import django
from datetime import datetime

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'osrs_tracker.settings')
sys.path.append('/Users/latchy/high_alch_item_recommender/backend')
django.setup()

from apps.prices.models import ProfitCalculation
from apps.items.models import Item

# Items we found data for in the async script
TEST_ITEMS = {
    113: {  # Strength potion(4)
        'name': 'Strength potion(4)',
        'weirdgloop_price': 118,
        'real_ge_price': 96,
        'expected_display_price': 3258,  # What user sees in frontend
    },
    157: {  # Strength potion(3) 
        'name': 'Strength potion(3)',
        'weirdgloop_price': 5066,
        'real_ge_price': 200,
        'expected_display_price': 2775,  # What user sees in frontend
    }
}

def diagnose_database_prices():
    """Check what's stored in database vs what should be there."""
    print("=" * 80)
    print("DATABASE PRICE ANALYSIS - SYNC VERSION")
    print("=" * 80)
    
    for item_id, data in TEST_ITEMS.items():
        print(f"\n🔍 {data['name']} (ID: {item_id})")
        print(f"   Real GE: {data['real_ge_price']} GP")
        print(f"   WeirdGloop: {data['weirdgloop_price']} GP") 
        print(f"   User sees: {data['expected_display_price']} GP")
        
        # Check Item table
        item = Item.objects.filter(id=item_id).first()
        if item:
            print(f"   📝 Item found: {item.name}")
        else:
            print(f"   ❌ Item not in database")
            continue
            
        # Check ProfitCalculation
        profit_calc = ProfitCalculation.objects.filter(item=item).first()
        if profit_calc:
            print(f"   💾 Database Prices:")
            print(f"      Buy Price: {profit_calc.current_buy_price:,} GP" if profit_calc.current_buy_price else "      Buy Price: None")
            print(f"      Sell Price: {profit_calc.current_sell_price:,} GP" if profit_calc.current_sell_price else "      Sell Price: None")
            print(f"      Source: {profit_calc.data_source}")
            print(f"      Quality: {profit_calc.data_quality}")
            print(f"      Updated: {profit_calc.last_updated}")
            
            # Here's the smoking gun - compare stored vs expected
            if profit_calc.current_buy_price:
                stored_vs_weirdgloop = profit_calc.current_buy_price - data['weirdgloop_price']
                stored_vs_real = profit_calc.current_buy_price - data['real_ge_price']
                stored_vs_displayed = abs(profit_calc.current_buy_price - data['expected_display_price'])
                
                print(f"   📊 Price Comparison:")
                print(f"      vs WeirdGloop: {stored_vs_weirdgloop:+,} GP")
                print(f"      vs Real GE: {stored_vs_real:+,} GP")
                print(f"      vs User Display: {stored_vs_displayed:,} GP difference")
                
                # Identify the transformation issue
                multiplier = profit_calc.current_buy_price / data['weirdgloop_price'] if data['weirdgloop_price'] else 0
                print(f"   🔍 Multiplier Analysis:")
                print(f"      Database price is {multiplier:.1f}x the WeirdGloop price")
                
                if multiplier > 10:
                    print(f"   🚨 CRITICAL: Database price is {multiplier:.0f}x higher than source!")
                    print(f"       This suggests a data processing bug or wrong price field mapping")
        else:
            print(f"   ❌ No ProfitCalculation found")

def check_all_strength_potions():
    """Check all strength potion doses to see the pattern."""
    print("\n" + "=" * 80)
    print("ALL STRENGTH POTION DOSES ANALYSIS")
    print("=" * 80)
    
    strength_items = Item.objects.filter(name__icontains='Strength potion').order_by('name')
    
    for item in strength_items:
        print(f"\n🧪 {item.name} (ID: {item.id})")
        
        profit_calc = ProfitCalculation.objects.filter(item=item).first()
        if profit_calc and profit_calc.current_buy_price:
            print(f"   Database Buy Price: {profit_calc.current_buy_price:,} GP")
            print(f"   Updated: {profit_calc.last_updated}")
            print(f"   Source: {profit_calc.data_source}")
            
            # Check if this follows the same pattern as our test items
            if profit_calc.current_buy_price > 1000:
                print(f"   ⚠️  Suspiciously high price (>{profit_calc.current_buy_price:,} GP)")
        elif profit_calc:
            print(f"   No price data (Buy: {profit_calc.current_buy_price}, Sell: {profit_calc.current_sell_price})")
        else:
            print(f"   No ProfitCalculation record")

def check_sample_of_high_priced_items():
    """Check other items with suspiciously high prices."""
    print("\n" + "=" * 80)
    print("HIGH-PRICED ITEMS ANALYSIS")
    print("=" * 80)
    
    # Get items with buy prices over 1000 GP - these might be affected
    high_priced = ProfitCalculation.objects.filter(
        current_buy_price__gt=1000
    ).select_related('item').order_by('-current_buy_price')[:10]
    
    print(f"Found {high_priced.count()} items with buy price >1000 GP")
    print("Top 10 highest priced items:")
    
    for calc in high_priced:
        print(f"\n💰 {calc.item.name} (ID: {calc.item.id})")
        print(f"   Buy: {calc.current_buy_price:,} GP")
        print(f"   Sell: {calc.current_sell_price:,} GP" if calc.current_sell_price else "   Sell: None")
        print(f"   Source: {calc.data_source}")
        print(f"   Updated: {calc.last_updated}")
        
        # Flag items that are likely potions with inflated prices
        if any(word in calc.item.name.lower() for word in ['potion', 'brew', 'dose']):
            print(f"   🔍 This is a potion - likely affected by the same bug")

def main():
    print("🔍 SYNCHRONOUS DATABASE PRICE DIAGNOSTIC")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    diagnose_database_prices()
    check_all_strength_potions()
    check_sample_of_high_priced_items()
    
    print(f"\n" + "=" * 80)
    print("KEY FINDINGS SUMMARY")
    print("=" * 80)
    print(f"""
🎯 CRITICAL DISCOVERIES:

1. WeirdGloop API prices are reasonable:
   - Strength potion(4): 118 GP (close to user's 96 GP)
   - Strength potion(3): 5,066 GP (high, but not 25x off)

2. The bug is in data processing or storage:
   - Some transformation inflates prices 25-30x
   - User sees 3,258 GP for item that should be ~118 GP

3. Investigation needed:
   - Check price data processing pipeline 
   - Look for unit conversion errors (GP to coins?)
   - Check for database field mapping mistakes
   - Verify data import/sync processes

4. Next steps:
   - Find where 118 GP becomes 3,258 GP
   - Check all price update and sync code
   - Add price sanity checks before database storage
""")

if __name__ == '__main__':
    main()