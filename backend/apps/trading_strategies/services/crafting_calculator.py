from typing import List, Dict, Optional, Tuple
from decimal import Decimal
from django.db import transaction
from apps.prices.models import PriceSnapshot, ProfitCalculation
from apps.items.models import Item
from apps.trading_strategies.models import TradingStrategy, CraftingOpportunity, StrategyType
from services.runescape_wiki_client import SyncRuneScapeWikiAPIClient
import logging
import asyncio

logger = logging.getLogger(__name__)


class CraftingCalculator:
    """
    Calculates profitable crafting opportunities like slaughter bracelets.
    
    Analyzes material costs vs finished product prices to find crafting
    strategies with high profit margins. The user's friend made significant
    profits crafting slaughter bracelets with 200% returns.
    """
    
    # Crafting recipes with materials and skill requirements
    CRAFTING_RECIPES = {
        # Jewelry crafting (high profit potential)
        'Slaughter bracelet': {
            'product_id': 21183,  # Slaughter bracelet
            'skill': 'Crafting',
            'level': 75,
            'materials': [
                {'id': 21721, 'name': 'Bracelet of slaughter', 'quantity': 1},
                {'id': 21637, 'name': 'Hydra leather', 'quantity': 1},
            ],
            'crafting_time': 60,  # seconds
        },
        'Expeditious bracelet': {
            'product_id': 21177,  # Expeditious bracelet  
            'skill': 'Crafting',
            'level': 75,
            'materials': [
                {'id': 21715, 'name': 'Expeditious bracelet', 'quantity': 1},
                {'id': 21637, 'name': 'Hydra leather', 'quantity': 1},
            ],
            'crafting_time': 60,
        },
        
        # Dragonhide crafting
        'Green d\'hide body': {
            'product_id': 1135,
            'skill': 'Crafting', 
            'level': 63,
            'materials': [
                {'id': 1753, 'name': 'Green dragonhide', 'quantity': 3},
                {'id': 1734, 'name': 'Thread', 'quantity': 1},
            ],
            'crafting_time': 45,
        },
        'Blue d\'hide body': {
            'product_id': 2499,
            'skill': 'Crafting',
            'level': 71, 
            'materials': [
                {'id': 2505, 'name': 'Blue dragonhide', 'quantity': 3},
                {'id': 1734, 'name': 'Thread', 'quantity': 1},
            ],
            'crafting_time': 45,
        },
        'Red d\'hide body': {
            'product_id': 2501,
            'skill': 'Crafting',
            'level': 77,
            'materials': [
                {'id': 2507, 'name': 'Red dragonhide', 'quantity': 3}, 
                {'id': 1734, 'name': 'Thread', 'quantity': 1},
            ],
            'crafting_time': 45,
        },
        'Black d\'hide body': {
            'product_id': 2503,
            'skill': 'Crafting',
            'level': 84,
            'materials': [
                {'id': 2509, 'name': 'Black dragonhide', 'quantity': 3},
                {'id': 1734, 'name': 'Thread', 'quantity': 1},
            ],
            'crafting_time': 45,
        },
        
        # Battlestaves (popular for XP and profit)
        'Air battlestaff': {
            'product_id': 1397,
            'skill': 'Crafting',
            'level': 66,
            'materials': [
                {'id': 1391, 'name': 'Battlestaff', 'quantity': 1},
                {'id': 573, 'name': 'Air orb', 'quantity': 1},
            ],
            'crafting_time': 30,
        },
        'Water battlestaff': {
            'product_id': 1395,
            'skill': 'Crafting',
            'level': 66,
            'materials': [
                {'id': 1391, 'name': 'Battlestaff', 'quantity': 1},
                {'id': 571, 'name': 'Water orb', 'quantity': 1},
            ],
            'crafting_time': 30,
        },
        'Earth battlestaff': {
            'product_id': 1399,
            'skill': 'Crafting', 
            'level': 66,
            'materials': [
                {'id': 1391, 'name': 'Battlestaff', 'quantity': 1},
                {'id': 575, 'name': 'Earth orb', 'quantity': 1},
            ],
            'crafting_time': 30,
        },
        'Fire battlestaff': {
            'product_id': 1393,
            'skill': 'Crafting',
            'level': 66, 
            'materials': [
                {'id': 1391, 'name': 'Battlestaff', 'quantity': 1},
                {'id': 569, 'name': 'Fire orb', 'quantity': 1},
            ],
            'crafting_time': 30,
        },
        
        # Fletching (bows and arrows)
        'Magic longbow': {
            'product_id': 859,
            'skill': 'Fletching',
            'level': 85,
            'materials': [
                {'id': 1513, 'name': 'Magic logs', 'quantity': 1},
                {'id': 1777, 'name': 'Bow string', 'quantity': 1},
            ],
            'crafting_time': 45,
        },
        'Yew longbow': {
            'product_id': 855,
            'skill': 'Fletching', 
            'level': 70,
            'materials': [
                {'id': 1515, 'name': 'Yew logs', 'quantity': 1},
                {'id': 1777, 'name': 'Bow string', 'quantity': 1},
            ],
            'crafting_time': 45,
        },
        
        # Smithing (platebodies and weapons)
        'Rune platebody': {
            'product_id': 1127,
            'skill': 'Smithing',
            'level': 99,
            'materials': [
                {'id': 2363, 'name': 'Runite bar', 'quantity': 5},
            ],
            'crafting_time': 120,
        },
        'Adamant platebody': {
            'product_id': 1123,
            'skill': 'Smithing',
            'level': 88,
            'materials': [
                {'id': 2361, 'name': 'Adamantite bar', 'quantity': 5},
            ],
            'crafting_time': 90,
        },
        
        # Cooking (profitable foods)
        'Shark': {
            'product_id': 385,  # Cooked shark
            'skill': 'Cooking',
            'level': 80,
            'materials': [
                {'id': 383, 'name': 'Raw shark', 'quantity': 1},
            ],
            'crafting_time': 15,
        },
        'Monkfish': {
            'product_id': 7946,  # Cooked monkfish
            'skill': 'Cooking', 
            'level': 62,
            'materials': [
                {'id': 7944, 'name': 'Raw monkfish', 'quantity': 1},
            ],
            'crafting_time': 12,
        },
    }
    
    def __init__(self, min_profit_margin: float = 0.10, min_profit_gp: int = 2000):
        """
        Initialize the crafting calculator with volume-weighted AI scoring.
        
        Args:
            min_profit_margin: Minimum profit margin (0.10 = 10%)
            min_profit_gp: Minimum profit per craft in GP
        """
        self.min_profit_margin = min_profit_margin
        self.min_profit_gp = min_profit_gp
        self.wiki_client = SyncRuneScapeWikiAPIClient()
    
    def calculate_opportunities(self) -> List[Dict]:
        """
        Calculate all profitable crafting opportunities.
        
        Returns:
            List of profitable crafting opportunities
        """
        opportunities = []
        
        for recipe_name, recipe_data in self.CRAFTING_RECIPES.items():
            try:
                opportunity = self._analyze_crafting_recipe(recipe_name, recipe_data)
                if opportunity:
                    opportunities.append(opportunity)
            except Exception as e:
                logger.warning(f"Error analyzing recipe {recipe_name}: {e}")
        
        # Sort by AI-weighted profit per hour (highest first) for maximum profit potential
        opportunities.sort(key=lambda x: x['ai_weighted_profit_per_hour'], reverse=True)
        
        return opportunities
    
    def _get_volume_analysis_for_recipe(self, recipe_data: Dict) -> Dict:
        """
        Get volume analysis for all items in a crafting recipe.
        
        Args:
            recipe_data: Recipe data with product and materials
            
        Returns:
            Dictionary with volume analysis for product and materials
        """
        volume_analysis = {
            'product_volume': {},
            'material_volumes': {},
            'overall_liquidity_score': 0.0,
            'ai_volume_score': 0.0
        }
        
        try:
            # Analyze product volume
            product_id = recipe_data['product_id']
            product_volume = self.wiki_client.get_volume_analysis(product_id, duration="24h")
            volume_analysis['product_volume'] = product_volume
            
            # Analyze material volumes
            for material in recipe_data['materials']:
                material_id = material['id']
                material_volume = self.wiki_client.get_volume_analysis(material_id, duration="24h")
                volume_analysis['material_volumes'][material_id] = material_volume
            
            # Calculate overall liquidity score
            all_volumes = [product_volume] + list(volume_analysis['material_volumes'].values())
            liquidity_scores = [vol.get('liquidity_score', 0.0) for vol in all_volumes]
            volume_analysis['overall_liquidity_score'] = sum(liquidity_scores) / len(liquidity_scores) if liquidity_scores else 0.0
            
            # Calculate AI volume score (emphasizes product liquidity and material availability)
            product_liquidity = product_volume.get('liquidity_score', 0.0)
            product_activity = 1.0 if product_volume.get('trading_activity') in ['very_active', 'active'] else 0.5
            
            # Material availability (average liquidity of materials)
            material_liquidity_avg = sum(vol.get('liquidity_score', 0.0) for vol in volume_analysis['material_volumes'].values()) / len(volume_analysis['material_volumes']) if volume_analysis['material_volumes'] else 0.0
            
            # Volume trend bonus (increasing trend is better)
            product_trend_bonus = 1.2 if product_volume.get('volume_trend') == 'increasing' else 1.0
            
            # AI score: weighted combination favoring product sellability
            ai_volume_score = (
                product_liquidity * 0.6 * product_activity * product_trend_bonus +
                material_liquidity_avg * 0.4
            )
            
            volume_analysis['ai_volume_score'] = min(ai_volume_score, 1.0)  # Cap at 1.0
            
        except Exception as e:
            logger.warning(f"Volume analysis failed for recipe {recipe_data.get('product_id', 'unknown')}: {e}")
            # Return safe defaults on failure
            volume_analysis['ai_volume_score'] = 0.1
            volume_analysis['overall_liquidity_score'] = 0.1
        
        return volume_analysis
    
    def _analyze_crafting_recipe(self, recipe_name: str, recipe_data: Dict) -> Optional[Dict]:
        """
        Analyze a specific crafting recipe for profitability.
        
        Args:
            recipe_name: Name of the crafted item
            recipe_data: Recipe data with materials and requirements
            
        Returns:
            Opportunity dictionary or None if not profitable
        """
        product_id = recipe_data['product_id']
        materials = recipe_data['materials']
        skill_level = recipe_data['level']
        skill_name = recipe_data['skill']
        crafting_time = recipe_data['crafting_time']
        
        # Get product price
        product_price_data = self._get_item_price(product_id)
        if not product_price_data:
            return None
        
        product_price = product_price_data['low']  # Price we sell at
        
        # Calculate materials cost
        materials_cost = 0
        materials_data = []
        
        for material in materials:
            material_price_data = self._get_item_price(material['id'])
            if not material_price_data:
                return None
            
            material_cost = material_price_data['high'] * material['quantity']  # Price we buy at
            materials_cost += material_cost
            
            materials_data.append({
                'id': material['id'],
                'name': material['name'],
                'quantity': material['quantity'],
                'unit_price': material_price_data['high'],
                'total_cost': material_cost,
            })
        
        # Calculate profit
        profit_per_craft = product_price - materials_cost
        
        if profit_per_craft < self.min_profit_gp:
            return None
        
        profit_margin_pct = (profit_per_craft / materials_cost * 100) if materials_cost > 0 else 0
        
        if profit_margin_pct < (self.min_profit_margin * 100):
            return None
        
        # Calculate hourly metrics
        crafts_per_hour = 3600 // crafting_time  # 3600 seconds in an hour
        profit_per_hour = profit_per_craft * crafts_per_hour
        
        # Get volume analysis for AI-weighted scoring
        volume_analysis = self._get_volume_analysis_for_recipe(recipe_data)
        
        # Calculate AI-weighted metrics
        ai_volume_score = volume_analysis['ai_volume_score']
        liquidity_score = volume_analysis['overall_liquidity_score']
        
        # AI-weighted profit per hour (considers volume and liquidity)
        ai_weighted_profit_per_hour = profit_per_hour * ai_volume_score
        
        # Market confidence score (combines profit margin and volume analysis)
        margin_confidence = min(1.0, profit_margin_pct / 50.0)  # Cap at 50% margin for confidence
        volume_confidence = ai_volume_score
        market_confidence = (margin_confidence * 0.5 + volume_confidence * 0.5) * 100
        
        # Risk assessment enhanced with volume data
        if profit_margin_pct > 50 and ai_volume_score > 0.7:
            enhanced_risk_level = 'low'
        elif profit_margin_pct > 25 and ai_volume_score > 0.4:
            enhanced_risk_level = 'medium'
        elif profit_margin_pct > 10 and ai_volume_score > 0.2:
            enhanced_risk_level = 'high'
        else:
            enhanced_risk_level = 'extreme'
        
        return {
            'recipe_name': recipe_name,
            'product_id': product_id,
            'product_price': product_price,
            'materials_cost': materials_cost,
            'materials_data': materials_data,
            'profit_per_craft': profit_per_craft,
            'profit_margin_pct': round(profit_margin_pct, 4),
            'skill_name': skill_name,
            'required_skill_level': skill_level,
            'crafting_time_seconds': crafting_time,
            'max_crafts_per_hour': crafts_per_hour,
            'profit_per_hour': profit_per_hour,
            # AI-enhanced metrics
            'ai_volume_score': round(ai_volume_score, 4),
            'liquidity_score': round(liquidity_score, 4),
            'ai_weighted_profit_per_hour': round(ai_weighted_profit_per_hour, 0),
            'market_confidence': round(market_confidence, 2),
            'enhanced_risk_level': enhanced_risk_level,
            'volume_analysis': volume_analysis,
        }
    
    def _get_item_price(self, item_id: int) -> Optional[Dict]:
        """
        Get current price data for an item, preferring real-time OSRS Wiki data.
        
        Args:
            item_id: OSRS item ID
            
        Returns:
            Price data dictionary or None if not available
        """
        try:
            # Try to get real-time data from OSRS Wiki API first
            try:
                wiki_prices = self.wiki_client.get_latest_prices(item_id=item_id)
                if wiki_prices and item_id in wiki_prices:
                    wiki_data = wiki_prices[item_id]
                    if wiki_data.has_valid_prices:
                        return {
                            'high': wiki_data.best_buy_price,  # Price we buy at
                            'low': wiki_data.best_sell_price,  # Price we sell at
                            'highTime': wiki_data.high_time or 0,
                            'lowTime': wiki_data.low_time or 0,
                            'data_source': 'osrs_wiki_api',
                            'data_quality': wiki_data.data_quality,
                            'age_hours': wiki_data.age_hours
                        }
            except Exception as wiki_error:
                logger.debug(f"OSRS Wiki API unavailable for item {item_id}: {wiki_error}")
            
            # Fallback to cached data from ProfitCalculation
            profit_calc = ProfitCalculation.objects.filter(item_id=item_id).first()
            if profit_calc and profit_calc.current_buy_price and profit_calc.current_sell_price:
                return {
                    'high': profit_calc.current_buy_price or 0,
                    'low': profit_calc.current_sell_price or 0,
                    'highTime': profit_calc.daily_volume or 0,
                    'lowTime': profit_calc.hourly_volume or 0,
                    'data_source': 'cached_profit_calc'
                }
            
            # Final fallback to latest PriceSnapshot
            price_obj = PriceSnapshot.objects.filter(item_id=item_id).order_by('-created_at').first()
            if not price_obj:
                return None
            
            return {
                'high': price_obj.high_price or 0,
                'low': price_obj.low_price or 0,
                'highTime': price_obj.high_price_volume or 0,
                'lowTime': price_obj.low_price_volume or 0,
                'data_source': 'price_snapshot'
            }
        except Exception as e:
            logger.warning(f"Error getting price for item {item_id}: {e}")
            return None
    
    @transaction.atomic
    def create_strategy_opportunities(self, opportunities: List[Dict]) -> int:
        """
        Create TradingStrategy and CraftingOpportunity records.
        
        Args:
            opportunities: List of opportunity dictionaries
            
        Returns:
            Number of strategies created
        """
        created_count = 0
        
        for opp in opportunities:
            try:
                profit_per_craft = opp['profit_per_craft']
                profit_margin_pct = Decimal(str(opp['profit_margin_pct']))
                
                # Calculate capital requirements (materials for 100 crafts)
                base_materials_cost = opp['materials_cost']
                min_capital = base_materials_cost * 50   # 50 crafts worth
                recommended_capital = base_materials_cost * 200  # 200 crafts worth
                
                # Use actual crafting time
                estimated_time_minutes = opp['crafting_time_seconds'] / 60
                
                # Calculate confidence based on margin and skill requirements
                margin_score = min(1.0, opp['profit_margin_pct'] / 100)  # Cap at 100% margin
                skill_score = 1.0 - (opp['required_skill_level'] / 100)  # Lower level = higher score
                confidence = (margin_score * 0.7 + skill_score * 0.3)
                
                # Risk assessment based on margin and skill level
                if opp['profit_margin_pct'] > 50 and opp['required_skill_level'] <= 75:
                    risk_level = 'low'
                elif opp['profit_margin_pct'] > 25 and opp['required_skill_level'] <= 85:
                    risk_level = 'medium'
                elif opp['profit_margin_pct'] > 10:
                    risk_level = 'high'
                else:
                    risk_level = 'extreme'
                
                # Create or update strategy
                strategy, created = TradingStrategy.objects.get_or_create(
                    strategy_type=StrategyType.CRAFTING,
                    name=f"Craft {opp['recipe_name']}",
                    defaults={
                        'description': (
                            f"Craft {opp['recipe_name']} using materials costing {base_materials_cost:,} GP, "
                            f"sell for {opp['product_price']:,} GP. "
                            f"Profit: {profit_per_craft:,} GP per craft ({opp['profit_margin_pct']:.1f}% margin). "
                            f"Requires {opp['skill_name']} level {opp['required_skill_level']}. "
                            f"Potential: {opp['profit_per_hour']:,} GP/hour with {opp['max_crafts_per_hour']} crafts/hour."
                        ),
                        'potential_profit_gp': profit_per_craft,
                        'profit_margin_pct': profit_margin_pct,
                        'risk_level': risk_level,
                        'min_capital_required': min_capital,
                        'recommended_capital': recommended_capital,
                        'optimal_market_condition': 'stable',
                        'estimated_time_minutes': int(estimated_time_minutes),
                        'confidence_score': Decimal(str(confidence)),
                        'is_active': True,
                        'strategy_data': {
                            'craft_type': 'production',
                            'skill_requirement': f"{opp['skill_name']} {opp['required_skill_level']}",
                            'materials_count': len(opp['materials_data']),
                            'hourly_potential': opp['profit_per_hour'],
                        }
                    }
                )
                
                if not created:
                    # Update existing strategy
                    strategy.potential_profit_gp = profit_per_craft
                    strategy.profit_margin_pct = profit_margin_pct
                    strategy.risk_level = risk_level
                    strategy.min_capital_required = min_capital
                    strategy.recommended_capital = recommended_capital
                    strategy.confidence_score = Decimal(str(confidence))
                    strategy.estimated_time_minutes = int(estimated_time_minutes)
                    strategy.save()
                
                # Create or update crafting opportunity
                craft_opp, _ = CraftingOpportunity.objects.update_or_create(
                    product_id=opp['product_id'],
                    defaults={
                        'strategy': strategy,
                        'product_name': opp['recipe_name'],
                        'product_price': opp['product_price'],
                        'materials_cost': opp['materials_cost'],
                        'materials_data': opp['materials_data'],
                        'required_skill_level': opp['required_skill_level'],
                        'skill_name': opp['skill_name'],
                        'profit_per_craft': profit_per_craft,
                        'profit_margin_pct': profit_margin_pct,
                        'crafting_time_seconds': opp['crafting_time_seconds'],
                        'max_crafts_per_hour': opp['max_crafts_per_hour'],
                    }
                )
                
                created_count += 1
                logger.info(f"Created crafting strategy: {strategy.name}")
                
            except Exception as e:
                logger.error(f"Error creating strategy for {opp['recipe_name']}: {e}")
        
        return created_count
    
    def scan_and_create_opportunities(self) -> int:
        """
        Full scan: calculate opportunities and create strategy records.
        
        Returns:
            Number of strategies created
        """
        logger.info("Starting crafting opportunity calculation...")
        
        opportunities = self.calculate_opportunities()
        logger.info(f"Found {len(opportunities)} crafting opportunities")
        
        if opportunities:
            created_count = self.create_strategy_opportunities(opportunities)
            logger.info(f"Created {created_count} crafting strategies")
            return created_count
        
        return 0