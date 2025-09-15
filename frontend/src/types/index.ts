// API Response Types
export interface PriceSourceMetadata {
  source: 'weird_gloop' | 'wiki_timeseries_5m' | 'wiki_timeseries_1h' | 'wiki_latest';
  quality: 'fresh' | 'recent' | 'acceptable' | 'stale' | 'unknown';
  confidence_score: number;
  age_hours: number;
  timestamp: number;
  volume_high: number;
  volume_low: number;
}

export interface ProfitCalculation {
  current_buy_price: number;
  current_sell_price: number;
  current_profit: number;
  current_profit_margin: number;
  daily_volume: number;
  hourly_volume: number;
  five_min_volume: number;
  price_trend: string;
  volume_category: string;
  price_volatility: number;
  price_momentum: number;
  recommendation_score: number;
  volume_weighted_score: number;
  // High Alchemy specific scoring
  high_alch_viability_score: number;
  alch_efficiency_rating: number;
  sustainable_alch_potential: number;
  magic_xp_efficiency: number;
  is_profitable: boolean;
  is_hot_item: boolean;
  volume_adjusted_profit: number;
  recommended_update_frequency_minutes: number;
  last_updated: string;
  // Multi-source price intelligence metadata
  price_source_metadata?: PriceSourceMetadata;
  // Backend multi-source fields (for backward compatibility)
  data_source?: string;
  data_quality?: string;
  confidence_score?: number;
  data_age_hours?: number;
  source_timestamp?: string;
}

export interface PriceSnapshot {
  id: number;
  high_price: number | null;
  high_time: string | null;
  low_price: number | null;
  low_time: string | null;
  high_price_volume: number | null;
  low_price_volume: number | null;
  total_volume: number | null;
  price_volatility: number | null;
  price_change_pct: number | null;
  data_interval: string;
  created_at: string;
  profit_if_buy_high: number;
  profit_margin_if_buy_high: number;
  is_high_volume: boolean;
  is_volatile: boolean;
  recommended_update_frequency_minutes: number;
}

export interface Item {
  item_id: number;
  name: string;
  examine: string;
  high_alch: number;
  members: boolean;
  limit: number;
  icon?: string;
  value?: number;
  low_alch?: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  base_profit_per_item: number;
  categories: any[];
  profit_calc?: ProfitCalculation;
  latest_price?: PriceSnapshot;
  price_history?: PriceSnapshot[];
  // Legacy properties for backward compatibility
  current_profit?: number;
  current_profit_margin?: number;
  current_buy_price?: number;
  recommendation_score?: number;
  volume_weighted_score?: number;
  volume_category?: string;
  daily_volume?: number;
  is_hot_item?: boolean;
  volume_adjusted_profit?: number;
  // Top-level multi-source fields from backend
  data_source?: string;
  data_quality?: string;
  confidence_score?: number;
  data_age_hours?: number;
}

export interface ItemSearchResult {
  count: number;
  next: string | null;
  previous: string | null;
  results: Item[];
}

export interface MarketAnalysis {
  total_profitable_items: number;
  average_profit_margin: number;
  highest_profit_item: string;
  highest_profit_amount: number;
  market_volatility_score: number;
  recommended_risk_level: string;
  data_freshness?: string;
  data_age_hours?: number;
  message?: string;
}

export interface GoalPlan {
  plan_id: string;
  session_key: string;
  current_gp: number;
  goal_gp: number;
  required_profit: number;
  preferred_timeframe_days?: number;
  risk_tolerance: string;
  is_active: boolean;
  is_achievable: boolean;
  created_at: string;
  updated_at: string;
  last_calculated: string;
  profit_needed: number;
  completion_percentage: number;
  strategies: Strategy[];
}

export interface Strategy {
  id: number;
  strategy_id: string;
  name: string;
  strategy_type: string;
  description?: string;
  estimated_days: number;
  estimated_profit: number;
  required_initial_investment: number;
  roi_percentage: number;
  risk_level: string;
  feasibility_score: number;
  is_recommended: boolean;
  is_active: boolean;
  items: StrategyItem[];
}

export interface StrategyItem {
  id: number;
  item_id: number;
  item?: Item;
  units_to_buy: number;
  buy_price: number;
  total_cost: number;
  total_profit: number;
  risk_score: number;
  priority: number;
}

export interface ProgressUpdate {
  id: number;
  current_gp_at_time: number;
  profit_made: number;
  remaining_profit_needed: number;
  completion_percentage: number;
  days_elapsed: number;
  market_notes?: string;
  is_on_track: boolean;
  needs_strategy_update: boolean;
  created_at: string;
}

export interface GoalPlanStats {
  total_plans: number;
  active_plans: number;
  completed_goals: number;
  average_completion_rate: number;
}

// Form Types
export interface CreateGoalPlanRequest {
  current_gp: number;
  goal_gp: number;
  risk_tolerance: 'conservative' | 'moderate' | 'aggressive';
}

export interface UpdateProgressRequest {
  current_gp: number;
  market_notes?: string;
}

export interface ItemFilters {
  search?: string;
  members?: boolean;
  min_profit?: number;
  max_profit?: number;
  min_margin?: number;
  max_margin?: number;
  ordering?: string;
  page?: number;
  page_size?: number;
}

// UI Types
export type RiskLevel = 'conservative' | 'moderate' | 'aggressive';
export type SortOption = 'profit' | 'margin' | 'name' | 'recommendation';
export type ViewMode = 'grid' | 'list' | 'table';