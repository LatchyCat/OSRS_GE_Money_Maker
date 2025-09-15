import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  ArrowPathIcon,
  MagnifyingGlassIcon,
  FunnelIcon,
  XMarkIcon,
  SparklesIcon,
  ChartBarIcon,
  BoltIcon,
  ChatBubbleLeftRightIcon,
  TrophyIcon,
  FireIcon,
  BeakerIcon
} from '@heroicons/react/24/outline';
import { Wand2 } from 'lucide-react';

import { itemsApi } from '../api/itemsApi';
import { tradingStrategiesApiClient } from '../api/tradingStrategiesApi';
import { HighAlchemyOpportunityCard } from '../components/trading/HighAlchemyOpportunityCard';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { useReactiveTradingContext } from '../contexts/ReactiveTrading';
import RealtimePriceChart from '../components/trading/RealtimePriceChart';
import ProfitCalculator from '../components/trading/ProfitCalculator';
import HighAlchemyProfitCalculator from '../components/trading/HighAlchemyProfitCalculator';
import HighAlchemyProfitChart from '../components/trading/HighAlchemyProfitChart';
import AITradingAssistant from '../components/ai/AITradingAssistant';
import { AIHighAlchemyAssistant } from '../components/ai/AIHighAlchemyAssistant';
import LiveProfitDashboard from '../components/trading/LiveProfitDashboard';
import QuickTradeModal from '../components/trading/QuickTradeModal';
import type { Item } from '../types';
import type { DecantingOpportunity } from '../types/tradingStrategies';

interface HighAlchemyFilters {
  search: string;
  minProfit: number;
  minAlchValue: number;
  sortBy: 'profit' | 'alch_score' | 'efficiency' | 'xp_rate' | 'margin' | 'volume';
  riskLevel: 'all' | 'low' | 'medium' | 'high';
  minMargin: string;
  maxMargin: string;
  minGpPerHour: string;
  maxGpPerHour: string;
  volumeFilter: 'all' | 'high' | 'medium' | 'low';
  includeNatureRuneCost: boolean;
  minXpRate: string;
  maxXpRate: string;
  profitabilityOnly: boolean;
  highValueOnly: boolean;
  minCapital: string;
  maxCapital: string;
  ordering: string;
}

export function HighAlchemyView() {
  const [items, setItems] = useState<Item[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [filters, setFilters] = useState<HighAlchemyFilters>({
    search: '',
    minProfit: 0,
    minAlchValue: 1,
    sortBy: 'profit',
    riskLevel: 'all',
    minMargin: '',
    maxMargin: '',
    minGpPerHour: '',
    maxGpPerHour: '',
    volumeFilter: 'all',
    includeNatureRuneCost: true,
    minXpRate: '',
    maxXpRate: '',
    profitabilityOnly: true,
    highValueOnly: false,
    minCapital: '',
    maxCapital: '',
    ordering: 'profit_desc'
  });

  // UI State
  const [searchInput, setSearchInput] = useState('');
  const [minProfitInput, setMinProfitInput] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [selectedItemForChart, setSelectedItemForChart] = useState<number | null>(null);
  const [showReactiveFeatures, setShowReactiveFeatures] = useState(true);
  const [selectedOpportunityForCalculator, setSelectedOpportunityForCalculator] = useState<Item | null>(null);
  const [showAIAssistant, setShowAIAssistant] = useState(false);
  const [currentCapital, setCurrentCapital] = useState(1000000); // 1M GP default
  const [showAchievements, setShowAchievements] = useState(false);
  const [selectedOpportunityForQuickTrade, setSelectedOpportunityForQuickTrade] = useState<Item | null>(null);
  const [selectedItemForProfitChart, setSelectedItemForProfitChart] = useState<Item | null>(null);
  const [selectedItemForCalculator, setSelectedItemForCalculator] = useState<Item | null>(null);
  const [natureRunePrice, setNatureRunePrice] = useState(180); // Default nature rune price
  const [favorites, setFavorites] = useState<Set<number>>(new Set());
  const [websocketError, setWebsocketError] = useState<string | null>(null);
  const [lastConnectionAttempt, setLastConnectionAttempt] = useState<Date | null>(null);
  
  // Real-time trading intelligence
  const { state: socketState, actions: socketActions } = useReactiveTradingContext();

  // Toggle favorite function
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
  
  // Gamification state
  const [playerStats, setPlayerStats] = useState({
    totalProfit: 1800000,
    tradesExecuted: 23,
    currentStreak: 12,
    bestStreak: 18,
    sessionsPlayed: 5,
    totalPlayTime: 14400, // 4 hours
    opportunitiesDiscovered: 45,
    perfectTrades: 4,
    level: 9,
    currentXP: 1340,
    xpToNextLevel: 210,
    totalXPForNextLevel: 1550,
    playerTitle: "Master Alchemist",
    totalXPGained: 156000,
    itemsAlched: 2400
  });

  const [stats, setStats] = useState({
    totalOpportunities: 0,
    avgProfit: 0,
    topAlchValue: 0,
    totalXpHour: 0,
    avgMargin: 0,
    bestGpPerHour: 0
  });

  const fetchHighAlchemyItems = async (showRefreshSpinner = false) => {
    if (showRefreshSpinner) setRefreshing(true);
    setLoading(true);

    try {
      // Fetch items with high alchemy focus
      const response = await itemsApi.getItems({
        ordering: '-profit_calc__high_alch_viability_score',
        page_size: 50,
        min_profit: filters.minProfit,
        search: filters.search || undefined
      });

      // Filter for items with high alchemy potential using available data
      const natureRuneCost = 180; // Nature rune cost
      
      const alchemyItems = response.results.filter(item => {
        if (!item.high_alch || item.high_alch < filters.minAlchValue) return false;
        
        // Calculate profit per cast: high_alch - buy_price - nature_rune_cost
        const buyPrice = item.current_buy_price || item.profit_calc?.current_buy_price || 0;
        const profitPerCast = item.high_alch - buyPrice - natureRuneCost;
        
        // Only show items that are potentially profitable
        return profitPerCast > -100; // Allow some slightly negative items for completeness
      });

      console.log('High Alchemy Debug - Filtering results:', {
        totalItems: response.results.length,
        itemsWithHighAlch: response.results.filter(item => item.high_alch).length,
        itemsAboveMinValue: response.results.filter(item => item.high_alch && item.high_alch >= filters.minAlchValue).length,
        finalAlchemyItems: alchemyItems.length,
        sampleItem: alchemyItems[0] ? {
          name: alchemyItems[0].name,
          high_alch: alchemyItems[0].high_alch,
          buy_price: alchemyItems[0].current_buy_price || alchemyItems[0].profit_calc?.current_buy_price,
          profitPerCast: alchemyItems[0].high_alch - (alchemyItems[0].current_buy_price || alchemyItems[0].profit_calc?.current_buy_price || 0) - natureRuneCost
        } : null
      });

      // Sort based on selected criteria using available data
      const sortedItems = [...alchemyItems].sort((a, b) => {
        const natureRuneCost = 180;
        
        switch (filters.sortBy) {
          case 'profit': {
            const aProfitPerCast = a.high_alch - (a.current_buy_price || a.profit_calc?.current_buy_price || 0) - natureRuneCost;
            const bProfitPerCast = b.high_alch - (b.current_buy_price || b.profit_calc?.current_buy_price || 0) - natureRuneCost;
            return bProfitPerCast - aProfitPerCast;
          }
          case 'alch_score':
          case 'efficiency': {
            // Calculate efficiency based on profit margin
            const aPrice = a.current_buy_price || a.profit_calc?.current_buy_price || 0;
            const bPrice = b.current_buy_price || b.profit_calc?.current_buy_price || 0;
            const aMargin = aPrice > 0 ? ((a.high_alch - aPrice - natureRuneCost) / aPrice) : 0;
            const bMargin = bPrice > 0 ? ((b.high_alch - bPrice - natureRuneCost) / bPrice) : 0;
            return bMargin - aMargin;
          }
          case 'xp_rate': {
            // Sort by high alch value (higher alch = more valuable items)
            return (b.high_alch || 0) - (a.high_alch || 0);
          }
          default:
            return 0;
        }
      });

      setItems(sortedItems);

      // Calculate stats using available data
      if (sortedItems.length > 0) {
        const runeCost = filters.includeNatureRuneCost ? natureRunePrice : 0;
        const xpPerCast = 65; // High alchemy XP
        const castsPerHour = 1200; // Approximate casts per hour
        
        // Calculate average profit per cast
        const profits = sortedItems.map(item => {
          const buyPrice = item.current_buy_price || item.profit_calc?.current_buy_price || 0;
          return item.high_alch - buyPrice - runeCost;
        });
        
        const margins = sortedItems.map(item => {
          const buyPrice = item.current_buy_price || item.profit_calc?.current_buy_price || 0;
          return buyPrice > 0 ? ((item.high_alch - buyPrice - runeCost) / buyPrice) * 100 : 0;
        });
        
        const gpPerHourValues = profits.map(profit => profit * castsPerHour);
        
        // Safe calculations with validation
        const avgProfitPerCast = profits.length > 0 ? profits.reduce((sum, profit) => sum + profit, 0) / profits.length : 0;
        const avgMargin = margins.length > 0 ? margins.reduce((sum, margin) => sum + margin, 0) / margins.length : 0;
        
        // Safe max calculations
        const alchValues = sortedItems.map(item => item.high_alch || 0).filter(val => val > 0);
        const validGpPerHourValues = gpPerHourValues.filter(val => val > 0);
        
        setStats({
          totalOpportunities: sortedItems.length,
          avgProfit: isFinite(avgProfitPerCast) ? avgProfitPerCast : 0,
          topAlchValue: alchValues.length > 0 ? Math.max(...alchValues) : 0,
          totalXpHour: xpPerCast * castsPerHour, // 78,000 XP/hour
          avgMargin: isFinite(avgMargin) ? avgMargin : 0,
          bestGpPerHour: validGpPerHourValues.length > 0 ? Math.max(...validGpPerHourValues) : 0
        });
      } else {
        setStats({
          totalOpportunities: 0,
          avgProfit: 0,
          topAlchValue: 0,
          totalXpHour: 0,
          avgMargin: 0,
          bestGpPerHour: 0
        });
      }
    } catch (error) {
      console.error('Error fetching high alchemy items:', error);
      
      // Set error state for user feedback
      setWebsocketError(error instanceof Error ? error.message : 'Failed to fetch high alchemy data');
      
      // Set empty state safely
      setItems([]);
      setStats({
        totalOpportunities: 0,
        avgProfit: 0,
        topAlchValue: 0,
        totalXpHour: 0,
        avgMargin: 0,
        bestGpPerHour: 0
      });
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchHighAlchemyItems();
  }, [filters]);

  // Real-time WebSocket integration with improved error handling
  useEffect(() => {
    if (socketState?.isConnected) {
      console.log('🔌 WebSocket connected, subscribing to high-alchemy updates...');
      setWebsocketError(null);
      setLastConnectionAttempt(new Date());
      
      // Add a small delay to prevent rapid successive calls
      const timeoutId = setTimeout(() => {
        try {
          const success = socketActions.subscribeToRoute('high-alchemy');
          if (success) {
            console.log('✅ Successfully subscribed to high-alchemy route');
            socketActions.getCurrentRecommendations('high-alchemy');
            socketActions.getMarketAlerts();
          } else {
            setWebsocketError('Failed to subscribe to high-alchemy updates');
          }
        } catch (error) {
          console.error('Error subscribing to high-alchemy route:', error);
          setWebsocketError('WebSocket subscription error');
        }
      }, 100);
      
      return () => clearTimeout(timeoutId);
    } else if (socketState?.error) {
      setWebsocketError(socketState.error);
    }
  }, [socketState?.isConnected, socketState?.error]); // Added error state to dependencies
  
  // Subscribe to items for real-time price updates with optimized dependencies
  useEffect(() => {
    if (socketState?.isConnected && items.length > 0) {
      const itemIds = items.map(item => item.item_id?.toString()).filter(Boolean);
      const uniqueItemIds = [...new Set(itemIds)];
      
      console.log(`📡 HighAlchemyView: Batch subscribing to ${uniqueItemIds.length} unique items`);
      
      // Add small delay to prevent overwhelming WebSocket
      const timeoutId = setTimeout(() => {
        uniqueItemIds.forEach(itemId => {
          if (itemId) socketActions.subscribeToItem(itemId);
        });
      }, 200);
      
      // Cleanup subscriptions when items change
      return () => {
        clearTimeout(timeoutId);
        console.log('🧹 HighAlchemyView: Cleaning up item subscriptions...');
        uniqueItemIds.forEach(itemId => {
          if (itemId) socketActions.unsubscribeFromItem(itemId);
        });
      };
    }
  }, [socketState?.isConnected, JSON.stringify(items.map(i => i.item_id))]); // Use stable item ID reference

  // Handle real-time recommendation updates
  useEffect(() => {
    const highAlchemyRecommendations = socketState?.recommendations?.['high-alchemy'];
    if (highAlchemyRecommendations && highAlchemyRecommendations.length > 0) {
      console.log('🔄 Received real-time high-alchemy recommendations:', highAlchemyRecommendations);
      
      // Update items with real-time data if they match our current view
      setItems(prevItems => {
        const updatedItems = [...prevItems];
        
        highAlchemyRecommendations.forEach((rec: any) => {
          const existingIndex = updatedItems.findIndex(item => item.item_id === rec.item_id);
          if (existingIndex !== -1) {
            // Update existing item with real-time data
            updatedItems[existingIndex] = {
              ...updatedItems[existingIndex],
              last_updated: new Date().toISOString()
            } as any;
          }
        });
        
        return updatedItems;
      });
    }
  }, [socketState?.recommendations]);

  // Handle real-time price updates
  useEffect(() => {
    const priceUpdates = Object.values(socketState?.priceUpdates || {});
    if (priceUpdates.length > 0) {
      console.log('💰 Received real-time price updates for high-alchemy:', priceUpdates);
      
      // Update items with latest price data
      setItems(prevItems => {
        const updatedItems = [...prevItems];
        
        priceUpdates.forEach((priceUpdate: any) => {
          const itemIndex = updatedItems.findIndex(item => item.item_id === priceUpdate.item_id);
          if (itemIndex !== -1) {
            const item = updatedItems[itemIndex];
            const currentPrice = (priceUpdate.high_price + priceUpdate.low_price) / 2;
            const oldPrice = item.current_buy_price || 0;
            const priceChangePercent = oldPrice > 0 ? Math.abs((currentPrice - oldPrice) / oldPrice * 100) : 0;
            
            // Update price if significant change (>1%)
            if (priceChangePercent > 1 || oldPrice === 0) {
              updatedItems[itemIndex] = {
                ...item,
                current_buy_price: priceUpdate.low_price,
                last_updated: priceUpdate.timestamp
              } as any;
            }
          }
        });
        
        return updatedItems;
      });
    }
  }, [socketState?.priceUpdates]);

  const handleRefresh = () => {
    fetchHighAlchemyItems(true);
  };

  // Apply filters function to update the actual filters
  const applyFilters = () => {
    setFilters(prev => ({
      ...prev,
      search: searchInput.trim(),
      minProfit: parseInt(minProfitInput) || 0
    }));
  };

  // Handle Enter key press
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      applyFilters();
    }
  };

  const formatGP = (amount: number) => {
    if (amount >= 1000000) {
      return `${(amount / 1000000).toFixed(1)}M`;
    } else if (amount >= 1000) {
      return `${(amount / 1000).toFixed(1)}K`;
    }
    return amount.toLocaleString();
  };

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
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 p-6">
      <div className="max-w-7xl mx-auto space-y-8">
        
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center"
        >
          <div className="flex items-center justify-center gap-3 mb-4">
            <div className="p-3 bg-yellow-400/10 rounded-xl">
              <Wand2 className="w-8 h-8 text-yellow-400" />
            </div>
            <h1 className="text-4xl font-bold text-gradient">
              High Alchemy Opportunities
            </h1>
          </div>
          <p className="text-xl text-gray-400 max-w-2xl mx-auto">
            Maximize your magic XP and GP/hour with optimal high alchemy targets
          </p>
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
                  Connected to live market data • Last connected: {lastConnectionAttempt?.toLocaleTimeString() || 'Unknown'}
                </div>
              </div>
            </div>
          </motion.div>
        )}

        {/* Stats Overview */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="grid grid-cols-2 md:grid-cols-4 gap-4"
        >
          <div className="bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6 text-center">
            <div className="text-2xl font-bold text-yellow-400 mb-1">{stats.totalOpportunities}</div>
            <div className="text-sm text-gray-400">Opportunities Found</div>
          </div>
          <div className="bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6 text-center">
            <div className="text-2xl font-bold text-green-400 mb-1">{formatGP(stats.avgProfit)}</div>
            <div className="text-sm text-gray-400">Avg Profit/Item</div>
          </div>
          <div className="bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6 text-center">
            <div className="text-2xl font-bold text-blue-400 mb-1">{formatGP(stats.topAlchValue)}</div>
            <div className="text-sm text-gray-400">Highest Alch Value</div>
          </div>
          <div className="bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6 text-center">
            <div className="text-2xl font-bold text-purple-400 mb-1">{formatGP(stats.totalXpHour)}</div>
            <div className="text-sm text-gray-400">Total XP Efficiency</div>
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
                placeholder="Search items... (Press Enter)"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                onKeyPress={handleKeyPress}
                onBlur={applyFilters}
                className="w-full pl-10 pr-4 py-2 bg-gray-700/50 border border-gray-600/50 rounded-lg focus:outline-none focus:ring-2 focus:ring-yellow-500/50 focus:border-yellow-500/50 text-white placeholder-gray-400"
              />
            </div>

            {/* Filters */}
            <div className="flex gap-3 items-center">
              <select
                value={filters.sortBy}
                onChange={(e) => setFilters({...filters, sortBy: e.target.value as any})}
                className="px-3 py-2 bg-gray-700/50 border border-gray-600/50 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-yellow-500/50"
              >
                <option value="alch_score">Alch Score</option>
                <option value="profit">Profit</option>
                <option value="efficiency">Efficiency</option>
                <option value="xp_rate">XP Rate</option>
              </select>

              <input
                type="number"
                placeholder="Min Profit (Enter)"
                value={minProfitInput}
                onChange={(e) => setMinProfitInput(e.target.value)}
                onKeyPress={handleKeyPress}
                onBlur={applyFilters}
                className="w-32 px-3 py-2 bg-gray-700/50 border border-gray-600/50 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-yellow-500/50"
              />

              <button
                onClick={applyFilters}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors text-sm"
              >
                <FunnelIcon className="w-4 h-4" />
                Apply
              </button>

              <button
                onClick={handleRefresh}
                disabled={refreshing}
                className="flex items-center gap-2 px-4 py-2 bg-yellow-600 hover:bg-yellow-700 disabled:bg-yellow-800 disabled:opacity-50 text-white rounded-lg transition-colors text-sm"
              >
                <ArrowPathIcon className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
                {refreshing ? 'Refreshing...' : 'Refresh'}
              </button>
            </div>
          </div>
        </motion.div>

        {/* High Alchemy Items Grid */}
        <motion.div
          key={filters.sortBy}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-2 gap-8"
        >
          {items.map((item) => {
            // Find real-time data for this specific item
            const realtimeItemData = (socketState as any)?.marketData?.find(
              (data: any) => data.item_id === item.item_id
            );
            
            // Extract AI insights for this item
            const aiInsights = (socketState as any)?.aiAnalysis?.find(
              (analysis: any) => analysis.item_id === item.item_id
            );

            return (
              <HighAlchemyOpportunityCard
                key={item.item_id}
                item={{
                  ...item,
                  profit_per_cast: item.high_alch - (item.current_buy_price || 0) - natureRunePrice,
                  nature_rune_cost: natureRunePrice,
                  is_favorite: favorites.has(item.item_id || 0),
                  real_time_data: realtimeItemData,
                  ai_insights: aiInsights
                }}
                onClick={() => {
                  console.log('View high alchemy details:', item.item_id);
                  // Show real-time price chart for this item
                  if (item.item_id) {
                    setSelectedItemForChart(item.item_id);
                    // Subscribe to real-time updates for this item only if connected
                    if (socketState?.isConnected) {
                      socketActions.subscribeToItem(item.item_id.toString());
                    }
                  }
                }}
                onToggleFavorite={() => {
                  if (item.item_id) toggleFavorite(item.item_id);
                }}
                onQuickTrade={() => {
                  setSelectedOpportunityForQuickTrade(item);
                }}
                onOpenCalculator={() => {
                  setSelectedItemForCalculator(item);
                }}
                onOpenChart={() => {
                  setSelectedItemForProfitChart(item);
                }}
              />
            );
          })}
        </motion.div>

        {/* No Results */}
        {items.length === 0 && !loading && (
          <div className="text-center py-12">
            <div className="w-16 h-16 bg-gray-700 rounded-full flex items-center justify-center mx-auto mb-4">
              <Wand2 className="w-8 h-8 text-gray-500" />
            </div>
            <h3 className="text-lg font-semibold text-gray-400 mb-2">
              No High Alchemy Opportunities Found
            </h3>
            <p className="text-gray-500">
              Try adjusting your search terms or filters
            </p>
          </div>
        )}

        {/* High Alchemy Profit Calculator Modal */}
        {selectedItemForCalculator && (
          <HighAlchemyProfitCalculator
            item={{
              ...selectedItemForCalculator,
              profit_per_cast: selectedItemForCalculator.high_alch - (selectedItemForCalculator.current_buy_price || 0) - natureRunePrice,
              nature_rune_cost: natureRunePrice
            }}
            onClose={() => setSelectedItemForCalculator(null)}
            onStartTrading={(item, capital) => {
              setSelectedOpportunityForQuickTrade(selectedItemForCalculator);
              setCurrentCapital(capital);
              setSelectedItemForCalculator(null);
            }}
            onSaveStrategy={(item, calculations) => {
              console.log('High alchemy strategy saved:', item.name, calculations);
            }}
            currentCapital={currentCapital}
            natureRunePrice={natureRunePrice}
          />
        )}

        {/* High Alchemy Profit Chart Modal */}
        {selectedItemForProfitChart && (
          <HighAlchemyProfitChart
            item={{
              ...selectedItemForProfitChart,
              profit_per_cast: selectedItemForProfitChart.high_alch - (selectedItemForProfitChart.current_buy_price || 0) - natureRunePrice,
              nature_rune_cost: natureRunePrice
            }}
            displayMode="modal"
            onClose={() => setSelectedItemForProfitChart(null)}
            height={500}
            showNatureRuneImpact={true}
            showXPEfficiency={true}
            showProfitTargets={true}
          />
        )}

        {/* Existing Modals */}
        {selectedOpportunityForQuickTrade && (
          <QuickTradeModal
            isOpen={!!selectedOpportunityForQuickTrade}
            onClose={() => setSelectedOpportunityForQuickTrade(null)}
            opportunity={{
              id: selectedOpportunityForQuickTrade.item_id || 0,
              item_id: selectedOpportunityForQuickTrade.item_id || 0,
              item_name: selectedOpportunityForQuickTrade.name || 'Unknown Item',
              profit_per_conversion: selectedOpportunityForQuickTrade.high_alch - (selectedOpportunityForQuickTrade.current_buy_price || 0) - natureRunePrice,
              profit_per_hour: (selectedOpportunityForQuickTrade.high_alch - (selectedOpportunityForQuickTrade.current_buy_price || 0) - natureRunePrice) * 1200,
              strategy: {
                profit_margin_pct: (selectedOpportunityForQuickTrade.current_buy_price || 0) > 0 ? (((selectedOpportunityForQuickTrade.high_alch - (selectedOpportunityForQuickTrade.current_buy_price || 0) - natureRunePrice) / (selectedOpportunityForQuickTrade.current_buy_price || 0)) * 100) : 0
              },
              from_dose: 1,
              to_dose: 1,
              from_dose_price: selectedOpportunityForQuickTrade.current_buy_price || 0,
              to_dose_price: selectedOpportunityForQuickTrade.high_alch || 0,
              confidence_score: 85,
              ai_confidence: 0.8,
              ai_timing: 'immediate'
            } as DecantingOpportunity}
            currentCapital={currentCapital}
            onTradeComplete={(tradeResult) => {
              setCurrentCapital(prev => Math.max(0, prev + tradeResult.profit));
              console.log('High Alchemy trade completed:', tradeResult);
            }}
          />
        )}

        {/* AI High Alchemy Assistant Modal */}
        {showAIAssistant && (
          <AIHighAlchemyAssistant
            isOpen={showAIAssistant}
            onClose={() => setShowAIAssistant(false)}
            items={items}
            currentCapital={currentCapital}
            natureRunePrice={natureRunePrice}
          />
        )}

        {/* Floating AI Assistant Button */}
        <motion.button
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.9 }}
          onClick={() => setShowAIAssistant(true)}
          className="fixed bottom-6 right-6 bg-gradient-to-r from-yellow-600 to-orange-600 hover:from-yellow-700 hover:to-orange-700 text-white p-4 rounded-full shadow-2xl border border-yellow-500/30 transition-all duration-200 z-40"
        >
          <ChatBubbleLeftRightIcon className="w-6 h-6" />
          <div className="absolute -top-1 -right-1 w-3 h-3 bg-green-400 rounded-full animate-pulse" />
        </motion.button>
      </div>
    </div>
  );
}

export default HighAlchemyView;