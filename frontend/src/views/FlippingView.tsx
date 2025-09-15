import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ArrowPathIcon,
  MagnifyingGlassIcon,
  ArrowTrendingUpIcon,
  SparklesIcon,
  ChartBarIcon,
  BoltIcon,
  FireIcon,
  EyeIcon,
  CpuChipIcon,
  RocketLaunchIcon,
  AdjustmentsHorizontalIcon,
  ClockIcon
} from '@heroicons/react/24/outline';

import { tradingStrategiesApiClient } from '../api/tradingStrategiesApi';
import { FlippingOpportunityCard } from '../components/trading/FlippingOpportunityCard';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { useReactiveTradingContext } from '../contexts/ReactiveTrading';
import type { FlippingOpportunity, TradingStrategyFilters } from '../types/tradingStrategies';
import type { PriceUpdate, MarketAlert } from '../hooks/useReactiveTradingSocket';

// Enhanced flipping view with AI-powered insights and real-time market intelligence
export function FlippingView() {
  // Core data state
  const [opportunities, setOpportunities] = useState<FlippingOpportunity[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  
  // UI state management
  const [searchTerm, setSearchTerm] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [viewMode, setViewMode] = useState<'heatmap' | 'grid'>('heatmap');
  
  // Professional trading state
  const [currentCapital, setCurrentCapital] = useState(1000000); // Default 1M GP
  const [favorites, setFavorites] = useState<Set<number>>(new Set());
  
  // Advanced filter state - increased page_size for more results
  const [filters, setFilters] = useState<TradingStrategyFilters>({
    is_active: true,
    page_size: 500 // Increased from 100 to show more opportunities
  });
  
  const [advancedFilters, setAdvancedFilters] = useState({
    minConfidence: 0,
    maxRisk: 'high' as 'low' | 'medium' | 'high',
    minVolume: 0,
    maxFlipTime: 120, // minutes
    sortBy: 'ai_score' as 'profit' | 'margin' | 'stability' | 'volume' | 'ai_score' | 'competition',
    showOnlyFavorites: false,
    capitalRange: 'all' as 'all' | 'low' | 'medium' | 'high'
  });

  // Enhanced statistics
  const [stats, setStats] = useState({
    totalOpportunities: 0,
    avgMargin: 0,
    totalPotentialProfit: 0,
    avgStability: 0,
    avgConfidence: 0,
    highVolumeCount: 0,
    lowRiskCount: 0,
    fastFlipCount: 0
  });
  
  // Real-time intelligence
  const { state: socketState, actions: socketActions } = useReactiveTradingContext();
  const [websocketError, setWebsocketError] = useState<string | null>(null);
  const [lastConnectionAttempt, setLastConnectionAttempt] = useState<Date | null>(null);

  // Enhanced data fetching with AI insights
  const fetchFlippingOpportunities = async (showRefreshSpinner = false) => {
    if (showRefreshSpinner) setRefreshing(true);
    setLoading(true);

    try {
      const response = await tradingStrategiesApiClient.flipping.getOpportunities({
        ...filters,
        ordering: getApiOrdering(advancedFilters.sortBy)
      });
      
      let enhancedOpportunities = response.results.map(opp => ({
        ...opp,
        // Calculate AI confidence score based on multiple factors
        aiConfidence: calculateAIConfidence(opp),
        // Calculate competition level
        competitionLevel: calculateCompetitionLevel(opp),
        // Enhanced risk assessment
        riskScore: calculateRiskScore(opp),
        // Volume quality score
        volumeQuality: calculateVolumeQuality(opp)
      }));

      // Apply client-side filtering
      enhancedOpportunities = applyAdvancedFiltering(enhancedOpportunities);
      
      setOpportunities(enhancedOpportunities);
      calculateEnhancedStats(enhancedOpportunities);
      
    } catch (error) {
      console.error('Error fetching flipping opportunities:', error);
      setWebsocketError(error instanceof Error ? error.message : 'Failed to fetch opportunities');
      setOpportunities([]);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  // Helper functions for AI calculations
  const calculateAIConfidence = (opp: FlippingOpportunity): number => {
    const volumeScore = Math.min((opp.buy_volume + opp.sell_volume) / 10000, 1) * 25;
    const stabilityScore = (typeof opp.price_stability === 'string' 
      ? parseFloat(opp.price_stability) 
      : opp.price_stability) * 25;
    const marginScore = Math.min(parseFloat(opp.margin_percentage.toString()) / 10, 1) * 25;
    const timeScore = Math.max(25 - (opp.estimated_flip_time_minutes / 10), 0);
    
    return Math.round(volumeScore + stabilityScore + marginScore + timeScore);
  };
  
  const calculateCompetitionLevel = (opp: FlippingOpportunity): 'low' | 'medium' | 'high' => {
    const totalVolume = opp.buy_volume + opp.sell_volume;
    const margin = parseFloat(opp.margin_percentage.toString());
    
    if (totalVolume > 50000 && margin > 5) return 'low';
    if (totalVolume > 20000 || margin > 3) return 'medium';
    return 'high';
  };
  
  const calculateRiskScore = (opp: FlippingOpportunity): number => {
    const stability = typeof opp.price_stability === 'string' 
      ? parseFloat(opp.price_stability) 
      : opp.price_stability;
    const volume = opp.buy_volume + opp.sell_volume;
    const flipTime = opp.estimated_flip_time_minutes;
    
    let riskScore = 10; // Start with low risk
    if (stability < 0.7) riskScore -= 3;
    if (volume < 10000) riskScore -= 2;
    if (flipTime > 60) riskScore -= 2;
    
    return Math.max(0, Math.min(10, riskScore));
  };
  
  const calculateVolumeQuality = (opp: FlippingOpportunity): 'excellent' | 'good' | 'fair' | 'poor' => {
    const totalVolume = opp.buy_volume + opp.sell_volume;
    if (totalVolume > 100000) return 'excellent';
    if (totalVolume > 50000) return 'good';
    if (totalVolume > 20000) return 'fair';
    return 'poor';
  };
  
  const getApiOrdering = (sortBy: string): string => {
    switch (sortBy) {
      case 'profit': return '-total_profit_potential';
      case 'margin': return '-margin_percentage';
      case 'stability': return '-price_stability';
      case 'volume': return '-buy_volume';
      case 'ai_score': return '-total_profit_potential'; // Default to profit for API
      default: return '-total_profit_potential';
    }
  };
  
  const applyAdvancedFiltering = (opportunities: any[]): any[] => {
    return opportunities.filter(opp => {
      // Confidence filter
      if (opp.aiConfidence < advancedFilters.minConfidence) return false;
      
      // Volume filter
      const totalVolume = opp.buy_volume + opp.sell_volume;
      if (totalVolume < advancedFilters.minVolume) return false;
      
      // Flip time filter
      if (opp.estimated_flip_time_minutes > advancedFilters.maxFlipTime) return false;
      
      // Favorites filter
      if (advancedFilters.showOnlyFavorites && !favorites.has(opp.item_id)) return false;
      
      // Capital range filter
      if (advancedFilters.capitalRange !== 'all') {
        const requiredCapital = opp.buy_price * opp.recommended_quantity;
        switch (advancedFilters.capitalRange) {
          case 'low':
            if (requiredCapital > 100000) return false;
            break;
          case 'medium':
            if (requiredCapital < 100000 || requiredCapital > 1000000) return false;
            break;
          case 'high':
            if (requiredCapital < 1000000) return false;
            break;
        }
      }
      
      return true;
    });
  };
  
  const calculateEnhancedStats = (opportunities: any[]) => {
    if (opportunities.length === 0) {
      setStats({
        totalOpportunities: 0,
        avgMargin: 0,
        totalPotentialProfit: 0,
        avgStability: 0,
        avgConfidence: 0,
        highVolumeCount: 0,
        lowRiskCount: 0,
        fastFlipCount: 0
      });
      return;
    }
    
    const totalOpportunities = opportunities.length;
    const avgMargin = opportunities.reduce((sum, opp) => sum + parseFloat(opp.margin_percentage.toString()), 0) / totalOpportunities;
    const totalPotentialProfit = opportunities.reduce((sum, opp) => sum + opp.total_profit_potential, 0);
    const avgStability = opportunities.reduce((sum, opp) => {
      const stability = typeof opp.price_stability === 'string' 
        ? parseFloat(opp.price_stability) 
        : opp.price_stability;
      return sum + stability;
    }, 0) / totalOpportunities;
    const avgConfidence = opportunities.reduce((sum, opp) => sum + opp.aiConfidence, 0) / totalOpportunities;
    const highVolumeCount = opportunities.filter(opp => (opp.buy_volume + opp.sell_volume) > 50000).length;
    const lowRiskCount = opportunities.filter(opp => opp.riskScore >= 7).length;
    const fastFlipCount = opportunities.filter(opp => opp.estimated_flip_time_minutes <= 30).length;
    
    setStats({
      totalOpportunities,
      avgMargin,
      totalPotentialProfit,
      avgStability,
      avgConfidence,
      highVolumeCount,
      lowRiskCount,
      fastFlipCount
    });
  };

  // Memoize fetchFlippingOpportunities to prevent infinite loops
  const memoizedFetchOpportunities = useCallback(() => {
    fetchFlippingOpportunities();
  }, [filters.is_active, filters.page_size, advancedFilters.sortBy, advancedFilters.minConfidence, advancedFilters.minVolume, advancedFilters.maxFlipTime, advancedFilters.showOnlyFavorites, advancedFilters.capitalRange]);

  // Effects
  useEffect(() => {
    memoizedFetchOpportunities();
  }, [memoizedFetchOpportunities]);

  // Memoize WebSocket actions to prevent re-renders
  const handleWebSocketConnection = useCallback(() => {
    if (socketState?.isConnected) {
      console.log('🔌 WebSocket connected, subscribing to flipping route...');
      socketActions.subscribeToRoute('flipping');
      socketActions.getCurrentRecommendations('flipping');
      socketActions.getMarketAlerts();
      setLastConnectionAttempt(new Date());
      setWebsocketError(null);
    } else if (socketState?.error) {
      setWebsocketError(socketState.error);
    }
  }, [socketState?.isConnected, socketState?.error, socketActions.subscribeToRoute, socketActions.getCurrentRecommendations, socketActions.getMarketAlerts]);

  // WebSocket integration for real-time updates
  useEffect(() => {
    handleWebSocketConnection();
  }, [handleWebSocketConnection]);
  
  // Memoize item IDs to prevent infinite re-renders
  const currentItemIds = useMemo(() => {
    return opportunities.map(opp => opp.item_id.toString()).filter(Boolean);
  }, [opportunities]);

  const uniqueItemIds = useMemo(() => {
    return [...new Set(currentItemIds)];
  }, [currentItemIds]);

  // Subscribe to individual item updates when opportunities change
  useEffect(() => {
    if (!socketState?.isConnected || uniqueItemIds.length === 0) {
      return;
    }

    console.log(`📡 Batch subscribing to ${uniqueItemIds.length} flipping items`);
    
    // Add a debounced delay to prevent rapid subscription changes
    const timeoutId = setTimeout(() => {
      uniqueItemIds.forEach(itemId => {
        socketActions.subscribeToItem(itemId);
      });
    }, 1000); // Increased delay to prevent rapid re-subscriptions
    
    return () => {
      clearTimeout(timeoutId);
      // Add delay before unsubscribing to prevent conflicts
      const cleanupTimeoutId = setTimeout(() => {
        if (socketState?.isConnected) {
          uniqueItemIds.forEach(itemId => {
            socketActions.unsubscribeFromItem(itemId);
          });
        }
      }, 100);
      
      // Store cleanup timeout for potential cancellation
      return () => clearTimeout(cleanupTimeoutId);
    };
  }, [socketState?.isConnected, uniqueItemIds.join(','), socketActions.subscribeToItem, socketActions.unsubscribeFromItem]);
  
  // Memoize price updates to prevent unnecessary re-renders
  const priceUpdates = useMemo(() => {
    return Object.values(socketState?.priceUpdates || {});
  }, [socketState?.priceUpdates]);

  const priceUpdatesString = useMemo(() => {
    return priceUpdates.map(u => `${u.item_id}:${u.timestamp}`).join(',');
  }, [priceUpdates]);

  // Handle real-time price updates
  useEffect(() => {
    if (priceUpdates.length === 0) return;

    setOpportunities(prevOpportunities => {
      const updatedOpportunities = [...prevOpportunities];
      let hasChanges = false;
      
      priceUpdates.forEach((priceUpdate: PriceUpdate) => {
        const oppIndex = updatedOpportunities.findIndex(opp => opp.item_id === priceUpdate.item_id);
        if (oppIndex !== -1) {
          const currentPrice = (priceUpdate.high_price + priceUpdate.low_price) / 2;
          const oldPrice = updatedOpportunities[oppIndex].buy_price || 0;
          const priceChangePercent = Math.abs((currentPrice - oldPrice) / oldPrice * 100);
          
          // Update if significant change (>2%)
          if (priceChangePercent > 2 || oldPrice === 0) {
            updatedOpportunities[oppIndex] = {
              ...updatedOpportunities[oppIndex],
              buy_price: priceUpdate.low_price,
              sell_price: priceUpdate.high_price,
              margin: priceUpdate.high_price - priceUpdate.low_price,
              margin_percentage: ((priceUpdate.high_price - priceUpdate.low_price) / priceUpdate.low_price * 100).toFixed(2),
              buy_volume: priceUpdate.low_volume,
              sell_volume: priceUpdate.high_volume,
              // Recalculate AI metrics
              aiConfidence: calculateAIConfidence({
                ...updatedOpportunities[oppIndex],
                buy_price: priceUpdate.low_price,
                sell_price: priceUpdate.high_price,
                buy_volume: priceUpdate.low_volume,
                sell_volume: priceUpdate.high_volume
              })
            };
            hasChanges = true;
          }
        }
      });
      
      return hasChanges ? updatedOpportunities : prevOpportunities;
    });
  }, [priceUpdatesString]);

  const handleRefresh = async () => {
    try {
      await tradingStrategiesApiClient.flipping.scanOpportunities();
      await fetchFlippingOpportunities(true);
    } catch (error) {
      console.error('Error refreshing flipping data:', error);
      setWebsocketError(error instanceof Error ? error.message : 'Failed to refresh data');
    }
  };
  
  // Advanced filter handlers
  const handleFilterChange = (key: string, value: any) => {
    setAdvancedFilters(prev => ({ ...prev, [key]: value }));
  };
  
  const toggleFavorite = (itemId: number) => {
    setFavorites(prev => {
      const newFavorites = new Set(prev);
      if (newFavorites.has(itemId)) {
        newFavorites.delete(itemId);
      } else {
        newFavorites.add(itemId);
      }
      return newFavorites;
    });
  };

  // Enhanced filtering with search
  const filteredAndSortedOpportunities = useMemo(() => {
    let filtered = opportunities.filter(opp =>
      searchTerm === '' ||
      opp.item_name.toLowerCase().includes(searchTerm.toLowerCase())
    );
    
    // Apply advanced sorting
    return filtered.sort((a, b) => {
      switch (advancedFilters.sortBy) {
        case 'profit':
          return b.total_profit_potential - a.total_profit_potential;
        case 'margin':
          const aMargin = parseFloat(a.margin_percentage.toString());
          const bMargin = parseFloat(b.margin_percentage.toString());
          return bMargin - aMargin;
        case 'stability':
          const aStability = typeof a.price_stability === 'string' 
            ? parseFloat(a.price_stability) 
            : a.price_stability;
          const bStability = typeof b.price_stability === 'string' 
            ? parseFloat(b.price_stability) 
            : b.price_stability;
          return bStability - aStability;
        case 'volume':
          return (b.buy_volume + b.sell_volume) - (a.buy_volume + a.sell_volume);
        case 'ai_score':
          return (b as any).aiConfidence - (a as any).aiConfidence;
        case 'competition':
          // Low competition is better
          const aComp = (a as any).competitionLevel;
          const bComp = (b as any).competitionLevel;
          const compMap = { 'low': 3, 'medium': 2, 'high': 1 };
          return (compMap[bComp] || 1) - (compMap[aComp] || 1);
        default:
          return b.total_profit_potential - a.total_profit_potential;
      }
    });
  }, [opportunities, searchTerm, advancedFilters.sortBy]);
  
  // Get heat map intensity for visual effects
  const getHeatMapIntensity = (opp: any): number => {
    const volumeScore = Math.min((opp.buy_volume + opp.sell_volume) / 100000, 1);
    const confidenceScore = opp.aiConfidence / 100;
    const marginScore = Math.min(parseFloat(opp.margin_percentage.toString()) / 20, 1);
    
    return (volumeScore + confidenceScore + marginScore) / 3;
  };
  
  // Get dynamic color based on opportunity quality
  const getOpportunityColor = (opp: any): string => {
    const intensity = getHeatMapIntensity(opp);
    if (intensity > 0.8) return 'from-green-500/20 to-emerald-500/30 border-green-400/50';
    if (intensity > 0.6) return 'from-yellow-500/20 to-orange-500/30 border-yellow-400/50';
    if (intensity > 0.4) return 'from-blue-500/20 to-purple-500/30 border-blue-400/50';
    return 'from-gray-500/20 to-gray-600/30 border-gray-400/50';
  };

  // Enhanced formatting functions
  const formatGP = (amount: number): string => {
    if (amount >= 1000000) {
      return `${(amount / 1000000).toFixed(1)}M`;
    } else if (amount >= 1000) {
      return `${(amount / 1000).toFixed(1)}K`;
    }
    return Math.round(amount).toLocaleString();
  };

  const formatPercentage = (value: number | string): string => {
    const numValue = typeof value === 'string' ? parseFloat(value) : value;
    return `${numValue.toFixed(1)}%`;
  };
  
  const getVolumeQualityColor = (quality: string): string => {
    switch (quality) {
      case 'excellent': return 'text-green-400 bg-green-400/10';
      case 'good': return 'text-blue-400 bg-blue-400/10';
      case 'fair': return 'text-yellow-400 bg-yellow-400/10';
      case 'poor': return 'text-red-400 bg-red-400/10';
      default: return 'text-gray-400 bg-gray-400/10';
    }
  };
  
  const getCompetitionColor = (level: string): string => {
    switch (level) {
      case 'low': return 'text-green-400 bg-green-400/10 border-green-400/30';
      case 'medium': return 'text-yellow-400 bg-yellow-400/10 border-yellow-400/30';
      case 'high': return 'text-red-400 bg-red-400/10 border-red-400/30';
      default: return 'text-gray-400 bg-gray-400/10 border-gray-400/30';
    }
  };

  if (loading && !refreshing) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 p-6">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-center py-20">
            <div className="text-center">
              <LoadingSpinner size="lg" />
              <p className="text-gray-400 mt-4">Loading AI-powered flipping opportunities...</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 p-6">
      <div className="max-w-7xl mx-auto space-y-8">
        
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center"
        >
          <div className="flex items-center justify-center gap-3 mb-4">
            <div className="p-3 bg-purple-400/10 rounded-xl">
              <ArrowTrendingUpIcon className="w-8 h-8 text-purple-400" />
            </div>
            <h1 className="text-4xl font-bold text-gradient">
              Item Flipping Opportunities
            </h1>
          </div>
          <p className="text-xl text-gray-400 max-w-2xl mx-auto">
            Buy low, sell high with the most profitable Grand Exchange flips
          </p>
        </motion.div>

        {/* Stats Overview */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="grid grid-cols-2 md:grid-cols-4 gap-4"
        >
          <div className="bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6 text-center">
            <div className="text-2xl font-bold text-purple-400 mb-1">{stats.totalOpportunities}</div>
            <div className="text-sm text-gray-400">Active Opportunities</div>
          </div>
          <div className="bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6 text-center">
            <div className="text-2xl font-bold text-green-400 mb-1">{formatPercentage(stats.avgMargin)}</div>
            <div className="text-sm text-gray-400">Avg Margin</div>
          </div>
          <div className="bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6 text-center">
            <div className="text-2xl font-bold text-emerald-400 mb-1">{formatGP(stats.totalPotentialProfit)}</div>
            <div className="text-sm text-gray-400">Total Potential</div>
          </div>
          <div className="bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6 text-center">
            <div className="text-2xl font-bold text-blue-400 mb-1">{formatPercentage(stats.avgStability)}</div>
            <div className="text-sm text-gray-400">Avg Stability</div>
          </div>
        </motion.div>

        {/* Controls */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6"
        >
          <div className="flex flex-col lg:flex-row gap-4 items-center justify-between">
            
            {/* Search Bar */}
            <div className="relative flex-1 max-w-md">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search items..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 bg-gray-700/50 border border-gray-600/50 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500/50 text-white placeholder-gray-400"
              />
            </div>

            {/* Filters and Actions */}
            <div className="flex gap-3 items-center">
              <select
                value={advancedFilters.sortBy}
                onChange={(e) => handleFilterChange('sortBy', e.target.value)}
                className="px-3 py-2 bg-gray-700/50 border border-gray-600/50 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-purple-500/50"
              >
                <option value="profit">Total Profit</option>
                <option value="margin">Margin %</option>
                <option value="stability">Price Stability</option>
                <option value="volume">Trading Volume</option>
              </select>

              <button
                onClick={handleRefresh}
                disabled={refreshing}
                className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:bg-purple-800 disabled:opacity-50 text-white rounded-lg transition-colors"
              >
                <ArrowPathIcon className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
                {refreshing ? 'Scanning...' : 'Scan Opportunities'}
              </button>
            </div>
          </div>
        </motion.div>

        {/* Flipping Opportunities Grid */}
        <motion.div
          key={advancedFilters.sortBy}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="grid grid-cols-1 lg:grid-cols-2 gap-6"
        >
          {filteredAndSortedOpportunities.map((opportunity) => (
            <FlippingOpportunityCard
              key={opportunity.id}
              opportunity={opportunity}
              onClick={() => console.log('View flipping opportunity:', opportunity.id)}
            />
          ))}
        </motion.div>

        {/* No Results */}
        {filteredAndSortedOpportunities.length === 0 && !loading && (
          <div className="text-center py-12">
            <div className="w-16 h-16 bg-gray-700 rounded-full flex items-center justify-center mx-auto mb-4">
              <ArrowTrendingUpIcon className="w-8 h-8 text-gray-500" />
            </div>
            <h3 className="text-lg font-semibold text-gray-400 mb-2">
              No Flipping Opportunities Found
            </h3>
            <p className="text-gray-500">
              {searchTerm ? 'Try adjusting your search terms' : 'No profitable flipping opportunities available at this time'}
            </p>
            <button
              onClick={handleRefresh}
              className="mt-4 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors"
            >
              Scan for New Opportunities
            </button>
          </div>
        )}

        {/* Market Tips */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="bg-gray-800/30 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6"
        >
          <h3 className="text-lg font-semibold text-gray-200 mb-4">📈 Flipping Tips</h3>
          <div className="grid md:grid-cols-3 gap-4 text-sm text-gray-400">
            <div>
              <strong className="text-purple-400">High Stability:</strong> Items with stable prices are safer for consistent flips
            </div>
            <div>
              <strong className="text-green-400">Volume Matters:</strong> Higher volume items flip faster but may have lower margins
            </div>
            <div>
              <strong className="text-blue-400">Margin vs Speed:</strong> Balance profit margins with flip time for optimal GP/hour
            </div>
          </div>
        </motion.div>
        
        {/* Connection Error Display */}
        {websocketError && (
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-red-900/20 border border-red-500/30 rounded-xl p-4"
          >
            <div className="flex items-center gap-3">
              <div className="w-3 h-3 rounded-full bg-red-500 animate-pulse" />
              <div className="flex-1">
                <div className="text-red-400 font-medium">Connection Issue</div>
                <div className="text-red-300 text-sm">{websocketError}</div>
                <div className="text-red-300/70 text-xs mt-1">
                  Real-time features may be limited. Data will refresh when connection is restored.
                </div>
              </div>
              <button
                onClick={() => setWebsocketError(null)}
                className="text-red-400 hover:text-red-300 transition-colors"
              >
                ×
              </button>
            </div>
          </motion.div>
        )}
        
      </div>
    </div>
  );
}

export default FlippingView;