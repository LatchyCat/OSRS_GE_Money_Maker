import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ArrowPathIcon,
  MagnifyingGlassIcon,
  AdjustmentsHorizontalIcon,
  ChatBubbleLeftRightIcon,
  ChartBarIcon,
  SparklesIcon,
  BoltIcon,
  StarIcon,
  EyeIcon,
  ClockIcon,
  ChevronDownIcon
} from '@heroicons/react/24/outline';
import { Shield, Sparkles, TrendingUp, Package, Timer, Zap } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

import { setCombiningApi } from '../api/tradingStrategiesApi';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { SetCombiningOpportunityCard } from '../components/trading/SetCombiningOpportunityCard';
import { SetCombiningLiveProfitDashboard } from '../components/trading/SetCombiningLiveProfitDashboard';
import { AISetCombiningAssistant } from '../components/ai/AISetCombiningAssistant';
import { SetCombiningCalculatorModal } from '../components/trading/SetCombiningCalculatorModal';
import { useReactiveTradingContext } from '../contexts/ReactiveTrading';
import type { SetCombiningOpportunity } from '../types/tradingStrategies';
import type { PriceUpdate } from '../hooks/useReactiveTradingSocket';

interface SetCombiningFilters {
  search: string;
  minProfit: number;
  maxProfit: string;
  minVolumeScore: number;
  sortBy: 'lazy_tax_profit' | 'profit_margin_pct' | 'volume_score' | 'confidence_score';
  dataSource: 'ai_opportunities' | 'database';
  setType: string; // 'all', 'barrows', 'god_wars', 'elite_void', 'achievement_diary', 'quest_rewards'
  pieceCount: string; // 'all', '3', '4', '5+'
  dataFreshness: string; // 'all', '1h', '6h', '24h'
  riskLevel: string; // 'all', 'low', 'medium', 'high'
  onlyFavorites: boolean;
  minCapital: string;
  maxCapital: string;
  volumeFilter: string; // 'all', 'high', 'medium', 'low'
  profitabilityOnly: boolean;
}

interface SetCombiningStats {
  totalOpportunities: number;
  avgLazyTaxProfit: number;
  avgVolumeScore: number;
  bestProfitPerHour: number;
  highConfidenceCount: number;
}

export function SetCombiningView() {
  const [opportunities, setOpportunities] = useState<SetCombiningOpportunity[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [filters, setFilters] = useState<SetCombiningFilters>({
    search: '',
    minProfit: 1000,
    maxProfit: '',
    minVolumeScore: 0.0,
    sortBy: 'lazy_tax_profit',
    dataSource: 'ai_opportunities',
    setType: 'all',
    pieceCount: 'all',
    dataFreshness: 'all',
    riskLevel: 'all',
    onlyFavorites: false,
    minCapital: '',
    maxCapital: '',
    volumeFilter: 'all',
    profitabilityOnly: true
  });

  // WebSocket and real-time state
  const { state: socketState, actions: socketActions } = useReactiveTradingContext();
  const [lastConnectionAttempt, setLastConnectionAttempt] = useState<Date | null>(null);
  const [websocketError, setWebsocketError] = useState<string | null>(null);

  // UI state
  const [showFilters, setShowFilters] = useState(false);
  const [selectedItemForChart, setSelectedItemForChart] = useState<number | null>(null);
  const [showAIAssistant, setShowAIAssistant] = useState(false);
  const [showReactiveFeatures, setShowReactiveFeatures] = useState(true);
  
  // Professional trading state
  const [currentCapital, setCurrentCapital] = useState(100000000); // Default 100M GP for high-value opportunities
  const [favorites, setFavorites] = useState<Set<number>>(new Set());
  const [selectedOpportunityForCalculator, setSelectedOpportunityForCalculator] = useState<SetCombiningOpportunity | null>(null);
  const [selectedOpportunityForQuickTrade, setSelectedOpportunityForQuickTrade] = useState<SetCombiningOpportunity | null>(null);

  const [stats, setStats] = useState<SetCombiningStats>({
    totalOpportunities: 0,
    avgLazyTaxProfit: 0,
    avgVolumeScore: 0,
    bestProfitPerHour: 0,
    highConfidenceCount: 0
  });

  const [metadata, setMetadata] = useState({
    data_source: '',
    pricing_source: '',
    features: [] as string[]
  });

  const fetchSetCombiningData = async (showRefreshSpinner = false) => {
    if (showRefreshSpinner) setRefreshing(true);
    setLoading(true);

    try {
      let response;
      const apiFilters = {
        min_profit: filters.minProfit,
        min_volume_score: filters.minVolumeScore,
        page_size: 50,
        use_stored: true,
        capital_available: currentCapital || 100_000_000  // Use current capital or default to 100M GP
      };

      if (filters.dataSource === 'ai_opportunities') {
        response = await setCombiningApi.getAIOpportunities(apiFilters);
      } else {
        response = await setCombiningApi.getOpportunities(apiFilters);
      }

      // Log successful data fetch for debugging
      console.log(`✅ Fetched ${response.results?.length || 0} set combining opportunities`);

      setOpportunities(response.results || []);
      
      // Set metadata if available
      if (response.data_source) {
        setMetadata({
          data_source: response.data_source,
          pricing_source: response.pricing_source || 'database',
          features: response.features || []
        });
      }

      // Calculate stats
      calculateStats(response.results || [], response.metadata);
    } catch (error) {
      console.error('Error fetching set combining data:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const calculateStats = (opportunities: SetCombiningOpportunity[], apiMetadata?: any) => {
    if (opportunities.length === 0) {
      setStats({
        totalOpportunities: 0,
        avgLazyTaxProfit: 0,
        avgVolumeScore: 0,
        bestProfitPerHour: 0,
        highConfidenceCount: 0
      });
      return;
    }

    // Use API metadata if available (for AI opportunities)
    if (apiMetadata) {
      setStats({
        totalOpportunities: opportunities.length,
        avgLazyTaxProfit: opportunities.reduce((sum, opp) => sum + (opp.lazy_tax_profit || 0), 0) / opportunities.length,
        avgVolumeScore: apiMetadata.avg_volume_score || 0,
        bestProfitPerHour: Math.max(...opportunities.map(opp => 
          ((opp as any).estimated_sets_per_hour || 6) * opp.lazy_tax_profit
        )),
        highConfidenceCount: apiMetadata.high_confidence_count || 0
      });
    } else {
      // Calculate from opportunities directly
      const avgLazyTaxProfit = opportunities.reduce((sum, opp) => sum + (opp.lazy_tax_profit || 0), 0) / opportunities.length;
      const bestProfitPerHour = Math.max(...opportunities.map(opp => 
        Math.min(12, opp.set_volume || 6) * opp.lazy_tax_profit
      ));
      
      setStats({
        totalOpportunities: opportunities.length,
        avgLazyTaxProfit: Math.round(avgLazyTaxProfit),
        avgVolumeScore: 0.5, // Default for database opportunities
        bestProfitPerHour: Math.round(bestProfitPerHour),
        highConfidenceCount: opportunities.filter(opp => (opp.profit_margin_pct || 0) > 10).length
      });
    }
  };

  // WebSocket subscription for set-combining route
  useEffect(() => {
    if (!socketState?.isConnected || !socketActions) {
      console.log('🚫 WebSocket not ready for set-combining subscription:', {
        connected: socketState?.isConnected,
        hasActions: !!socketActions
      });
      return;
    }

    console.log('🔌 WebSocket connected, subscribing to set-combining route...');
    
    try {
      const subscribeToRouteStable = socketActions.subscribeToRoute;
      const getCurrentRecommendationsStable = socketActions.getCurrentRecommendations;
      const getMarketAlertsStable = socketActions.getMarketAlerts;
      
      if (subscribeToRouteStable) {
        subscribeToRouteStable('set-combining');
      }
      if (getCurrentRecommendationsStable) {
        getCurrentRecommendationsStable('set-combining');
      }
      if (getMarketAlertsStable) {
        getMarketAlertsStable();
      }
      
      setLastConnectionAttempt(new Date());
      setWebsocketError(null);
    } catch (error) {
      console.error('❌ Error during WebSocket set-combining subscription setup:', error);
      setWebsocketError(error instanceof Error ? error.message : 'Subscription setup failed');
    }

    return () => {
      console.log('🧹 Cleaning up set-combining subscription');
    };
  }, [socketState?.isConnected]);

  // Handle WebSocket errors separately
  useEffect(() => {
    if (socketState?.error) {
      setWebsocketError(socketState.error);
    }
  }, [socketState?.error]);

  // Subscribe to specific items when opportunities change
  const currentItemIds = useMemo(() => {
    return opportunities
      .filter(opp => opp.set_item_id)
      .map(opp => opp.set_item_id.toString())
      .filter(Boolean);
  }, [opportunities]);

  const uniqueItemIds = useMemo(() => {
    return [...new Set(currentItemIds)];
  }, [currentItemIds]);

  const stableSubscribeToItem = useCallback(
    (itemId: string) => socketActions?.subscribeToItem?.(itemId),
    [socketActions?.subscribeToItem]
  );

  const stableUnsubscribeFromItem = useCallback(
    (itemId: string) => socketActions?.unsubscribeFromItem?.(itemId),
    [socketActions?.unsubscribeFromItem]
  );

  useEffect(() => {
    if (!socketState?.isConnected || uniqueItemIds.length === 0) {
      return;
    }

    console.log(`📡 Batch subscribing to ${uniqueItemIds.length} set items`);
    
    const timeoutId = setTimeout(() => {
      uniqueItemIds.forEach(itemId => {
        stableSubscribeToItem(itemId);
      });
    }, 1000);
    
    return () => {
      clearTimeout(timeoutId);
      if (socketState?.isConnected) {
        uniqueItemIds.forEach(itemId => {
          stableUnsubscribeFromItem(itemId);
        });
      }
    };
  }, [socketState?.isConnected, uniqueItemIds.join(','), stableSubscribeToItem, stableUnsubscribeFromItem]);

  // Handle real-time price updates
  const priceUpdates = useMemo(() => {
    return Object.values(socketState?.priceUpdates || {});
  }, [socketState?.priceUpdates]);

  useEffect(() => {
    if (priceUpdates.length === 0) return;

    setOpportunities(prevOpportunities => {
      const updatedOpportunities = [...prevOpportunities];
      let hasChanges = false;
      
      priceUpdates.forEach((priceUpdate: PriceUpdate) => {
        const oppIndex = updatedOpportunities.findIndex(opp => opp.set_item_id === priceUpdate.item_id);
        if (oppIndex !== -1) {
          const currentPrice = (priceUpdate.high_price + priceUpdate.low_price) / 2;
          const oldPrice = updatedOpportunities[oppIndex].complete_set_price || 0;
          const priceChangePercent = Math.abs((currentPrice - oldPrice) / oldPrice * 100);
          
          // Update if significant change (>2%)
          if (priceChangePercent > 2 || oldPrice === 0) {
            updatedOpportunities[oppIndex] = {
              ...updatedOpportunities[oppIndex],
              complete_set_price: priceUpdate.low_price,
              // Recalculate profit with new price
              lazy_tax_profit: Math.max(0, 
                updatedOpportunities[oppIndex].individual_pieces_total_cost - priceUpdate.low_price
              ),
              last_updated: new Date().toISOString()
            };
            hasChanges = true;
          }
        }
      });
      
      return hasChanges ? updatedOpportunities : prevOpportunities;
    });
  }, [priceUpdates]);

  // Data fetching with dependencies
  useEffect(() => {
    fetchSetCombiningData(true);
  }, [filters.minProfit, filters.minVolumeScore, filters.dataSource]);

  const handleRefresh = async () => {
    await fetchSetCombiningData(true);
  };

  const formatGP = (amount: number) => {
    if (amount >= 1000000) {
      return `${(amount / 1000000).toFixed(1)}M`;
    } else if (amount >= 1000) {
      return `${(amount / 1000).toFixed(1)}K`;
    }
    return Math.round(amount).toLocaleString();
  };

  // Enhanced filter and helper functions
  const handleFilterChange = (key: string, value: any) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  const clearFilters = () => {
    setFilters({
      search: '',
      minProfit: 1000,
      maxProfit: '',
      minVolumeScore: 0.3,
      sortBy: 'lazy_tax_profit',
      dataSource: 'ai_opportunities',
      setType: 'all',
      pieceCount: 'all',
      dataFreshness: 'all',
      riskLevel: 'all',
      onlyFavorites: false,
      minCapital: '',
      maxCapital: '',
      volumeFilter: 'all',
      profitabilityOnly: true
    });
  };

  const toggleFavorite = (setItemId: number) => {
    setFavorites(prev => {
      const newFavorites = new Set(prev);
      if (newFavorites.has(setItemId)) {
        newFavorites.delete(setItemId);
      } else {
        newFavorites.add(setItemId);
      }
      return newFavorites;
    });
  };

  const handleItemClick = (opportunity: SetCombiningOpportunity) => {
    console.log('Set combining opportunity clicked:', opportunity.set_name);
    // Could open detailed view modal
  };

  // Enhanced filtering with multiple dimensions
  const getFilteredAndSortedOpportunities = () => {
    let filtered = [...opportunities];

    // Search filter
    if (filters.search) {
      const searchTerm = filters.search.toLowerCase();
      filtered = filtered.filter(opp => 
        opp.set_name.toLowerCase().includes(searchTerm) ||
        opp.piece_names.some(piece => piece.toLowerCase().includes(searchTerm))
      );
    }

    // Profit range filters
    if (filters.minProfit > 0) {
      filtered = filtered.filter(opp => opp.lazy_tax_profit >= filters.minProfit);
    }
    if (filters.maxProfit) {
      const maxProfit = parseInt(filters.maxProfit);
      filtered = filtered.filter(opp => opp.lazy_tax_profit <= maxProfit);
    }

    // Volume score filter
    if (filters.minVolumeScore > 0) {
      filtered = filtered.filter(opp => 
        (opp as any).volume_score >= filters.minVolumeScore
      );
    }

    // Set type filter
    if (filters.setType !== 'all') {
      const setTypeKeywords = {
        'barrows': ['barrows', 'dharok', 'ahrim', 'karil', 'torag', 'verac', 'guthan'],
        'god_wars': ['bandos', 'armadyl', 'saradomin', 'zamorak'],
        'elite_void': ['void', 'elite'],
        'achievement_diary': ['diary', 'achievement'],
        'quest_rewards': ['quest', 'reward']
      };
      const keywords = setTypeKeywords[filters.setType as keyof typeof setTypeKeywords] || [];
      filtered = filtered.filter(opp => 
        keywords.some(keyword => 
          opp.set_name.toLowerCase().includes(keyword)
        )
      );
    }

    // Piece count filter
    if (filters.pieceCount !== 'all') {
      const targetCount = filters.pieceCount === '5+' ? 5 : parseInt(filters.pieceCount);
      filtered = filtered.filter(opp => {
        if (filters.pieceCount === '5+') {
          return opp.piece_names.length >= targetCount;
        }
        return opp.piece_names.length === targetCount;
      });
    }

    // Data freshness filter
    if (filters.dataFreshness !== 'all' && (filtered[0] as any)?.avg_data_age_hours !== undefined) {
      const maxAge = {
        '1h': 1,
        '6h': 6,
        '24h': 24
      }[filters.dataFreshness] || 24;
      filtered = filtered.filter(opp => 
        (opp as any).avg_data_age_hours <= maxAge
      );
    }

    // Risk level filter
    if (filters.riskLevel !== 'all') {
      filtered = filtered.filter(opp => 
        ((opp as any).ai_risk_level || opp.strategy.risk_level) === filters.riskLevel
      );
    }

    // Favorites filter
    if (filters.onlyFavorites) {
      filtered = filtered.filter(opp => favorites.has(opp.set_item_id));
    }

    // Capital filters
    if (filters.minCapital) {
      const minCap = parseInt(filters.minCapital);
      filtered = filtered.filter(opp => opp.complete_set_price >= minCap);
    }
    if (filters.maxCapital) {
      const maxCap = parseInt(filters.maxCapital);
      filtered = filtered.filter(opp => opp.complete_set_price <= maxCap);
    }

    // Volume filter
    if (filters.volumeFilter !== 'all') {
      const volumeThresholds = {
        'high': 0.7,
        'medium': 0.4,
        'low': 0.1
      };
      const threshold = volumeThresholds[filters.volumeFilter as keyof typeof volumeThresholds] || 0;
      filtered = filtered.filter(opp => 
        ((opp as any).volume_score || 0) >= threshold
      );
    }

    // Profitability filter
    if (filters.profitabilityOnly) {
      filtered = filtered.filter(opp => opp.lazy_tax_profit > 0);
    }

    // Sort the results
    return filtered.sort((a, b) => {
      switch (filters.sortBy) {
        case 'lazy_tax_profit':
          return (b.lazy_tax_profit || 0) - (a.lazy_tax_profit || 0);
        case 'profit_margin_pct':
          return (b.profit_margin_pct || 0) - (a.profit_margin_pct || 0);
        case 'volume_score':
          return ((b as any).volume_score || 0) - ((a as any).volume_score || 0);
        case 'confidence_score':
          return ((b as any).confidence_score || 0) - ((a as any).confidence_score || 0);
        default:
          return (b.lazy_tax_profit || 0) - (a.lazy_tax_profit || 0);
      }
    });
  };

  const filteredOpportunities = getFilteredAndSortedOpportunities();

  if (loading && !refreshing) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 p-6">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-center py-20">
            <LoadingSpinner size="lg" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-indigo-900/20 to-gray-900 p-6">
      <div className="max-w-7xl mx-auto space-y-8">
        
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center"
        >
          <div className="flex items-center justify-center gap-3 mb-4">
            <div className="p-3 bg-indigo-400/10 rounded-xl">
              <Shield className="w-8 h-8 text-indigo-400" />
            </div>
            <h1 className="text-4xl font-bold text-gradient bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
              Set Combining Opportunities
            </h1>
          </div>
          <p className="text-xl text-gray-400 max-w-2xl mx-auto">
            AI-powered set combining opportunities with real-time OSRS Wiki pricing and volume analysis
          </p>
          {metadata.data_source && (
            <div className="mt-2 flex items-center justify-center gap-2 text-sm text-gray-500">
              <Sparkles className="w-4 h-4" />
              <span>Data: {metadata.data_source}</span>
              {metadata.pricing_source && (
                <>
                  <span>•</span>
                  <span>Pricing: {metadata.pricing_source}</span>
                </>
              )}
            </div>
          )}
        </motion.div>

        {/* WebSocket Connection Status */}
        {websocketError && (
          <motion.div 
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-red-900/20 border border-red-500/30 rounded-xl p-4"
          >
            <div className="flex items-center gap-3">
              <div className="w-3 h-3 rounded-full bg-red-500" />
              <div>
                <div className="text-red-400 font-medium">WebSocket Connection Issue</div>
                <div className="text-red-300 text-sm">{websocketError}</div>
                <div className="text-red-300/70 text-xs mt-1">
                  Real-time updates may be unavailable. Data will refresh automatically when connection is restored.
                </div>
              </div>
            </div>
          </motion.div>
        )}

        {socketState?.isConnected && !websocketError && (
          <motion.div 
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-green-900/20 border border-green-500/30 rounded-xl p-4"
          >
            <div className="flex items-center gap-3">
              <div className="w-3 h-3 rounded-full bg-green-500 animate-pulse" />
              <div>
                <div className="text-green-400 font-medium">Real-Time Intelligence Active</div>
                <div className="text-green-300 text-sm">
                  Connected to live market data • {lastConnectionAttempt && (
                    <span>Last connected: {formatDistanceToNow(lastConnectionAttempt)} ago</span>
                  )}
                </div>
              </div>
            </div>
          </motion.div>
        )}

        {/* Live Profit Dashboard */}
        <SetCombiningLiveProfitDashboard 
          opportunities={filteredOpportunities}
          currentCapital={currentCapital}
          onCapitalChange={setCurrentCapital}
        />

        {/* Stats Overview */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="grid grid-cols-1 md:grid-cols-4 gap-4"
        >
          <div className="bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6 text-center">
            <div className="text-2xl font-bold text-indigo-400 mb-1">{filteredOpportunities.length}</div>
            <div className="text-sm text-gray-400">Active Opportunities</div>
            <div className="text-xs text-gray-500 mt-1">
              {favorites.size > 0 && `${favorites.size} favorited`}
            </div>
          </div>
          <div className="bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6 text-center">
            <div className="text-2xl font-bold text-green-400 mb-1">
              {formatGP(filteredOpportunities.length > 0 ? 
                filteredOpportunities.reduce((sum, opp) => sum + opp.lazy_tax_profit, 0) / filteredOpportunities.length : 0
              )}
            </div>
            <div className="text-sm text-gray-400">Avg Profit</div>
          </div>
          <div className="bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6 text-center">
            <div className="text-2xl font-bold text-blue-400 mb-1">
              {formatGP(filteredOpportunities.length > 0 ? Math.max(...filteredOpportunities.map(opp => opp.lazy_tax_profit)) : 0)}
            </div>
            <div className="text-sm text-gray-400">Top Profit</div>
          </div>
          <div className="bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6 text-center">
            <div className="text-2xl font-bold text-purple-400 mb-1">
              {socketState?.isConnected ? (
                <div className="flex items-center justify-center gap-1">
                  <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
                  <span>LIVE</span>
                </div>
              ) : (
                <span className="text-gray-500">OFFLINE</span>
              )}
            </div>
            <div className="text-sm text-gray-400">Market Data</div>
          </div>
        </motion.div>

        {/* Controls */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6"
        >
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 mb-4">
            
            {/* Search Bar */}
            <div className="relative">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search armor sets..."
                value={filters.search}
                onChange={(e) => handleFilterChange('search', e.target.value)}
                className="w-full pl-10 pr-4 py-2 bg-gray-700/50 border border-gray-600/50 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500/50 text-white placeholder-gray-400"
              />
            </div>

            {/* Data Source */}
            <select
              value={filters.dataSource}
              onChange={(e) => handleFilterChange('dataSource', e.target.value)}
              className="px-3 py-2 bg-gray-700/50 border border-gray-600/50 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
            >
              <option value="ai_opportunities">🤖 AI Real-time</option>
              <option value="database">📊 Database</option>
            </select>

            {/* Sort By */}
            <select
              value={filters.sortBy}
              onChange={(e) => handleFilterChange('sortBy', e.target.value)}
              className="px-3 py-2 bg-gray-700/50 border border-gray-600/50 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
            >
              <option value="lazy_tax_profit">Lazy Tax Profit</option>
              <option value="profit_margin_pct">Profit Margin</option>
              <option value="volume_score">Volume Score</option>
              <option value="confidence_score">Confidence Score</option>
            </select>

            {/* Placeholder for consistency */}
            <div></div>
          </div>

          <div className="flex flex-col lg:flex-row gap-4 items-center">
            
            {/* Filters */}
            <div className="flex gap-3 items-center">
              <div className="flex items-center gap-2">
                <label className="text-sm text-gray-400">Min Profit:</label>
                <input
                  type="number"
                  min="0"
                  value={filters.minProfit}
                  onChange={(e) => handleFilterChange('minProfit', parseInt(e.target.value) || 0)}
                  className="w-20 px-2 py-1 bg-gray-700/50 border border-gray-600/50 rounded text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                />
              </div>

              {filters.dataSource === 'ai_opportunities' && (
                <div className="flex items-center gap-2">
                  <label className="text-sm text-gray-400">Min Volume Score:</label>
                  <input
                    type="number"
                    min="0"
                    max="1"
                    step="0.1"
                    value={filters.minVolumeScore}
                    onChange={(e) => handleFilterChange('minVolumeScore', parseFloat(e.target.value) || 0)}
                    className="w-16 px-2 py-1 bg-gray-700/50 border border-gray-600/50 rounded text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                  />
                </div>
              )}
            </div>

            {/* Actions */}
            <div className="flex gap-3 items-center ml-auto">
              <button
                onClick={() => setShowAIAssistant(true)}
                className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white rounded-lg transition-all duration-200 shadow-lg"
              >
                <ChatBubbleLeftRightIcon className="w-4 h-4" />
                <span className="text-sm font-medium">AI Assistant</span>
              </button>
              
              <button
                onClick={handleRefresh}
                disabled={refreshing}
                className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-800 disabled:opacity-50 text-white rounded-lg transition-colors"
              >
                <ArrowPathIcon className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
                {refreshing ? 'Refreshing...' : 'Refresh'}
              </button>
            </div>
          </div>
        </motion.div>

        {/* Set Combining Opportunities Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
        >
          <div className="flex items-center gap-3 mb-6">
            <TrendingUp className="w-6 h-6 text-indigo-400" />
            <h2 className="text-2xl font-bold text-white">Set Combining Opportunities</h2>
            {metadata.features.length > 0 && (
              <div className="flex gap-1">
                {metadata.features.map((feature, index) => (
                  <span key={index} className="px-2 py-1 bg-indigo-500/20 text-indigo-300 text-xs rounded">
                    {feature.replace(/_/g, ' ')}
                  </span>
                ))}
              </div>
            )}
          </div>
          
          {filteredOpportunities.length === 0 ? (
            <div className="bg-gray-800/30 border border-gray-700/50 rounded-xl p-8 text-center">
              <Package className="w-12 h-12 text-gray-500 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-gray-400 mb-2">No Set Combining Opportunities</h3>
              <p className="text-gray-500">No profitable set combining opportunities found with current filters. Try adjusting your criteria.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
              {filteredOpportunities.map((opportunity, index) => {
                // Real-time data enhancement
                const realtimeItemData = socketState?.priceUpdates?.[opportunity.set_item_id];
                
                // AI insights integration
                const aiInsights = socketState?.aiAnalysis?.[opportunity.set_item_id];

                return (
                  <SetCombiningOpportunityCard
                    key={`${opportunity.id}-${index}`}
                    opportunity={{
                      ...opportunity,
                      // Add calculated fields
                      is_favorite: favorites.has(opportunity.set_item_id || 0),
                      real_time_data: realtimeItemData,
                      ai_insights: aiInsights
                    }}
                    onClick={() => handleItemClick(opportunity)}
                    onOpenCalculator={() => setSelectedOpportunityForCalculator(opportunity)}
                  />
                );
              })}
            </div>
          )}
        </motion.div>

        {/* Live Market Intelligence Dashboard */}
        {showReactiveFeatures && socketState?.isConnected && (
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="bg-gradient-to-r from-blue-900/20 via-purple-900/20 to-blue-900/20 backdrop-blur-sm border border-blue-500/30 rounded-xl p-6"
          >
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-500/20 rounded-lg">
                  <SparklesIcon className="w-6 h-6 text-blue-400" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-blue-400">🚀 AI Market Intelligence</h3>
                  <p className="text-sm text-gray-400">Real-time market analysis and pattern detection for set combining</p>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
              {/* Market Events */}
              <div className="bg-gray-800/30 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <ChartBarIcon className="w-4 h-4 text-green-400" />
                  <span className="text-sm font-medium text-green-400">Market Events</span>
                  <span className="text-xs bg-green-500/20 text-green-400 px-2 py-0.5 rounded-full">
                    {socketState?.marketEvents?.length || 0}
                  </span>
                </div>
                <div className="text-xs text-gray-400">
                  {socketState?.marketEvents?.length > 0 ? (
                    <div className="space-y-1">
                      {socketState.marketEvents.slice(0, 2).map((event: any, i: number) => (
                        <div key={i} className="text-green-300">
                          • {event.message || 'Market activity detected'}
                        </div>
                      ))}
                    </div>
                  ) : (
                    'No recent events'
                  )}
                </div>
              </div>

              {/* Pattern Detections */}
              <div className="bg-gray-800/30 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <BoltIcon className="w-4 h-4 text-yellow-400" />
                  <span className="text-sm font-medium text-yellow-400">Pattern Detections</span>
                  <span className="text-xs bg-yellow-500/20 text-yellow-400 px-2 py-0.5 rounded-full">
                    {socketState?.patternDetections?.length || 0}
                  </span>
                </div>
                <div className="text-xs text-gray-400">
                  {socketState?.patternDetections?.length > 0 ? (
                    <div className="space-y-1">
                      {socketState.patternDetections.slice(0, 2).map((pattern: any, i: number) => (
                        <div key={i} className="text-yellow-300">
                          • {pattern.pattern_type || 'Price pattern detected'}
                        </div>
                      ))}
                    </div>
                  ) : (
                    'Analyzing patterns...'
                  )}
                </div>
              </div>

              {/* Market Alerts */}
              <div className="bg-gray-800/30 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <SparklesIcon className="w-4 h-4 text-red-400" />
                  <span className="text-sm font-medium text-red-400">Active Alerts</span>
                  <span className="text-xs bg-red-500/20 text-red-400 px-2 py-0.5 rounded-full">
                    {(socketState?.marketAlerts || []).filter(alert => alert.is_active).length}
                  </span>
                </div>
                <div className="text-xs text-gray-400">
                  {(socketState?.marketAlerts || []).filter(alert => alert.is_active).length > 0 ? (
                    <div className="space-y-1">
                      {socketState.marketAlerts.filter(alert => alert.is_active).slice(0, 2).map((alert: any, i: number) => (
                        <div key={i} className="text-red-300">
                          • {alert.alert_type || 'Price alert'}
                        </div>
                      ))}
                    </div>
                  ) : (
                    'No active alerts'
                  )}
                </div>
              </div>
            </div>
          </motion.div>
        )}

        {/* Tips Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="bg-gray-800/30 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6"
        >
          <h3 className="text-lg font-semibold text-gray-200 mb-4">🛡️ Set Combining Tips</h3>
          <div className="grid md:grid-cols-2 gap-4 text-sm text-gray-400">
            <div>
              <strong className="text-green-400">Lazy Tax Strategy:</strong> Buy complete armor sets cheaply, then break them apart and sell individual pieces for higher prices. Players pay extra for convenience of not having to buy complete sets.
            </div>
            <div>
              <strong className="text-blue-400">Real-time Pricing:</strong> AI opportunities use live OSRS Wiki API data for the most accurate profit calculations and volume analysis with individual piece prices shown.
            </div>
          </div>
        </motion.div>

        {/* AI Assistant Modal */}
        <AISetCombiningAssistant
          isOpen={showAIAssistant}
          onClose={() => setShowAIAssistant(false)}
          opportunities={filteredOpportunities}
          currentCapital={currentCapital}
        />

        {/* Set Combining Calculator Modal */}
        <SetCombiningCalculatorModal
          isOpen={!!selectedOpportunityForCalculator}
          onClose={() => setSelectedOpportunityForCalculator(null)}
          opportunity={selectedOpportunityForCalculator!}
        />

        {/* Floating AI Assistant Button */}
        <motion.button
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.9 }}
          onClick={() => setShowAIAssistant(true)}
          className="fixed bottom-6 right-6 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white p-4 rounded-full shadow-2xl border border-indigo-500/30 transition-all duration-200 z-40"
        >
          <ChatBubbleLeftRightIcon className="w-6 h-6" />
          <div className="absolute -top-1 -right-1 w-3 h-3 bg-green-400 rounded-full animate-pulse" />
        </motion.button>
      </div>
    </div>
  );
}

export default SetCombiningView;