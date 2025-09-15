/**
 * Real-Time Market Engine API Client
 * 
 * Handles all API calls for seasonal patterns, forecasts, events, and recommendations.
 */

import { fastApiClient, apiClient } from './client';
import type {
  SeasonalPattern,
  SeasonalForecast,
  SeasonalEvent,
  SeasonalRecommendation,
  TechnicalAnalysis,
  MarketMomentum,
  SentimentAnalysis,
  PricePrediction,
  PaginatedResponse,
  MarketOverview,
  SeasonalAnalytics,
  ForecastAccuracyStats,
  SeasonalPatternFilters,
  SeasonalForecastFilters,
  SeasonalEventFilters,
  SeasonalRecommendationFilters,
} from '../types/seasonal';

// =============================================================================
// SEASONAL PATTERN API
// =============================================================================

export const seasonalPatternsApi = {
  /**
   * Get paginated list of seasonal patterns with filtering
   */
  async getPatterns(filters: SeasonalPatternFilters = {}): Promise<PaginatedResponse<SeasonalPattern>> {
    const params = new URLSearchParams();
    
    if (filters.item_id) params.append('item_id', filters.item_id.toString());
    if (filters.min_strength) params.append('min_strength', filters.min_strength.toString());
    if (filters.pattern_type) params.append('pattern_type', filters.pattern_type);
    if (filters.days_back) params.append('days_back', filters.days_back.toString());
    if (filters.ordering) params.append('ordering', filters.ordering);
    if (filters.page) params.append('page', filters.page.toString());
    if (filters.page_size) params.append('page_size', filters.page_size.toString());
    
    const response = await fastApiClient.get(`/realtime/seasonal/patterns/?${params}`);
    return response.data;
  },

  /**
   * Get specific seasonal pattern by ID
   */
  async getPattern(id: number): Promise<SeasonalPattern> {
    const response = await fastApiClient.get(`/realtime/seasonal/patterns/${id}/`);
    return response.data;
  },

  /**
   * Get latest seasonal pattern for specific item
   */
  async getPatternByItem(itemId: number): Promise<SeasonalPattern | null> {
    try {
      const response = await fastApiClient.get(`/realtime/seasonal/patterns/item/${itemId}/`);
      return response.data;
    } catch (error: any) {
      if (error.response?.status === 404) {
        return null;
      }
      throw error;
    }
  },

  /**
   * Get strong patterns (strength >= 0.6)
   */
  async getStrongPatterns(limit = 20): Promise<SeasonalPattern[]> {
    const response = await this.getPatterns({
      min_strength: 0.6,
      ordering: '-overall_pattern_strength',
      page_size: limit
    });
    return response.results;
  },
};

// =============================================================================
// SEASONAL FORECAST API
// =============================================================================

export const seasonalForecastsApi = {
  /**
   * Get paginated list of seasonal forecasts with filtering
   */
  async getForecasts(filters: SeasonalForecastFilters = {}): Promise<PaginatedResponse<SeasonalForecast>> {
    const params = new URLSearchParams();
    
    if (filters.item_id) params.append('item_id', filters.item_id.toString());
    if (filters.horizon) params.append('horizon', filters.horizon);
    if (filters.validated !== undefined) params.append('validated', filters.validated.toString());
    if (filters.upcoming !== undefined) params.append('upcoming', filters.upcoming.toString());
    if (filters.min_confidence) params.append('min_confidence', filters.min_confidence.toString());
    if (filters.ordering) params.append('ordering', filters.ordering);
    if (filters.page) params.append('page', filters.page.toString());
    if (filters.page_size) params.append('page_size', filters.page_size.toString());
    
    const response = await fastApiClient.get(`/realtime/seasonal/forecasts/?${params}`);
    return response.data;
  },

  /**
   * Get specific seasonal forecast by ID
   */
  async getForecast(id: number): Promise<SeasonalForecast> {
    const response = await fastApiClient.get(`/realtime/seasonal/forecasts/${id}/`);
    return response.data;
  },

  /**
   * Get upcoming forecasts for next 30 days
   */
  async getUpcomingForecasts(limit = 20): Promise<SeasonalForecast[]> {
    const response = await this.getForecasts({
      upcoming: true,
      min_confidence: 0.7,
      ordering: 'target_date',
      page_size: limit
    });
    return response.results;
  },

  /**
   * Get forecasts by item ID
   */
  async getForecastsByItem(itemId: number, limit = 10): Promise<SeasonalForecast[]> {
    const response = await this.getForecasts({
      item_id: itemId,
      ordering: 'target_date',
      page_size: limit
    });
    return response.results;
  },
};

// =============================================================================
// SEASONAL EVENT API
// =============================================================================

export const seasonalEventsApi = {
  /**
   * Get paginated list of seasonal events with filtering
   */
  async getEvents(filters: SeasonalEventFilters = {}): Promise<PaginatedResponse<SeasonalEvent>> {
    const params = new URLSearchParams();
    
    if (filters.event_type) params.append('event_type', filters.event_type);
    if (filters.upcoming !== undefined) params.append('upcoming', filters.upcoming.toString());
    if (filters.active !== undefined) params.append('active', filters.active.toString());
    if (filters.verified !== undefined) params.append('verified', filters.verified.toString());
    if (filters.significant_impact !== undefined) params.append('significant_impact', filters.significant_impact.toString());
    if (filters.ordering) params.append('ordering', filters.ordering);
    if (filters.page) params.append('page', filters.page.toString());
    if (filters.page_size) params.append('page_size', filters.page_size.toString());
    
    const response = await fastApiClient.get(`/realtime/seasonal/events/?${params}`);
    return response.data;
  },

  /**
   * Get specific seasonal event by ID
   */
  async getEvent(id: number): Promise<SeasonalEvent> {
    const response = await fastApiClient.get(`/realtime/seasonal/events/${id}/`);
    return response.data;
  },

  /**
   * Get upcoming events for next 60 days
   */
  async getUpcomingEvents(limit = 10): Promise<SeasonalEvent[]> {
    const response = await this.getEvents({
      upcoming: true,
      verified: true,
      ordering: 'start_date',
      page_size: limit
    });
    return response.results;
  },

  /**
   * Get events with significant market impact
   */
  async getSignificantEvents(limit = 20): Promise<SeasonalEvent[]> {
    const response = await this.getEvents({
      significant_impact: true,
      ordering: '-average_price_impact_pct',
      page_size: limit
    });
    return response.results;
  },
};

// =============================================================================
// SEASONAL RECOMMENDATION API
// =============================================================================

export const seasonalRecommendationsApi = {
  /**
   * Get paginated list of seasonal recommendations with filtering
   */
  async getRecommendations(filters: SeasonalRecommendationFilters = {}): Promise<PaginatedResponse<SeasonalRecommendation>> {
    const params = new URLSearchParams();
    
    if (filters.item_id) params.append('item_id', filters.item_id.toString());
    if (filters.recommendation_type) params.append('recommendation_type', filters.recommendation_type);
    if (filters.active !== undefined) params.append('active', filters.active.toString());
    if (filters.executed !== undefined) params.append('executed', filters.executed.toString());
    if (filters.current !== undefined) params.append('current', filters.current.toString());
    if (filters.min_confidence) params.append('min_confidence', filters.min_confidence.toString());
    if (filters.ordering) params.append('ordering', filters.ordering);
    if (filters.page) params.append('page', filters.page.toString());
    if (filters.page_size) params.append('page_size', filters.page_size.toString());
    
    const response = await fastApiClient.get(`/realtime/seasonal/recommendations/?${params}`);
    return response.data;
  },

  /**
   * Get specific seasonal recommendation by ID
   */
  async getRecommendation(id: number): Promise<SeasonalRecommendation> {
    const response = await fastApiClient.get(`/realtime/seasonal/recommendations/${id}/`);
    return response.data;
  },

  /**
   * Get active recommendations
   */
  async getActiveRecommendations(limit = 20): Promise<SeasonalRecommendation[]> {
    const response = await this.getRecommendations({
      active: true,
      current: true,
      min_confidence: 0.6,
      ordering: '-confidence_score',
      page_size: limit
    });
    return response.results;
  },

  /**
   * Get recommendations by item ID
   */
  async getRecommendationsByItem(itemId: number, limit = 10): Promise<SeasonalRecommendation[]> {
    const response = await this.getRecommendations({
      item_id: itemId,
      ordering: '-recommendation_timestamp',
      page_size: limit
    });
    return response.results;
  },

  /**
   * Get buy/sell recommendations
   */
  async getTradingRecommendations(limit = 15): Promise<SeasonalRecommendation[]> {
    const buyRecommendations = await this.getRecommendations({
      recommendation_type: 'buy',
      active: true,
      current: true,
      ordering: '-confidence_score',
      page_size: Math.ceil(limit / 2)
    });

    const sellRecommendations = await this.getRecommendations({
      recommendation_type: 'sell',
      active: true,
      current: true,
      ordering: '-confidence_score',
      page_size: Math.ceil(limit / 2)
    });

    return [...buyRecommendations.results, ...sellRecommendations.results]
      .sort((a, b) => b.confidence_score - a.confidence_score)
      .slice(0, limit);
  },
};

// =============================================================================
// TECHNICAL ANALYSIS API
// =============================================================================

export const technicalAnalysisApi = {
  /**
   * Get paginated list of technical analyses
   */
  async getAnalyses(filters: { page?: number; page_size?: number; ordering?: string } = {}): Promise<PaginatedResponse<TechnicalAnalysis>> {
    const params = new URLSearchParams();
    
    if (filters.ordering) params.append('ordering', filters.ordering);
    if (filters.page) params.append('page', filters.page.toString());
    if (filters.page_size) params.append('page_size', filters.page_size.toString());
    
    const response = await fastApiClient.get(`/realtime/technical/analyses/?${params}`);
    return response.data;
  },

  /**
   * Get latest technical analysis for specific item
   */
  async getAnalysisByItem(itemId: number): Promise<TechnicalAnalysis | null> {
    try {
      const response = await fastApiClient.get(`/realtime/technical/analyses/item/${itemId}/`);
      return response.data;
    } catch (error: any) {
      if (error.response?.status === 404) {
        return null;
      }
      throw error;
    }
  },
};

// =============================================================================
// MARKET DATA API
// =============================================================================

export const marketDataApi = {
  /**
   * Get market momentum data
   */
  async getMomentum(filters: { ordering?: string; page?: number; page_size?: number } = {}): Promise<PaginatedResponse<MarketMomentum>> {
    const params = new URLSearchParams();
    
    if (filters.ordering) params.append('ordering', filters.ordering);
    if (filters.page) params.append('page', filters.page.toString());
    if (filters.page_size) params.append('page_size', filters.page_size.toString());
    
    const response = await fastApiClient.get(`/realtime/market/momentum/?${params}`);
    return response.data;
  },

  /**
   * Get sentiment analysis data
   */
  async getSentiment(filters: { ordering?: string; page?: number; page_size?: number } = {}): Promise<PaginatedResponse<SentimentAnalysis>> {
    const params = new URLSearchParams();
    
    if (filters.ordering) params.append('ordering', filters.ordering);
    if (filters.page) params.append('page', filters.page.toString());
    if (filters.page_size) params.append('page_size', filters.page_size.toString());
    
    const response = await fastApiClient.get(`/realtime/market/sentiment/?${params}`);
    return response.data;
  },

  /**
   * Get price predictions
   */
  async getPredictions(filters: { ordering?: string; page?: number; page_size?: number } = {}): Promise<PaginatedResponse<PricePrediction>> {
    const params = new URLSearchParams();
    
    if (filters.ordering) params.append('ordering', filters.ordering);
    if (filters.page) params.append('page', filters.page.toString());
    if (filters.page_size) params.append('page_size', filters.page_size.toString());
    
    const response = await fastApiClient.get(`/realtime/market/predictions/?${params}`);
    return response.data;
  },

  /**
   * Get latest price prediction for specific item
   */
  async getPredictionByItem(itemId: number): Promise<PricePrediction | null> {
    try {
      const response = await fastApiClient.get(`/realtime/market/predictions/item/${itemId}/`);
      return response.data;
    } catch (error: any) {
      if (error.response?.status === 404) {
        return null;
      }
      throw error;
    }
  },
};

// =============================================================================
// ANALYTICS AND OVERVIEW API
// =============================================================================

export const analyticsApi = {
  /**
   * Get market overview dashboard data
   */
  async getMarketOverview(): Promise<MarketOverview> {
    const response = await fastApiClient.get('/realtime/analytics/overview/');
    return response.data;
  },

  /**
   * Get seasonal analytics dashboard data
   */
  async getSeasonalAnalytics(): Promise<SeasonalAnalytics> {
    const response = await fastApiClient.get('/realtime/analytics/seasonal/');
    return response.data;
  },

  /**
   * Get forecast accuracy statistics
   */
  async getForecastAccuracyStats(daysBack = 30): Promise<ForecastAccuracyStats> {
    const response = await fastApiClient.get(`/realtime/analytics/forecast-accuracy/?days_back=${daysBack}`);
    return response.data;
  },
};

// =============================================================================
// COMBINED API OBJECT
// =============================================================================

export const realtimeApi = {
  patterns: seasonalPatternsApi,
  forecasts: seasonalForecastsApi,
  events: seasonalEventsApi,
  recommendations: seasonalRecommendationsApi,
  technical: technicalAnalysisApi,
  market: marketDataApi,
  analytics: analyticsApi,
};

// Individual APIs are already exported above with export const declarations

export default realtimeApi;