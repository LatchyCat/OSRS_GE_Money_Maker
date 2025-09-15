#!/usr/bin/env python
"""
Test script for the Universal Opportunity Scanner
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'osrs_tracker.settings')
sys.path.append('/Users/latchy/high_alch_item_recommender/backend')
django.setup()

from apps.trading_strategies.services.universal_opportunity_scanner import UniversalOpportunityScanner

def test_universal_scanner():
    print('Testing Universal Opportunity Scanner...')
    scanner = UniversalOpportunityScanner(min_profit_gp=500)  # Lower threshold for testing

    # Run the scan
    print('Running comprehensive opportunity scan...')
    results = scanner.scan_all_opportunities()

    # Print summary
    print(f'\n=== SCAN RESULTS ===')
    for strategy_type, opportunities in results.items():
        if strategy_type != 'cross_strategy_analysis':
            print(f'{strategy_type}: {len(opportunities)} opportunities')
            if opportunities:
                best = opportunities[0]  # Best opportunity (sorted by profit)
                print(f'  Best: {best.get("item_name")} - {best.get("profit_gp", 0):,} GP profit')

    cross_strategy = results.get('cross_strategy_analysis', [])
    print(f'\nItems with multiple strategies: {len(cross_strategy)}')
    if cross_strategy:
        print('Top 3 multi-strategy items:')
        for i, item in enumerate(cross_strategy[:3]):
            strategies = item.get('strategies', [])
            best_profit = item.get('best_profit', 0)
            item_name = item.get('item_name', 'Unknown')
            print(f'  {i+1}. {item_name} - {len(strategies)} strategies, best: {best_profit:,} GP')
            for strategy in strategies:
                strategy_type = strategy.get('type', 'unknown')
                profit = strategy.get('profit_gp', 0)
                print(f'     - {strategy_type}: {profit:,} GP')

    print('\n=== SCAN COMPLETE ===')
    return results

if __name__ == '__main__':
    test_universal_scanner()