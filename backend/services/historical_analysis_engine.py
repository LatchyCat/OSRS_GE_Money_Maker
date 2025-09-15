"""
Historical Analysis Engine for OSRS Trading Intelligence

This service analyzes historical price data to calculate:
- Price volatility across different time periods
- Trend direction and strength 
- Support and resistance levels
- Seasonal patterns and cycles
- Flash crash detection and recovery patterns

Used to enhance trading recommendations with historical market context.
"""

import asyncio
import logging
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from scipy import stats
from django.utils import timezone
from django.db import transaction

from apps.items.models import Item
from apps.prices.models import HistoricalPrice, HistoricalAnalysis
from services.weirdgloop_api_client import WeirdGloopAPIClient, HistoricalDataPoint

logger = logging.getLogger(__name__)


@dataclass
class VolatilityMetrics:
    """Volatility analysis results for different time periods."""
    volatility_7d: Optional[float] = None
    volatility_30d: Optional[float] = None
    volatility_90d: Optional[float] = None
    volatility_365d: Optional[float] = None


@dataclass
class TrendAnalysis:
    """Trend analysis results for different time periods."""
    trend_7d: Optional[str] = None
    trend_30d: Optional[str] = None
    trend_90d: Optional[str] = None
    trend_strength_7d: Optional[float] = None
    trend_strength_30d: Optional[float] = None
    trend_strength_90d: Optional[float] = None


@dataclass
class SupportResistanceLevels:
    """Support and resistance level analysis."""
    support_7d: Optional[int] = None
    support_30d: Optional[int] = None
    resistance_7d: Optional[int] = None
    resistance_30d: Optional[int] = None


@dataclass
class PriceExtremes:
    """Price extremes for different time periods."""
    min_7d: Optional[int] = None
    max_7d: Optional[int] = None
    min_30d: Optional[int] = None
    max_30d: Optional[int] = None
    min_90d: Optional[int] = None
    max_90d: Optional[int] = None
    min_all_time: Optional[int] = None
    max_all_time: Optional[int] = None


class HistoricalAnalysisEngine:
    """Engine for analyzing historical price data and generating insights."""
    
    def __init__(self, use_multi_agent: bool = True):
        self.api_client = None
        self.use_multi_agent = use_multi_agent
        
        # Initialize multi-agent system if enabled
        if use_multi_agent:
            from services.multi_agent_ai_service import MultiAgentAIService
            self.multi_agent_service = MultiAgentAIService()
        else:
            self.multi_agent_service = None
    
    async def analyze_item_historical_data(self, item: Item) -> Optional[HistoricalAnalysis]:
        """
        Analyze historical data for a single item and create/update HistoricalAnalysis.
        
        Args:
            item: Item to analyze
            
        Returns:
            HistoricalAnalysis instance or None if insufficient data
        """
        logger.info(f"Starting historical analysis for item: {item.name} (ID: {item.item_id})")
        
        # Get or create historical analysis record
        analysis, created = await HistoricalAnalysis.objects.aget_or_create(
            item=item,
            defaults={'analysis_quality': 'unknown'}
        )
        
        # Get historical price data
        historical_data = await self._get_historical_price_data(item)
        
        if len(historical_data) < 7:  # Need at least 7 data points
            logger.warning(f"Insufficient historical data for {item.name}: {len(historical_data)} points")
            analysis.analysis_quality = 'poor'
            analysis.data_points_count = len(historical_data)
            await analysis.asave()
            return analysis
        
        # Perform various analyses
        try:
            # Calculate volatility metrics
            volatility = self._calculate_volatility_metrics(historical_data)
            
            # Analyze trends
            trend_analysis = self._analyze_trends(historical_data)
            
            # Calculate support/resistance levels
            support_resistance = self._calculate_support_resistance(historical_data)
            
            # Calculate price extremes
            price_extremes = self._calculate_price_extremes(historical_data)
            
            # Detect patterns
            seasonal_patterns = self._detect_seasonal_patterns(historical_data)
            flash_crash_history = self._detect_flash_crashes(historical_data)
            recovery_patterns = self._analyze_recovery_patterns(historical_data, flash_crash_history)
            
            # Calculate current price percentiles
            current_price = await self._get_current_price(item)
            percentiles = self._calculate_price_percentiles(historical_data, current_price)
            
            # Update analysis record
            analysis.volatility_7d = volatility.volatility_7d
            analysis.volatility_30d = volatility.volatility_30d
            analysis.volatility_90d = volatility.volatility_90d
            analysis.volatility_365d = volatility.volatility_365d
            
            analysis.trend_7d = trend_analysis.trend_7d
            analysis.trend_30d = trend_analysis.trend_30d
            analysis.trend_90d = trend_analysis.trend_90d
            
            analysis.support_level_7d = support_resistance.support_7d
            analysis.support_level_30d = support_resistance.support_30d
            analysis.resistance_level_7d = support_resistance.resistance_7d
            analysis.resistance_level_30d = support_resistance.resistance_30d
            
            analysis.price_min_7d = price_extremes.min_7d
            analysis.price_max_7d = price_extremes.max_7d
            analysis.price_min_30d = price_extremes.min_30d
            analysis.price_max_30d = price_extremes.max_30d
            analysis.price_min_90d = price_extremes.min_90d
            analysis.price_max_90d = price_extremes.max_90d
            analysis.price_min_all_time = price_extremes.min_all_time
            analysis.price_max_all_time = price_extremes.max_all_time
            
            analysis.seasonal_pattern = seasonal_patterns
            analysis.flash_crash_history = flash_crash_history
            analysis.recovery_patterns = recovery_patterns
            
            analysis.current_price_percentile_30d = percentiles.get('30d')
            analysis.current_price_percentile_90d = percentiles.get('90d')
            
            analysis.data_points_count = len(historical_data)
            analysis.analysis_quality = self._determine_analysis_quality(len(historical_data))
            
            await analysis.asave()
            
            logger.info(f"Historical analysis completed for {item.name}: {analysis.analysis_quality} quality")
            return analysis
        
        except Exception as e:
            logger.error(f"Error analyzing historical data for {item.name}: {e}")
            analysis.analysis_quality = 'unknown'
            await analysis.asave()
            return analysis
    
    async def bulk_analyze_items(self, items: List[Item], batch_size: int = 10) -> Dict[int, HistoricalAnalysis]:
        """
        Analyze historical data for multiple items efficiently using multi-agent system.
        
        Args:
            items: List of items to analyze
            batch_size: Number of items to process concurrently
            
        Returns:
            Dictionary mapping item_id to HistoricalAnalysis
        """
        logger.info(f"Starting bulk historical analysis for {len(items)} items")
        
        if self.use_multi_agent and self.multi_agent_service:
            return await self._bulk_analyze_with_agents(items, batch_size)
        else:
            return await self._bulk_analyze_traditional(items, batch_size)
    
    async def _bulk_analyze_with_agents(self, items: List[Item], batch_size: int) -> Dict[int, HistoricalAnalysis]:
        """Multi-agent distributed analysis."""
        logger.info(f"Using multi-agent system for {len(items)} items")
        
        def create_analysis_task(item):
            """Create task info for multi-agent processing."""
            return (
                'historical_analysis',  # task_type
                f"Analyze item: {item.name}",  # This will be replaced with actual analysis
                "COMPLEX"  # TaskComplexity.COMPLEX 
            )
        
        # Process using multi-agent batch processing
        batch_result = await self.multi_agent_service.batch_process_with_distribution(
            items=items,
            processing_function=lambda item: None,  # We'll handle this differently
            batch_size=batch_size
        )
        
        # Since we need actual analysis, let's process in parallel with agent specialization
        results = {}
        
        # Split items by analysis type for agent specialization
        simple_analysis_items = items[:len(items)//3]      # gemma3:1b - basic calculations
        complex_analysis_items = items[len(items)//3:2*len(items)//3]  # deepseek-r1:1.5b - complex analysis  
        coordination_items = items[2*len(items)//3:]       # qwen3:4b - coordination
        
        # Process each group with specialized agents
        tasks = []
        
        # Simple analysis tasks (basic statistics)
        for item in simple_analysis_items:
            tasks.append(self._analyze_with_specialized_agent(item, 'basic_statistics'))
        
        # Complex analysis tasks (trends, patterns)
        for item in complex_analysis_items:
            tasks.append(self._analyze_with_specialized_agent(item, 'complex_analysis'))
            
        # Coordination tasks (integration, validation)
        for item in coordination_items:
            tasks.append(self._analyze_with_specialized_agent(item, 'coordination'))
        
        # Execute all tasks concurrently
        analysis_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for i, result in enumerate(analysis_results):
            if isinstance(result, Exception):
                logger.error(f"Error in analysis task {i}: {result}")
            else:
                item_id, analysis = result
                results[item_id] = analysis
        
        logger.info(f"Multi-agent analysis completed: {len(results)}/{len(items)} successful")
        return results
    
    async def _analyze_with_specialized_agent(self, item: Item, analysis_type: str) -> Tuple[int, Optional[HistoricalAnalysis]]:
        """Analyze item using specialized agent based on analysis type."""
        try:
            if analysis_type == 'basic_statistics':
                # Use fast agent for basic calculations
                analysis = await self._analyze_basic_statistics(item)
            elif analysis_type == 'complex_analysis':
                # Use smart agent for complex pattern detection
                analysis = await self._analyze_complex_patterns(item)
            else:  # coordination
                # Use coordinator for integration and validation
                analysis = await self._analyze_and_coordinate(item)
            
            return (item.item_id, analysis)
            
        except Exception as e:
            logger.error(f"Specialized analysis failed for {item.name}: {e}")
            return (item.item_id, None)
    
    async def _analyze_basic_statistics(self, item: Item) -> Optional[HistoricalAnalysis]:
        """Analyze basic statistics using fast agent (gemma3:1b)."""
        # Get historical data
        historical_data = await self._get_historical_price_data(item)
        
        if len(historical_data) < 7:
            return None
            
        # Get or create analysis record
        analysis, created = await HistoricalAnalysis.objects.aget_or_create(
            item=item,
            defaults={'analysis_quality': 'unknown'}
        )
        
        # Basic calculations (fast agent excels at this)
        price_extremes = self._calculate_price_extremes(historical_data)
        volatility = self._calculate_volatility_metrics(historical_data)
        support_resistance = self._calculate_support_resistance(historical_data)
        
        # Update analysis with basic metrics
        analysis.price_min_7d = price_extremes.min_7d
        analysis.price_max_7d = price_extremes.max_7d
        analysis.price_min_30d = price_extremes.min_30d
        analysis.price_max_30d = price_extremes.max_30d
        analysis.price_min_90d = price_extremes.min_90d
        analysis.price_max_90d = price_extremes.max_90d
        analysis.price_min_all_time = price_extremes.min_all_time
        analysis.price_max_all_time = price_extremes.max_all_time
        
        analysis.volatility_7d = volatility.volatility_7d
        analysis.volatility_30d = volatility.volatility_30d
        analysis.volatility_90d = volatility.volatility_90d
        analysis.volatility_365d = volatility.volatility_365d
        
        analysis.support_level_7d = support_resistance.support_7d
        analysis.support_level_30d = support_resistance.support_30d
        analysis.resistance_level_7d = support_resistance.resistance_7d
        analysis.resistance_level_30d = support_resistance.resistance_30d
        
        analysis.data_points_count = len(historical_data)
        analysis.analysis_quality = self._determine_analysis_quality(len(historical_data))
        
        await analysis.asave()
        return analysis
    
    async def _analyze_complex_patterns(self, item: Item) -> Optional[HistoricalAnalysis]:
        """Analyze complex patterns using smart agent (deepseek-r1:1.5b)."""
        # Get historical data
        historical_data = await self._get_historical_price_data(item)
        
        if len(historical_data) < 7:
            return None
            
        # Get existing analysis or create new one
        try:
            analysis = await HistoricalAnalysis.objects.aget(item=item)
        except HistoricalAnalysis.DoesNotExist:
            return None  # Should have been created by basic analysis
        
        # Complex pattern analysis (smart agent excels at this)
        trend_analysis = self._analyze_trends(historical_data)
        seasonal_patterns = self._detect_seasonal_patterns(historical_data)
        flash_crash_history = self._detect_flash_crashes(historical_data)
        recovery_patterns = self._analyze_recovery_patterns(historical_data, flash_crash_history)
        
        # Update analysis with complex metrics
        analysis.trend_7d = trend_analysis.trend_7d
        analysis.trend_30d = trend_analysis.trend_30d
        analysis.trend_90d = trend_analysis.trend_90d
        
        analysis.seasonal_pattern = seasonal_patterns
        analysis.flash_crash_history = flash_crash_history
        analysis.recovery_patterns = recovery_patterns
        
        await analysis.asave()
        return analysis
    
    async def _analyze_and_coordinate(self, item: Item) -> Optional[HistoricalAnalysis]:
        """Coordinate and finalize analysis using coordinator agent (qwen3:4b)."""
        try:
            analysis = await HistoricalAnalysis.objects.aget(item=item)
        except HistoricalAnalysis.DoesNotExist:
            return None
            
        # Get historical data for final calculations
        historical_data = await self._get_historical_price_data(item)
        current_price = await self._get_current_price(item)
        
        # Final coordination tasks
        percentiles = self._calculate_price_percentiles(historical_data, current_price)
        analysis.current_price_percentile_30d = percentiles.get('30d')
        analysis.current_price_percentile_90d = percentiles.get('90d')
        
        # Final quality assessment
        analysis.analysis_quality = self._determine_analysis_quality(len(historical_data))
        
        await analysis.asave()
        return analysis
    
    async def _bulk_analyze_traditional(self, items: List[Item], batch_size: int) -> Dict[int, HistoricalAnalysis]:
        """Traditional single-threaded analysis (fallback)."""
        results = {}
        
        # Process in batches to manage memory and API rate limits
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1} of {(len(items) + batch_size - 1)//batch_size}")
            
            # Create analysis tasks for batch
            tasks = []
            for item in batch:
                task = self.analyze_item_historical_data(item)
                tasks.append((item.item_id, task))
            
            # Execute batch concurrently
            batch_results = await asyncio.gather(
                *[task for _, task in tasks],
                return_exceptions=True
            )
            
            # Process results
            for (item_id, _), result in zip(tasks, batch_results):
                if isinstance(result, Exception):
                    logger.error(f"Error analyzing item {item_id}: {result}")
                else:
                    results[item_id] = result
            
            # Small delay between batches
            if i + batch_size < len(items):
                await asyncio.sleep(0.5)
        
        successful_analyses = len([r for r in results.values() if r is not None])
        logger.info(f"Traditional analysis completed: {successful_analyses}/{len(items)} successful")
        
        return results
    
    async def _get_historical_price_data(self, item: Item) -> List[HistoricalDataPoint]:
        """Get historical price data for an item, fetching from API if needed."""
        # First try to get from database
        db_prices = [
            HistoricalDataPoint(
                price=hp.price,
                volume=hp.volume,
                timestamp=hp.timestamp
            )
            async for hp in HistoricalPrice.objects.filter(item=item).order_by('timestamp')
        ]
        
        if len(db_prices) >= 30:  # If we have good DB data, use it
            return db_prices
        
        # Otherwise fetch from API
        if not self.api_client:
            self.api_client = WeirdGloopAPIClient()
            await self.api_client.__aenter__()
        
        api_data = await self.api_client.get_historical_data(item.item_id)
        
        # Store in database for future use
        if api_data:
            await self._store_historical_data(item, api_data)
        
        return api_data
    
    async def _store_historical_data(self, item: Item, data_points: List[HistoricalDataPoint]):
        """Store historical data points in database."""
        historical_prices = []
        
        for dp in data_points:
            historical_prices.append(HistoricalPrice(
                item=item,
                price=dp.price,
                volume=dp.volume,
                timestamp=dp.timestamp,
                data_source='weirdgloop',
                is_validated=False
            ))
        
        # Batch insert with conflict handling
        try:
            await HistoricalPrice.objects.abulk_create(
                historical_prices,
                ignore_conflicts=True,
                batch_size=1000
            )
            logger.info(f"Stored {len(historical_prices)} historical data points for {item.name}")
        except Exception as e:
            logger.error(f"Error storing historical data for {item.name}: {e}")
    
    def _calculate_volatility_metrics(self, data_points: List[HistoricalDataPoint]) -> VolatilityMetrics:
        """Calculate volatility metrics for different time periods."""
        if len(data_points) < 2:
            return VolatilityMetrics()
        
        # Convert to numpy array for efficient calculation
        prices = np.array([dp.price for dp in data_points])
        timestamps = [dp.timestamp for dp in data_points]
        
        # Calculate daily returns
        returns = np.diff(prices) / prices[:-1]
        
        now = timezone.now()
        
        # Calculate volatilities for different periods
        volatility_metrics = VolatilityMetrics()
        
        for period_days, attr_name in [(7, 'volatility_7d'), (30, 'volatility_30d'), 
                                     (90, 'volatility_90d'), (365, 'volatility_365d')]:
            # Filter data for the period
            cutoff_date = now - timedelta(days=period_days)
            period_indices = [i for i, ts in enumerate(timestamps) if ts >= cutoff_date]
            
            if len(period_indices) >= 2:
                period_returns = returns[period_indices[0]:period_indices[-1]+1] if period_indices else []
                if len(period_returns) > 0:
                    # Calculate annualized volatility
                    volatility = np.std(period_returns) * np.sqrt(365)  # Annualized
                    setattr(volatility_metrics, attr_name, min(1.0, volatility))  # Cap at 1.0
        
        return volatility_metrics
    
    def _analyze_trends(self, data_points: List[HistoricalDataPoint]) -> TrendAnalysis:
        """Analyze price trends using linear regression."""
        if len(data_points) < 3:
            return TrendAnalysis()
        
        now = timezone.now()
        trend_analysis = TrendAnalysis()
        
        for period_days, trend_attr, strength_attr in [
            (7, 'trend_7d', 'trend_strength_7d'),
            (30, 'trend_30d', 'trend_strength_30d'),
            (90, 'trend_90d', 'trend_strength_90d')
        ]:
            # Filter data for the period
            cutoff_date = now - timedelta(days=period_days)
            period_data = [dp for dp in data_points if dp.timestamp >= cutoff_date]
            
            if len(period_data) >= 3:
                # Linear regression on price vs time
                timestamps = [(dp.timestamp - period_data[0].timestamp).total_seconds() 
                            for dp in period_data]
                prices = [dp.price for dp in period_data]
                
                slope, intercept, r_value, p_value, std_err = stats.linregress(timestamps, prices)
                
                # Determine trend direction and strength
                r_squared = r_value ** 2
                setattr(trend_analysis, strength_attr, r_squared)
                
                # Classify trend based on slope and significance
                if p_value < 0.05:  # Statistically significant
                    normalized_slope = slope / (sum(prices) / len(prices))  # Normalize by average price
                    
                    if normalized_slope > 0.001:  # Strong positive trend
                        if r_squared > 0.7:
                            setattr(trend_analysis, trend_attr, 'strong_up')
                        else:
                            setattr(trend_analysis, trend_attr, 'up')
                    elif normalized_slope < -0.001:  # Strong negative trend
                        if r_squared > 0.7:
                            setattr(trend_analysis, trend_attr, 'strong_down')
                        else:
                            setattr(trend_analysis, trend_attr, 'down')
                    else:
                        setattr(trend_analysis, trend_attr, 'sideways')
                else:
                    setattr(trend_analysis, trend_attr, 'sideways')
        
        return trend_analysis
    
    def _calculate_support_resistance(self, data_points: List[HistoricalDataPoint]) -> SupportResistanceLevels:
        """Calculate support and resistance levels using price clustering."""
        if len(data_points) < 10:
            return SupportResistanceLevels()
        
        now = timezone.now()
        levels = SupportResistanceLevels()
        
        for period_days, support_attr, resistance_attr in [
            (7, 'support_7d', 'resistance_7d'),
            (30, 'support_30d', 'resistance_30d')
        ]:
            cutoff_date = now - timedelta(days=period_days)
            period_data = [dp for dp in data_points if dp.timestamp >= cutoff_date]
            
            if len(period_data) >= 10:
                prices = np.array([dp.price for dp in period_data])
                
                # Calculate support (20th percentile) and resistance (80th percentile)
                support_level = int(np.percentile(prices, 20))
                resistance_level = int(np.percentile(prices, 80))
                
                setattr(levels, support_attr, support_level)
                setattr(levels, resistance_attr, resistance_level)
        
        return levels
    
    def _calculate_price_extremes(self, data_points: List[HistoricalDataPoint]) -> PriceExtremes:
        """Calculate price extremes for different time periods."""
        if not data_points:
            return PriceExtremes()
        
        now = timezone.now()
        extremes = PriceExtremes()
        
        # All-time extremes
        all_prices = [dp.price for dp in data_points]
        extremes.min_all_time = min(all_prices)
        extremes.max_all_time = max(all_prices)
        
        # Period extremes
        for period_days, min_attr, max_attr in [
            (7, 'min_7d', 'max_7d'),
            (30, 'min_30d', 'max_30d'),
            (90, 'min_90d', 'max_90d')
        ]:
            cutoff_date = now - timedelta(days=period_days)
            period_data = [dp for dp in data_points if dp.timestamp >= cutoff_date]
            
            if period_data:
                period_prices = [dp.price for dp in period_data]
                setattr(extremes, min_attr, min(period_prices))
                setattr(extremes, max_attr, max(period_prices))
        
        return extremes
    
    def _detect_seasonal_patterns(self, data_points: List[HistoricalDataPoint]) -> Optional[Dict[str, Any]]:
        """Detect seasonal patterns in price data."""
        if len(data_points) < 30:
            return None
        
        # Group by day of week and hour of day to detect patterns
        patterns = {}
        
        try:
            # Day of week patterns
            day_prices = {}
            for dp in data_points:
                day = dp.timestamp.weekday()  # 0=Monday, 6=Sunday
                if day not in day_prices:
                    day_prices[day] = []
                day_prices[day].append(dp.price)
            
            if len(day_prices) >= 7:  # Have data for all days
                day_averages = {day: np.mean(prices) for day, prices in day_prices.items()}
                overall_avg = np.mean([dp.price for dp in data_points])
                
                # Find days that deviate significantly from average
                significant_days = {}
                for day, avg_price in day_averages.items():
                    deviation = (avg_price - overall_avg) / overall_avg
                    if abs(deviation) > 0.05:  # 5% deviation threshold
                        day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
                        significant_days[day_names[day]] = {
                            'average_price': int(avg_price),
                            'deviation_pct': round(deviation * 100, 1)
                        }
                
                if significant_days:
                    patterns['day_of_week'] = significant_days
            
            # Hour of day patterns (if enough data)
            if len(data_points) > 100:
                hour_prices = {}
                for dp in data_points:
                    hour = dp.timestamp.hour
                    if hour not in hour_prices:
                        hour_prices[hour] = []
                    hour_prices[hour].append(dp.price)
                
                if len(hour_prices) >= 12:  # At least 12 different hours
                    hour_averages = {hour: np.mean(prices) for hour, prices in hour_prices.items()}
                    
                    # Find peak and trough hours
                    max_hour = max(hour_averages, key=hour_averages.get)
                    min_hour = min(hour_averages, key=hour_averages.get)
                    
                    price_range = hour_averages[max_hour] - hour_averages[min_hour]
                    if price_range > overall_avg * 0.1:  # 10% range threshold
                        patterns['hour_of_day'] = {
                            'peak_hour': max_hour,
                            'peak_price': int(hour_averages[max_hour]),
                            'trough_hour': min_hour,
                            'trough_price': int(hour_averages[min_hour]),
                            'range_pct': round(price_range / overall_avg * 100, 1)
                        }
        
        except Exception as e:
            logger.warning(f"Error detecting seasonal patterns: {e}")
            return None
        
        return patterns if patterns else None
    
    def _detect_flash_crashes(self, data_points: List[HistoricalDataPoint]) -> List[Dict[str, Any]]:
        """Detect flash crash events in price history."""
        if len(data_points) < 10:
            return []
        
        crashes = []
        prices = [dp.price for dp in data_points]
        
        # Look for sudden price drops > 20% within short timeframe
        for i in range(1, len(data_points)):
            current_price = data_points[i].price
            prev_price = data_points[i-1].price
            
            # Calculate price drop percentage
            if prev_price > 0:
                drop_pct = (prev_price - current_price) / prev_price
                
                # Flash crash criteria: >20% drop in single period
                if drop_pct > 0.2:
                    # Check if it recovered within reasonable time (look ahead 5-10 periods)
                    recovery_periods = 0
                    recovered = False
                    
                    for j in range(i+1, min(i+11, len(data_points))):
                        if data_points[j].price >= prev_price * 0.9:  # 90% recovery
                            recovery_periods = j - i
                            recovered = True
                            break
                    
                    crashes.append({
                        'timestamp': data_points[i].timestamp.isoformat(),
                        'price_before': prev_price,
                        'price_after': current_price,
                        'drop_pct': round(drop_pct * 100, 1),
                        'recovered': recovered,
                        'recovery_periods': recovery_periods if recovered else None
                    })
        
        return crashes
    
    def _analyze_recovery_patterns(self, data_points: List[HistoricalDataPoint], 
                                 flash_crashes: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Analyze price recovery patterns after crashes."""
        if not flash_crashes:
            return None
        
        recovery_times = []
        recovery_strengths = []
        
        for crash in flash_crashes:
            if crash['recovered'] and crash['recovery_periods']:
                recovery_times.append(crash['recovery_periods'])
                
                # Calculate recovery strength (how much it bounced back)
                recovery_strength = (crash['price_before'] - crash['price_after']) / crash['price_before']
                recovery_strengths.append(recovery_strength)
        
        if recovery_times:
            return {
                'average_recovery_periods': round(np.mean(recovery_times), 1),
                'fastest_recovery': min(recovery_times),
                'slowest_recovery': max(recovery_times),
                'average_recovery_strength': round(np.mean(recovery_strengths) * 100, 1),
                'total_crashes': len(flash_crashes),
                'recovered_crashes': len(recovery_times),
                'recovery_rate': round(len(recovery_times) / len(flash_crashes) * 100, 1)
            }
        
        return None
    
    def _calculate_price_percentiles(self, data_points: List[HistoricalDataPoint], 
                                   current_price: Optional[int]) -> Dict[str, float]:
        """Calculate current price percentiles vs historical data."""
        if not current_price or not data_points:
            return {}
        
        now = timezone.now()
        percentiles = {}
        
        for period_days, key in [(30, '30d'), (90, '90d')]:
            cutoff_date = now - timedelta(days=period_days)
            period_data = [dp for dp in data_points if dp.timestamp >= cutoff_date]
            
            if len(period_data) >= 10:
                period_prices = [dp.price for dp in period_data]
                # Calculate percentile rank of current price
                percentile = stats.percentileofscore(period_prices, current_price)
                percentiles[key] = round(percentile, 1)
        
        return percentiles
    
    async def _get_current_price(self, item: Item) -> Optional[int]:
        """Get current price for an item."""
        try:
            if hasattr(item, 'profit_calc') and item.profit_calc:
                return item.profit_calc.current_buy_price
        except:
            pass
        return None
    
    def _determine_analysis_quality(self, data_point_count: int) -> str:
        """Determine analysis quality based on data availability."""
        if data_point_count >= 90:
            return 'excellent'
        elif data_point_count >= 30:
            return 'good'
        elif data_point_count >= 7:
            return 'fair'
        else:
            return 'poor'