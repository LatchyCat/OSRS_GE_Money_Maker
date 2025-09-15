#!/usr/bin/env python3
"""
Test script for Merchant AI API endpoints.
"""

import requests
import json
import time

# Configuration
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1/merchant"

def test_merchant_chat():
    """Test the AI chat endpoint."""
    print("🤖 Testing Merchant AI Chat...")
    
    test_queries = [
        "What are the best items to flip right now?",
        "Tell me about dragon bones price trends",
        "Should I buy trailblazer trousers at 700k each?",
        "What items have high volume and good profit margins?",
        "Compare dragon bones to big bones for profit",
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n📝 Test {i}: {query}")
        
        payload = {
            "query": query,
            "user_id": "test_user_123",
            "include_context": True
        }
        
        try:
            response = requests.post(
                f"{API_BASE}/chat/",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Response: {data['response'][:200]}...")
                print(f"📊 Query Type: {data.get('query_type', 'unknown')}")
                print(f"🎯 Entities: {data.get('entities', [])}")
                print(f"⏱️  Response Time: {data.get('metadata', {}).get('response_time_ms', 0)}ms")
            else:
                print(f"❌ Error {response.status_code}: {response.text}")
                
        except Exception as e:
            print(f"❌ Exception: {e}")
        
        time.sleep(1)  # Rate limiting

def test_market_opportunities():
    """Test the market opportunities endpoint."""
    print("\n\n💰 Testing Market Opportunities...")
    
    try:
        response = requests.get(
            f"{API_BASE}/opportunities/",
            params={
                "risk_levels": "conservative,moderate",
                "min_profit": 100,
                "limit": 5
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Found {data['total']} opportunities")
            for opp in data['opportunities'][:3]:
                print(f"  📈 {opp['item_name']}: {opp['projected_profit_per_item']}GP profit ({opp['risk_level']})")
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

def test_market_overview():
    """Test the market overview endpoint."""
    print("\n\n📊 Testing Market Overview...")
    
    try:
        response = requests.get(f"{API_BASE}/overview/")
        
        if response.status_code == 200:
            data = response.json()
            overview = data['market_overview']
            print(f"✅ Market Overview:")
            print(f"  📊 Active Opportunities: {overview['total_active_opportunities']}")
            print(f"  💰 Max Profit Opportunity: {overview['max_profit_opportunity']}GP")
            print(f"  📈 Average Profit: {overview['average_projected_profit']}GP")
            print(f"  📊 Items Analyzed (24h): {overview['items_analyzed_24h']}")
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

def test_analyze_opportunities():
    """Test the opportunity analysis trigger."""
    print("\n\n🔍 Testing Market Analysis...")
    
    try:
        payload = {
            "risk_levels": ["conservative", "moderate"],
            "min_profit": 200,
            "max_results": 10
        }
        
        response = requests.post(
            f"{API_BASE}/opportunities/analyze/",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ {data['message']}")
            print(f"📊 Found {len(data['opportunities'])} opportunities")
            for opp in data['opportunities'][:3]:
                print(f"  💡 {opp['item_name']}: {opp['projected_profit']}GP ({opp['opportunity_type']})")
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

def main():
    """Run all tests."""
    print("🚀 OSRS Merchant API Test Suite")
    print("=" * 50)
    
    try:
        # Test basic connectivity
        response = requests.get(f"{BASE_URL}/health/", timeout=5)
        print(f"✅ Server is running (Health check: {response.status_code})")
    except Exception as e:
        print(f"❌ Server not accessible: {e}")
        return
    
    # Run tests
    test_market_opportunities()
    test_market_overview()
    test_analyze_opportunities()
    test_merchant_chat()
    
    print("\n\n🎉 Test suite completed!")

if __name__ == "__main__":
    main()