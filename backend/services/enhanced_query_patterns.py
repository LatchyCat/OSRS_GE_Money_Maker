"""
Enhanced Query Patterns for AI Trading Assistant
100+ intelligent patterns to handle diverse trading scenarios and capital optimization.
"""

import re
from typing import Dict, List, Tuple

class EnhancedQueryPatterns:
    """
    Comprehensive query pattern matching for intelligent trading recommendations.
    """
    
    def __init__(self):
        self.patterns = {
            # Capital-Specific Strategies (20+ patterns)
            'capital_10k_strategy': [
                r'\b10[k]?\s*gp?\b.*(?:strategy|invest|flip|trade)',
                r'small.*budget.*(?:10k|ten.*thousand)',
                r'starting.*capital.*10k',
                r'beginner.*money.*10k',
                r'turn.*10k.*into',
                r'what.*can.*i.*do.*with.*10k',
            ],
            'capital_100k_strategy': [
                r'\b100[k]?\s*gp?\b.*(?:strategy|invest|flip|trade)',
                r'medium.*budget.*(?:100k|hundred.*thousand)',
                r'turn.*100k.*into',
                r'flip.*with.*100k',
                r'best.*items.*100k.*budget',
                r'intermediate.*trading.*100k',
            ],
            'capital_1m_strategy': [
                r'\b1m\s*gp?\b.*(?:strategy|invest|flip|trade)',
                r'\b1.*million\s*gp?\b.*(?:strategy|flip)',
                r'turn.*1m.*into',
                r'million.*gp.*investment',
                r'high.*value.*trading.*1m',
                r'whale.*trading.*strategies',
            ],
            'capital_10m_strategy': [
                r'\b10m\s*gp?\b.*(?:strategy|invest|flip|trade)',
                r'\b10.*million\s*gp?\b.*(?:strategy|flip)',
                r'turn.*10m.*into',
                r'massive.*capital.*10m',
                r'serious.*trading.*10m',
                r'professional.*level.*trading',
            ],

            # High-Value Flip Detection (15+ patterns)
            'million_margin_flips': [
                r'million.*gp.*margin',
                r'1m\+.*profit',
                r'huge.*margins',
                r'big.*money.*flips',
                r'whale.*trading',
                r'high.*value.*items',
                r'rare.*item.*trading',
                r'boss.*drop.*flipping',
                r'expensive.*gear.*flips',
                r'maximum.*profit.*items',
            ],
            'medium_margin_flips': [
                r'(?:100k|medium).*margin',
                r'mid.*tier.*trading',
                r'regular.*profit.*items',
                r'steady.*income.*flips',
                r'consistent.*margins',
                r'reliable.*trading',
            ],
            'small_margin_flips': [
                r'(?:small|quick).*margins',
                r'fast.*flips',
                r'high.*frequency.*trading',
                r'volume.*trading',
                r'bulk.*opportunities',
                r'frequent.*trades',
            ],

            # Specialized Item Categories (25+ patterns)
            'magic_items_trading': [
                r'magic.*items',
                r'runes?.*trading',
                r'nature.*runes?',
                r'law.*runes?',
                r'death.*runes?',
                r'blood.*runes?',
                r'wrath.*runes?',
                r'battlestaffs?.*profit',
                r'magic.*equipment',
                r'spell.*components',
                r'runecrafting.*supplies',
                r'magic.*gear.*flips',
            ],
            'resource_trading': [
                r'resources?.*trading',
                r'ore.*flipping',
                r'logs?.*profit',
                r'mining.*materials',
                r'woodcutting.*supplies',
                r'fishing.*resources',
                r'farming.*materials',
                r'crafting.*supplies',
                r'skilling.*resources',
                r'raw.*materials',
                r'gems?.*trading',
                r'bars?.*profit',
            ],
            'consumable_trading': [
                r'potions?.*trading',
                r'food.*flipping',
                r'consumables?.*profit',
                r'prayer.*potions?',
                r'combat.*potions?',
                r'skill.*potions?',
                r'herblore.*items',
                r'cooking.*supplies',
                r'temporary.*boost.*items',
            ],
            'rare_valuable_items': [
                r'rare.*items',
                r'valuable.*gear',
                r'boss.*drops',
                r'high.*level.*equipment',
                r'end.*game.*gear',
                r'expensive.*items',
                r'luxury.*items',
                r'collector.*items',
                r'discontinued.*items',
                r'event.*items',
            ],

            # Advanced Trading Strategies (20+ patterns)
            'seasonal_trading': [
                r'seasonal.*items',
                r'holiday.*trading',
                r'event.*speculation',
                r'limited.*time.*items',
                r'christmas.*items',
                r'halloween.*items',
                r'summer.*event.*items',
                r'update.*speculation',
            ],
            'volume_abuse_strategies': [
                r'buy.*limit.*abuse',
                r'volume.*strategies',
                r'bulk.*trading',
                r'mass.*buying',
                r'quantity.*restrictions',
                r'limit.*optimization',
                r'high.*volume.*items',
            ],
            'market_manipulation': [
                r'market.*control',
                r'price.*manipulation',
                r'cornering.*market',
                r'monopoly.*strategies',
                r'supply.*control',
                r'demand.*creation',
            ],
            'arbitrage_opportunities': [
                r'arbitrage',
                r'price.*differences',
                r'market.*inefficiencies',
                r'cross.*market.*opportunities',
                r'regional.*price.*gaps',
            ],

            # Risk and Timing Analysis (15+ patterns)
            'low_risk_investments': [
                r'safe.*investments',
                r'low.*risk.*trading',
                r'guaranteed.*profit',
                r'stable.*items',
                r'conservative.*trading',
                r'risk.*free.*opportunities',
                r'secure.*investments',
            ],
            'high_risk_high_reward': [
                r'high.*risk.*high.*reward',
                r'risky.*investments',
                r'volatile.*items',
                r'gambling.*items',
                r'speculative.*trading',
                r'dangerous.*flips',
            ],
            'market_timing': [
                r'when.*to.*buy',
                r'when.*to.*sell',
                r'timing.*the.*market',
                r'optimal.*entry.*point',
                r'best.*time.*to.*trade',
                r'market.*cycles',
                r'price.*patterns',
            ],

            # Skill-Based Trading (15+ patterns)
            'combat_supplies': [
                r'combat.*supplies',
                r'pvp.*gear',
                r'pvm.*equipment',
                r'boss.*supplies',
                r'raid.*gear',
                r'slayer.*equipment',
                r'training.*combat.*gear',
            ],
            'skilling_supplies': [
                r'skilling.*supplies',
                r'training.*materials',
                r'xp.*efficient.*items',
                r'skill.*training.*gear',
                r'leveling.*supplies',
                r'construction.*materials',
                r'crafting.*training.*items',
            ],
            'quest_items': [
                r'quest.*items',
                r'requirement.*items',
                r'achievement.*items',
                r'diary.*requirements',
                r'unlock.*items',
            ],

            # Growth and Progression (10+ patterns)
            'compound_growth': [
                r'compound.*growth',
                r'exponential.*returns',
                r'growing.*wealth',
                r'scaling.*profits',
                r'reinvestment.*strategies',
                r'wealth.*building',
            ],
            'portfolio_diversification': [
                r'diversified.*portfolio',
                r'multiple.*investments',
                r'balanced.*trading',
                r'risk.*distribution',
                r'varied.*strategies',
            ],

            # Market Intelligence (10+ patterns)
            'insider_knowledge': [
                r'insider.*knowledge',
                r'market.*secrets',
                r'hidden.*opportunities',
                r'advanced.*techniques',
                r'professional.*strategies',
                r'expert.*tips',
                r'what.*pros.*do',
            ],
            'competitive_analysis': [
                r'competition.*analysis',
                r'market.*share',
                r'competitor.*strategies',
                r'trading.*competition',
                r'market.*dominance',
            ],

            # Specific Profit Targets (10+ patterns)
            'double_money': [
                r'double.*my.*money',
                r'2x.*returns',
                r'doubling.*capital',
                r'turn.*(\d+k?).*into.*(\d+k?)',
                r'100%.*returns',
            ],
            'triple_money': [
                r'triple.*my.*money',
                r'3x.*returns',
                r'tripling.*capital',
                r'300%.*returns',
            ],
            'exact_profit_targets': [
                r'make.*exactly.*(\d+[km]?).*profit',
                r'need.*(\d+[km]?).*by.*(\w+)',
                r'goal.*of.*(\d+[km]?)',
                r'target.*(\d+[km]?).*gp',
            ]
        }

        # Capital extraction patterns
        self.capital_patterns = [
            r'(\d+(?:\.\d+)?)\s*m(?:il)?(?:lion)?\s*gp?',  # 1m, 1.5mil, 10million gp
            r'(\d+(?:\.\d+)?)\s*k\s*gp?',                  # 100k, 500k gp  
            r'(\d+(?:,\d{3})*)\s*gp?',                     # 1,000,000 gp
            r'(\d+(?:\.\d+)?)\s*b(?:il)?(?:lion)?\s*gp?',  # 1b, 1.5bil gp
        ]

    def extract_capital_amount(self, query: str) -> int:
        """Extract capital amount from query in GP."""
        query_lower = query.lower()
        
        for pattern in self.capital_patterns:
            matches = re.finditer(pattern, query_lower)
            for match in matches:
                amount_str = match.group(1).replace(',', '')
                try:
                    amount = float(amount_str)
                    
                    # Convert based on suffix
                    if 'm' in match.group(0):
                        return int(amount * 1_000_000)
                    elif 'k' in match.group(0):
                        return int(amount * 1_000)
                    elif 'b' in match.group(0):
                        return int(amount * 1_000_000_000)
                    else:
                        return int(amount)
                except ValueError:
                    continue
        
        # Default fallback amounts based on query content
        if any(term in query_lower for term in ['beginner', 'starting', 'new', 'small']):
            return 10_000
        elif any(term in query_lower for term in ['medium', 'intermediate', 'decent']):
            return 100_000
        elif any(term in query_lower for term in ['large', 'big', 'serious', 'whale']):
            return 1_000_000
            
        return 0

    def classify_enhanced_query(self, query: str) -> Tuple[str, List[str], int]:
        """
        Enhanced query classification with capital extraction.
        
        Returns:
            - Primary query type
            - Entity list (extracted items/terms)
            - Capital amount in GP
        """
        query_lower = query.lower().strip()
        capital_amount = self.extract_capital_amount(query)
        
        # Score each pattern category
        classification_scores = {}
        
        for category, patterns in self.patterns.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, query_lower, re.IGNORECASE):
                    score += 1
            
            if score > 0:
                classification_scores[category] = score
        
        # Get highest scoring category
        if classification_scores:
            primary_category = max(classification_scores.items(), key=lambda x: x[1])[0]
        else:
            primary_category = 'opportunity_search'  # Default fallback
        
        # Extract entities (item names, terms)
        entities = self._extract_entities(query)
        
        return primary_category, entities, capital_amount

    def _extract_entities(self, query: str) -> List[str]:
        """Extract item names and trading terms from query."""
        entities = []
        
        # Extract quoted terms
        quoted_terms = re.findall(r'"([^"]+)"', query)
        entities.extend(quoted_terms)
        
        # Extract capitalized terms (likely item names)
        capitalized = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', query)
        entities.extend(capitalized)
        
        # Extract common OSRS item patterns
        osrs_patterns = [
            r'\b(rune|dragon|adamant|mithril|steel|iron|bronze)\s+(sword|scimitar|dagger|axe|mace|arrow)\b',
            r'\b(nature|law|death|blood|chaos|cosmic|fire|water|earth|air)\s+runes?\b',
            r'\b(prayer|combat|super|antifire|strength|attack|defence)\s+potions?\b',
            r'\b(logs?|ore|bars?|gems?|hides?)\b',
        ]
        
        for pattern in osrs_patterns:
            matches = re.findall(pattern, query.lower())
            for match in matches:
                if isinstance(match, tuple):
                    entities.append(' '.join(match))
                else:
                    entities.append(match)
        
        return list(set(entities))  # Remove duplicates

    def get_capital_tier(self, capital: int) -> str:
        """Get capital tier classification."""
        if capital >= 10_000_000:  # 10m+
            return 'whale'
        elif capital >= 1_000_000:  # 1m-10m
            return 'high'
        elif capital >= 100_000:   # 100k-1m
            return 'medium'
        elif capital >= 10_000:    # 10k-100k
            return 'small'
        else:
            return 'micro'

    def get_suggested_strategies(self, category: str, capital: int) -> List[str]:
        """Get strategy suggestions based on query category and capital."""
        capital_tier = self.get_capital_tier(capital)
        
        strategy_map = {
            'capital_10k_strategy': {
                'small': ['consumable_flipping', 'resource_trading', 'high_frequency_small_margins'],
                'medium': ['skill_supplies', 'combat_consumables', 'bulk_trading'],
                'high': ['equipment_flipping', 'rare_item_speculation', 'market_timing'],
                'whale': ['market_manipulation', 'large_volume_trading', 'rare_collections']
            },
            'million_margin_flips': {
                'high': ['boss_drop_trading', 'rare_equipment_flips', 'seasonal_speculation'],
                'whale': ['discontinued_items', 'market_cornering', 'whale_trading']
            },
            'magic_items_trading': {
                'small': ['rune_trading', 'battlestaff_flipping', 'magic_supplies'],
                'medium': ['magic_equipment', 'spell_components', 'runecrafting_materials'],
                'high': ['high_level_magic_gear', 'rare_magic_items'],
                'whale': ['discontinued_magic_items', 'collector_magic_gear']
            }
        }
        
        return strategy_map.get(category, {}).get(capital_tier, ['general_trading'])

# Instance for use in merchant AI agent
enhanced_patterns = EnhancedQueryPatterns()