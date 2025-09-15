#!/usr/bin/env python3
"""
Simplified test script for the reactive trading system.
This version focuses on testing the key components without dependencies.
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'osrs_tracker.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    django.setup()
    print("✅ Django setup completed successfully")
except Exception as e:
    print(f"❌ Django setup failed: {e}")
    sys.exit(1)

def test_imports():
    """Test that all our new services can be imported."""
    print("\n🔍 Testing imports...")
    
    try:
        from services.reactive_trading_engine import ReactiveTradingEngine
        print("✅ ReactiveTradingEngine imported")
    except Exception as e:
        print(f"❌ ReactiveTradingEngine import failed: {e}")
    
    try:
        from services.price_pattern_analysis_service import PricePatternAnalysisService
        print("✅ PricePatternAnalysisService imported")
    except Exception as e:
        print(f"❌ PricePatternAnalysisService import failed: {e}")
    
    try:
        from services.unified_data_ingestion_service import UnifiedDataIngestionService
        print("✅ UnifiedDataIngestionService imported")
    except Exception as e:
        print(f"❌ UnifiedDataIngestionService import failed: {e}")
    
    try:
        from apps.prices.consumers import TradingIntelligenceConsumer, PriceChartsConsumer
        print("✅ WebSocket consumers imported")
    except Exception as e:
        print(f"❌ WebSocket consumers import failed: {e}")

def test_engine_initialization():
    """Test that the reactive engine can be initialized."""
    print("\n🚀 Testing engine initialization...")
    
    try:
        from services.reactive_trading_engine import ReactiveTradingEngine
        
        config = {
            'monitoring_interval': 10,
            'pattern_analysis_interval': 30,
            'recommendation_update_interval': 60,
            'volume_surge_threshold': 2.0,
            'test_mode': True
        }
        
        engine = ReactiveTradingEngine(config)
        
        # Test basic properties
        assert hasattr(engine, 'config'), "Engine missing config attribute"
        assert hasattr(engine, 'task_scheduler'), "Engine missing task_scheduler attribute"
        assert engine.config['test_mode'] == True, "Test mode not properly set"
        
        print("✅ ReactiveTrading Engine initialized successfully")
        print(f"   Configuration: {engine.config}")
        
    except Exception as e:
        print(f"❌ Engine initialization failed: {e}")

def test_management_commands():
    """Test that our management commands are available."""
    print("\n📋 Testing management commands...")
    
    try:
        from django.core.management import get_commands
        available_commands = get_commands()
        
        required_commands = [
            'start_reactive_engine',
            'analyze_price_patterns',
            'ingest_historical_data'
        ]
        
        for cmd in required_commands:
            if cmd in available_commands:
                print(f"✅ {cmd} command available")
            else:
                print(f"❌ {cmd} command not found")
        
    except Exception as e:
        print(f"❌ Management commands test failed: {e}")

def test_websocket_routing():
    """Test that WebSocket routing is properly configured."""
    print("\n🔌 Testing WebSocket routing...")
    
    try:
        from osrs_tracker.routing import websocket_urlpatterns
        
        # Check that our routes are registered
        route_patterns = [str(pattern.pattern) for pattern in websocket_urlpatterns]
        
        trading_route_found = any('trading' in pattern for pattern in route_patterns)
        charts_route_found = any('charts' in pattern for pattern in route_patterns)
        
        if trading_route_found:
            print("✅ Trading WebSocket route found")
        else:
            print("❌ Trading WebSocket route not found")
            
        if charts_route_found:
            print("✅ Charts WebSocket route found") 
        else:
            print("❌ Charts WebSocket route not found")
        
        print(f"   Total WebSocket routes: {len(websocket_urlpatterns)}")
        
    except Exception as e:
        print(f"❌ WebSocket routing test failed: {e}")

def test_frontend_components():
    """Test that frontend components exist."""
    print("\n⚛️  Testing frontend components...")
    
    frontend_files = [
        "/Users/latchy/high_alch_item_recommender/frontend/src/hooks/useReactiveTradingSocket.ts",
        "/Users/latchy/high_alch_item_recommender/frontend/src/components/trading/RealtimePriceChart.tsx",
        "/Users/latchy/high_alch_item_recommender/frontend/src/components/trading/ReactiveTradingDashboard.tsx",
        "/Users/latchy/high_alch_item_recommender/frontend/src/components/trading/ReactiveTradingPage.tsx"
    ]
    
    for file_path in frontend_files:
        if os.path.exists(file_path):
            print(f"✅ {os.path.basename(file_path)} exists")
        else:
            print(f"❌ {os.path.basename(file_path)} missing")

def main():
    """Run all simplified tests."""
    print("🎯 SIMPLIFIED REACTIVE TRADING SYSTEM TESTS")
    print("=" * 60)
    
    test_imports()
    test_engine_initialization()
    test_management_commands()
    test_websocket_routing()
    test_frontend_components()
    
    print("\n" + "=" * 60)
    print("🏁 SIMPLIFIED TESTS COMPLETED")
    print("\n💡 Next Steps:")
    print("   1. Fix any failing tests above")
    print("   2. Run database migrations: python manage.py migrate")
    print("   3. Run full test: python test_reactive_system.py") 
    print("   4. Start reactive engine: python manage.py start_reactive_engine --test-mode")

if __name__ == "__main__":
    main()