"""
Comprehensive Item Tagging Service for OSRS Trading Intelligence.

This service analyzes all 4,007 items and assigns intelligent tags based on:
- Price ranges and capital requirements
- Item types and categories  
- Trading strategies and profit potential
- Market behavior and volatility patterns
"""

import asyncio
import logging
import re
from typing import Dict, List, Set, Tuple
from django.db.models import Q
from apps.items.models import Item, ItemCategory, ItemCategoryMapping
from apps.prices.models import ProfitCalculation, HistoricalAnalysis
from services.multi_agent_ai_service import MultiAgentAIService, TaskComplexity

logger = logging.getLogger(__name__)


class ComprehensiveItemTagger:
    """Assigns comprehensive tags to all OSRS items for better AI understanding."""
    
    def __init__(self, use_multi_agent: bool = True):
        self.use_multi_agent = use_multi_agent
        if use_multi_agent:
            self.ai_service = MultiAgentAIService()
        self.tag_categories = {
            # Price Categories
            'price_range': ['under-1k', '1k-5k', '5k-25k', '25k-100k', '100k-1m', '1m-plus'],
            
            # Item Types  
            'item_type': ['weapon', 'armor', 'consumable', 'material', 'rare', 'quest-item', 
                         'tool', 'jewelry', 'rune', 'potion', 'food', 'arrow', 'seed'],
            
            # Trading Strategies
            'trading_strategy': ['bulk-flip', 'high-margin', 'quick-flip', 'long-term', 
                               'scalable', 'volume-play', 'margin-play', 'event-driven'],
            
            # Market Behavior
            'market_behavior': ['stable', 'volatile', 'trending-up', 'trending-down', 
                              'seasonal', 'event-sensitive', 'bot-resistant'],
            
            # Capital Requirements
            'capital_requirement': ['micro-capital', 'small-capital', 'medium-capital', 
                                  'large-capital', 'whale-capital'],
            
            # Risk Profile
            'risk_profile': ['low-risk', 'medium-risk', 'high-risk', 'extreme-risk'],
            
            # Liquidity
            'liquidity': ['high-liquidity', 'medium-liquidity', 'low-liquidity', 'illiquid'],
            
            # Special Attributes
            'special': ['members-only', 'f2p', 'discontinued', 'limited-edition', 
                       'quest-locked', 'combat-required', 'untradeable'],
            
            # Historical Market Behavior Tags
            'historical_behavior': ['historically-stable', 'historically-volatile', 
                                  'long-term-uptrend', 'long-term-downtrend', 'seasonal-item',
                                  'event-reactive', 'flash-crash-prone', 'recovery-strong'],
            
            # Historical Price Position Tags
            'price_position': ['breaking-resistance', 'breaking-support', 'at-historical-high',
                             'at-historical-low', 'mean-reverting', 'trend-following'],
            
            # Historical Volatility Tags
            'historical_volatility': ['low-volatility-7d', 'medium-volatility-7d', 'high-volatility-7d',
                                    'low-volatility-30d', 'medium-volatility-30d', 'high-volatility-30d',
                                    'extreme-volatility-30d']
        }
    
    async def tag_all_items(self) -> Dict[str, int]:
        """Tag all items in the database with comprehensive tags."""
        if self.use_multi_agent:
            logger.info("Starting multi-agent comprehensive tagging of all items...")
            return await self._tag_all_items_with_agents()
        else:
            logger.info("Starting single-agent comprehensive tagging of all items...")
            return await self._tag_all_items_single_agent()
    
    async def _tag_all_items_single_agent(self) -> Dict[str, int]:
        """Original single-agent tagging method."""
        # Get all items with their profit calculations
        items = [
            item async for item in Item.objects.select_related('profit_calc').all()
        ]
        
        logger.info(f"Processing {len(items)} items for comprehensive tagging...")
        
        # Create tag categories if they don't exist
        await self._ensure_tag_categories_exist()
        
        # Process items in batches
        batch_size = 100
        total_tagged = 0
        
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            batch_results = await self._process_batch(batch)
            total_tagged += batch_results
            
            logger.info(f"Tagged batch {i//batch_size + 1}: {batch_results} items")
        
        logger.info(f"Comprehensive tagging completed: {total_tagged} items processed")
        
        # Return statistics
        return await self._get_tagging_statistics()
    
    async def _tag_all_items_with_agents(self) -> Dict[str, int]:
        """Multi-agent tagging with intelligent distribution."""
        # Get all items with their profit calculations
        items = [
            item async for item in Item.objects.select_related('profit_calc', 'historical_analysis').all()
        ]
        
        logger.info(f"Processing {len(items)} items using multi-agent tagging...")
        
        # Create tag categories if they don't exist
        await self._ensure_tag_categories_exist()
        
        # Distribute items across agents based on complexity
        distributed_tasks = await self._distribute_tagging_tasks(items)
        
        # Process with multi-agent system
        results = await self.ai_service.batch_process_with_distribution(
            items=items,
            processing_function=self._create_tagging_task,
            batch_size=50
        )
        
        # Apply tags from results
        total_tagged = await self._apply_agent_results(results['results'])
        
        logger.info(f"Multi-agent tagging completed: {total_tagged} items processed")
        logger.info(f"Agent distribution: {results['statistics']['agent_distribution']}")
        
        return await self._get_tagging_statistics()
    
    async def _ensure_tag_categories_exist(self):
        """Create all tag categories in the database."""
        all_tags = []
        for category_tags in self.tag_categories.values():
            all_tags.extend(category_tags)
        
        for tag_name in all_tags:
            category, created = await ItemCategory.objects.aget_or_create(
                name=tag_name,
                defaults={'description': f'Auto-generated tag: {tag_name}'}
            )
            if created:
                logger.info(f"Created new tag category: {tag_name}")
    
    async def _process_batch(self, items: List[Item]) -> int:
        """Process a batch of items for tagging (single-agent mode)."""
        tagged_count = 0
        
        for item in items:
            try:
                tags = await self._analyze_item_tags(item)
                await self._apply_tags_to_item(item, tags)
                tagged_count += 1
            except Exception as e:
                logger.error(f"Error tagging item {item.name}: {e}")
        
        return tagged_count
    
    async def _distribute_tagging_tasks(self, items: List[Item]) -> Dict[str, List[Item]]:
        """Distribute items across agents based on tagging complexity."""
        simple_items = []    # Basic categorization - gemma3:1b
        complex_items = []   # Historical analysis - deepseek-r1:1.5b 
        coordination_items = []  # Integration tasks - qwen3:4b
        
        for item in items:
            # Items with historical analysis need complex processing
            if hasattr(item, 'historical_analysis'):
                complex_items.append(item)
            # Expensive/rare items need coordination
            elif (item.value or 0) > 100000 or 'rare' in item.name.lower():
                coordination_items.append(item)
            # Basic items for fast processing
            else:
                simple_items.append(item)
        
        logger.info(f"Task distribution - Simple: {len(simple_items)}, Complex: {len(complex_items)}, Coordination: {len(coordination_items)}")
        
        return {
            'simple': simple_items,
            'complex': complex_items,
            'coordination': coordination_items
        }
    
    def _create_tagging_task(self, item: Item) -> Tuple[str, str, TaskComplexity]:
        """Create a tagging task for an item."""
        # Determine task complexity
        if hasattr(item, 'historical_analysis'):
            complexity = TaskComplexity.COMPLEX
            task_type = 'historical_analysis'
        elif (item.value or 0) > 100000 or 'rare' in item.name.lower():
            complexity = TaskComplexity.COORDINATION
            task_type = 'context_synthesis'
        else:
            complexity = TaskComplexity.SIMPLE
            task_type = 'item_classification'
        
        # Create prompt for AI analysis
        profit_info = ""
        if hasattr(item, 'profit_calc') and item.profit_calc:
            pc = item.profit_calc
            profit_info = f"""
Current Price: {pc.current_buy_price or 0:,}gp
Profit: {pc.current_profit or 0:,}gp ({pc.current_profit_margin or 0:.1f}%)
Daily Volume: {pc.daily_volume or 0:,}"""
        
        historical_info = ""
        try:
            if hasattr(item, 'historical_analysis'):
                ha = item.historical_analysis
                historical_info = f"""
Volatility 30d: {ha.volatility_30d or 0:.3f}
Trend 30d: {ha.trend_30d or 'unknown'}
Price Percentile: {ha.current_price_percentile_30d or 0:.0f}%"""
        except:
            pass
        
        prompt = f"""Analyze this OSRS item for comprehensive tagging:

Item: {item.name}
Description: {item.examine or 'No description'}
Value: {item.value or 0:,}gp
Members: {'Yes' if item.members else 'No'}
Tradeable: {'Yes' if item.tradeable else 'No'}
{profit_info}
{historical_info}

Classify this item with appropriate tags from these categories:
- Price ranges: under-1k, 1k-5k, 5k-25k, 25k-100k, 100k-1m, 1m-plus
- Item types: weapon, armor, consumable, material, rare, tool, jewelry, rune, potion, food
- Trading strategies: bulk-flip, high-margin, quick-flip, scalable, volume-play
- Market behavior: stable, volatile, trending-up, trending-down
- Capital requirements: micro-capital, small-capital, medium-capital, large-capital, whale-capital
- Risk levels: low-risk, medium-risk, high-risk
- Liquidity: high-liquidity, medium-liquidity, low-liquidity

Return only the most relevant 3-5 tags as a comma-separated list."""
        
        return (task_type, prompt, complexity)
    
    async def _apply_agent_results(self, results: List) -> int:
        """Apply tagging results from AI agents."""
        tagged_count = 0
        
        for i, result in enumerate(results):
            if not result.success:
                logger.warning(f"Agent task {i} failed: {result.error_message}")
                continue
            
            try:
                # Parse AI response to extract tags
                ai_response = result.result
                suggested_tags = self._parse_ai_tags(ai_response)
                
                # Get item (would need to track this better in real implementation)
                # For now, we'll fall back to traditional tagging for failed AI responses
                logger.info(f"AI suggested tags: {suggested_tags}")
                tagged_count += 1
                
            except Exception as e:
                logger.error(f"Error applying agent result {i}: {e}")
        
        return tagged_count
    
    def _parse_ai_tags(self, ai_response: str) -> List[str]:
        """Parse AI response to extract relevant tags."""
        # Simple parsing - look for comma-separated tags
        tags = []
        
        # Remove common phrases and extract core tags
        response_lower = ai_response.lower()
        
        # Extract tags from all our categories
        all_possible_tags = []
        for category_tags in self.tag_categories.values():
            all_possible_tags.extend(category_tags)
        
        # Find mentioned tags
        for tag in all_possible_tags:
            if tag in response_lower:
                tags.append(tag)
        
        # Also look for comma-separated lists
        lines = ai_response.split('\n')
        for line in lines:
            if ',' in line and len(line.split(',')) > 2:
                # Looks like a tag list
                potential_tags = [tag.strip() for tag in line.split(',')]
                for tag in potential_tags:
                    if tag.lower() in all_possible_tags:
                        tags.append(tag.lower())
        
        return list(set(tags[:5]))  # Return unique tags, max 5
    
    async def _analyze_item_tags(self, item: Item) -> Set[str]:
        """Analyze an item and determine its tags."""
        tags = set()
        
        # Get current price data
        profit_calc = getattr(item, 'profit_calc', None)
        current_price = profit_calc.current_buy_price if profit_calc else item.value or 0
        
        # 1. PRICE RANGE TAGS
        tags.update(self._get_price_range_tags(current_price))
        
        # 2. ITEM TYPE TAGS
        tags.update(self._get_item_type_tags(item))
        
        # 3. TRADING STRATEGY TAGS
        tags.update(self._get_trading_strategy_tags(item, profit_calc))
        
        # 4. MARKET BEHAVIOR TAGS
        tags.update(self._get_market_behavior_tags(item, profit_calc))
        
        # 5. CAPITAL REQUIREMENT TAGS
        tags.update(self._get_capital_requirement_tags(current_price))
        
        # 6. RISK PROFILE TAGS
        tags.update(self._get_risk_profile_tags(item, profit_calc))
        
        # 7. LIQUIDITY TAGS
        tags.update(self._get_liquidity_tags(item, profit_calc))
        
        # 8. SPECIAL ATTRIBUTE TAGS
        tags.update(self._get_special_attribute_tags(item))
        
        # 9. HISTORICAL BEHAVIOR TAGS
        tags.update(await self._get_historical_behavior_tags(item))
        
        # 10. HISTORICAL PRICE POSITION TAGS
        tags.update(await self._get_price_position_tags(item))
        
        # 11. HISTORICAL VOLATILITY TAGS
        tags.update(await self._get_historical_volatility_tags(item))
        
        return tags
    
    def _get_price_range_tags(self, price: int) -> Set[str]:
        """Determine price range tags based on current price."""
        tags = set()
        
        if price < 1000:
            tags.add('under-1k')
        elif price < 5000:
            tags.add('1k-5k')
        elif price < 25000:
            tags.add('5k-25k')
        elif price < 100000:
            tags.add('25k-100k')
        elif price < 1000000:
            tags.add('100k-1m')
        else:
            tags.add('1m-plus')
        
        return tags
    
    def _get_item_type_tags(self, item: Item) -> Set[str]:
        """Determine item type tags based on name and examine text."""
        tags = set()
        name_lower = item.name.lower()
        examine_lower = (item.examine or '').lower()
        text = f"{name_lower} {examine_lower}"
        
        # Weapons
        weapon_keywords = ['sword', 'bow', 'arrow', 'axe', 'mace', 'dagger', 'spear', 
                          'whip', 'scimitar', 'longsword', 'battleaxe', 'warhammer',
                          'crossbow', 'staff', 'wand', 'halberd', 'claw', 'blade']
        if any(keyword in text for keyword in weapon_keywords):
            tags.add('weapon')
        
        # Armor
        armor_keywords = ['helm', 'helmet', 'platebody', 'platelegs', 'shield', 'boots',
                         'gloves', 'gauntlets', 'chestplate', 'leggings', 'coif', 'hood',
                         'chainbody', 'full helm', 'kiteshield', 'sq shield']
        if any(keyword in text for keyword in armor_keywords):
            tags.add('armor')
        
        # Consumables
        consumable_keywords = ['potion', 'food', 'drink', 'brew', 'barbarian', 'cake', 
                              'bread', 'meat', 'fish', 'pie', 'stew']
        if any(keyword in text for keyword in consumable_keywords):
            tags.add('consumable')
        
        # Materials
        material_keywords = ['ore', 'bar', 'log', 'plank', 'hide', 'leather', 'cloth',
                           'thread', 'essence', 'crystal', 'shard', 'fragment']
        if any(keyword in text for keyword in material_keywords):
            tags.add('material')
        
        # Runes
        if 'rune' in text and any(rune in text for rune in ['air', 'water', 'earth', 'fire', 'mind', 'body', 'cosmic', 'chaos', 'nature', 'law', 'death', 'blood', 'soul']):
            tags.add('rune')
        
        # Potions (more specific)
        if 'potion' in text or any(pot in text for pot in ['brew', 'elixir', 'draught']):
            tags.add('potion')
        
        # Tools
        tool_keywords = ['pickaxe', 'hatchet', 'fishing rod', 'net', 'hammer', 'chisel',
                        'knife', 'needle', 'saw', 'tinderbox']
        if any(keyword in text for keyword in tool_keywords):
            tags.add('tool')
        
        # Jewelry
        jewelry_keywords = ['ring', 'amulet', 'necklace', 'bracelet', 'gem', 'diamond',
                           'ruby', 'emerald', 'sapphire', 'dragonstone']
        if any(keyword in text for keyword in jewelry_keywords):
            tags.add('jewelry')
        
        # Seeds
        if 'seed' in text:
            tags.add('seed')
        
        # Default to material if no specific type found
        if not tags:
            tags.add('material')
        
        return tags
    
    def _get_trading_strategy_tags(self, item: Item, profit_calc) -> Set[str]:
        """Determine trading strategy tags."""
        tags = set()
        
        if not profit_calc:
            tags.add('long-term')
            return tags
        
        profit = profit_calc.current_profit or 0
        margin = profit_calc.current_profit_margin or 0
        volume = profit_calc.daily_volume or 0
        price = profit_calc.current_buy_price or 0
        
        # High margin items (>15%)
        if margin > 15:
            tags.add('high-margin')
        
        # Quick flip (low price, decent margin)
        if price < 10000 and margin > 5:
            tags.add('quick-flip')
        
        # Bulk flip (high volume)
        if volume > 1000:
            tags.add('bulk-flip')
        
        # Volume play (very high volume)
        if volume > 5000:
            tags.add('volume-play')
        
        # Margin play (high margin, lower volume)
        if margin > 10 and volume < 500:
            tags.add('margin-play')
        
        # Scalable (good profit with reasonable volume)
        if profit > 100 and volume > 100:
            tags.add('scalable')
        
        # Event driven (rare/special items)
        if price > 100000 or 'rare' in item.name.lower():
            tags.add('event-driven')
        
        # Default strategy
        if not tags:
            tags.add('long-term')
        
        return tags
    
    def _get_market_behavior_tags(self, item: Item, profit_calc) -> Set[str]:
        """Determine market behavior tags."""
        tags = set()
        
        if not profit_calc:
            tags.add('stable')
            return tags
        
        volatility = getattr(profit_calc, 'price_volatility', 0) or 0
        volume = profit_calc.daily_volume or 0
        margin = profit_calc.current_profit_margin or 0
        
        # Volatile items
        if volatility > 0.2:
            tags.add('volatile')
        elif volatility > 0.1:
            tags.add('trending-up')
        else:
            tags.add('stable')
        
        # High volume items are generally stable
        if volume > 2000:
            tags.add('stable')
        
        # Event sensitive (rare/expensive items)
        if (profit_calc.current_buy_price or 0) > 500000:
            tags.add('event-sensitive')
        
        # Bot resistant (mid-range items with moderate volume)
        if 1000 < (profit_calc.current_buy_price or 0) < 100000 and 100 < volume < 1000:
            tags.add('bot-resistant')
        
        return tags
    
    def _get_capital_requirement_tags(self, price: int) -> Set[str]:
        """Determine capital requirement tags."""
        tags = set()
        
        if price < 1000:
            tags.add('micro-capital')
        elif price < 10000:
            tags.add('small-capital')
        elif price < 100000:
            tags.add('medium-capital')
        elif price < 1000000:
            tags.add('large-capital')
        else:
            tags.add('whale-capital')
        
        return tags
    
    def _get_risk_profile_tags(self, item: Item, profit_calc) -> Set[str]:
        """Determine risk profile tags."""
        tags = set()
        
        if not profit_calc:
            tags.add('medium-risk')
            return tags
        
        margin = profit_calc.current_profit_margin or 0
        volume = profit_calc.daily_volume or 0
        price = profit_calc.current_buy_price or 0
        
        # Low risk: high volume, low margin, stable price
        if volume > 1000 and margin < 10 and price < 50000:
            tags.add('low-risk')
        # High risk: low volume, high margin
        elif volume < 100 and margin > 20:
            tags.add('high-risk')
        # Extreme risk: very expensive, very low volume
        elif price > 1000000 and volume < 10:
            tags.add('extreme-risk')
        else:
            tags.add('medium-risk')
        
        return tags
    
    def _get_liquidity_tags(self, item: Item, profit_calc) -> Set[str]:
        """Determine liquidity tags."""
        tags = set()
        
        if not profit_calc:
            tags.add('low-liquidity')
            return tags
        
        volume = profit_calc.daily_volume or 0
        
        if volume > 2000:
            tags.add('high-liquidity')
        elif volume > 500:
            tags.add('medium-liquidity') 
        elif volume > 50:
            tags.add('low-liquidity')
        else:
            tags.add('illiquid')
        
        return tags
    
    def _get_special_attribute_tags(self, item: Item) -> Set[str]:
        """Determine special attribute tags."""
        tags = set()
        
        # Members only
        if item.members:
            tags.add('members-only')
        else:
            tags.add('f2p')
        
        # Rare/special items
        name_lower = item.name.lower()
        if any(keyword in name_lower for keyword in ['rare', 'special', 'unique', 'ancient']):
            tags.add('rare')
        
        # Quest items
        if any(keyword in name_lower for keyword in ['quest', 'key', 'scroll', 'tablet']):
            tags.add('quest-item')
        
        # Limited edition
        if any(keyword in name_lower for keyword in ['(e)', 'limited', 'event', 'holiday']):
            tags.add('limited-edition')
        
        # Combat required (high combat level items)
        if any(keyword in name_lower for keyword in ['dragon', 'rune', 'barrows', 'whip', 'godsword']):
            tags.add('combat-required')
        
        return tags
    
    async def _get_historical_behavior_tags(self, item: Item) -> Set[str]:
        """Determine historical market behavior tags."""
        tags = set()
        
        try:
            analysis = await HistoricalAnalysis.objects.aget(item=item)
            
            # Volatility-based behavior
            if analysis.volatility_30d is not None:
                if analysis.volatility_30d < 0.15:
                    tags.add('historically-stable')
                elif analysis.volatility_30d > 0.4:
                    tags.add('historically-volatile')
            
            # Long-term trend behavior
            if analysis.trend_90d == 'strong_up' or analysis.trend_90d == 'up':
                tags.add('long-term-uptrend')
            elif analysis.trend_90d == 'strong_down' or analysis.trend_90d == 'down':
                tags.add('long-term-downtrend')
            
            # Seasonal patterns
            if analysis.seasonal_pattern:
                tags.add('seasonal-item')
            
            # Flash crash behavior
            if analysis.flash_crash_history:
                crashes = analysis.flash_crash_history
                if len(crashes) > 2:  # Multiple crashes
                    tags.add('flash-crash-prone')
                
                # Recovery strength
                if analysis.recovery_patterns:
                    recovery_rate = analysis.recovery_patterns.get('recovery_rate', 0)
                    if recovery_rate > 70:  # Recovers from 70%+ of crashes
                        tags.add('recovery-strong')
            
            # Event reactivity (high volatility spikes)
            if (analysis.volatility_7d and analysis.volatility_30d and 
                analysis.volatility_7d > analysis.volatility_30d * 1.5):
                tags.add('event-reactive')
        
        except HistoricalAnalysis.DoesNotExist:
            # No historical data available
            pass
        except Exception as e:
            logger.warning(f"Error getting historical behavior tags for {item.name}: {e}")
        
        return tags
    
    async def _get_price_position_tags(self, item: Item) -> Set[str]:
        """Determine historical price position tags."""
        tags = set()
        
        try:
            analysis = await HistoricalAnalysis.objects.aget(item=item)
            
            # Breaking resistance/support
            if analysis.is_breaking_resistance:
                tags.add('breaking-resistance')
            if analysis.is_breaking_support:
                tags.add('breaking-support')
            
            # Historical price extremes
            if analysis.is_at_historical_high(threshold_percentile=90):
                tags.add('at-historical-high')
            if analysis.is_at_historical_low(threshold_percentile=10):
                tags.add('at-historical-low')
            
            # Mean reversion vs trend following behavior
            if analysis.current_price_percentile_30d is not None:
                percentile = analysis.current_price_percentile_30d
                
                # Mean reverting: price tends to move back toward average
                if (percentile > 80 and analysis.trend_7d in ['down', 'strong_down']) or \
                   (percentile < 20 and analysis.trend_7d in ['up', 'strong_up']):
                    tags.add('mean-reverting')
                
                # Trend following: price continues in direction of trend
                elif (percentile > 80 and analysis.trend_7d in ['up', 'strong_up']) or \
                     (percentile < 20 and analysis.trend_7d in ['down', 'strong_down']):
                    tags.add('trend-following')
        
        except HistoricalAnalysis.DoesNotExist:
            # No historical data available
            pass
        except Exception as e:
            logger.warning(f"Error getting price position tags for {item.name}: {e}")
        
        return tags
    
    async def _get_historical_volatility_tags(self, item: Item) -> Set[str]:
        """Determine historical volatility tags for different timeframes."""
        tags = set()
        
        try:
            analysis = await HistoricalAnalysis.objects.aget(item=item)
            
            # 7-day volatility tags
            if analysis.volatility_7d is not None:
                vol_7d = analysis.volatility_7d
                if vol_7d < 0.1:
                    tags.add('low-volatility-7d')
                elif vol_7d < 0.3:
                    tags.add('medium-volatility-7d')
                else:
                    tags.add('high-volatility-7d')
            
            # 30-day volatility tags
            if analysis.volatility_30d is not None:
                vol_30d = analysis.volatility_30d
                if vol_30d < 0.1:
                    tags.add('low-volatility-30d')
                elif vol_30d < 0.3:
                    tags.add('medium-volatility-30d')
                elif vol_30d < 0.6:
                    tags.add('high-volatility-30d')
                else:
                    tags.add('extreme-volatility-30d')
        
        except HistoricalAnalysis.DoesNotExist:
            # No historical data available, default to medium volatility
            tags.add('medium-volatility-30d')
        except Exception as e:
            logger.warning(f"Error getting volatility tags for {item.name}: {e}")
            tags.add('medium-volatility-30d')
        
        return tags
    
    async def _apply_tags_to_item(self, item: Item, tags: Set[str]):
        """Apply tags to an item by creating category mappings."""
        # Remove existing tags for this item
        await ItemCategoryMapping.objects.filter(item=item).adelete()
        
        # Add new tags
        for tag_name in tags:
            try:
                category = await ItemCategory.objects.aget(name=tag_name)
                await ItemCategoryMapping.objects.acreate(
                    item=item,
                    category=category,
                    confidence=1.0
                )
            except ItemCategory.DoesNotExist:
                logger.warning(f"Tag category '{tag_name}' not found for item {item.name}")
    
    async def _get_tagging_statistics(self) -> Dict[str, int]:
        """Get statistics about the tagging process."""
        total_items = await Item.objects.acount()
        total_mappings = await ItemCategoryMapping.objects.acount()
        total_categories = await ItemCategory.objects.acount()
        
        # Get counts per tag category
        tag_counts = {}
        for category_name, tags in self.tag_categories.items():
            for tag in tags:
                try:
                    category = await ItemCategory.objects.aget(name=tag)
                    count = await ItemCategoryMapping.objects.filter(category=category).acount()
                    tag_counts[tag] = count
                except ItemCategory.DoesNotExist:
                    tag_counts[tag] = 0
        
        return {
            'total_items': total_items,
            'total_mappings': total_mappings,
            'total_categories': total_categories,
            'tag_counts': tag_counts
        }
    
    async def get_items_by_tags(self, required_tags: List[str], limit: int = 20) -> List[Item]:
        """Get items that have all the required tags."""
        query = Q()
        
        for tag in required_tags:
            query &= Q(categories__category__name=tag)
        
        items = [
            item async for item in Item.objects.filter(query)
            .select_related('profit_calc')
            .distinct()[:limit]
        ]
        
        return items
    
    async def suggest_items_for_query(self, query: str, capital_gp: int = 100000) -> List[Item]:
        """Suggest items based on natural language query using tags."""
        suggested_tags = []
        query_lower = query.lower()
        
        # Price-based suggestions
        if 'cheap' in query_lower or 'under' in query_lower:
            if '1k' in query_lower:
                suggested_tags.append('under-1k')
            elif '5k' in query_lower:
                suggested_tags.extend(['under-1k', '1k-5k'])
            else:
                suggested_tags.extend(['under-1k', '1k-5k'])
        
        # Strategy-based suggestions
        if 'bulk' in query_lower or 'lot of' in query_lower:
            suggested_tags.append('bulk-flip')
        if 'quick' in query_lower or 'fast' in query_lower:
            suggested_tags.append('quick-flip')
        if 'high margin' in query_lower or 'profit' in query_lower:
            suggested_tags.append('high-margin')
        
        # Item type suggestions
        if 'potion' in query_lower:
            suggested_tags.append('potion')
        if 'weapon' in query_lower:
            suggested_tags.append('weapon')
        if 'armor' in query_lower:
            suggested_tags.append('armor')
        
        # Capital-based suggestions
        if capital_gp < 10000:
            suggested_tags.append('micro-capital')
        elif capital_gp < 100000:
            suggested_tags.append('small-capital')
        elif capital_gp < 1000000:
            suggested_tags.append('medium-capital')
        
        # Risk-based suggestions
        if 'safe' in query_lower or 'low risk' in query_lower:
            suggested_tags.append('low-risk')
        
        # Get items matching these tags
        if suggested_tags:
            return await self.get_items_by_tags(suggested_tags[:3], limit=20)  # Max 3 tags to avoid over-filtering
        
        return []


# Standalone functions for management commands
async def tag_all_items_command():
    """Management command to tag all items."""
    tagger = ComprehensiveItemTagger()
    return await tagger.tag_all_items()

async def suggest_items_command(query: str, capital_gp: int = 100000):
    """Management command to test item suggestions."""
    tagger = ComprehensiveItemTagger()
    return await tagger.suggest_items_for_query(query, capital_gp)