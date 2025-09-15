from typing import List, Dict, Optional
from decimal import Decimal
from django.db import transaction
from django.db.models import Q
from apps.prices.models import PriceSnapshot, ProfitCalculation
from apps.items.models import Item
from apps.trading_strategies.models import TradingStrategy, FlippingOpportunity, StrategyType
import logging

logger = logging.getLogger(__name__)


class FlippingScanner:
    """
    Scans for profitable flipping opportunities on the Grand Exchange.
    
    Flipping involves buying items at low prices and selling at high prices.
    The scanner identifies items with good margins and decent volume for
    quick profit turnaround.
    """
    
    def __init__(self, min_margin_gp: int = 1000, min_margin_pct: float = 5.0, 
                 min_price: int = 10000, max_price: int = 100000000):
        """
        Initialize the flipping scanner.
        
        Args:
            min_margin_gp: Minimum margin in GP
            min_margin_pct: Minimum margin percentage
            min_price: Minimum item price to consider (filters out junk)
            max_price: Maximum item price to consider (capital constraints)
        """
        self.min_margin_gp = min_margin_gp
        self.min_margin_pct = min_margin_pct
        self.min_price = min_price
        self.max_price = max_price
    
    def scan_flipping_opportunities(self) -> List[Dict]:
        """
        Scan all items for profitable flipping opportunities.
        
        Returns:
            List of profitable flipping opportunities
        """
        opportunities = []
        
        # Get all items with recent price data and decent margins
        price_queryset = ProfitCalculation.objects.filter(
            current_buy_price__gte=self.min_price,
            current_buy_price__lte=self.max_price,
            current_sell_price__gt=0,
            current_buy_price__gt=0
        ).select_related('item')
        
        logger.info(f"Scanning {price_queryset.count()} items for flipping opportunities...")
        
        for price_data in price_queryset:
            try:
                opportunity = self._analyze_flipping_opportunity(price_data)
                if opportunity:
                    opportunities.append(opportunity)
            except Exception as e:
                logger.warning(f"Error analyzing item {price_data.item_id}: {e}")
        
        # Sort by margin percentage (highest first)
        opportunities.sort(key=lambda x: x['margin_percentage'], reverse=True)
        
        return opportunities[:200]  # Limit to top 200 opportunities
    
    def _analyze_flipping_opportunity(self, price_data: ProfitCalculation) -> Optional[Dict]:
        """
        Analyze a specific item for flipping profitability.
        
        Args:
            price_data: ItemPrice object with current market data
            
        Returns:
            Opportunity dictionary or None if not profitable
        """
        buy_price = price_data.current_buy_price  # Price we buy at (instant buy)
        sell_price = price_data.current_sell_price  # Price we sell at (instant sell)
        
        if not buy_price or not sell_price or buy_price >= sell_price:
            return None
        
        # Calculate margins
        margin = sell_price - buy_price
        margin_percentage = (margin / buy_price * 100) if buy_price > 0 else 0
        
        # Apply filters
        if margin < self.min_margin_gp:
            return None
        
        if margin_percentage < self.min_margin_pct:
            return None
        
        # Get volume data (transaction frequency)
        buy_volume = price_data.daily_volume or 0
        sell_volume = price_data.hourly_volume or 0
        
        # Calculate price stability (how often prices change)
        price_stability = self._calculate_price_stability(price_data)
        
        # Estimate flip time based on volume
        flip_time = self._estimate_flip_time(buy_volume, sell_volume)
        
        # Calculate recommended quantity based on volume and capital
        recommended_qty = self._calculate_recommended_quantity(
            buy_price, buy_volume, sell_volume
        )
        
        return {
            'item_id': price_data.item.id,
            'item_name': price_data.item.name,
            'buy_price': buy_price,
            'sell_price': sell_price,
            'margin': margin,
            'margin_percentage': round(margin_percentage, 4),
            'buy_volume': buy_volume,
            'sell_volume': sell_volume,
            'price_stability': price_stability,
            'estimated_flip_time_minutes': flip_time,
            'recommended_quantity': recommended_qty,
        }
    
    def _calculate_price_stability(self, price_data: ProfitCalculation) -> float:
        """
        Calculate price stability score (0-1, higher is more stable).
        
        Args:
            price_data: ItemPrice object
            
        Returns:
            Stability score between 0 and 1
        """
        # For now, use a simple heuristic based on volume consistency
        # More sophisticated analysis could use historical price variance
        
        buy_vol = price_data.daily_volume or 0
        sell_vol = price_data.hourly_volume or 0
        
        if buy_vol == 0 or sell_vol == 0:
            return 0.1  # Low stability if no volume data
        
        # Stability is higher when buy/sell volumes are balanced
        volume_ratio = min(buy_vol, sell_vol) / max(buy_vol, sell_vol)
        
        # Items with consistent volume are more stable
        avg_volume = (buy_vol + sell_vol) / 2
        volume_score = min(1.0, avg_volume / 1000)  # Normalize to 0-1
        
        return (volume_ratio * 0.6 + volume_score * 0.4)
    
    def _estimate_flip_time(self, buy_volume: int, sell_volume: int) -> int:
        """
        Estimate time to complete a flip in minutes.
        
        Args:
            buy_volume: Buy transaction frequency
            sell_volume: Sell transaction frequency
            
        Returns:
            Estimated flip time in minutes
        """
        # Higher volume = faster flips
        avg_volume = (buy_volume + sell_volume) / 2 if buy_volume and sell_volume else 1
        
        if avg_volume >= 1000:
            return 5   # Very high volume, almost instant
        elif avg_volume >= 500:
            return 15  # High volume, quick flip
        elif avg_volume >= 100:
            return 30  # Medium volume
        elif avg_volume >= 50:
            return 60  # Lower volume
        else:
            return 120 # Low volume, slow flip
    
    def _calculate_recommended_quantity(self, price: int, buy_vol: int, sell_vol: int) -> int:
        """
        Calculate recommended quantity to flip.
        
        Args:
            price: Item price
            buy_vol: Buy volume
            sell_vol: Sell volume
            
        Returns:
            Recommended quantity
        """
        # Base quantity on available volume and reasonable capital usage
        min_volume = min(buy_vol, sell_vol) if buy_vol and sell_vol else 1
        
        # Don't recommend more than what market can handle
        max_by_volume = max(1, min_volume // 10)  # Use 10% of available volume
        
        # Don't recommend more than reasonable capital (10M GP)
        max_capital = 10000000
        max_by_capital = max(1, max_capital // price)
        
        return min(max_by_volume, max_by_capital, 100)  # Cap at 100 items
    
    @transaction.atomic
    def create_strategy_opportunities(self, opportunities: List[Dict]) -> int:
        """
        Create TradingStrategy and FlippingOpportunity records.
        
        Args:
            opportunities: List of opportunity dictionaries
            
        Returns:
            Number of strategies created
        """
        created_count = 0
        
        for opp in opportunities:
            try:
                margin = opp['margin']
                margin_pct = Decimal(str(opp['margin_percentage']))
                
                # Calculate capital requirements
                min_capital = opp['buy_price'] * opp['recommended_quantity']
                recommended_capital = min_capital * 2  # 2x for safety margin
                
                # Calculate confidence based on stability and margin
                stability_score = opp['price_stability']
                margin_score = min(1.0, opp['margin_percentage'] / 50)  # Cap at 50%
                volume_score = min(1.0, (opp['buy_volume'] + opp['sell_volume']) / 2000)
                confidence = (stability_score * 0.4 + margin_score * 0.3 + volume_score * 0.3)
                
                # Risk assessment
                if opp['margin_percentage'] > 20 and stability_score > 0.6:
                    risk_level = 'low'
                elif opp['margin_percentage'] > 10 and stability_score > 0.4:
                    risk_level = 'medium'
                elif opp['margin_percentage'] > 5:
                    risk_level = 'high'
                else:
                    risk_level = 'extreme'
                
                # Create or update strategy
                strategy, created = TradingStrategy.objects.get_or_create(
                    strategy_type=StrategyType.FLIPPING,
                    name=f"Flip {opp['item_name']}",
                    defaults={
                        'description': (
                            f"Buy {opp['item_name']} for {opp['buy_price']:,} GP, "
                            f"sell for {opp['sell_price']:,} GP. "
                            f"Margin: {margin:,} GP ({opp['margin_percentage']:.1f}%). "
                            f"Recommended quantity: {opp['recommended_quantity']} items. "
                            f"Estimated flip time: {opp['estimated_flip_time_minutes']} minutes."
                        ),
                        'potential_profit_gp': margin * opp['recommended_quantity'],
                        'profit_margin_pct': margin_pct,
                        'risk_level': risk_level,
                        'min_capital_required': min_capital,
                        'recommended_capital': recommended_capital,
                        'optimal_market_condition': 'stable',
                        'estimated_time_minutes': opp['estimated_flip_time_minutes'],
                        'confidence_score': Decimal(str(confidence)),
                        'is_active': True,
                        'strategy_data': {
                            'item_type': 'flipping',
                            'price_stability': opp['price_stability'],
                            'volume_ratio': min(opp['buy_volume'], opp['sell_volume']) / max(opp['buy_volume'], opp['sell_volume']) if opp['buy_volume'] and opp['sell_volume'] else 0,
                        }
                    }
                )
                
                if not created:
                    # Update existing strategy
                    strategy.potential_profit_gp = margin * opp['recommended_quantity']
                    strategy.profit_margin_pct = margin_pct
                    strategy.risk_level = risk_level
                    strategy.min_capital_required = min_capital
                    strategy.recommended_capital = recommended_capital
                    strategy.confidence_score = Decimal(str(confidence))
                    strategy.estimated_time_minutes = opp['estimated_flip_time_minutes']
                    strategy.save()
                
                # Create or update flipping opportunity
                flip_opp, _ = FlippingOpportunity.objects.update_or_create(
                    item_id=opp['item_id'],
                    defaults={
                        'strategy': strategy,
                        'item_name': opp['item_name'],
                        'buy_price': opp['buy_price'],
                        'sell_price': opp['sell_price'],
                        'margin': margin,
                        'margin_percentage': margin_pct,
                        'buy_volume': opp['buy_volume'],
                        'sell_volume': opp['sell_volume'],
                        'price_stability': Decimal(str(opp['price_stability'])),
                        'estimated_flip_time_minutes': opp['estimated_flip_time_minutes'],
                        'recommended_quantity': opp['recommended_quantity'],
                    }
                )
                
                created_count += 1
                if created_count <= 10:  # Log first 10 to avoid spam
                    logger.info(f"Created flipping strategy: {strategy.name}")
                
            except Exception as e:
                logger.error(f"Error creating strategy for {opp['item_name']}: {e}")
        
        return created_count
    
    def scan_and_create_opportunities(self) -> int:
        """
        Full scan: find opportunities and create strategy records.
        
        Returns:
            Number of strategies created
        """
        logger.info("Starting flipping opportunity scan...")
        
        opportunities = self.scan_flipping_opportunities()
        logger.info(f"Found {len(opportunities)} flipping opportunities")
        
        if opportunities:
            created_count = self.create_strategy_opportunities(opportunities)
            logger.info(f"Created {created_count} flipping strategies")
            return created_count
        
        return 0