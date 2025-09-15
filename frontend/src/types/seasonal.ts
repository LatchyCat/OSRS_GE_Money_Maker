/**
 * TypeScript interfaces for seasonal pattern analysis data.
 * These interfaces match the Django REST Framework serializers.
 */

export interface ItemBasic {
  item_id: number;
  name: string;
  current_price: number;
  profit_margin: number;
}

export interface SeasonalPattern {
  id: number;
  item: ItemBasic;
  analysis_timestamp: string;
  lookback_days: number;
  data_points_analyzed: number;
  analysis_types: string[];
  
  // Pattern Strengths (0-1 scale)
  weekly_pattern_strength: number;
  monthly_pattern_strength: number;
  yearly_pattern_strength: number;
  event_pattern_strength: number;
  overall_pattern_strength: number;
  
  // Weekly Patterns
  weekend_effect_pct: number;
  best_day_of_week: string;
  worst_day_of_week: string;
  day_of_week_effects: Record<string, any>;
  
  // Monthly & Seasonal Patterns
  best_month: string;
  worst_month: string;
  monthly_effects: Record<string, any>;
  quarterly_effects: Record<string, any>;
  
  // Events & Forecasting
  detected_events: any[];
  event_impact_analysis: Record<string, any>;
  short_term_forecast: Record<string, any>;
  medium_term_forecast: Record<string, any>;
  forecast_confidence: number;
  
  // Recommendations
  recommendations: string[];
  confidence_score: number;
  analysis_duration_seconds: number;
  
  // Computed Properties
  has_strong_patterns: boolean;
  dominant_pattern_type: 'weekly' | 'monthly' | 'yearly' | 'event';
  has_significant_weekend_effect: boolean;
  signal_quality: 'excellent' | 'good' | 'fair' | 'poor';
  is_high_conviction: boolean;
}

export interface SeasonalForecast {
  id: number;
  seasonal_pattern: number;
  item_name: string;
  forecast_timestamp: string;
  horizon: '1d' | '3d' | '7d' | '14d' | '30d' | '60d' | '90d';
  target_date: string;
  
  // Forecast Values
  forecasted_price: number;
  confidence_level: number;
  lower_bound: number;
  upper_bound: number;
  
  // Forecast Components
  base_price: number;
  seasonal_factor: number;
  trend_adjustment: number;
  primary_pattern_type: string;
  pattern_strength: number;
  forecast_method: string;
  
  // Validation Data
  actual_price?: number;
  forecast_error?: number;
  is_within_confidence_interval?: boolean;
  validation_date?: string;
  absolute_error?: number;
  percentage_error?: number;
  
  // Computed Properties
  is_validated: boolean;
  days_until_target: number | null;
  forecast_accuracy: number | null;
}

export interface SeasonalEvent {
  id: number;
  event_name: string;
  event_type: 'osrs_official' | 'community' | 'detected_anomaly' | 'holiday' | 'update' | 'seasonal';
  description: string;
  start_date?: string;
  end_date?: string;
  duration_days: number;
  
  // Recurrence
  is_recurring: boolean;
  recurrence_pattern: '' | 'weekly' | 'monthly' | 'quarterly' | 'yearly';
  
  // Impact Analysis
  average_price_impact_pct: number;
  average_volume_impact_pct: number;
  impact_confidence: number;
  affected_categories: string[];
  historical_occurrences: any[];
  
  // Metadata
  verification_status: 'unverified' | 'verified' | 'disputed';
  detection_method: string;
  detection_timestamp: string;
  last_updated: string;
  is_active: boolean;
  
  // Computed Properties
  is_upcoming: boolean;
  is_current: boolean;
  has_significant_impact: boolean;
  days_until_start: number | null;
}

export interface SeasonalRecommendation {
  id: number;
  seasonal_pattern: number;
  item_name: string;
  recommendation_timestamp: string;
  recommendation_type: 'buy' | 'sell' | 'hold' | 'avoid' | 'monitor';
  
  // Timing & Validity
  target_date?: string;
  valid_from: string;
  valid_until: string;
  
  // Recommendation Details
  primary_pattern: string;
  confidence_score: number;
  expected_impact_pct: number;
  suggested_position_size_pct: number;
  stop_loss_pct?: number;
  take_profit_pct?: number;
  max_hold_days: number;
  
  // Reasoning
  recommendation_text: string;
  supporting_factors: string[];
  
  // Execution Status
  is_active: boolean;
  is_executed: boolean;
  execution_timestamp?: string;
  execution_price?: number;
  final_performance_pct?: number;
  
  // Computed Properties
  is_current: boolean;
  days_remaining: number;
  is_high_confidence: boolean;
  current_performance_pct: number;
  max_performance_pct: number;
  min_performance_pct: number;
}

export interface TechnicalAnalysis {
  id: number;
  item: ItemBasic;
  analysis_timestamp: string;
  timeframes_analyzed: string[];
  lookback_days: number;
  data_points_used: number;
  
  // Analysis Results
  overall_recommendation: 'strong_buy' | 'buy' | 'weak_buy' | 'neutral' | 'weak_sell' | 'sell' | 'strong_sell';
  strength_score: number;
  consensus_signal: string;
  timeframe_agreement: number;
  dominant_timeframes: string[];
  conflicting_signals: boolean;
  confidence_score: number;
  analysis_duration_seconds: number;
  
  // Computed Properties
  signal_quality: 'excellent' | 'good' | 'fair' | 'poor';
  is_high_conviction: boolean;
}

export interface MarketMomentum {
  id: number;
  item: ItemBasic;
  momentum_score: number;
  trend_direction: 'uptrend' | 'downtrend' | 'sideways';
  price_velocity: number;
  price_acceleration: number;
  volatility: number;
  support_level: number;
  resistance_level: number;
  breakout_probability: number;
  last_updated: string;
}

export interface SentimentAnalysis {
  id: number;
  source: string;
  analysis_timestamp: string;
  overall_sentiment: 'positive' | 'negative' | 'neutral';
  sentiment_score: number;
  confidence: number;
  analyzed_articles: number;
  key_themes: string[];
  sentiment_breakdown: Record<string, any>;
  market_impact_predictions: Record<string, any>;
  category_sentiment: Record<string, any>;
  top_mentioned_items: string[];
  analysis_duration_seconds: number;
  data_quality_score: number;
  sentiment_strength: 'strong' | 'moderate' | 'weak';
}

export interface PricePrediction {
  id: number;
  item: ItemBasic;
  prediction_timestamp: string;
  current_price: number;
  
  // Predictions
  predicted_price_1h: number;
  predicted_price_4h: number;
  predicted_price_24h: number;
  confidence_1h: number;
  confidence_4h: number;
  confidence_24h: number;
  
  // Analysis
  trend_direction: 'uptrend' | 'downtrend' | 'sideways';
  prediction_factors: Record<string, any>;
  model_version: string;
  prediction_method: string;
  
  // Validation
  actual_price_1h?: number;
  actual_price_4h?: number;
  actual_price_24h?: number;
  error_1h?: number;
  error_4h?: number;
  error_24h?: number;
  
  // Computed Properties
  is_high_confidence: boolean;
  predicted_change_24h_pct: number;
}

// API Response Types
export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface MarketOverview {
  total_items_analyzed: number;
  strong_patterns_count: number;
  active_recommendations: number;
  upcoming_events: number;
  forecast_accuracy: number;
  market_sentiment: string;
  last_updated: string;
  recent_analyses?: number;
}

export interface SeasonalAnalytics {
  top_patterns: SeasonalPattern[];
  upcoming_forecasts: SeasonalForecast[];
  active_recommendations: SeasonalRecommendation[];
  upcoming_events: SeasonalEvent[];
  generated_at: string;
}

export interface ForecastAccuracyStats {
  total_validated_forecasts: number;
  overall_ci_hit_rate: number;
  accuracy_by_horizon: Record<string, {
    average_accuracy: number;
    forecast_count: number;
    ci_hit_rate: number;
  }>;
  period_days: number;
  generated_at: string;
}

// Filter and Query Types
export interface SeasonalPatternFilters {
  item_id?: number;
  min_strength?: number;
  pattern_type?: 'weekly' | 'monthly' | 'yearly' | 'event';
  days_back?: number;
  ordering?: string;
  page?: number;
  page_size?: number;
}

export interface SeasonalForecastFilters {
  item_id?: number;
  horizon?: string;
  validated?: boolean;
  upcoming?: boolean;
  min_confidence?: number;
  ordering?: string;
  page?: number;
  page_size?: number;
}

export interface SeasonalEventFilters {
  event_type?: string;
  upcoming?: boolean;
  active?: boolean;
  verified?: boolean;
  significant_impact?: boolean;
  ordering?: string;
  page?: number;
  page_size?: number;
}

export interface SeasonalRecommendationFilters {
  item_id?: number;
  recommendation_type?: 'buy' | 'sell' | 'hold' | 'avoid' | 'monitor';
  active?: boolean;
  executed?: boolean;
  current?: boolean;
  min_confidence?: number;
  ordering?: string;
  page?: number;
  page_size?: number;
}