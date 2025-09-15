#!/usr/bin/env python3
"""
Create database tables for our reactive trading system.
This script manually creates the necessary tables if migrations fail.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'osrs_tracker.settings')
django.setup()

from django.db import connection

def create_tables():
    """Create the necessary tables for our reactive trading system."""
    with connection.cursor() as cursor:
        
        print("📊 Creating HistoricalPricePoint table...")
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS historical_price_points (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_id INTEGER NOT NULL REFERENCES items_item(id) ON DELETE CASCADE,
                    timestamp DATETIME NOT NULL,
                    high_price INTEGER,
                    low_price INTEGER,
                    high_volume INTEGER,
                    low_volume INTEGER,
                    average_high_price INTEGER,
                    average_low_price INTEGER,
                    high_price_volume INTEGER,
                    low_price_volume INTEGER,
                    source VARCHAR(50) DEFAULT 'wiki_api',
                    data_quality VARCHAR(20) DEFAULT 'standard',
                    confidence_score REAL DEFAULT 1.0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_historical_item_timestamp 
                ON historical_price_points(item_id, timestamp);
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_historical_timestamp 
                ON historical_price_points(timestamp);
            """)
            print("✅ HistoricalPricePoint table created")
            
        except Exception as e:
            print(f"❌ Failed to create HistoricalPricePoint table: {e}")
        
        print("📈 Creating PriceTrend table...")
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS price_trends (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_id INTEGER NOT NULL REFERENCES items_item(id) ON DELETE CASCADE,
                    period VARCHAR(10) NOT NULL,
                    direction VARCHAR(20) NOT NULL,
                    strength REAL NOT NULL,
                    confidence REAL NOT NULL,
                    start_price INTEGER,
                    end_price INTEGER,
                    price_change REAL,
                    percentage_change REAL,
                    volume_trend VARCHAR(20),
                    momentum_score REAL,
                    analysis_timestamp DATETIME NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_trend_item_period 
                ON price_trends(item_id, period);
            """)
            print("✅ PriceTrend table created")
            
        except Exception as e:
            print(f"❌ Failed to create PriceTrend table: {e}")
        
        print("🚨 Creating MarketAlert table...")
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS market_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_id INTEGER REFERENCES items_item(id) ON DELETE CASCADE,
                    alert_type VARCHAR(50) NOT NULL,
                    priority VARCHAR(20) NOT NULL,
                    message TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    trigger_price INTEGER,
                    current_price INTEGER,
                    volume_change REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    expires_at DATETIME
                );
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_alert_item_active 
                ON market_alerts(item_id, is_active);
            """)
            print("✅ MarketAlert table created")
            
        except Exception as e:
            print(f"❌ Failed to create MarketAlert table: {e}")
        
        print("🎯 Creating PricePattern table...")
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS price_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_id INTEGER NOT NULL REFERENCES items_item(id) ON DELETE CASCADE,
                    pattern_name VARCHAR(100) NOT NULL,
                    confidence REAL NOT NULL,
                    predicted_target INTEGER,
                    predicted_timeframe INTEGER,
                    support_level INTEGER,
                    resistance_level INTEGER,
                    pattern_data TEXT,
                    detection_time DATETIME NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    completion_probability REAL,
                    risk_level VARCHAR(20),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_pattern_item_active 
                ON price_patterns(item_id, is_active);
            """)
            print("✅ PricePattern table created")
            
        except Exception as e:
            print(f"❌ Failed to create PricePattern table: {e}")
        
        print("🔄 Creating DecantingOpportunity table...")
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS decanting_opportunities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_id INTEGER NOT NULL REFERENCES items_item(id) ON DELETE CASCADE,
                    item_name VARCHAR(255),
                    from_dose INTEGER NOT NULL,
                    to_dose INTEGER NOT NULL,
                    from_dose_price INTEGER NOT NULL,
                    to_dose_price INTEGER NOT NULL,
                    profit_per_conversion INTEGER,
                    profit_per_hour INTEGER,
                    confidence_score REAL,
                    trading_activity VARCHAR(50),
                    is_active BOOLEAN DEFAULT 1,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                    ai_confidence REAL,
                    ai_timing VARCHAR(20),
                    model_agreement REAL,
                    pattern_detected TEXT,
                    volume_analysis TEXT
                );
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_decanting_item_active 
                ON decanting_opportunities(item_id, is_active);
            """)
            print("✅ DecantingOpportunity table created")
            
        except Exception as e:
            print(f"❌ Failed to create DecantingOpportunity table: {e}")

def verify_tables():
    """Verify that all tables were created successfully."""
    print("\n🔍 Verifying tables...")
    
    with connection.cursor() as cursor:
        # Get list of tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        
        required_tables = [
            'historical_price_points',
            'price_trends', 
            'market_alerts',
            'price_patterns',
            'decanting_opportunities'
        ]
        
        for table in required_tables:
            if table in tables:
                print(f"✅ {table} table exists")
            else:
                print(f"❌ {table} table missing")

def main():
    """Main execution function."""
    print("🛠️  Creating Reactive Trading System Database Tables")
    print("=" * 60)
    
    try:
        create_tables()
        verify_tables()
        
        print("\n" + "=" * 60)
        print("✅ Database tables created successfully!")
        print("\n💡 Next Steps:")
        print("   1. Test historical data ingestion")
        print("   2. Test pattern analysis")
        print("   3. Start reactive engine")
        
    except Exception as e:
        print(f"\n❌ Table creation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()