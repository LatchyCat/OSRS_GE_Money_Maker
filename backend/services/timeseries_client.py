"""
InfluxDB Time-Series Client for High-Performance Price History Storage

Handles storing and querying historical price data in a time-series optimized format.
This allows for fast analytics, trend analysis, and real-time momentum calculations.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from django.conf import settings
from django.utils import timezone
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client.client.exceptions import InfluxDBError
import pandas as pd

logger = logging.getLogger(__name__)


class TimeSeriesClient:
    """
    High-performance time-series client for OSRS market data.
    Optimized for storing millions of price data points with fast analytics.
    """
    
    def __init__(self):
        # InfluxDB configuration
        self.url = getattr(settings, 'INFLUXDB_URL', 'http://localhost:8086')
        self.token = getattr(settings, 'INFLUXDB_TOKEN', '')
        self.org = getattr(settings, 'INFLUXDB_ORG', 'osrs-tracker')
        self.bucket = getattr(settings, 'INFLUXDB_BUCKET', 'market-data')
        
        # Initialize client
        self.client = None
        self.write_api = None
        self.query_api = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize InfluxDB client with proper error handling."""
        try:
            if not self.token:
                logger.warning("InfluxDB token not configured, using mock mode")
                return
            
            self.client = InfluxDBClient(
                url=self.url,
                token=self.token,
                org=self.org,
                timeout=30000  # 30 seconds timeout
            )
            
            self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
            self.query_api = self.client.query_api()
            
            # Test connection
            self._test_connection()
            logger.info("✅ InfluxDB client initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize InfluxDB client: {e}")
            self.client = None
    
    def _test_connection(self):
        """Test InfluxDB connection and create bucket if needed."""
        try:
            # Test with a simple ping
            health = self.client.health()
            if health.status != "pass":
                raise InfluxDBError(f"InfluxDB health check failed: {health.message}")
            
            # Verify bucket exists (create if needed)
            buckets_api = self.client.buckets_api()
            bucket = buckets_api.find_bucket_by_name(self.bucket)
            
            if not bucket:
                logger.info(f"Creating InfluxDB bucket: {self.bucket}")
                buckets_api.create_bucket(bucket_name=self.bucket, org=self.org)
            
        except Exception as e:
            logger.error(f"InfluxDB connection test failed: {e}")
            raise e
    
    @property
    def is_available(self) -> bool:
        """Check if InfluxDB is available for use."""
        return self.client is not None
    
    def write_price_data(self, item_id: int, price_data: Dict, timestamp: Optional[datetime] = None):
        """
        Write price data to InfluxDB time-series database.
        
        Args:
            item_id: OSRS item ID
            price_data: Dictionary containing price information
            timestamp: When the price was recorded (defaults to now)
        """
        if not self.is_available:
            logger.warning("InfluxDB not available, skipping price write")
            return False
        
        try:
            timestamp = timestamp or timezone.now()
            
            # Create data point
            point = (
                Point("price")
                .tag("item_id", str(item_id))
                .field("high_price", price_data.get('high_price', 0))
                .field("low_price", price_data.get('low_price', 0))
                .field("high_volume", price_data.get('high_volume', 0))
                .field("low_volume", price_data.get('low_volume', 0))
                .field("total_volume", price_data.get('total_volume', 0))
                .time(timestamp, WritePrecision.MS)
            )
            
            # Add optional fields if present
            if 'spread' in price_data:
                point = point.field("spread", price_data['spread'])
            if 'volatility' in price_data:
                point = point.field("volatility", price_data['volatility'])
            if 'momentum_score' in price_data:
                point = point.field("momentum_score", price_data['momentum_score'])
            if 'volume_weighted_price' in price_data:
                point = point.field("volume_weighted_price", price_data['volume_weighted_price'])
            if 'trading_activity' in price_data:
                point = point.tag("trading_activity", price_data['trading_activity'])
            if 'liquidity_score' in price_data:
                point = point.field("liquidity_score", price_data['liquidity_score'])
            
            # Write to InfluxDB
            self.write_api.write(bucket=self.bucket, org=self.org, record=point)
            logger.debug(f"Wrote price data for item {item_id} at {timestamp}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to write price data for item {item_id}: {e}")
            return False
    
    def write_timeseries_data(self, item_id: int, timeseries_points: List, source: str = "wiki_api"):
        """
        Write RuneScape Wiki timeseries data to InfluxDB.
        
        Args:
            item_id: OSRS item ID
            timeseries_points: List of TimeSeriesData points from RuneScape Wiki API
            source: Data source identifier
        """
        if not self.is_available or not timeseries_points:
            logger.warning("InfluxDB not available or no timeseries data, skipping write")
            return False
        
        try:
            points = []
            for ts_data in timeseries_points:
                # Convert timestamp to datetime
                ts_datetime = datetime.fromtimestamp(ts_data.timestamp, tz=timezone.utc)
                
                point = (
                    Point("timeseries")
                    .tag("item_id", str(item_id))
                    .tag("source", source)
                    .field("avg_high_price", ts_data.avg_high_price or 0)
                    .field("avg_low_price", ts_data.avg_low_price or 0)
                    .field("high_price_volume", ts_data.high_price_volume)
                    .field("low_price_volume", ts_data.low_price_volume)
                    .field("total_volume", ts_data.total_volume)
                    .time(ts_datetime, WritePrecision.MS)
                )
                
                # Add volume-weighted price if available
                if ts_data.volume_weighted_price:
                    point = point.field("volume_weighted_price", ts_data.volume_weighted_price)
                
                # Add trading activity classification
                if ts_data.total_volume > 100:
                    point = point.tag("activity_level", "very_active")
                elif ts_data.total_volume > 50:
                    point = point.tag("activity_level", "active")
                elif ts_data.total_volume > 10:
                    point = point.tag("activity_level", "moderate")
                elif ts_data.total_volume > 0:
                    point = point.tag("activity_level", "low")
                else:
                    point = point.tag("activity_level", "inactive")
                
                points.append(point)
            
            # Bulk write
            self.write_api.write(bucket=self.bucket, org=self.org, record=points)
            logger.info(f"Wrote {len(points)} timeseries data points for item {item_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to write timeseries data for item {item_id}: {e}")
            return False
    
    def write_bulk_price_data(self, price_records: List[Dict]):
        """
        Write multiple price records efficiently.
        
        Args:
            price_records: List of dicts with 'item_id', 'price_data', 'timestamp'
        """
        if not self.is_available or not price_records:
            return False
        
        try:
            points = []
            for record in price_records:
                item_id = record['item_id']
                price_data = record['price_data']
                timestamp = record.get('timestamp', timezone.now())
                
                point = (
                    Point("price")
                    .tag("item_id", str(item_id))
                    .field("high_price", price_data.get('high_price', 0))
                    .field("low_price", price_data.get('low_price', 0))
                    .field("high_volume", price_data.get('high_volume', 0))
                    .field("low_volume", price_data.get('low_volume', 0))
                    .field("total_volume", price_data.get('total_volume', 0))
                    .time(timestamp, WritePrecision.MS)
                )
                
                points.append(point)
            
            # Bulk write
            self.write_api.write(bucket=self.bucket, org=self.org, record=points)
            logger.info(f"Bulk wrote {len(points)} price records to InfluxDB")
            return True
            
        except Exception as e:
            logger.error(f"Bulk price write failed: {e}")
            return False
    
    def get_price_history(self, item_id: int, duration: str = "24h") -> pd.DataFrame:
        """
        Get price history for an item over a specific duration.
        
        Args:
            item_id: OSRS item ID
            duration: Time range (e.g., "1h", "24h", "7d", "30d")
            
        Returns:
            pandas DataFrame with price history
        """
        if not self.is_available:
            logger.warning("InfluxDB not available, returning empty DataFrame")
            return pd.DataFrame()
        
        try:
            query = f'''
            from(bucket: "{self.bucket}")
                |> range(start: -{duration})
                |> filter(fn: (r) => r["_measurement"] == "price")
                |> filter(fn: (r) => r["item_id"] == "{item_id}")
                |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
            '''
            
            result = self.query_api.query_data_frame(query)
            
            if not result.empty:
                # Clean up the DataFrame
                result['_time'] = pd.to_datetime(result['_time'])
                result = result.set_index('_time')
                result = result.drop(columns=['result', 'table'], errors='ignore')
                logger.debug(f"Retrieved {len(result)} price records for item {item_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get price history for item {item_id}: {e}")
            return pd.DataFrame()
    
    def calculate_momentum_metrics(self, item_id: int, window: str = "1h") -> Dict:
        """
        Calculate momentum metrics using InfluxDB analytics.
        
        Args:
            item_id: OSRS item ID
            window: Analysis window (e.g., "5m", "1h", "4h")
            
        Returns:
            Dictionary with momentum metrics
        """
        if not self.is_available:
            return {}
        
        try:
            query = f'''
            from(bucket: "{self.bucket}")
                |> range(start: -{window})
                |> filter(fn: (r) => r["_measurement"] == "price")
                |> filter(fn: (r) => r["item_id"] == "{item_id}")
                |> filter(fn: (r) => r["_field"] == "high_price" or r["_field"] == "low_price")
                |> aggregateWindow(every: 5m, fn: mean, createEmpty: false)
                |> yield(name: "momentum_data")
            '''
            
            df = self.query_api.query_data_frame(query)
            
            if df.empty:
                return {}
            
            # Calculate momentum metrics
            metrics = {}
            
            # Price velocity (change per minute)
            if len(df) >= 2:
                recent_prices = df['_value'].tail(2)
                time_diff = (df['_time'].iloc[-1] - df['_time'].iloc[-2]).total_seconds() / 60
                if time_diff > 0:
                    metrics['price_velocity'] = (recent_prices.iloc[-1] - recent_prices.iloc[0]) / time_diff
            
            # Price volatility (standard deviation)
            if len(df) >= 3:
                metrics['volatility'] = df['_value'].std()
            
            # Trend direction
            if len(df) >= 2:
                if df['_value'].iloc[-1] > df['_value'].iloc[0]:
                    metrics['trend'] = 'rising'
                elif df['_value'].iloc[-1] < df['_value'].iloc[0]:
                    metrics['trend'] = 'falling'
                else:
                    metrics['trend'] = 'stable'
            
            logger.debug(f"Calculated momentum metrics for item {item_id}: {metrics}")
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to calculate momentum for item {item_id}: {e}")
            return {}
    
    def get_volume_analysis(self, item_id: int, duration: str = "24h") -> Dict:
        """
        Get volume analysis metrics from time-series data.
        
        Args:
            item_id: OSRS item ID
            duration: Analysis duration
            
        Returns:
            Dictionary with volume metrics
        """
        if not self.is_available:
            return {}
        
        try:
            query = f'''
            from(bucket: "{self.bucket}")
                |> range(start: -{duration})
                |> filter(fn: (r) => r["_measurement"] == "price")
                |> filter(fn: (r) => r["item_id"] == "{item_id}")
                |> filter(fn: (r) => r["_field"] == "total_volume")
                |> aggregateWindow(every: 1h, fn: sum, createEmpty: false)
            '''
            
            df = self.query_api.query_data_frame(query)
            
            if df.empty:
                return {}
            
            volumes = df['_value'].tolist()
            
            return {
                'current_volume': volumes[-1] if volumes else 0,
                'average_volume': sum(volumes) / len(volumes) if volumes else 0,
                'max_volume': max(volumes) if volumes else 0,
                'volume_trend': 'increasing' if len(volumes) >= 2 and volumes[-1] > volumes[-2] else 'stable'
            }
            
        except Exception as e:
            logger.error(f"Failed to get volume analysis for item {item_id}: {e}")
            return {}
    
    def get_market_summary(self, duration: str = "1h") -> Dict:
        """
        Get market-wide summary statistics.
        
        Args:
            duration: Analysis duration
            
        Returns:
            Dictionary with market summary
        """
        if not self.is_available:
            return {}
        
        try:
            query = f'''
            from(bucket: "{self.bucket}")
                |> range(start: -{duration})
                |> filter(fn: (r) => r["_measurement"] == "price")
                |> filter(fn: (r) => r["_field"] == "total_volume")
                |> group(columns: ["item_id"])
                |> sum()
            '''
            
            df = self.query_api.query_data_frame(query)
            
            if df.empty:
                return {}
            
            return {
                'total_items': len(df),
                'total_volume': df['_value'].sum(),
                'active_items': len(df[df['_value'] > 0]),
                'high_volume_items': len(df[df['_value'] > 1000])
            }
            
        except Exception as e:
            logger.error(f"Failed to get market summary: {e}")
            return {}
    
    def close(self):
        """Close InfluxDB client connection."""
        if self.client:
            self.client.close()
            logger.info("InfluxDB client connection closed")


# Global time-series client instance
timeseries_client = TimeSeriesClient()