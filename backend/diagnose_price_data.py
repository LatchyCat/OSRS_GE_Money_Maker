#!/usr/bin/env python
"""
Diagnostic script to investigate price data sources and compare with real GE prices.

This script will:
1. Check WeirdGloop API responses for specific items
2. Compare with user-reported real GE prices
3. Analyze data freshness and quality
4. Identify source of price discrepancies
"""

import os
import sys
import asyncio
import django
from datetime import datetime, timezone
import json

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'osrs_tracker.settings')
sys.path.append('/Users/latchy/high_alch_item_recommender/backend')
django.setup()

from services.weird_gloop_client import WeirdGloopAPIClient
from services.multi_source_price_client import MultiSourcePriceClient
from apps.prices.models import ProfitCalculation
from apps.items.models import Item

# User-reported real GE prices for comparison
REAL_GE_PRICES = {
    113: {  # Strength potion(4) 
        'name': 'Strength potion(4)',
        'real_ge_price': 96,  # User reported: 96 GP active trading price
        'ge_default_price': 118,  # User reported: 118 GP default price
    },
    157: {  # Strength potion(3)
        'name': 'Strength potion(3)', 
        'real_ge_price': 200,  # Estimated based on user's pattern
        'ge_default_price': 250,
    },
    2775: { # Magic potion(3) 
        'name': 'Magic potion(3)',
        'real_ge_price': 160,  # User reported: 160 GP active trading price  
        'ge_default_price': 133,  # User reported: 133 GP default price
    },
    431: {  # Zamorak brew(3) - user mentioned
        'name': 'Zamorak brew(3)',
        'real_ge_price': 431,  # User reported: 431 GP active trading price
        'ge_default_price': 475,  # User reported: 475 GP default price  
    },
    433: {  # Zamorak brew(2) - user mentioned
        'name': 'Zamorak brew(2)', 
        'real_ge_price': 200,  # User reported: 200 GP active trading price
        'ge_default_price': 680,  # User reported: 680 GP default price
    }
}

async def check_weirdgloop_raw_data():
    """Check raw WeirdGloop API responses for our test items."""
    print("=" * 80)
    print("WEIRDGLOOP API RAW DATA ANALYSIS")
    print("=" * 80)
    
    async with WeirdGloopAPIClient() as client:
        for item_id, expected in REAL_GE_PRICES.items():
            print(f"\n🔍 Checking {expected['name']} (ID: {item_id})")
            print(f"   Expected Real GE: {expected['real_ge_price']} GP")
            print(f"   Expected GE Default: {expected['ge_default_price']} GP")
            
            try:
                # Get raw API response
                raw_data = await client.get_latest_price(item_id)
                
                if raw_data:
                    print(f"   📊 WeirdGloop Raw Response:")
                    print(f"      {json.dumps(raw_data, indent=6, default=str)}")
                    
                    # Extract price and timestamp
                    price = raw_data.get('price', 'N/A')
                    timestamp = raw_data.get('timestamp', 'N/A')
                    
                    print(f"   💰 WeirdGloop Price: {price:,} GP" if isinstance(price, (int, float)) else f"   💰 WeirdGloop Price: {price}")
                    print(f"   ⏰ Data Timestamp: {timestamp}")
                    
                    # Calculate age if timestamp is available
                    if timestamp and timestamp != 'N/A':
                        try:
                            if isinstance(timestamp, str):
                                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                            else:
                                dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
                            
                            age_hours = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
                            print(f"   📅 Data Age: {age_hours:.1f} hours")
                            
                            if age_hours > 24:
                                print(f"   ⚠️  WARNING: Data is {age_hours:.1f} hours old (stale)")
                        except Exception as e:
                            print(f"   ❌ Error parsing timestamp: {e}")
                    
                    # Compare with expected prices
                    if isinstance(price, (int, float)):
                        real_ge_diff = price - expected['real_ge_price']
                        default_diff = price - expected['ge_default_price'] 
                        
                        print(f"   📈 Price Analysis:")
                        print(f"      vs Real GE: {real_ge_diff:+,} GP ({price/expected['real_ge_price']*100:.1f}% of real)")
                        print(f"      vs GE Default: {default_diff:+,} GP ({price/expected['ge_default_price']*100:.1f}% of default)")
                        
                        # Flag major discrepancies
                        if abs(real_ge_diff) > expected['real_ge_price'] * 2:  # More than 200% off
                            print(f"   🚨 MAJOR DISCREPANCY: API price is {abs(real_ge_diff):,} GP off real GE price!")
                        elif abs(real_ge_diff) > expected['real_ge_price'] * 0.5:  # More than 50% off
                            print(f"   ⚠️  Significant difference from real GE price")
                else:
                    print(f"   ❌ No data returned from WeirdGloop API")
                    
            except Exception as e:
                print(f"   💥 Error fetching from WeirdGloop: {e}")

async def check_processed_price_data():
    """Check how prices are processed through the multi-source client."""
    print("\n" + "=" * 80) 
    print("PROCESSED PRICE DATA ANALYSIS")
    print("=" * 80)
    
    async with MultiSourcePriceClient() as client:
        for item_id, expected in REAL_GE_PRICES.items():
            print(f"\n🔄 Processing {expected['name']} (ID: {item_id})")
            
            try:
                # Get processed price data
                price_data = await client.get_best_price_data(item_id)
                
                if price_data:
                    print(f"   📊 Processed Price Data:")
                    print(f"      High Price (buy): {price_data.high_price:,} GP")
                    print(f"      Low Price (sell): {price_data.low_price:,} GP") 
                    print(f"      Source: {price_data.source.value}")
                    print(f"      Quality: {price_data.quality.value}")
                    print(f"      Age: {price_data.age_hours:.1f} hours")
                    print(f"      Confidence: {price_data.confidence_score:.2f}")
                    
                    # This is the critical issue - both high and low are the same!
                    if price_data.high_price == price_data.low_price:
                        print(f"   ⚠️  ISSUE: High price equals low price - no bid/ask spread!")
                        print(f"       Real markets have spreads. This suggests mid-price data.")
                        
                    # Compare with real prices
                    real_diff = price_data.high_price - expected['real_ge_price'] 
                    print(f"   📈 vs Real GE: {real_diff:+,} GP ({price_data.high_price/expected['real_ge_price']*100:.1f}% of real)")
                    
                else:
                    print(f"   ❌ No processed data available")
                    
            except Exception as e:
                print(f"   💥 Error in price processing: {e}")

def check_database_stored_prices():
    """Check what prices are stored in the database."""
    print("\n" + "=" * 80)
    print("DATABASE STORED PRICES ANALYSIS") 
    print("=" * 80)
    
    for item_id, expected in REAL_GE_PRICES.items():
        print(f"\n💾 Database prices for {expected['name']} (ID: {item_id})")
        
        try:
            # Check if item exists
            item = Item.objects.filter(id=item_id).first()
            if not item:
                print(f"   ❌ Item not found in database")
                continue
                
            print(f"   📝 Item Name: {item.name}")
            
            # Check ProfitCalculation data
            profit_calc = ProfitCalculation.objects.filter(item_id=item_id).first()
            if profit_calc:
                print(f"   💰 Database Prices:")
                print(f"      Current Buy Price: {profit_calc.current_buy_price:,} GP" if profit_calc.current_buy_price else "      Current Buy Price: None")
                print(f"      Current Sell Price: {profit_calc.current_sell_price:,} GP" if profit_calc.current_sell_price else "      Current Sell Price: None")
                print(f"      Data Source: {profit_calc.data_source}")
                print(f"      Data Quality: {profit_calc.data_quality}")
                print(f"      Data Age: {profit_calc.data_age_hours:.1f} hours" if profit_calc.data_age_hours else "      Data Age: Unknown")
                print(f"      Last Updated: {profit_calc.last_updated}")
                
                # Compare stored price with real GE
                if profit_calc.current_buy_price:
                    stored_diff = profit_calc.current_buy_price - expected['real_ge_price']
                    print(f"   📊 Analysis:")
                    print(f"      vs Real GE: {stored_diff:+,} GP ({profit_calc.current_buy_price/expected['real_ge_price']*100:.1f}% of real)")
                    
                    if abs(stored_diff) > expected['real_ge_price'] * 10:  # More than 10x off
                        print(f"   🚨 EXTREME DISCREPANCY: Stored price is {abs(stored_diff):,} GP off!")
                    elif abs(stored_diff) > expected['real_ge_price'] * 2:  # More than 2x off  
                        print(f"   ⚠️  MAJOR DISCREPANCY: Stored price is significantly wrong")
            else:
                print(f"   ❌ No ProfitCalculation data found")
                
        except Exception as e:
            print(f"   💥 Database error: {e}")

def print_summary_and_recommendations():
    """Print summary of findings and recommendations."""
    print("\n" + "=" * 80)
    print("SUMMARY & RECOMMENDATIONS")  
    print("=" * 80)
    
    print(f"""
📋 KEY FINDINGS TO VERIFY:

1. 🔍 DATA SOURCE ACCURACY
   - Check if WeirdGloop API returns single prices vs bid/ask spreads
   - Verify if returned prices are current market prices vs historical averages
   - Look for data staleness (>24 hours old)

2. ⚙️  PROCESSING PIPELINE ISSUES  
   - Multi-source client maps single WeirdGloop price to both high/low
   - No bid/ask spread handling - assumes single market price
   - Database stores these as separate buy/sell prices incorrectly

3. 🎯 SPECIFIC DISCREPANCIES TO INVESTIGATE
   - User reports Strength potion(4) = 96 GP, but system likely shows 3,258 GP
   - User reports Magic potion(3) = 160 GP, but system likely shows 1,009 GP  
   - These are 30-60x price differences!

4. 🛠️  IMMEDIATE FIXES NEEDED
   - Add price sanity checks (reject prices >10x expected ranges)  
   - Implement data freshness validation (reject stale data)
   - Fix price interpretation in processing pipeline
   - Add real-time price validation against known ranges
   
5. 📊 TESTING PLAN
   - Compare diagnostic output with user's real GE observations
   - Verify if API data is actually wrong vs processing errors
   - Test with additional items beyond the reported ones
""")

async def main():
    """Run comprehensive price data diagnostics."""
    print("🧹 OSRS PRICE DATA DIAGNOSTIC TOOL")
    print(f"📅 Run Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 Testing {len(REAL_GE_PRICES)} items with known real GE prices")
    
    # Run all diagnostic checks
    await check_weirdgloop_raw_data()
    await check_processed_price_data()  
    check_database_stored_prices()
    print_summary_and_recommendations()
    
    print(f"\n✅ Diagnostic complete. Use this data to identify and fix price issues.")

if __name__ == '__main__':
    asyncio.run(main())