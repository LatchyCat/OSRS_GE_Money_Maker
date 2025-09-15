"""
Enhanced Response Generator for AI Trading Assistant
Generates detailed, actionable trading insights with comprehensive analysis.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from services.profit_detection_engine import profit_engine
from services.enhanced_query_patterns import enhanced_patterns

logger = logging.getLogger(__name__)

class EnhancedResponseGenerator:
    """
    Advanced response generation system that creates detailed, actionable trading insights.
    """
    
    def __init__(self):
        self.profit_engine = profit_engine
        self.query_patterns = enhanced_patterns
        
        # Response templates for different scenarios
        self.templates = {
            'million_margin_header': """🎯 **Million+ GP Margin Opportunities**
*For serious traders with substantial capital*

""",
            'capital_strategy_header': """💰 **Capital-Optimized Trading Strategy**
*Tailored for your {capital:,} GP investment*

""",
            'portfolio_header': """📊 **Intelligent Portfolio Analysis**
*Risk-balanced approach with {roi:.1f}% expected ROI*

""",
            'opportunity_section': """**🔥 {tier_name}:**
{opportunities}

""",
            'single_opportunity': """• **{item_name}** - {description}
  💵 Buy: {buy_price:,} GP | 📈 Sell: {sell_price:,} GP | 💰 Profit: {profit:,} GP
  📊 Margin: {margin:.1f}% | ⚡ Score: {score}/100 | 🎲 Risk: {risk_level}
  {additional_info}
""",
            'analysis_footer': """
**📈 Market Analysis:**
{analysis}

**⚠️ Trading Tips:**
{tips}

**🎯 Next Steps:**
{next_steps}
""",
            'no_opportunities': """🔍 **Market Search Complete**

No significant opportunities found matching your criteria at current market conditions.

**💡 Suggestions:**
• Expand your capital range for more options
• Consider different profit tiers (small/medium/large margins)
• Check back in 10-15 minutes as markets change rapidly
• Try specific item queries like "nature runes" or "dragon items"
"""
        }

    def generate_comprehensive_response(self, query: str, query_type: str, 
                                      context: Dict[str, Any], 
                                      capital_gp: Optional[int] = None) -> str:
        """
        Generate comprehensive trading response with detailed analysis.
        """
        try:
            # Determine response type and extract key data
            million_opportunities = context.get('million_margin_opportunities', [])
            portfolio = context.get('optimized_portfolio', {})
            tier_opportunities = context.get('tier_opportunities', [])
            precision_opportunities = context.get('precision_opportunities', [])
            
            # Build response based on available data
            response_parts = []
            
            # 1. Handle million+ margin opportunities
            if million_opportunities:
                response_parts.append(self.templates['million_margin_header'])
                response_parts.append(self._format_opportunities(million_opportunities, "Million Margin Flips"))
            
            # 2. Handle capital-optimized strategies  
            elif portfolio and capital_gp:
                header = self.templates['capital_strategy_header'].format(capital=capital_gp)
                response_parts.append(header)
                response_parts.append(self._format_portfolio_analysis(portfolio, capital_gp))
            
            # 3. Handle tier-based opportunities
            elif tier_opportunities:
                capital_tier = self.query_patterns.get_capital_tier(capital_gp) if capital_gp else 'general'
                tier_name = self._get_tier_display_name(capital_tier)
                response_parts.append(f"💎 **{tier_name} Trading Opportunities**\n")
                response_parts.append(self._format_opportunities(tier_opportunities, tier_name))
            
            # 4. Handle precision opportunities (fallback)
            elif precision_opportunities:
                response_parts.append("🎯 **Precision Trading Opportunities**\n")
                response_parts.append(self._format_precision_opportunities(precision_opportunities))
            
            # 5. No opportunities found
            else:
                return self.templates['no_opportunities']
            
            # Add market analysis and recommendations
            analysis = self._generate_market_analysis(context, query_type, capital_gp)
            tips = self._generate_trading_tips(context, query_type, capital_gp)
            next_steps = self._generate_next_steps(context, query_type, capital_gp)
            
            footer = self.templates['analysis_footer'].format(
                analysis=analysis,
                tips=tips,
                next_steps=next_steps
            )
            response_parts.append(footer)
            
            return '\n'.join(response_parts)
            
        except Exception as e:
            logger.error(f"Enhanced response generation failed: {e}")
            return self._generate_fallback_response(query, context, capital_gp)

    def _format_opportunities(self, opportunities: List[Dict], section_name: str) -> str:
        """Format opportunities with detailed analysis."""
        if not opportunities:
            return "No opportunities found in this tier.\n"
        
        formatted_opps = []
        
        for i, opp in enumerate(opportunities[:8], 1):  # Top 8 opportunities
            # Extract opportunity data
            item_name = opp.get('item_name', 'Unknown Item')
            buy_price = opp.get('buy_price', 0)
            sell_price = opp.get('sell_price', 0)
            profit = opp.get('current_profit', 0)
            margin = opp.get('profit_margin', 0)
            score = opp.get('overall_score', 0)
            
            # Determine risk level
            risk_analysis = opp.get('risk_analysis', {})
            risk_level = risk_analysis.get('risk_level', 'unknown')
            
            # Generate description
            description = self._generate_opportunity_description(opp)
            
            # Additional info
            additional_info = self._generate_additional_info(opp)
            
            formatted_opp = self.templates['single_opportunity'].format(
                item_name=item_name,
                description=description,
                buy_price=buy_price,
                sell_price=sell_price,
                profit=profit,
                margin=margin,
                score=score,
                risk_level=risk_level.replace('_', ' ').title(),
                additional_info=additional_info
            )
            
            formatted_opps.append(formatted_opp)
        
        return '\n'.join(formatted_opps) + '\n'

    def _format_portfolio_analysis(self, portfolio: Dict, capital_gp: int) -> str:
        """Format comprehensive portfolio analysis."""
        allocations = portfolio.get('allocations', {})
        expected_returns = portfolio.get('expected_returns', {})
        recommendations = portfolio.get('recommendations', [])
        
        sections = []
        
        # Portfolio summary
        total_expected = expected_returns.get('total_expected', 0)
        roi_percentage = expected_returns.get('roi_percentage', 0)
        
        sections.append(f"**💼 Portfolio Overview:**")
        sections.append(f"• Capital: {capital_gp:,} GP")
        sections.append(f"• Expected Return: {total_expected:,.0f} GP ({roi_percentage:.1f}% ROI)")
        sections.append("")
        
        # Allocation breakdown
        sections.append("**📈 Asset Allocation:**")
        for tier_name, allocation in allocations.items():
            tier_display = self._get_tier_display_name(tier_name)
            capital_amount = allocation.get('capital', 0)
            percentage = allocation.get('percentage', 0)
            expected_return = allocation.get('expected_return', 0)
            avg_profit = allocation.get('avg_profit_per_flip', 0)
            
            sections.append(f"• **{tier_display}**: {capital_amount:,} GP ({percentage:.1f}%)")
            sections.append(f"  Expected: {expected_return:,.0f} GP | Avg Flip: {avg_profit:,.0f} GP")
            
            # Show top opportunities in this tier
            opportunities = allocation.get('opportunities', [])[:2]  # Top 2
            for opp in opportunities:
                item_name = opp.get('item_name', 'Unknown')
                profit = opp.get('current_profit', 0)
                sections.append(f"    ◦ {item_name}: {profit:,} GP profit")
            sections.append("")
        
        # Recommendations
        if recommendations:
            sections.append("**🎯 Portfolio Recommendations:**")
            for rec in recommendations[:3]:  # Top 3 recommendations
                sections.append(f"• {rec}")
            sections.append("")
        
        return '\n'.join(sections)

    def _format_precision_opportunities(self, opportunities: List[Dict]) -> str:
        """Format precision opportunities from the existing system."""
        if not opportunities:
            return "No precision opportunities available.\n"
        
        formatted = []
        
        for i, opp in enumerate(opportunities[:6], 1):
            item_id = opp.get('item_id', 0)
            current_profit = opp.get('current_profit', 0)
            profit_margin = opp.get('profit_margin', 0)
            buy_price = opp.get('current_buy_price', 0)
            sell_price = opp.get('current_sell_price', 0)
            
            # Try to get item name from ID
            try:
                from apps.items.models import Item
                item = Item.objects.get(item_id=item_id)
                item_name = item.name
            except:
                item_name = f"Item {item_id}"
            
            formatted.append(f"{i}. **{item_name}**")
            formatted.append(f"   💵 Buy: {buy_price:,} GP | 📈 Sell: {sell_price:,} GP")
            formatted.append(f"   💰 Profit: {current_profit:,} GP | 📊 Margin: {profit_margin:.1f}%")
            formatted.append("")
        
        return '\n'.join(formatted)

    def _generate_opportunity_description(self, opportunity: Dict) -> str:
        """Generate contextual description for an opportunity."""
        profit_tier = opportunity.get('profit_tier', {})
        tier_name = profit_tier.get('tier_key', 'unknown')
        
        descriptions = {
            'whale_tier': 'Ultra-high value trade for massive capital',
            'mega_margin': 'Extremely high-margin flip opportunity',
            'million_margin': 'Million+ GP profit potential',
            'large_margin': 'Substantial profit opportunity',
            'medium_margin': 'Solid profit with good volume',
            'small_margin': 'Quick flip with high frequency',
            'micro_margin': 'Volume-based opportunity'
        }
        
        return descriptions.get(tier_name, 'Trading opportunity')

    def _generate_additional_info(self, opportunity: Dict) -> str:
        """Generate additional contextual information."""
        info_parts = []
        
        # Volume info
        volume_analysis = opportunity.get('volume_analysis', {})
        daily_volume = volume_analysis.get('daily_volume', 0)
        volume_level = volume_analysis.get('volume_level', 'unknown')
        
        if daily_volume > 1000:
            info_parts.append(f"🔥 High liquidity: {daily_volume:,} daily volume")
        elif daily_volume > 100:
            info_parts.append(f"📊 Good volume: {daily_volume:,} daily trades")
        elif daily_volume > 0:
            info_parts.append(f"⚠️ Limited volume: {daily_volume} daily trades")
        
        # Capital efficiency
        capital_analysis = opportunity.get('capital_analysis', {})
        roi_percentage = capital_analysis.get('roi_percentage', 0)
        if roi_percentage > 50:
            info_parts.append(f"⚡ Excellent ROI: {roi_percentage:.1f}%")
        elif roi_percentage > 20:
            info_parts.append(f"📈 Good ROI: {roi_percentage:.1f}%")
        
        return ' | '.join(info_parts) if info_parts else "Standard opportunity"

    def _generate_market_analysis(self, context: Dict, query_type: str, capital_gp: Optional[int]) -> str:
        """Generate market analysis summary."""
        analysis_parts = []
        
        # Market conditions
        market_signals = context.get('market_signals', [])
        if market_signals:
            strong_buy_count = len([s for s in market_signals if s.get('signal_type') == 'strong_buy'])
            buy_count = len([s for s in market_signals if s.get('signal_type') == 'buy'])
            
            if strong_buy_count > 0:
                analysis_parts.append(f"• {strong_buy_count} strong buy signals detected")
            if buy_count > 0:
                analysis_parts.append(f"• {buy_count} buy opportunities identified")
        
        # Capital tier analysis
        if capital_gp:
            tier = self.query_patterns.get_capital_tier(capital_gp)
            tier_advice = {
                'micro': 'Focus on high-frequency, low-risk opportunities',
                'small': 'Balance volume and margins for steady growth',
                'medium': 'Diversify across multiple profit tiers',
                'high': 'Target large margins with selective opportunities',
                'whale': 'Focus on exclusive high-value items'
            }
            advice = tier_advice.get(tier, 'Standard trading approach recommended')
            analysis_parts.append(f"• {advice} for your capital tier")
        
        # Market timing
        analysis_parts.append("• Current market conditions favor active trading")
        
        return '\n'.join(analysis_parts) if analysis_parts else "Market analysis in progress"

    def _generate_trading_tips(self, context: Dict, query_type: str, capital_gp: Optional[int]) -> str:
        """Generate actionable trading tips."""
        tips = [
            "Start with smaller quantities to test market conditions",
            "Monitor buy limits to maximize trading potential",
            "Set profit targets before entering positions"
        ]
        
        # Context-specific tips
        if capital_gp and capital_gp >= 1_000_000:
            tips.append("Consider diversifying across multiple high-value opportunities")
        
        risk_assessments = context.get('risk_assessments', [])
        if risk_assessments:
            high_risk_count = len([r for r in risk_assessments if r.get('risk_score', 0) > 60])
            if high_risk_count > 0:
                tips.append("Several high-risk opportunities detected - proceed with caution")
        
        return '\n'.join(f"• {tip}" for tip in tips[:4])

    def _generate_next_steps(self, context: Dict, query_type: str, capital_gp: Optional[int]) -> str:
        """Generate actionable next steps."""
        steps = []
        
        # Query-specific steps
        if query_type == 'million_margin_flips':
            steps.extend([
                "Verify current Grand Exchange prices before trading",
                "Start with one high-confidence opportunity",
                "Monitor market conditions for optimal entry timing"
            ])
        elif query_type.startswith('capital_'):
            steps.extend([
                "Begin with the highest-scoring opportunity",
                "Set aside 20% of capital for emergency opportunities",
                "Track performance and adjust strategy accordingly"
            ])
        else:
            steps.extend([
                "Review the top 3 opportunities for your capital level",
                "Check current market prices and volumes",
                "Start trading with smaller quantities initially"
            ])
        
        return '\n'.join(f"{i+1}. {step}" for i, step in enumerate(steps[:3]))

    def _get_tier_display_name(self, tier_key: str) -> str:
        """Convert tier key to display name."""
        display_names = {
            'whale_tier': 'Whale Trading',
            'mega_margin': 'Mega Margin',
            'million_margin': 'Million Margin',
            'large_margin': 'Large Margin',
            'medium_margin': 'Medium Margin', 
            'small_margin': 'Small Margin',
            'micro_margin': 'Micro Margin',
            'whale': 'Whale Tier',
            'high': 'High Capital',
            'medium': 'Medium Capital',
            'small': 'Small Capital',
            'micro': 'Micro Capital'
        }
        return display_names.get(tier_key, tier_key.replace('_', ' ').title())

    def _generate_fallback_response(self, query: str, context: Dict, capital_gp: Optional[int]) -> str:
        """Generate fallback response when main generation fails."""
        return f"""🤖 **AI Trading Assistant**

I'm analyzing your query: "{query}"

Current market data is being processed. Please try:
• Asking about specific items like "nature runes" or "dragon weapons"
• Specifying your capital amount for personalized recommendations
• Requesting "profitable items" or "high alchemy opportunities"

Market analysis is continuously updating. Check back shortly for fresh opportunities!
"""

# Global instance
enhanced_response_generator = EnhancedResponseGenerator()