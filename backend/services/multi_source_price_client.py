"""
Multi-source price client compatibility layer.

This module provides backward compatibility for legacy imports that expect
a multi_source_price_client module. It re-exports the unified wiki price client
functionality to maintain API compatibility.

Current implementation uses only OSRS Wiki API as the authoritative source.
"""

import logging
from typing import Dict, List, Optional, Union

# Import all necessary components from the unified wiki client
from .unified_wiki_price_client import (
    PriceData,
    DataSource, 
    DataQuality,
    UnifiedPriceClient
)

# Re-export the main client class for backward compatibility
MultiSourcePriceClient = UnifiedPriceClient
UnifiedWikiPriceClient = UnifiedPriceClient

logger = logging.getLogger(__name__)

# Legacy compatibility aliases
class MultiSourcePriceData(PriceData):
    """Legacy compatibility alias for PriceData."""
    pass

# Module-level convenience functions for backward compatibility
async def get_comprehensive_price_data(item_ids: List[int], **kwargs) -> Dict[int, PriceData]:
    """
    Legacy compatibility function for getting comprehensive price data.
    Uses unified wiki client underneath.
    """
    async with UnifiedPriceClient() as client:
        try:
            results = await client.fetch_comprehensive_data(item_ids, **kwargs)
            return results
        except Exception as e:
            logger.error(f"Error fetching comprehensive price data: {e}")
            return {}

def get_price_data_sync(item_id: int) -> Optional[PriceData]:
    """
    Synchronous wrapper for getting price data for a single item.
    For backward compatibility with legacy code.
    """
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're already in an async context, use the existing loop
            task = asyncio.create_task(get_single_item_price_data(item_id))
            return task.result() if hasattr(task, 'result') else None
        else:
            return loop.run_until_complete(get_single_item_price_data(item_id))
    except Exception as e:
        logger.error(f"Error in synchronous price data fetch for item {item_id}: {e}")
        return None

async def get_single_item_price_data(item_id: int) -> Optional[PriceData]:
    """Get price data for a single item."""
    async with UnifiedPriceClient() as client:
        try:
            results = await client.fetch_comprehensive_data([item_id])
            return results.get(item_id)
        except Exception as e:
            logger.error(f"Error fetching price data for item {item_id}: {e}")
            return None

# Export commonly used classes and functions
__all__ = [
    'PriceData',
    'MultiSourcePriceData',
    'DataSource',
    'DataQuality', 
    'MultiSourcePriceClient',
    'UnifiedWikiPriceClient',
    'UnifiedPriceClient',
    'get_comprehensive_price_data',
    'get_price_data_sync',
    'get_single_item_price_data'
]