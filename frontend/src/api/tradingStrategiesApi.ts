import { apiClient, aiApiClient } from './client';
import type {
  TradingStrategy,
  TradingStrategiesResponse,
  DecantingOpportunity,
  DecantingOpportunitiesResponse,
  FlippingOpportunity,
  FlippingOpportunitiesResponse,
  CraftingOpportunity,
  CraftingOpportunitiesResponse,
  SetCombiningOpportunity,
  SetCombiningOpportunitiesResponse,
  MarketConditionSnapshot,
  StrategyPerformance,
  TradingStrategyFilters,
  StrategyDashboardData
} from '../types/tradingStrategies';

const BASE_URL = '/trading';

// Trading Strategies CRUD Operations
export const tradingStrategiesApi = {
  // Get all trading strategies with optional filters
  getStrategies: async (filters?: TradingStrategyFilters): Promise<TradingStrategiesResponse> => {
    const params = new URLSearchParams();
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          params.append(key, String(value));
        }
      });
    }
    
    const response = await apiClient.get(`${BASE_URL}/strategies/?${params.toString()}`);
    return response.data;
  },

  // Get single strategy by ID
  getStrategy: async (id: number): Promise<TradingStrategy> => {
    const response = await apiClient.get(`${BASE_URL}/strategies/${id}/`);
    return response.data;
  },

  // Create new strategy
  createStrategy: async (strategy: Partial<TradingStrategy>): Promise<TradingStrategy> => {
    const response = await apiClient.post(`${BASE_URL}/strategies/`, strategy);
    return response.data;
  },

  // Update strategy
  updateStrategy: async (id: number, strategy: Partial<TradingStrategy>): Promise<TradingStrategy> => {
    const response = await apiClient.patch(`${BASE_URL}/strategies/${id}/`, strategy);
    return response.data;
  },

  // Delete strategy
  deleteStrategy: async (id: number): Promise<void> => {
    await apiClient.delete(`${BASE_URL}/strategies/${id}/`);
  },

  // Toggle strategy active status
  toggleStrategyActive: async (id: number): Promise<TradingStrategy> => {
    const response = await apiClient.patch(`${BASE_URL}/strategies/${id}/toggle_active/`);
    return response.data;
  },
};

// Decanting Opportunities
export const decantingApi = {
  getOpportunities: async (filters?: TradingStrategyFilters): Promise<DecantingOpportunitiesResponse> => {
    const params = new URLSearchParams();
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          params.append(key, String(value));
        }
      });
    }
    
    const response = await apiClient.get(`${BASE_URL}/decanting/?${params.toString()}`);
    return response.data;
  },

  getOpportunity: async (id: number): Promise<DecantingOpportunity> => {
    const response = await apiClient.get(`${BASE_URL}/decanting/${id}/`);
    return response.data;
  },

  // Trigger decanting opportunity scan
  scanOpportunities: async (): Promise<{ message: string; created_count: number }> => {
    const response = await apiClient.post(`${BASE_URL}/decanting/scan/`);
    return response.data;
  },

  // Generate comprehensive high-value opportunities
  discoverAllOpportunities: async (): Promise<{ message: string; created_count: number }> => {
    const response = await apiClient.post(`${BASE_URL}/decanting/discover_all/`, {}, {
      timeout: 30000 // 30 second timeout
    });
    return response.data;
  },

  // Get fresh decanting opportunities using WeirdGloop data
  getFreshOpportunities: async (filters?: TradingStrategyFilters): Promise<DecantingOpportunitiesResponse> => {
    const params = new URLSearchParams();
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          params.append(key, String(value));
        }
      });
    }
    
    const response = await apiClient.get(`${BASE_URL}/decanting/fresh_opportunities/?${params.toString()}`);
    return response.data;
  },

  // Get AI-powered decanting opportunities (can take 60+ seconds)
  getAIOpportunities: async (filters?: TradingStrategyFilters): Promise<DecantingOpportunitiesResponse> => {
    const params = new URLSearchParams();
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          params.append(key, String(value));
        }
      });
    }
    
    // Use regular endpoint for display (has legacy data but shows opportunities)
    const response = await apiClient.get(`${BASE_URL}/decanting/?${params.toString()}`, {
      timeout: 180000
    });
    return response.data;
  },

  // Get corrected decanting opportunities with proper OSRS logic
  getAdvancedOpportunities: async (filters?: TradingStrategyFilters): Promise<DecantingOpportunitiesResponse> => {
    const params = new URLSearchParams();
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          params.append(key, String(value));
        }
      });
    }
    
    // Use the corrected advanced-decanting endpoint (fixed backwards pricing issue)
    const response = await apiClient.get(`${BASE_URL}/advanced-decanting/?${params.toString()}`, {
      timeout: 180000
    });
    return response.data;
  }
};

// Flipping Opportunities
export const flippingApi = {
  getOpportunities: async (filters?: TradingStrategyFilters): Promise<FlippingOpportunitiesResponse> => {
    const params = new URLSearchParams();
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          params.append(key, String(value));
        }
      });
    }
    
    const response = await apiClient.get(`${BASE_URL}/flipping/?${params.toString()}`);
    return response.data;
  },

  getOpportunity: async (id: number): Promise<FlippingOpportunity> => {
    const response = await apiClient.get(`${BASE_URL}/flipping/${id}/`);
    return response.data;
  },

  // Trigger flipping opportunity scan
  scanOpportunities: async (): Promise<{ message: string; created_count: number }> => {
    const response = await apiClient.post(`${BASE_URL}/flipping/scan/`);
    return response.data;
  }
};

// Crafting Opportunities
export const craftingApi = {
  getOpportunities: async (filters?: TradingStrategyFilters): Promise<CraftingOpportunitiesResponse> => {
    const params = new URLSearchParams();
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          params.append(key, String(value));
        }
      });
    }
    
    const response = await apiClient.get(`${BASE_URL}/crafting/?${params.toString()}`);
    return response.data;
  },

  getOpportunity: async (id: number): Promise<CraftingOpportunity> => {
    const response = await apiClient.get(`${BASE_URL}/crafting/${id}/`);
    return response.data;
  },

  // Trigger crafting opportunity scan with AI-weighted volume analysis
  scanOpportunities: async (): Promise<{ message: string; created_count: number }> => {
    const response = await apiClient.post(`${BASE_URL}/crafting/scan/`);
    return response.data;
  },

  // Get AI-weighted crafting opportunities using real-time OSRS Wiki API data
  getAIOpportunities: async (filters?: TradingStrategyFilters): Promise<CraftingOpportunitiesResponse> => {
    const params = new URLSearchParams();
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          params.append(key, String(value));
        }
      });
    }
    
    const response = await apiClient.get(`${BASE_URL}/crafting/ai_opportunities/?${params.toString()}`, {
      timeout: 60000 // 60 second timeout for real-time analysis
    });
    return response.data;
  }
};

// Set Combining Opportunities
export const setCombiningApi = {
  getOpportunities: async (filters?: TradingStrategyFilters): Promise<SetCombiningOpportunitiesResponse> => {
    const params = new URLSearchParams();
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          params.append(key, String(value));
        }
      });
    }
    
    const response = await apiClient.get(`${BASE_URL}/set-combining/?${params.toString()}`);
    return response.data;
  },

  getOpportunity: async (id: number): Promise<SetCombiningOpportunity> => {
    const response = await apiClient.get(`${BASE_URL}/set-combining/${id}/`);
    return response.data;
  },

  // Trigger set combining opportunity scan
  scanOpportunities: async (): Promise<{ message: string; created_count: number }> => {
    const response = await apiClient.post(`${BASE_URL}/set-combining/scan/`);
    return response.data;
  },

  // Get AI-powered set combining opportunities using real-time OSRS Wiki data
  getAIOpportunities: async (filters?: TradingStrategyFilters & { use_stored?: boolean }): Promise<SetCombiningOpportunitiesResponse> => {
    const params = new URLSearchParams();
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          params.append(key, String(value));
        }
      });
    }
    
    // Use stored dynamic opportunities by default for faster loading
    if (!params.has('use_stored')) {
      params.append('use_stored', 'true');
    }
    
    // Use specialized AI client with extended timeout and circuit breaker protection
    const response = await aiApiClient.get(`${BASE_URL}/set-combining/ai_opportunities/?${params.toString()}`);
    return response.data;
  }
};

// Market Condition Monitoring
export const marketConditionApi = {
  // Get latest market condition
  getLatestCondition: async (): Promise<MarketConditionSnapshot> => {
    const response = await apiClient.get(`${BASE_URL}/market-conditions/latest/`);
    return response.data;
  },

  // Get market condition history
  getConditionHistory: async (limit = 50): Promise<MarketConditionSnapshot[]> => {
    const response = await apiClient.get(`${BASE_URL}/market-conditions/?limit=${limit}`);
    return response.data.results || response.data;
  },

  // Get specific market condition
  getCondition: async (id: number): Promise<MarketConditionSnapshot> => {
    const response = await apiClient.get(`${BASE_URL}/market-conditions/${id}/`);
    return response.data;
  },

  // Trigger market condition analysis
  analyzeMarket: async (): Promise<MarketConditionSnapshot> => {
    const response = await apiClient.post(`${BASE_URL}/market-conditions/analyze/`);
    return response.data;
  },

  // Check if market is safe for trading
  isMarketSafe: async (): Promise<{ is_safe: boolean; reason?: string }> => {
    const response = await apiClient.get(`${BASE_URL}/market-conditions/is_safe/`);
    return response.data;
  }
};

// Strategy Performance Tracking
export const strategyPerformanceApi = {
  // Get performance for specific strategy
  getStrategyPerformance: async (strategyId: number): Promise<StrategyPerformance[]> => {
    const response = await apiClient.get(`${BASE_URL}/performance/?strategy_id=${strategyId}`);
    return response.data.results || response.data;
  },

  // Record strategy execution results
  recordPerformance: async (performance: Omit<StrategyPerformance, 'id' | 'timestamp' | 'success_rate' | 'profit_vs_expected'>): Promise<StrategyPerformance> => {
    const response = await apiClient.post(`${BASE_URL}/performance/`, performance);
    return response.data;
  },

  // Get performance analytics
  getPerformanceAnalytics: async (strategyId?: number): Promise<{
    total_executions: number;
    successful_executions: number;
    total_profit: number;
    average_accuracy: number;
    success_rate: number;
    best_performing_strategy: string;
  }> => {
    const params = strategyId ? `?strategy_id=${strategyId}` : '';
    const response = await apiClient.get(`${BASE_URL}/performance/analytics/${params}`);
    return response.data;
  }
};

// Dashboard Data
export const dashboardApi = {
  // Get comprehensive dashboard data
  getDashboardData: async (): Promise<StrategyDashboardData> => {
    const response = await apiClient.get(`${BASE_URL}/dashboard/`);
    return response.data;
  },

  // Get strategy summary stats
  getStrategySummary: async (): Promise<{
    total_strategies: number;
    active_strategies: number;
    total_profit_potential: number;
    average_roi: number;
  }> => {
    const response = await apiClient.get(`${BASE_URL}/dashboard/summary/`);
    return response.data;
  }
};

// Mass Operations
export const massOperationsApi = {
  // Trigger all opportunity scans
  scanAllOpportunities: async (): Promise<{
    decanting_count: number;
    flipping_count: number;
    crafting_count: number;
    set_combining_count: number;
    total_count: number;
  }> => {
    const response = await apiClient.post(`${BASE_URL}/scan_all/`);
    return response.data;
  },

  // Refresh all strategy data
  refreshStrategies: async (): Promise<{ message: string; updated_count: number }> => {
    const response = await apiClient.post(`${BASE_URL}/refresh_strategies/`);
    return response.data;
  },

  // Cleanup inactive strategies
  cleanupInactiveStrategies: async (): Promise<{ message: string; deleted_count: number }> => {
    const response = await apiClient.post(`${BASE_URL}/cleanup_inactive/`);
    return response.data;
  }
};

// Export all APIs as a single object for convenience
export const tradingStrategiesApiClient = {
  strategies: tradingStrategiesApi,
  decanting: decantingApi,
  flipping: flippingApi,
  crafting: craftingApi,
  setCombining: setCombiningApi,
  marketCondition: marketConditionApi,
  performance: strategyPerformanceApi,
  dashboard: dashboardApi,
  massOperations: massOperationsApi,
};

export default tradingStrategiesApiClient;