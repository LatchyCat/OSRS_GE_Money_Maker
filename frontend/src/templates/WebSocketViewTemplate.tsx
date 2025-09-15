/**
 * 🔌 WebSocket View Template
 * 
 * Copy this template to create new views with WebSocket functionality.
 * 
 * INSTRUCTIONS:
 * 1. Copy this file to your new view location
 * 2. Rename the component and file
 * 3. Replace 'YOUR_ROUTE_NAME' with your actual route (e.g., 'high-alchemy', 'flipping')
 * 4. Customize the data interfaces and API calls
 * 5. Update the UI components for your specific needs
 * 
 * IMPORTANT: Follow the patterns exactly to avoid infinite loops and connection issues.
 */

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ArrowPathIcon,
  MagnifyingGlassIcon,
  BellIcon,
  LightBulbIcon
} from '@heroicons/react/24/outline';
import { Sparkles, Target, TrendingUp } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

// ✅ REQUIRED: Import WebSocket context
import { useReactiveTradingContext } from '../contexts/ReactiveTrading';
import type { PriceUpdate } from '../hooks/useReactiveTradingSocket';

// 📝 TODO: Replace with your actual API import
import { moneyMakerApi } from '../api/moneyMaker';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';

// 📝 TODO: Define your data interfaces
interface YourDataItem {
  id: number;
  item_id: number;
  name: string;
  profit: number;
  price: number;
  // Add other fields specific to your view
}

interface YourFilters {
  search: string;
  minProfit: number;
  sortBy: 'profit' | 'name' | 'efficiency';
  // Add other filters specific to your view
}

// 📝 TODO: Rename this component to match your view
const WebSocketViewTemplate: React.FC = () => {
  // ✅ REQUIRED: WebSocket connection setup
  const { state: socketState, actions: socketActions } = useReactiveTradingContext();
  
  // ✅ REQUIRED: Connection state management
  const [lastConnectionAttempt, setLastConnectionAttempt] = useState<Date | null>(null);
  const [websocketError, setWebsocketError] = useState<string | null>(null);
  
  // 📝 TODO: Replace with your component state
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [data, setData] = useState<YourDataItem[]>([]);
  const [filters, setFilters] = useState<YourFilters>({
    search: '',
    minProfit: 0,
    sortBy: 'profit'
  });

  // 📝 TODO: Replace with your data fetching logic
  const fetchData = useCallback(async (showRefreshSpinner = false) => {
    if (showRefreshSpinner) setRefreshing(true);
    setLoading(true);
    
    try {
      console.log('📊 Fetching data from API...');
      
      // TODO: Replace with your actual API call
      const response = await moneyMakerApi.getStrategies();
      
      console.log('✅ Data fetched successfully:', response);
      setData(response.results || []);
    } catch (error) {
      console.error('❌ Error fetching data:', error);
      setData([]);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  // ✅ REQUIRED: WebSocket route subscription (MAIN CONNECTION)
  useEffect(() => {
    // Enhanced connection state guards
    if (!socketState?.isConnected || !socketActions) {
      console.log('🚫 WebSocket not ready for subscription:', {
        connected: socketState?.isConnected,
        hasActions: !!socketActions
      });
      return;
    }

    // 📝 TODO: Replace 'YOUR_ROUTE_NAME' with your actual route
    console.log('🔌 WebSocket connected, subscribing to YOUR_ROUTE_NAME route...');
    
    try {
      // Subscribe to route only once per connection with error boundaries
      const subscribeToRouteStable = socketActions.subscribeToRoute;
      const getCurrentRecommendationsStable = socketActions.getCurrentRecommendations;
      const getMarketAlertsStable = socketActions.getMarketAlerts;
      
      if (subscribeToRouteStable) {
        subscribeToRouteStable('YOUR_ROUTE_NAME'); // 📝 TODO: Replace this
      }
      if (getCurrentRecommendationsStable) {
        getCurrentRecommendationsStable('YOUR_ROUTE_NAME'); // 📝 TODO: Replace this
      }
      if (getMarketAlertsStable) {
        getMarketAlertsStable();
      }
      
      setLastConnectionAttempt(new Date());
      setWebsocketError(null);
    } catch (error) {
      console.error('❌ Error during WebSocket subscription setup:', error);
      setWebsocketError(error instanceof Error ? error.message : 'Subscription setup failed');
    }

    // Cleanup function
    return () => {
      console.log('🧹 Cleaning up YOUR_ROUTE_NAME route subscription');
    };
  }, [socketState?.isConnected]); // ⚠️ CRITICAL: Only socketState?.isConnected in deps!

  // ✅ REQUIRED: Handle WebSocket errors separately to avoid infinite loops
  useEffect(() => {
    if (socketState?.error) {
      setWebsocketError(socketState.error);
    }
  }, [socketState?.error]);

  // ✅ OPTIONAL: Item-level subscriptions (if your view needs real-time price updates)
  // Memoize subscription functions to prevent infinite loops
  const stableSubscribeToItem = useCallback(
    (itemId: string) => socketActions?.subscribeToItem?.(itemId),
    [socketActions?.subscribeToItem]
  );
  
  const stableUnsubscribeFromItem = useCallback(
    (itemId: string) => socketActions?.unsubscribeFromItem?.(itemId),
    [socketActions?.unsubscribeFromItem]
  );

  // Subscribe to individual items when data changes
  const currentItemIds = useMemo(() => {
    return data.map(item => item.item_id.toString()).filter(Boolean);
  }, [data]);

  const uniqueItemIds = useMemo(() => {
    return [...new Set(currentItemIds)];
  }, [currentItemIds]);

  useEffect(() => {
    if (!socketState?.isConnected || uniqueItemIds.length === 0) {
      return;
    }

    console.log(`📡 Batch subscribing to ${uniqueItemIds.length} items`);
    
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

  // ✅ REQUIRED: Handle real-time price updates
  const priceUpdates = useMemo(() => {
    return Object.values(socketState?.priceUpdates || {});
  }, [socketState?.priceUpdates]);

  useEffect(() => {
    if (priceUpdates.length === 0) return;

    setData(prevData => {
      const updatedData = [...prevData];
      let hasChanges = false;
      
      priceUpdates.forEach((priceUpdate: PriceUpdate) => {
        const itemIndex = updatedData.findIndex(item => item.item_id === priceUpdate.item_id);
        if (itemIndex !== -1) {
          const currentPrice = (priceUpdate.high_price + priceUpdate.low_price) / 2;
          const oldPrice = updatedData[itemIndex].price || 0;
          const priceChangePercent = Math.abs((currentPrice - oldPrice) / oldPrice * 100);
          
          // Update if significant change (>2%)
          if (priceChangePercent > 2 || oldPrice === 0) {
            updatedData[itemIndex] = {
              ...updatedData[itemIndex],
              price: priceUpdate.low_price,
              // 📝 TODO: Update other relevant fields based on your data structure
              // profit: calculateNewProfit(updatedData[itemIndex], priceUpdate.low_price),
            };
            hasChanges = true;
          }
        }
      });
      
      return hasChanges ? updatedData : prevData;
    });
  }, [priceUpdates]);

  // ✅ REQUIRED: Initial data fetch
  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // 📝 TODO: Add your filtering logic
  const filteredData = useMemo(() => {
    return data.filter(item => {
      const matchesSearch = item.name.toLowerCase().includes(filters.search.toLowerCase());
      const matchesProfit = item.profit >= filters.minProfit;
      return matchesSearch && matchesProfit;
    }).sort((a, b) => {
      switch (filters.sortBy) {
        case 'profit':
          return b.profit - a.profit;
        case 'name':
          return a.name.localeCompare(b.name);
        default:
          return 0;
      }
    });
  }, [data, filters]);

  // 📝 TODO: Add your refresh handler
  const handleRefresh = useCallback(() => {
    fetchData(true);
  }, [fetchData]);

  // 📝 TODO: Add your utility functions (formatters, etc.)
  const formatGP = (value: number) => {
    if (value >= 1000000) {
      return `${(value / 1000000).toFixed(1)}M`;
    }
    if (value >= 1000) {
      return `${(value / 1000).toFixed(1)}K`;
    }
    return value.toLocaleString();
  };

  // Loading state
  if (loading && data.length === 0) {
    return (
      <div className="p-6">
        <LoadingSpinner />
        <p className="text-center text-gray-400 mt-4">Loading data...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      <div className="container mx-auto px-4 py-8 space-y-8">
        
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center"
        >
          <div className="flex items-center justify-center gap-3 mb-4">
            <Target className="w-8 h-8 text-blue-400" />
            <h1 className="text-4xl font-bold text-white">
              {/* 📝 TODO: Replace with your view title */}
              Your Trading View
            </h1>
            <Sparkles className="w-8 h-8 text-purple-400" />
          </div>
          <p className="text-xl text-gray-400">
            {/* 📝 TODO: Replace with your view description */}
            Real-time trading opportunities with OSRS Wiki data
          </p>
        </motion.div>

        {/* Stats Overview */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="grid grid-cols-1 md:grid-cols-3 gap-6"
        >
          <div className="bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6 text-center">
            <div className="text-2xl font-bold text-blue-400 mb-1">{filteredData.length}</div>
            <div className="text-sm text-gray-400">Total Opportunities</div>
          </div>
          <div className="bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6 text-center">
            <div className="text-2xl font-bold text-green-400 mb-1">
              {filteredData.length > 0 ? formatGP(Math.max(...filteredData.map(item => item.profit))) : '0'}
            </div>
            <div className="text-sm text-gray-400">Best Profit</div>
          </div>
          <div className="bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6 text-center">
            <div className="text-2xl font-bold text-purple-400 mb-1">
              {filteredData.length > 0 ? formatGP(Math.floor(filteredData.reduce((sum, item) => sum + item.profit, 0) / filteredData.length)) : '0'}
            </div>
            <div className="text-sm text-gray-400">Avg Profit</div>
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
                value={filters.search}
                onChange={(e) => setFilters(prev => ({ ...prev, search: e.target.value }))}
                className="w-full pl-10 pr-4 py-2 bg-gray-700/50 border border-gray-600/50 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500/50 text-white placeholder-gray-400"
              />
            </div>

            {/* Filters and Actions */}
            <div className="flex gap-3 items-center">
              <select
                value={filters.sortBy}
                onChange={(e) => setFilters(prev => ({ ...prev, sortBy: e.target.value as any }))}
                className="px-3 py-2 bg-gray-700/50 border border-gray-600/50 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-purple-500/50"
              >
                <option value="profit">Sort by Profit</option>
                <option value="name">Sort by Name</option>
                <option value="efficiency">Sort by Efficiency</option>
              </select>

              <button
                onClick={handleRefresh}
                disabled={refreshing}
                className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:bg-purple-800 disabled:opacity-50 text-white rounded-lg transition-colors"
              >
                <ArrowPathIcon className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
                {refreshing ? 'Refreshing...' : 'Refresh'}
              </button>
            </div>
          </div>
        </motion.div>

        {/* Data Display */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
        >
          <div className="flex items-center gap-3 mb-6">
            <TrendingUp className="w-6 h-6 text-green-400" />
            <h2 className="text-2xl font-bold text-white">Trading Opportunities</h2>
          </div>
          
          {filteredData.length === 0 ? (
            <div className="bg-gray-800/30 border border-gray-700/50 rounded-xl p-8 text-center">
              <Target className="w-12 h-12 text-gray-500 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-gray-400 mb-2">No Opportunities Found</h3>
              <p className="text-gray-500">Try adjusting your filters or refresh the data.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {filteredData.map((item, index) => (
                <motion.div
                  key={item.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.1 * index }}
                  className="bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6 hover:border-purple-500/50 transition-colors"
                >
                  <h3 className="text-lg font-semibold text-white mb-2">{item.name}</h3>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-gray-400">Profit:</span>
                      <span className="text-green-400 font-medium">{formatGP(item.profit)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Price:</span>
                      <span className="text-blue-400 font-medium">{formatGP(item.price)}</span>
                    </div>
                    {/* 📝 TODO: Add more fields specific to your data */}
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </motion.div>

        {/* WebSocket Status & Tips */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="bg-gray-800/30 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6"
        >
          <h3 className="text-lg font-semibold text-gray-200 mb-4 flex items-center gap-2">
            <LightBulbIcon className="w-5 h-5 text-yellow-400" />
            Real-Time Trading Tips
          </h3>
          
          {/* 📝 TODO: Add your specific tips */}
          <div className="grid md:grid-cols-2 gap-4 text-sm text-gray-400 mb-4">
            <div>
              <strong className="text-blue-400 block">📊 Data Source:</strong>
              All data comes from real OSRS Wiki API with live price updates
            </div>
            <div>
              <strong className="text-green-400 block">⚡ Real-Time:</strong>
              Prices update automatically every 30 seconds via WebSocket
            </div>
          </div>
          
          {/* ✅ REQUIRED: WebSocket Status Display */}
          <div className="pt-4 border-t border-gray-600/30">
            <div className="flex items-center justify-between text-xs">
              <div className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${
                  socketState?.isConnected ? 'bg-green-400' : 'bg-red-400'
                }`}></div>
                <span className="text-gray-400">
                  WebSocket: {socketState?.isConnected ? 'Connected' : 'Disconnected'}
                </span>
              </div>
              {lastConnectionAttempt && (
                <span className="text-gray-500">
                  Last update: {formatDistanceToNow(lastConnectionAttempt)} ago
                </span>
              )}
            </div>
            {websocketError && (
              <div className="mt-2 text-xs text-red-400 bg-red-900/20 rounded px-2 py-1">
                Connection Error: {websocketError}
              </div>
            )}
          </div>
        </motion.div>
      </div>
    </div>
  );
};

export default WebSocketViewTemplate;