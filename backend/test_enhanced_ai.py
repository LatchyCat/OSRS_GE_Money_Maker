#!/usr/bin/env python3
"""
Test the enhanced AI system to validate improvements:
1. Magic items, resources, and potions can be found
2. Million+ margin opportunities are detected
3. Capital-aware recommendations work
"""

import os
import sys
import django
import asyncio
from pathlib import Path

sys.path.append('/Users/latchy/high_alch_item_recommender/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'osrs_tracker.settings')
django.setup()

import logging
from services.merchant_ai_agent import MerchantAIAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_enhanced_ai():
    """Test the enhanced AI system with various scenarios."""
    
    agent = MerchantAIAgent()
    
    # Test scenarios that were previously failing
    test_cases = [
        {
            'query': 'find me profitable magic items to flip',
            'capital': 100_000,
            'description': 'Magic items detection test'
        },
        {
            'query': 'nature runes trading opportunities', 
            'capital': 50_000,
            'description': 'Nature runes specific test'
        },
        {
            'query': 'show me million gp margin flips',
            'capital': 10_000_000, 
            'description': 'Million+ margin opportunities test'
        },
        {
            'query': 'profitable resources and materials',
            'capital': 200_000,
            'description': 'Resources detection test'
        },
        {
            'query': 'best potions to flip for profit',
            'capital': 150_000,
            'description': 'Potions trading test'
        },
        {
            'query': 'turn 1m into 2m gp strategies',
            'capital': 1_000_000,
            'description': 'Capital growth strategy test'
        }
    ]
    
    print("🚀 Testing Enhanced AI Trading Assistant")
    print("=" * 60)
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n📋 Test {i}: {test['description']}")
        print(f"Query: '{test['query']}'")
        print(f"Capital: {test['capital']:,} GP")
        print("-" * 40)
        
        try:
            # Process query with enhanced AI
            result = await agent.process_query(
                query=test['query'],
                user_id="test_user",
                capital_gp=test['capital']
            )
            
            # Extract key results
            response = result.get('response', '')
            query_type = result.get('query_type', 'unknown')
            opportunities = result.get('precision_opportunities', [])
            million_opportunities = result.get('million_margin_opportunities', [])
            tier_opportunities = result.get('tier_opportunities', [])
            
            print(f"✅ Query Type: {query_type}")
            print(f"📊 Precision Opportunities: {len(opportunities)}")
            
            if million_opportunities:
                print(f"💎 Million+ Margin Opportunities: {len(million_opportunities)}")
                
            if tier_opportunities:
                print(f"🎯 Tier Opportunities: {len(tier_opportunities)}")
            
            # Show response preview
            response_preview = response[:200] + "..." if len(response) > 200 else response
            print(f"🤖 AI Response Preview:")
            print(response_preview)
            
            # Success indicators
            if 'No opportunities found' in response or 'No significant opportunities' in response:
                print("⚠️  WARNING: No opportunities detected")
            elif len(opportunities) > 0 or len(million_opportunities) > 0 or len(tier_opportunities) > 0:
                print("🎉 SUCCESS: Opportunities detected!")
            else:
                print("ℹ️  Partial success - response generated but no structured opportunities")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
            logger.error(f"Test {i} failed: {e}")
        
        print("-" * 40)
    
    print(f"\n🏁 Enhanced AI Testing Complete!")
    print("Check the results above to validate:")
    print("• Magic items can be found ✓")
    print("• Resources and potions are detected ✓")
    print("• Million+ margin opportunities work ✓")
    print("• Capital-aware recommendations function ✓")

if __name__ == "__main__":
    asyncio.run(test_enhanced_ai())