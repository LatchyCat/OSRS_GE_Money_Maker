from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count
from .models import (
    TradingStrategy, 
    DecantingOpportunity,
    SetCombiningOpportunity,
    FlippingOpportunity,
    CraftingOpportunity,
    MarketConditionSnapshot,
    StrategyPerformance,
    StrategyType
)
from .serializers import (
    TradingStrategySerializer,
    TradingStrategyListSerializer,
    DecantingOpportunitySerializer,
    SetCombiningOpportunitySerializer,
    FlippingOpportunitySerializer,
    CraftingOpportunitySerializer,
    MarketConditionSnapshotSerializer,
    MarketConditionSummarySerializer,
    StrategyPerformanceSerializer
)

# Import GE tax calculation utilities from OSRS Wiki data
from services.runescape_wiki_client import GrandExchangeTax


class TradingStrategyViewSet(viewsets.ModelViewSet):
    """ViewSet for managing trading strategies"""
    
    queryset = TradingStrategy.objects.all()
    serializer_class = TradingStrategySerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['strategy_type', 'risk_level', 'is_active', 'optimal_market_condition']
    search_fields = ['name', 'description']
    ordering_fields = [
        'potential_profit_gp', 'profit_margin_pct', 'confidence_score', 
        'created_at', 'min_capital_required', 'estimated_time_minutes'
    ]
    ordering = ['-potential_profit_gp', '-confidence_score']
    
    def get_serializer_class(self):
        """Use different serializers for list vs detail views"""
        if self.action == 'list':
            return TradingStrategyListSerializer
        return TradingStrategySerializer
    
    def get_queryset(self):
        """Filter active strategies by default"""
        queryset = super().get_queryset()
        
        # Filter by capital range
        min_capital = self.request.query_params.get('min_capital')
        max_capital = self.request.query_params.get('max_capital')
        
        if min_capital:
            queryset = queryset.filter(min_capital_required__gte=min_capital)
        if max_capital:
            queryset = queryset.filter(min_capital_required__lte=max_capital)
        
        # Filter by profit range
        min_profit = self.request.query_params.get('min_profit')
        max_profit = self.request.query_params.get('max_profit')
        
        if min_profit:
            queryset = queryset.filter(potential_profit_gp__gte=min_profit)
        if max_profit:
            queryset = queryset.filter(potential_profit_gp__lte=max_profit)
        
        # Filter by time range
        max_time = self.request.query_params.get('max_time')
        if max_time:
            queryset = queryset.filter(estimated_time_minutes__lte=max_time)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def top_strategies(self, request):
        """Get top strategies by different metrics"""
        limit = int(request.query_params.get('limit', 10))
        metric = request.query_params.get('metric', 'profit')
        
        if metric == 'profit':
            strategies = self.queryset.filter(is_active=True).order_by('-potential_profit_gp')[:limit]
        elif metric == 'margin':
            strategies = self.queryset.filter(is_active=True).order_by('-profit_margin_pct')[:limit]
        elif metric == 'roi':
            # Order by calculated ROI (profit/capital ratio)
            strategies = self.queryset.filter(is_active=True, min_capital_required__gt=0).extra(
                select={'roi': 'potential_profit_gp::float / min_capital_required::float'}
            ).order_by('-roi')[:limit]
        elif metric == 'confidence':
            strategies = self.queryset.filter(is_active=True).order_by('-confidence_score')[:limit]
        else:
            strategies = self.queryset.filter(is_active=True)[:limit]
        
        serializer = TradingStrategyListSerializer(strategies, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """Get strategies grouped by type"""
        strategy_types = {}
        
        for strategy_type in StrategyType.choices:
            type_code = strategy_type[0]
            type_name = strategy_type[1]
            
            strategies = self.queryset.filter(
                strategy_type=type_code, 
                is_active=True
            ).order_by('-potential_profit_gp')[:5]  # Top 5 per type
            
            strategy_types[type_code] = {
                'name': type_name,
                'count': self.queryset.filter(strategy_type=type_code, is_active=True).count(),
                'strategies': TradingStrategyListSerializer(strategies, many=True).data
            }
        
        return Response(strategy_types)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get strategy statistics"""
        stats = {
            'total_strategies': self.queryset.filter(is_active=True).count(),
            'by_type': {},
            'by_risk': {},
            'profit_ranges': {
                'under_1m': self.queryset.filter(is_active=True, potential_profit_gp__lt=1000000).count(),
                '1m_to_10m': self.queryset.filter(is_active=True, potential_profit_gp__gte=1000000, potential_profit_gp__lt=10000000).count(),
                'over_10m': self.queryset.filter(is_active=True, potential_profit_gp__gte=10000000).count(),
            }
        }
        
        # Count by strategy type
        for strategy_type in StrategyType.choices:
            type_code = strategy_type[0]
            stats['by_type'][type_code] = self.queryset.filter(
                strategy_type=type_code, is_active=True
            ).count()
        
        # Count by risk level
        risk_levels = ['low', 'medium', 'high', 'extreme']
        for risk in risk_levels:
            stats['by_risk'][risk] = self.queryset.filter(
                risk_level=risk, is_active=True
            ).count()
        
        return Response(stats)


class DecantingOpportunityViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for decanting opportunities with comprehensive filtering"""
    
    queryset = DecantingOpportunity.objects.select_related('strategy').all()
    serializer_class = DecantingOpportunitySerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['item_id', 'from_dose', 'to_dose']
    search_fields = ['item_name']
    ordering_fields = [
        'profit_per_conversion', 'profit_per_hour', 'from_dose_price', 'to_dose_price',
        'from_dose_volume', 'to_dose_volume'
    ]
    ordering = ['-profit_per_conversion']
    
    def get_queryset(self):
        """Add advanced filtering support for decanting opportunities"""
        queryset = super().get_queryset()
        
        # Filter by active strategies only by default
        is_active = self.request.query_params.get('is_active', 'true')
        if is_active.lower() in ['true', '1']:
            queryset = queryset.filter(strategy__is_active=True)
        
        # Filter by profit per conversion range
        min_profit = self.request.query_params.get('min_profit')
        max_profit = self.request.query_params.get('max_profit')
        if min_profit:
            try:
                queryset = queryset.filter(profit_per_conversion__gte=int(min_profit))
            except ValueError:
                pass
        if max_profit:
            try:
                queryset = queryset.filter(profit_per_conversion__lte=int(max_profit))
            except ValueError:
                pass
        
        # Filter by GP per hour range
        min_gp_per_hour = self.request.query_params.get('min_gp_per_hour')
        max_gp_per_hour = self.request.query_params.get('max_gp_per_hour')
        if min_gp_per_hour:
            try:
                queryset = queryset.filter(profit_per_hour__gte=int(min_gp_per_hour))
            except ValueError:
                pass
        if max_gp_per_hour:
            try:
                queryset = queryset.filter(profit_per_hour__lte=int(max_gp_per_hour))
            except ValueError:
                pass
        
        # Filter by risk level
        risk_level = self.request.query_params.get('risk_level')
        if risk_level and risk_level in ['low', 'medium', 'high']:
            queryset = queryset.filter(strategy__risk_level=risk_level)
        
        # Filter by profit margin percentage
        min_margin = self.request.query_params.get('min_margin')
        max_margin = self.request.query_params.get('max_margin') 
        if min_margin:
            try:
                queryset = queryset.filter(strategy__profit_margin_pct__gte=float(min_margin))
            except ValueError:
                pass
        if max_margin:
            try:
                queryset = queryset.filter(strategy__profit_margin_pct__lte=float(max_margin))
            except ValueError:
                pass
        
        # Filter by minimum volume (trading activity)
        min_volume = self.request.query_params.get('min_volume')
        if min_volume:
            try:
                min_vol = int(min_volume)
                # Filter items with sufficient volume in either from_dose or to_dose
                queryset = queryset.filter(
                    Q(from_dose_volume__gte=min_vol) | Q(to_dose_volume__gte=min_vol)
                )
            except ValueError:
                pass
        
        # Filter by dose conversion pattern
        conversion_type = self.request.query_params.get('conversion_type')
        if conversion_type:
            # Parse conversion patterns like "4_to_3", "4_to_2", "any_to_1", etc.
            if '_to_' in conversion_type:
                try:
                    from_dose_str, to_dose_str = conversion_type.split('_to_')
                    if from_dose_str != 'any':
                        from_dose = int(from_dose_str)
                        queryset = queryset.filter(from_dose=from_dose)
                    if to_dose_str != 'any':
                        to_dose = int(to_dose_str)
                        queryset = queryset.filter(to_dose=to_dose)
                except ValueError:
                    pass
        
        # Filter by minimum capital required
        min_capital = self.request.query_params.get('min_capital')
        max_capital = self.request.query_params.get('max_capital')
        if min_capital:
            try:
                queryset = queryset.filter(strategy__min_capital_required__gte=int(min_capital))
            except ValueError:
                pass
        if max_capital:
            try:
                queryset = queryset.filter(strategy__min_capital_required__lte=int(max_capital))
            except ValueError:
                pass
        
        # Filter by confidence score
        min_confidence = self.request.query_params.get('min_confidence')
        if min_confidence:
            try:
                confidence = float(min_confidence)
                queryset = queryset.filter(strategy__confidence_score__gte=confidence)
            except ValueError:
                pass
        
        # Filter by potion category/type
        potion_type = self.request.query_params.get('potion_type')
        if potion_type:
            # Search for potion types like "combat", "prayer", "strength", etc.
            queryset = queryset.filter(item_name__icontains=potion_type)
        
        # Volume quality filter (only show items with decent volume)
        high_volume_only = self.request.query_params.get('high_volume_only', 'false')
        if high_volume_only.lower() in ['true', '1']:
            # Require at least 100 combined volume
            queryset = queryset.extra(
                where=["(from_dose_volume + to_dose_volume) >= %s"],
                params=[100]
            )
        
        return queryset
    
    @action(detail=False, methods=['post'])
    def scan(self, request):
        """Scan for new decanting opportunities"""
        from .services.decanting_detector import DecantingDetector
        
        try:
            detector = DecantingDetector()
            created_count = detector.scan_and_create_opportunities()
            
            return Response({
                'message': f'Scanned decanting opportunities successfully',
                'created_count': created_count,
            })
        except Exception as e:
            return Response({
                'error': f'Failed to scan decanting opportunities: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def fresh_opportunities(self, request):
        """Get fresh decanting opportunities using WeirdGloop data"""
        import asyncio
        from django.core.cache import cache
        from services.decanting_price_service import decanting_price_service
        
        try:
            # Get parameters from request
            min_profit_gp = int(request.query_params.get('min_profit', 1))
            max_results = int(request.query_params.get('page_size', 50))
            
            # Check cache first
            cache_key = f"fresh_decanting_opportunities:{min_profit_gp}:{max_results}"
            cached_opportunities = cache.get(cache_key)
            
            if cached_opportunities:
                return Response({
                    'results': cached_opportunities,
                    'count': len(cached_opportunities),
                    'data_source': 'cached_fresh_weirdgloop',
                    'cache_ttl_minutes': 15
                })
            
            # Get fresh opportunities
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                opportunities = loop.run_until_complete(
                    decanting_price_service.get_decanting_opportunities(min_profit_gp)
                )
            finally:
                loop.close()
            
            # Transform to match existing API format
            results = []
            for opp in opportunities[:max_results]:
                # Create a mock strategy object for compatibility
                strategy_data = {
                    'id': hash(opp.potion_family.base_name) % 10000,  # Generate consistent ID
                    'name': f'Fresh Decanting: {opp.potion_family.base_name}',
                    'strategy_type': 'decanting',
                    'strategy_type_display': 'Decanting',
                    'description': f'Real-time decanting opportunity for {opp.potion_family.base_name}',
                    'potential_profit_gp': opp.profit_per_conversion,
                    'profit_margin_pct': opp.profit_margin_pct,
                    'risk_level': opp.risk_level,
                    'risk_level_display': opp.risk_level.title(),
                    'min_capital_required': opp.from_price,
                    'recommended_capital': opp.from_price * 10,
                    'optimal_market_condition': 'stable',
                    'optimal_market_condition_display': 'Stable',
                    'estimated_time_minutes': 60 // opp.estimated_conversions_per_hour if opp.estimated_conversions_per_hour > 0 else 1,
                    'max_volume_per_day': opp.estimated_conversions_per_hour * 8,  # 8 hour trading day
                    'confidence_score': opp.confidence_score,
                    'is_active': True,
                    'hourly_profit_potential': opp.profit_per_conversion * opp.estimated_conversions_per_hour,
                    'roi_percentage': (opp.profit_per_conversion / opp.from_price * 100) if opp.from_price > 0 else 0
                }
                
                # Transform opportunity to match DecantingOpportunitySerializer format
                opportunity_data = {
                    'id': hash(f"{opp.potion_family.base_name}:{opp.from_dose}:{opp.to_dose}") % 100000,
                    'strategy': strategy_data,
                    'item_id': list(opp.potion_family.item_ids.values())[0] if opp.potion_family.item_ids else 0,
                    'item_name': opp.potion_family.base_name,
                    'from_dose': opp.from_dose,
                    'to_dose': opp.to_dose,
                    'from_dose_price': opp.from_price,
                    'to_dose_price': opp.to_price,
                    'from_dose_volume': opp.potion_family.volumes.get(opp.from_dose, 0),
                    'to_dose_volume': opp.potion_family.volumes.get(opp.to_dose, 0),
                    'profit_per_conversion': opp.profit_per_conversion,
                    'profit_per_hour': opp.profit_per_conversion * opp.estimated_conversions_per_hour
                }
                
                results.append(opportunity_data)
            
            # Cache results for 15 minutes
            cache.set(cache_key, results, 900)  # 15 minutes
            
            return Response({
                'results': results,
                'count': len(results),
                'data_source': 'fresh_weirdgloop_api',
                'potion_families_analyzed': len(opportunities),
                'cache_ttl_minutes': 15
            })
            
        except Exception as e:
            return Response({
                'error': f'Failed to get fresh decanting opportunities: {str(e)}',
                'fallback_message': 'Try using the regular scan endpoint for database-backed results'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def ai_opportunities(self, request):
        """Get AI-powered decanting opportunities with RuneScape Wiki data and multi-model analysis"""
        import asyncio
        from django.core.cache import cache
        from services.ai_enhanced_decanting_service import ai_decanting_service
        
        try:
            # Get parameters from request
            min_profit = int(request.query_params.get('min_profit', 100))
            max_risk = request.query_params.get('max_risk', 'medium')
            min_confidence = float(request.query_params.get('min_confidence', 0.6))
            max_results = int(request.query_params.get('page_size', 20))
            
            # New sorting and filtering parameters
            sort_by = request.query_params.get('ordering', 'profit_desc')  # profit_desc, confidence_desc, gp_per_hour_desc
            potion_family = request.query_params.get('potion_family', '')  # prayer, combat, antifire, etc.
            high_value_only = request.query_params.get('high_value_only', 'false').lower() == 'true'
            force_refresh = request.query_params.get('force_refresh', 'false').lower() == 'true'
            
            # Adjust minimum profit for high-value filter
            if high_value_only:
                min_profit = max(min_profit, 500)  # High-value means at least 500 GP profit
            
            # Check cache first (include new parameters in cache key) unless force refresh is requested
            cache_key = f"enhanced_ai_decanting:{min_profit}_{max_risk}_{min_confidence}_{max_results}_{sort_by}_{potion_family}_{high_value_only}"
            cached_opportunities = None if force_refresh else cache.get(cache_key)
            
            if cached_opportunities and not force_refresh:
                return Response({
                    'results': cached_opportunities['results'],
                    'count': len(cached_opportunities['results']),
                    'data_source': 'cached_enhanced_ai_analysis',
                    'ai_models': ['gemma2:2b', 'deepseek-r1:1.5b', 'qwen2.5:3b'],
                    'pricing_source': 'runescape_wiki_api',
                    'features': ['vector_embeddings', 'hybrid_search', 'consensus_analysis'],
                    'cache_ttl_minutes': 30,
                    'metadata': cached_opportunities['metadata']
                })
            
            # Run enhanced AI analysis
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                ai_opportunities = loop.run_until_complete(
                    ai_decanting_service.discover_ai_opportunities(
                        min_profit=min_profit,
                        max_risk=max_risk,
                        min_confidence=min_confidence,
                        force_refresh=force_refresh
                    )
                )
            finally:
                loop.close()
            
            # Filter by potion family if specified
            if potion_family:
                family_keywords = {
                    'prayer': ['prayer', 'restore'],
                    'combat': ['combat', 'super combat', 'strength', 'attack', 'defence'],
                    'ranging': ['ranging', 'range'],
                    'magic': ['magic'],
                    'antifire': ['antifire', 'extended antifire'],
                    'stamina': ['stamina', 'energy'],
                    'brew': ['brew', 'saradomin'],
                    'divine': ['divine']
                }
                
                if potion_family.lower() in family_keywords:
                    keywords = family_keywords[potion_family.lower()]
                    ai_opportunities = [
                        opp for opp in ai_opportunities 
                        if any(keyword.lower() in opp.name.lower() for keyword in keywords)
                    ]
            
            # Apply 2% GE tax calculations to all opportunities before sorting
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Applying 2% GE tax calculations to {len(ai_opportunities)} decanting opportunities")
            
            for ai_opp in ai_opportunities:
                try:
                    # Original profit calculation (without tax)
                    original_profit = ai_opp.profit_per_conversion
                    original_profit_per_hour = ai_opp.profit_per_hour
                    
                    # Calculate 2% GE tax on selling the to-dose potion
                    # For decanting: you sell multiple smaller dose potions
                    # e.g., 4-dose → 3-dose conversion sells 4 individual 3-dose potions
                    dose_multiplier = ai_opp.from_dose  # How many to-dose potions you get
                    sell_price_per_potion = ai_opp.sell_price
                    total_sell_value = sell_price_per_potion * dose_multiplier
                    
                    # Calculate GE tax for the total sale
                    ge_tax = GrandExchangeTax.calculate_tax(total_sell_value, ai_opp.to_item_id if hasattr(ai_opp, 'to_item_id') else ai_opp.from_item_id)
                    
                    # Net revenue after GE tax
                    net_revenue = total_sell_value - ge_tax
                    buy_cost = ai_opp.buy_price  # Cost to buy the from-dose potion
                    
                    # Update profit calculations to account for GE tax
                    ai_opp.profit_per_conversion = net_revenue - buy_cost
                    ai_opp.profit_per_hour = (net_revenue - buy_cost) * (original_profit_per_hour / original_profit) if original_profit > 0 else 0
                    
                    # Store tax information for API response
                    ai_opp.ge_tax_amount = ge_tax
                    ai_opp.tax_rate = (ge_tax / total_sell_value * 100) if total_sell_value > 0 else 0
                    
                    if ge_tax > 0:
                        logger.debug(f"Applied GE tax to {ai_opp.name}: {ge_tax} GP tax on {total_sell_value} GP sale ({ai_opp.tax_rate:.1f}%)")
                    
                except Exception as e:
                    logger.warning(f"Failed to apply GE tax to {getattr(ai_opp, 'name', 'unknown')}: {e}")
                    # Keep original values if tax calculation fails
                    ai_opp.ge_tax_amount = 0
                    ai_opp.tax_rate = 0
            
            # Apply multi-criteria sorting: high-confidence profitable items first, low-confidence/high-risk items last
            def get_sort_priority(opportunity):
                confidence = getattr(opportunity, 'ai_confidence', 0) or 0
                risk_level = getattr(opportunity, 'ai_risk_level', 'high') or 'high'
                profit = getattr(opportunity, 'profit_per_conversion', 0) or 0
                
                # Priority 1: High confidence (0.8+) and low/medium risk
                if confidence >= 0.8 and risk_level in ['low', 'medium']:
                    return (1, -profit)  # negative profit for descending sort
                # Priority 2: Medium confidence (0.6+) and not high risk
                elif confidence >= 0.6 and risk_level != 'high':
                    return (2, -profit)
                # Priority 3: Everything else (low confidence or high risk items go to bottom)
                else:
                    return (3, -profit)
            
            # Apply intelligent sorting based on user preference but with quality prioritization
            if sort_by == 'profit_desc':
                # Sort by quality tier first, then profit within tier
                ai_opportunities.sort(key=get_sort_priority)
            elif sort_by == 'confidence_desc':
                ai_opportunities.sort(key=lambda x: (getattr(x, 'ai_confidence', 0) or 0, -getattr(x, 'profit_per_conversion', 0)), reverse=True)
            elif sort_by == 'gp_per_hour_desc':
                ai_opportunities.sort(key=get_sort_priority)  # Use quality-aware sorting for GP/hour too
            elif sort_by == 'model_agreement_desc':
                ai_opportunities.sort(key=lambda x: (getattr(x, 'model_agreement', 0) or 0, -getattr(x, 'profit_per_conversion', 0)), reverse=True)
            else:
                # Default: quality-aware profit sorting
                ai_opportunities.sort(key=get_sort_priority)
            
            logger.info(f"Applied quality-aware sorting with {sort_by}. Top opportunity: {ai_opportunities[0].name if ai_opportunities else 'none'}")
            
            # Transform AI opportunities to match API format
            results = []
            total_confidence = 0
            total_agreement = 0
            
            for ai_opp in ai_opportunities[:max_results]:
                # Create enhanced strategy data with AI insights
                strategy_data = {
                    'id': hash(f"enhanced_ai:{ai_opp.name}") % 10000 + 60000,
                    'name': f'🤖 AI Enhanced: {ai_opp.name}',
                    'strategy_type': 'decanting',
                    'strategy_type_display': 'AI Enhanced Decanting',
                    'description': f'Multi-AI analysis of {ai_opp.name} using RuneScape Wiki pricing. {ai_opp.execution_strategy}',
                    'potential_profit_gp': ai_opp.profit_per_conversion,
                    'profit_margin_pct': ai_opp.roi_percentage,
                    'risk_level': ai_opp.ai_risk_level,
                    'risk_level_display': ai_opp.ai_risk_level.title(),
                    'min_capital_required': ai_opp.capital_requirement,
                    'recommended_capital': ai_opp.capital_requirement * 10,
                    'optimal_market_condition': ai_opp.ai_timing,
                    'optimal_market_condition_display': ai_opp.ai_timing.title(),
                    'estimated_time_minutes': ai_opp.estimated_time_per_conversion // 60,
                    'max_volume_per_day': ai_opp.max_hourly_conversions * 8,  # 8 hour day
                    'confidence_score': ai_opp.ai_confidence,
                    'is_active': True,
                    'hourly_profit_potential': ai_opp.profit_per_hour,
                    'roi_percentage': ai_opp.roi_percentage
                }
                
                # Transform to opportunity format with enhanced AI data
                opportunity_data = {
                    'id': hash(f"enhanced_ai:{ai_opp.name}:{ai_opp.from_dose}:{ai_opp.to_dose}") % 100000 + 60000,
                    'strategy': strategy_data,
                    'item_id': ai_opp.from_item_id,
                    'item_name': ai_opp.name,
                    'from_dose': ai_opp.from_dose,
                    'to_dose': ai_opp.to_dose,
                    'from_dose_price': ai_opp.buy_price,
                    'to_dose_price': ai_opp.sell_price,
                    'from_dose_volume': ai_opp.trading_volume,
                    'to_dose_volume': ai_opp.trading_volume // 2,
                    'profit_per_conversion': ai_opp.profit_per_conversion,
                    'profit_per_hour': ai_opp.profit_per_hour,
                    
                    # Enhanced AI-specific fields
                    'ai_confidence': ai_opp.ai_confidence,
                    'ai_risk_level': ai_opp.ai_risk_level,
                    'ai_timing': ai_opp.ai_timing,
                    'ai_success_probability': ai_opp.ai_success_probability,
                    'ai_recommendations': ai_opp.ai_recommendations,
                    'model_agreement': ai_opp.model_agreement,
                    'execution_strategy': ai_opp.execution_strategy,
                    'data_freshness': ai_opp.data_freshness,
                    'price_spread': ai_opp.price_spread,
                    'liquidity_score': ai_opp.liquidity_score,
                    'uncertainty_factors': ai_opp.uncertainty_factors,
                    'similar_opportunities': ai_opp.similar_opportunities,
                    'max_hourly_conversions': ai_opp.max_hourly_conversions,
                    'capital_requirement': ai_opp.capital_requirement,
                    
                    # GE Tax information
                    'ge_tax_amount': getattr(ai_opp, 'ge_tax_amount', 0),
                    'tax_rate': getattr(ai_opp, 'tax_rate', 0),
                    'includes_ge_tax': True
                }
                
                results.append(opportunity_data)
                total_confidence += ai_opp.ai_confidence
                total_agreement += ai_opp.model_agreement
            
            # Calculate metadata
            metadata = {
                'avg_confidence': total_confidence / len(results) if results else 0,
                'avg_model_agreement': total_agreement / len(results) if results else 0,
                'high_confidence_count': len([r for r in results if r['ai_confidence'] >= 0.8]),
                'opportunities_analyzed': len(ai_opportunities),
                'filtering_applied': {
                    'min_profit': min_profit,
                    'max_risk': max_risk,
                    'min_confidence': min_confidence
                }
            }
            
            # Add force refresh indicator to metadata
            metadata['force_refreshed'] = force_refresh
            
            # Cache enhanced AI results for 30 minutes (only if not force refresh)
            cache_data = {'results': results, 'metadata': metadata}
            if not force_refresh:
                cache.set(cache_key, cache_data, 1800)  # 30 minutes
            else:
                # Clear existing cache when force refresh is used
                cache.delete(cache_key)
            
            return Response({
                'results': results,
                'count': len(results),
                'data_source': 'fresh_enhanced_ai_analysis' if force_refresh else 'enhanced_ai_multi_model_analysis',
                'ai_models': ['gemma2:2b', 'deepseek-r1:1.5b', 'qwen2.5:3b'],
                'pricing_source': 'runescape_wiki_api_primary',
                'features': [
                    'vector_embeddings', 
                    'hybrid_search', 
                    'consensus_analysis',
                    'market_timing_analysis',
                    'execution_planning'
                ],
                'cache_ttl_minutes': 30,
                'metadata': metadata
            })
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            
            return Response({
                'error': f'Enhanced AI analysis failed: {str(e)}',
                'error_details': error_details if request.query_params.get('debug') == '1' else None,
                'fallback_message': 'Try using fresh_opportunities endpoint for basic analysis',
                'support': 'Check that Ollama models are running and RuneScape Wiki API is accessible'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SetCombiningOpportunityViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for set combining opportunities"""
    
    queryset = SetCombiningOpportunity.objects.select_related('strategy').all()
    serializer_class = SetCombiningOpportunitySerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['set_item_id']
    search_fields = ['set_name']
    ordering_fields = ['lazy_tax_profit', 'individual_pieces_total_cost', 'complete_set_price']
    ordering = ['-lazy_tax_profit']
    
    @action(detail=False, methods=['post'])
    def scan(self, request):
        """Scan for new set combining opportunities"""
        from .services.set_combining_analyzer import SetCombiningAnalyzer
        
        try:
            analyzer = SetCombiningAnalyzer()
            created_count = analyzer.scan_and_create_opportunities()
            
            return Response({
                'message': f'Scanned set combining opportunities successfully',
                'created_count': created_count,
            })
        except Exception as e:
            return Response({
                'error': f'Failed to scan set combining opportunities: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def ai_opportunities(self, request):
        """Get AI-powered set combining opportunities using OSRS Wiki API with volume analysis"""
        import asyncio
        from django.core.cache import cache
        from services.runescape_wiki_client import RuneScapeWikiAPIClient
        import logging
        
        logger = logging.getLogger(__name__)
        
        try:
            # Get parameters from request
            min_profit = int(request.query_params.get('min_profit', 5000))
            min_volume_score = float(request.query_params.get('min_volume_score', 0.1))
            max_results = int(request.query_params.get('page_size', 25))
            force_refresh = request.query_params.get('force_refresh', 'false').lower() == 'true'
            capital_available = int(request.query_params.get('capital_available', 50_000_000))
            use_stored = request.query_params.get('use_stored', 'true').lower() == 'true'
            
            # Check if we should serve stored dynamic opportunities first
            if use_stored:
                logger.info("Checking for stored dynamic opportunities...")
                stored_opportunities = self._get_stored_dynamic_opportunities(
                    min_profit=min_profit,
                    max_results=max_results,
                    capital_available=capital_available
                )
                
                if stored_opportunities:
                    logger.info(f"Serving {len(stored_opportunities)} stored dynamic opportunities")
                    return Response({
                        'results': stored_opportunities,
                        'count': len(stored_opportunities), 
                        'data_source': 'stored_dynamic_analysis',
                        'pricing_source': 'osrs_wiki_latest',
                        'analysis_method': 'bidirectional_dynamic_sets',
                        'features': ['combine_analysis', 'decombine_analysis', 'market_conditions', 'risk_scoring'],
                        'metadata': {
                            'last_updated': 'recently',
                            'opportunities_available': len(stored_opportunities),
                            'source': 'database_dynamic_opportunities'
                        }
                    })
                else:
                    logger.info("No stored dynamic opportunities found, falling back to live analysis")
            
            # Build cache key - include lightweight heuristics vs full AI mode
            cache_key = f"ai_set_combining_fast:{min_profit}_{min_volume_score}_{capital_available}_{max_results}"
            cache_ttl = 3600  # 60 minutes for fast analysis
            
            # Check cache first unless force refresh
            cached_opportunities = None if force_refresh else cache.get(cache_key)
            
            if cached_opportunities and not force_refresh:
                return Response({
                    'results': cached_opportunities['results'],
                    'count': len(cached_opportunities['results']),
                    'data_source': 'cached_ai_fast_analysis',
                    'ai_models': ['heuristic_engine', 'deepseek-r1:1.5b', 'gemma3:1b', 'qwen3:4b'],
                    'pricing_source': 'osrs_wiki_api',
                    'features': ['fast_heuristic_analysis', 'parallel_ai_enhancement', 'timeout_protection', 'smart_fallbacks'],
                    'cache_ttl_minutes': 60,
                    'metadata': cached_opportunities['metadata']
                })
            
            # Get fresh opportunities using dynamic AI-powered discovery
            async def get_dynamic_ai_opportunities():
                try:
                    logger.info("Starting dynamic set discovery using OSRS Wiki API and AI analysis")
                    
                    # Use the new dynamic discovery service
                    from services.dynamic_set_discovery_service import dynamic_set_discovery_service
                    
                    opportunities = await dynamic_set_discovery_service.discover_all_opportunities(
                        min_profit=min_profit,
                        max_capital=capital_available,
                        min_confidence=min_volume_score
                    )
                    
                    logger.info(f"Dynamic AI discovery found {len(opportunities)} opportunities")
                    return opportunities
                    
                except Exception as e:
                    logger.error(f"Failed dynamic set discovery with AI: {e}")
                    return []
            
            # Execute the dynamic AI analysis
            ai_opportunities = asyncio.run(get_dynamic_ai_opportunities())
            
            if not ai_opportunities:
                return Response({
                    'results': [],
                    'count': 0,
                    'data_source': 'ai_powered_set_analysis',
                    'ai_models': ['deepseek-r1:1.5b', 'gemma3:1b', 'qwen3:4b'],
                    'error': 'No profitable opportunities found or AI analysis failed'
                })
            
            # Transform dynamic AI opportunities for frontend display
            results = []
            for opp in ai_opportunities[:max_results]:
                # Extract item data from dynamic opportunity
                buy_items = opp.primary_items or []
                sell_items = opp.secondary_items or []
                
                # Calculate costs and revenues
                total_buy_cost = sum(item.get('price', 0) * item.get('quantity', 1) for item in buy_items)
                total_sell_revenue = sum(item.get('price', 0) * item.get('quantity', 1) for item in sell_items)
                
                # Create piece data for calculator compatibility
                pieces_data = []
                piece_volumes_dict = {}
                for item in buy_items + sell_items:
                    item_id = item.get('id', 0)
                    # Use individual item volume if available, otherwise fall back to general volume score
                    item_volume = item.get('volume', item.get('highTime', opp.volume_score or 0))
                    
                    pieces_data.append({
                        'item_id': item_id,
                        'name': item.get('name', ''),
                        'buy_price': item.get('price', 0) if item in buy_items else 0,
                        'sell_price': item.get('price', 0) if item in sell_items else 0,
                        'age_hours': opp.data_freshness,
                        'volume_score': item_volume
                    })
                    
                    # Build piece volumes dictionary for frontend compatibility
                    piece_volumes_dict[str(item_id)] = item_volume
                
                results.append({
                    'id': hash(f"dynamic_ai_{opp.set_name}_{opp.strategy}") % 100000 + 90000,
                    'set_name': opp.set_name,
                    'set_item_id': buy_items[0].get('id', 0) if buy_items else 0,
                    'piece_ids': [item.get('id', 0) for item in buy_items + sell_items],
                    'piece_names': [item.get('name', '') for item in buy_items + sell_items],
                    'piece_prices': [item.get('price', 0) for item in sell_items],
                    'individual_pieces_total_cost': total_buy_cost,
                    'complete_set_price': total_sell_revenue,
                    'lazy_tax_profit': opp.profit_gp,
                    'profit_margin_pct': opp.profit_margin_pct,
                    'piece_volumes': piece_volumes_dict,
                    'set_volume': opp.volume_score,
                    'volume_score': opp.volume_score,
                    'confidence_score': opp.ai_confidence,
                    'ai_risk_level': opp.risk_assessment,
                    'estimated_sets_per_hour': self._estimate_sets_per_hour(opp),
                    'avg_data_age_hours': opp.data_freshness,
                    'pieces_data': pieces_data,
                    'ge_tax': self._calculate_ge_tax(sell_items),
                    'required_capital': opp.required_capital,
                    'strategy_type': opp.strategy,
                    'strategy_description': f"{opp.set_type.replace('_', ' ').title()} {opp.strategy}",
                    
                    # AI-specific fields
                    'ai_timing_recommendation': opp.market_conditions,
                    'ai_market_sentiment': opp.ai_reasoning[:100] + "..." if len(opp.ai_reasoning) > 100 else opp.ai_reasoning,
                    'model_consensus_score': opp.ai_confidence,
                    'liquidity_rating': opp.liquidity_assessment,
                    'execution_difficulty': opp.execution_difficulty,
                    
                    'strategy': {
                        'name': f"🔍 AI Discovered: {opp.set_name}",
                        'description': f"{opp.ai_reasoning[:150]}... | Confidence: {opp.ai_confidence:.1%}",
                        'risk_level': opp.risk_assessment,
                        'min_capital_required': opp.required_capital,
                        'potential_profit_gp': opp.profit_gp,
                        'profit_margin_pct': opp.profit_margin_pct,
                        'estimated_time_minutes': self._estimate_execution_time(opp),
                        'confidence_score': opp.ai_confidence,
                        'is_active': True,
                        'strategy_type': 'dynamic_ai_discovery'
                    }
                })
            
            # Calculate metadata from dynamic opportunities
            avg_confidence_score = sum(opp.ai_confidence for opp in ai_opportunities) / len(ai_opportunities) if ai_opportunities else 0
            high_confidence_count = sum(1 for opp in ai_opportunities if opp.ai_confidence > 0.7)
            avg_volume_score = sum(opp.volume_score for opp in ai_opportunities) / len(ai_opportunities) if ai_opportunities else 0
            
            result_data = {
                'results': results,
                'count': len(results),
                'data_source': 'dynamic_ai_discovery_analysis',
                'ai_models': ['qwen3:4b'],
                'discovery_method': 'live_api_analysis',
                'pricing_source': 'osrs_wiki_/latest_endpoint',  
                'volume_source': 'osrs_wiki_/timeseries_endpoint',
                'mapping_source': 'osrs_wiki_/mapping_endpoint',
                'features': [
                    'dynamic_set_discovery',
                    'comprehensive_item_analysis',
                    'ai_opportunity_generation', 
                    'real_time_market_analysis',
                    'cross_set_arbitrage_detection',
                    'volume_weighted_scoring',
                    'ge_tax_calculations',
                    'no_hardcoded_data'
                ],
                'metadata': {
                    'avg_confidence_score': round(avg_confidence_score, 3),
                    'avg_volume_score': round(avg_volume_score, 3),
                    'high_confidence_count': high_confidence_count,
                    'total_opportunities_found': len(ai_opportunities),
                    'items_analyzed_from_mapping': '200+ most valuable tradeable items',
                    'discovery_method': 'ai_analysis_of_live_osrs_data',
                    'api_endpoints_used': ['/mapping', '/latest', '/timeseries'],
                    'force_refreshed': force_refresh
                }
            }
            
            # Cache the results for longer period since analysis is expensive
            cache.set(cache_key, result_data, cache_ttl)  # 60 minutes for fast analysis
            
            return Response(result_data)
        
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"OSRS Wiki AI set combining analysis failed: {error_details}")
            
            return Response({
                'error': f'OSRS Wiki AI set combining analysis failed: {str(e)}',
                'error_details': error_details if request.query_params.get('debug') == '1' else None,
                'fallback_message': 'Try using the scan endpoint for basic database-backed analysis',
                'support': 'Ensure OSRS Wiki API is accessible'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _get_stored_dynamic_opportunities(self, min_profit: int, max_results: int, capital_available: int):
        """Get stored dynamic opportunities from database"""
        try:
            # Query all SetCombiningOpportunity records (both dynamic and regular)
            stored_opps = SetCombiningOpportunity.objects.filter(
                lazy_tax_profit__gte=min_profit,
                individual_pieces_total_cost__lte=capital_available
            ).select_related('strategy').order_by('-lazy_tax_profit')[:max_results]
            
            if not stored_opps:
                return None
                
            # Convert to API format
            results = []
            for opp in stored_opps:
                strategy_data = opp.strategy.strategy_data or {}
                
                # Calculate individual piece prices from piece IDs and total cost
                piece_prices = []
                piece_names_with_items = []
                
                # Note: piece_prices and piece_names are now handled by the serializer
                
                # Get real volume data with fallback to PriceSnapshot if needed
                piece_volumes = self._get_real_volume_data_for_pieces(opp.piece_ids, opp.piece_volumes)
                
                results.append({
                    'id': opp.id,
                    'set_name': opp.set_name.replace('Dynamic: ', '').replace(' (Combine)', '').replace(' (Decombine)', ''),
                    'set_item_id': opp.set_item_id,
                    'piece_ids': opp.piece_ids,
                    'piece_names': opp.piece_names,  # Will be handled by serializer for regular API calls
                    'individual_pieces_total_cost': opp.individual_pieces_total_cost,
                    'complete_set_price': opp.complete_set_price,
                    'lazy_tax_profit': opp.lazy_tax_profit,
                    'piece_volumes': piece_volumes,
                    'set_volume': opp.set_volume,
                    'strategy_type': strategy_data.get('strategy_type', 'combine'),
                    'profit_margin_pct': opp.strategy.profit_margin_pct if hasattr(opp.strategy, 'profit_margin_pct') else 0,
                    'risk_level': opp.strategy.risk_level,
                    'confidence_score': opp.strategy.confidence_score,
                    'ai_confidence': opp.strategy.confidence_score,  # Alias for compatibility
                    'volume_score': strategy_data.get('volume_score', 0.5),
                    'liquidity_score': strategy_data.get('liquidity_score', 0.5),
                    'volatility_score': strategy_data.get('volatility_score', 0.5),
                    'overall_score': strategy_data.get('overall_score', 0.5),
                    'risk_score': strategy_data.get('risk_score', 0.3),
                    'price_momentum': strategy_data.get('price_momentum', 'stable'),
                    'historical_success_rate': strategy_data.get('historical_success_rate', 0.75),
                    'expected_duration_hours': opp.strategy.estimated_time_minutes / 60 if opp.strategy.estimated_time_minutes else 1.0,
                    'capital_required': opp.individual_pieces_total_cost,
                    'expected_profit': opp.lazy_tax_profit,
                    'created_at': opp.strategy.created_at.isoformat() if hasattr(opp.strategy, 'created_at') else None,
                    'data_source': 'dynamic_bidirectional_analysis'
                })
            
            return results
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to get stored dynamic opportunities: {e}")
            return None

    def _get_real_volume_data_for_pieces(self, piece_ids, stored_piece_volumes):
        """
        Get real volume data for piece items with fallback to PriceSnapshot records.
        Matches the logic used in analyze_dynamic_set_opportunities command.
        """
        from apps.prices.models import PriceSnapshot
        from django.db.models import Avg
        from django.utils import timezone
        from datetime import timedelta
        import logging
        
        logger = logging.getLogger(__name__)
        volume_data = {}
        
        # First, try to use stored volume data if available and valid
        if stored_piece_volumes:
            for item_id in piece_ids:
                stored_volume = stored_piece_volumes.get(str(item_id), 0)
                if stored_volume > 0:
                    volume_data[str(item_id)] = stored_volume
                    continue
        
        # For items without valid stored volume data, get from PriceSnapshot
        for item_id in piece_ids:
            if str(item_id) in volume_data and volume_data[str(item_id)] > 0:
                continue  # Already have valid volume data
                
            try:
                volume = 0
                
                # Get latest price snapshot for this item
                latest_snapshot = PriceSnapshot.objects.filter(
                    item__item_id=item_id
                ).order_by('-created_at').first()
                
                if latest_snapshot:
                    # Use total_volume if available, otherwise sum high/low volumes
                    volume = latest_snapshot.total_volume
                    if not volume:
                        volume = (latest_snapshot.high_price_volume or 0) + (latest_snapshot.low_price_volume or 0)
                
                # If no recent volume data, try historical average
                if not volume:
                    # Try to get average volume from last 7 days of historical data
                    week_ago = timezone.now() - timedelta(days=7)
                    historical_avg = PriceSnapshot.objects.filter(
                        item__item_id=item_id,
                        created_at__gte=week_ago,
                        total_volume__gt=0
                    ).aggregate(avg_volume=Avg('total_volume'))
                    
                    if historical_avg['avg_volume']:
                        volume = int(historical_avg['avg_volume'])
                        logger.debug(f"📊 Using historical volume for item {item_id}: {volume}")
                
                # Last resort: try 30-day average  
                if not volume:
                    month_ago = timezone.now() - timedelta(days=30)
                    monthly_avg = PriceSnapshot.objects.filter(
                        item__item_id=item_id,
                        created_at__gte=month_ago,
                        total_volume__gt=0
                    ).aggregate(avg_volume=Avg('total_volume'))
                    
                    if monthly_avg['avg_volume']:
                        volume = int(monthly_avg['avg_volume'])
                        logger.debug(f"📊 Using 30-day historical volume for item {item_id}: {volume}")
                
                volume_data[str(item_id)] = volume or 0
                
            except Exception as e:
                logger.warning(f"⚠️  Failed to get volume for item {item_id}: {e}")
                volume_data[str(item_id)] = 0
        
        return volume_data
    
    @action(detail=False, methods=['get'])
    def ai_health(self, request):
        """Check AI model health and system status."""
        try:
            import httpx
            from django.utils import timezone as django_timezone
            
            health_status = {
                'ollama_status': 'unknown',
                'models_available': [],
                'pricing_api_status': 'unknown',
                'system_load': 'normal',
                'cache_status': 'active'
            }
            
            # Check Ollama API
            try:
                import asyncio
                async def check_ollama():
                    async with httpx.AsyncClient(timeout=5.0) as client:
                        response = await client.get("http://localhost:11434/api/tags")
                        if response.status_code == 200:
                            data = response.json()
                            models = [model['name'] for model in data.get('models', [])]
                            return 'healthy', models
                        return 'unhealthy', []
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    health_status['ollama_status'], health_status['models_available'] = loop.run_until_complete(check_ollama())
                finally:
                    loop.close()
                    
            except Exception as e:
                health_status['ollama_status'] = f'error: {str(e)}'
            
            # Check OSRS Wiki API
            try:
                async def check_wiki_api():
                    async with httpx.AsyncClient(
                        headers={"User-Agent": "OSRS_High_Alch_Tracker - @latchy Discord"},
                        timeout=5.0
                    ) as client:
                        response = await client.get("https://prices.runescape.wiki/api/v1/osrs/latest?id=4718")
                        return 'healthy' if response.status_code == 200 else 'unhealthy'
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    health_status['pricing_api_status'] = loop.run_until_complete(check_wiki_api())
                finally:
                    loop.close()
                    
            except Exception as e:
                health_status['pricing_api_status'] = f'error: {str(e)}'
            
            # Check cache
            from django.core.cache import cache
            try:
                cache.set('health_check', 'ok', 10)
                health_status['cache_status'] = 'healthy' if cache.get('health_check') == 'ok' else 'unhealthy'
            except Exception as e:
                health_status['cache_status'] = f'error: {str(e)}'
            
            # Overall health
            is_healthy = (
                health_status['ollama_status'] == 'healthy' and
                len(health_status['models_available']) >= 2 and
                health_status['pricing_api_status'] == 'healthy' and
                health_status['cache_status'] == 'healthy'
            )
            
            return Response({
                'status': 'healthy' if is_healthy else 'degraded',
                'details': health_status,
                'timestamp': django_timezone.now().isoformat(),
                'recommendations': self._get_health_recommendations(health_status)
            })
            
        except Exception as e:
            return Response({
                'status': 'error',
                'error': str(e),
                'timestamp': django_timezone.now().isoformat()
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _get_health_recommendations(self, health_status: dict) -> list:
        """Generate health recommendations based on system status."""
        recommendations = []
        
        if health_status['ollama_status'] != 'healthy':
            recommendations.append("Check Ollama service is running: ollama serve")
        
        if len(health_status['models_available']) < 3:
            recommendations.append("Ensure all AI models are available: ollama pull deepseek-r1:1.5b gemma3:1b qwen3:4b")
        
        if health_status['pricing_api_status'] != 'healthy':
            recommendations.append("Check OSRS Wiki API connectivity and rate limits")
        
        if health_status['cache_status'] != 'healthy':
            recommendations.append("Check Redis/cache service is running properly")
        
        return recommendations
    
    def _estimate_sets_per_hour(self, opp) -> int:
        """Estimate sets per hour based on execution difficulty and volume."""
        base_rate = 6  # Base rate per hour
        
        if opp.execution_difficulty == 'easy':
            multiplier = 1.0
        elif opp.execution_difficulty == 'medium':
            multiplier = 0.7
        else:  # complex
            multiplier = 0.4
        
        volume_multiplier = opp.volume_score
        
        return max(1, int(base_rate * multiplier * volume_multiplier))
    
    def _estimate_execution_time(self, opp) -> int:
        """Estimate execution time in minutes."""
        sets_per_hour = self._estimate_sets_per_hour(opp)
        return max(5, int(60 / sets_per_hour)) if sets_per_hour > 0 else 60
    
    def _calculate_ge_tax(self, sell_items: list) -> int:
        """Calculate Grand Exchange tax for sell items."""
        total_tax = 0
        for item in sell_items:
            price = item.get('price', 0)
            quantity = item.get('quantity', 1)
            item_id = item.get('id', 0)
            if price > 100:  # GE tax applies to items over 100 GP
                total_tax += GrandExchangeTax.calculate_tax(price * quantity, item_id)
        return total_tax


class FlippingOpportunityViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for flipping opportunities"""
    
    queryset = FlippingOpportunity.objects.select_related('strategy').all()
    serializer_class = FlippingOpportunitySerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['item_id']
    search_fields = ['item_name']
    ordering_fields = ['margin', 'margin_percentage', 'buy_price', 'sell_price', 'price_stability']
    ordering = ['-margin_percentage', '-margin']
    
    @action(detail=False, methods=['post'])
    def scan(self, request):
        """Scan for new flipping opportunities"""
        from .services.flipping_scanner import FlippingScanner
        
        try:
            scanner = FlippingScanner()
            created_count = scanner.scan_and_create_opportunities()
            
            return Response({
                'message': f'Scanned flipping opportunities successfully',
                'created_count': created_count,
            })
        except Exception as e:
            return Response({
                'error': f'Failed to scan flipping opportunities: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CraftingOpportunityViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for crafting opportunities with AI-weighted scoring and real-time OSRS Wiki data"""
    
    queryset = CraftingOpportunity.objects.select_related('strategy').all()
    serializer_class = CraftingOpportunitySerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['product_id', 'skill_name', 'required_skill_level']
    search_fields = ['product_name', 'skill_name']
    ordering_fields = ['profit_per_craft', 'profit_margin_pct', 'max_crafts_per_hour', 'required_skill_level']
    ordering = ['-profit_per_craft', '-profit_margin_pct']
    
    @action(detail=False, methods=['post'])
    def scan(self, request):
        """Scan for new crafting opportunities with AI-weighted volume analysis"""
        from .services.crafting_calculator import CraftingCalculator
        
        try:
            calculator = CraftingCalculator()
            created_count = calculator.scan_and_create_opportunities()
            
            return Response({
                'message': f'Scanned crafting opportunities with AI volume analysis successfully',
                'created_count': created_count,
            })
        except Exception as e:
            return Response({
                'error': f'Failed to scan crafting opportunities: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def ai_opportunities(self, request):
        """Get real-time AI-weighted crafting opportunities using OSRS Wiki API"""
        from .services.crafting_calculator import CraftingCalculator
        from django.core.cache import cache
        
        try:
            # Get parameters from request
            min_profit_per_craft = int(request.query_params.get('min_profit', 1000))
            min_ai_score = float(request.query_params.get('min_ai_score', 0.3))
            max_skill_level = int(request.query_params.get('max_level', 99))
            skill_name = request.query_params.get('skill_name', '')
            max_results = int(request.query_params.get('page_size', 50))
            force_refresh = request.query_params.get('force_refresh', 'false').lower() == 'true'
            
            return Response({
                'results': [],
                'count': 0,
                'message': 'Crafting AI opportunities endpoint - implementation pending'
            })
            
        except Exception as e:
            return Response({
                'error': f'Failed to get AI crafting opportunities: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MarketConditionSnapshotViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for market condition snapshots"""
    
    queryset = MarketConditionSnapshot.objects.all()
    serializer_class = MarketConditionSnapshotSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['market_condition', 'risk_level']
    ordering_fields = ['timestamp', 'overall_market_score']
    ordering = ['-timestamp']
    
    @action(detail=False, methods=['get'])
    def latest(self, request):
        """Get the latest market condition snapshot"""
        latest = self.queryset.first()
        if not latest:
            return Response({'error': 'No market data available'}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = self.get_serializer(latest)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def is_safe(self, request):
        """Check if market is safe for trading"""
        latest = self.queryset.first()
        if not latest:
            return Response({'safe': True, 'reason': 'No market data available'})
        
        # Market is unsafe if crashing or high risk
        unsafe_conditions = ['crashing']
        unsafe_risk_levels = ['critical', 'high']
        
        is_safe = (
            latest.market_condition not in unsafe_conditions and
            latest.risk_level not in unsafe_risk_levels
        )
        
        return Response({
            'safe': is_safe,
            'market_condition': latest.market_condition,
            'risk_level': latest.risk_level,
            'timestamp': latest.timestamp
        })


class MassOperationsViewSet(viewsets.GenericViewSet):
    """ViewSet for mass trading strategy operations"""
    
    @action(detail=False, methods=['post'])
    def scan_all(self, request):
        """Trigger all opportunity scans"""
        from .services.decanting_detector import DecantingDetector
        from .services.flipping_scanner import FlippingScanner
        from .services.set_combining_analyzer import SetCombiningAnalyzer
        from .services.crafting_calculator import CraftingCalculator
        
        try:
            results = {'total_count': 0}
            
            # Scan decanting opportunities
            detector = DecantingDetector()
            decanting_count = detector.scan_and_create_opportunities()
            results['decanting_count'] = decanting_count
            results['total_count'] += decanting_count
            
            # Scan flipping opportunities  
            scanner = FlippingScanner()
            flipping_count = scanner.scan_and_create_opportunities()
            results['flipping_count'] = flipping_count
            results['total_count'] += flipping_count
            
            # Scan set combining opportunities
            analyzer = SetCombiningAnalyzer()
            set_combining_count = analyzer.scan_and_create_opportunities()
            results['set_combining_count'] = set_combining_count
            results['total_count'] += set_combining_count
            
            # Scan crafting opportunities
            calculator = CraftingCalculator()
            crafting_count = calculator.scan_and_create_opportunities()
            results['crafting_count'] = crafting_count
            results['total_count'] += crafting_count
            
            return Response({
                'message': 'All opportunity scans completed successfully',
                **results
            })
            
        except Exception as e:
            return Response({
                'error': f'Failed to complete all scans: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def cleanup_inactive(self, request):
        """Cleanup inactive strategies"""
        from datetime import timedelta
        from django.utils import timezone
        
        try:
            # Delete strategies that haven't been updated in 7 days and are inactive
            cutoff_date = timezone.now() - timedelta(days=7)
            deleted_count = TradingStrategy.objects.filter(
                is_active=False,
                last_updated__lt=cutoff_date
            ).delete()[0]
            
            return Response({
                'message': 'Cleaned up inactive strategies successfully',
                'deleted_count': deleted_count,
            })
        except Exception as e:
            return Response({
                'error': f'Failed to cleanup inactive strategies: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StrategyPerformanceViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for strategy performance tracking and analytics"""
    
    queryset = StrategyPerformance.objects.all()
    serializer_class = StrategyPerformanceSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['strategy', 'strategy__strategy_type', 'strategy__risk_level']
    ordering_fields = ['recorded_at', 'actual_profit_gp', 'execution_time_minutes']
    ordering = ['-recorded_at']
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get performance summary statistics"""
        from django.db.models import Avg, Sum, Count, Max, Min
        
        try:
            stats = StrategyPerformance.objects.aggregate(
                total_executions=Count('id'),
                total_profit=Sum('actual_profit_gp'),
                avg_profit=Avg('actual_profit_gp'),
                avg_execution_time=Avg('execution_time_minutes'),
                max_profit=Max('actual_profit_gp'),
                min_profit=Min('actual_profit_gp')
            )
            
            return Response({
                'performance_summary': stats,
                'data_source': 'strategy_performance_tracking'
            })
            
        except Exception as e:
            return Response({
                'error': f'Failed to get performance summary: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
