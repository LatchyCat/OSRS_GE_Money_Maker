"""
Dynamic Set Discovery Service using OSRS Wiki API and AI Analysis

Completely dynamic system that:
1. Fetches all items from /mapping endpoint  
2. Gets real-time pricing from /latest endpoint
3. Analyzes volume data from /timeseries endpoint
4. Uses AI to discover profitable set combining opportunities
5. Returns comprehensive analysis to frontend

No hardcoded data - everything comes from live OSRS Wiki API.
"""

import asyncio
import logging
import json
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timezone
import httpx
from dataclasses import dataclass

from services.runescape_wiki_client import RuneScapeWikiAPIClient
from services.weird_gloop_client import GrandExchangeTax

logger = logging.getLogger(__name__)


@dataclass
class DynamicSetOpportunity:
    """Dynamically discovered set opportunity from AI analysis."""
    set_name: str
    set_type: str  # 'armor_set', 'individual_pieces', 'cross_arbitrage'
    strategy: str  # 'combining', 'decombining', 'arbitrage'
    
    # Core items
    primary_items: List[Dict]  # Main items involved
    secondary_items: List[Dict]  # Alternative/related items
    
    # Financial analysis
    profit_gp: int
    profit_margin_pct: float
    required_capital: int
    risk_assessment: str
    
    # AI analysis
    ai_confidence: float
    ai_reasoning: str
    market_conditions: str
    execution_difficulty: str
    
    # Market data
    volume_score: float
    liquidity_assessment: str
    price_stability: str
    data_freshness: float


class DynamicSetDiscoveryService:
    """Service for discovering set combining opportunities using AI analysis of live OSRS data."""
    
    def __init__(self):
        self.ollama_base_url = "http://localhost:11434"
        self.analysis_model = "qwen3:4b"  # Use best model for analysis
        self.fast_model = "gemma3:1b"  # Faster model for bulk processing
        self.chunk_size = 50  # Process items in chunks to prevent timeout
        self.ai_timeout = 180.0  # Increased timeout for AI requests
        self.max_retries = 3  # Retry failed AI requests
        
    async def discover_all_opportunities(
        self,
        min_profit: int = 5000,
        max_capital: int = 100_000_000,
        min_confidence: float = 0.3
    ) -> List[DynamicSetOpportunity]:
        """
        Discover all profitable set combining opportunities using AI analysis.
        
        Args:
            min_profit: Minimum profit threshold in GP
            max_capital: Maximum capital available
            min_confidence: Minimum AI confidence score
            
        Returns:
            List of discovered opportunities
        """
        logger.info("Starting dynamic set discovery using OSRS Wiki API and AI analysis")
        
        opportunities = []
        
        async with RuneScapeWikiAPIClient() as wiki_client:
            # Step 1: Get complete item mapping  
            logger.info("Fetching complete OSRS item mapping...")
            mapping_dict = await wiki_client.get_item_mapping()
            logger.info(f"Retrieved {len(mapping_dict)} items from mapping")
            
            # Convert dict to list of ItemMetadata objects for easier processing
            mapping = list(mapping_dict.values())
            
            # Step 2: Get latest pricing for all items
            logger.info("Fetching latest pricing data...")
            all_prices = await wiki_client.get_latest_prices()
            logger.info(f"Retrieved pricing for {len(all_prices)} items")
            
            # Step 3: Identify armor and weapon items for analysis
            relevant_items = self._filter_relevant_items(mapping, all_prices)
            logger.info(f"Identified {len(relevant_items)} relevant items for analysis")
            
            # Debug: log sample items
            if len(relevant_items) == 0:
                logger.warning("No relevant items found! Debugging...")
                sample_mapping = mapping[:10]
                logger.warning(f"Sample mapping items: {[(item.name, item.id) for item in sample_mapping]}")
                sample_with_prices = [item for item in sample_mapping if item.id in all_prices]
                logger.warning(f"Sample items with prices: {len(sample_with_prices)}")
                
                # Check first few items with prices to see if they match our keywords
                for item in sample_with_prices[:5]:
                    logger.warning(f"Item with prices: {item.name} - matches keywords? {any(kw in item.name.lower() for kw in ['armour', 'armor', 'helm', 'sword'])}")
                
            else:
                logger.info(f"Top relevant items: {[item['name'] for item in relevant_items[:10]]}")
            
            # Step 4: Prioritize and process items intelligently
            logger.info(f"Processing {len(relevant_items)} items with intelligent chunking")
            
            # Sort items by priority for better results in early chunks
            prioritized_items = self._prioritize_items_for_analysis(relevant_items)
            logger.info(f"Prioritized {len(prioritized_items)} items for analysis")
            
            # Use adaptive chunk sizing based on item value/complexity
            all_ai_opportunities = []
            
            # Split items into chunks for processing
            for i in range(0, len(prioritized_items), self.chunk_size):
                chunk = prioritized_items[i:i + self.chunk_size]
                chunk_num = (i // self.chunk_size) + 1
                total_chunks = (len(prioritized_items) + self.chunk_size - 1) // self.chunk_size
                
                logger.info(f"Processing chunk {chunk_num}/{total_chunks} ({len(chunk)} items)")
                
                # Create AI analysis context for this chunk
                chunk_context = await self._create_ai_analysis_context(
                    chunk, all_prices, wiki_client
                )
                
                # Step 5: Get AI analysis for this chunk with retry logic
                logger.info(f"Getting AI analysis for chunk {chunk_num}/{total_chunks}...")
                chunk_opportunities = await self._get_ai_analysis_with_retry(
                    chunk_context, min_profit, max_capital, chunk_num
                )
                
                if chunk_opportunities:
                    all_ai_opportunities.extend(chunk_opportunities)
                    logger.info(f"Found {len(chunk_opportunities)} opportunities in chunk {chunk_num}")
                else:
                    logger.warning(f"No opportunities found in chunk {chunk_num}")
                
                # Add small delay between chunks to prevent overwhelming the AI
                if i + self.chunk_size < len(relevant_items):
                    await asyncio.sleep(2)
            
            logger.info(f"Total opportunities found across all chunks: {len(all_ai_opportunities)}")
            
            # Combine and deduplicate opportunities from all chunks
            ai_analysis = self._combine_chunk_results(all_ai_opportunities)
            
            # Step 6: Parse AI response and create opportunities
            opportunities = await self._parse_ai_analysis_to_opportunities(
                ai_analysis, prioritized_items, all_prices, wiki_client,
                min_profit, max_capital, min_confidence
            )
            
        logger.info(f"Dynamic discovery found {len(opportunities)} opportunities")
        return opportunities
    
    def _filter_relevant_items(self, mapping: List, all_prices: Dict) -> List[Dict]:
        """Filter items to those relevant for set combining analysis."""
        
        relevant_keywords = [
            # Core armor pieces
            'armour', 'armor', 'set', 'helm', 'helmet', 'platebody', 'platelegs', 
            'chainbody', 'full helm', 'kiteshield', 'kite', 'med helm', 'square shield',
            'plateskirt', 'chainmail', 'hauberk', 'coif', 'leather', 'chaps', 'vambraces',
            'gauntlets', 'gloves', 'boots', 'body', 'legs', 'skirt',
            
            # Weapons for weapon sets
            'sword', 'axe', 'mace', 'scimitar', 'longsword', 'battleaxe', 'warhammer', 
            'spear', 'halberd', 'dagger', 'shortsword', 'rapier', 'claws', 'whip',
            'crossbow', 'bow', 'javelin', 'dart', 'knife', 'thrownaxe',
            
            # Magic equipment
            'robe', 'hood', 'staff', 'wand', 'book', 'orb', 'hat', 'wizard',
            'mystic', 'enchanted', 'magical', 'elemental',
            
            # Ranged equipment
            'dragonhide', 'hide', 'studded', 'range', 'archer', 'bowstring',
            'bolts', 'arrows', 'ammunition', 'quiver',
            
            # Special armor types
            'barrows', 'void', 'fighter', 'elite', 'superior', 'blessed', 'ancient',
            'crystal', 'dragonstone', 'obsidian', 'granite', 'torag', 'dharok',
            'ahrim', 'karil', 'verac', 'guthan', 'third-age', 'gilded',
            'bandos', 'armadyl', 'saradomin', 'zamorak', 'guthix', 'ancient',
            'torva', 'pernix', 'virtus', 'malevolent', 'tectonic', 'sirenic',
            'anima', 'refined', 'superior', 'elite',
            
            # Material types that often form sets
            'bronze', 'iron', 'steel', 'mithril', 'adamant', 'rune', 'dragon',
            'black', 'white', 'blue', 'red', 'green', 'yellow', 'purple',
            'trimmed', 'gold-trimmed', 'god', 'sara', 'zammy', 'guthix',
            'decorative', 'castle wars', 'heraldic'
        ]
        
        # Items that are likely part of equipment sets
        relevant_items = []
        
        for item in mapping:
            try:
                # Must have pricing data
                if item.id not in all_prices:
                    continue
                    
                price_data = all_prices[item.id]
                if not price_data.has_valid_prices:
                    continue
                
                item_name_lower = item.name.lower()
                
                # Enhanced filtering with multiple criteria
                is_relevant = False
                
                # 1. Direct keyword match
                if any(keyword in item_name_lower for keyword in relevant_keywords):
                    is_relevant = True
                
                # 2. High value items that might be parts of expensive sets
                elif price_data.best_sell_price > 100000:  # 100k+ GP items
                    # Look for equipment-related words
                    equipment_words = ['helm', 'body', 'legs', 'shield', 'sword', 'staff', 'bow', 'crossbow']
                    if any(word in item_name_lower for word in equipment_words):
                        is_relevant = True
                
                # 3. Items with "(e)" or special suffixes that might be enhanced versions
                elif any(suffix in item_name_lower for suffix in ['(e)', '(t)', '(g)', '(s)', '(i)']):
                    is_relevant = True
                
                # 4. Items that are part of known set families
                elif any(family in item_name_lower for family in [
                    'dharok', 'ahrim', 'karil', 'torag', 'verac', 'guthan',  # Barrows
                    'bandos', 'armadyl', 'saradomin', 'zamorak',  # God wars
                    'void', 'elite void', 'superior',  # Special sets
                    'graceful', 'robes of darkness', 'infinity',  # Other sets
                    'crystal', 'dragonstone', 'obsidian'  # Material sets
                ]):
                    is_relevant = True
                
                if is_relevant:
                    # Exclude junk items and unusable items
                    exclusions = [
                        'broken', 'damaged', 'rusty', 'poisoned', 'noted', 'dummy',
                        'placeholder', 'null', 'test', 'unused', 'beta', 'removed'
                    ]
                    if not any(junk in item_name_lower for junk in exclusions):
                        relevant_items.append({
                            'id': item.id,
                            'name': item.name,
                            'examine': getattr(item, 'examine', ''),
                            'members': getattr(item, 'members', True),
                            'high_alch': getattr(item, 'highalch', 0),
                            'low_alch': getattr(item, 'lowalch', 0),
                            'ge_limit': getattr(item, 'limit', 0),
                            'buy_price': price_data.best_buy_price,
                            'sell_price': price_data.best_sell_price,
                            'age_hours': price_data.age_hours
                        })
            except Exception as e:
                logger.debug(f"Error processing item: {e}")
                continue
        
        # Sort by value for better AI analysis
        relevant_items.sort(key=lambda x: x['buy_price'], reverse=True)
        
        # Limit to top items to prevent context overflow
        return relevant_items[:200]  # Top 200 most valuable relevant items
    
    def _prioritize_items_for_analysis(self, items: List[Dict]) -> List[Dict]:
        """Prioritize items for AI analysis to get best results from early chunks."""
        
        def get_priority_score(item):
            score = 0
            name_lower = item['name'].lower()
            
            # High priority for known valuable sets
            if any(valuable in name_lower for valuable in [
                'barrows', 'bandos', 'armadyl', 'saradomin', 'zamorak', 
                'third-age', 'gilded', 'void', 'torva', 'pernix', 'virtus'
            ]):
                score += 1000
            
            # Medium priority for common sets
            elif any(common in name_lower for common in [
                'dragon', 'rune', 'adamant', 'mithril', 'steel', 'iron', 'bronze',
                'dragonhide', 'mystic', 'graceful', 'infinity'
            ]):
                score += 500
            
            # Priority based on item value
            score += min(item['sell_price'] / 1000, 500)  # Up to 500 points for price
            
            # Priority for items that look like sets
            if 'set' in name_lower:
                score += 300
            
            # Priority for complete armor pieces
            if any(piece in name_lower for piece in ['helm', 'body', 'legs', 'shield']):
                score += 100
            
            # Bonus for items with good GE limits (more tradeable)
            if item.get('ge_limit', 0) > 0:
                score += min(item['ge_limit'] / 10, 100)
            
            return score
        
        # Sort by priority score (highest first)
        prioritized = sorted(items, key=get_priority_score, reverse=True)
        
        # Log top priority items for debugging
        if prioritized:
            logger.info(f"Top priority items: {[item['name'] for item in prioritized[:5]]}")
        
        return prioritized
    
    async def _create_ai_analysis_context(
        self, 
        relevant_items: List[Dict],
        all_prices: Dict,
        wiki_client: RuneScapeWikiAPIClient
    ) -> str:
        """Create comprehensive context for AI analysis."""
        
        # Group items by likely categories for better analysis
        armor_sets = []
        individual_pieces = []
        weapons = []
        
        for item in relevant_items:
            name_lower = item['name'].lower()
            
            if 'set' in name_lower and 'armour' in name_lower:
                armor_sets.append(item)
            elif any(armor in name_lower for armor in ['helm', 'platebody', 'platelegs', 'chainbody', 'robe']):
                individual_pieces.append(item)
            elif any(weapon in name_lower for weapon in ['sword', 'axe', 'mace', 'staff', 'bow']):
                weapons.append(item)
        
        # Get sample volume data for high-value items
        volume_samples = []
        for item in relevant_items[:20]:  # Sample top 20 items
            try:
                timeseries = await wiki_client.get_timeseries(item['id'], "6h")
                if timeseries:
                    volume_samples.append({
                        'name': item['name'],
                        'trading_volume': sum(getattr(ts, 'total_volume', 0) for ts in timeseries[-5:]),
                        'price_stability': self._calculate_price_stability(timeseries)
                    })
            except Exception as e:
                logger.debug(f"Failed to get volume for {item['name']}: {e}")
        
        # Create comprehensive analysis context
        context = f"""
# OSRS Set Combining & Trading Opportunity Analysis

## Market Data Summary
- Total items analyzed: {len(relevant_items)}
- Armor sets found: {len(armor_sets)}
- Individual pieces found: {len(individual_pieces)}
- Weapons found: {len(weapons)}
- Items with volume data: {len(volume_samples)}

## High-Value Armor Sets Available
"""
        
        for armor_set in armor_sets[:10]:
            context += f"- {armor_set['name']}: {armor_set['buy_price']:,} GP (buy) / {armor_set['sell_price']:,} GP (sell)\n"
        
        context += "\n## High-Value Individual Pieces\n"
        for piece in individual_pieces[:15]:
            context += f"- {piece['name']}: {piece['buy_price']:,} GP (buy) / {piece['sell_price']:,} GP (sell)\n"
        
        context += "\n## Volume & Liquidity Data\n"
        for vol in volume_samples[:10]:
            context += f"- {vol['name']}: Volume: {vol['trading_volume']}, Stability: {vol['price_stability']}\n"
        
        context += f"""

## Analysis Request
Please analyze this OSRS market data to identify profitable set combining opportunities.

Focus on:
1. **Set Combining**: Buying individual armor pieces and combining into complete sets
2. **Set Decombining**: Buying complete armor sets and selling individual pieces  
3. **Cross-Set Arbitrage**: Price differences between similar items from different sets
4. **Upgrade Chains**: Profitable upgrade paths (bronze → iron → steel → mithril → adamant → rune)

Consider:
- Grand Exchange tax (1% on sales over 100 GP)
- Trading volume and liquidity
- Price stability and market conditions
- Capital requirements vs profit potential
- Risk assessment based on data freshness

Identify the top 10-20 most profitable opportunities with specific buy/sell strategies.
"""
        
        return context
    
    def _calculate_price_stability(self, timeseries: List) -> str:
        """Calculate price stability from timeseries data."""
        if len(timeseries) < 3:
            return "unknown"
        
        try:
            prices = []
            for ts in timeseries[-10:]:  # Last 10 data points
                if hasattr(ts, 'volume_weighted_price') and ts.volume_weighted_price:
                    prices.append(ts.volume_weighted_price)
            
            if len(prices) < 3:
                return "insufficient_data"
            
            # Calculate coefficient of variation
            avg_price = sum(prices) / len(prices)
            variance = sum((p - avg_price) ** 2 for p in prices) / len(prices)
            std_dev = variance ** 0.5
            cv = std_dev / avg_price if avg_price > 0 else 1
            
            if cv < 0.05:
                return "very_stable"
            elif cv < 0.1:
                return "stable"
            elif cv < 0.2:
                return "moderate"
            else:
                return "volatile"
                
        except Exception:
            return "unknown"
    
    async def _get_ai_opportunity_analysis(
        self,
        context: str,
        min_profit: int,
        max_capital: int
    ) -> str:
        """Get AI analysis of trading opportunities."""
        
        prompt = f"""
{context}

CONSTRAINTS:
- Minimum profit: {min_profit:,} GP
- Maximum capital: {max_capital:,} GP
- Focus on realistic, executable strategies
- Include Grand Exchange tax calculations
- Consider liquidity and risk factors

Please provide a detailed analysis in JSON format with this structure:

{{
    "opportunities": [
        {{
            "name": "Strategy name",
            "type": "combining|decombining|arbitrage", 
            "description": "Detailed explanation",
            "items_to_buy": [
                {{"name": "Item name", "id": "item_id", "quantity": 1, "price": 123456}}
            ],
            "items_to_sell": [
                {{"name": "Item name", "id": "item_id", "quantity": 1, "price": 123456}}
            ],
            "profit_before_tax": 123456,
            "ge_tax": 1234,
            "net_profit": 123456,
            "required_capital": 123456,
            "profit_margin_pct": 12.34,
            "risk_level": "low|medium|high",
            "confidence": 0.85,
            "reasoning": "Why this opportunity exists",
            "execution_steps": ["Step 1", "Step 2", "Step 3"],
            "market_conditions": "Current market assessment"
        }}
    ],
    "market_summary": "Overall market conditions and trends",
    "recommendations": ["General trading advice"]
}}

Identify the most profitable opportunities based on the real market data provided.
"""
        
        try:
            async with httpx.AsyncClient(timeout=self.ai_timeout) as client:
                response = await client.post(
                    f"{self.ollama_base_url}/api/generate",
                    json={
                        "model": self.analysis_model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.2,  # Lower temperature for more consistent analysis
                            "top_p": 0.9,
                            "num_predict": 2000
                        }
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result.get('response', '')
                else:
                    logger.error(f"AI analysis failed with status {response.status_code}")
                    return ""
                    
        except Exception as e:
            logger.error(f"Failed to get AI analysis: {e}")
            return ""
    
    async def _parse_ai_analysis_to_opportunities(
        self,
        ai_response: str,
        relevant_items: List[Dict],
        all_prices: Dict,
        wiki_client: RuneScapeWikiAPIClient,
        min_profit: int,
        max_capital: int,
        min_confidence: float
    ) -> List[DynamicSetOpportunity]:
        """Parse AI analysis response into structured opportunities."""
        
        opportunities = []
        
        try:
            # Try to extract JSON from AI response
            json_start = ai_response.find('{')
            json_end = ai_response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = ai_response[json_start:json_end]
                ai_data = json.loads(json_str)
                
                for opp_data in ai_data.get('opportunities', []):
                    try:
                        # Validate opportunity meets criteria
                        if (opp_data.get('net_profit', 0) >= min_profit and
                            opp_data.get('required_capital', 0) <= max_capital and
                            opp_data.get('confidence', 0) >= min_confidence):
                            
                            # Create structured opportunity
                            opportunity = DynamicSetOpportunity(
                                set_name=opp_data.get('name', 'Unknown Opportunity'),
                                set_type=opp_data.get('type', 'unknown'),
                                strategy=opp_data.get('type', 'unknown'),
                                
                                primary_items=opp_data.get('items_to_buy', []),
                                secondary_items=opp_data.get('items_to_sell', []),
                                
                                profit_gp=opp_data.get('net_profit', 0),
                                profit_margin_pct=opp_data.get('profit_margin_pct', 0),
                                required_capital=opp_data.get('required_capital', 0),
                                risk_assessment=opp_data.get('risk_level', 'unknown'),
                                
                                ai_confidence=opp_data.get('confidence', 0.5),
                                ai_reasoning=opp_data.get('reasoning', ''),
                                market_conditions=opp_data.get('market_conditions', ''),
                                execution_difficulty=self._assess_execution_difficulty(opp_data),
                                
                                volume_score=await self._calculate_opportunity_volume_score(
                                    opp_data, wiki_client
                                ),
                                liquidity_assessment='unknown',
                                price_stability='unknown',
                                data_freshness=0.5
                            )
                            
                            opportunities.append(opportunity)
                            
                    except Exception as e:
                        logger.warning(f"Failed to parse opportunity: {e}")
                        continue
                        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            # Fallback: create basic opportunities from text analysis
            opportunities = self._create_fallback_opportunities(ai_response, relevant_items)
        
        return opportunities[:25]  # Limit to top 25 opportunities
    
    def _assess_execution_difficulty(self, opp_data: Dict) -> str:
        """Assess execution difficulty based on opportunity data."""
        
        num_items = len(opp_data.get('items_to_buy', [])) + len(opp_data.get('items_to_sell', []))
        capital_required = opp_data.get('required_capital', 0)
        
        if num_items <= 2 and capital_required < 5_000_000:
            return "easy"
        elif num_items <= 4 and capital_required < 20_000_000:
            return "medium"
        else:
            return "complex"
    
    async def _calculate_opportunity_volume_score(
        self, 
        opp_data: Dict,
        wiki_client: RuneScapeWikiAPIClient
    ) -> float:
        """Calculate volume score for opportunity items."""
        
        try:
            all_items = opp_data.get('items_to_buy', []) + opp_data.get('items_to_sell', [])
            volume_scores = []
            
            for item in all_items[:5]:  # Limit to prevent timeout
                if 'id' in item:
                    timeseries = await wiki_client.get_timeseries(int(item['id']), "1h")
                    if timeseries and len(timeseries) > 0:
                        avg_volume = sum(getattr(ts, 'total_volume', 0) for ts in timeseries) / len(timeseries)
                        # Normalize volume score (1000+ volume = 1.0 score)
                        volume_scores.append(min(1.0, avg_volume / 1000))
            
            return sum(volume_scores) / len(volume_scores) if volume_scores else 0.5
            
        except Exception as e:
            logger.debug(f"Failed to calculate volume score: {e}")
            return 0.5
    
    def _create_fallback_opportunities(self, ai_text: str, relevant_items: List[Dict]) -> List[DynamicSetOpportunity]:
        """Create basic opportunities if AI JSON parsing fails."""
        
        # Simple fallback: find high-spread items
        opportunities = []
        
        for item in relevant_items[:10]:
            buy_price = item['buy_price']
            sell_price = item['sell_price']
            
            if buy_price > 0 and sell_price > 0:
                spread = sell_price - buy_price
                margin_pct = (spread / buy_price * 100) if buy_price > 0 else 0
                
                if spread > 5000 and margin_pct > 5:  # Basic profitability check
                    opportunity = DynamicSetOpportunity(
                        set_name=f"{item['name']} Arbitrage",
                        set_type='individual_item',
                        strategy='arbitrage',
                        
                        primary_items=[item],
                        secondary_items=[],
                        
                        profit_gp=spread,
                        profit_margin_pct=margin_pct,
                        required_capital=buy_price,
                        risk_assessment='medium',
                        
                        ai_confidence=0.3,  # Low confidence for fallback
                        ai_reasoning='Basic price spread analysis',
                        market_conditions='unknown',
                        execution_difficulty='easy',
                        
                        volume_score=0.5,
                        liquidity_assessment='unknown',
                        price_stability='unknown',
                        data_freshness=item['age_hours']
                    )
                    
                    opportunities.append(opportunity)
        
        return opportunities
    
    async def _get_ai_analysis_with_retry(
        self,
        context: str,
        min_profit: int,
        max_capital: int,
        chunk_num: int
    ) -> List[str]:
        """Get AI analysis with retry logic and error handling."""
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"AI analysis attempt {attempt + 1}/{self.max_retries} for chunk {chunk_num}")
                
                # Use faster model for chunks to reduce timeout risk
                model = self.fast_model if chunk_num > 1 else self.analysis_model
                
                ai_response = await self._get_ai_opportunity_analysis_with_model(
                    context, min_profit, max_capital, model
                )
                
                if ai_response and ai_response.strip():
                    # Parse the response and extract opportunities
                    opportunities = self._extract_opportunities_from_response(ai_response)
                    if opportunities:
                        logger.info(f"Successfully extracted {len(opportunities)} opportunities from chunk {chunk_num}")
                        return opportunities
                
                logger.warning(f"Empty or invalid AI response for chunk {chunk_num}, attempt {attempt + 1}")
                
            except Exception as e:
                logger.error(f"AI analysis failed for chunk {chunk_num}, attempt {attempt + 1}: {e}")
                
                # Wait before retry
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(min(2 ** attempt, 10))  # Exponential backoff
        
        # If all retries failed, return empty list
        logger.error(f"All AI analysis attempts failed for chunk {chunk_num}")
        return []
    
    async def _get_ai_opportunity_analysis_with_model(
        self,
        context: str,
        min_profit: int,
        max_capital: int,
        model: str
    ) -> str:
        """Get AI analysis using specified model."""
        
        prompt = f"""
{context}

CONSTRAINTS:
- Minimum profit: {min_profit:,} GP
- Maximum capital: {max_capital:,} GP
- Focus on realistic, executable strategies
- Include Grand Exchange tax calculations
- Consider liquidity and risk factors

Please provide a detailed analysis in JSON format with this structure:

{{
    "opportunities": [
        {{
            "name": "Strategy name",
            "type": "combining|decombining|arbitrage", 
            "description": "Detailed explanation",
            "items_to_buy": [
                {{"name": "Item name", "id": "item_id", "quantity": 1, "price": 123456}}
            ],
            "items_to_sell": [
                {{"name": "Item name", "id": "item_id", "quantity": 1, "price": 123456}}
            ],
            "profit_before_tax": 123456,
            "ge_tax": 1234,
            "net_profit": 123456,
            "required_capital": 123456,
            "profit_margin_pct": 12.34,
            "risk_level": "low|medium|high",
            "confidence": 0.85,
            "reasoning": "Why this opportunity exists",
            "execution_steps": ["Step 1", "Step 2", "Step 3"],
            "market_conditions": "Current market assessment"
        }}
    ],
    "market_summary": "Overall market conditions and trends",
    "recommendations": ["General trading advice"]
}}

Identify the most profitable opportunities based on the real market data provided.
"""
        
        try:
            async with httpx.AsyncClient(timeout=self.ai_timeout) as client:
                response = await client.post(
                    f"{self.ollama_base_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.2,  # Lower temperature for more consistent analysis
                            "top_p": 0.9,
                            "num_predict": 1500 if model == self.fast_model else 2000
                        }
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result.get('response', '')
                else:
                    logger.error(f"AI analysis failed with status {response.status_code} for model {model}")
                    return ""
                    
        except Exception as e:
            logger.error(f"AI analysis request failed for model {model}: {e}")
            return ""
    
    def _extract_opportunities_from_response(self, ai_response: str) -> List[str]:
        """Extract opportunities from AI response, handling various formats."""
        
        opportunities = []
        
        try:
            # Try to parse as JSON first
            if '{' in ai_response and '}' in ai_response:
                # Extract JSON part
                start = ai_response.find('{')
                end = ai_response.rfind('}') + 1
                json_part = ai_response[start:end]
                
                parsed = json.loads(json_part)
                if 'opportunities' in parsed:
                    opportunities = parsed['opportunities']
                
        except json.JSONDecodeError:
            # If JSON parsing fails, try to extract structured text
            logger.warning("Failed to parse AI response as JSON, attempting text extraction")
            
            # Look for opportunity patterns in text
            lines = ai_response.split('\n')
            current_opportunity = {}
            
            for line in lines:
                line = line.strip()
                if 'profit' in line.lower() and any(char.isdigit() for char in line):
                    # Found a line with profit information
                    opportunities.append(line)
        
        return opportunities
    
    def _combine_chunk_results(self, all_opportunities: List[List[str]]) -> str:
        """Combine results from multiple chunks into a single analysis."""
        
        if not all_opportunities:
            return ""
        
        # Flatten the list of opportunities
        flattened = []
        for chunk_opps in all_opportunities:
            flattened.extend(chunk_opps)
        
        if not flattened:
            return ""
        
        # Create a combined JSON structure
        combined_result = {
            "opportunities": flattened,
            "market_summary": f"Analysis of {len(flattened)} opportunities across multiple chunks",
            "recommendations": ["Results combined from chunked analysis"]
        }
        
        try:
            return json.dumps(combined_result, indent=2)
        except Exception as e:
            logger.error(f"Failed to combine chunk results: {e}")
            # Return a simple text format as fallback
            return f"Combined {len(flattened)} opportunities from chunks"


# Global service instance
dynamic_set_discovery_service = DynamicSetDiscoveryService()