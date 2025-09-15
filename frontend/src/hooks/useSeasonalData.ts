import { useState, useEffect, useCallback } from 'react';
import { realtimeApi } from '../api/realtimeApi';
import type {
  SeasonalPattern,
  SeasonalForecast,
  SeasonalEvent,
  SeasonalRecommendation,
  TechnicalAnalysis,
  MarketMomentum,
  SentimentAnalysis,
  PricePrediction,
  MarketOverview,
  SeasonalAnalytics,
  ForecastAccuracyStats,
  PaginatedResponse,
  SeasonalPatternFilters,
  SeasonalForecastFilters,
  SeasonalEventFilters,
  SeasonalRecommendationFilters,
} from '../types/seasonal';

interface UseApiState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

interface UsePaginatedState<T> {
  data: T[];
  loading: boolean;
  error: string | null;
  hasMore: boolean;
  loadMore: () => Promise<void>;
  refetch: () => Promise<void>;
  totalCount: number;
}

// Generic hook for simple API calls
function useApiCall<T>(
  apiCall: () => Promise<T>,
  dependencies: any[] = []
): UseApiState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const result = await apiCall();
      setData(result);
    } catch (err: any) {
      setError(err.message || 'An error occurred');
      console.error('API call failed:', err);
    } finally {
      setLoading(false);
    }
  }, dependencies);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return {
    data,
    loading,
    error,
    refetch: fetchData,
  };
}

// Generic hook for paginated API calls
function usePaginatedApi<T>(
  apiCall: (filters: any) => Promise<PaginatedResponse<T>>,
  initialFilters: any = {},
  pageSize = 20
): UsePaginatedState<T> {
  const [data, setData] = useState<T[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(true);
  const [totalCount, setTotalCount] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);

  const fetchData = useCallback(async (page = 1, append = false) => {
    try {
      setLoading(true);
      setError(null);
      
      const filters = {
        ...initialFilters,
        page,
        page_size: pageSize,
      };
      
      const result = await apiCall(filters);
      
      if (append) {
        setData(prev => [...prev, ...result.results]);
      } else {
        setData(result.results);
      }
      
      setTotalCount(result.count);
      setHasMore(result.next !== null);
      setCurrentPage(page);
    } catch (err: any) {
      setError(err.message || 'An error occurred');
      console.error('Paginated API call failed:', err);
    } finally {
      setLoading(false);
    }
  }, [apiCall, initialFilters, pageSize]);

  const loadMore = useCallback(async () => {
    if (hasMore && !loading) {
      await fetchData(currentPage + 1, true);
    }
  }, [hasMore, loading, currentPage, fetchData]);

  const refetch = useCallback(async () => {
    setCurrentPage(1);
    await fetchData(1, false);
  }, [fetchData]);

  useEffect(() => {
    fetchData(1, false);
  }, [fetchData]);

  return {
    data,
    loading,
    error,
    hasMore,
    loadMore,
    refetch,
    totalCount,
  };
}

// =============================================================================
// SEASONAL PATTERN HOOKS
// =============================================================================

export function useSeasonalPatterns(filters: SeasonalPatternFilters = {}) {
  return usePaginatedApi(
    (f: SeasonalPatternFilters) => realtimeApi.patterns.getPatterns(f),
    filters
  );
}

export function useSeasonalPattern(id: number) {
  return useApiCall(
    () => realtimeApi.patterns.getPattern(id),
    [id]
  );
}

export function useSeasonalPatternByItem(itemId: number) {
  return useApiCall(
    () => realtimeApi.patterns.getPatternByItem(itemId),
    [itemId]
  );
}

export function useStrongSeasonalPatterns(limit = 20) {
  return useApiCall(
    () => realtimeApi.patterns.getStrongPatterns(limit),
    [limit]
  );
}

// =============================================================================
// SEASONAL FORECAST HOOKS
// =============================================================================

export function useSeasonalForecasts(filters: SeasonalForecastFilters = {}) {
  return usePaginatedApi(
    (f: SeasonalForecastFilters) => realtimeApi.forecasts.getForecasts(f),
    filters
  );
}

export function useSeasonalForecast(id: number) {
  return useApiCall(
    () => realtimeApi.forecasts.getForecast(id),
    [id]
  );
}

export function useUpcomingForecasts(limit = 20) {
  return useApiCall(
    () => realtimeApi.forecasts.getUpcomingForecasts(limit),
    [limit]
  );
}

export function useForecastsByItem(itemId: number, limit = 10) {
  return useApiCall(
    () => realtimeApi.forecasts.getForecastsByItem(itemId, limit),
    [itemId, limit]
  );
}

// =============================================================================
// SEASONAL EVENT HOOKS
// =============================================================================

export function useSeasonalEvents(filters: SeasonalEventFilters = {}) {
  return usePaginatedApi(
    (f: SeasonalEventFilters) => realtimeApi.events.getEvents(f),
    filters
  );
}

export function useSeasonalEvent(id: number) {
  return useApiCall(
    () => realtimeApi.events.getEvent(id),
    [id]
  );
}

export function useUpcomingEvents(limit = 10) {
  return useApiCall(
    () => realtimeApi.events.getUpcomingEvents(limit),
    [limit]
  );
}

export function useSignificantEvents(limit = 20) {
  return useApiCall(
    () => realtimeApi.events.getSignificantEvents(limit),
    [limit]
  );
}

// =============================================================================
// SEASONAL RECOMMENDATION HOOKS
// =============================================================================

export function useSeasonalRecommendations(filters: SeasonalRecommendationFilters = {}) {
  return usePaginatedApi(
    (f: SeasonalRecommendationFilters) => realtimeApi.recommendations.getRecommendations(f),
    filters
  );
}

export function useSeasonalRecommendation(id: number) {
  return useApiCall(
    () => realtimeApi.recommendations.getRecommendation(id),
    [id]
  );
}

export function useActiveRecommendations(limit = 20) {
  return useApiCall(
    () => realtimeApi.recommendations.getActiveRecommendations(limit),
    [limit]
  );
}

export function useRecommendationsByItem(itemId: number, limit = 10) {
  return useApiCall(
    () => realtimeApi.recommendations.getRecommendationsByItem(itemId, limit),
    [itemId, limit]
  );
}

export function useTradingRecommendations(limit = 15) {
  return useApiCall(
    () => realtimeApi.recommendations.getTradingRecommendations(limit),
    [limit]
  );
}

// =============================================================================
// TECHNICAL ANALYSIS HOOKS
// =============================================================================

export function useTechnicalAnalyses(filters: { page?: number; page_size?: number; ordering?: string } = {}) {
  return usePaginatedApi(
    (f: any) => realtimeApi.technical.getAnalyses(f),
    filters
  );
}

export function useTechnicalAnalysisByItem(itemId: number) {
  return useApiCall(
    () => realtimeApi.technical.getAnalysisByItem(itemId),
    [itemId]
  );
}

// =============================================================================
// MARKET DATA HOOKS
// =============================================================================

export function useMarketMomentum(filters: { ordering?: string; page?: number; page_size?: number } = {}) {
  return usePaginatedApi(
    (f: any) => realtimeApi.market.getMomentum(f),
    filters
  );
}

export function useMarketSentiment(filters: { ordering?: string; page?: number; page_size?: number } = {}) {
  return usePaginatedApi(
    (f: any) => realtimeApi.market.getSentiment(f),
    filters
  );
}

export function usePricePredictions(filters: { ordering?: string; page?: number; page_size?: number } = {}) {
  return usePaginatedApi(
    (f: any) => realtimeApi.market.getPredictions(f),
    filters
  );
}

export function usePricePredictionByItem(itemId: number) {
  return useApiCall(
    () => realtimeApi.market.getPredictionByItem(itemId),
    [itemId]
  );
}

// =============================================================================
// ANALYTICS HOOKS
// =============================================================================

export function useMarketOverview() {
  return useApiCall(
    () => realtimeApi.analytics.getMarketOverview()
  );
}

export function useSeasonalAnalytics() {
  return useApiCall(
    () => realtimeApi.analytics.getSeasonalAnalytics()
  );
}

export function useForecastAccuracyStats(daysBack = 30) {
  return useApiCall(
    () => realtimeApi.analytics.getForecastAccuracyStats(daysBack),
    [daysBack]
  );
}

// =============================================================================
// COMPOSITE HOOKS FOR DASHBOARD VIEWS
// =============================================================================

export function useSeasonalDashboard() {
  const marketOverview = useMarketOverview();
  const seasonalAnalytics = useSeasonalAnalytics();
  const strongPatterns = useStrongSeasonalPatterns(10);
  const upcomingEvents = useUpcomingEvents(5);
  const activeRecommendations = useActiveRecommendations(10);
  const tradingRecommendations = useTradingRecommendations(8);

  return {
    marketOverview,
    seasonalAnalytics,
    strongPatterns,
    upcomingEvents,
    activeRecommendations,
    tradingRecommendations,
    loading: marketOverview.loading || seasonalAnalytics.loading || strongPatterns.loading,
    error: marketOverview.error || seasonalAnalytics.error || strongPatterns.error,
    refetchAll: async () => {
      await Promise.all([
        marketOverview.refetch(),
        seasonalAnalytics.refetch(),
        strongPatterns.refetch(),
        upcomingEvents.refetch(),
        activeRecommendations.refetch(),
        tradingRecommendations.refetch(),
      ]);
    },
  };
}

export function useItemSeasonalData(itemId: number) {
  const pattern = useSeasonalPatternByItem(itemId);
  const forecasts = useForecastsByItem(itemId, 5);
  const recommendations = useRecommendationsByItem(itemId, 5);
  const technicalAnalysis = useTechnicalAnalysisByItem(itemId);
  const pricePrediction = usePricePredictionByItem(itemId);

  return {
    pattern,
    forecasts,
    recommendations,
    technicalAnalysis,
    pricePrediction,
    loading: pattern.loading || forecasts.loading || recommendations.loading,
    error: pattern.error || forecasts.error || recommendations.error,
    refetchAll: async () => {
      await Promise.all([
        pattern.refetch(),
        forecasts.refetch(),
        recommendations.refetch(),
        technicalAnalysis.refetch(),
        pricePrediction.refetch(),
      ]);
    },
  };
}