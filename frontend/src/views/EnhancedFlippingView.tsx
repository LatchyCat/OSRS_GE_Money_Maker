import React, { useState, useEffect, useMemo } from 'react';
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
  ClockIcon,
  StarIcon
} from '@heroicons/react/24/outline';

import { tradingStrategiesApiClient } from '../api/tradingStrategiesApi';
import { FlippingOpportunityCard } from '../components/trading/FlippingOpportunityCard';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { useReactiveTradingContext } from '../contexts/ReactiveTrading';
import type { FlippingOpportunity, TradingStrategyFilters } from '../types/tradingStrategies';
import type { PriceUpdate, MarketAlert } from '../hooks/useReactiveTradingSocket';

// Enhanced flipping view with AI-powered insights and real-time market intelligence
export function EnhancedFlippingView() {
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
  
  // Advanced filter state
  const [filters, setFilters] = useState<TradingStrategyFilters>({
    is_active: true,
    page_size: 100
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

  // Effects
  useEffect(() => {
    fetchFlippingOpportunities();
  }, [filters, advancedFilters]);

  // WebSocket integration for real-time updates
  useEffect(() => {
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
  }, [socketState?.isConnected, socketActions]);
  
  // Subscribe to individual item updates when opportunities change
  useEffect(() => {
    if (socketState?.isConnected && opportunities.length > 0) {
      const itemIds = opportunities.map(opp => opp.item_id.toString()).filter(Boolean);
      const uniqueItemIds = [...new Set(itemIds)];
      
      console.log(`📡 Batch subscribing to ${uniqueItemIds.length} flipping items`);
      
      const timeoutId = setTimeout(() => {
        uniqueItemIds.forEach(itemId => {
          socketActions.subscribeToItem(itemId);
        });
      }, 200);
      
      return () => {
        clearTimeout(timeoutId);
        uniqueItemIds.forEach(itemId => {
          socketActions.unsubscribeFromItem(itemId);
        });
      };
    }
  }, [socketState?.isConnected, opportunities.map(o => o.item_id).join(','), socketActions]);
  
  // Handle real-time price updates
  useEffect(() => {
    const priceUpdates = Object.values(socketState?.priceUpdates || {});
    if (priceUpdates.length > 0) {
      setOpportunities(prevOpportunities => {
        const updatedOpportunities = [...prevOpportunities];
        
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
            }
          }
        });
        
        return updatedOpportunities;
      });
    }
  }, [socketState?.priceUpdates]);

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
            <div className="p-3 bg-gradient-to-r from-purple-600 to-pink-600 rounded-xl shadow-lg">
              <RocketLaunchIcon className="w-8 h-8 text-white" />
            </div>
            <h1 className="text-4xl font-bold bg-gradient-to-r from-purple-400 via-pink-400 to-red-400 bg-clip-text text-transparent">
              AI-Powered Flipping Intelligence
            </h1>
          </div>
          <p className="text-xl text-gray-400 max-w-3xl mx-auto">
            Advanced market analysis with real-time intelligence, competition tracking, and predictive insights
          </p>
          
          {/* Real-time connection status */}
          <div className="flex items-center justify-center gap-4 mt-4">
            {socketState?.isConnected && !websocketError ? (
              <div className="flex items-center gap-2 px-3 py-1 bg-green-900/20 border border-green-500/30 rounded-full">
                <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
                <span className="text-green-400 text-sm font-medium">Live Market Intelligence</span>
              </div>
            ) : (
              <div className="flex items-center gap-2 px-3 py-1 bg-yellow-900/20 border border-yellow-500/30 rounded-full">
                <div className="w-2 h-2 rounded-full bg-yellow-400" />
                <span className="text-yellow-400 text-sm font-medium">Static Data Mode</span>
              </div>
            )}
            <div className="flex items-center gap-2 px-3 py-1 bg-purple-900/20 border border-purple-500/30 rounded-full">
              <CpuChipIcon className="w-4 h-4 text-purple-400" />
              <span className="text-purple-400 text-sm font-medium">AI Analytics Active</span>
            </div>
          </div>
        </motion.div>

        {/* Enhanced Stats Overview */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-8 gap-4"
        >
          <div className="bg-gradient-to-br from-purple-900/20 to-purple-800/20 backdrop-blur-sm border border-purple-500/30 rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-purple-400 mb-1">{stats.totalOpportunities}</div>
            <div className="text-xs text-gray-400">Total Opportunities</div>
          </div>
          <div className="bg-gradient-to-br from-green-900/20 to-emerald-800/20 backdrop-blur-sm border border-green-500/30 rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-green-400 mb-1">{formatPercentage(stats.avgMargin)}</div>
            <div className="text-xs text-gray-400">Avg Margin</div>
          </div>
          <div className="bg-gradient-to-br from-emerald-900/20 to-teal-800/20 backdrop-blur-sm border border-emerald-500/30 rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-emerald-400 mb-1">{formatGP(stats.totalPotentialProfit)}</div>
            <div className="text-xs text-gray-400">Total Potential</div>
          </div>
          <div className="bg-gradient-to-br from-blue-900/20 to-cyan-800/20 backdrop-blur-sm border border-blue-500/30 rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-blue-400 mb-1">{formatPercentage(stats.avgStability)}</div>
            <div className="text-xs text-gray-400">Avg Stability</div>
          </div>
          <div className="bg-gradient-to-br from-yellow-900/20 to-orange-800/20 backdrop-blur-sm border border-yellow-500/30 rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-yellow-400 mb-1">{Math.round(stats.avgConfidence)}</div>
            <div className="text-xs text-gray-400">AI Confidence</div>
          </div>
          <div className="bg-gradient-to-br from-indigo-900/20 to-violet-800/20 backdrop-blur-sm border border-indigo-500/30 rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-indigo-400 mb-1">{stats.highVolumeCount}</div>
            <div className="text-xs text-gray-400">High Volume</div>
          </div>
          <div className="bg-gradient-to-br from-teal-900/20 to-green-800/20 backdrop-blur-sm border border-teal-500/30 rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-teal-400 mb-1">{stats.lowRiskCount}</div>
            <div className="text-xs text-gray-400">Low Risk</div>
          </div>
          <div className="bg-gradient-to-br from-pink-900/20 to-rose-800/20 backdrop-blur-sm border border-pink-500/30 rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-pink-400 mb-1">{stats.fastFlipCount}</div>
            <div className="text-xs text-gray-400">Fast Flips</div>
          </div>
        </motion.div>

        {/* Enhanced Controls Panel */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-gradient-to-r from-gray-800/40 via-gray-800/60 to-gray-800/40 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6"
        >
          <div className="flex flex-col space-y-4">
            
            {/* Top Row: Search, View Mode, and Actions */}
            <div className="flex flex-col lg:flex-row gap-4 items-center justify-between">
              
              {/* Search Bar with AI Icon */}
              <div className="relative flex-1 max-w-md">
                <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
                <SparklesIcon className="absolute right-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-purple-400" />
                <input
                  type="text"
                  placeholder="Search items with AI insights..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full pl-10 pr-10 py-3 bg-gray-700/50 border border-gray-600/50 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500/50 text-white placeholder-gray-400"
                />
              </div>

              {/* View Mode Toggle */}
              <div className="flex items-center gap-2 bg-gray-700/30 rounded-lg p-1">
                <button
                  onClick={() => setViewMode('heatmap')}
                  className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                    viewMode === 'heatmap' 
                      ? 'bg-purple-600 text-white' 
                      : 'text-gray-400 hover:text-white'
                  }`}
                >
                  <FireIcon className="w-4 h-4 inline mr-1" />
                  Heat Map
                </button>
                <button
                  onClick={() => setViewMode('grid')}
                  className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                    viewMode === 'grid' 
                      ? 'bg-purple-600 text-white' 
                      : 'text-gray-400 hover:text-white'
                  }`}
                >
                  <ChartBarIcon className="w-4 h-4 inline mr-1" />
                  Grid View
                </button>
              </div>
              
              {/* Actions */}
              <div className="flex gap-3 items-center">
                <button
                  onClick={() => setShowFilters(!showFilters)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    showFilters 
                      ? 'bg-blue-600 text-white' 
                      : 'bg-gray-700/50 text-gray-300 hover:bg-gray-600/50'
                  }`}
                >
                  <AdjustmentsHorizontalIcon className="w-4 h-4" />
                  Filters
                </button>
                
                <button
                  onClick={handleRefresh}
                  disabled={refreshing}
                  className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 disabled:from-purple-800 disabled:to-pink-800 disabled:opacity-50 text-white rounded-lg transition-all transform hover:scale-105"
                >
                  <ArrowPathIcon className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
                  {refreshing ? 'AI Scanning...' : 'Refresh Intelligence'}
                </button>
              </div>
            </div>
            
            {/* Advanced Filters Panel */}
            <AnimatePresence>
              {showFilters && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="border-t border-gray-700/50 pt-4 space-y-4"
                >
                  <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
                    
                    {/* Sort By */}
                    <div className="space-y-2">
                      <label className="text-sm font-medium text-purple-400">🔄 Sort By</label>
                      <select
                        value={advancedFilters.sortBy}
                        onChange={(e) => handleFilterChange('sortBy', e.target.value)}
                        className="w-full px-3 py-2 bg-gray-700/50 border border-gray-600/50 rounded-lg text-white text-sm focus:outline-none focus:ring-1 focus:ring-purple-500/50"
                      >
                        <option value="profit">💰 Total Profit</option>
                        <option value="margin">📈 Margin %</option>
                        <option value="stability">⚖️ Stability</option>
                        <option value="volume">📊 Volume</option>
                        <option value="ai_score">🤖 AI Score</option>
                        <option value="competition">🏆 Competition</option>
                      </select>
                    </div>
                    
                    {/* Min Confidence */}
                    <div className="space-y-2">
                      <label className="text-sm font-medium text-yellow-400">🎯 Min AI Confidence</label>
                      <input
                        type="range"
                        min="0"
                        max="100"
                        value={advancedFilters.minConfidence}
                        onChange={(e) => handleFilterChange('minConfidence', parseInt(e.target.value))}
                        className="w-full"
                      />
                      <div className="text-xs text-gray-400 text-center">{advancedFilters.minConfidence}%</div>
                    </div>
                    
                    {/* Max Risk */}
                    <div className="space-y-2">
                      <label className="text-sm font-medium text-red-400">⚠️ Max Risk</label>
                      <select
                        value={advancedFilters.maxRisk}
                        onChange={(e) => handleFilterChange('maxRisk', e.target.value)}
                        className="w-full px-3 py-2 bg-gray-700/50 border border-gray-600/50 rounded-lg text-white text-sm focus:outline-none focus:ring-1 focus:ring-red-500/50"
                      >
                        <option value="low">🟢 Low Risk</option>
                        <option value="medium">🟡 Medium Risk</option>
                        <option value="high">🔴 High Risk</option>
                      </select>
                    </div>
                    
                    {/* Min Volume */}
                    <div className="space-y-2">
                      <label className="text-sm font-medium text-blue-400">📊 Min Volume</label>
                      <input
                        type="number"
                        placeholder="e.g. 10000"
                        value={advancedFilters.minVolume}
                        onChange={(e) => handleFilterChange('minVolume', parseInt(e.target.value) || 0)}
                        className="w-full px-3 py-2 bg-gray-700/50 border border-gray-600/50 rounded-lg text-white text-sm placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-blue-500/50"
                      />
                    </div>
                    
                    {/* Max Flip Time */}
                    <div className="space-y-2">
                      <label className="text-sm font-medium text-green-400">⏱️ Max Flip Time</label>
                      <input
                        type="number"
                        placeholder="Minutes"
                        value={advancedFilters.maxFlipTime}
                        onChange={(e) => handleFilterChange('maxFlipTime', parseInt(e.target.value) || 120)}
                        className="w-full px-3 py-2 bg-gray-700/50 border border-gray-600/50 rounded-lg text-white text-sm placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-green-500/50"
                      />
                    </div>
                    
                    {/* Capital Range */}
                    <div className="space-y-2">
                      <label className="text-sm font-medium text-orange-400">💎 Capital Range</label>
                      <select
                        value={advancedFilters.capitalRange}
                        onChange={(e) => handleFilterChange('capitalRange', e.target.value)}
                        className="w-full px-3 py-2 bg-gray-700/50 border border-gray-600/50 rounded-lg text-white text-sm focus:outline-none focus:ring-1 focus:ring-orange-500/50"
                      >
                        <option value="all">All Ranges</option>
                        <option value="low">< 100K GP</option>
                        <option value="medium">100K - 1M GP</option>
                        <option value="high">> 1M GP</option>
                      </select>
                    </div>
                    
                  </div>
                  
                  {/* Quick Filters */}
                  <div className="flex flex-wrap gap-3">
                    <label className="flex items-center space-x-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={advancedFilters.showOnlyFavorites}
                        onChange={(e) => handleFilterChange('showOnlyFavorites', e.target.checked)}
                        className="w-4 h-4 text-pink-600 bg-gray-700 border-gray-600 rounded focus:ring-pink-500"
                      />
                      <span className="text-sm text-pink-400">⭐ Show Only Favorites</span>
                    </label>
                  </div>
                  
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </motion.div>

        {/* AI Market Intelligence Dashboard (when connected) */}
        {socketState?.isConnected && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="bg-gradient-to-r from-blue-900/10 via-purple-900/20 to-pink-900/10 backdrop-blur-sm border border-blue-500/30 rounded-xl p-6"
          >
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-500/20 rounded-lg">
                  <BoltIcon className="w-6 h-6 text-blue-400" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-blue-400">🚀 Real-Time Market Intelligence</h3>
                  <p className="text-sm text-gray-400">AI-powered analysis and live market tracking</p>
                </div>
              </div>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              {/* Market Events */}
              <div className="bg-gray-800/30 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <SparklesIcon className="w-4 h-4 text-green-400" />
                  <span className="text-sm font-medium text-green-400">Market Events</span>
                  <span className="text-xs bg-green-500/20 text-green-400 px-2 py-0.5 rounded-full">
                    {socketState?.marketEvents?.length || 0}
                  </span>
                </div>
                <div className="text-xs text-gray-400">Live event tracking</div>
              </div>
              
              {/* Price Updates */}
              <div className="bg-gray-800/30 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <ArrowTrendingUpIcon className="w-4 h-4 text-blue-400" />
                  <span className="text-sm font-medium text-blue-400">Price Updates</span>
                  <span className="text-xs bg-blue-500/20 text-blue-400 px-2 py-0.5 rounded-full">
                    {Object.keys(socketState?.priceUpdates || {}).length}
                  </span>
                </div>
                <div className="text-xs text-gray-400">Real-time pricing</div>
              </div>
              
              {/* Volume Surges */}
              <div className="bg-gray-800/30 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <ChartBarIcon className="w-4 h-4 text-yellow-400" />
                  <span className="text-sm font-medium text-yellow-400">Volume Surges</span>
                  <span className="text-xs bg-yellow-500/20 text-yellow-400 px-2 py-0.5 rounded-full">
                    {socketState?.volumeSurges?.length || 0}
                  </span>
                </div>
                <div className="text-xs text-gray-400">Activity spikes</div>
              </div>
              
              {/* Market Alerts */}
              <div className="bg-gray-800/30 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <BoltIcon className="w-4 h-4 text-red-400" />
                  <span className="text-sm font-medium text-red-400">Active Alerts</span>
                  <span className="text-xs bg-red-500/20 text-red-400 px-2 py-0.5 rounded-full">
                    {(socketState?.marketAlerts || []).filter(alert => alert.is_active).length}
                  </span>
                </div>
                <div className="text-xs text-gray-400">Smart notifications</div>
              </div>
            </div>
          </motion.div>
        )}
        
        {/* Enhanced Opportunities Display */}
        <motion.div
          key={`${advancedFilters.sortBy}-${viewMode}`}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className={viewMode === 'heatmap' 
            ? "grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4" 
            : "grid grid-cols-1 lg:grid-cols-2 gap-6"}
        >
          {filteredAndSortedOpportunities.map((opportunity, index) => {
            const enhancedOpp = opportunity as any; // Type assertion for enhanced properties
            
            return (
              <motion.div
                key={opportunity.id}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: index * 0.05 }}
                className={`relative overflow-hidden rounded-xl transition-all duration-300 ${
                  viewMode === 'heatmap' 
                    ? `bg-gradient-to-br ${getOpportunityColor(enhancedOpp)} backdrop-blur-sm border hover:scale-105 cursor-pointer`
                    : ''
                }`}
                style={{
                  animation: viewMode === 'heatmap' && getHeatMapIntensity(enhancedOpp) > 0.7 
                    ? `pulse 2s infinite` 
                    : 'none'
                }}
                onClick={() => {
                  console.log('Enhanced flipping opportunity:', {
                    ...opportunity,
                    aiConfidence: enhancedOpp.aiConfidence,
                    competitionLevel: enhancedOpp.competitionLevel,
                    riskScore: enhancedOpp.riskScore,
                    volumeQuality: enhancedOpp.volumeQuality
                  });
                }}
              >
                {viewMode === 'heatmap' ? (
                  // Heat Map Card Layout
                  <div className="p-4 space-y-3">
                    {/* Header with AI indicators */}
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <h3 className="font-semibold text-gray-100 text-sm mb-1 truncate">
                          {opportunity.item_name}
                        </h3>
                        <div className="flex items-center gap-2 mb-2">
                          <div className={`px-2 py-0.5 rounded-full text-xs font-medium border ${getCompetitionColor(enhancedOpp.competitionLevel)}`}>
                            {enhancedOpp.competitionLevel.toUpperCase()}
                          </div>
                          <div className={`px-2 py-0.5 rounded-full text-xs font-medium ${getVolumeQualityColor(enhancedOpp.volumeQuality)}`}>
                            {enhancedOpp.volumeQuality.toUpperCase()}
                          </div>
                        </div>
                      </div>
                      <div className="flex flex-col items-end gap-1">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            toggleFavorite(opportunity.item_id);
                          }}
                          className={`p-1 rounded-full transition-colors ${
                            favorites.has(opportunity.item_id)
                              ? 'text-pink-400 hover:text-pink-300'
                              : 'text-gray-400 hover:text-pink-400'
                          }`}
                        >
                          <StarIcon className={`w-4 h-4 ${favorites.has(opportunity.item_id) ? 'fill-current' : ''}`} />
                        </button>
                        <div className="text-right">
                          <div className="text-xs text-gray-400">AI Score</div>
                          <div className={`text-sm font-bold ${
                            enhancedOpp.aiConfidence >= 80 ? 'text-green-400' :
                            enhancedOpp.aiConfidence >= 60 ? 'text-yellow-400' :
                            'text-red-400'
                          }`}>
                            {enhancedOpp.aiConfidence}%
                          </div>
                        </div>
                      </div>
                    </div>
                    
                    {/* Key Metrics Grid */}
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <div className="bg-gray-800/40 rounded-lg p-2 text-center">
                        <div className="text-green-400 font-bold">{formatGP(opportunity.margin)}</div>
                        <div className="text-xs text-gray-400">Margin</div>
                      </div>
                      <div className="bg-gray-800/40 rounded-lg p-2 text-center">
                        <div className="text-purple-400 font-bold">{formatPercentage(opportunity.margin_percentage)}%</div>
                        <div className="text-xs text-gray-400">%</div>
                      </div>
                      <div className="bg-gray-800/40 rounded-lg p-2 text-center">
                        <div className="text-blue-400 font-bold">{formatGP(opportunity.buy_volume + opportunity.sell_volume)}</div>
                        <div className="text-xs text-gray-400">Volume</div>
                      </div>
                      <div className="bg-gray-800/40 rounded-lg p-2 text-center">
                        <div className="text-orange-400 font-bold">{opportunity.estimated_flip_time_minutes}m</div>
                        <div className="text-xs text-gray-400">Time</div>
                      </div>
                    </div>
                    
                    {/* Risk and Stability Bar */}
                    <div className="space-y-2">
                      <div className="flex justify-between items-center">
                        <span className="text-xs text-gray-400">Risk Score</span>
                        <span className="text-xs font-medium">{enhancedOpp.riskScore}/10</span>
                      </div>
                      <div className="w-full bg-gray-700 rounded-full h-1.5">
                        <div 
                          className={`h-1.5 rounded-full transition-all ${
                            enhancedOpp.riskScore >= 7 ? 'bg-green-400' :
                            enhancedOpp.riskScore >= 5 ? 'bg-yellow-400' :
                            'bg-red-400'
                          }`}
                          style={{ width: `${enhancedOpp.riskScore * 10}%` }}
                        />
                      </div>
                    </div>
                  </div>
                ) : (
                  // Grid View - Use original FlippingOpportunityCard
                  <FlippingOpportunityCard
                    opportunity={opportunity}
                    onClick={() => {
                      console.log('Enhanced flipping opportunity:', {
                        ...opportunity,
                        aiConfidence: enhancedOpp.aiConfidence,
                        competitionLevel: enhancedOpp.competitionLevel,
                        riskScore: enhancedOpp.riskScore,
                        volumeQuality: enhancedOpp.volumeQuality
                      });
                    }}
                  />
                )}
              </motion.div>
            );
          })}
        </motion.div>

        {/* Enhanced No Results */}
        {filteredAndSortedOpportunities.length === 0 && !loading && (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-center py-16"
          >
            <div className="w-20 h-20 bg-gradient-to-r from-purple-600 to-pink-600 rounded-full flex items-center justify-center mx-auto mb-6 shadow-lg">
              <EyeIcon className="w-10 h-10 text-white" />
            </div>
            <h3 className="text-xl font-semibold text-gray-300 mb-3">
              No Opportunities Match Your Criteria
            </h3>
            <p className="text-gray-400 mb-6 max-w-md mx-auto">
              {searchTerm || showFilters ? 'Try adjusting your search terms or filters to discover more opportunities' : 'AI is analyzing market conditions for new profitable flipping opportunities'}
            </p>
            <div className="flex flex-col sm:flex-row gap-3 items-center justify-center">
              {(searchTerm || showFilters) && (
                <button
                  onClick={() => {
                    setSearchTerm('');
                    setAdvancedFilters({
                      minConfidence: 0,
                      maxRisk: 'high',
                      minVolume: 0,
                      maxFlipTime: 120,
                      sortBy: 'ai_score',
                      showOnlyFavorites: false,
                      capitalRange: 'all'
                    });
                    setShowFilters(false);
                  }}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
                >
                  Clear Filters
                </button>
              )}
              <button
                onClick={handleRefresh}
                className="px-4 py-2 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white rounded-lg transition-all transform hover:scale-105"
              >
                <SparklesIcon className="w-4 h-4 inline mr-2" />
                Refresh AI Analysis
              </button>
            </div>
          </motion.div>
        )}

        {/* Enhanced AI Insights Panel */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="bg-gradient-to-r from-gray-800/20 via-gray-800/40 to-gray-800/20 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6"
        >
          <div className="flex items-center gap-3 mb-6">
            <div className="p-2 bg-gradient-to-r from-purple-600 to-pink-600 rounded-lg">
              <CpuChipIcon className="w-6 h-6 text-white" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-200">🤖 AI Trading Intelligence</h3>
              <p className="text-sm text-gray-400">Advanced insights and market analysis</p>
            </div>
          </div>
          
          <div className="grid md:grid-cols-3 lg:grid-cols-5 gap-4 text-sm">
            <div className="bg-purple-900/20 border border-purple-500/30 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <SparklesIcon className="w-4 h-4 text-purple-400" />
                <strong className="text-purple-400">AI Confidence</strong>
              </div>
              <p className="text-gray-400">Our AI analyzes volume, stability, and timing to provide confidence scores for each opportunity.</p>
            </div>
            
            <div className="bg-yellow-900/20 border border-yellow-500/30 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <ChartBarIcon className="w-4 h-4 text-yellow-400" />
                <strong className="text-yellow-400">Volume Quality</strong>
              </div>
              <p className="text-gray-400">Items are rated on trading volume quality to predict flip speed and reliability.</p>
            </div>
            
            <div className="bg-red-900/20 border border-red-500/30 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <BoltIcon className="w-4 h-4 text-red-400" />
                <strong className="text-red-400">Competition Analysis</strong>
              </div>
              <p className="text-gray-400">Real-time tracking of market competition levels to find less contested opportunities.</p>
            </div>
            
            <div className="bg-green-900/20 border border-green-500/30 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <FireIcon className="w-4 h-4 text-green-400" />
                <strong className="text-green-400">Heat Map View</strong>
              </div>
              <p className="text-gray-400">Visual intensity shows the hottest opportunities with pulsing animations for high-activity items.</p>
            </div>
            
            <div className="bg-blue-900/20 border border-blue-500/30 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <RocketLaunchIcon className="w-4 h-4 text-blue-400" />
                <strong className="text-blue-400">Real-Time Updates</strong>
              </div>
              <p className="text-gray-400">Live price updates and market events keep your opportunities current and accurate.</p>
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

export default EnhancedFlippingView;