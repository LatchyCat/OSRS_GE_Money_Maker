"""
AI-powered decanting analyzer using existing profit calculation data with Ollama AI models.

This service leverages the working ProfitCalculation system that powers the 
successful high-alchemy view, then applies AI analysis for smart decanting recommendations.
"""

import asyncio
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum

import ollama
from django.utils import timezone
from django.db.models import Q
from django.core.cache import cache

from apps.items.models import Item
from apps.prices.models import ProfitCalculation

logger = logging.getLogger(__name__)


@dataclass
class PotionAnalysis:
    """AI analysis results for a potion family."""
    base_name: str
    doses_available: List[int]  # Available doses (1,2,3,4)
    profit_potential: float     # AI-scored profit potential 0-1
    risk_assessment: str        # low, medium, high
    market_conditions: str      # AI assessment of market
    recommended_conversions: List[Tuple[int, int]]  # (from_dose, to_dose) pairs
    confidence_score: float     # AI confidence in analysis 0-1


@dataclass
class DecantingRecommendation:
    """AI-powered decanting recommendation."""
    potion_name: str
    from_dose: int
    to_dose: int
    buy_price: int
    sell_price: int
    profit_per_conversion: int
    profit_margin_pct: float
    ai_confidence: float
    risk_level: str
    market_timing: str          # AI assessment: "excellent", "good", "fair", "poor"
    volume_rating: str          # AI assessment: "high", "medium", "low"
    reasoning: str              # AI explanation of the recommendation


class AIDecantingAnalyzer:
    """
    AI-powered decanting analyzer using three Ollama models for consensus decisions.
    """
    
    def __init__(self):
        self.ollama_client = ollama.Client()
        
        # Three AI models for consensus analysis
        self.analysis_model = "qwen3:4b"        # Primary analysis
        self.calculation_model = "deepseek-r1:1.5b"  # Profit calculations  
        self.validation_model = "gemma3:1b"     # Validation and risk assessment
        
        self.cache_timeout = 1800  # 30 minute cache for AI analysis
        
    async def analyze_decanting_opportunities(
        self, 
        min_profit_gp: int = 1,
        max_results: int = 50
    ) -> List[DecantingRecommendation]:
        """
        Get fast decanting recommendations using mathematical profit calculations.
        
        Args:
            min_profit_gp: Minimum profit threshold
            max_results: Maximum recommendations to return
            
        Returns:
            List of profitable decanting recommendations
        """
        logger.info("Starting fast decanting analysis...")
        
        # Get potion families with fresh profit data
        potion_families = await self._discover_potion_families()
        logger.info(f"Discovered {len(potion_families)} potion families for analysis")
        
        if not potion_families:
            logger.warning("No potion families found for analysis")
            return []
        
        # Calculate profitable conversions directly (skip AI for speed)
        all_recommendations = []
        families_with_opportunities = 0
        total_opportunities_before_filter = 0
        
        for family_name, doses_data in potion_families.items():
            try:
                family_recommendations = await self._calculate_fast_recommendations(
                    family_name, doses_data, min_profit_gp
                )
                total_opportunities_before_filter += len(family_recommendations)
                if family_recommendations:
                    families_with_opportunities += 1
                    logger.debug(f"{family_name}: {len(family_recommendations)} opportunities")
                all_recommendations.extend(family_recommendations)
                    
            except Exception as e:
                logger.warning(f"Failed to analyze {family_name}: {e}")
                continue
        
        logger.info(f"Found opportunities in {families_with_opportunities}/{len(potion_families)} families")
        logger.info(f"Total opportunities before final filter: {total_opportunities_before_filter}")
        
        # Sort by profit potential
        all_recommendations.sort(
            key=lambda x: x.profit_per_conversion, 
            reverse=True
        )
        
        result = all_recommendations[:max_results]
        logger.info(f"Generated {len(result)} fast decanting recommendations")
        
        return result
    
    async def _discover_potion_families(self) -> Dict[str, Dict]:
        """
        Discover potion families using the existing ProfitCalculation system.
        
        Returns:
            Dictionary mapping family names to dose data
        """
        # Get items with profit calculations that look like potions
        potion_items = await asyncio.to_thread(
            lambda: list(
                ProfitCalculation.objects.select_related('item').filter(
                    Q(item__name__iregex=r'.*\([1-4]\).*') &  # Has dose indicators
                    Q(current_buy_price__gt=0) &              # Has valid prices
                    Q(current_sell_price__gt=0) &
                    Q(item__is_active=True)
                ).order_by('item__name')
            )
        )
        
        families = {}
        
        for profit_calc in potion_items:
            item_name = profit_calc.item.name
            family_name = self._extract_family_name(item_name)
            dose = self._extract_dose_count(item_name)
            
            if family_name and dose:
                if family_name not in families:
                    families[family_name] = {}
                
                families[family_name][dose] = {
                    'item_id': profit_calc.item.item_id,
                    'item_name': item_name,
                    'buy_price': profit_calc.current_buy_price,
                    'sell_price': profit_calc.current_sell_price,
                    'volume_category': profit_calc.volume_category,
                    'profit_calc': profit_calc,
                    'last_updated': profit_calc.created_at
                }
        
        # Filter families with at least 2 doses for decanting
        valid_families = {
            name: data for name, data in families.items() 
            if len(data) >= 2
        }
        
        return valid_families
    
    def _extract_family_name(self, item_name: str) -> Optional[str]:
        """Extract base potion name without dose information."""
        # Remove dose indicators like (1), (2), (3), (4) 
        base_name = re.sub(r'\s*\([1-4]\)\s*', '', item_name).strip()
        
        # Check if it's actually a potion
        potion_keywords = [
            'potion', 'brew', 'mix', 'antipoison', 'antifire', 'antidote',
            'prayer', 'combat', 'strength', 'attack', 'defence', 'ranging',
            'magic', 'agility', 'energy', 'stamina', 'serum', 'balm'
        ]
        
        if any(keyword in base_name.lower() for keyword in potion_keywords):
            return base_name
            
        return None
    
    def _extract_dose_count(self, item_name: str) -> Optional[int]:
        """Extract dose count from item name."""
        match = re.search(r'\(([1-4])\)', item_name)
        return int(match.group(1)) if match else None
    
    async def _ai_analyze_family(self, family_name: str, doses_data: Dict) -> Optional[PotionAnalysis]:
        """
        Use AI models to analyze a potion family for decanting potential.
        
        Args:
            family_name: Base name of potion family
            doses_data: Dictionary of dose data with prices and volumes
            
        Returns:
            AI analysis of the potion family
        """
        cache_key = f"ai_analysis:{family_name}"
        cached_analysis = cache.get(cache_key)
        if cached_analysis:
            return cached_analysis
        
        # Prepare data for AI analysis
        analysis_prompt = self._build_analysis_prompt(family_name, doses_data)
        
        try:
            # Get analysis from primary AI model
            analysis_response = await asyncio.to_thread(
                self.ollama_client.generate,
                model=self.analysis_model,
                prompt=analysis_prompt,
                options={"temperature": 0.1}  # Low temperature for consistent analysis
            )
            
            # Parse AI analysis
            analysis = self._parse_ai_analysis(family_name, doses_data, analysis_response['response'])
            
            if analysis:
                # Cache successful analysis
                cache.set(cache_key, analysis, self.cache_timeout)
            
            return analysis
            
        except Exception as e:
            logger.error(f"AI analysis failed for {family_name}: {e}")
            return None
    
    def _build_analysis_prompt(self, family_name: str, doses_data: Dict) -> str:
        """Build prompt for AI analysis of potion family."""
        
        prompt = f"""Analyze this OSRS potion family for decanting profit opportunities:

POTION: {family_name}

MARKET DATA:
"""
        
        for dose, data in sorted(doses_data.items()):
            prompt += f"""
{dose}-dose: Buy {data['buy_price']}gp, Sell {data['sell_price']}gp
Volume: {data['volume_category']} trading
Updated: {data['last_updated'].strftime('%Y-%m-%d %H:%M')}
"""
        
        prompt += f"""
DECANTING RULES:
- Drinking a potion reduces dose by 1 (4→3, 3→2, 2→1)  
- Barbarian Herblore lets you decant remaining doses to separate potions
- Example: Buy 4-dose for 1000gp, drink once (3 doses remain), split into 3x 1-dose, sell each for 400gp = 1200gp revenue

ANALYSIS REQUIRED:
1. PROFIT_POTENTIAL: Rate 0.0-1.0 based on conversion profits
2. RISK_LEVEL: "low"/"medium"/"high" based on price stability
3. MARKET_CONDITIONS: Brief assessment of trading conditions  
4. BEST_CONVERSIONS: List viable (from_dose→to_dose) pairs
5. CONFIDENCE: Your confidence 0.0-1.0 in this analysis

Respond in this exact format:
PROFIT_POTENTIAL: 0.X
RISK_LEVEL: low/medium/high
MARKET_CONDITIONS: brief description
BEST_CONVERSIONS: 4→1,3→1,2→1 (if viable)
CONFIDENCE: 0.X
"""
        
        return prompt
    
    def _parse_ai_analysis(self, family_name: str, doses_data: Dict, ai_response: str) -> Optional[PotionAnalysis]:
        """Parse AI response into structured analysis."""
        try:
            lines = ai_response.strip().split('\n')
            analysis_data = {}
            
            for line in lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    analysis_data[key.strip()] = value.strip()
            
            # Extract and validate values
            profit_potential = float(analysis_data.get('PROFIT_POTENTIAL', '0.0'))
            risk_level = analysis_data.get('RISK_LEVEL', 'high').lower()
            market_conditions = analysis_data.get('MARKET_CONDITIONS', 'unknown')
            confidence = float(analysis_data.get('CONFIDENCE', '0.0'))
            
            # Parse conversions
            conversions_str = analysis_data.get('BEST_CONVERSIONS', '')
            recommended_conversions = []
            
            if conversions_str:
                for conv in conversions_str.split(','):
                    if '→' in conv:
                        try:
                            from_dose, to_dose = conv.strip().split('→')
                            recommended_conversions.append((int(from_dose), int(to_dose)))
                        except ValueError:
                            continue
            
            return PotionAnalysis(
                base_name=family_name,
                doses_available=list(doses_data.keys()),
                profit_potential=profit_potential,
                risk_assessment=risk_level,
                market_conditions=market_conditions,
                recommended_conversions=recommended_conversions,
                confidence_score=confidence
            )
            
        except Exception as e:
            logger.warning(f"Failed to parse AI analysis for {family_name}: {e}")
            return None
    
    async def _generate_recommendations(
        self, 
        analysis: PotionAnalysis, 
        doses_data: Dict, 
        min_profit_gp: int
    ) -> List[DecantingRecommendation]:
        """
        Generate specific recommendations based on AI analysis.
        
        Args:
            analysis: AI analysis of potion family
            doses_data: Market data for doses
            min_profit_gp: Minimum profit threshold
            
        Returns:
            List of specific decanting recommendations
        """
        recommendations = []
        
        for from_dose, to_dose in analysis.recommended_conversions:
            if from_dose not in doses_data or to_dose not in doses_data:
                continue
            
            from_data = doses_data[from_dose]
            to_data = doses_data[to_dose]
            
            # Calculate decanting profit
            buy_price = from_data['buy_price']
            sell_price = to_data['sell_price']
            
            # Decanting calculation: drink reduces dose by 1, remaining split into target doses
            remaining_doses = from_dose - 1
            target_potions_created = remaining_doses // to_dose
            
            if target_potions_created <= 0:
                continue
            
            revenue = target_potions_created * sell_price
            profit = revenue - buy_price
            
            if profit < min_profit_gp:
                continue
            
            profit_margin = (profit / buy_price * 100) if buy_price > 0 else 0
            
            # Get AI assessment of this specific conversion
            ai_assessment = await self._ai_assess_conversion(
                analysis.base_name, from_dose, to_dose, profit, profit_margin,
                from_data['volume_category'], to_data['volume_category']
            )
            
            recommendation = DecantingRecommendation(
                potion_name=analysis.base_name,
                from_dose=from_dose,
                to_dose=to_dose,
                buy_price=buy_price,
                sell_price=sell_price,
                profit_per_conversion=profit,
                profit_margin_pct=profit_margin,
                ai_confidence=ai_assessment.get('confidence', analysis.confidence_score),
                risk_level=ai_assessment.get('risk', analysis.risk_assessment),
                market_timing=ai_assessment.get('timing', 'fair'),
                volume_rating=ai_assessment.get('volume', 'medium'),
                reasoning=ai_assessment.get('reasoning', 'AI-recommended decanting opportunity')
            )
            
            recommendations.append(recommendation)
        
        return recommendations
    
    async def _ai_assess_conversion(
        self, 
        potion_name: str, 
        from_dose: int, 
        to_dose: int,
        profit: int,
        margin: float,
        from_volume: str,
        to_volume: str
    ) -> Dict[str, str]:
        """Get AI assessment of specific conversion."""
        
        prompt = f"""Assess this OSRS decanting conversion:

CONVERSION: {potion_name} {from_dose}-dose → {to_dose}-dose
PROFIT: {profit}gp ({margin:.1f}% margin)
VOLUME: Buy from {from_volume} market, sell to {to_volume} market

Rate this conversion:
CONFIDENCE: 0.0-1.0 (higher = better opportunity)
RISK: low/medium/high
TIMING: excellent/good/fair/poor (market timing)
VOLUME: high/medium/low (trading volume adequacy)
REASONING: Brief explanation

Format:
CONFIDENCE: 0.X
RISK: level
TIMING: rating  
VOLUME: rating
REASONING: explanation
"""
        
        try:
            response = await asyncio.to_thread(
                self.ollama_client.generate,
                model=self.validation_model,
                prompt=prompt,
                options={"temperature": 0.2}
            )
            
            # Parse response
            lines = response['response'].strip().split('\n')
            result = {}
            
            for line in lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    result[key.strip().lower()] = value.strip()
            
            return result
            
        except Exception as e:
            logger.warning(f"AI conversion assessment failed: {e}")
            return {
                'confidence': '0.5',
                'risk': 'medium', 
                'timing': 'fair',
                'volume': 'medium',
                'reasoning': 'Default assessment due to AI error'
            }
    
    async def _calculate_fast_recommendations(
        self, 
        family_name: str, 
        doses_data: Dict, 
        min_profit_gp: int
    ) -> List[DecantingRecommendation]:
        """
        Calculate profitable decanting opportunities without AI analysis.
        
        Args:
            family_name: Base name of potion family
            doses_data: Market data for doses
            min_profit_gp: Minimum profit threshold
            
        Returns:
            List of profitable decanting recommendations
        """
        recommendations = []
        total_conversions_checked = 0
        profitable_conversions = 0
        
        # Check all possible dose conversions (higher to lower doses)
        for from_dose in sorted(doses_data.keys(), reverse=True):
            for to_dose in sorted(doses_data.keys()):
                total_conversions_checked += 1
                
                if from_dose <= to_dose:  # Skip invalid conversions
                    continue
                
                from_data = doses_data[from_dose]
                to_data = doses_data[to_dose]
                
                # Calculate decanting profit
                buy_price = from_data['buy_price']
                sell_price = to_data['sell_price']
                
                # Decanting calculation: drink reduces dose by 1, remaining split into target doses
                remaining_doses = from_dose - 1
                target_potions_created = remaining_doses // to_dose
                
                if target_potions_created <= 0:
                    continue
                
                revenue = target_potions_created * sell_price
                profit = revenue - buy_price
                
                if profit < min_profit_gp:
                    continue
                
                profitable_conversions += 1
                
                profit_margin = (profit / buy_price * 100) if buy_price > 0 else 0
                
                # Create recommendation with reasonable defaults (no AI needed)
                recommendation = DecantingRecommendation(
                    potion_name=family_name,
                    from_dose=from_dose,
                    to_dose=to_dose,
                    buy_price=buy_price,
                    sell_price=sell_price,
                    profit_per_conversion=profit,
                    profit_margin_pct=profit_margin,
                    ai_confidence=0.8,  # High confidence for mathematical calculation
                    risk_level="medium",  # Conservative default
                    market_timing="good",  # Neutral default
                    volume_rating=from_data['volume_category'],
                    reasoning=f"Buy {from_dose}-dose for {buy_price}gp, drink once, split {remaining_doses} doses into {target_potions_created}x {to_dose}-dose potions, sell for {sell_price}gp each. Profit: {profit}gp"
                )
                
                recommendations.append(recommendation)
        
        if total_conversions_checked > 0:
            logger.debug(f"{family_name}: {profitable_conversions}/{total_conversions_checked} conversions profitable")
        
        return recommendations


# Singleton instance for the application
ai_decanting_analyzer = AIDecantingAnalyzer()