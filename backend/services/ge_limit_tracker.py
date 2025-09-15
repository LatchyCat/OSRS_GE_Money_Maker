"""
Grand Exchange Buy Limit Tracker

Advanced GE trading limit management system that provides:
- Real-time buy limit tracking with 4-hour reset timers
- User-specific limit management and history  
- Smart diversification suggestions
- Limit utilization optimization
- Multi-account coordination (for legitimate alts)
- Trading opportunity scheduling based on limit resets
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import transaction
from django.contrib.auth.models import User
from django.core.cache import cache
from asgiref.sync import sync_to_async
import json

from apps.items.models import Item
from apps.prices.models import ProfitCalculation
from apps.realtime_engine.models import GELimitEntry
from services.intelligent_cache import intelligent_cache
from services.dynamic_risk_engine import dynamic_risk_engine

logger = logging.getLogger(__name__)


class GELimitTracker:
    """
    Advanced Grand Exchange buy limit tracking and management system.
    """
    
    def __init__(self):
        self.cache_prefix = "ge_limits:"
        self.reset_check_interval = 300  # Check for resets every 5 minutes
        
        # Diversification thresholds
        self.max_single_item_portfolio_pct = 25.0  # Max 25% in single item
        self.recommended_active_items = 8  # Recommend tracking 8+ items
        
    async def track_purchase(self, user_id: int, item_id: int, quantity: int, 
                           price_per_item: int) -> Dict[str, Any]:
        """
        Track a GE purchase and update limits.
        
        Args:
            user_id: Django user ID
            item_id: OSRS item ID  
            quantity: Quantity purchased
            price_per_item: Price per item in GP
            
        Returns:
            Dictionary with tracking results
        """
        logger.debug(f"📦 Tracking GE purchase: User {user_id}, Item {item_id}, Qty {quantity}")
        
        try:
            # Get or create limit entry
            limit_entry = await self._get_or_create_limit_entry(user_id, item_id)
            
            if not limit_entry:
                return {'error': 'Failed to create/retrieve limit entry'}
            
            # Check if limit would be exceeded
            if limit_entry.quantity_bought + quantity > limit_entry.max_limit:
                return {
                    'error': 'Purchase would exceed GE buy limit',
                    'current_quantity': limit_entry.quantity_bought,
                    'max_limit': limit_entry.max_limit,
                    'attempted_quantity': quantity,
                    'remaining_limit': limit_entry.remaining_limit
                }
            
            # Check if limit period has expired and reset if needed
            if limit_entry.is_limit_expired():
                await sync_to_async(limit_entry.reset_limit)()
            
            # Update the limit entry
            await self._update_limit_entry(limit_entry, quantity, price_per_item)
            
            # Calculate updated metrics
            updated_entry = await self._get_limit_entry(user_id, item_id)
            
            # Generate recommendations
            recommendations = await self._generate_purchase_recommendations(user_id, updated_entry)
            
            # Cache updated data
            await self._cache_user_limits(user_id)
            
            return {
                'success': True,
                'item_id': item_id,
                'item_name': updated_entry.item.name,
                'quantity_purchased': quantity,
                'total_investment': quantity * price_per_item,
                'current_usage': {
                    'quantity_bought': updated_entry.quantity_bought,
                    'max_limit': updated_entry.max_limit,
                    'remaining_limit': updated_entry.remaining_limit,
                    'utilization_pct': updated_entry.limit_utilization_pct,
                    'minutes_until_reset': updated_entry.minutes_until_reset
                },
                'recommendations': recommendations
            }
            
        except Exception as e:
            logger.error(f"❌ Purchase tracking failed: {e}")
            return {'error': str(e)}
    
    async def get_user_limits_overview(self, user_id: int) -> Dict[str, Any]:
        """
        Get comprehensive overview of user's GE limits.
        
        Args:
            user_id: Django user ID
            
        Returns:
            Dictionary with complete limits overview
        """
        logger.debug(f"📊 Getting limits overview for user {user_id}")
        
        try:
            # Check cache first
            cache_key = f"{self.cache_prefix}overview:{user_id}"
            cached_overview = intelligent_cache.get(cache_key, tiers=["hot", "warm"])
            
            if cached_overview:
                return cached_overview
            
            # Get all active limit entries for user
            limit_entries = await self._get_user_limit_entries(user_id)
            
            # Process each entry
            active_limits = []
            total_investment = 0
            limits_near_max = 0
            limits_ready_for_reset = 0
            
            for entry in limit_entries:
                # Check if expired and reset
                if entry.is_limit_expired():
                    await sync_to_async(entry.reset_limit)()
                    entry.refresh_from_db()
                
                limit_data = {
                    'item_id': entry.item.item_id,
                    'item_name': entry.item.name,
                    'quantity_bought': entry.quantity_bought,
                    'max_limit': entry.max_limit,
                    'remaining_limit': entry.remaining_limit,
                    'utilization_pct': round(entry.limit_utilization_pct, 1),
                    'total_investment': entry.total_investment,
                    'average_price': entry.average_purchase_price,
                    'minutes_until_reset': entry.minutes_until_reset,
                    'reset_time': entry.limit_reset_time.isoformat(),
                    'is_limit_reached': entry.is_limit_reached
                }
                
                active_limits.append(limit_data)
                total_investment += entry.total_investment
                
                # Track statistics
                if entry.limit_utilization_pct >= 90:
                    limits_near_max += 1
                if entry.minutes_until_reset <= 30:
                    limits_ready_for_reset += 1
            
            # Sort by utilization (highest first)
            active_limits.sort(key=lambda x: x['utilization_pct'], reverse=True)
            
            # Calculate portfolio diversification
            diversification_score = await self._calculate_diversification_score(user_id, limit_entries)
            
            # Generate strategic recommendations
            strategic_recommendations = await self._generate_strategic_recommendations(
                user_id, limit_entries, total_investment
            )
            
            # Upcoming resets in next 2 hours
            upcoming_resets = [
                limit for limit in active_limits 
                if limit['minutes_until_reset'] <= 120
            ]
            
            overview = {
                'user_id': user_id,
                'timestamp': timezone.now().isoformat(),
                'summary': {
                    'total_active_items': len(active_limits),
                    'total_investment': total_investment,
                    'limits_near_max': limits_near_max,
                    'limits_ready_for_reset': limits_ready_for_reset,
                    'diversification_score': diversification_score
                },
                'active_limits': active_limits,
                'upcoming_resets': upcoming_resets,
                'strategic_recommendations': strategic_recommendations,
                'portfolio_analysis': await self._analyze_portfolio_balance(user_id, limit_entries)
            }
            
            # Cache the overview
            intelligent_cache.set(
                cache_key, 
                overview, 
                tier="warm", 
                tags=[f"user_{user_id}", "ge_limits", "overview"]
            )
            
            return overview
            
        except Exception as e:
            logger.error(f"❌ Limits overview failed for user {user_id}: {e}")
            return {'error': str(e)}
    
    async def suggest_diversification_opportunities(self, user_id: int, 
                                                  max_suggestions: int = 10) -> List[Dict[str, Any]]:
        """
        Suggest items for portfolio diversification based on profit potential and limits.
        
        Args:
            user_id: Django user ID
            max_suggestions: Maximum number of suggestions
            
        Returns:
            List of diversification suggestions
        """
        logger.debug(f"💡 Generating diversification suggestions for user {user_id}")
        
        try:
            # Get current user positions
            current_items = await self._get_user_tracked_items(user_id)
            current_item_ids = set(current_items)
            
            # Get profitable items not currently tracked
            profitable_items = await self._get_diversification_candidates(current_item_ids)
            
            suggestions = []
            
            for item_data in profitable_items[:max_suggestions]:
                # Calculate risk assessment
                risk_analysis = await dynamic_risk_engine.calculate_comprehensive_risk(item_data['item_id'])
                
                suggestion = {
                    'item_id': item_data['item_id'],
                    'item_name': item_data['item_name'],
                    'profit_per_item': item_data['profit_per_item'],
                    'profit_margin': item_data['profit_margin'],
                    'buy_limit': item_data['buy_limit'],
                    'estimated_daily_profit': item_data['estimated_daily_profit'],
                    'risk_score': risk_analysis.get('overall_risk_score', 50),
                    'risk_category': risk_analysis.get('risk_category', 'moderate'),
                    'diversification_benefit': self._calculate_diversification_benefit(
                        item_data, current_items
                    ),
                    'recommendation_strength': 'high'  # Would be calculated based on multiple factors
                }
                
                suggestions.append(suggestion)
            
            # Sort by diversification benefit and profit potential
            suggestions.sort(
                key=lambda x: (x['diversification_benefit'] * x['profit_per_item']), 
                reverse=True
            )
            
            return suggestions
            
        except Exception as e:
            logger.error(f"❌ Diversification suggestions failed: {e}")
            return []
    
    async def schedule_limit_resets(self, user_id: int) -> Dict[str, Any]:
        """
        Create a schedule of upcoming limit resets for planning.
        
        Args:
            user_id: Django user ID
            
        Returns:
            Dictionary with reset schedule
        """
        logger.debug(f"📅 Creating limit reset schedule for user {user_id}")
        
        try:
            limit_entries = await self._get_user_limit_entries(user_id)
            
            reset_schedule = []
            
            for entry in limit_entries:
                if not entry.is_limit_expired() and entry.quantity_bought > 0:
                    reset_info = {
                        'item_id': entry.item.item_id,
                        'item_name': entry.item.name,
                        'reset_time': entry.limit_reset_time.isoformat(),
                        'minutes_until_reset': entry.minutes_until_reset,
                        'current_investment': entry.total_investment,
                        'utilization_pct': entry.limit_utilization_pct,
                        'profit_potential_on_reset': await self._calculate_reset_profit_potential(entry)
                    }
                    reset_schedule.append(reset_info)
            
            # Sort by reset time (soonest first)
            reset_schedule.sort(key=lambda x: x['minutes_until_reset'])
            
            # Group by time periods
            next_hour = [r for r in reset_schedule if r['minutes_until_reset'] <= 60]
            next_4_hours = [r for r in reset_schedule if 60 < r['minutes_until_reset'] <= 240]
            later = [r for r in reset_schedule if r['minutes_until_reset'] > 240]
            
            return {
                'total_scheduled_resets': len(reset_schedule),
                'next_hour': next_hour,
                'next_4_hours': next_4_hours,
                'later': later,
                'total_capital_to_free': sum(r['current_investment'] for r in reset_schedule),
                'estimated_profit_potential': sum(r['profit_potential_on_reset'] for r in reset_schedule)
            }
            
        except Exception as e:
            logger.error(f"❌ Reset scheduling failed: {e}")
            return {'error': str(e)}
    
    # Helper methods
    
    @sync_to_async
    def _get_or_create_limit_entry(self, user_id: int, item_id: int) -> Optional[GELimitEntry]:
        """Get or create a limit entry for user and item."""
        try:
            user = User.objects.get(id=user_id)
            item = Item.objects.get(item_id=item_id)
            
            entry, created = GELimitEntry.objects.get_or_create(
                user=user,
                item=item,
                defaults={
                    'max_limit': item.limit or 100,  # Default to 100 if no limit set
                    'limit_reset_time': timezone.now() + timedelta(hours=4)
                }
            )
            
            return entry
            
        except (User.DoesNotExist, Item.DoesNotExist) as e:
            logger.error(f"User or item not found: {e}")
            return None
    
    @sync_to_async
    def _update_limit_entry(self, limit_entry: GELimitEntry, quantity: int, price_per_item: int):
        """Update limit entry with new purchase."""
        # Calculate new averages
        total_quantity = limit_entry.quantity_bought + quantity
        total_investment = limit_entry.total_investment + (quantity * price_per_item)
        
        # Update fields
        limit_entry.quantity_bought = total_quantity
        limit_entry.total_investment = total_investment
        limit_entry.average_purchase_price = total_investment // total_quantity if total_quantity > 0 else price_per_item
        limit_entry.is_limit_reached = (total_quantity >= limit_entry.max_limit)
        limit_entry.last_purchase_time = timezone.now()
        
        limit_entry.save()
    
    @sync_to_async
    def _get_limit_entry(self, user_id: int, item_id: int) -> Optional[GELimitEntry]:
        """Get a specific limit entry."""
        try:
            return GELimitEntry.objects.select_related('user', 'item').get(
                user_id=user_id, 
                item__item_id=item_id
            )
        except GELimitEntry.DoesNotExist:
            return None
    
    @sync_to_async
    def _get_user_limit_entries(self, user_id: int) -> List[GELimitEntry]:
        """Get all active limit entries for a user."""
        return list(
            GELimitEntry.objects.select_related('item')
            .filter(user_id=user_id, is_active=True)
            .order_by('-updated_at')
        )
    
    @sync_to_async
    def _get_user_tracked_items(self, user_id: int) -> List[int]:
        """Get list of item IDs currently tracked by user."""
        return list(
            GELimitEntry.objects.filter(user_id=user_id, is_active=True)
            .values_list('item__item_id', flat=True)
        )
    
    @sync_to_async  
    def _get_diversification_candidates(self, exclude_item_ids: set) -> List[Dict]:
        """Get profitable items for diversification (excluding already tracked items)."""
        candidates = ProfitCalculation.objects.filter(
            current_profit__gte=500,  # At least 500gp profit
            current_profit_margin__gte=5.0,  # At least 5% margin
            volume_category__in=['hot', 'warm', 'cool']  # Active trading
        ).exclude(
            item__item_id__in=exclude_item_ids
        ).select_related('item').order_by('-volume_weighted_score')[:50]
        
        return [
            {
                'item_id': calc.item.item_id,
                'item_name': calc.item.name,
                'profit_per_item': calc.current_profit,
                'profit_margin': calc.current_profit_margin,
                'buy_limit': calc.item.limit or 100,
                'estimated_daily_profit': calc.volume_adjusted_profit,
                'volume_category': calc.volume_category
            }
            for calc in candidates
        ]
    
    def _calculate_diversification_benefit(self, item_data: Dict, current_items: List[int]) -> float:
        """Calculate diversification benefit of adding this item."""
        # Simple diversification benefit calculation
        # In reality, this would consider correlations, categories, etc.
        base_benefit = 1.0
        
        # Higher profit = higher benefit
        profit_factor = min(2.0, item_data['profit_per_item'] / 1000)
        
        # Lower risk = higher benefit (would need risk data)
        # For now, assume medium benefit
        risk_factor = 1.0
        
        return base_benefit * profit_factor * risk_factor
    
    async def _calculate_diversification_score(self, user_id: int, limit_entries: List[GELimitEntry]) -> float:
        """Calculate portfolio diversification score (0-100)."""
        if not limit_entries:
            return 0.0
        
        # Number of items factor (more items = better diversification)
        item_count_score = min(50, len(limit_entries) * 6)  # Max 50 points for 8+ items
        
        # Investment distribution factor
        investments = [entry.total_investment for entry in limit_entries if entry.total_investment > 0]
        
        if not investments:
            return item_count_score
        
        total_investment = sum(investments)
        if total_investment == 0:
            return item_count_score
        
        # Calculate concentration (lower concentration = better diversification)
        max_investment_pct = max(investments) / total_investment * 100
        
        if max_investment_pct <= 15:
            concentration_score = 50  # Excellent diversification
        elif max_investment_pct <= 25:
            concentration_score = 40  # Good diversification
        elif max_investment_pct <= 40:
            concentration_score = 30  # Fair diversification
        else:
            concentration_score = 10  # Poor diversification
        
        return min(100, item_count_score + concentration_score)
    
    async def _generate_purchase_recommendations(self, user_id: int, 
                                              limit_entry: GELimitEntry) -> List[Dict]:
        """Generate recommendations after a purchase."""
        recommendations = []
        
        # Limit utilization warnings
        if limit_entry.limit_utilization_pct >= 90:
            recommendations.append({
                'type': 'limit_warning',
                'priority': 'high',
                'message': f'Buy limit nearly reached ({limit_entry.limit_utilization_pct:.1f}%). Consider diversifying to other items.',
                'action': 'diversify'
            })
        
        # Reset timing recommendations
        if limit_entry.minutes_until_reset <= 60:
            recommendations.append({
                'type': 'timing',
                'priority': 'medium',
                'message': f'Limit resets in {limit_entry.minutes_until_reset} minutes. Plan your next purchases.',
                'action': 'schedule'
            })
        
        return recommendations
    
    async def _generate_strategic_recommendations(self, user_id: int, limit_entries: List[GELimitEntry], 
                                               total_investment: int) -> List[Dict]:
        """Generate strategic recommendations for the user."""
        recommendations = []
        
        # Portfolio size recommendations
        if len(limit_entries) < self.recommended_active_items:
            recommendations.append({
                'type': 'diversification',
                'priority': 'medium',
                'message': f'Consider tracking more items for better diversification. Currently tracking {len(limit_entries)}, recommended: {self.recommended_active_items}+',
                'action': 'add_items'
            })
        
        # Investment concentration warnings
        if limit_entries:
            max_investment = max(entry.total_investment for entry in limit_entries)
            max_investment_pct = (max_investment / total_investment * 100) if total_investment > 0 else 0
            
            if max_investment_pct > self.max_single_item_portfolio_pct:
                recommendations.append({
                    'type': 'concentration_risk',
                    'priority': 'high',
                    'message': f'High concentration risk: {max_investment_pct:.1f}% in single item. Consider rebalancing.',
                    'action': 'rebalance'
                })
        
        return recommendations
    
    async def _analyze_portfolio_balance(self, user_id: int, limit_entries: List[GELimitEntry]) -> Dict:
        """Analyze portfolio balance and distribution."""
        if not limit_entries:
            return {'status': 'empty'}
        
        total_investment = sum(entry.total_investment for entry in limit_entries)
        
        # Calculate distribution
        distribution = []
        for entry in limit_entries:
            if entry.total_investment > 0:
                pct = (entry.total_investment / total_investment * 100)
                distribution.append({
                    'item_name': entry.item.name,
                    'investment': entry.total_investment,
                    'percentage': round(pct, 1)
                })
        
        # Sort by investment size
        distribution.sort(key=lambda x: x['investment'], reverse=True)
        
        return {
            'total_investment': total_investment,
            'item_count': len(distribution),
            'distribution': distribution,
            'largest_position_pct': distribution[0]['percentage'] if distribution else 0,
            'balance_score': await self._calculate_diversification_score(user_id, limit_entries)
        }
    
    async def _calculate_reset_profit_potential(self, limit_entry: GELimitEntry) -> int:
        """Calculate potential profit when limit resets."""
        try:
            profit_calc = await sync_to_async(
                lambda: getattr(limit_entry.item, 'profit_calc', None)
            )()
            
            if profit_calc and profit_calc.current_profit > 0:
                # Estimate profit for full limit usage
                return profit_calc.current_profit * limit_entry.max_limit
            
            return 0
            
        except Exception:
            return 0
    
    async def _cache_user_limits(self, user_id: int):
        """Cache user limit data for faster access."""
        cache_key = f"{self.cache_prefix}user_data:{user_id}"
        
        try:
            # Get fresh data
            overview = await self.get_user_limits_overview(user_id)
            
            # Cache with shorter TTL since this changes frequently  
            intelligent_cache.set(
                cache_key,
                overview,
                tier="hot",  # High-frequency access
                tags=[f"user_{user_id}", "ge_limits"]
            )
            
        except Exception as e:
            logger.error(f"Failed to cache user limits for {user_id}: {e}")


# Global GE limit tracker instance  
ge_limit_tracker = GELimitTracker()