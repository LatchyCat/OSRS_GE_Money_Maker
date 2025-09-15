// Trading Strategies Types
// Based on backend models and serializers

export type StrategyType = 'decanting' | 'flipping' | 'crafting' | 'set_combining';
export type RiskLevel = 'low' | 'medium' | 'high';
export type MarketCondition = 'stable' | 'volatile' | 'bullish' | 'bearish' | 'crashing' | 'recovering';
export type CrashRiskLevel = 'low' | 'medium' | 'high' | 'critical';

// Core Trading Strategy Interface
export interface TradingStrategy {
  id: number;
  strategy_type: StrategyType;
  strategy_type_display: string;
  name: string;
  description: string;
  potential_profit_gp: number;
  profit_margin_pct: number;
  risk_level: RiskLevel;
  risk_level_display: string;
  min_capital_required: number;
  recommended_capital: number;
  optimal_market_condition: MarketCondition;
  optimal_market_condition_display: string;
  estimated_time_minutes: number;
  max_volume_per_day: number | null;
  confidence_score: number;
  is_active: boolean;
  last_updated: string;
  created_at: string;
  strategy_data: Record<string, any>;
  hourly_profit_potential: number;
  roi_percentage: number;
}

// Decanting Opportunity
export interface DecantingOpportunity {
  id: number;
  strategy: TradingStrategy;
  item_id: number;
  item_name: string;
  from_dose: number;
  to_dose: number;
  from_dose_price: number;
  to_dose_price: number;
  from_dose_volume: number;
  to_dose_volume: number;
  profit_per_conversion: number;
  profit_per_hour: number;
  
  // Volume analysis fields
  trading_activity: 'very_active' | 'active' | 'moderate' | 'low' | 'inactive' | 'unknown';
  trading_activity_display: string;
  liquidity_score: number;
  confidence_score: number;
  volume_analysis_data?: {
    total_volume: number;
    avg_volume_per_hour: number;
    volume_trend: string;
    trading_activity: string;
    liquidity_score: number;
    price_stability: number;
    active_trading_periods: number;
    total_periods_analyzed: number;
    timestep: string;
  };
  volume_analysis_summary?: {
    avg_volume_per_hour: number;
    volume_trend: string;
    price_stability: number;
    liquidity_indicator: {
      level: 'high' | 'medium' | 'low';
      color: 'green' | 'yellow' | 'red';
      icon: string;
    };
    volume_description: string;
  };
  risk_assessment?: {
    risk_level: 'low' | 'medium' | 'high';
    risk_color: 'green' | 'yellow' | 'red';
    risk_description: string;
    confidence_score: number;
    recommendation: string;
  };

  // AI-enhanced fields
  ai_confidence?: number;
  ai_risk_level?: string;
  ai_timing?: string;
  ai_success_probability?: number;
  ai_recommendations?: string[];
  model_agreement?: number;
  execution_strategy?: string;
  estimated_time_per_conversion?: number;
  max_hourly_conversions?: number;
  capital_requirement?: number;
  price_spread?: number;
  data_freshness?: string;
  liquidity_score?: number;
  uncertainty_factors?: string[];
  similar_opportunities?: number[];
}

// Set Combining Opportunity  
export interface SetCombiningOpportunity {
  id: number;
  strategy: TradingStrategy;
  set_name: string;
  set_item_id: number;
  piece_ids: number[];
  piece_names: string[];
  piece_prices: number[]; // Individual piece prices
  individual_pieces_total_cost: number;
  complete_set_price: number;
  lazy_tax_profit: number;
  piece_volumes: { [key: string]: number } | number[]; // Support both object and array formats
  set_volume: number;
  profit_margin_pct: number;
  
  // AI-enhanced fields
  volume_score: number;
  confidence_score: number;
  ai_risk_level: RiskLevel;
  estimated_sets_per_hour: number;
  avg_data_age_hours: number;
  pieces_data: Array<{
    item_id: number;
    name: string;
    buy_price: number;
    sell_price: number;
    age_hours: number;
    volume_score?: number;
  }>;
  ge_tax: number;
  required_capital: number;
  strategy_type: string;
  strategy_description: string;
  
  // AI insights
  ai_timing_recommendation?: string;
  ai_market_sentiment?: string;
  model_consensus_score?: number;
  liquidity_rating?: string;
}

// Flipping Opportunity
export interface FlippingOpportunity {
  id: number;
  strategy: TradingStrategy;
  item_id: number;
  item_name: string;
  buy_price: number;
  sell_price: number;
  margin: number;
  margin_percentage: number | string;
  buy_volume: number;
  sell_volume: number;
  price_stability: number | string;
  estimated_flip_time_minutes: number;
  recommended_quantity: number;
  total_profit_potential: number;
}

// Crafting Opportunity
export interface CraftingOpportunity {
  id: number;
  strategy: TradingStrategy;
  product_id: number;
  product_name: string;
  product_price: number;
  materials_cost: number;
  materials_data: Record<string, any>;
  required_skill_level: number;
  skill_name: string;
  profit_per_craft: number;
  profit_margin_pct: number;
  crafting_time_seconds: number;
  max_crafts_per_hour: number;
  profit_per_hour: number;
}

// Market Condition Snapshot
export interface MarketConditionSnapshot {
  id: number;
  timestamp: string;
  market_condition: MarketCondition;
  market_condition_display: string;
  total_volume_24h: number;
  average_price_change_pct: number;
  volatility_score: number;
  bot_activity_score: number;
  crash_risk_level: CrashRiskLevel;
  crash_risk_level_display: string;
  market_data: {
    items_analyzed: number;
    volume_spikes_detected: number;
    price_crashes_detected: number;
    high_volatility_items: number;
  };
}

// Strategy Performance 
export interface StrategyPerformance {
  id: number;
  strategy: TradingStrategy;
  timestamp: string;
  actual_profit_gp: number;
  expected_profit_gp: number;
  accuracy_score: number;
  capital_used: number;
  execution_time_minutes: number;
  successful_trades: number;
  failed_trades: number;
  success_rate: number;
  profit_vs_expected: number;
}

// API Response Types
export interface TradingStrategiesResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: TradingStrategy[];
}

export interface DecantingOpportunitiesResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: DecantingOpportunity[];
}

export interface FlippingOpportunitiesResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: FlippingOpportunity[];
}

export interface CraftingOpportunitiesResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: CraftingOpportunity[];
}

export interface SetCombiningOpportunitiesResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: SetCombiningOpportunity[];
}

// Filters and Search
export interface TradingStrategyFilters {
  strategy_type?: StrategyType;
  risk_level?: RiskLevel;
  min_profit?: number;
  max_profit?: number;
  min_capital?: number;
  max_capital?: number;
  is_active?: boolean;
  search?: string;
  ordering?: string;
  page?: number;
  page_size?: number;
}

// Union type for all opportunity types
export type TradingOpportunity = 
  | DecantingOpportunity
  | FlippingOpportunity
  | CraftingOpportunity
  | SetCombiningOpportunity;

// Strategy Summary for Dashboard
export interface StrategyDashboardData {
  total_strategies: number;
  active_strategies: number;
  total_profit_potential: number;
  average_roi: number;
  market_condition: MarketConditionSnapshot;
  top_opportunities: TradingOpportunity[];
  performance_summary: {
    successful_executions: number;
    total_profit_made: number;
    average_success_rate: number;
  };
}