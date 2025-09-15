import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  ArrowPathIcon,
  MagnifyingGlassIcon,
  BeakerIcon,
  FunnelIcon,
  XMarkIcon,
  SparklesIcon,
  ChartBarIcon,
  BoltIcon,
  ChatBubbleLeftRightIcon,
  TrophyIcon
} from '@heroicons/react/24/outline';

import { tradingStrategiesApiClient } from '../api/tradingStrategiesApi';
import { DecantingOpportunityCard } from '../components/trading/DecantingOpportunityCard';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { useReactiveTradingContext } from '../contexts/ReactiveTrading';
import RealtimePriceChart from '../components/trading/RealtimePriceChart';
import ProfitCalculator from '../components/trading/ProfitCalculator';
import AITradingAssistant from '../components/ai/AITradingAssistant';
import LiveProfitDashboard from '../components/trading/LiveProfitDashboard';
import AchievementSystem from '../components/gamification/AchievementSystem';
import PlayerLevel from '../components/gamification/PlayerLevel';
import StreakCounter from '../components/gamification/StreakCounter';
import QuickTradeModal from '../components/trading/QuickTradeModal';
import type { DecantingOpportunity } from '../types/tradingStrategies';

// Use real backend data - no mock data
const USE_MOCK_DATA = false;

export function DecantingView() {
  const [opportunities, setOpportunities] = useState<DecantingOpportunity[]>([]);
  const [loading, setLoading] = useState(true);
  // Removed refreshing, aiAnalyzing, and discovering states - data loads automatically
  const [searchTerm, setSearchTerm] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [selectedItemForChart, setSelectedItemForChart] = useState<number | null>(null);
  const [showReactiveFeatures, setShowReactiveFeatures] = useState(true);
  const [selectedOpportunityForCalculator, setSelectedOpportunityForCalculator] = useState<DecantingOpportunity | null>(null);
  const [showAIAssistant, setShowAIAssistant] = useState(false);
  const [currentCapital, setCurrentCapital] = useState(5000000); // 5M GP default
  const [showAchievements, setShowAchievements] = useState(false);
  const [selectedOpportunityForQuickTrade, setSelectedOpportunityForQuickTrade] = useState<DecantingOpportunity | null>(null);
  
  // Gamification state
  const [playerStats, setPlayerStats] = useState({
    totalProfit: 2500000, // Mock data for demo
    tradesExecuted: 15,
    currentStreak: 8,
    bestStreak: 12,
    sessionsPlayed: 3,
    totalPlayTime: 7200, // 2 hours
    opportunitiesDiscovered: 28,
    perfectTrades: 2,
    level: 7,
    currentXP: 850,
    xpToNextLevel: 150,
    totalXPForNextLevel: 1000,
    playerTitle: "Aspiring Alchemist"
  });

  // Handle quick trade completion
  const handleTradeComplete = (tradeResult: {
    profit: number;
    quantity: number;
    success: boolean;
    experience?: number;
  }) => {
    // Update player stats based on trade result
    setPlayerStats(prev => ({
      ...prev,
      totalProfit: Math.max(0, prev.totalProfit + tradeResult.profit),
      tradesExecuted: prev.tradesExecuted + 1,
      currentStreak: tradeResult.success ? prev.currentStreak + 1 : 0,
      bestStreak: tradeResult.success ? Math.max(prev.bestStreak, prev.currentStreak + 1) : prev.bestStreak,
      currentXP: prev.currentXP + (tradeResult.experience || 0)
    }));

    // Update current capital
    setCurrentCapital(prev => Math.max(0, prev + tradeResult.profit));

    console.log('Trade completed:', tradeResult);
  };
  
  // Real-time trading intelligence
  const { state: socketState, actions: socketActions } = useReactiveTradingContext();

  // Filter states
  const [filters, setFilters] = useState({
    minProfit: '',
    maxProfit: '',
    minGpPerHour: '',
    maxGpPerHour: '',
    riskLevel: '',
    minMargin: '',
    maxMargin: '',
    conversionType: '',
    potionType: '',
    potionFamily: '',  // New: prayer, combat, antifire, etc.
    minVolume: '',
    highVolumeOnly: false,
    highValueOnly: false,  // New: 500+ GP filter
    minCapital: '',
    maxCapital: '',
    minConfidence: '',
    ordering: 'profit_desc',  // New: sorting option
    hideTaxNegative: true,  // New: hide tax-negative trades by default
    minTaxAdjustedProfit: '',  // New: minimum profit after tax
    onlyProfitable: true  // New: only show tax-profitable trades
  });

  const [stats, setStats] = useState({
    totalOpportunities: 0,
    avgProfitPerConversion: 0,
    avgProfitPerHour: 0,
    topMargin: 0
  });

  const fetchDecantingOpportunities = async () => {
    setLoading(true);

    try {
      // Build filter parameters
      const filterParams: any = {
        is_active: true,
        page_size: 50,
        search: searchTerm || undefined,
      };

      // Add all active filters - set min_profit low enough to capture high-value opportunities
      filterParams.min_profit = filters.minProfit ? parseInt(filters.minProfit) : 10;
      if (filters.maxProfit) filterParams.max_profit = parseInt(filters.maxProfit);
      if (filters.minGpPerHour) filterParams.min_gp_per_hour = parseInt(filters.minGpPerHour);
      if (filters.maxGpPerHour) filterParams.max_gp_per_hour = parseInt(filters.maxGpPerHour);
      if (filters.riskLevel) filterParams.risk_level = filters.riskLevel;
      if (filters.minMargin) filterParams.min_margin = parseFloat(filters.minMargin);
      if (filters.maxMargin) filterParams.max_margin = parseFloat(filters.maxMargin);
      if (filters.conversionType) filterParams.conversion_type = filters.conversionType;
      if (filters.potionType) filterParams.potion_type = filters.potionType;
      if (filters.minVolume) filterParams.min_volume = parseInt(filters.minVolume);
      if (filters.highVolumeOnly) filterParams.high_volume_only = true;
      if (filters.minCapital) filterParams.min_capital = parseInt(filters.minCapital);
      if (filters.maxCapital) filterParams.max_capital = parseInt(filters.maxCapital);
      if (filters.minConfidence) filterParams.min_confidence = parseFloat(filters.minConfidence);
      
      // New enhanced filters
      if (filters.potionFamily) filterParams.potion_family = filters.potionFamily;
      if (filters.highValueOnly) filterParams.high_value_only = true;
      if (filters.ordering) filterParams.ordering = filters.ordering;
      
      // Load fresh data automatically

      // Use AI-enhanced opportunities with RuneScape Wiki pricing
      const response = await tradingStrategiesApiClient.decanting.getAIOpportunities(filterParams);
      const opportunities = response.results;
      
      setOpportunities(opportunities);

      // Stats will be calculated in a separate useEffect after filtering
    } catch (error) {
      console.error('Error fetching decanting opportunities:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDecantingOpportunities();
  }, [searchTerm, filters]);

  // Calculate accurate stats based on filtered and sorted opportunities
  useEffect(() => {
    const visibleOpportunities = getFilteredAndSortedOpportunities();
    if (visibleOpportunities.length > 0) {
      setStats({
        totalOpportunities: visibleOpportunities.length,
        avgProfitPerConversion: visibleOpportunities.reduce((sum, opp) => sum + opp.profit_per_conversion, 0) / visibleOpportunities.length,
        avgProfitPerHour: visibleOpportunities.reduce((sum, opp) => sum + opp.profit_per_hour, 0) / visibleOpportunities.length,
        topMargin: Math.max(...visibleOpportunities.map(opp => opp.strategy.profit_margin_pct))
      });
    } else {
      setStats({
        totalOpportunities: 0,
        avgProfitPerConversion: 0,
        avgProfitPerHour: 0,
        topMargin: 0
      });
    }
  }, [opportunities, filters]); // Recalculate when opportunities or filters change

  // Real-time WebSocket integration with proper dependency management
  useEffect(() => {
    if (socketState?.isConnected) {
      console.log('🔌 WebSocket connected, subscribing to decanting updates...');
      
      // Use a flag to prevent multiple subscriptions
      let subscribed = false;
      
      const subscribeToDecanting = () => {
        if (!subscribed) {
          const success = socketActions.subscribeToRoute('decanting');
          if (success) {
            subscribed = true;
            console.log('✅ Successfully subscribed to decanting route');
            
            // Get current data only after successful subscription
            socketActions.getCurrentRecommendations('decanting');
            socketActions.getMarketAlerts();
          }
        }
      };
      
      // Small delay to ensure WebSocket is fully ready
      const timeoutId = setTimeout(subscribeToDecanting, 100);
      
      return () => {
        clearTimeout(timeoutId);
        if (subscribed) {
          console.log('🧹 Cleaning up decanting subscriptions...');
          // Clean up on unmount or connection change
        }
      };
    }
  }, [socketState?.isConnected]); // Only depend on connection state
  
  // Centralized item subscriptions - subscribe to all visible opportunities efficiently
  useEffect(() => {
    if (socketState?.isConnected && opportunities.length > 0) {
      // Get unique item IDs to avoid duplicate subscriptions
      const itemIds = opportunities.map(opp => opp.item_id.toString());
      const uniqueItemIds = [...new Set(itemIds)];
      
      console.log(`📡 DecantingView: Batch subscribing to ${uniqueItemIds.length} unique items`);
      
      // Subscribe to all visible items
      const subscriptionPromises = uniqueItemIds.map(itemId => {
        return socketActions.subscribeToItem(itemId);
      });
      
      // Only clean up if we actually have subscriptions
      const hasSubscriptions = subscriptionPromises.some(Boolean);
      
      if (hasSubscriptions) {
        return () => {
          console.log('🧹 DecantingView: Cleaning up batch item subscriptions...');
          uniqueItemIds.forEach(itemId => {
            socketActions.unsubscribeFromItem(itemId);
          });
        };
      }
    }
  }, [socketState?.isConnected, JSON.stringify(opportunities.map(o => o.item_id))]); // Only re-run when actual item IDs change
  
  // Component unmount cleanup
  useEffect(() => {
    return () => {
      // Clean up subscriptions when DecantingView unmounts
      console.log('🧹 DecantingView unmounting, cleaning up all subscriptions...');
      // Note: Actual cleanup is handled by the WebSocket hook itself and above useEffect
    };
  }, []); // Empty deps - only run on mount/unmount

  // Handle real-time recommendation updates
  useEffect(() => {
    const decantingRecommendations = socketState?.recommendations?.['decanting'];
    if (decantingRecommendations && decantingRecommendations.length > 0) {
      console.log('🔄 Received real-time decanting recommendations:', decantingRecommendations);
      
      // Update opportunities with real-time data if they match our current view
      setOpportunities(prevOpportunities => {
        const updatedOpportunities = [...prevOpportunities];
        
        decantingRecommendations.forEach((rec: any) => {
          const existingIndex = updatedOpportunities.findIndex(opp => opp.item_id === rec.item_id);
          if (existingIndex !== -1) {
            // Update existing opportunity with real-time data
            updatedOpportunities[existingIndex] = {
              ...updatedOpportunities[existingIndex],
              ai_confidence: rec.confidence,
              ai_timing: rec.timing || 'immediate',
              ai_recommendations: rec.ai_reasoning ? [rec.ai_reasoning] : [],
              last_updated: new Date().toISOString()
            };
          }
        });
        
        return updatedOpportunities;
      });
    }
  }, [socketState?.recommendations]);

  // Handle real-time price updates
  useEffect(() => {
    const priceUpdates = Object.values(socketState?.priceUpdates || {});
    if (priceUpdates.length > 0) {
      console.log('💰 Received real-time price updates:', priceUpdates);
      
      // Update opportunities with latest price data
      setOpportunities(prevOpportunities => {
        const updatedOpportunities = [...prevOpportunities];
        
        priceUpdates.forEach((priceUpdate: any) => {
          const opportunityIndex = updatedOpportunities.findIndex(opp => opp.item_id === priceUpdate.item_id);
          if (opportunityIndex !== -1) {
            const opportunity = updatedOpportunities[opportunityIndex];
            
            // Update prices if they've changed significantly (>1% change)
            const currentPrice = (priceUpdate.high_price + priceUpdate.low_price) / 2;
            const oldPrice = (opportunity.from_dose_price + opportunity.to_dose_price) / 2;
            const priceChangePercent = Math.abs((currentPrice - oldPrice) / oldPrice * 100);
            
            if (priceChangePercent > 1) {
              updatedOpportunities[opportunityIndex] = {
                ...opportunity,
                from_dose_price: priceUpdate.low_price,
                to_dose_price: priceUpdate.high_price,
                last_updated: priceUpdate.timestamp
              };
            }
          }
        });
        
        return updatedOpportunities;
      });
    }
  }, [socketState?.priceUpdates]);

  const handleFilterChange = (key: string, value: any) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  const clearFilters = () => {
    setFilters({
      minProfit: '',
      maxProfit: '',
      minGpPerHour: '',
      maxGpPerHour: '',
      riskLevel: '',
      minMargin: '',
      maxMargin: '',
      conversionType: '',
      potionType: '',
      potionFamily: '',
      minVolume: '',
      highVolumeOnly: false,
      highValueOnly: false,
      minCapital: '',
      maxCapital: '',
      minConfidence: '',
      ordering: 'profit_desc',
      hideTaxNegative: true,  // Keep this enabled by default
      minTaxAdjustedProfit: '',
      onlyProfitable: true  // Keep this enabled by default
    });
  };

  // Removed action button handlers - data loads automatically when navigating to route

  // Tax calculation for filtering (same as in card component)
  const calculateTaxedProfitForFiltering = (opportunity: DecantingOpportunity) => {
    const buyPrice = opportunity.from_dose_price;
    const sellPrice = opportunity.to_dose_price;
    const dosesPerConversion = opportunity.from_dose;
    
    const totalBuyCost = buyPrice;
    const buyTax = totalBuyCost * 0.02;
    const totalBuyCostWithTax = totalBuyCost + buyTax;
    
    const totalSellRevenue = sellPrice * dosesPerConversion;
    const sellTax = totalSellRevenue * 0.02;
    const totalSellRevenueAfterTax = totalSellRevenue - sellTax;
    
    const netProfit = totalSellRevenueAfterTax - totalBuyCostWithTax;
    
    return {
      netProfit: Math.floor(netProfit),
      isProfit: netProfit > 0
    };
  };

  // Helper function to determine if an opportunity is recommended (now tax-aware)
  const isRecommended = (opportunity: DecantingOpportunity) => {
    const taxedResult = calculateTaxedProfitForFiltering(opportunity);
    
    // Primary check: must be profitable after tax
    if (!taxedResult.isProfit) {
      return false;
    }
    // Check risk assessment recommendation first (most reliable)
    if (opportunity.risk_assessment?.recommendation) {
      const recommendation = opportunity.risk_assessment.recommendation.toLowerCase();
      
      // Check for positive recommendation patterns
      const isPositive = recommendation.includes('✅') || 
                        recommendation.includes('recommended') ||
                        recommendation.includes('good') ||
                        recommendation.includes('high confidence');
      
      // Check for negative recommendation patterns
      const isNegative = recommendation.includes('❌') || 
                        recommendation.includes('not recommended') ||
                        recommendation.includes('avoid') ||
                        recommendation.includes('low confidence') ||
                        recommendation.includes('high risk');
      
      // Return true only if positive and not negative
      if (isPositive && !isNegative) return true;
      if (isNegative) return false;
    }
    
    // Fallback to AI confidence and other metrics
    if (opportunity.ai_confidence && opportunity.ai_confidence >= 0.7) {
      return true;
    }
    
    // Check if AI timing suggests immediate action
    if (opportunity.ai_timing === 'immediate') {
      return true;
    }
    
    // Check if confidence score is high
    if (opportunity.confidence_score && opportunity.confidence_score >= 70) {
      return true;
    }
    
    return false;
  };

  // Filter and sort opportunities with tax-awareness
  const getFilteredAndSortedOpportunities = () => {
    let filtered = [...opportunities];
    
    // Apply tax-based filtering
    if (filters.onlyProfitable) {
      filtered = filtered.filter(opp => {
        const taxedResult = calculateTaxedProfitForFiltering(opp);
        return taxedResult.isProfit;
      });
    }
    
    if (filters.hideTaxNegative) {
      filtered = filtered.filter(opp => {
        const taxedResult = calculateTaxedProfitForFiltering(opp);
        return taxedResult.isProfit;
      });
    }
    
    if (filters.minTaxAdjustedProfit) {
      const minProfit = parseInt(filters.minTaxAdjustedProfit);
      filtered = filtered.filter(opp => {
        const taxedResult = calculateTaxedProfitForFiltering(opp);
        return taxedResult.netProfit >= minProfit;
      });
    }
    
    // Sort by tax-adjusted profit and recommendation status
    return filtered.sort((a, b) => {
      const aTaxed = calculateTaxedProfitForFiltering(a);
      const bTaxed = calculateTaxedProfitForFiltering(b);
      const aRecommended = isRecommended(a);
      const bRecommended = isRecommended(b);
      
      // First priority: profitable vs non-profitable
      if (aTaxed.isProfit !== bTaxed.isProfit) {
        return bTaxed.isProfit ? 1 : -1;
      }
      
      // Second priority: recommended vs not recommended (among profitable)
      if (aTaxed.isProfit && bTaxed.isProfit && aRecommended !== bRecommended) {
        return aRecommended ? -1 : 1;
      }
      
      // Third priority: actual tax-adjusted profit
      return bTaxed.netProfit - aTaxed.netProfit;
    });
  };
  
  const sortedOpportunities = getFilteredAndSortedOpportunities();

  const formatGP = (amount: number) => {
    if (amount >= 1000000) {
      return `${(amount / 1000000).toFixed(1)}M`;
    } else if (amount >= 1000) {
      return `${(amount / 1000).toFixed(1)}K`;
    }
    return Math.round(amount).toLocaleString();
  };

  const formatPercentage = (value: number) => {
    return `${value.toFixed(1)}%`;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 p-6">
        <div className="max-w-7xl mx-auto">
          <div className="flex flex-col items-center justify-center py-20">
            <LoadingSpinner size="lg" />
            <div className="mt-6 text-center">
              <h3 className="text-xl font-semibold text-gray-200 mb-2">
                Analyzing Decanting Opportunities
              </h3>
              <p className="text-gray-400 max-w-md">
                Discovering potion families and fetching fresh Grand Exchange prices from OSRS Wiki API...
              </p>
              <p className="text-sm text-gray-500 mt-2">
                This may take 30-60 seconds for fresh market data
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Removed AI analyzing loading screen - using automatic data loading

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
            <div className="p-3 bg-blue-400/10 rounded-xl">
              <BeakerIcon className="w-8 h-8 text-blue-400" />
            </div>
            <h1 className="text-4xl font-bold text-gradient">
              Decanting Opportunities
            </h1>
          </div>
          <p className="text-xl text-gray-400 max-w-2xl mx-auto">
            AI-powered decanting analysis using 3 Ollama models for optimal profit opportunities
          </p>
          <div className="mt-4 space-y-2">
            {filters.onlyProfitable && (
              <div className="inline-flex items-center gap-2 px-4 py-2 bg-green-900/20 border border-green-500/30 rounded-lg">
                <span className="text-green-400 text-sm">✅</span>
                <span className="text-green-300 text-sm">
                  Showing only tax-profitable trades • {sortedOpportunities.length} opportunities after GE tax filtering
                </span>
              </div>
            )}
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-blue-900/20 border border-blue-500/30 rounded-lg">
              <span className="text-blue-400 text-sm">🔍</span>
              <span className="text-blue-300 text-sm">
                All profit calculations include 4% Grand Exchange tax (2% buy + 2% sell)
              </span>
            </div>
          </div>
        </motion.div>

        {/* Player Progress & Gamification */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05 }}
          className="grid grid-cols-1 lg:grid-cols-3 gap-4"
        >
          {/* Player Level */}
          <PlayerLevel
            currentXP={playerStats.currentXP}
            level={playerStats.level}
            xpToNextLevel={playerStats.xpToNextLevel}
            totalXPForNextLevel={playerStats.totalXPForNextLevel}
            playerTitle={playerStats.playerTitle}
            achievements={3} // Count of unlocked achievements
            showDetailed={false}
          />
          
          {/* Current Streak */}
          <StreakCounter
            currentStreak={playerStats.currentStreak}
            bestStreak={playerStats.bestStreak}
            streakType="profit"
            showAnimation={true}
          />
          
          {/* Achievement Button */}
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => setShowAchievements(true)}
            className="bg-gradient-to-r from-yellow-900/40 to-orange-900/40 border border-yellow-500/30 rounded-xl p-4 text-left hover:from-yellow-800/40 hover:to-orange-800/40 transition-all"
          >
            <div className="flex items-center gap-3">
              <div className="p-2 bg-yellow-500/20 rounded-lg">
                <TrophyIcon className="w-6 h-6 text-yellow-400" />
              </div>
              <div>
                <div className="text-yellow-400 font-bold text-lg">3 / 11</div>
                <div className="text-sm text-gray-300">Achievements Unlocked</div>
                <div className="text-xs text-yellow-300 mt-1">Click to view progress</div>
              </div>
            </div>
          </motion.button>
        </motion.div>

        {/* Stats Overview */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="grid grid-cols-2 md:grid-cols-5 gap-4"
        >
          <div className="bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6 text-center">
            <div className="text-2xl font-bold text-blue-400 mb-1">{stats.totalOpportunities}</div>
            <div className="text-sm text-gray-400">Active Opportunities</div>
          </div>
          <div className="bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6 text-center">
            <div className="text-2xl font-bold text-green-400 mb-1">{formatGP(stats.avgProfitPerConversion)}</div>
            <div className="text-sm text-gray-400">Avg Profit/Convert</div>
          </div>
          <div className="bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6 text-center">
            <div className="text-2xl font-bold text-emerald-400 mb-1">{formatGP(stats.avgProfitPerHour)}</div>
            <div className="text-sm text-gray-400">Avg GP/Hour</div>
          </div>
          <div className="bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6 text-center">
            <div className="text-2xl font-bold text-purple-400 mb-1">{formatPercentage(stats.topMargin)}</div>
            <div className="text-sm text-gray-400">Top Margin</div>
          </div>
          {/* Real-time WebSocket Status */}
          <div className="bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6 text-center">
            <div className="flex items-center justify-center gap-2 mb-1">
              <div className={`w-3 h-3 rounded-full ${socketState?.isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
              <div className={`text-2xl font-bold ${socketState?.isConnected ? 'text-green-400' : 'text-red-400'}`}>
                {socketState?.isConnected ? 'LIVE' : 'OFF'}
              </div>
            </div>
            <div className="text-sm text-gray-400">AI Trading Intelligence</div>
          </div>
        </motion.div>

        {/* Live Profit Tracking Dashboard */}
        <LiveProfitDashboard 
          opportunities={getFilteredAndSortedOpportunities()}
          currentCapital={currentCapital}
          onCapitalChange={setCurrentCapital}
        />

        {/* Reactive AI Intelligence Dashboard */}
        {showReactiveFeatures && socketState?.isConnected && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 }}
            className="bg-gradient-to-r from-blue-900/20 via-purple-900/20 to-blue-900/20 backdrop-blur-sm border border-blue-500/30 rounded-xl p-6"
          >
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-500/20 rounded-lg">
                  <SparklesIcon className="w-6 h-6 text-blue-400" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-blue-400">🚀 AI Super Trader Intelligence</h3>
                  <p className="text-sm text-gray-400">Real-time market analysis and pattern detection</p>
                </div>
              </div>
              <button
                onClick={() => setShowReactiveFeatures(!showReactiveFeatures)}
                className="text-gray-400 hover:text-gray-300 transition-colors"
              >
                <XMarkIcon className="w-5 h-5" />
              </button>
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
                <div className="text-xs text-gray-400 space-y-1 max-h-16 overflow-y-auto">
                  {(socketState?.marketEvents || []).slice(0, 3).map((event, index) => (
                    <div key={index} className="flex items-center gap-2">
                      <span className="text-green-400">•</span>
                      <span>{event.event_type}</span>
                      {event.item_id && <span className="text-blue-400">#{event.item_id}</span>}
                    </div>
                  ))}
                  {(socketState?.marketEvents?.length || 0) === 0 && (
                    <div className="text-gray-500">Monitoring for events...</div>
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
                <div className="text-xs text-gray-400 space-y-1 max-h-16 overflow-y-auto">
                  {(socketState?.patternDetections || []).slice(0, 3).map((pattern, index) => (
                    <div key={index} className="flex items-center gap-2">
                      <span className="text-yellow-400">•</span>
                      <span>{pattern.pattern_name}</span>
                      <span className="text-purple-400">{(pattern.confidence * 100).toFixed(0)}%</span>
                    </div>
                  ))}
                  {(socketState?.patternDetections?.length || 0) === 0 && (
                    <div className="text-gray-500">Analyzing patterns...</div>
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
                <div className="text-xs text-gray-400 space-y-1 max-h-16 overflow-y-auto">
                  {(socketState?.marketAlerts || []).filter(alert => alert.is_active).slice(0, 3).map((alert, index) => (
                    <div key={index} className="flex items-center gap-2">
                      <span className="text-red-400">•</span>
                      <span>{alert.alert_type}</span>
                      {alert.item_name && <span className="text-blue-400">{alert.item_name}</span>}
                    </div>
                  ))}
                  {(socketState?.marketAlerts || []).filter(alert => alert.is_active).length === 0 && (
                    <div className="text-gray-500">No active alerts</div>
                  )}
                </div>
              </div>
            </div>

            {/* Real-time Recommendations */}
            {socketState?.recommendations?.['decanting'] && socketState?.recommendations?.['decanting'].length > 0 && (
              <div className="bg-gray-800/30 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-3">
                  <SparklesIcon className="w-4 h-4 text-purple-400" />
                  <span className="text-sm font-medium text-purple-400">Live AI Recommendations</span>
                  <span className="text-xs bg-purple-500/20 text-purple-400 px-2 py-0.5 rounded-full">
                    {socketState?.recommendations?.['decanting']?.length || 0}
                  </span>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {(socketState?.recommendations?.['decanting'] || []).slice(0, 4).map((rec: any, index: number) => (
                    <div key={index} className="bg-gray-700/30 rounded p-3">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm font-medium text-blue-400">
                          {rec.item_name || `Item #${rec.item_id}`}
                        </span>
                        <span className="text-xs text-green-400">
                          {(rec.confidence * 100).toFixed(0)}% confidence
                        </span>
                      </div>
                      <div className="text-xs text-gray-400">
                        {rec.ai_reasoning || 'AI-powered recommendation'}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </motion.div>
        )}

        {/* Real-time Price Chart Modal */}
        {selectedItemForChart && (
          <RealtimePriceChart
            itemId={selectedItemForChart}
            itemName={opportunities.find(opp => opp.item_id === selectedItemForChart)?.item_name || `Item #${selectedItemForChart}`}
            height={500}
            showVolume={true}
            showPatterns={true}
            displayMode="modal"
            onClose={() => setSelectedItemForChart(null)}
            chartType="line"
            showTechnicalIndicators={true}
          />
        )}

        {/* Controls */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6 space-y-4"
        >
          {/* Top Row: Search, Filter Toggle, Action Buttons */}
          <div className="flex flex-col lg:flex-row gap-4 items-center justify-between">
            
            {/* Search Bar */}
            <div className="relative flex-1 max-w-md">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search potions..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 bg-gray-700/50 border border-gray-600/50 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 text-white placeholder-gray-400"
              />
            </div>

            {/* Sort, Filter Toggle and Action Buttons */}
            <div className="flex gap-3 items-center">
              {/* Sorting Dropdown */}
              <select
                value={filters.ordering}
                onChange={(e) => handleFilterChange('ordering', e.target.value)}
                className="px-3 py-2 bg-gray-700/50 border border-gray-600/50 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50"
              >
                <option value="profit_desc">🥇 Highest Profit</option>
                <option value="gp_per_hour_desc">⏱️ Best GP/Hour</option>
                <option value="confidence_desc">🤖 AI Confidence</option>
                <option value="model_agreement_desc">🎯 Model Agreement</option>
              </select>

              <button
                onClick={() => setShowFilters(!showFilters)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                  showFilters 
                    ? 'bg-blue-600 text-white' 
                    : 'bg-gray-700 hover:bg-gray-600 text-gray-300'
                }`}
              >
                <FunnelIcon className="w-4 h-4" />
                Filters
              </button>
              
              {/* Removed action buttons - data loads automatically when navigating to decanting route */}
            </div>
          </div>

          {/* Advanced Filters Panel */}
          {showFilters && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="border-t border-gray-700/50 pt-4 space-y-4"
            >
              {/* Filter Header */}
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-200">Advanced Filters</h3>
                <button
                  onClick={clearFilters}
                  className="flex items-center gap-2 px-3 py-1 text-sm bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-lg transition-colors"
                >
                  <XMarkIcon className="w-4 h-4" />
                  Clear All
                </button>
              </div>

              {/* Filter Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                
                {/* Potion Family */}
                <div className="space-y-2">
                  <label className="text-sm font-medium text-blue-400">🧪 Potion Family</label>
                  <select
                    value={filters.potionFamily}
                    onChange={(e) => handleFilterChange('potionFamily', e.target.value)}
                    className="w-full px-3 py-2 bg-gray-700/50 border border-gray-600/50 rounded-lg text-white text-sm focus:outline-none focus:ring-1 focus:ring-blue-500/50"
                  >
                    <option value="">All Families</option>
                    <option value="prayer">🙏 Prayer & Restore</option>
                    <option value="combat">⚔️ Combat Potions</option>
                    <option value="ranging">🏹 Ranging Potions</option>
                    <option value="magic">🔮 Magic Potions</option>
                    <option value="antifire">🐉 Antifire Potions</option>
                    <option value="stamina">🏃 Stamina & Energy</option>
                    <option value="brew">🍺 Saradomin Brew</option>
                    <option value="divine">✨ Divine Potions</option>
                  </select>
                </div>

                {/* Quick Filters */}
                <div className="space-y-2">
                  <label className="text-sm font-medium text-green-400">🎯 Quick Filters</label>
                  <div className="space-y-2">
                    <label className="flex items-center space-x-2">
                      <input
                        type="checkbox"
                        checked={filters.highValueOnly}
                        onChange={(e) => handleFilterChange('highValueOnly', e.target.checked)}
                        className="w-4 h-4 text-green-600 bg-gray-700 border-gray-600 rounded focus:ring-green-500 focus:ring-2"
                      />
                      <span className="text-sm text-green-400">💎 High Value (500+ GP)</span>
                    </label>
                    <label className="flex items-center space-x-2">
                      <input
                        type="checkbox"
                        checked={filters.highVolumeOnly}
                        onChange={(e) => handleFilterChange('highVolumeOnly', e.target.checked)}
                        className="w-4 h-4 text-blue-600 bg-gray-700 border-gray-600 rounded focus:ring-blue-500 focus:ring-2"
                      />
                      <span className="text-sm text-blue-400">📈 High Volume</span>
                    </label>
                  </div>
                </div>
                
                {/* Profit Range */}
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-300">Profit/Conversion (GP)</label>
                  <div className="flex gap-2">
                    <input
                      type="number"
                      placeholder="Min"
                      value={filters.minProfit}
                      onChange={(e) => handleFilterChange('minProfit', e.target.value)}
                      className="flex-1 px-3 py-2 bg-gray-700/50 border border-gray-600/50 rounded-lg text-white text-sm placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-blue-500/50"
                    />
                    <input
                      type="number"
                      placeholder="Max"
                      value={filters.maxProfit}
                      onChange={(e) => handleFilterChange('maxProfit', e.target.value)}
                      className="flex-1 px-3 py-2 bg-gray-700/50 border border-gray-600/50 rounded-lg text-white text-sm placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-blue-500/50"
                    />
                  </div>
                </div>

                {/* GP/Hour Range */}
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-300">GP/Hour</label>
                  <div className="flex gap-2">
                    <input
                      type="number"
                      placeholder="Min"
                      value={filters.minGpPerHour}
                      onChange={(e) => handleFilterChange('minGpPerHour', e.target.value)}
                      className="flex-1 px-3 py-2 bg-gray-700/50 border border-gray-600/50 rounded-lg text-white text-sm placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-blue-500/50"
                    />
                    <input
                      type="number"
                      placeholder="Max"
                      value={filters.maxGpPerHour}
                      onChange={(e) => handleFilterChange('maxGpPerHour', e.target.value)}
                      className="flex-1 px-3 py-2 bg-gray-700/50 border border-gray-600/50 rounded-lg text-white text-sm placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-blue-500/50"
                    />
                  </div>
                </div>

                {/* Risk Level */}
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-300">Risk Level</label>
                  <select
                    value={filters.riskLevel}
                    onChange={(e) => handleFilterChange('riskLevel', e.target.value)}
                    className="w-full px-3 py-2 bg-gray-700/50 border border-gray-600/50 rounded-lg text-white text-sm focus:outline-none focus:ring-1 focus:ring-blue-500/50"
                  >
                    <option value="">Any</option>
                    <option value="low">Low Risk</option>
                    <option value="medium">Medium Risk</option>
                    <option value="high">High Risk</option>
                  </select>
                </div>

                {/* Conversion Type */}
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-300">Conversion Type</label>
                  <select
                    value={filters.conversionType}
                    onChange={(e) => handleFilterChange('conversionType', e.target.value)}
                    className="w-full px-3 py-2 bg-gray-700/50 border border-gray-600/50 rounded-lg text-white text-sm focus:outline-none focus:ring-1 focus:ring-blue-500/50"
                  >
                    <option value="">Any</option>
                    <option value="4_to_3">4-dose → 3-dose</option>
                    <option value="4_to_2">4-dose → 2-dose</option>
                    <option value="4_to_1">4-dose → 1-dose</option>
                    <option value="3_to_2">3-dose → 2-dose</option>
                    <option value="3_to_1">3-dose → 1-dose</option>
                    <option value="2_to_1">2-dose → 1-dose</option>
                  </select>
                </div>

                {/* Profit Margin */}
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-300">Profit Margin (%)</label>
                  <div className="flex gap-2">
                    <input
                      type="number"
                      placeholder="Min"
                      step="0.1"
                      value={filters.minMargin}
                      onChange={(e) => handleFilterChange('minMargin', e.target.value)}
                      className="flex-1 px-3 py-2 bg-gray-700/50 border border-gray-600/50 rounded-lg text-white text-sm placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-blue-500/50"
                    />
                    <input
                      type="number"
                      placeholder="Max"
                      step="0.1"
                      value={filters.maxMargin}
                      onChange={(e) => handleFilterChange('maxMargin', e.target.value)}
                      className="flex-1 px-3 py-2 bg-gray-700/50 border border-gray-600/50 rounded-lg text-white text-sm placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-blue-500/50"
                    />
                  </div>
                </div>

                {/* Potion Type */}
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-300">Potion Type</label>
                  <select
                    value={filters.potionType}
                    onChange={(e) => handleFilterChange('potionType', e.target.value)}
                    className="w-full px-3 py-2 bg-gray-700/50 border border-gray-600/50 rounded-lg text-white text-sm focus:outline-none focus:ring-1 focus:ring-blue-500/50"
                  >
                    <option value="">Any</option>
                    <option value="combat">Combat</option>
                    <option value="prayer">Prayer</option>
                    <option value="strength">Strength</option>
                    <option value="attack">Attack</option>
                    <option value="defence">Defence</option>
                    <option value="ranging">Ranging</option>
                    <option value="magic">Magic</option>
                    <option value="antifire">Antifire</option>
                    <option value="poison">Antipoison</option>
                  </select>
                </div>

                {/* Minimum Volume */}
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-300">Min Volume</label>
                  <input
                    type="number"
                    placeholder="Min trading volume"
                    value={filters.minVolume}
                    onChange={(e) => handleFilterChange('minVolume', e.target.value)}
                    className="w-full px-3 py-2 bg-gray-700/50 border border-gray-600/50 rounded-lg text-white text-sm placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-blue-500/50"
                  />
                </div>

                {/* Capital Range */}
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-300">Required Capital (GP)</label>
                  <div className="flex gap-2">
                    <input
                      type="number"
                      placeholder="Min"
                      value={filters.minCapital}
                      onChange={(e) => handleFilterChange('minCapital', e.target.value)}
                      className="flex-1 px-3 py-2 bg-gray-700/50 border border-gray-600/50 rounded-lg text-white text-sm placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-blue-500/50"
                    />
                    <input
                      type="number"
                      placeholder="Max"
                      value={filters.maxCapital}
                      onChange={(e) => handleFilterChange('maxCapital', e.target.value)}
                      className="flex-1 px-3 py-2 bg-gray-700/50 border border-gray-600/50 rounded-lg text-white text-sm placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-blue-500/50"
                    />
                  </div>
                </div>
              </div>

              {/* Additional Filter Options Row */}
              <div className="flex flex-wrap gap-4 items-center pt-2">
                <div className="space-y-1">
                  <label className="text-sm font-medium text-gray-300">🤖 Min AI Confidence</label>
                  <input
                    type="number"
                    placeholder="0.0 - 1.0"
                    step="0.1"
                    min="0"
                    max="1"
                    value={filters.minConfidence}
                    onChange={(e) => handleFilterChange('minConfidence', e.target.value)}
                    className="w-28 px-3 py-1 bg-gray-700/50 border border-gray-600/50 rounded-lg text-white text-sm placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-blue-500/50"
                  />
                  <div className="text-xs text-gray-500">0.6+ recommended</div>
                </div>
              </div>
            </motion.div>
          )}
        </motion.div>

        {/* Decanting Opportunities Grid */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="grid grid-cols-1 lg:grid-cols-2 gap-6"
        >
          {sortedOpportunities.map((opportunity) => {
            // Find real-time data for this specific opportunity
            const realtimeItemData = socketState?.marketData?.find(
              (data: any) => data.item_id === opportunity.item_id
            );
            
            // Extract AI insights for this item
            const aiInsights = socketState?.aiAnalysis?.find(
              (analysis: any) => analysis.item_id === opportunity.item_id
            );

            return (
              <DecantingOpportunityCard
                key={opportunity.id}
                opportunity={opportunity}
                realtimeData={realtimeItemData}
                aiInsights={aiInsights}
                onClick={() => {
                  console.log('View decanting opportunity:', opportunity.id);
                  // Show real-time price chart for this item
                  setSelectedItemForChart(opportunity.item_id);
                  // Subscribe to real-time updates for this item only if connected
                  if (socketState?.isConnected) {
                    socketActions.subscribeToItem(opportunity.item_id.toString());
                  }
                }}
                onCalculateProfit={() => {
                  setSelectedOpportunityForCalculator(opportunity);
                }}
                onQuickTrade={() => {
                  setSelectedOpportunityForQuickTrade(opportunity);
                }}
              />
            );
          })}
        </motion.div>

        {/* No Results */}
        {sortedOpportunities.length === 0 && !loading && (
          <div className="text-center py-12">
            <div className="w-16 h-16 bg-gray-700 rounded-full flex items-center justify-center mx-auto mb-4">
              <BeakerIcon className="w-8 h-8 text-gray-500" />
            </div>
            <h3 className="text-lg font-semibold text-gray-400 mb-2">
              No Decanting Opportunities Found
            </h3>
            <p className="text-gray-500">
              {searchTerm ? 'Try adjusting your search terms' : 'No profitable decanting opportunities available at this time'}
            </p>
            {/* Removed action buttons from no results section - data loads automatically */}
          </div>
        )}

        {/* Profit Calculator Modal */}
        {selectedOpportunityForCalculator && (
          <ProfitCalculator
            opportunity={selectedOpportunityForCalculator}
            onClose={() => setSelectedOpportunityForCalculator(null)}
            onStartTrading={(opportunity, capital) => {
              // Start trading by opening Quick Trade Modal
              setSelectedOpportunityForQuickTrade(opportunity);
            }}
            onSaveStrategy={(opportunity, calculations) => {
              console.log('Strategy saved for:', opportunity.item_name, calculations);
              // Could implement backend API call here to persist strategies
            }}
          />
        )}

        {/* AI Trading Assistant Modal */}
        <AITradingAssistant
          isOpen={showAIAssistant}
          onClose={() => setShowAIAssistant(false)}
          opportunities={sortedOpportunities}
          currentCapital={currentCapital}
        />

        {/* Achievement System Modal */}
        <AchievementSystem
          isOpen={showAchievements}
          onClose={() => setShowAchievements(false)}
          playerStats={playerStats}
          onAchievementUnlocked={(achievement) => {
            console.log('Achievement unlocked:', achievement.title);
            // In a real app, you'd save this to backend/localStorage
          }}
        />

        {/* Quick Trade Modal */}
        {selectedOpportunityForQuickTrade && (
          <QuickTradeModal
            isOpen={!!selectedOpportunityForQuickTrade}
            onClose={() => setSelectedOpportunityForQuickTrade(null)}
            opportunity={selectedOpportunityForQuickTrade}
            currentCapital={currentCapital}
            onTradeComplete={handleTradeComplete}
          />
        )}

        {/* Floating AI Assistant Button */}
        <motion.button
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.9 }}
          onClick={() => setShowAIAssistant(true)}
          className="fixed bottom-6 right-6 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white p-4 rounded-full shadow-2xl border border-blue-500/30 transition-all duration-200 z-40"
        >
          <ChatBubbleLeftRightIcon className="w-6 h-6" />
          <div className="absolute -top-1 -right-1 w-3 h-3 bg-green-400 rounded-full animate-pulse" />
        </motion.button>
      </div>
    </div>
  );
}

export default DecantingView;