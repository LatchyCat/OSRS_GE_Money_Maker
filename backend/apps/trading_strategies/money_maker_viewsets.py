"""
Money Maker API ViewSets
Comprehensive REST API endpoints for money making strategies and opportunities.
"""

import asyncio
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, Any, List

from django.db.models import Q, Count, Sum, Avg
from django.utils import timezone
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from asgiref.sync import sync_to_async

from .models import (
    MoneyMakerStrategy,
    BondFlippingStrategy, 
    AdvancedDecantingStrategy,
    EnhancedSetCombiningStrategy,
    RuneMagicStrategy
)
from .serializers import (
    MoneyMakerStrategySerializer,
    BondFlippingStrategySerializer,
    AdvancedDecantingStrategySerializer,
    EnhancedSetCombiningStrategySerializer,
    RuneMagicStrategySerializer
)
from services.money_maker_detector import MoneyMakerDetector
from services.capital_progression_advisor import CapitalProgressionAdvisor
from services.weird_gloop_client import WeirdGloopAPIClient, GrandExchangeTax
from .services.universal_opportunity_scanner import UniversalOpportunityScanner


class MoneyMakerStrategyViewSet(viewsets.ModelViewSet):
    """
    ViewSet for comprehensive money maker strategy management
    Based on your friend's 50M → 100M progression methods
    """
    
    queryset = MoneyMakerStrategy.objects.select_related('strategy').all()
    serializer_class = MoneyMakerStrategySerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = [
        'starting_capital', 'target_capital', 'scales_with_capital',
        'exploits_lazy_tax', 'strategy__strategy_type'
    ]
    search_fields = ['strategy__name', 'strategy__description']
    ordering_fields = [
        'hourly_profit_gp', 'success_rate_percentage', 'starting_capital',
        'capital_efficiency_multiplier', 'total_profit_realized'
    ]
    ordering = ['-hourly_profit_gp']
    
    def get_queryset(self):
        """Enhanced filtering for capital ranges and profit tiers"""
        queryset = super().get_queryset()
        
        # Capital range filtering
        min_capital = self.request.query_params.get('min_capital')
        max_capital = self.request.query_params.get('max_capital')
        if min_capital:
            queryset = queryset.filter(current_capital__gte=min_capital)
        if max_capital:
            queryset = queryset.filter(current_capital__lte=max_capital)
            
        # Hourly profit filtering
        min_hourly = self.request.query_params.get('min_hourly_profit')
        if min_hourly:
            queryset = queryset.filter(hourly_profit_gp__gte=min_hourly)
            
        # Success rate filtering
        min_success = self.request.query_params.get('min_success_rate')
        if min_success:
            queryset = queryset.filter(success_rate_percentage__gte=min_success)
            
        return queryset
    
    @action(detail=False, methods=['get'])
    def progression_tiers(self, request):
        """Get strategies organized by capital progression tiers"""
        tiers = {
            'starter': self.queryset.filter(starting_capital__lte=10_000_000),  # Under 10M
            'intermediate': self.queryset.filter(
                starting_capital__gt=10_000_000, 
                starting_capital__lte=50_000_000
            ),  # 10M-50M
            'advanced': self.queryset.filter(
                starting_capital__gt=50_000_000,
                starting_capital__lte=100_000_000  
            ),  # 50M-100M
            'expert': self.queryset.filter(starting_capital__gt=100_000_000),  # 100M+
        }
        
        result = {}
        for tier_name, tier_queryset in tiers.items():
            strategies = tier_queryset.order_by('-hourly_profit_gp')[:10]
            result[tier_name] = {
                'count': tier_queryset.count(),
                'avg_hourly_profit': tier_queryset.aggregate(
                    avg_profit=Avg('hourly_profit_gp')
                )['avg_profit'] or 0,
                'strategies': self.serializer_class(strategies, many=True).data
            }
            
        return Response(result)
    
    @action(detail=False, methods=['get'])
    def top_performers(self, request):
        """Get top performing strategies by various metrics"""
        limit = int(request.query_params.get('limit', 5))
        
        return Response({
            'highest_hourly_profit': self.serializer_class(
                self.queryset.order_by('-hourly_profit_gp')[:limit], many=True
            ).data,
            'best_success_rate': self.serializer_class(
                self.queryset.order_by('-success_rate_percentage')[:limit], many=True
            ).data,
            'most_capital_efficient': self.serializer_class(
                self.queryset.order_by('-capital_efficiency_multiplier')[:limit], many=True
            ).data,
            'best_lazy_tax_exploiters': self.serializer_class(
                self.queryset.filter(exploits_lazy_tax=True).order_by(
                    '-lazy_tax_premium_pct'
                )[:limit], many=True
            ).data
        })
    
    @action(detail=False, methods=['get'])
    def capital_scaling_analysis(self, request):
        """Analyze how strategies scale with increased capital"""
        capital_amount = int(request.query_params.get('capital', 50_000_000))
        
        scalable_strategies = self.queryset.filter(scales_with_capital=True)
        non_scalable = self.queryset.filter(scales_with_capital=False)
        
        # Calculate potential profits at given capital level
        scalable_projections = []
        for strategy in scalable_strategies:
            efficiency = float(strategy.capital_efficiency_multiplier)
            base_hourly = strategy.hourly_profit_gp
            
            # Simple scaling: more capital = more parallel trades
            capital_ratio = capital_amount / max(strategy.starting_capital, 1)
            projected_hourly = int(base_hourly * capital_ratio * efficiency)
            
            scalable_projections.append({
                'strategy': strategy.strategy.name,
                'base_hourly_profit': base_hourly,
                'projected_hourly_profit': projected_hourly,
                'capital_efficiency': efficiency,
                'scaling_factor': capital_ratio
            })
        
        return Response({
            'capital_analyzed': capital_amount,
            'scalable_strategies': scalable_projections,
            'non_scalable_count': non_scalable.count(),
            'total_projected_hourly': sum(p['projected_hourly_profit'] for p in scalable_projections)
        })


class BondFlippingStrategyViewSet(viewsets.ModelViewSet):
    """
    ViewSet for bond flipping strategies - your friend's tax-exempt approach
    """
    
    queryset = BondFlippingStrategy.objects.select_related('money_maker__strategy').all()
    serializer_class = BondFlippingStrategySerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['min_margin_percentage', 'max_hold_time_hours']
    ordering_fields = ['bond_price_gp', 'min_margin_percentage', 'bond_to_gp_rate']
    ordering = ['-bond_to_gp_rate']
    
    @action(detail=False, methods=['get'])
    async def current_opportunities(self, request):
        """Get current bond flipping opportunities with real-time data"""
        try:
            detector = MoneyMakerDetector()
            capital = int(request.query_params.get('capital', 50_000_000))
            
            # Get bond opportunities asynchronously
            opportunities = await detector.detect_bond_strategies(capital)
            
            # Format for API response
            formatted_opportunities = []
            for opp in opportunities:
                formatted_opportunities.append({
                    'item_id': opp.item_id,
                    'item_name': opp.item_name,
                    'buy_price': opp.buy_price,
                    'sell_price': opp.sell_price,
                    'profit_per_item': opp.profit_per_item,
                    'profit_margin_pct': opp.profit_margin_pct,
                    'ge_tax_saved': opp.ge_tax_exemption_value,
                    'confidence_score': opp.confidence_score,
                    'estimated_volume': opp.estimated_daily_volume,
                    'max_trades_with_capital': capital // opp.buy_price
                })
            
            return Response({
                'opportunities': formatted_opportunities,
                'total_opportunities': len(formatted_opportunities),
                'capital_analyzed': capital,
                'tax_exemption_benefit': True
            })
            
        except Exception as e:
            return Response(
                {'error': f'Failed to fetch opportunities: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def bond_price_analysis(self, request):
        """Analyze current bond prices and conversion rates"""
        try:
            # Get current bond price from most recent strategy
            latest_strategy = self.queryset.first()
            
            if not latest_strategy:
                return Response({'error': 'No bond strategies configured'})
                
            current_bond_price = latest_strategy.bond_price_gp
            gp_per_dollar = float(latest_strategy.bond_to_gp_rate)
            
            # Typical bond costs in USD (approximate)
            bond_usd_cost = 6.99  # Current membership bond cost
            
            analysis = {
                'current_bond_price_gp': current_bond_price,
                'bond_cost_usd': bond_usd_cost,
                'gp_per_dollar': gp_per_dollar,
                'gp_per_bond_bought': int(gp_per_dollar * bond_usd_cost),
                'arbitrage_profit_per_bond': current_bond_price - int(gp_per_dollar * bond_usd_cost),
                'is_profitable': current_bond_price > int(gp_per_dollar * bond_usd_cost),
                'ge_tax_exemption': 'Bonds are exempt from 2% GE tax',
                'recommendation': 'Profitable' if current_bond_price > int(gp_per_dollar * bond_usd_cost) else 'Not profitable'
            }
            
            return Response(analysis)
            
        except Exception as e:
            return Response(
                {'error': f'Analysis failed: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AdvancedDecantingStrategyViewSet(viewsets.ModelViewSet):
    """
    ViewSet for advanced decanting strategies - your friend's 40M profit method
    """
    
    queryset = AdvancedDecantingStrategy.objects.select_related('money_maker__strategy').all()
    serializer_class = AdvancedDecantingStrategySerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['barbarian_herblore_required', 'min_profit_per_dose_gp']
    ordering_fields = ['decanting_speed_per_hour', 'total_decanting_profit']
    ordering = ['-total_decanting_profit']
    
    @action(detail=False, methods=['get'])
    async def profitable_potions(self, request):
        """Get currently profitable potion decanting opportunities"""
        try:
            detector = MoneyMakerDetector()
            capital = int(request.query_params.get('capital', 50_000_000))
            min_profit = int(request.query_params.get('min_profit_per_dose', 100))
            
            opportunities = await detector.detect_decanting_opportunities(capital)
            
            # Filter by minimum profit per dose
            profitable = [
                opp for opp in opportunities 
                if opp.profit_per_item >= min_profit
            ]
            
            # Calculate hourly projections
            formatted_opportunities = []
            for opp in profitable:
                # Estimate hourly volume based on strategy settings
                strategy = self.queryset.first()
                hourly_speed = strategy.decanting_speed_per_hour if strategy else 1000
                
                hourly_profit = opp.profit_per_item * min(hourly_speed, opp.estimated_daily_volume // 24)
                
                formatted_opportunities.append({
                    'item_id': opp.item_id,
                    'potion_name': opp.item_name,
                    'from_dose': getattr(opp, 'from_dose', 4),
                    'to_dose': getattr(opp, 'to_dose', 3),
                    'profit_per_conversion': opp.profit_per_item,
                    'hourly_profit_potential': hourly_profit,
                    'ge_tax_impact': opp.ge_tax_cost,
                    'market_liquidity': opp.estimated_daily_volume,
                    'confidence_score': opp.confidence_score
                })
            
            return Response({
                'profitable_potions': formatted_opportunities,
                'total_found': len(formatted_opportunities),
                'capital_analyzed': capital,
                'min_profit_filter': min_profit,
                'barbarian_herblore_note': 'Required for most profitable decanting methods'
            })
            
        except Exception as e:
            return Response(
                {'error': f'Failed to analyze potions: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def dose_combination_analysis(self, request):
        """Analyze optimal dose combinations for maximum profit"""
        strategies = self.queryset.all()
        
        analysis = []
        for strategy in strategies:
            optimal_combinations = strategy.optimal_dose_combinations
            
            for combo in optimal_combinations:
                analysis.append({
                    'strategy_id': strategy.id,
                    'from_dose': combo.get('from_dose'),
                    'to_dose': combo.get('to_dose'),
                    'profit_per_conversion': combo.get('profit'),
                    'potion_type': combo.get('potion_type'),
                    'estimated_hourly': combo.get('profit') * strategy.decanting_speed_per_hour
                })
        
        # Sort by profitability
        analysis.sort(key=lambda x: x['estimated_hourly'], reverse=True)
        
        return Response({
            'dose_combinations': analysis,
            'total_combinations': len(analysis),
            'recommendation': 'Focus on highest hourly profit combinations first'
        })


class EnhancedSetCombiningStrategyViewSet(viewsets.ModelViewSet):
    """
    ViewSet for enhanced set combining strategies - lazy tax exploitation
    """
    
    queryset = EnhancedSetCombiningStrategy.objects.select_related('money_maker__strategy').all()
    serializer_class = EnhancedSetCombiningStrategySerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['max_sets_held_simultaneously', 'piece_acquisition_timeout_hours']
    ordering_fields = ['total_set_profit', 'average_lazy_tax_percentage']
    ordering = ['-average_lazy_tax_percentage']
    
    @action(detail=False, methods=['get'])
    async def lazy_tax_opportunities(self, request):
        """Get current set combining opportunities with lazy tax premiums"""
        try:
            detector = MoneyMakerDetector()
            capital = int(request.query_params.get('capital', 50_000_000))
            
            opportunities = await detector.detect_set_combining_opportunities(capital)
            
            # Format with lazy tax analysis
            formatted_opportunities = []
            for opp in opportunities:
                lazy_tax_premium = opp.profit_margin_pct  # This represents the lazy tax
                
                formatted_opportunities.append({
                    'set_name': opp.item_name,
                    'set_item_id': opp.item_id,
                    'pieces_total_cost': opp.buy_price,
                    'complete_set_price': opp.sell_price,
                    'lazy_tax_profit': opp.profit_per_item,
                    'lazy_tax_premium_pct': lazy_tax_premium,
                    'ge_tax_cost': opp.ge_tax_cost,
                    'net_profit_after_tax': opp.profit_per_item - opp.ge_tax_cost,
                    'confidence_score': opp.confidence_score,
                    'estimated_completion_time': '24-48 hours',
                    'capital_efficiency': (opp.profit_per_item / opp.buy_price * 100) if opp.buy_price > 0 else 0
                })
            
            return Response({
                'set_opportunities': formatted_opportunities,
                'total_sets_found': len(formatted_opportunities),
                'capital_analyzed': capital,
                'lazy_tax_explanation': 'Players pay premium for convenience of complete sets',
                'recommendation': 'Focus on highest lazy tax premium percentages'
            })
            
        except Exception as e:
            return Response(
                {'error': f'Failed to analyze sets: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def set_competition_analysis(self, request):
        """Analyze competition levels for different armor/weapon sets"""
        strategies = self.queryset.all()
        
        competition_data = []
        for strategy in strategies:
            competition_levels = strategy.set_competition_levels
            
            for set_id, competition_level in competition_levels.items():
                competition_data.append({
                    'set_id': set_id,
                    'competition_level': competition_level,
                    'recommended_daily_sets': strategy.recommended_daily_sets.get(set_id, 1),
                    'average_lazy_tax': float(strategy.average_lazy_tax_percentage)
                })
        
        # Group by competition level
        grouped = {}
        for item in competition_data:
            level = item['competition_level']
            if level not in grouped:
                grouped[level] = []
            grouped[level].append(item)
        
        return Response({
            'competition_analysis': grouped,
            'recommendation': {
                'low': 'Safe, consistent profits with higher volumes',
                'medium': 'Good balance of profit and competition', 
                'high': 'Higher profits but more competition and risk'
            }
        })


class RuneMagicStrategyViewSet(viewsets.ModelViewSet):
    """
    ViewSet for rune and magic supply strategies
    """
    
    queryset = RuneMagicStrategy.objects.select_related('money_maker__strategy').all()
    serializer_class = RuneMagicStrategySerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['runecrafting_level_required', 'runes_per_hour']
    ordering_fields = ['runecrafting_level_required', 'runes_per_hour']
    ordering = ['-runes_per_hour']
    
    @action(detail=False, methods=['get'])
    def rune_trading_opportunities(self, request):
        """Get current rune trading and crafting profit opportunities from real OSRS data"""
        from services.rune_crafting_calculator import RuneCraftingCalculator
        from django.utils import timezone as django_timezone
        
        try:
            calculator = RuneCraftingCalculator()
            
            # Get minimum level from query params
            min_level = int(request.query_params.get('min_level', 1))
            max_level = int(request.query_params.get('max_level', 99))
            
            # Calculate real rune crafting opportunities
            opportunities = calculator.calculate_rune_crafting_profits(min_level, max_level)
            
            # Format opportunities for API response
            formatted_opportunities = []
            for opp in opportunities:
                hourly_data = calculator.calculate_hourly_profits(opp)
                
                formatted_opportunities.append({
                    'rune_type': opp.rune_type,
                    'rune_item_id': opp.rune_item_id,
                    'level_required': opp.level_required,
                    'essence_buy_price': opp.essence_buy_price,
                    'rune_sell_price': opp.rune_sell_price,
                    'profit_per_essence': opp.profit_per_essence,
                    'profit_per_rune': opp.profit_per_rune,
                    'runes_per_essence': opp.runes_per_essence,
                    'hourly_profit_gp': hourly_data['hourly_profit_gp'],
                    'runes_per_hour': hourly_data['runes_per_hour'],
                    'essences_per_hour': hourly_data['essences_per_hour'],
                    'capital_required': hourly_data['capital_required'],
                    'profit_margin_pct': hourly_data['profit_margin_pct'],
                    'volume_score': opp.confidence_score,
                    'last_updated': opp.last_updated,
                    'data_freshness': 'real-time'
                })
            
            return Response({
                'rune_trading_opportunities': formatted_opportunities[:20],  # Top 20 opportunities
                'total_opportunities': len(formatted_opportunities),
                'data_source': 'Real OSRS Wiki API - Essence and Rune Prices',
                'last_analysis': django_timezone.now().isoformat(),
                'market_note': 'Real market prices for essence costs and rune sell values',
                'profit_explanation': 'Profits calculated from current GE prices - negative values indicate unprofitable market conditions',
                'level_range': f'Runecrafting levels {min_level}-{max_level}'
            })
            
        except Exception as e:
            return Response({
                'error': f'Failed to calculate rune trading opportunities: {str(e)}',
                'rune_trading_opportunities': [],
                'total_opportunities': 0
            }, status=500)


class MoneyMakerOpportunityViewSet(viewsets.ViewSet):
    """
    ViewSet for real-time money making opportunity detection
    """
    
    @action(detail=False, methods=['get'])
    async def detect_all(self, request):
        """Detect all current money making opportunities"""
        try:
            capital = int(request.query_params.get('capital', 50_000_000))
            detector = MoneyMakerDetector()
            
            # Get all opportunities asynchronously
            all_opportunities = await detector.detect_all_opportunities(capital)
            
            # Group by strategy type
            grouped_opportunities = {}
            for opp in all_opportunities:
                strategy_type = opp.strategy_type
                if strategy_type not in grouped_opportunities:
                    grouped_opportunities[strategy_type] = []
                
                grouped_opportunities[strategy_type].append({
                    'item_id': opp.item_id,
                    'item_name': opp.item_name,
                    'buy_price': opp.buy_price,
                    'sell_price': opp.sell_price,
                    'profit_per_item': opp.profit_per_item,
                    'profit_margin_pct': opp.profit_margin_pct,
                    'confidence_score': opp.confidence_score,
                    'estimated_daily_volume': opp.estimated_daily_volume,
                    'ge_tax_cost': opp.ge_tax_cost,
                    'max_trades_with_capital': capital // opp.buy_price if opp.buy_price > 0 else 0
                })
            
            return Response({
                'opportunities_by_type': grouped_opportunities,
                'total_opportunities': len(all_opportunities),
                'capital_analyzed': capital,
                'detection_timestamp': timezone.now().isoformat()
            })
            
        except Exception as e:
            return Response(
                {'error': f'Opportunity detection failed: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def universal_scan(self, request):
        """
        Universal opportunity scanner - evaluates all trading strategies per item
        and provides cross-strategy analysis with recommendations.
        """
        try:
            min_profit_gp = int(request.query_params.get('min_profit', 1000))
            scanner = UniversalOpportunityScanner(min_profit_gp=min_profit_gp)
            
            # Perform comprehensive scan
            results = scanner.scan_all_opportunities()
            
            # Calculate summary statistics
            total_opportunities = sum(len(opportunities) for strategy_type, opportunities in results.items() if strategy_type != 'cross_strategy_analysis')
            cross_strategy_count = len(results.get('cross_strategy_analysis', []))
            
            # Find best opportunities per strategy type
            best_by_strategy = {}
            for strategy_type, opportunities in results.items():
                if strategy_type != 'cross_strategy_analysis' and opportunities:
                    best_by_strategy[strategy_type] = {
                        'count': len(opportunities),
                        'best_opportunity': opportunities[0],  # Already sorted by profit
                        'total_profit_potential': sum(opp.get('profit_gp', 0) for opp in opportunities[:10])  # Top 10
                    }
            
            return Response({
                'scan_results': results,
                'summary': {
                    'total_opportunities': total_opportunities,
                    'cross_strategy_items': cross_strategy_count,
                    'min_profit_filter': min_profit_gp,
                    'best_by_strategy': best_by_strategy
                },
                'recommendations': {
                    'focus_areas': [
                        strategy for strategy, data in best_by_strategy.items() 
                        if data['count'] > 5  # Strategies with multiple opportunities
                    ],
                    'cross_strategy_note': f'Found {cross_strategy_count} items with multiple profitable strategies'
                },
                'scan_timestamp': timezone.now().isoformat()
            })
            
        except Exception as e:
            return Response(
                {'error': f'Universal scan failed: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def ge_tax_calculator(self, request):
        """Calculate Grand Exchange tax for different price points"""
        price = int(request.query_params.get('price', 1_000_000))
        item_id = request.query_params.get('item_id', None)
        
        if item_id:
            item_id = int(item_id)
        
        tax_amount = GrandExchangeTax.calculate_tax(price, item_id)
        net_received = price - tax_amount
        tax_percentage = (tax_amount / price * 100) if price > 0 else 0
        
        return Response({
            'sell_price': price,
            'item_id': item_id,
            'ge_tax': tax_amount,
            'net_received': net_received,
            'effective_tax_percentage': round(tax_percentage, 2),
            'is_tax_exempt': tax_amount == 0 and price > 50,
            'tax_rules': {
                'base_rate': '2%',
                'exemption_threshold': '50 GP',
                'maximum_tax': '5,000,000 GP',
                'exempt_items': ['Old School Bonds (ID: 13190)']
            }
        })


class CapitalProgressionAdvisorViewSet(viewsets.ViewSet):
    """
    ViewSet for AI-powered capital progression advice
    """
    
    @action(detail=False, methods=['get'])
    async def get_advice(self, request):
        """Get personalized capital progression advice"""
        try:
            current_capital = int(request.query_params.get('capital', 50_000_000))
            target_capital = int(request.query_params.get('target', 100_000_000))
            risk_tolerance = request.query_params.get('risk', 'medium')
            
            advisor = CapitalProgressionAdvisor()
            advice = await advisor.get_progression_advice(
                current_capital=current_capital,
                target_capital=target_capital,
                risk_tolerance=risk_tolerance
            )
            
            return Response(advice)
            
        except Exception as e:
            return Response(
                {'error': f'Advice generation failed: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    async def progression_roadmap(self, request):
        """Get detailed roadmap from current to target capital"""
        try:
            current_capital = int(request.query_params.get('capital', 50_000_000))
            target_capital = int(request.query_params.get('target', 100_000_000))
            
            advisor = CapitalProgressionAdvisor()
            roadmap = await advisor.create_progression_roadmap(
                current_capital=current_capital,
                target_capital=target_capital
            )
            
            return Response(roadmap)
            
        except Exception as e:
            return Response(
                {'error': f'Roadmap generation failed: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MoneyMakerAnalyticsViewSet(viewsets.ViewSet):
    """
    ViewSet for money maker analytics and insights
    """
    
    @action(detail=False, methods=['get'])
    def market_overview(self, request):
        """Get overall market overview for money making"""
        
        # Aggregate data from all strategy types
        total_strategies = MoneyMakerStrategy.objects.count()
        active_strategies = MoneyMakerStrategy.objects.filter(
            hourly_profit_gp__gt=0
        ).count()
        
        avg_hourly_profit = MoneyMakerStrategy.objects.aggregate(
            avg_profit=Avg('hourly_profit_gp')
        )['avg_profit'] or 0
        
        total_realized_profit = MoneyMakerStrategy.objects.aggregate(
            total_profit=Sum('total_profit_realized')
        )['total_profit'] or 0
        
        # Strategy type distribution
        strategy_distribution = {}
        bond_flipping_count = BondFlippingStrategy.objects.count()
        decanting_count = AdvancedDecantingStrategy.objects.count()
        set_combining_count = EnhancedSetCombiningStrategy.objects.count()
        rune_magic_count = RuneMagicStrategy.objects.count()
        
        return Response({
            'market_overview': {
                'total_strategies': total_strategies,
                'active_strategies': active_strategies,
                'average_hourly_profit': int(avg_hourly_profit),
                'total_realized_profit': int(total_realized_profit),
                'activity_percentage': (active_strategies / max(total_strategies, 1) * 100)
            },
            'strategy_distribution': {
                'bond_flipping': bond_flipping_count,
                'advanced_decanting': decanting_count,
                'enhanced_set_combining': set_combining_count,
                'rune_magic': rune_magic_count
            },
            'market_health': {
                'status': 'healthy' if active_strategies > 0 else 'inactive',
                'recommendation': 'Market conditions favorable for money making' if active_strategies > 0 else 'Consider market analysis before trading'
            }
        })
    
    @action(detail=False, methods=['get'])
    def profit_projections(self, request):
        """Calculate profit projections based on current strategies"""
        
        time_horizon = request.query_params.get('hours', '24')
        hours = int(time_horizon)
        
        # Get all active strategies
        strategies = MoneyMakerStrategy.objects.filter(hourly_profit_gp__gt=0)
        
        projections = []
        total_projected = 0
        
        for strategy in strategies:
            hourly_profit = strategy.hourly_profit_gp
            projected_profit = hourly_profit * hours
            success_rate = float(strategy.success_rate_percentage) / 100
            
            adjusted_profit = int(projected_profit * success_rate)
            total_projected += adjusted_profit
            
            projections.append({
                'strategy_name': strategy.strategy.name,
                'strategy_type': strategy.strategy.strategy_type,
                'hourly_profit': hourly_profit,
                'projected_profit': projected_profit,
                'success_adjusted_profit': adjusted_profit,
                'success_rate': float(strategy.success_rate_percentage),
                'capital_required': strategy.starting_capital
            })
        
        return Response({
            'time_horizon_hours': hours,
            'individual_projections': projections,
            'total_projected_profit': total_projected,
            'average_hourly_rate': total_projected // hours if hours > 0 else 0,
            'projection_accuracy': 'Based on historical success rates and current market conditions'
        })