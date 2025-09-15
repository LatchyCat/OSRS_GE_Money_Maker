#!/usr/bin/env python
"""
Script to clear old broken decanting records and regenerate with fixed calculations
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'osrs_tracker.settings')
sys.path.append('/Users/latchy/high_alch_item_recommender/backend')
django.setup()

from apps.trading_strategies.models import DecantingOpportunity, TradingStrategy, StrategyType
from apps.trading_strategies.services.decanting_detector import DecantingDetector

def clear_old_records():
    """Clear all existing decanting records with broken calculations"""
    print("=== CLEARING OLD DECANTING RECORDS ===")
    
    # Count existing records
    decanting_count = DecantingOpportunity.objects.count()
    strategy_count = TradingStrategy.objects.filter(strategy_type=StrategyType.DECANTING).count()
    
    print(f"Found {decanting_count} DecantingOpportunity records")
    print(f"Found {strategy_count} TradingStrategy records for decanting")
    
    # Delete DecantingOpportunity records (this will cascade delete related TradingStrategy records)
    deleted_opps = DecantingOpportunity.objects.all().delete()
    print(f"Deleted DecantingOpportunity records: {deleted_opps}")
    
    # Delete any remaining TradingStrategy records for decanting
    deleted_strategies = TradingStrategy.objects.filter(strategy_type=StrategyType.DECANTING).delete()
    print(f"Deleted TradingStrategy records: {deleted_strategies}")
    
    print("✅ Old records cleared successfully")

def regenerate_opportunities():
    """Generate new opportunities using the fixed calculation logic"""
    print("\n=== REGENERATING DECANTING OPPORTUNITIES ===")
    
    # Initialize the fixed detector with reasonable thresholds
    detector = DecantingDetector(min_profit_gp=10, min_profit_margin=0.05)  # 10 GP min, 5% margin min
    
    # Get the opportunities using fixed logic (this only calculates, doesn't save to DB)
    opportunities = detector.detect_opportunities()
    print(f"Fixed detector found {len(opportunities)} valid opportunities")
    
    if opportunities:
        # Show sample opportunities
        print("\nTop 5 opportunities from fixed calculator:")
        for i, opp in enumerate(opportunities[:5], 1):
            print(f"{i}. {opp['potion_name']} {opp['from_dose']}→{opp['potions_gained']}x{opp['to_dose']}: {opp['profit_per_conversion']:,} GP")
        
        # Now use the method that saves to database
        created_count = detector.scan_and_create_opportunities()
        print(f"\n✅ Created {created_count} new database records")
    else:
        print("⚠️  No opportunities found with current thresholds")
    
    return opportunities

def verify_database():
    """Verify the new database records are realistic"""
    print("\n=== VERIFYING DATABASE RECORDS ===")
    
    # Check DecantingOpportunity records
    new_opps = DecantingOpportunity.objects.all()
    print(f"Total DecantingOpportunity records: {new_opps.count()}")
    
    if new_opps.count() > 0:
        print("\nSample of new records:")
        for opp in new_opps[:5]:
            print(f"- {opp.item_name} {opp.from_dose}→{opp.to_dose}: {opp.profit_per_conversion:,} GP "
                  f"(buy: {opp.from_dose_price:,}, sell: {opp.to_dose_price:,})")
            
            # Check for unrealistic values
            if opp.profit_per_conversion > 50000:  # 50k GP is very high for decanting
                print(f"  ⚠️  High profit detected: {opp.profit_per_conversion:,} GP")
            if opp.from_dose_price > 50000 or opp.to_dose_price > 50000:
                print(f"  ⚠️  High prices detected: buy {opp.from_dose_price:,}, sell {opp.to_dose_price:,}")
        
        # Check TradingStrategy records
        strategy_count = TradingStrategy.objects.filter(strategy_type=StrategyType.DECANTING).count()
        print(f"\nTotal TradingStrategy records for decanting: {strategy_count}")
        
        if strategy_count > 0:
            high_profit_strategies = TradingStrategy.objects.filter(
                strategy_type=StrategyType.DECANTING,
                potential_profit_gp__gt=50000
            )
            if high_profit_strategies.exists():
                print(f"⚠️  Found {high_profit_strategies.count()} strategies with >50k GP profit")
        
        print("✅ Database verification complete")
    else:
        print("❌ No records found in database")

def main():
    """Main execution function"""
    print("🧹 DECANTING DATABASE CLEANUP & REGENERATION")
    print("=" * 50)
    
    # Step 1: Clear old broken records
    clear_old_records()
    
    # Step 2: Regenerate with fixed logic
    opportunities = regenerate_opportunities()
    
    # Step 3: Verify new records
    verify_database()
    
    print("\n" + "=" * 50)
    print("✅ CLEANUP & REGENERATION COMPLETE")
    
    if opportunities and len(opportunities) > 0:
        print(f"Frontend should now display {len(opportunities)} realistic opportunities")
        print("Expected profit ranges: 10-10,000 GP per conversion")
        print("Expected margins: 5%-1000%")
    else:
        print("⚠️  No opportunities generated - check price data quality")

if __name__ == '__main__':
    main()