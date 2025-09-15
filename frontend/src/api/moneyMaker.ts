// Money Maker API Client
// Comprehensive API client for money making strategies and opportunities

import React from 'react';
import axios from 'axios';
import * as MoneyMakerTypes from '../types/moneyMaker';

// API Configuration
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
const MONEY_MAKER_BASE = `${API_BASE_URL}/v1/trading`;

// Create axios instance with default config
const apiClient = axios.create({
  baseURL: MONEY_MAKER_BASE,
  timeout: 30000, // 30 second timeout for async operations
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request/Response interfaces
interface PaginatedResponse<T> {
  count: number;
  next?: string;
  previous?: string;
  results: T[];
}

interface APIError {
  error: string;
  details?: any;
}

// Money Maker Strategy API
export const moneyMakerApi = {
  // Core Money Maker Strategies
  async getStrategies(params?: {
    min_capital?: number;
    max_capital?: number;
    min_hourly_profit?: number;
    min_success_rate?: number;
    ordering?: string;
    limit?: number;
    offset?: number;
  }): Promise<PaginatedResponse<MoneyMakerTypes.MoneyMakerStrategy>> {
    const response = await apiClient.get<PaginatedResponse<MoneyMakerTypes.MoneyMakerStrategy>>(
      '/money-makers/',
      { params }
    );
    return response.data;
  },

  async getStrategy(id: number): Promise<MoneyMakerTypes.MoneyMakerStrategy> {
    const response = await apiClient.get<MoneyMakerTypes.MoneyMakerStrategy>(`/money-makers/${id}/`);
    return response.data;
  },

  async createStrategy(data: Partial<MoneyMakerTypes.MoneyMakerStrategy>): Promise<MoneyMakerTypes.MoneyMakerStrategy> {
    const response = await apiClient.post<MoneyMakerTypes.MoneyMakerStrategy>('/money-makers/', data);
    return response.data;
  },

  async updateStrategy(id: number, data: Partial<MoneyMakerTypes.MoneyMakerStrategy>): Promise<MoneyMakerTypes.MoneyMakerStrategy> {
    const response = await apiClient.patch<MoneyMakerTypes.MoneyMakerStrategy>(`/money-makers/${id}/`, data);
    return response.data;
  },

  async deleteStrategy(id: number): Promise<void> {
    await apiClient.delete(`/money-makers/${id}/`);
  },

  // Capital Progression Analysis
  async getProgressionTiers(): Promise<Record<string, MoneyMakerTypes.CapitalTier>> {
    const response = await apiClient.get<Record<string, MoneyMakerTypes.CapitalTier>>(
      '/money-makers/progression_tiers/'
    );
    return response.data;
  },

  async getTopPerformers(limit: number = 5): Promise<{
    highest_hourly_profit: MoneyMakerTypes.MoneyMakerStrategy[];
    best_success_rate: MoneyMakerTypes.MoneyMakerStrategy[];
    most_capital_efficient: MoneyMakerTypes.MoneyMakerStrategy[];
    best_lazy_tax_exploiters: MoneyMakerTypes.MoneyMakerStrategy[];
  }> {
    const response = await apiClient.get('/money-makers/top_performers/', {
      params: { limit }
    });
    return response.data;
  },

  async getCapitalScalingAnalysis(capital: number): Promise<{
    capital_analyzed: number;
    scalable_strategies: Array<{
      strategy: string;
      base_hourly_profit: number;
      projected_hourly_profit: number;
      capital_efficiency: number;
      scaling_factor: number;
    }>;
    non_scalable_count: number;
    total_projected_hourly: number;
  }> {
    const response = await apiClient.get('/money-makers/capital_scaling_analysis/', {
      params: { capital }
    });
    return response.data;
  },

  // Bond Flipping Strategy API
  async getBondFlippingStrategies(params?: {
    min_margin_percentage?: number;
    max_hold_time_hours?: number;
  }): Promise<PaginatedResponse<MoneyMakerTypes.BondFlippingStrategy>> {
    const response = await apiClient.get('/bond-flipping/', { params });
    return response.data;
  },

  async getBondFlippingStrategy(id: number): Promise<MoneyMakerTypes.BondFlippingStrategy> {
    const response = await apiClient.get(`/bond-flipping/${id}/`);
    return response.data;
  },

  async getCurrentBondOpportunities(capital: number = 50_000_000): Promise<{
    opportunities: Array<{
      item_id: number;
      item_name: string;
      buy_price: number;
      sell_price: number;
      profit_per_item: number;
      profit_margin_pct: number;
      ge_tax_saved: number;
      confidence_score: number;
      estimated_volume: number;
      max_trades_with_capital: number;
    }>;
    total_opportunities: number;
    capital_analyzed: number;
    tax_exemption_benefit: boolean;
  }> {
    const response = await apiClient.get('/bond-flipping/current_opportunities/', {
      params: { capital }
    });
    return response.data;
  },

  async getBondPriceAnalysis(): Promise<{
    current_bond_price_gp: number;
    bond_cost_usd: number;
    gp_per_dollar: number;
    gp_per_bond_bought: number;
    arbitrage_profit_per_bond: number;
    is_profitable: boolean;
    ge_tax_exemption: string;
    recommendation: string;
  }> {
    const response = await apiClient.get('/bond-flipping/bond_price_analysis/');
    return response.data;
  },

  // Advanced Decanting Strategy API
  async getDecantingStrategies(params?: {
    barbarian_herblore_required?: boolean;
    min_profit_per_dose_gp?: number;
  }): Promise<PaginatedResponse<MoneyMakerTypes.AdvancedDecantingStrategy>> {
    const response = await apiClient.get('/advanced-decanting/', { params });
    return response.data;
  },

  async getProfitablePotions(capital: number = 50_000_000, minProfitPerDose: number = 100): Promise<{
    profitable_potions: Array<{
      item_id: number;
      potion_name: string;
      from_dose: number;
      to_dose: number;
      profit_per_conversion: number;
      hourly_profit_potential: number;
      ge_tax_impact: number;
      market_liquidity: number;
      confidence_score: number;
    }>;
    total_found: number;
    capital_analyzed: number;
    min_profit_filter: number;
    barbarian_herblore_note: string;
  }> {
    const response = await apiClient.get('/advanced-decanting/profitable_potions/', {
      params: { capital, min_profit_per_dose: minProfitPerDose }
    });
    return response.data;
  },

  async getDoseCombinationAnalysis(): Promise<{
    dose_combinations: Array<{
      strategy_id: number;
      from_dose: number;
      to_dose: number;
      profit_per_conversion: number;
      potion_type: string;
      estimated_hourly: number;
    }>;
    total_combinations: number;
    recommendation: string;
  }> {
    const response = await apiClient.get('/advanced-decanting/dose_combination_analysis/');
    return response.data;
  },

  // Enhanced Set Combining Strategy API
  async getSetCombiningStrategies(params?: {
    max_sets_held_simultaneously?: number;
    piece_acquisition_timeout_hours?: number;
  }): Promise<PaginatedResponse<MoneyMakerTypes.EnhancedSetCombiningStrategy>> {
    const response = await apiClient.get('/enhanced-set-combining/', { params });
    return response.data;
  },

  async getLazyTaxOpportunities(capital: number = 50_000_000): Promise<{
    set_opportunities: Array<{
      set_name: string;
      set_item_id: number;
      pieces_total_cost: number;
      complete_set_price: number;
      lazy_tax_profit: number;
      lazy_tax_premium_pct: number;
      ge_tax_cost: number;
      net_profit_after_tax: number;
      confidence_score: number;
      estimated_completion_time: string;
      capital_efficiency: number;
    }>;
    total_sets_found: number;
    capital_analyzed: number;
    lazy_tax_explanation: string;
    recommendation: string;
  }> {
    const response = await apiClient.get('/enhanced-set-combining/lazy_tax_opportunities/', {
      params: { capital }
    });
    return response.data;
  },

  async getSetCompetitionAnalysis(): Promise<{
    competition_analysis: Record<'low' | 'medium' | 'high', Array<{
      set_id: string;
      competition_level: string;
      recommended_daily_sets: number;
      average_lazy_tax: number;
    }>>;
    recommendation: Record<'low' | 'medium' | 'high', string>;
  }> {
    const response = await apiClient.get('/enhanced-set-combining/set_competition_analysis/');
    return response.data;
  },

  // Rune & Magic Strategy API
  async getRuneMagicStrategies(params?: {
    runecrafting_level_required?: number;
    runes_per_hour?: number;
  }): Promise<PaginatedResponse<MoneyMakerTypes.RuneMagicStrategy>> {
    const response = await apiClient.get('/rune-magic/', { params });
    return response.data;
  },

  async getHighAlchemyOpportunities(): Promise<{
    high_alchemy_opportunities: Array<{
      item_id: number;
      item_name: string;
      buy_price: number;
      alch_value: number;
      profit_per_alch: number;
      nature_rune_cost: number;
      magic_level_required: number;
      hourly_profit_potential: number;
    }>;
    total_opportunities: number;
    magic_level_note: string;
    alching_speed: string;
  }> {
    const response = await apiClient.get('/rune-magic/high_alchemy_opportunities/');
    return response.data;
  },

  async getRuneTradingOpportunities(params?: {
    min_level?: number;
    max_level?: number;
  }): Promise<{
    rune_trading_opportunities: Array<{
      rune_type: string;
      rune_item_id: number;
      level_required: number;
      essence_buy_price: number;
      rune_sell_price: number;
      profit_per_essence: number;
      profit_per_rune: number;
      runes_per_essence: number;
      hourly_profit_gp: number;
      runes_per_hour: number;
      essences_per_hour: number;
      capital_required: number;
      profit_margin_pct: number;
      volume_score: number;
      last_updated: string;
      data_freshness: string;
    }>;
    total_opportunities: number;
    data_source: string;
    last_analysis: string;
    market_note: string;
    profit_explanation: string;
    level_range: string;
  }> {
    const response = await apiClient.get('/rune-magic/rune_trading_opportunities/', { params });
    return response.data;
  },

  // Real-Time Opportunity Detection
  async detectAllOpportunities(capital: number = 50_000_000): Promise<{
    opportunities_by_type: Record<MoneyMakerTypes.StrategyType, MoneyMakerTypes.MoneyMakerOpportunity[]>;
    total_opportunities: number;
    capital_analyzed: number;
    detection_timestamp: string;
  }> {
    const response = await apiClient.get('/opportunities/detect_all/', {
      params: { capital }
    });
    return response.data;
  },

  // GE Tax Calculator
  async calculateGETax(price: number, itemId?: number): Promise<MoneyMakerTypes.GETaxCalculation> {
    const response = await apiClient.get('/opportunities/ge_tax_calculator/', {
      params: { price, item_id: itemId }
    });
    return response.data;
  },

  // Capital Progression Advisor
  async getProgressionAdvice(
    currentCapital: number,
    targetCapital: number = 100_000_000,
    riskTolerance: string = 'medium'
  ): Promise<MoneyMakerTypes.CapitalProgressionAdvice> {
    const response = await apiClient.get('/capital-progression/get_advice/', {
      params: {
        capital: currentCapital,
        target: targetCapital,
        risk: riskTolerance
      }
    });
    return response.data;
  },

  async getProgressionRoadmap(
    currentCapital: number,
    targetCapital: number = 100_000_000
  ): Promise<{
    roadmap: {
      current_tier: string;
      target_tier: string;
      total_phases: number;
      estimated_total_hours: number;
      phases: Array<{
        phase_number: number;
        capital_start: number;
        capital_target: number;
        recommended_strategies: string[];
        estimated_hours: number;
        key_milestones: string[];
      }>;
    };
  }> {
    const response = await apiClient.get('/capital-progression/progression_roadmap/', {
      params: {
        capital: currentCapital,
        target: targetCapital
      }
    });
    return response.data;
  },

  // Analytics & Market Overview
  async getMarketOverview(): Promise<MoneyMakerTypes.MarketOverview> {
    const response = await apiClient.get('/analytics/market_overview/');
    return response.data;
  },

  async getProfitProjections(hours: number = 24): Promise<MoneyMakerTypes.ProfitProjection> {
    const response = await apiClient.get('/analytics/profit_projections/', {
      params: { hours }
    });
    return response.data;
  },
};

// Error handling wrapper
export const handleApiError = (error: any): string => {
  if (error.response?.data?.error) {
    return error.response.data.error;
  }
  if (error.message) {
    return error.message;
  }
  return 'An unexpected error occurred';
};

// Real-time data hooks for React components
export const useMoneyMakerData = () => {
  const [data, setData] = React.useState<{
    strategies: MoneyMakerTypes.MoneyMakerStrategy[];
    opportunities: Record<MoneyMakerTypes.StrategyType, MoneyMakerTypes.MoneyMakerOpportunity[]>;
    loading: boolean;
    error: string | null;
  }>({
    strategies: [],
    opportunities: {} as Record<MoneyMakerTypes.StrategyType, MoneyMakerTypes.MoneyMakerOpportunity[]>,
    loading: true,
    error: null
  });

  const refreshData = async (capital: number = 50_000_000) => {
    try {
      setData(prev => ({ ...prev, loading: true, error: null }));
      
      const [strategiesResponse, opportunitiesResponse] = await Promise.all([
        moneyMakerApi.getStrategies({ min_capital: capital }),
        moneyMakerApi.detectAllOpportunities(capital)
      ]);

      setData({
        strategies: strategiesResponse.results,
        opportunities: opportunitiesResponse.opportunities_by_type,
        loading: false,
        error: null
      });
    } catch (error) {
      setData(prev => ({
        ...prev,
        loading: false,
        error: handleApiError(error)
      }));
    }
  };

  return { ...data, refreshData };
};

export default moneyMakerApi;