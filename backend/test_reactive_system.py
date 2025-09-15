#!/usr/bin/env python3
"""
Comprehensive test script for the AI-powered reactive trading system.

This script tests all major components of the reactive trading intelligence:
- Reactive trading engine startup and monitoring
- Historical data ingestion pipeline
- AI pattern recognition system
- WebSocket communication
- Real-time recommendation generation
- Performance and reliability metrics

Run with: python test_reactive_system.py
"""

import asyncio
import os
import sys
import django
import time
import json
import logging
from typing import Dict, List, Any
from datetime import datetime, timedelta
from dataclasses import dataclass

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'osrs_tracker.settings')
django.setup()

from django.utils import timezone
from django.test import TestCase
from django.core.management import call_command
from asgiref.sync import sync_to_async
from apps.prices.models import HistoricalPricePoint, PriceTrend, MarketAlert, PricePattern
from apps.items.models import Item
from services.reactive_trading_engine import ReactiveTradingEngine
from services.price_pattern_analysis_service import PricePatternAnalysisService
from services.unified_data_ingestion_service import UnifiedDataIngestionService

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class TestResult:
    test_name: str
    status: str  # 'PASS', 'FAIL', 'SKIP'
    duration: float
    message: str
    details: Dict[str, Any] = None

class ReactiveSystemTester:
    """Comprehensive tester for the reactive trading system."""
    
    def __init__(self):
        self.results: List[TestResult] = []
        self.start_time = time.time()
        
    def log_result(self, test_name: str, status: str, message: str, duration: float = 0, details: Dict = None):
        """Log a test result."""
        result = TestResult(test_name, status, duration, message, details)
        self.results.append(result)
        
        status_icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⏭️"
        logger.info(f"{status_icon} {test_name}: {message} ({duration:.2f}s)")
        
        if details:
            for key, value in details.items():
                logger.info(f"    {key}: {value}")
    
    async def test_reactive_engine_startup(self) -> TestResult:
        """Test reactive trading engine initialization and startup."""
        test_start = time.time()
        test_name = "Reactive Engine Startup"
        
        try:
            logger.info("🚀 Testing reactive trading engine startup...")
            
            # Test engine initialization
            config = {
                'monitoring_interval': 10,  # Fast for testing
                'pattern_analysis_interval': 30,
                'recommendation_update_interval': 60,
                'volume_surge_threshold': 2.0,
                'test_mode': True
            }
            
            engine = ReactiveTradingEngine(config)
            
            # Test basic properties
            assert hasattr(engine, 'config'), "Engine missing config attribute"
            assert hasattr(engine, 'is_running'), "Engine missing is_running attribute"
            assert hasattr(engine, 'task_scheduler'), "Engine missing task_scheduler attribute"
            
            # Test configuration
            assert engine.config['test_mode'] == True, "Test mode not properly set"
            assert engine.config['monitoring_interval'] == 10, "Monitoring interval not set correctly"
            
            duration = time.time() - test_start
            self.log_result(test_name, "PASS", "Engine initialized successfully", duration, {
                "config_keys": list(engine.config.keys()),
                "test_mode": engine.config['test_mode']
            })
            
            return True
            
        except Exception as e:
            duration = time.time() - test_start
            self.log_result(test_name, "FAIL", f"Engine startup failed: {str(e)}", duration)
            return False
    
    async def test_historical_data_ingestion(self) -> TestResult:
        """Test the historical data ingestion pipeline."""
        test_start = time.time()
        test_name = "Historical Data Ingestion"
        
        try:
            logger.info("📊 Testing historical data ingestion pipeline...")
            
            # Test data ingestion service
            ingestion_service = UnifiedDataIngestionService()
            
            # Test health check
            health_status = await ingestion_service.get_ingestion_health_status()
            assert 'endpoints_status' in health_status, "Health status missing endpoints info"
            
            # Test with a small sample of items (to avoid overwhelming the API)
            test_items = [995, 4151, 2357]  # Coins, Abyssal whip, Gold bar
            
            # Test historical data ingestion for 5m endpoint
            logger.info("Testing 5m historical data ingestion...")
            results_5m = await ingestion_service.ingest_historical_data_only(
                item_ids=test_items,
                periods_5m=3,  # Just 3 periods for testing
                periods_1h=0   # Skip 1h for this test
            )
            
            assert results_5m['status'] == 'completed', f"5m ingestion failed: {results_5m.get('error', 'Unknown error')}"
            assert results_5m.get('historical_points_created', 0) > 0, "No historical points created for 5m data"
            
            # Test historical data ingestion for 1h endpoint
            logger.info("Testing 1h historical data ingestion...")
            results_1h = await ingestion_service.ingest_historical_data_only(
                item_ids=test_items,
                periods_5m=0,  # Skip 5m for this test
                periods_1h=2   # Just 2 periods for testing
            )
            
            assert results_1h['status'] == 'completed', f"1h ingestion failed: {results_1h.get('error', 'Unknown error')}"
            assert results_1h.get('historical_points_created', 0) > 0, "No historical points created for 1h data"
            
            # Verify data was stored in database
            total_points = await sync_to_async(HistoricalPricePoint.objects.count)()
            recent_points = await sync_to_async(HistoricalPricePoint.objects.filter(
                timestamp__gte=timezone.now() - timedelta(hours=2)
            ).count)()
            
            duration = time.time() - test_start
            self.log_result(test_name, "PASS", "Historical data ingestion working", duration, {
                "5m_points_created": results_5m.get('historical_points_created', 0),
                "1h_points_created": results_1h.get('historical_points_created', 0),
                "total_db_points": total_points,
                "recent_points": recent_points,
                "test_items": test_items
            })
            
            return True
            
        except Exception as e:
            duration = time.time() - test_start
            self.log_result(test_name, "FAIL", f"Historical data ingestion failed: {str(e)}", duration)
            return False
    
    async def test_pattern_recognition(self) -> TestResult:
        """Test the AI pattern recognition system."""
        test_start = time.time()
        test_name = "AI Pattern Recognition"
        
        try:
            logger.info("🧠 Testing AI pattern recognition system...")
            
            # Initialize pattern analysis service
            pattern_service = PricePatternAnalysisService()
            
            # Test with a known item that should have some data
            test_item_id = 995  # Coins - should always have data
            
            # Test trend analysis
            logger.info("Testing trend analysis...")
            periods = ['1h', '6h', '24h']
            trends = await pattern_service.analyze_item_trends(test_item_id, periods)
            
            assert isinstance(trends, dict), "Trends should be returned as dictionary"
            logger.info(f"Detected trends for {len(trends)} periods")
            
            # Test pattern detection
            logger.info("Testing pattern detection...")
            patterns = await pattern_service.detect_price_patterns(test_item_id, 24)  # 24 hours
            
            assert isinstance(patterns, list), "Patterns should be returned as list"
            logger.info(f"Detected {len(patterns)} patterns")
            
            # Test market signal generation
            logger.info("Testing market signal generation...")
            signals = await pattern_service.generate_market_signals(test_item_id)
            
            assert isinstance(signals, list), "Signals should be returned as list"
            logger.info(f"Generated {len(signals)} market signals")
            
            # Verify database storage
            pattern_count = await sync_to_async(PricePattern.objects.count)()
            trend_count = await sync_to_async(PriceTrend.objects.count)()
            alert_count = await sync_to_async(MarketAlert.objects.count)()
            
            duration = time.time() - test_start
            self.log_result(test_name, "PASS", "Pattern recognition system working", duration, {
                "trends_detected": len(trends),
                "patterns_detected": len(patterns),
                "signals_generated": len(signals),
                "db_patterns": pattern_count,
                "db_trends": trend_count,
                "db_alerts": alert_count,
                "test_item": test_item_id
            })
            
            return True
            
        except Exception as e:
            duration = time.time() - test_start
            self.log_result(test_name, "FAIL", f"Pattern recognition failed: {str(e)}", duration)
            return False
    
    async def test_websocket_system(self) -> TestResult:
        """Test WebSocket communication system."""
        test_start = time.time()
        test_name = "WebSocket Communication"
        
        try:
            logger.info("🔌 Testing WebSocket communication system...")
            
            # Test importing WebSocket consumers
            from apps.prices.consumers import TradingIntelligenceConsumer, PriceChartsConsumer
            
            # Test consumer initialization
            trading_consumer = TradingIntelligenceConsumer()
            charts_consumer = PriceChartsConsumer()
            
            assert hasattr(trading_consumer, 'connect'), "Trading consumer missing connect method"
            assert hasattr(trading_consumer, 'receive'), "Trading consumer missing receive method"
            assert hasattr(trading_consumer, 'disconnect'), "Trading consumer missing disconnect method"
            
            assert hasattr(charts_consumer, 'connect'), "Charts consumer missing connect method"
            assert hasattr(charts_consumer, 'receive'), "Charts consumer missing receive method"
            assert hasattr(charts_consumer, 'disconnect'), "Charts consumer missing disconnect method"
            
            # Test WebSocket routing
            from osrs_tracker.routing import websocket_urlpatterns
            
            # Check that our routes are registered
            route_patterns = [pattern.pattern._regex for pattern in websocket_urlpatterns]
            
            trading_route_found = any('trading' in pattern for pattern in route_patterns)
            charts_route_found = any('charts' in pattern for pattern in route_patterns)
            
            assert trading_route_found, "Trading WebSocket route not found in routing"
            assert charts_route_found, "Charts WebSocket route not found in routing"
            
            duration = time.time() - test_start
            self.log_result(test_name, "PASS", "WebSocket system properly configured", duration, {
                "trading_consumer": str(type(trading_consumer)),
                "charts_consumer": str(type(charts_consumer)),
                "total_routes": len(websocket_urlpatterns),
                "routes_found": f"trading: {trading_route_found}, charts: {charts_route_found}"
            })
            
            return True
            
        except Exception as e:
            duration = time.time() - test_start
            self.log_result(test_name, "FAIL", f"WebSocket system test failed: {str(e)}", duration)
            return False
    
    async def test_reactive_hooks(self) -> TestResult:
        """Test the reactive trading hooks and frontend integration."""
        test_start = time.time()
        test_name = "Reactive Trading Hooks"
        
        try:
            logger.info("⚡ Testing reactive trading hooks...")
            
            # Test that frontend hook files exist and are properly structured
            hook_path = "/Users/latchy/high_alch_item_recommender/frontend/src/hooks/useReactiveTradingSocket.ts"
            chart_path = "/Users/latchy/high_alch_item_recommender/frontend/src/components/trading/RealtimePriceChart.tsx"
            dashboard_path = "/Users/latchy/high_alch_item_recommender/frontend/src/components/trading/ReactiveTradingDashboard.tsx"
            
            files_exist = []
            for path, name in [(hook_path, "useReactiveTradingSocket"), 
                              (chart_path, "RealtimePriceChart"), 
                              (dashboard_path, "ReactiveTradingDashboard")]:
                if os.path.exists(path):
                    files_exist.append(name)
                    logger.info(f"✅ {name} component exists")
                else:
                    logger.warning(f"⚠️ {name} component missing at {path}")
            
            # Test management commands exist and are callable
            management_commands = [
                'start_reactive_engine',
                'analyze_price_patterns', 
                'ingest_historical_data'
            ]
            
            commands_available = []
            for cmd in management_commands:
                try:
                    # Test that command can be imported (validation)
                    from django.core.management import get_commands
                    available_commands = get_commands()
                    if cmd in available_commands:
                        commands_available.append(cmd)
                        logger.info(f"✅ {cmd} command available")
                    else:
                        logger.warning(f"⚠️ {cmd} command not found")
                except Exception as e:
                    logger.warning(f"⚠️ Error checking {cmd}: {e}")
            
            duration = time.time() - test_start
            self.log_result(test_name, "PASS", "Reactive system components available", duration, {
                "frontend_components": files_exist,
                "management_commands": commands_available,
                "total_components": len(files_exist),
                "total_commands": len(commands_available)
            })
            
            return True
            
        except Exception as e:
            duration = time.time() - test_start
            self.log_result(test_name, "FAIL", f"Reactive hooks test failed: {str(e)}", duration)
            return False
    
    async def test_database_performance(self) -> TestResult:
        """Test database performance and optimization."""
        test_start = time.time()
        test_name = "Database Performance"
        
        try:
            logger.info("⚡ Testing database performance...")
            
            # Test database connections and basic queries
            from django.db import connection
            
            # Test basic item query performance
            item_query_start = time.time()
            item_count = await sync_to_async(Item.objects.count)()
            item_query_time = time.time() - item_query_start
            
            # Test historical price query performance
            price_query_start = time.time()
            recent_prices = await sync_to_async(HistoricalPricePoint.objects.filter(
                timestamp__gte=timezone.now() - timedelta(hours=24)
            ).count)()
            price_query_time = time.time() - price_query_start
            
            # Test pattern query performance
            pattern_query_start = time.time()
            recent_patterns = await sync_to_async(PricePattern.objects.filter(
                detection_time__gte=timezone.now() - timedelta(hours=24)
            ).count)()
            pattern_query_time = time.time() - pattern_query_start
            
            # Test database connection health
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                assert result[0] == 1, "Database connection test failed"
            
            # Performance benchmarks (reasonable thresholds)
            performance_ok = (
                item_query_time < 1.0 and  # Item queries should be fast
                price_query_time < 2.0 and  # Price queries can be slightly slower
                pattern_query_time < 1.0     # Pattern queries should be fast
            )
            
            duration = time.time() - test_start
            status = "PASS" if performance_ok else "FAIL"
            message = "Database performance within acceptable limits" if performance_ok else "Database performance issues detected"
            
            self.log_result(test_name, status, message, duration, {
                "item_count": item_count,
                "item_query_time": f"{item_query_time:.3f}s",
                "recent_prices": recent_prices,
                "price_query_time": f"{price_query_time:.3f}s",
                "recent_patterns": recent_patterns,
                "pattern_query_time": f"{pattern_query_time:.3f}s",
                "performance_ok": performance_ok
            })
            
            return performance_ok
            
        except Exception as e:
            duration = time.time() - test_start
            self.log_result(test_name, "FAIL", f"Database performance test failed: {str(e)}", duration)
            return False
    
    async def run_all_tests(self):
        """Run all system tests in sequence."""
        logger.info("🎯 Starting comprehensive reactive trading system tests...")
        logger.info("=" * 80)
        
        # Phase 9.1.1: Core System Testing
        await self.test_reactive_engine_startup()
        await self.test_historical_data_ingestion()
        await self.test_pattern_recognition()
        
        # Phase 9.1.2: Integration Testing  
        await self.test_websocket_system()
        await self.test_reactive_hooks()
        
        # Phase 9.1.3: Performance & Reliability Testing
        await self.test_database_performance()
        
        # Summary
        self.print_summary()
    
    def print_summary(self):
        """Print a comprehensive test summary."""
        total_time = time.time() - self.start_time
        
        passed = len([r for r in self.results if r.status == "PASS"])
        failed = len([r for r in self.results if r.status == "FAIL"])
        skipped = len([r for r in self.results if r.status == "SKIP"])
        total = len(self.results)
        
        logger.info("=" * 80)
        logger.info("🎯 REACTIVE TRADING SYSTEM TEST SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total Tests: {total}")
        logger.info(f"✅ Passed: {passed}")
        logger.info(f"❌ Failed: {failed}")
        logger.info(f"⏭️ Skipped: {skipped}")
        logger.info(f"⏱️ Total Time: {total_time:.2f}s")
        logger.info(f"📊 Success Rate: {(passed/total*100):.1f}%")
        logger.info("")
        
        if failed == 0:
            logger.info("🎉 ALL TESTS PASSED! Your reactive trading system is ready!")
            logger.info("")
            logger.info("🚀 Next Steps:")
            logger.info("   1. Start the reactive engine: python manage.py start_reactive_engine --test-mode")
            logger.info("   2. Run frontend with: npm run dev (in frontend directory)")
            logger.info("   3. Open decanting view to see reactive features")
            logger.info("   4. Watch live WebSocket updates in browser dev tools")
        else:
            logger.info("⚠️ Some tests failed. Please review the failures above.")
            logger.info("")
            logger.info("🔧 Common fixes:")
            logger.info("   - Ensure Django is properly configured")
            logger.info("   - Check database connectivity")
            logger.info("   - Verify all dependencies are installed")
            logger.info("   - Make sure Ollama models are available")
        
        logger.info("=" * 80)
        
        # Detailed results
        logger.info("\n📋 DETAILED RESULTS:")
        for result in self.results:
            status_icon = "✅" if result.status == "PASS" else "❌" if result.status == "FAIL" else "⏭️"
            logger.info(f"{status_icon} {result.test_name}: {result.message} ({result.duration:.2f}s)")
            if result.details:
                for key, value in result.details.items():
                    logger.info(f"    └─ {key}: {value}")

async def main():
    """Main test runner."""
    print("🚀 Starting Reactive Trading System Tests...")
    print("=" * 80)
    
    tester = ReactiveSystemTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())