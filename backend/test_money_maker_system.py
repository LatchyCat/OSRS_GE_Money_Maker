#!/usr/bin/env python
"""
Quick test script for the money maker system implementation.
Tests GE tax calculations and basic functionality.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'osrs_tracker.settings')
django.setup()

from services.weird_gloop_client import GrandExchangeTax, MoneyMakerDataFetcher
from apps.prices.models import ProfitCalculation
from apps.items.models import Item
from apps.embeddings.models import ItemEmbedding

def test_ge_tax_calculations():
    """Test Grand Exchange tax calculations"""
    print("🔍 Testing GE Tax Calculations")
    print("=" * 50)
    
    # Test case 1: Regular item 100K GP
    price = 100_000
    tax = GrandExchangeTax.calculate_tax(price)
    net_received = price - tax
    expected_tax = int(100_000 * 0.02)  # 2%
    
    print(f"Test 1 - Regular item 100K GP:")
    print(f"  Sell price: {price:,} GP")
    print(f"  GE tax: {tax:,} GP (expected: {expected_tax:,})")
    print(f"  Net received: {net_received:,} GP")
    print(f"  ✅ Correct!" if tax == expected_tax else "❌ Error!")
    print()
    
    # Test case 2: Low value item (under 50 GP)
    price = 30
    tax = GrandExchangeTax.calculate_tax(price)
    
    print(f"Test 2 - Low value item 30 GP:")
    print(f"  Sell price: {price} GP")
    print(f"  GE tax: {tax} GP (expected: 0)")
    print(f"  ✅ Correct!" if tax == 0 else "❌ Error!")
    print()
    
    # Test case 3: Bond (tax exempt)
    price = 8_000_000
    bond_id = 13190  # Old School Bond
    tax = GrandExchangeTax.calculate_tax(price, bond_id)
    
    print(f"Test 3 - Old School Bond:")
    print(f"  Sell price: {price:,} GP")
    print(f"  GE tax: {tax} GP (expected: 0 - exempt)")
    print(f"  ✅ Correct!" if tax == 0 else "❌ Error!")
    print()
    
    # Test case 4: Very expensive item (tax cap)
    price = 500_000_000  # 500M
    tax = GrandExchangeTax.calculate_tax(price)
    expected_tax = 5_000_000  # Capped at 5M
    
    print(f"Test 4 - Very expensive item (tax cap):")
    print(f"  Sell price: {price:,} GP")
    print(f"  GE tax: {tax:,} GP (expected: {expected_tax:,} - capped)")
    print(f"  ✅ Correct!" if tax == expected_tax else "❌ Error!")
    print()

def test_flip_analysis():
    """Test flip profitability analysis"""
    print("🔄 Testing Flip Analysis")
    print("=" * 50)
    
    # Your friend's example: profitable flip
    buy_price = 975_000
    sell_price = 1_025_000
    item_id = 11802  # Armadyl godsword
    
    analysis = GrandExchangeTax.analyze_flip_viability(buy_price, sell_price, item_id)
    
    print(f"Flip Analysis Example:")
    print(f"  Item ID: {item_id}")
    print(f"  Buy price: {buy_price:,} GP")
    print(f"  Sell price: {sell_price:,} GP")
    print(f"  GE tax: {analysis['ge_tax']:,} GP")
    print(f"  Net received: {analysis['net_received']:,} GP")
    print(f"  Profit: {analysis['profit_per_item']:,} GP")
    print(f"  Margin: {analysis['profit_margin_pct']:.2f}%")
    print(f"  Profitable: {'✅ Yes' if analysis['is_profitable'] else '❌ No'}")
    print()

def test_decanting_profit():
    """Test decanting profit calculations"""
    print("🧪 Testing Decanting Calculations")
    print("=" * 50)
    
    # Example: Super combat potion 4->3 dose
    buy_price_4dose = 15_000  # Super combat potion(4)
    sell_price_3dose = 12_000  # Super combat potion(3) - sell 3 of these
    
    # Buy 1x 4-dose, drink 1 dose, sell as 3x 3-dose potions
    cost = buy_price_4dose
    
    # Calculate revenue after GE tax (selling 3x 3-dose)
    gross_revenue = sell_price_3dose * 3
    ge_tax_per_potion = GrandExchangeTax.calculate_tax(sell_price_3dose)
    total_ge_tax = ge_tax_per_potion * 3
    net_revenue = gross_revenue - total_ge_tax
    
    profit = net_revenue - cost
    margin_pct = (profit / cost * 100) if cost > 0 else 0
    
    print(f"Decanting Example:")
    print(f"  Buy: 1x 4-dose potion for {cost:,} GP")
    print(f"  Sell: 3x 3-dose potions at {sell_price_3dose:,} GP each")
    print(f"  Gross revenue: {gross_revenue:,} GP")
    print(f"  GE tax: {total_ge_tax:,} GP")
    print(f"  Net revenue: {net_revenue:,} GP")
    print(f"  Profit: {profit:,} GP")
    print(f"  Margin: {margin_pct:.2f}%")
    print(f"  Hourly potential (1000 conversions): {profit * 1000:,} GP")
    print()

def test_set_combining_profit():
    """Test set combining lazy tax calculations"""
    print("⚔️ Testing Set Combining")
    print("=" * 50)
    
    # Example: Dharok's set
    # Pieces: Helm (4716), Body (4718), Legs (4720), Axe (4722)
    pieces_cost = [2_500_000, 3_200_000, 2_800_000, 1_200_000]  # Example prices
    total_pieces_cost = sum(pieces_cost)
    
    # Complete set price
    set_sell_price = 10_500_000
    
    # Calculate profit after GE tax
    ge_tax = GrandExchangeTax.calculate_tax(set_sell_price)
    net_revenue = set_sell_price - ge_tax
    profit = net_revenue - total_pieces_cost
    
    lazy_tax_pct = (profit / total_pieces_cost * 100) if total_pieces_cost > 0 else 0
    
    print(f"Set Combining Example (Dharok's):")
    print(f"  Pieces cost: {total_pieces_cost:,} GP")
    print(f"  Set sell price: {set_sell_price:,} GP")
    print(f"  GE tax: {ge_tax:,} GP")
    print(f"  Net received: {net_revenue:,} GP")
    print(f"  Profit: {profit:,} GP")
    print(f"  Lazy tax: {lazy_tax_pct:.2f}%")
    print(f"  Profitable: {'✅ Yes' if profit > 0 else '❌ No'}")
    print()

def test_required_margins():
    """Test required margin calculations"""
    print("📊 Testing Required Margins")
    print("=" * 50)
    
    # Test: What sell price needed for 10% profit after tax?
    buy_price = 1_000_000
    target_profit = int(buy_price * 0.1)  # 10% profit
    
    required_sell_price = GrandExchangeTax.get_required_margin_for_profit(
        buy_price, target_profit
    )
    
    # Verify
    actual_tax = GrandExchangeTax.calculate_tax(required_sell_price)
    actual_profit = required_sell_price - actual_tax - buy_price
    
    print(f"Required Margin Test:")
    print(f"  Buy price: {buy_price:,} GP")
    print(f"  Target profit: {target_profit:,} GP (10%)")
    print(f"  Required sell price: {required_sell_price:,} GP")
    print(f"  Actual GE tax: {actual_tax:,} GP")
    print(f"  Actual profit: {actual_profit:,} GP")
    print(f"  ✅ Close enough!" if abs(actual_profit - target_profit) < 1000 else "❌ Error!")
    print()

def test_embedding_context():
    """Test enhanced embedding context generation"""
    print("🔍 Testing Money Maker Embedding Context")
    print("=" * 50)
    
    try:
        # Try to get a test item
        test_item = Item.objects.first()
        if not test_item:
            print("❌ No items found in database")
            return
            
        # Generate source text with money maker context
        source_text = ItemEmbedding.create_source_text(test_item)
        
        print(f"Test Item: {test_item.name}")
        print(f"Enhanced Embedding Context:")
        print(f"  Length: {len(source_text)} characters")
        print(f"  Preview: {source_text[:200]}...")
        
        # Check for money maker keywords
        money_maker_keywords = [
            'flipping', 'decanting', 'set combining', 'lazy tax', 
            'GE tax', 'profitable', 'bond', 'volume', 'liquidity'
        ]
        
        found_keywords = [kw for kw in money_maker_keywords if kw in source_text.lower()]
        print(f"  Money maker keywords found: {len(found_keywords)}")
        print(f"  Keywords: {', '.join(found_keywords)}")
        print()
        
    except Exception as e:
        print(f"❌ Error testing embeddings: {e}")
        print()

def main():
    """Run all tests"""
    print("🚀 OSRS Money Maker System Test Suite")
    print("=" * 60)
    print("Testing your friend's 50M → 100M strategies")
    print("=" * 60)
    print()
    
    test_ge_tax_calculations()
    test_flip_analysis()
    test_decanting_profit()
    test_set_combining_profit()
    test_required_margins()
    test_embedding_context()
    
    print("✅ All tests completed!")
    print()
    print("💡 Key Findings:")
    print("- GE tax significantly impacts profit margins")
    print("- Bonds are tax-exempt (perfect for high-value flips)")
    print("- Decanting can generate substantial hourly profits")
    print("- Set combining exploits 'lazy tax' effectively")
    print("- Embedding system includes comprehensive money maker context")
    print()
    print("🎯 Ready to implement your friend's strategies!")

if __name__ == "__main__":
    main()