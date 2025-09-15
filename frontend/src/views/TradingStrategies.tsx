import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  BeakerIcon,
  ArrowTrendingUpIcon,
  WrenchIcon,
  CubeIcon,
  ArrowPathIcon,
  FunnelIcon,
  MagnifyingGlassIcon,
  PlayIcon,
  PauseIcon
} from '@heroicons/react/24/outline';

// API imports
import { tradingStrategiesApiClient } from '../api/tradingStrategiesApi';

// Component imports
import { DecantingOpportunityCard } from '../components/trading/DecantingOpportunityCard';
import { FlippingOpportunityCard } from '../components/trading/FlippingOpportunityCard';
import { MarketConditionDisplay } from '../components/trading/MarketConditionDisplay';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';

// Type imports
import type {
  TradingStrategy,
  DecantingOpportunity,
  FlippingOpportunity,
  CraftingOpportunity,
  SetCombiningOpportunity,
  MarketConditionSnapshot,
  StrategyType,
  RiskLevel,
  TradingStrategyFilters
} from '../types/tradingStrategies';

type ActiveTab = 'all' | 'decanting' | 'flipping' | 'crafting' | 'set_combining';

export function TradingStrategies() {
  // State management
  const [activeTab, setActiveTab] = useState<ActiveTab>('all');
  const [strategies, setStrategies] = useState<TradingStrategy[]>([]);
  const [decantingOpportunities, setDecantingOpportunities] = useState<DecantingOpportunity[]>([]);
  const [flippingOpportunities, setFlippingOpportunities] = useState<FlippingOpportunity[]>([]);
  const [marketCondition, setMarketCondition] = useState<MarketConditionSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [filters, setFilters] = useState<TradingStrategyFilters>({
    is_active: true,
    page_size: 20
  });

  // Fetch data functions
  const fetchStrategies = async () => {
    try {
      const response = await tradingStrategiesApiClient.strategies.getStrategies(filters);
      setStrategies(response.results);
    } catch (error) {
      console.error('Error fetching strategies:', error);
    }
  };

  const fetchDecantingOpportunities = async () => {
    try {
      const response = await tradingStrategiesApiClient.decanting.getOpportunities(filters);
      setDecantingOpportunities(response.results);
    } catch (error) {
      console.error('Error fetching decanting opportunities:', error);
    }
  };

  const fetchFlippingOpportunities = async () => {
    try {
      const response = await tradingStrategiesApiClient.flipping.getOpportunities(filters);
      setFlippingOpportunities(response.results);
    } catch (error) {
      console.error('Error fetching flipping opportunities:', error);
    }
  };

  const fetchMarketCondition = async () => {
    try {
      const condition = await tradingStrategiesApiClient.marketCondition.getLatestCondition();
      setMarketCondition(condition);
    } catch (error) {
      console.error('Error fetching market condition:', error);
    }
  };

  const fetchAllData = async () => {
    setLoading(true);
    try {
      await Promise.all([
        fetchStrategies(),
        fetchDecantingOpportunities(), 
        fetchFlippingOpportunities(),
        fetchMarketCondition()
      ]);
    } finally {
      setLoading(false);
    }
  };

  const refreshData = async () => {
    setRefreshing(true);
    try {
      // Trigger backend scans
      await tradingStrategiesApiClient.massOperations.scanAllOpportunities();
      // Refresh market analysis
      await tradingStrategiesApiClient.marketCondition.analyzeMarket();
      // Reload all data
      await fetchAllData();
    } catch (error) {
      console.error('Error refreshing data:', error);
    } finally {
      setRefreshing(false);
    }
  };

  // Initial data load
  useEffect(() => {
    fetchAllData();
  }, []);

  // Filter and search functionality
  const filteredStrategies = strategies.filter(strategy => {
    const matchesSearch = searchTerm === '' || 
      strategy.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      strategy.description?.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesTab = activeTab === 'all' || strategy.strategy_type === activeTab;
    
    return matchesSearch && matchesTab;
  });

  const filteredDecanting = decantingOpportunities.filter(opp => 
    searchTerm === '' || 
    opp.item_name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const filteredFlipping = flippingOpportunities.filter(opp => 
    searchTerm === '' || 
    opp.item_name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // Tab configuration
  const tabs = [
    { id: 'all' as ActiveTab, label: 'All Strategies', icon: CubeIcon, count: strategies.length },
    { id: 'decanting' as ActiveTab, label: 'Decanting', icon: BeakerIcon, count: decantingOpportunities.length },
    { id: 'flipping' as ActiveTab, label: 'Flipping', icon: ArrowTrendingUpIcon, count: flippingOpportunities.length },
    { id: 'crafting' as ActiveTab, label: 'Crafting', icon: WrenchIcon, count: 0 },
    { id: 'set_combining' as ActiveTab, label: 'Set Combining', icon: CubeIcon, count: 0 }
  ];

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
          <h1 className="text-4xl font-bold text-gradient mb-4">
            Trading Strategies
          </h1>
          <p className="text-xl text-gray-400 max-w-2xl mx-auto">
            Advanced OSRS trading opportunities based on your friend's 100M GP success strategies
          </p>
        </motion.div>

        {/* Market Condition */}
        <MarketConditionDisplay 
          marketCondition={marketCondition}
          isLoading={loading}
        />

        {/* Controls */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6"
        >
          <div className="flex flex-col lg:flex-row gap-4 items-center justify-between">
            
            {/* Search Bar */}
            <div className="relative flex-1 max-w-md">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search strategies..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 bg-gray-700/50 border border-gray-600/50 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 text-white placeholder-gray-400"
              />
            </div>

            {/* Action Buttons */}
            <div className="flex gap-3">
              <button
                onClick={refreshData}
                disabled={refreshing}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800 disabled:opacity-50 text-white rounded-lg transition-colors"
              >
                <ArrowPathIcon className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
                {refreshing ? 'Refreshing...' : 'Refresh Data'}
              </button>
              
              <button className="flex items-center gap-2 px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded-lg transition-colors">
                <FunnelIcon className="w-4 h-4" />
                Filters
              </button>
            </div>
          </div>
        </motion.div>

        {/* Strategy Tabs */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6"
        >
          <div className="flex flex-wrap gap-2">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-all duration-200 ${
                    isActive 
                      ? 'bg-blue-600 text-white border border-blue-500' 
                      : 'bg-gray-700/50 text-gray-300 hover:bg-gray-600/50 hover:text-white border border-gray-600/50'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span className="font-medium">{tab.label}</span>
                  <span className="px-2 py-1 text-xs rounded-full bg-gray-600/50 text-gray-300">
                    {tab.count}
                  </span>
                </button>
              );
            })}
          </div>
        </motion.div>

        {/* Strategy Content */}
        <motion.div
          key={activeTab}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="space-y-6"
        >
          {/* Decanting Opportunities */}
          {(activeTab === 'all' || activeTab === 'decanting') && filteredDecanting.length > 0 && (
            <div className="space-y-4">
              {activeTab === 'all' && (
                <h2 className="text-2xl font-semibold text-gray-100 flex items-center gap-2">
                  <BeakerIcon className="w-6 h-6 text-blue-400" />
                  Decanting Opportunities
                </h2>
              )}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {filteredDecanting.map((opportunity) => (
                  <DecantingOpportunityCard
                    key={opportunity.id}
                    opportunity={opportunity}
                    onClick={() => console.log('View decanting opportunity:', opportunity.id)}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Flipping Opportunities */}
          {(activeTab === 'all' || activeTab === 'flipping') && filteredFlipping.length > 0 && (
            <div className="space-y-4">
              {activeTab === 'all' && (
                <h2 className="text-2xl font-semibold text-gray-100 flex items-center gap-2">
                  <ArrowTrendingUpIcon className="w-6 h-6 text-purple-400" />
                  Flipping Opportunities
                </h2>
              )}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {filteredFlipping.map((opportunity) => (
                  <FlippingOpportunityCard
                    key={opportunity.id}
                    opportunity={opportunity}
                    onClick={() => console.log('View flipping opportunity:', opportunity.id)}
                  />
                ))}
              </div>
            </div>
          )}

          {/* No Results */}
          {((activeTab === 'decanting' && filteredDecanting.length === 0) ||
            (activeTab === 'flipping' && filteredFlipping.length === 0) ||
            (activeTab === 'crafting') ||
            (activeTab === 'set_combining') ||
            (activeTab === 'all' && filteredDecanting.length === 0 && filteredFlipping.length === 0)) && (
            <div className="text-center py-12">
              <div className="w-16 h-16 bg-gray-700 rounded-full flex items-center justify-center mx-auto mb-4">
                <MagnifyingGlassIcon className="w-8 h-8 text-gray-500" />
              </div>
              <h3 className="text-lg font-semibold text-gray-400 mb-2">
                No {activeTab === 'all' ? 'strategies' : activeTab.replace('_', ' ')} found
              </h3>
              <p className="text-gray-500">
                {searchTerm ? 'Try adjusting your search terms' : 'No opportunities available at this time'}
              </p>
              {activeTab === 'crafting' || activeTab === 'set_combining' ? (
                <p className="text-sm text-blue-400 mt-2">
                  This strategy type is coming soon!
                </p>
              ) : null}
            </div>
          )}
        </motion.div>
      </div>
    </div>
  );
}

export default TradingStrategies;