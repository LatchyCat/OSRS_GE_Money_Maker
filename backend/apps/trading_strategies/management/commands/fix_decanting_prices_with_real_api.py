"""
Fix decanting opportunities using real RuneScape Wiki API prices.

This command replaces fake sample prices with actual market data from the
RuneScape Wiki API, ensuring all displayed prices match real GE prices.
"""

import asyncio
import logging
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.trading_strategies.models import DecantingOpportunity, TradingStrategy
from services.runescape_wiki_client import RuneScapeWikiAPIClient

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Fix decanting opportunities with real RuneScape Wiki API prices'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear-existing',
            action='store_true',
            help='Clear existing opportunities before adding new ones'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without saving to database'
        )

    def handle(self, *args, **options):
        self.clear_existing = options['clear_existing']
        self.dry_run = options['dry_run']
        
        self.stdout.write(
            self.style.SUCCESS('🔧 Fixing decanting prices with real API data...')
        )
        
        if self.clear_existing:
            if not self.dry_run:
                self.stdout.write('🧹 Clearing existing opportunities...')
                DecantingOpportunity.objects.all().delete()
            else:
                self.stdout.write('🔍 DRY RUN: Would clear existing opportunities')
        
        # Create real opportunities with API prices
        opportunities = self.create_real_opportunities()
        
        if self.dry_run:
            self.stdout.write(
                self.style.WARNING('🔍 DRY RUN - Showing what would be created:')
            )
            for opp in opportunities:
                profit = opp['profit_per_conversion'] 
                if profit > 0:
                    self.stdout.write(
                        f"✅ {opp['name']}: {profit} GP profit "
                        f"(Buy: {opp['from_price']} GP, Sell: {opp['to_price']} GP each)"
                    )
                else:
                    self.stdout.write(
                        f"❌ {opp['name']}: {profit} GP loss - would skip"
                    )
        else:
            saved_count = self.save_opportunities(opportunities)
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Successfully created {saved_count} opportunities with real API prices!'
                )
            )

    def create_real_opportunities(self):
        """Create opportunities using real RuneScape Wiki API prices."""
        self.stdout.write('📡 Fetching real prices from RuneScape Wiki API...')
        
        # Define potion families with their CORRECT item IDs (verified from /mapping)
        potion_families = {
            'Prayer potion': [(2434, 4), (139, 3), (141, 2), (143, 1)],  # (item_id, doses)
            'Divine super combat potion': [(23685, 4), (23688, 3), (23691, 2), (23694, 1)],
            'Divine bastion potion': [(24635, 4), (24638, 3), (24641, 2), (24644, 1)],
            'Divine battlemage potion': [(24623, 4), (24626, 3), (24629, 2), (24632, 1)],
            'Super restore': [(3024, 4), (3026, 3), (3028, 2), (3030, 1)],  
            'Stamina potion': [(12625, 4), (12627, 3), (12629, 2), (12631, 1)],  # CORRECTED: 12631 is 1-dose
            'Saradomin brew': [(6685, 4), (6687, 3), (6689, 2), (6691, 1)],  
            'Super combat potion': [(12695, 4), (12697, 3), (12699, 2), (12701, 1)],  
        }
        
        # Get all item IDs we need to fetch prices for
        all_item_ids = []
        for family_items in potion_families.values():
            for item_id, doses in family_items:
                all_item_ids.append(item_id)
        
        # Fetch prices from API
        prices = self.fetch_prices_batch(all_item_ids)
        
        opportunities = []
        
        for family_name, items in potion_families.items():
            # Sort by doses descending  
            items.sort(key=lambda x: x[1], reverse=True)
            
            # Generate decanting combinations
            for i, (from_item_id, from_dose) in enumerate(items):
                for j, (to_item_id, to_dose) in enumerate(items):
                    if from_dose > to_dose:  # Only higher to lower dose
                        opportunity = self.calculate_real_opportunity(
                            family_name, 
                            from_item_id, from_dose, 
                            to_item_id, to_dose, 
                            prices
                        )
                        if opportunity:
                            opportunities.append(opportunity)
        
        # Sort by profit and return only profitable ones
        profitable_opportunities = [opp for opp in opportunities if opp['profit_per_conversion'] > 0]
        profitable_opportunities.sort(key=lambda x: x['profit_per_conversion'], reverse=True)
        
        self.stdout.write(f'📊 Found {len(profitable_opportunities)} profitable opportunities out of {len(opportunities)} total combinations')
        
        return profitable_opportunities[:20]  # Top 20 most profitable

    def fetch_prices_batch(self, item_ids):
        """Fetch prices for multiple items using the API."""
        import asyncio
        
        async def fetch_all_prices():
            try:
                client = RuneScapeWikiAPIClient()
                async with client:
                    # Fetch all prices at once (no item_id parameter = all items)
                    all_prices = await client.get_latest_prices()
                    
                    # Extract only the prices we need
                    needed_prices = {}
                    for item_id in item_ids:
                        if item_id in all_prices:
                            price_data = all_prices[item_id]
                            if price_data.has_valid_prices:
                                needed_prices[item_id] = price_data.best_buy_price
                            else:
                                logger.warning(f"No valid price for item {item_id}")
                        else:
                            logger.warning(f"Item {item_id} not found in API response")
                    
                    return needed_prices
                    
            except Exception as e:
                logger.error(f"Error fetching prices: {e}")
                return {}
        
        # Run async function
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're in Django context, run in thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, fetch_all_prices())
                    return future.result(timeout=60)
            else:
                return loop.run_until_complete(fetch_all_prices())
        except RuntimeError:
            return asyncio.run(fetch_all_prices())

    def calculate_real_opportunity(self, family_name, from_item_id, from_dose, to_item_id, to_dose, prices):
        """Calculate opportunity using real API prices with volume validation."""
        # Get prices
        from_price = prices.get(from_item_id)
        to_price = prices.get(to_item_id)
        
        if not from_price or not to_price:
            return None
        
        # Get volume analysis for the target item
        try:
            client = RuneScapeWikiAPIClient()
            import asyncio
            import concurrent.futures
            
            def get_volume_data(item_id):
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # We're in Django context, run in thread
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = executor.submit(asyncio.run, self._get_volume_async(item_id))
                            return future.result(timeout=10)
                    else:
                        return loop.run_until_complete(self._get_volume_async(item_id))
                except RuntimeError:
                    return asyncio.run(self._get_volume_async(item_id))
                except Exception as e:
                    logger.warning(f"Failed to get volume data for item {item_id}: {e}")
                    return {}
            
            # Get volume data for target item (where we sell)
            volume_analysis = get_volume_data(to_item_id)
            
        except Exception as e:
            logger.warning(f"Volume analysis failed for item {to_item_id}: {e}")
            volume_analysis = {}
        
        # CRITICAL: Add price sanity check to prevent losses
        if from_price <= 0 or to_price <= 0:
            logger.warning(f"Invalid price data for {family_name}: from_price={from_price}, to_price={to_price}")
            return None
            
        # Calculate OSRS decanting mathematics
        doses_gained = from_dose // to_dose  # How many lower-dose potions we get
        
        # Use volume-weighted pricing if available
        if volume_analysis.get('avg_volume_per_hour', 0) > 0:
            # Get recent timeseries data for more accurate pricing
            try:
                recent_timeseries = asyncio.run(self._get_recent_timeseries(to_item_id))
                if recent_timeseries:
                    # Use volume-weighted average from recent trading
                    volume_weighted_prices = [ts.volume_weighted_price for ts in recent_timeseries[-5:] if ts.volume_weighted_price]
                    if volume_weighted_prices:
                        to_price = int(sum(volume_weighted_prices) / len(volume_weighted_prices))
                        logger.debug(f"Using volume-weighted price {to_price} for item {to_item_id}")
            except Exception as e:
                logger.debug(f"Could not get volume-weighted price for {to_item_id}: {e}")
        
        # Revenue calculation  
        cost = from_price
        revenue = to_price * doses_gained
        profit = revenue - cost
        
        # CRITICAL: Validate profit makes sense (detect data errors)
        profit_margin = (profit / cost) * 100 if cost > 0 else 0
        
        # Log suspicious profits for debugging
        if profit_margin > 100:  # More than 100% profit is suspicious
            logger.warning(f"SUSPICIOUS HIGH PROFIT for {family_name} ({from_dose}→{to_dose}): {profit} GP ({profit_margin:.1f}%)")
            logger.warning(f"  Buy: {cost} GP, Sell: {doses_gained}×{to_price} = {revenue} GP")
            
        if profit_margin < -10:  # More than 10% loss is definitely wrong
            logger.warning(f"LOSS DETECTED for {family_name} ({from_dose}→{to_dose}): {profit} GP ({profit_margin:.1f}% loss)")
            logger.warning(f"  Buy: {cost} GP, Sell: {doses_gained}×{to_price} = {revenue} GP")
            return None  # Skip opportunities that would cause losses
        
        # Volume-based profit adjustment
        liquidity_score = volume_analysis.get('liquidity_score', 1.0)
        trading_activity = volume_analysis.get('trading_activity', 'unknown')
        
        # Adjust profit based on trading activity
        if trading_activity == 'inactive':
            # High-risk, reduce expected profit by 80%
            profit = profit * 0.2
            confidence_modifier = 0.3
        elif trading_activity == 'low':
            # Medium-risk, reduce expected profit by 50%
            profit = profit * 0.5
            confidence_modifier = 0.5
        elif trading_activity == 'moderate':
            # Some risk, reduce expected profit by 20%
            profit = profit * 0.8
            confidence_modifier = 0.7
        elif trading_activity in ['active', 'very_active']:
            # Low risk, keep full profit
            confidence_modifier = 0.9
        else:
            # Unknown activity, be conservative
            profit = profit * 0.6
            confidence_modifier = 0.4
        
        # Skip unprofitable opportunities after volume adjustment
        if profit <= 0:
            return None
        
        # Calculate metrics with volume context
        profit_per_hour = profit * 800  # Conservative conversion rate
        roi_percentage = (profit / cost) * 100
        profit_margin = roi_percentage
        
        # Volume-based confidence scoring
        volume_score = min(volume_analysis.get('avg_volume_per_hour', 0) / 100, 1.0)  # Normalize to 0-1
        stability_score = 1.0 - min(volume_analysis.get('price_stability', 1.0), 1.0)  # Invert, lower is better
        overall_confidence = (confidence_modifier * 0.5 + volume_score * 0.3 + stability_score * 0.2) * 100
        
        return {
            'name': f"{family_name} ({from_dose}→{to_dose})",
            'family': family_name,
            'item_id': to_item_id,  # Use target item as primary
            'from_dose': from_dose,
            'to_dose': to_dose,
            'from_price': from_price,
            'to_price': to_price,
            'profit_per_conversion': profit,
            'profit_per_hour': profit_per_hour,
            'roi_percentage': roi_percentage,
            'profit_margin': profit_margin,
            'volume_analysis': volume_analysis,
            'trading_activity': trading_activity,
            'liquidity_score': liquidity_score,
            'confidence_score': overall_confidence,
        }
    
    async def _get_volume_async(self, item_id):
        """Get volume analysis asynchronously."""
        client = RuneScapeWikiAPIClient()
        async with client:
            return await client.get_volume_analysis(item_id, "24h")
    
    async def _get_recent_timeseries(self, item_id):
        """Get recent timeseries data asynchronously."""
        client = RuneScapeWikiAPIClient()
        async with client:
            return await client.get_timeseries(item_id, "1h")

    def save_opportunities(self, opportunities):
        """Save opportunities to database."""
        saved_count = 0
        
        with transaction.atomic():
            # Create strategy
            strategy, created = TradingStrategy.objects.get_or_create(
                name="Real-Price Decanting Opportunities",
                defaults={
                    'strategy_type': 'decanting',
                    'description': 'Decanting opportunities using real RuneScape Wiki API prices',
                    'potential_profit_gp': 1000,  # Average
                    'profit_margin_pct': Decimal('15.00'),  # Conservative
                    'risk_level': 'low',
                    'min_capital_required': 10000,
                    'recommended_capital': 100000,
                    'optimal_market_condition': 'stable',
                    'estimated_time_minutes': 1,
                    'confidence_score': Decimal('0.90'),  # High confidence with real data
                    'is_active': True,
                }
            )
            
            for opp_data in opportunities:
                try:
                    opportunity = DecantingOpportunity.objects.create(
                        strategy=strategy,
                        item_id=opp_data['item_id'],
                        item_name=opp_data['name'],
                        from_dose=opp_data['from_dose'],
                        to_dose=opp_data['to_dose'],
                        from_dose_price=opp_data['from_price'],
                        to_dose_price=opp_data['to_price'],
                        from_dose_volume=100,  # API doesn't provide volume
                        to_dose_volume=50,     # Conservative estimate
                        profit_per_conversion=opp_data['profit_per_conversion'],
                        profit_per_hour=opp_data['profit_per_hour'],
                        # Volume analysis fields
                        trading_activity=opp_data.get('trading_activity', 'unknown'),
                        liquidity_score=opp_data.get('liquidity_score', 0.0),
                        confidence_score=opp_data.get('confidence_score', 0.0),
                        volume_analysis_data=opp_data.get('volume_analysis', {}),
                    )
                    saved_count += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to save opportunity {opp_data['name']}: {e}")
        
        return saved_count