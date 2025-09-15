from rest_framework import serializers
from decimal import Decimal
from .models import (
    TradingStrategy, 
    MoneyMakerStrategy,
    BondFlippingStrategy,
    AdvancedDecantingStrategy, 
    EnhancedSetCombiningStrategy,
    RuneMagicStrategy,
    DecantingOpportunity,
    SetCombiningOpportunity,
    FlippingOpportunity,
    CraftingOpportunity,
    MarketConditionSnapshot,
    StrategyPerformance,
    StrategyType
)


class TradingStrategySerializer(serializers.ModelSerializer):
    """Serializer for TradingStrategy model"""
    
    strategy_type_display = serializers.CharField(source='get_strategy_type_display', read_only=True)
    risk_level_display = serializers.CharField(source='get_risk_level_display', read_only=True)
    optimal_market_condition_display = serializers.CharField(source='get_optimal_market_condition_display', read_only=True)
    hourly_profit_potential = serializers.ReadOnlyField()
    roi_percentage = serializers.ReadOnlyField()
    
    class Meta:
        model = TradingStrategy
        fields = [
            'id', 'strategy_type', 'strategy_type_display', 'name', 'description',
            'potential_profit_gp', 'profit_margin_pct', 'risk_level', 'risk_level_display',
            'min_capital_required', 'recommended_capital', 'optimal_market_condition',
            'optimal_market_condition_display', 'estimated_time_minutes', 'max_volume_per_day',
            'confidence_score', 'is_active', 'last_updated', 'created_at', 'strategy_data',
            'hourly_profit_potential', 'roi_percentage'
        ]
        read_only_fields = ['id', 'last_updated', 'created_at']


class DecantingOpportunitySerializer(serializers.ModelSerializer):
    """Serializer for DecantingOpportunity model"""
    
    strategy = TradingStrategySerializer(read_only=True)
    trading_activity_display = serializers.CharField(source='get_trading_activity_display', read_only=True)
    volume_analysis_summary = serializers.SerializerMethodField()
    risk_assessment = serializers.SerializerMethodField()
    
    class Meta:
        model = DecantingOpportunity
        fields = [
            'id', 'strategy', 'item_id', 'item_name', 'from_dose', 'to_dose',
            'from_dose_price', 'to_dose_price', 'from_dose_volume', 'to_dose_volume',
            'profit_per_conversion', 'profit_per_hour', 'trading_activity',
            'trading_activity_display', 'liquidity_score', 'confidence_score',
            'volume_analysis_data', 'volume_analysis_summary', 'risk_assessment'
        ]
    
    def get_volume_analysis_summary(self, obj):
        """Get volume analysis summary for frontend display"""
        if not obj.volume_analysis_data:
            return None
        
        data = obj.volume_analysis_data
        return {
            'avg_volume_per_hour': data.get('avg_volume_per_hour', 0),
            'volume_trend': data.get('volume_trend', 'unknown'),
            'price_stability': data.get('price_stability', 0),
            'liquidity_indicator': self._get_liquidity_indicator(obj.liquidity_score, obj.trading_activity),
            'volume_description': self._get_volume_description(obj.trading_activity, data.get('avg_volume_per_hour', 0))
        }
    
    def get_risk_assessment(self, obj):
        """Get risk assessment based on volume analysis"""
        activity = obj.trading_activity
        liquidity = obj.liquidity_score
        confidence = obj.confidence_score
        
        # Risk level determination
        if activity in ['very_active', 'active'] and liquidity > 0.8 and confidence > 80:
            risk_level = 'low'
            risk_color = 'green'
            risk_description = 'High volume, consistent trading activity'
        elif activity == 'moderate' and liquidity > 0.5 and confidence > 60:
            risk_level = 'medium'
            risk_color = 'yellow'
            risk_description = 'Moderate volume, some price volatility'
        else:
            risk_level = 'high'
            risk_color = 'red'
            risk_description = 'Low volume or inconsistent trading'
        
        return {
            'risk_level': risk_level,
            'risk_color': risk_color,
            'risk_description': risk_description,
            'confidence_score': confidence,
            'recommendation': self._get_trading_recommendation(risk_level, activity, confidence)
        }
    
    def _get_liquidity_indicator(self, liquidity_score, activity):
        """Get liquidity indicator for frontend"""
        if activity in ['very_active', 'active'] and liquidity_score > 0.8:
            return {'level': 'high', 'color': 'green', 'icon': '🟢'}
        elif activity == 'moderate' and liquidity_score > 0.5:
            return {'level': 'medium', 'color': 'yellow', 'icon': '🟡'}
        else:
            return {'level': 'low', 'color': 'red', 'icon': '🔴'}
    
    def _get_volume_description(self, activity, volume_per_hour):
        """Get human-readable volume description"""
        if activity == 'very_active':
            return f"Very active market ({volume_per_hour:.0f} trades/hour)"
        elif activity == 'active':
            return f"Active trading ({volume_per_hour:.0f} trades/hour)"
        elif activity == 'moderate':
            return f"Moderate volume ({volume_per_hour:.0f} trades/hour)"
        elif activity == 'low':
            return f"Low trading volume ({volume_per_hour:.0f} trades/hour)"
        else:
            return "Inactive or unknown trading volume"
    
    def _get_trading_recommendation(self, risk_level, activity, confidence):
        """Get trading recommendation based on analysis"""
        if risk_level == 'low' and confidence > 80:
            return "✅ Recommended - High confidence trade"
        elif risk_level == 'medium' and confidence > 60:
            return "⚠️ Proceed with caution - Moderate confidence"
        else:
            return "❌ Not recommended - Low confidence or high risk"


class SetCombiningOpportunitySerializer(serializers.ModelSerializer):
    """Serializer for SetCombiningOpportunity model"""
    
    strategy = TradingStrategySerializer(read_only=True)
    profit_margin_pct = serializers.SerializerMethodField()
    piece_prices = serializers.SerializerMethodField()
    piece_names = serializers.SerializerMethodField()
    
    class Meta:
        model = SetCombiningOpportunity
        fields = [
            'id', 'strategy', 'set_name', 'set_item_id', 'piece_ids', 'piece_names', 'piece_prices',
            'individual_pieces_total_cost', 'complete_set_price', 'lazy_tax_profit',
            'piece_volumes', 'set_volume', 'profit_margin_pct'
        ]
    
    def get_profit_margin_pct(self, obj):
        """Calculate profit margin percentage"""
        if obj.individual_pieces_total_cost > 0:
            return round((obj.lazy_tax_profit / obj.individual_pieces_total_cost) * 100, 2)
        return 0.0
    
    def get_piece_names(self, obj):
        """Get actual item names from piece IDs"""
        try:
            from apps.items.models import Item
            
            if obj.piece_ids:
                # Get actual item names from piece IDs
                items = Item.objects.filter(item_id__in=obj.piece_ids)
                item_map = {item.item_id: item.name for item in items}
                
                piece_names = []
                for piece_id in obj.piece_ids:
                    item_name = item_map.get(piece_id, f'Item {piece_id}')
                    piece_names.append(item_name)
                
                return piece_names
            else:
                # Fallback to stored piece names
                return obj.piece_names or []
        except Exception as e:
            print(f"Error getting piece names for opportunity {obj.id}: {e}")
            return obj.piece_names or []

    def get_piece_prices(self, obj):
        """Calculate individual piece prices from piece IDs and total cost"""
        try:
            if obj.piece_ids and obj.individual_pieces_total_cost:
                # Estimate individual prices (simplified approach - could be enhanced with real price data)
                avg_piece_price = obj.individual_pieces_total_cost / len(obj.piece_ids) if obj.piece_ids else 0
                
                piece_prices = []
                for piece_id in obj.piece_ids:
                    piece_prices.append(round(avg_piece_price))  # Simple average for now
                
                return piece_prices
            else:
                # Return empty array if no data available
                return []
        except Exception as e:
            print(f"Error calculating piece prices for opportunity {obj.id}: {e}")
            return []


class FlippingOpportunitySerializer(serializers.ModelSerializer):
    """Serializer for FlippingOpportunity model"""
    
    strategy = TradingStrategySerializer(read_only=True)
    total_profit_potential = serializers.SerializerMethodField()
    
    class Meta:
        model = FlippingOpportunity
        fields = [
            'id', 'strategy', 'item_id', 'item_name', 'buy_price', 'sell_price',
            'margin', 'margin_percentage', 'buy_volume', 'sell_volume',
            'price_stability', 'estimated_flip_time_minutes', 'recommended_quantity',
            'total_profit_potential'
        ]
    
    def get_total_profit_potential(self, obj):
        """Calculate total profit with recommended quantity"""
        return obj.margin * obj.recommended_quantity


class CraftingOpportunitySerializer(serializers.ModelSerializer):
    """Serializer for CraftingOpportunity model"""
    
    strategy = TradingStrategySerializer(read_only=True)
    profit_per_hour = serializers.SerializerMethodField()
    
    class Meta:
        model = CraftingOpportunity
        fields = [
            'id', 'strategy', 'product_id', 'product_name', 'product_price',
            'materials_cost', 'materials_data', 'required_skill_level', 'skill_name',
            'profit_per_craft', 'profit_margin_pct', 'crafting_time_seconds',
            'max_crafts_per_hour', 'profit_per_hour'
        ]
    
    def get_profit_per_hour(self, obj):
        """Calculate profit per hour"""
        return obj.profit_per_craft * obj.max_crafts_per_hour


class MarketConditionSnapshotSerializer(serializers.ModelSerializer):
    """Serializer for MarketConditionSnapshot model"""
    
    market_condition_display = serializers.CharField(source='get_market_condition_display', read_only=True)
    crash_risk_level_display = serializers.CharField(source='get_crash_risk_level_display', read_only=True)
    
    class Meta:
        model = MarketConditionSnapshot
        fields = [
            'id', 'timestamp', 'market_condition', 'market_condition_display',
            'total_volume_24h', 'average_price_change_pct', 'volatility_score',
            'bot_activity_score', 'crash_risk_level', 'crash_risk_level_display',
            'market_data'
        ]
        read_only_fields = ['id', 'timestamp']


class StrategyPerformanceSerializer(serializers.ModelSerializer):
    """Serializer for StrategyPerformance model"""
    
    strategy = TradingStrategySerializer(read_only=True)
    success_rate = serializers.SerializerMethodField()
    profit_vs_expected = serializers.SerializerMethodField()
    
    class Meta:
        model = StrategyPerformance
        fields = [
            'id', 'strategy', 'timestamp', 'actual_profit_gp', 'expected_profit_gp',
            'accuracy_score', 'capital_used', 'execution_time_minutes',
            'successful_trades', 'failed_trades', 'success_rate', 'profit_vs_expected'
        ]
        read_only_fields = ['id', 'timestamp']
    
    def get_success_rate(self, obj):
        """Calculate success rate percentage"""
        total_trades = obj.successful_trades + obj.failed_trades
        if total_trades > 0:
            return round((obj.successful_trades / total_trades) * 100, 2)
        return 0.0
    
    def get_profit_vs_expected(self, obj):
        """Calculate actual vs expected profit ratio"""
        if obj.expected_profit_gp > 0:
            return round((obj.actual_profit_gp / obj.expected_profit_gp) * 100, 2)
        return 0.0


# Simplified serializers for list views
class TradingStrategyListSerializer(serializers.ModelSerializer):
    """Simplified serializer for strategy list views"""
    
    strategy_type_display = serializers.CharField(source='get_strategy_type_display', read_only=True)
    hourly_profit_potential = serializers.ReadOnlyField()
    roi_percentage = serializers.ReadOnlyField()
    
    class Meta:
        model = TradingStrategy
        fields = [
            'id', 'strategy_type', 'strategy_type_display', 'name',
            'potential_profit_gp', 'profit_margin_pct', 'risk_level',
            'min_capital_required', 'confidence_score', 'is_active',
            'estimated_time_minutes', 'hourly_profit_potential', 'roi_percentage'
        ]


class MarketConditionSummarySerializer(serializers.ModelSerializer):
    """Simplified serializer for market condition summary"""
    
    market_condition_display = serializers.CharField(source='get_market_condition_display', read_only=True)
    
    class Meta:
        model = MarketConditionSnapshot
        fields = [
            'id', 'timestamp', 'market_condition', 'market_condition_display',
            'bot_activity_score', 'crash_risk_level', 'volatility_score'
        ]


# Money Maker Strategy Serializers
class MoneyMakerStrategySerializer(serializers.ModelSerializer):
    """Comprehensive money maker strategy serializer"""
    
    strategy = TradingStrategySerializer(read_only=True)
    capital_growth_rate = serializers.SerializerMethodField()
    estimated_time_to_target = serializers.SerializerMethodField()
    profit_efficiency_score = serializers.SerializerMethodField()
    lazy_tax_exploitation = serializers.SerializerMethodField()
    ge_tax_impact_analysis = serializers.SerializerMethodField()
    
    class Meta:
        model = MoneyMakerStrategy
        fields = '__all__'
    
    def get_capital_growth_rate(self, obj):
        """Calculate daily capital growth rate"""
        if obj.starting_capital > 0 and obj.hourly_profit_gp > 0:
            daily_profit = obj.hourly_profit_gp * 24
            growth_rate = (daily_profit / obj.starting_capital) * 100
            return round(growth_rate, 2)
        return 0
    
    def get_estimated_time_to_target(self, obj):
        """Estimate time to reach target capital in hours"""
        if obj.hourly_profit_gp > 0:
            remaining_capital = obj.target_capital - obj.current_capital
            if remaining_capital > 0:
                hours_needed = remaining_capital // obj.hourly_profit_gp
                return int(hours_needed)
        return None
    
    def get_profit_efficiency_score(self, obj):
        """Calculate profit efficiency (profit per GP invested per hour)"""
        if obj.starting_capital > 0 and obj.hourly_profit_gp > 0:
            efficiency = (obj.hourly_profit_gp / obj.starting_capital) * 100
            return round(efficiency * float(obj.capital_efficiency_multiplier), 4)
        return 0
    
    def get_lazy_tax_exploitation(self, obj):
        """Get lazy tax exploitation details"""
        if obj.exploits_lazy_tax and obj.lazy_tax_premium_pct:
            return {
                'exploits_lazy_tax': True,
                'premium_percentage': float(obj.lazy_tax_premium_pct),
                'description': 'Strategy profits from player convenience premium'
            }
        return {'exploits_lazy_tax': False}
    
    def get_ge_tax_impact_analysis(self, obj):
        """Analyze Grand Exchange tax impact on strategy"""
        if obj.hourly_profit_gp > 0:
            avg_trade_size = obj.starting_capital // 10
            ge_tax_per_trade = min(max(avg_trade_size * 0.02, 0), 5_000_000)
            
            return {
                'estimated_ge_tax_per_trade': int(ge_tax_per_trade),
                'hourly_ge_tax_cost': int(ge_tax_per_trade * (obj.hourly_profit_gp // max(obj.strategy.potential_profit_gp, 1))),
                'tax_efficiency_rating': 'medium'
            }
        return {}


class BondFlippingStrategySerializer(serializers.ModelSerializer):
    """Bond flipping strategy serializer - tax-exempt high-value flipping"""
    
    money_maker = MoneyMakerStrategySerializer(read_only=True)
    bond_arbitrage_analysis = serializers.SerializerMethodField()
    tax_exemption_value = serializers.SerializerMethodField()
    
    class Meta:
        model = BondFlippingStrategy
        fields = '__all__'
    
    def get_bond_arbitrage_analysis(self, obj):
        """Analyze bond arbitrage potential"""
        bond_price_gp = obj.bond_price_gp
        gp_per_dollar = float(obj.bond_to_gp_rate)
        bond_cost_usd = 6.99
        gp_from_purchase = gp_per_dollar * bond_cost_usd
        arbitrage_profit = bond_price_gp - gp_from_purchase
        
        return {
            'current_bond_price_gp': bond_price_gp,
            'gp_from_direct_purchase': int(gp_from_purchase),
            'arbitrage_profit_per_bond': int(arbitrage_profit),
            'is_arbitrage_profitable': arbitrage_profit > 0,
            'profit_percentage': round((arbitrage_profit / gp_from_purchase * 100), 2) if gp_from_purchase > 0 else 0
        }
    
    def get_tax_exemption_value(self, obj):
        """Calculate value of GE tax exemption for bonds"""
        bond_price = obj.bond_price_gp
        standard_tax = bond_price * 0.02
        tax_exemption_savings = min(standard_tax, 5_000_000)
        
        return {
            'bond_price': bond_price,
            'ge_tax_saved_per_trade': int(tax_exemption_savings),
            'exemption_value_percentage': round((tax_exemption_savings / bond_price * 100), 2),
            'total_exemption_description': 'Bonds completely exempt from GE tax'
        }


class AdvancedDecantingStrategySerializer(serializers.ModelSerializer):
    """Advanced decanting strategy serializer - your friend's 40M profit method"""
    
    money_maker = MoneyMakerStrategySerializer(read_only=True)
    profit_analysis = serializers.SerializerMethodField()
    optimal_potions = serializers.SerializerMethodField()
    
    class Meta:
        model = AdvancedDecantingStrategy
        fields = '__all__'
    
    def get_profit_analysis(self, obj):
        """Analyze decanting profit potential"""
        speed_per_hour = obj.decanting_speed_per_hour
        min_profit_per_dose = obj.min_profit_per_dose_gp
        total_profit = obj.total_decanting_profit
        total_potions = obj.total_potions_decanted
        
        avg_profit_per_potion = total_profit // max(total_potions, 1) if total_potions > 0 else min_profit_per_dose
        hourly_profit_potential = speed_per_hour * avg_profit_per_potion
        
        return {
            'hourly_potion_capacity': speed_per_hour,
            'minimum_profit_per_dose': min_profit_per_dose,
            'average_profit_per_potion': int(avg_profit_per_potion),
            'hourly_profit_potential': int(hourly_profit_potential),
            'total_realized_profit': total_profit,
            'efficiency_rating': 'high' if hourly_profit_potential > 1_000_000 else 'medium'
        }
    
    def get_optimal_potions(self, obj):
        """Get optimal potion dose combinations"""
        combinations = []
        for combo in obj.optimal_dose_combinations:
            from_dose = combo.get('from_dose')
            to_dose = combo.get('to_dose') 
            profit = combo.get('profit', 0)
            
            combinations.append({
                'from_dose': from_dose,
                'to_dose': to_dose,
                'profit_per_conversion': profit,
                'conversion_ratio': f"{from_dose}-dose → {to_dose}-dose",
                'hourly_profit_potential': profit * obj.decanting_speed_per_hour,
                'efficiency_score': profit * (from_dose - to_dose)
            })
        
        combinations.sort(key=lambda x: x['efficiency_score'], reverse=True)
        return combinations[:10]


class EnhancedSetCombiningStrategySerializer(serializers.ModelSerializer):
    """Enhanced set combining strategy serializer - lazy tax exploitation"""
    
    money_maker = MoneyMakerStrategySerializer(read_only=True)
    lazy_tax_analysis = serializers.SerializerMethodField()
    top_sets = serializers.SerializerMethodField()
    
    class Meta:
        model = EnhancedSetCombiningStrategy
        fields = '__all__'
    
    def get_lazy_tax_analysis(self, obj):
        """Analyze lazy tax exploitation potential"""
        avg_lazy_tax = float(obj.average_lazy_tax_percentage)
        total_profit = obj.total_set_profit
        sets_completed = obj.total_sets_completed
        avg_profit_per_set = total_profit // max(sets_completed, 1) if sets_completed > 0 else 0
        
        return {
            'average_lazy_tax_percentage': avg_lazy_tax,
            'total_sets_completed': sets_completed,
            'total_lazy_tax_profit': total_profit,
            'average_profit_per_set': int(avg_profit_per_set),
            'lazy_tax_explanation': 'Players pay premium for convenience of complete armor/weapon sets',
            'exploitation_rating': 'high' if avg_lazy_tax > 15 else 'medium' if avg_lazy_tax > 8 else 'low'
        }
    
    def get_top_sets(self, obj):
        """Get top profitable set opportunities"""
        opportunities = []
        for set_id, opportunity in obj.set_opportunities.items():
            opportunities.append({
                'set_id': set_id,
                'set_name': opportunity.get('name', 'Unknown Set'),
                'pieces_cost': opportunity.get('pieces_cost', 0),
                'complete_set_price': opportunity.get('set_price', 0),
                'lazy_tax_profit': opportunity.get('profit', 0),
                'lazy_tax_percentage': opportunity.get('lazy_tax_pct', 0),
                'competition_level': obj.set_competition_levels.get(set_id, 'unknown'),
                'recommended_daily_volume': obj.recommended_daily_sets.get(set_id, 1)
            })
        
        opportunities.sort(key=lambda x: x['lazy_tax_profit'], reverse=True)
        return opportunities[:15]


class RuneMagicStrategySerializer(serializers.ModelSerializer):
    """Rune and magic strategy serializer"""
    
    money_maker = MoneyMakerStrategySerializer(read_only=True)
    runecrafting_analysis = serializers.SerializerMethodField()
    high_alchemy_opportunities = serializers.SerializerMethodField()
    
    class Meta:
        model = RuneMagicStrategy
        fields = '__all__'
    
    def get_runecrafting_analysis(self, obj):
        """Analyze runecrafting profit potential"""
        level_required = obj.runecrafting_level_required
        runes_per_hour = obj.runes_per_hour
        
        rune_profits = []
        for rune_data in obj.target_runes:
            rune_profits.append({
                'rune_type': rune_data.get('type', 'Unknown'),
                'profit_per_rune': rune_data.get('profit', 0),
                'hourly_profit': rune_data.get('profit', 0) * runes_per_hour,
                'level_required': rune_data.get('level', level_required)
            })
        
        return {
            'minimum_level_required': level_required,
            'runes_craftable_per_hour': runes_per_hour,
            'profitable_runes': rune_profits,
            'essence_costs': obj.essence_costs
        }
    
    def get_high_alchemy_opportunities(self, obj):
        """Get high alchemy opportunities"""
        opportunities = []
        for alch_opp in obj.high_alch_opportunities:
            profit = alch_opp.get('profit', 0)
            opportunities.append({
                'item_id': alch_opp.get('item_id'),
                'item_name': alch_opp.get('item_name', 'Unknown'),
                'buy_price': alch_opp.get('buy_price', 0),
                'alch_value': alch_opp.get('alch_value', 0),
                'profit_per_alch': profit,
                'hourly_profit_potential': profit * 1200,  # ~1200 alchs/hour max
                'magic_level_required': 55
            })
        
        opportunities.sort(key=lambda x: x['hourly_profit_potential'], reverse=True)
        return opportunities[:10]