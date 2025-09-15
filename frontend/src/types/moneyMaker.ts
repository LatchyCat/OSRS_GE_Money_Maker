// Money Maker Types
// Comprehensive TypeScript definitions for money making strategies and opportunities

export interface MoneyMakerStrategy {
  id: number;
  starting_capital: number;
  current_capital: number;
  target_capital: number;
  hourly_profit_gp: number;
  hourly_profit_updated: string;
  optimal_trading_hours: number[];
  update_frequency_minutes: number;
  scales_with_capital: boolean;
  capital_efficiency_multiplier: string; // Decimal
  max_capital_per_trade: number;
  stop_loss_percentage?: string; // Decimal
  success_rate_percentage: string; // Decimal
  total_trades_executed: number;
  total_profit_realized: number;
  exploits_lazy_tax: boolean;
  lazy_tax_premium_pct?: string; // Decimal
  
  // Related strategy data
  strategy: {
    id: number;
    name: string;
    description: string;
    strategy_type: StrategyType;
    risk_level: RiskLevel;
    potential_profit_gp: number;
    profit_margin_pct: string; // Decimal
    min_capital_required: number;
    confidence_score: string; // Decimal
    is_active: boolean;
  };

  // Serialized calculated fields
  capital_growth_rate: number;
  estimated_time_to_target?: number;
  profit_efficiency_score: number;
  lazy_tax_exploitation: {
    exploits_lazy_tax: boolean;
    premium_percentage?: number;
    description?: string;
  };
  ge_tax_impact_analysis: {
    estimated_ge_tax_per_trade: number;
    hourly_ge_tax_cost: number;
    tax_efficiency_rating: 'high' | 'medium' | 'low';
  };
}

export interface BondFlippingStrategy {
  id: number;
  money_maker: MoneyMakerStrategy;
  target_item_ids: number[];
  target_item_data: Record<string, {
    name: string;
    buy_price: number;
    sell_price: number;
    margin: number;
    margin_pct: number;
    volume: number;
  }>;
  bond_price_gp: number;
  bond_to_gp_rate: string; // Decimal
  min_margin_percentage: string; // Decimal
  max_hold_time_hours: number;
  price_check_frequency_minutes: number;
  last_opportunity_scan?: string;

  // Serialized analysis fields
  bond_arbitrage_analysis: {
    current_bond_price_gp: number;
    gp_from_direct_purchase: number;
    arbitrage_profit_per_bond: number;
    is_arbitrage_profitable: boolean;
    profit_percentage: number;
  };
  tax_exemption_value: {
    bond_price: number;
    ge_tax_saved_per_trade: number;
    exemption_value_percentage: number;
    total_exemption_description: string;
  };
}

export interface AdvancedDecantingStrategy {
  id: number;
  money_maker: MoneyMakerStrategy;
  target_potions: Record<string, {
    doses: number[];
    base_name: string;
  }>;
  potion_profits: Record<string, any>;
  min_profit_per_dose_gp: number;
  optimal_dose_combinations: Array<{
    from_dose: number;
    to_dose: number;
    profit: number;
    potion_type?: string;
  }>;
  daily_volume_targets: Record<string, number>;
  market_liquidity_scores: Record<string, number>;
  barbarian_herblore_required: boolean;
  decanting_speed_per_hour: number;
  total_potions_decanted: number;
  total_decanting_profit: number;

  // Serialized analysis fields
  profit_analysis: {
    hourly_potion_capacity: number;
    minimum_profit_per_dose: number;
    average_profit_per_potion: number;
    hourly_profit_potential: number;
    total_realized_profit: number;
    efficiency_rating: 'high' | 'medium' | 'low';
  };
  optimal_potions: Array<{
    from_dose: number;
    to_dose: number;
    profit_per_conversion: number;
    conversion_ratio: string;
    hourly_profit_potential: number;
    efficiency_score: number;
  }>;
}

export interface EnhancedSetCombiningStrategy {
  id: number;
  money_maker: MoneyMakerStrategy;
  target_sets: Record<string, {
    pieces: number[];
    set_name: string;
  }>;
  set_opportunities: Record<string, {
    name: string;
    pieces_cost: number;
    set_price: number;
    profit: number;
    lazy_tax_pct: number;
  }>;
  average_lazy_tax_percentage: string; // Decimal
  high_lazy_tax_sets: string[];
  optimal_buying_times: string[];
  optimal_selling_times: string[];
  max_sets_held_simultaneously: number;
  piece_acquisition_timeout_hours: number;
  set_competition_levels: Record<string, 'low' | 'medium' | 'high'>;
  recommended_daily_sets: Record<string, number>;
  total_sets_completed: number;
  total_set_profit: number;
  incomplete_sets_value: number;

  // Serialized analysis fields
  lazy_tax_analysis: {
    average_lazy_tax_percentage: number;
    total_sets_completed: number;
    total_lazy_tax_profit: number;
    average_profit_per_set: number;
    lazy_tax_explanation: string;
    exploitation_rating: 'high' | 'medium' | 'low';
  };
  top_sets: Array<{
    set_id: string;
    set_name: string;
    pieces_cost: number;
    complete_set_price: number;
    lazy_tax_profit: number;
    lazy_tax_percentage: number;
    competition_level: 'low' | 'medium' | 'high';
    recommended_daily_volume: number;
  }>;
}

export interface RuneMagicStrategy {
  id: number;
  money_maker: MoneyMakerStrategy;
  target_runes: Array<{
    type: string;
    profit: number;
    level: number;
  }>;
  magic_supplies: Array<{
    type: string;
    name: string;
    buy_price: number;
    sell_price: number;
    profit: number;
    margin_pct: number;
    usage: string;
  }>;
  runecrafting_level_required: number;
  runes_per_hour: number;
  essence_costs: Record<string, number>;
  magic_training_items: any[];
  high_alch_opportunities: Array<{
    item_id: number;
    item_name: string;
    buy_price: number;
    alch_value: number;
    profit: number;
    nature_rune_cost?: number;
  }>;

  // Serialized analysis fields
  runecrafting_analysis: {
    minimum_level_required: number;
    runes_craftable_per_hour: number;
    profitable_runes: Array<{
      rune_type: string;
      profit_per_rune: number;
      hourly_profit: number;
      level_required: number;
    }>;
    essence_costs: Record<string, number>;
  };
  high_alchemy_opportunities: Array<{
    item_id: number;
    item_name: string;
    buy_price: number;
    alch_value: number;
    profit_per_alch: number;
    hourly_profit_potential: number;
    magic_level_required: number;
  }>;
}

export interface MoneyMakerOpportunity {
  item_id: number;
  item_name: string;
  strategy_type: StrategyType;
  buy_price: number;
  sell_price: number;
  profit_per_item: number;
  profit_margin_pct: number;
  confidence_score: number;
  estimated_daily_volume: number;
  ge_tax_cost: number;
  ge_tax_exemption_value?: number;
  max_trades_with_capital: number;

  // Strategy-specific fields
  from_dose?: number;
  to_dose?: number;
  lazy_tax_premium?: number;
  tax_exempt?: boolean;
}

export interface CapitalTier {
  count: number;
  avg_hourly_profit: number;
  strategies: MoneyMakerStrategy[];
}

export interface CapitalProgressionAdvice {
  current_tier: string;
  target_tier: string;
  recommended_strategies: Array<{
    name: string;
    type: StrategyType;
    why_recommended: string;
    expected_hourly_profit: number;
    risk_level: RiskLevel;
    capital_required: number;
    success_probability: number;
  }>;
  progression_timeline: {
    estimated_hours_to_target: number;
    milestones: Array<{
      capital_amount: number;
      estimated_time_hours: number;
      key_strategies: string[];
    }>;
  };
  risk_assessment: {
    overall_risk: RiskLevel;
    risk_factors: string[];
    mitigation_strategies: string[];
  };
  market_considerations: {
    current_market_condition: string;
    recommendation: string;
    optimal_trading_hours: number[];
  };
}

export interface GETaxCalculation {
  sell_price: number;
  item_id?: number;
  ge_tax: number;
  net_received: number;
  effective_tax_percentage: number;
  is_tax_exempt: boolean;
  tax_rules: {
    base_rate: string;
    exemption_threshold: string;
    maximum_tax: string;
    exempt_items: string[];
  };
}

export interface MarketOverview {
  market_overview: {
    total_strategies: number;
    active_strategies: number;
    average_hourly_profit: number;
    total_realized_profit: number;
    activity_percentage: number;
  };
  strategy_distribution: {
    bond_flipping: number;
    advanced_decanting: number;
    enhanced_set_combining: number;
    rune_magic: number;
  };
  market_health: {
    status: 'healthy' | 'inactive' | 'volatile';
    recommendation: string;
  };
}

export interface ProfitProjection {
  time_horizon_hours: number;
  individual_projections: Array<{
    strategy_name: string;
    strategy_type: StrategyType;
    hourly_profit: number;
    projected_profit: number;
    success_adjusted_profit: number;
    success_rate: number;
    capital_required: number;
  }>;
  total_projected_profit: number;
  average_hourly_rate: number;
  projection_accuracy: string;
}

// Enums and constants
export type StrategyType = 
  | 'flipping'
  | 'decanting' 
  | 'set_combining'
  | 'crafting'
  | 'arbitrage'
  | 'high_alchemy'
  | 'bond_flipping'
  | 'rune_magic';

export type RiskLevel = 'low' | 'medium' | 'high' | 'extreme';

export const STRATEGY_TYPE_DISPLAY: Record<StrategyType, string> = {
  flipping: 'Flipping',
  decanting: 'Decanting',
  set_combining: 'Set Combining',
  crafting: 'Crafting',
  arbitrage: 'Arbitrage',
  high_alchemy: 'High Alchemy',
  bond_flipping: 'Bond Flipping',
  rune_magic: 'Rune & Magic'
};

export const RISK_LEVEL_COLORS: Record<RiskLevel, string> = {
  low: 'text-green-400',
  medium: 'text-yellow-400',
  high: 'text-orange-400',
  extreme: 'text-red-400'
};

export const CAPITAL_TIERS = [
  { min: 0, max: 10_000_000, name: 'starter', display: 'Starter (Under 10M)' },
  { min: 10_000_000, max: 50_000_000, name: 'intermediate', display: 'Intermediate (10M-50M)' },
  { min: 50_000_000, max: 100_000_000, name: 'advanced', display: 'Advanced (50M-100M)' },
  { min: 100_000_000, max: Infinity, name: 'expert', display: 'Expert (100M+)' }
];

// Utility functions
export const formatGP = (amount: number): string => {
  if (amount >= 1_000_000_000) {
    return `${(amount / 1_000_000_000).toFixed(1)}B GP`;
  } else if (amount >= 1_000_000) {
    return `${(amount / 1_000_000).toFixed(1)}M GP`;
  } else if (amount >= 1_000) {
    return `${(amount / 1_000).toFixed(0)}K GP`;
  }
  return `${amount.toLocaleString()} GP`;
};

export const getCapitalTier = (capital: number): string => {
  const tier = CAPITAL_TIERS.find(t => capital >= t.min && capital < t.max);
  return tier?.name || 'starter';
};

export const getStrategyTypeColor = (type: StrategyType): string => {
  const colors: Record<StrategyType, string> = {
    flipping: 'text-blue-400',
    decanting: 'text-green-400',
    set_combining: 'text-purple-400',
    crafting: 'text-orange-400',
    arbitrage: 'text-yellow-400',
    high_alchemy: 'text-red-400',
    bond_flipping: 'text-pink-400',
    rune_magic: 'text-indigo-400'
  };
  return colors[type] || 'text-gray-400';
};