"""
Historical Data Service for OSRS Trading Intelligence

This service orchestrates historical data fetching, analysis, and tagging.
It coordinates between the WeirdGloop API client, analysis engine, and tagging system
to provide comprehensive historical market intelligence.

Main responsibilities:
- Fetch historical data from external APIs
- Run historical analysis calculations
- Update historical tags for items
- Provide historical insights for trading decisions
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from django.utils import timezone
from django.core.cache import cache
from django.db import transaction
from django.conf import settings

from apps.items.models import Item
from apps.prices.models import HistoricalPrice, HistoricalAnalysis
from services.weirdgloop_api_client import WeirdGloopAPIClient
from services.historical_analysis_engine import HistoricalAnalysisEngine
from services.comprehensive_item_tagger import ComprehensiveItemTagger
from services.multi_agent_ai_service import MultiAgentAIService, TaskComplexity

logger = logging.getLogger(__name__)


class HistoricalDataService:
    """Main service for managing historical data operations."""
    
    def __init__(self, use_multi_agent: bool = True):
        self.api_client = None
        self.use_multi_agent = use_multi_agent
        
        if use_multi_agent:
            self.ai_service = MultiAgentAIService()
            self.analysis_engine = HistoricalAnalysisEngine(use_multi_agent=True)
            self.tagger = ComprehensiveItemTagger(use_multi_agent=True)
        else:
            self.analysis_engine = HistoricalAnalysisEngine(use_multi_agent=False)
            self.tagger = ComprehensiveItemTagger(use_multi_agent=False)
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.api_client = WeirdGloopAPIClient()
        await self.api_client.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.api_client:
            await self.api_client.__aexit__(exc_type, exc_val, exc_tb)
    
    async def bootstrap_historical_data(self, 
                                      top_n_items: int = 500,
                                      force_refresh: bool = False) -> Dict[str, int]:
        """
        Bootstrap historical data for the most actively traded items.
        
        Args:
            top_n_items: Number of top items to process (by volume)
            force_refresh: Whether to refresh existing data
            
        Returns:
            Statistics about the bootstrap process
        """
        if self.use_multi_agent:
            logger.info(f"Starting multi-agent historical data bootstrap for top {top_n_items} items")
            return await self._bootstrap_with_agents(top_n_items, force_refresh)
        else:
            logger.info(f"Starting single-agent historical data bootstrap for top {top_n_items} items")
            return await self._bootstrap_single_agent(top_n_items, force_refresh)
    
    async def _bootstrap_single_agent(self, top_n_items: int, force_refresh: bool) -> Dict[str, int]:
        """Original single-agent bootstrap method."""
        # Get top traded items (by volume)
        top_items = await self._get_top_traded_items(top_n_items)
        
        if not top_items:
            logger.warning("No items found for historical bootstrap")
            return {'items_processed': 0, 'data_fetched': 0, 'analyses_created': 0}
        
        stats = {
            'items_processed': 0,
            'data_fetched': 0,
            'analyses_created': 0,
            'tags_updated': 0,
            'errors': 0
        }
        
        # Process in batches
        batch_size = 20
        for i in range(0, len(top_items), batch_size):
            batch = top_items[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1} of {(len(top_items) + batch_size - 1)//batch_size}")
            
            batch_stats = await self._process_item_batch(batch, force_refresh)
            
            # Aggregate stats
            for key in stats:
                stats[key] += batch_stats.get(key, 0)
            
            # Rate limiting delay
            if i + batch_size < len(top_items):
                await asyncio.sleep(2)
        
        logger.info(f"Historical data bootstrap completed: {stats}")
        return stats
    
    async def _bootstrap_with_agents(self, top_n_items: int, force_refresh: bool) -> Dict[str, int]:
        """Multi-agent bootstrap with parallel processing."""
        # Get top traded items (by volume)
        top_items = await self._get_top_traded_items(top_n_items)
        
        if not top_items:
            logger.warning("No items found for historical bootstrap")
            return {'items_processed': 0, 'data_fetched': 0, 'analyses_created': 0}
        
        logger.info(f"Starting multi-agent bootstrap for {len(top_items)} items")
        
        # Phase 1: Parallel data fetching (using coordination agents)
        fetch_results = await self.ai_service.batch_process_with_distribution(
            items=top_items,
            processing_function=lambda item: self._create_data_fetch_task(item, force_refresh),
            batch_size=30
        )
        
        # Process fetched data
        fetched_items = []
        for result in fetch_results['results']:
            if result.success:
                # Parse result to get item data
                # In a real implementation, this would contain actual historical data
                fetched_items.append(result)
        
        # Phase 2: Parallel analysis processing (distribute across all agents)
        analysis_tasks = []
        for item in top_items:
            complexity = self._determine_analysis_complexity(item)
            task_type = 'historical_analysis' if complexity == TaskComplexity.COMPLEX else 'trend_analysis'
            analysis_tasks.append((task_type, f"Analyze historical data for {item.name}", complexity))
        
        analysis_results = await self.ai_service.execute_parallel_tasks(
            tasks=analysis_tasks,
            max_concurrent=8
        )
        
        # Compile statistics
        fetch_stats = fetch_results['statistics']
        successful_analyses = len([r for r in analysis_results if r.success])
        
        stats = {
            'items_processed': len(top_items),
            'data_fetched': fetch_stats['successful'],
            'analyses_created': successful_analyses,
            'tags_updated': 0,  # Will be updated in separate tagging process
            'errors': fetch_stats['failed'] + len(analysis_results) - successful_analyses,
            'agent_distribution': fetch_stats['agent_distribution'],
            'avg_processing_time_ms': fetch_stats['average_execution_time_ms'],
            'items_per_second': fetch_stats['items_per_second']
        }
        
        logger.info(f"Multi-agent bootstrap completed: {stats}")
        return stats
    
    def _create_data_fetch_task(self, item: Item, force_refresh: bool):
        """Create a data fetching task for multi-agent processing."""
        # Determine complexity based on item characteristics
        if (item.value or 0) > 1000000 or 'rare' in item.name.lower():
            complexity = TaskComplexity.COORDINATION
            task_type = 'context_integration'
        elif hasattr(item, 'profit_calc') and item.profit_calc and (item.profit_calc.daily_volume or 0) > 5000:
            complexity = TaskComplexity.COMPLEX  
            task_type = 'pattern_detection'
        else:
            complexity = TaskComplexity.SIMPLE
            task_type = 'data_validation'
        
        # Create prompt for data fetching coordination
        prompt = f"""Coordinate historical data fetching for OSRS item:

Item: {item.name} (ID: {item.item_id})
Value: {item.value or 0:,}gp
Members: {'Yes' if item.members else 'No'}
Force Refresh: {'Yes' if force_refresh else 'No'}

Tasks to coordinate:
1. Validate item tradeable status
2. Check for existing recent data
3. Determine optimal fetch strategy
4. Prepare data storage parameters

Return status: 'ready_for_fetch' or 'skip_existing' with reasoning."""
        
        return (task_type, prompt, complexity)
    
    def _determine_analysis_complexity(self, item: Item) -> TaskComplexity:
        """Determine analysis complexity for an item."""
        # High-value or rare items need coordination
        if (item.value or 0) > 500000 or 'rare' in item.name.lower():
            return TaskComplexity.COORDINATION
        
        # High-volume items need complex analysis
        if hasattr(item, 'profit_calc') and item.profit_calc and (item.profit_calc.daily_volume or 0) > 2000:
            return TaskComplexity.COMPLEX
        
        # Simple items for basic analysis
        return TaskComplexity.SIMPLE
    
    async def update_item_historical_data(self, 
                                        item: Item, 
                                        force_refresh: bool = False) -> bool:
        """
        Update historical data for a single item.
        
        Args:
            item: Item to update
            force_refresh: Whether to refresh existing data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Updating historical data for {item.name}")
            
            # Check if we need to fetch new data
            if not force_refresh and await self._has_recent_historical_data(item):
                logger.info(f"Recent historical data exists for {item.name}, skipping fetch")
                return True
            
            # Fetch historical price data
            if not self.api_client:
                async with WeirdGloopAPIClient() as client:
                    historical_data = await client.get_historical_data(item.item_id)
            else:
                historical_data = await self.api_client.get_historical_data(item.item_id)
            
            if not historical_data:
                logger.warning(f"No historical data available for {item.name}")
                return False
            
            # Store historical data
            await self._store_historical_data(item, historical_data)
            
            # Run analysis
            analysis = await self.analysis_engine.analyze_item_historical_data(item)
            
            if analysis:
                logger.info(f"Historical analysis completed for {item.name}: {analysis.analysis_quality} quality")
                return True
            else:
                logger.warning(f"Failed to create historical analysis for {item.name}")
                return False
        
        except Exception as e:
            logger.error(f"Error updating historical data for {item.name}: {e}")
            return False
    
    async def refresh_historical_analyses(self, 
                                        item_ids: Optional[List[int]] = None,
                                        older_than_hours: int = 24) -> Dict[str, int]:
        """
        Refresh historical analyses for items that haven't been updated recently.
        
        Args:
            item_ids: Specific item IDs to refresh (if None, refreshes stale analyses)
            older_than_hours: Refresh analyses older than this many hours
            
        Returns:
            Statistics about the refresh process
        """
        if self.use_multi_agent:
            logger.info("Starting multi-agent historical analyses refresh")
            return await self._refresh_analyses_with_agents(item_ids, older_than_hours)
        else:
            logger.info("Starting single-agent historical analyses refresh")
            return await self._refresh_analyses_single_agent(item_ids, older_than_hours)
    
    async def _refresh_analyses_single_agent(self, item_ids: Optional[List[int]], older_than_hours: int) -> Dict[str, int]:
        """Original single-agent refresh method."""
        if item_ids:
            # Refresh specific items
            items = [item async for item in Item.objects.filter(item_id__in=item_ids)]
        else:
            # Find stale analyses
            cutoff_time = timezone.now() - timedelta(hours=older_than_hours)
            stale_analyses = [
                analysis async for analysis in HistoricalAnalysis.objects.filter(
                    last_analyzed__lt=cutoff_time
                ).select_related('item')[:200]  # Limit to prevent overload
            ]
            items = [analysis.item for analysis in stale_analyses]
        
        if not items:
            logger.info("No items need historical analysis refresh")
            return {'items_refreshed': 0}
        
        # Refresh analyses
        results = await self.analysis_engine.bulk_analyze_items(items, batch_size=10)
        
        successful_refreshes = len([r for r in results.values() if r is not None])
        
        logger.info(f"Historical analyses refresh completed: {successful_refreshes}/{len(items)} successful")
        
        return {
            'items_refreshed': successful_refreshes,
            'items_failed': len(items) - successful_refreshes
        }
    
    async def _refresh_analyses_with_agents(self, item_ids: Optional[List[int]], older_than_hours: int) -> Dict[str, int]:
        """Multi-agent analyses refresh with parallel processing."""
        if item_ids:
            # Refresh specific items
            items = [item async for item in Item.objects.filter(item_id__in=item_ids)]
        else:
            # Find stale analyses
            cutoff_time = timezone.now() - timedelta(hours=older_than_hours)
            stale_analyses = [
                analysis async for analysis in HistoricalAnalysis.objects.filter(
                    last_analyzed__lt=cutoff_time
                ).select_related('item')[:200]  # Limit to prevent overload
            ]
            items = [analysis.item for analysis in stale_analyses]
        
        if not items:
            logger.info("No items need historical analysis refresh")
            return {'items_refreshed': 0}
        
        logger.info(f"Refreshing {len(items)} stale analyses with multi-agent system")
        
        # Use enhanced analysis engine with multi-agent processing
        results = await self.analysis_engine.bulk_analyze_items_with_agents(items, batch_size=15)
        
        successful_refreshes = len([r for r in results.values() if r is not None])
        
        logger.info(f"Multi-agent analyses refresh completed: {successful_refreshes}/{len(items)} successful")
        
        return {
            'items_refreshed': successful_refreshes,
            'items_failed': len(items) - successful_refreshes,
            'processing_method': 'multi_agent'
        }
    
    async def get_historical_insights(self, item: Item) -> Optional[Dict]:
        """
        Get comprehensive historical insights for an item.
        
        Args:
            item: Item to get insights for
            
        Returns:
            Dictionary of insights or None if no data
        """
        try:
            analysis = await HistoricalAnalysis.objects.aget(item=item)
            
            insights = {
                'item_name': item.name,
                'analysis_quality': analysis.analysis_quality,
                'data_points_count': analysis.data_points_count,
                
                # Volatility insights
                'volatility': {
                    '7d': analysis.volatility_7d,
                    '30d': analysis.volatility_30d,
                    '90d': analysis.volatility_90d,
                    'category_30d': analysis.get_volatility_category('30d')
                },
                
                # Trend insights
                'trends': {
                    '7d': analysis.trend_7d,
                    '30d': analysis.trend_30d,
                    '90d': analysis.trend_90d,
                    'strength_30d': analysis.get_trend_strength('30d')
                },
                
                # Price position
                'price_position': {
                    'percentile_30d': analysis.current_price_percentile_30d,
                    'percentile_90d': analysis.current_price_percentile_90d,
                    'at_historical_high': analysis.is_at_historical_high(),
                    'at_historical_low': analysis.is_at_historical_low(),
                    'breaking_resistance': analysis.is_breaking_resistance,
                    'breaking_support': analysis.is_breaking_support
                },
                
                # Support and resistance
                'levels': {
                    'support_7d': analysis.support_level_7d,
                    'support_30d': analysis.support_level_30d,
                    'resistance_7d': analysis.resistance_level_7d,
                    'resistance_30d': analysis.resistance_level_30d
                },
                
                # Price extremes
                'extremes': {
                    'min_7d': analysis.price_min_7d,
                    'max_7d': analysis.price_max_7d,
                    'min_30d': analysis.price_min_30d,
                    'max_30d': analysis.price_max_30d,
                    'min_all_time': analysis.price_min_all_time,
                    'max_all_time': analysis.price_max_all_time
                },
                
                # Patterns
                'patterns': {
                    'seasonal': analysis.seasonal_pattern,
                    'flash_crashes': len(analysis.flash_crash_history or []),
                    'recovery_patterns': analysis.recovery_patterns
                },
                
                'last_analyzed': analysis.last_analyzed.isoformat()
            }
            
            return insights
        
        except HistoricalAnalysis.DoesNotExist:
            return None
        except Exception as e:
            logger.error(f"Error getting historical insights for {item.name}: {e}")
            return None
    
    async def get_items_with_pattern(self, 
                                   pattern_type: str, 
                                   limit: int = 20) -> List[Dict]:
        """
        Get items matching a specific historical pattern.
        
        Args:
            pattern_type: Type of pattern to search for
            limit: Maximum items to return
            
        Returns:
            List of items with pattern information
        """
        filters = {}
        
        if pattern_type == 'breaking_resistance':
            items = []
            async for analysis in HistoricalAnalysis.objects.select_related('item')[:limit * 2]:
                if analysis.is_breaking_resistance:
                    items.append({
                        'item': analysis.item,
                        'resistance_level': analysis.resistance_level_30d,
                        'current_percentile': analysis.current_price_percentile_30d
                    })
                if len(items) >= limit:
                    break
                    
        elif pattern_type == 'at_historical_low':
            items = []
            async for analysis in HistoricalAnalysis.objects.select_related('item')[:limit * 2]:
                if analysis.is_at_historical_low():
                    items.append({
                        'item': analysis.item,
                        'percentile_90d': analysis.current_price_percentile_90d,
                        'min_price_90d': analysis.price_min_90d
                    })
                if len(items) >= limit:
                    break
                    
        elif pattern_type == 'high_volatility':
            filters['volatility_30d__gt'] = 0.4
            
        elif pattern_type == 'strong_uptrend':
            filters['trend_30d__in'] = ['strong_up', 'up']
            
        elif pattern_type == 'flash_crash_prone':
            items = []
            async for analysis in HistoricalAnalysis.objects.select_related('item')[:limit * 2]:
                if analysis.flash_crash_history and len(analysis.flash_crash_history) > 2:
                    items.append({
                        'item': analysis.item,
                        'crash_count': len(analysis.flash_crash_history),
                        'recovery_rate': (analysis.recovery_patterns or {}).get('recovery_rate', 0)
                    })
                if len(items) >= limit:
                    break
        
        if filters:
            items = []
            async for analysis in HistoricalAnalysis.objects.filter(**filters).select_related('item')[:limit]:
                items.append({'item': analysis.item, 'analysis': analysis})
        
        return items
    
    async def _get_top_traded_items(self, limit: int) -> List[Item]:
        """Get top traded items by volume."""
        items = [
            item async for item in Item.objects.select_related('profit_calc')
            .filter(profit_calc__daily_volume__gt=50)  # Minimum volume threshold
            .order_by('-profit_calc__daily_volume')[:limit]
        ]
        
        logger.info(f"Found {len(items)} top traded items for historical bootstrap")
        return items
    
    async def _process_item_batch(self, items: List[Item], force_refresh: bool) -> Dict[str, int]:
        """Process a batch of items for historical data."""
        stats = {'items_processed': 0, 'data_fetched': 0, 'analyses_created': 0, 'tags_updated': 0, 'errors': 0}
        
        for item in items:
            try:
                # Update historical data
                success = await self.update_item_historical_data(item, force_refresh)
                
                stats['items_processed'] += 1
                if success:
                    stats['data_fetched'] += 1
                    stats['analyses_created'] += 1
                else:
                    stats['errors'] += 1
                
                # Small delay between items
                await asyncio.sleep(0.1)
            
            except Exception as e:
                logger.error(f"Error processing item {item.name} in batch: {e}")
                stats['errors'] += 1
        
        return stats
    
    async def _has_recent_historical_data(self, item: Item, max_age_hours: int = 168) -> bool:
        """Check if item has recent historical data (within max_age_hours)."""
        cutoff_time = timezone.now() - timedelta(hours=max_age_hours)
        
        # Check if we have recent historical price data
        recent_prices_count = await HistoricalPrice.objects.filter(
            item=item,
            created_at__gte=cutoff_time
        ).acount()
        
        # Check if we have recent analysis
        try:
            analysis = await HistoricalAnalysis.objects.aget(item=item)
            has_recent_analysis = analysis.last_analyzed >= cutoff_time
        except HistoricalAnalysis.DoesNotExist:
            has_recent_analysis = False
        
        return recent_prices_count > 10 and has_recent_analysis
    
    async def _store_historical_data(self, item: Item, data_points: List) -> int:
        """Store historical data points for an item."""
        from services.weirdgloop_api_client import HistoricalDataPoint
        
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
        created_count = 0
        try:
            await HistoricalPrice.objects.abulk_create(
                historical_prices,
                ignore_conflicts=True,
                batch_size=1000
            )
            created_count = len(historical_prices)
            logger.info(f"Stored {created_count} historical data points for {item.name}")
        except Exception as e:
            logger.error(f"Error storing historical data for {item.name}: {e}")
        
        return created_count


# Convenience functions for management commands
async def bootstrap_historical_data(top_n: int = 500, force_refresh: bool = False, use_multi_agent: bool = True):
    """Management command to bootstrap historical data."""
    async with HistoricalDataService(use_multi_agent=use_multi_agent) as service:
        return await service.bootstrap_historical_data(top_n, force_refresh)


async def refresh_historical_analyses(item_ids: Optional[List[int]] = None):
    """Management command to refresh historical analyses."""
    async with HistoricalDataService() as service:
        return await service.refresh_historical_analyses(item_ids)


async def get_historical_insights_command(item_id: int):
    """Management command to get historical insights for an item."""
    try:
        item = await Item.objects.aget(item_id=item_id)
        async with HistoricalDataService() as service:
            return await service.get_historical_insights(item)
    except Item.DoesNotExist:
        return None