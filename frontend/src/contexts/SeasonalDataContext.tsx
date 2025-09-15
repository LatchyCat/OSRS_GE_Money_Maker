import React, { createContext, useContext, useReducer, useCallback, useEffect, ReactNode } from 'react';
import type {
  SeasonalPattern,
  SeasonalForecast,
  SeasonalEvent,
  SeasonalRecommendation,
  MarketOverview,
  SeasonalAnalytics,
} from '../types/seasonal';
import { realtimeApi } from '../api/realtimeApi';

interface SeasonalDataState {
  // Cache for frequently accessed data
  marketOverview: MarketOverview | null;
  seasonalAnalytics: SeasonalAnalytics | null;
  strongPatterns: SeasonalPattern[];
  upcomingEvents: SeasonalEvent[];
  activeRecommendations: SeasonalRecommendation[];
  upcomingForecasts: SeasonalForecast[];
  
  // Loading states
  loading: {
    overview: boolean;
    analytics: boolean;
    patterns: boolean;
    events: boolean;
    recommendations: boolean;
    forecasts: boolean;
  };
  
  // Error states
  errors: {
    overview: string | null;
    analytics: string | null;
    patterns: string | null;
    events: string | null;
    recommendations: string | null;
    forecasts: string | null;
  };
  
  // Last updated timestamps
  lastUpdated: {
    overview: number | null;
    analytics: number | null;
    patterns: number | null;
    events: number | null;
    recommendations: number | null;
    forecasts: number | null;
  };
  
  // Item-specific cache
  itemData: Record<number, {
    pattern: SeasonalPattern | null;
    forecasts: SeasonalForecast[];
    recommendations: SeasonalRecommendation[];
    lastUpdated: number;
  }>;
}

type SeasonalDataAction =
  | { type: 'SET_LOADING'; payload: { key: keyof SeasonalDataState['loading']; loading: boolean } }
  | { type: 'SET_ERROR'; payload: { key: keyof SeasonalDataState['errors']; error: string | null } }
  | { type: 'SET_MARKET_OVERVIEW'; payload: MarketOverview }
  | { type: 'SET_SEASONAL_ANALYTICS'; payload: SeasonalAnalytics }
  | { type: 'SET_STRONG_PATTERNS'; payload: SeasonalPattern[] }
  | { type: 'SET_UPCOMING_EVENTS'; payload: SeasonalEvent[] }
  | { type: 'SET_ACTIVE_RECOMMENDATIONS'; payload: SeasonalRecommendation[] }
  | { type: 'SET_UPCOMING_FORECASTS'; payload: SeasonalForecast[] }
  | { type: 'SET_ITEM_DATA'; payload: { itemId: number; data: Partial<SeasonalDataState['itemData'][number]> } }
  | { type: 'INVALIDATE_CACHE'; payload?: { itemId?: number } }
  | { type: 'CLEAR_ERRORS' };

const initialState: SeasonalDataState = {
  marketOverview: null,
  seasonalAnalytics: null,
  strongPatterns: [],
  upcomingEvents: [],
  activeRecommendations: [],
  upcomingForecasts: [],
  loading: {
    overview: false,
    analytics: false,
    patterns: false,
    events: false,
    recommendations: false,
    forecasts: false,
  },
  errors: {
    overview: null,
    analytics: null,
    patterns: null,
    events: null,
    recommendations: null,
    forecasts: null,
  },
  lastUpdated: {
    overview: null,
    analytics: null,
    patterns: null,
    events: null,
    recommendations: null,
    forecasts: null,
  },
  itemData: {},
};

function seasonalDataReducer(state: SeasonalDataState, action: SeasonalDataAction): SeasonalDataState {
  switch (action.type) {
    case 'SET_LOADING':
      return {
        ...state,
        loading: {
          ...state.loading,
          [action.payload.key]: action.payload.loading,
        },
      };
      
    case 'SET_ERROR':
      return {
        ...state,
        errors: {
          ...state.errors,
          [action.payload.key]: action.payload.error,
        },
      };
      
    case 'SET_MARKET_OVERVIEW':
      return {
        ...state,
        marketOverview: action.payload,
        lastUpdated: {
          ...state.lastUpdated,
          overview: Date.now(),
        },
        errors: {
          ...state.errors,
          overview: null,
        },
      };
      
    case 'SET_SEASONAL_ANALYTICS':
      return {
        ...state,
        seasonalAnalytics: action.payload,
        lastUpdated: {
          ...state.lastUpdated,
          analytics: Date.now(),
        },
        errors: {
          ...state.errors,
          analytics: null,
        },
      };
      
    case 'SET_STRONG_PATTERNS':
      return {
        ...state,
        strongPatterns: action.payload,
        lastUpdated: {
          ...state.lastUpdated,
          patterns: Date.now(),
        },
        errors: {
          ...state.errors,
          patterns: null,
        },
      };
      
    case 'SET_UPCOMING_EVENTS':
      return {
        ...state,
        upcomingEvents: action.payload,
        lastUpdated: {
          ...state.lastUpdated,
          events: Date.now(),
        },
        errors: {
          ...state.errors,
          events: null,
        },
      };
      
    case 'SET_ACTIVE_RECOMMENDATIONS':
      return {
        ...state,
        activeRecommendations: action.payload,
        lastUpdated: {
          ...state.lastUpdated,
          recommendations: Date.now(),
        },
        errors: {
          ...state.errors,
          recommendations: null,
        },
      };
      
    case 'SET_UPCOMING_FORECASTS':
      return {
        ...state,
        upcomingForecasts: action.payload,
        lastUpdated: {
          ...state.lastUpdated,
          forecasts: Date.now(),
        },
        errors: {
          ...state.errors,
          forecasts: null,
        },
      };
      
    case 'SET_ITEM_DATA':
      return {
        ...state,
        itemData: {
          ...state.itemData,
          [action.payload.itemId]: {
            ...state.itemData[action.payload.itemId],
            ...action.payload.data,
            lastUpdated: Date.now(),
          },
        },
      };
      
    case 'INVALIDATE_CACHE':
      if (action.payload?.itemId) {
        const { [action.payload.itemId]: removed, ...remainingItemData } = state.itemData;
        return {
          ...state,
          itemData: remainingItemData,
        };
      }
      return {
        ...initialState,
        loading: state.loading,
      };
      
    case 'CLEAR_ERRORS':
      return {
        ...state,
        errors: {
          overview: null,
          analytics: null,
          patterns: null,
          events: null,
          recommendations: null,
          forecasts: null,
        },
      };
      
    default:
      return state;
  }
}

interface SeasonalDataContextValue {
  state: SeasonalDataState;
  actions: {
    fetchMarketOverview: () => Promise<void>;
    fetchSeasonalAnalytics: () => Promise<void>;
    fetchStrongPatterns: (limit?: number) => Promise<void>;
    fetchUpcomingEvents: (limit?: number) => Promise<void>;
    fetchActiveRecommendations: (limit?: number) => Promise<void>;
    fetchUpcomingForecasts: (limit?: number) => Promise<void>;
    fetchItemData: (itemId: number) => Promise<void>;
    refreshAll: () => Promise<void>;
    invalidateCache: (itemId?: number) => void;
    clearErrors: () => void;
  };
  utils: {
    isDataStale: (key: keyof SeasonalDataState['lastUpdated'], maxAgeMs?: number) => boolean;
    getItemData: (itemId: number) => SeasonalDataState['itemData'][number] | null;
    hasAnyError: () => boolean;
    isAnyLoading: () => boolean;
  };
}

const SeasonalDataContext = createContext<SeasonalDataContextValue | undefined>(undefined);

interface SeasonalDataProviderProps {
  children: ReactNode;
  cacheTimeMs?: number; // Default 5 minutes
  autoRefreshIntervalMs?: number; // Default 30 seconds for critical data
}

export function SeasonalDataProvider({ 
  children, 
  cacheTimeMs = 5 * 60 * 1000,
  autoRefreshIntervalMs = 30 * 1000,
}: SeasonalDataProviderProps) {
  const [state, dispatch] = useReducer(seasonalDataReducer, initialState);

  // Utility functions
  const isDataStale = useCallback((key: keyof SeasonalDataState['lastUpdated'], maxAgeMs = cacheTimeMs) => {
    const lastUpdated = state.lastUpdated[key];
    return !lastUpdated || (Date.now() - lastUpdated) > maxAgeMs;
  }, [state.lastUpdated, cacheTimeMs]);

  const getItemData = useCallback((itemId: number) => {
    return state.itemData[itemId] || null;
  }, [state.itemData]);

  const hasAnyError = useCallback(() => {
    return Object.values(state.errors).some(error => error !== null);
  }, [state.errors]);

  const isAnyLoading = useCallback(() => {
    return Object.values(state.loading).some(loading => loading);
  }, [state.loading]);

  // API actions
  const fetchMarketOverview = useCallback(async () => {
    if (state.loading.overview) return;
    
    dispatch({ type: 'SET_LOADING', payload: { key: 'overview', loading: true } });
    dispatch({ type: 'SET_ERROR', payload: { key: 'overview', error: null } });
    
    try {
      const data = await realtimeApi.analytics.getMarketOverview();
      dispatch({ type: 'SET_MARKET_OVERVIEW', payload: data });
    } catch (error: any) {
      dispatch({ type: 'SET_ERROR', payload: { key: 'overview', error: error.message } });
    } finally {
      dispatch({ type: 'SET_LOADING', payload: { key: 'overview', loading: false } });
    }
  }, [state.loading.overview]);

  const fetchSeasonalAnalytics = useCallback(async () => {
    if (state.loading.analytics) return;
    
    dispatch({ type: 'SET_LOADING', payload: { key: 'analytics', loading: true } });
    dispatch({ type: 'SET_ERROR', payload: { key: 'analytics', error: null } });
    
    try {
      const data = await realtimeApi.analytics.getSeasonalAnalytics();
      dispatch({ type: 'SET_SEASONAL_ANALYTICS', payload: data });
    } catch (error: any) {
      dispatch({ type: 'SET_ERROR', payload: { key: 'analytics', error: error.message } });
    } finally {
      dispatch({ type: 'SET_LOADING', payload: { key: 'analytics', loading: false } });
    }
  }, [state.loading.analytics]);

  const fetchStrongPatterns = useCallback(async (limit = 20) => {
    if (state.loading.patterns) return;
    
    dispatch({ type: 'SET_LOADING', payload: { key: 'patterns', loading: true } });
    dispatch({ type: 'SET_ERROR', payload: { key: 'patterns', error: null } });
    
    try {
      const data = await realtimeApi.patterns.getStrongPatterns(limit);
      dispatch({ type: 'SET_STRONG_PATTERNS', payload: data });
    } catch (error: any) {
      dispatch({ type: 'SET_ERROR', payload: { key: 'patterns', error: error.message } });
    } finally {
      dispatch({ type: 'SET_LOADING', payload: { key: 'patterns', loading: false } });
    }
  }, [state.loading.patterns]);

  const fetchUpcomingEvents = useCallback(async (limit = 10) => {
    if (state.loading.events) return;
    
    dispatch({ type: 'SET_LOADING', payload: { key: 'events', loading: true } });
    dispatch({ type: 'SET_ERROR', payload: { key: 'events', error: null } });
    
    try {
      const data = await realtimeApi.events.getUpcomingEvents(limit);
      dispatch({ type: 'SET_UPCOMING_EVENTS', payload: data });
    } catch (error: any) {
      dispatch({ type: 'SET_ERROR', payload: { key: 'events', error: error.message } });
    } finally {
      dispatch({ type: 'SET_LOADING', payload: { key: 'events', loading: false } });
    }
  }, [state.loading.events]);

  const fetchActiveRecommendations = useCallback(async (limit = 20) => {
    if (state.loading.recommendations) return;
    
    dispatch({ type: 'SET_LOADING', payload: { key: 'recommendations', loading: true } });
    dispatch({ type: 'SET_ERROR', payload: { key: 'recommendations', error: null } });
    
    try {
      const data = await realtimeApi.recommendations.getActiveRecommendations(limit);
      dispatch({ type: 'SET_ACTIVE_RECOMMENDATIONS', payload: data });
    } catch (error: any) {
      dispatch({ type: 'SET_ERROR', payload: { key: 'recommendations', error: error.message } });
    } finally {
      dispatch({ type: 'SET_LOADING', payload: { key: 'recommendations', loading: false } });
    }
  }, [state.loading.recommendations]);

  const fetchUpcomingForecasts = useCallback(async (limit = 20) => {
    if (state.loading.forecasts) return;
    
    dispatch({ type: 'SET_LOADING', payload: { key: 'forecasts', loading: true } });
    dispatch({ type: 'SET_ERROR', payload: { key: 'forecasts', error: null } });
    
    try {
      const data = await realtimeApi.forecasts.getUpcomingForecasts(limit);
      dispatch({ type: 'SET_UPCOMING_FORECASTS', payload: data });
    } catch (error: any) {
      dispatch({ type: 'SET_ERROR', payload: { key: 'forecasts', error: error.message } });
    } finally {
      dispatch({ type: 'SET_LOADING', payload: { key: 'forecasts', loading: false } });
    }
  }, [state.loading.forecasts]);

  const fetchItemData = useCallback(async (itemId: number) => {
    try {
      const [pattern, forecasts, recommendations] = await Promise.all([
        realtimeApi.patterns.getPatternByItem(itemId).catch(() => null),
        realtimeApi.forecasts.getForecastsByItem(itemId, 5).catch(() => []),
        realtimeApi.recommendations.getRecommendationsByItem(itemId, 5).catch(() => []),
      ]);

      dispatch({
        type: 'SET_ITEM_DATA',
        payload: {
          itemId,
          data: {
            pattern,
            forecasts,
            recommendations,
          },
        },
      });
    } catch (error: any) {
      console.error(`Failed to fetch item data for ${itemId}:`, error);
    }
  }, []);

  const refreshAll = useCallback(async () => {
    await Promise.allSettled([
      fetchMarketOverview(),
      fetchSeasonalAnalytics(),
      fetchStrongPatterns(),
      fetchUpcomingEvents(),
      fetchActiveRecommendations(),
      fetchUpcomingForecasts(),
    ]);
  }, [
    fetchMarketOverview,
    fetchSeasonalAnalytics,
    fetchStrongPatterns,
    fetchUpcomingEvents,
    fetchActiveRecommendations,
    fetchUpcomingForecasts,
  ]);

  const invalidateCache = useCallback((itemId?: number) => {
    dispatch({ type: 'INVALIDATE_CACHE', payload: itemId ? { itemId } : undefined });
  }, []);

  const clearErrors = useCallback(() => {
    dispatch({ type: 'CLEAR_ERRORS' });
  }, []);

  // Auto-refresh critical data
  useEffect(() => {
    if (!autoRefreshIntervalMs) return;

    const interval = setInterval(() => {
      // Only refresh if data is stale and not currently loading
      if (isDataStale('overview', autoRefreshIntervalMs) && !state.loading.overview) {
        fetchMarketOverview();
      }
      if (isDataStale('analytics', autoRefreshIntervalMs * 2) && !state.loading.analytics) {
        fetchSeasonalAnalytics();
      }
      if (isDataStale('recommendations', autoRefreshIntervalMs) && !state.loading.recommendations) {
        fetchActiveRecommendations();
      }
    }, autoRefreshIntervalMs);

    return () => clearInterval(interval);
  }, [
    autoRefreshIntervalMs,
    isDataStale,
    state.loading,
    fetchMarketOverview,
    fetchSeasonalAnalytics,
    fetchActiveRecommendations,
  ]);

  // Initial data fetch
  useEffect(() => {
    refreshAll();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const value: SeasonalDataContextValue = {
    state,
    actions: {
      fetchMarketOverview,
      fetchSeasonalAnalytics,
      fetchStrongPatterns,
      fetchUpcomingEvents,
      fetchActiveRecommendations,
      fetchUpcomingForecasts,
      fetchItemData,
      refreshAll,
      invalidateCache,
      clearErrors,
    },
    utils: {
      isDataStale,
      getItemData,
      hasAnyError,
      isAnyLoading,
    },
  };

  return (
    <SeasonalDataContext.Provider value={value}>
      {children}
    </SeasonalDataContext.Provider>
  );
}

export function useSeasonalDataContext() {
  const context = useContext(SeasonalDataContext);
  if (!context) {
    throw new Error('useSeasonalDataContext must be used within a SeasonalDataProvider');
  }
  return context;
}

export default SeasonalDataContext;