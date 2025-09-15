// Centralized AI-related TypeScript interfaces
// This file contains all AI API related type definitions

export interface AIQueryRequest {
  query: string;
  capital?: number;
  strategy_type?: string;
}

export interface AIRecommendation {
  item_id: number;
  item_name: string;
  current_price: number;
  recommended_buy_price: number;
  recommended_sell_price: number;
  expected_profit_per_item: number;
  expected_profit_margin_pct: number;
  success_probability_pct: number;
  risk_level: string;
  estimated_hold_time_hours: number;
  buy_limit?: number;
  marketing_strategy?: string;
  market_catalysts?: string[];
  timing_insights?: string;
  competition_analysis?: string;
  freshness_status?: string;
  freshness_warnings?: string[];
  data_age_hours?: number;
}

export interface MarketSignal {
  signal_type: string;
  item_name: string;
  strength: string;
  reasoning: string;
  target_price?: number;
  change_pct?: number;
  data_age_hours?: number;
}

export interface AgentMetadata {
  query_complexity: string;
  agent_used: string;
  processing_time_ms: number;
  task_routing_reason: string;
  data_quality_score: number;
  confidence_level: number;
  system_load?: any;
}

export interface AIQueryResponse {
  success: boolean;
  response: string;
  precision_opportunities: AIRecommendation[];
  market_signals: MarketSignal[];
  risk_assessment?: any;
  portfolio_suggestions?: any[];
  agent_metadata?: AgentMetadata;
  timestamp?: string;
  ai_error?: string;
  fallback_response?: string;
}

export interface MultiAgentPerformanceData {
  success: boolean;
  timestamp: string;
  system_status: {
    system_healthy: boolean;
    agents_available: Record<string, boolean>;
    current_load: any;
  };
  performance_metrics: any;
  agent_capabilities: Record<string, {
    name: string;
    description: string;
    speed_multiplier: number;
    specialties: string[];
    complexity_rating: number;
    color: string;
  }>;
  routing_logic: any;
}