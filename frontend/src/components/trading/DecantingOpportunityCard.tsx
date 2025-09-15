import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  ArrowRightIcon,
  ClockIcon,
  CurrencyDollarIcon,
  BeakerIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  ChartBarIcon,
  SparklesIcon,
  ExclamationTriangleIcon,
  LightBulbIcon,
  CogIcon,
  ShieldCheckIcon,
  CalculatorIcon,
  BoltIcon,
  EyeIcon,
  FireIcon
} from '@heroicons/react/24/outline';
import type { DecantingOpportunity } from '../../types/tradingStrategies';
import { useReactiveTradingContext } from '../../contexts/ReactiveTrading';

interface DecantingOpportunityCardProps {
  opportunity: DecantingOpportunity;
  onClick?: () => void;
  onCalculateProfit?: () => void;
  onQuickTrade?: () => void;
  className?: string;
  realtimeData?: any;
  aiInsights?: any;
}

export function DecantingOpportunityCard({ 
  opportunity, 
  onClick, 
  onCalculateProfit,
  onQuickTrade,
  className = '',
  realtimeData,
  aiInsights
}: DecantingOpportunityCardProps) {
  const [calculatorQuantity, setCalculatorQuantity] = useState(10);
  const [showAIInsights, setShowAIInsights] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const [priceChange, setPriceChange] = useState<number | null>(null);
  const [volumeChange, setVolumeChange] = useState<number | null>(null);
  const [aiAlerts, setAiAlerts] = useState<any[]>([]);

  // WebSocket integration for real-time updates
  const { state: socketState, actions: socketActions } = useReactiveTradingContext();

  // Note: Item subscriptions are now managed centrally by DecantingView
  // This prevents duplicate subscriptions and reduces WebSocket traffic

  // Process real-time data updates
  useEffect(() => {
    if (realtimeData?.item_id === opportunity.item_id) {
      setLastUpdate(new Date());
      
      // Calculate price changes
      if (realtimeData.price_change) {
        setPriceChange(realtimeData.price_change.percentage);
      }
      
      // Calculate volume changes
      if (realtimeData.volume_change) {
        setVolumeChange(realtimeData.volume_change.percentage);
      }
      
      // Update AI alerts
      if (realtimeData.ai_alerts) {
        setAiAlerts(realtimeData.ai_alerts);
      }
    }
  }, [realtimeData, opportunity.item_id]);

  // AI insights processing
  useEffect(() => {
    if (aiInsights?.pattern_detected || aiInsights?.ai_confidence) {
      setShowAIInsights(true);
    }
  }, [aiInsights]);
  const formatPrice = (price: number) => {
    return price.toLocaleString();
  };

  const formatPercentage = (value: number | string) => {
    const numValue = typeof value === 'string' ? parseFloat(value) : value;
    if (isNaN(numValue)) return '0.0%';
    return `${numValue > 0 ? '+' : ''}${numValue.toFixed(1)}%`;
  };

  const formatTimestamp = (date: Date) => {
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);

    if (seconds < 60) return `${seconds}s ago`;
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    return date.toLocaleTimeString();
  };

  const getRealtimeStatusColor = () => {
    if (!socketState?.isConnected) return 'text-red-400';
    const now = new Date();
    const timeDiff = now.getTime() - lastUpdate.getTime();
    if (timeDiff < 30000) return 'text-green-400'; // Fresh data (< 30s)
    if (timeDiff < 300000) return 'text-yellow-400'; // Somewhat fresh (< 5m)
    return 'text-orange-400'; // Stale data
  };

  const getPriceChangeIcon = (change: number | null) => {
    if (change === null) return null;
    if (change > 0) return <ArrowTrendingUpIcon className="w-3 h-3 text-green-400" />;
    if (change < 0) return <ArrowTrendingDownIcon className="w-3 h-3 text-red-400" />;
    return <div className="w-3 h-3 rounded-full bg-gray-400"></div>;
  };

  const formatVolume = (volume: number) => {
    if (volume === 0) return '0';
    if (volume >= 1000000) {
      return `${(volume / 1000000).toFixed(1)}M`;
    } else if (volume >= 1000) {
      return `${(volume / 1000).toFixed(1)}K`;
    }
    return volume.toLocaleString();
  };

  const getRiskColor = (riskLevel: string) => {
    switch (riskLevel) {
      case 'low': return 'text-green-400 bg-green-400/10 border-green-400/30';
      case 'medium': return 'text-yellow-400 bg-yellow-400/10 border-yellow-400/30';
      case 'high': return 'text-red-400 bg-red-400/10 border-red-400/30';
      default: return 'text-gray-400 bg-gray-400/10 border-gray-400/30';
    }
  };

  const getConfidenceColor = (confidence: number | string) => {
    const numConfidence = typeof confidence === 'string' ? parseFloat(confidence) : confidence;
    if (isNaN(numConfidence)) return 'text-gray-400';
    if (numConfidence >= 0.8) return 'text-green-400';
    if (numConfidence >= 0.6) return 'text-yellow-400';
    if (numConfidence >= 0.4) return 'text-orange-400';
    return 'text-red-400';
  };

  const safeParseNumber = (value: number | string): number => {
    const numValue = typeof value === 'string' ? parseFloat(value) : value;
    return isNaN(numValue) ? 0 : numValue;
  };

  // Grand Exchange tax calculations (2% on both buy and sell)
  const calculateTaxedProfit = (quantity: number, buyPrice: number, sellPrice: number, dosesPerConversion: number) => {
    const totalBuyCost = quantity * buyPrice;
    const buyTax = totalBuyCost * 0.02;
    const totalBuyCostWithTax = totalBuyCost + buyTax;
    
    const totalSellRevenue = quantity * sellPrice * dosesPerConversion;
    const sellTax = totalSellRevenue * 0.02;
    const totalSellRevenueAfterTax = totalSellRevenue - sellTax;
    
    const netProfit = totalSellRevenueAfterTax - totalBuyCostWithTax;
    
    return {
      totalCapitalNeeded: Math.ceil(totalBuyCostWithTax),
      grossRevenue: Math.floor(totalSellRevenue),
      netRevenue: Math.floor(totalSellRevenueAfterTax),
      buyTax: Math.ceil(buyTax),
      sellTax: Math.ceil(sellTax),
      totalTax: Math.ceil(buyTax + sellTax),
      netProfit: Math.floor(netProfit),
      profitPerConversion: Math.floor(netProfit / quantity),
      isProfit: netProfit > 0
    };
  };

  const calculateBreakEven = (buyPrice: number, sellPrice: number, dosesPerConversion: number) => {
    // Calculate minimum quantity where profit > 0
    // Formula: (sellPrice * doses * 0.98 - buyPrice * 1.02) * qty > 0
    const profitPerUnit = (sellPrice * dosesPerConversion * 0.98) - (buyPrice * 1.02);
    if (profitPerUnit <= 0) {
      return null; // Never profitable due to taxes
    }
    return Math.ceil(1 / profitPerUnit); // Minimum 1 unit if profitable
  };

  // Tax-aware recommendation system that overrides backend data
  const getTaxAwareRecommendation = (opportunity: DecantingOpportunity) => {
    const singleUnitCalc = calculateTaxedProfit(1, opportunity.from_dose_price, opportunity.to_dose_price, dosesPerConversion);
    
    // Check for arbitrage opportunity (same or lower price for higher dose)
    const isArbitrage = opportunity.from_dose_price <= opportunity.to_dose_price;
    
    if (singleUnitCalc.netProfit <= 0) {
      return {
        status: 'not_recommended',
        reason: 'Tax-negative trade',
        icon: '❌',
        color: 'red',
        description: 'GE taxes exceed profit margin',
        badge: 'TAX LOSS',
        priority: 0
      };
    }
    
    // Special handling for arbitrage opportunities
    if (isArbitrage && singleUnitCalc.netProfit > 0) {
      return {
        status: 'arbitrage',
        reason: 'Arbitrage opportunity',
        icon: '🎯',
        color: 'gold',
        description: 'Market inefficiency - same price arbitrage',
        badge: 'ARBITRAGE',
        priority: 5  // Highest priority
      };
    }
    
    if (singleUnitCalc.profitPerConversion < 50) {
      return {
        status: 'marginal',
        reason: 'Low profit after tax',
        icon: '⚠️',
        color: 'yellow',
        description: 'Minimal profit after taxes',
        badge: 'MARGINAL',
        priority: 1
      };
    }
    
    if (singleUnitCalc.profitPerConversion >= 500) {
      return {
        status: 'excellent',
        reason: 'Excellent profit after tax',
        icon: '🔥',
        color: 'purple',
        description: 'High profit potential',
        badge: 'EXCELLENT',
        priority: 4
      };
    }
    
    if (singleUnitCalc.profitPerConversion >= 200) {
      return {
        status: 'high',
        reason: 'High profit after tax',
        icon: '💎',
        color: 'emerald',
        description: 'Strong profit margin',
        badge: 'HIGH VALUE',
        priority: 3
      };
    }
    
    if (singleUnitCalc.profitPerConversion >= 100) {
      return {
        status: 'good',
        reason: 'Good profit after tax',
        icon: '⚡',
        color: 'blue',
        description: 'Solid profit opportunity',
        badge: 'GOOD',
        priority: 2
      };
    }
    
    // 50-99 gp profit
    return {
      status: 'decent',
      reason: 'Decent profit after tax',
      icon: '💰',
      color: 'green',
      description: 'Modest but profitable',
      badge: 'DECENT',
      priority: 1
    };
  };

  const getAIConfidenceColor = (confidence?: number) => {
    if (!confidence) return 'text-gray-400';
    if (confidence >= 0.85) return 'text-emerald-400';
    if (confidence >= 0.7) return 'text-green-400';
    if (confidence >= 0.55) return 'text-yellow-400';
    if (confidence >= 0.4) return 'text-orange-400';
    return 'text-red-400';
  };

  const getAITimingColor = (timing?: string) => {
    switch (timing) {
      case 'immediate': return 'text-green-400 bg-green-400/10 border-green-400/30';
      case 'wait': return 'text-yellow-400 bg-yellow-400/10 border-yellow-400/30';
      case 'avoid': return 'text-red-400 bg-red-400/10 border-red-400/30';
      default: return 'text-gray-400 bg-gray-400/10 border-gray-400/30';
    }
  };

  const getModelAgreementColor = (agreement?: number) => {
    if (!agreement) return 'text-gray-400';
    if (agreement >= 0.8) return 'text-green-400';
    if (agreement >= 0.6) return 'text-yellow-400';
    return 'text-red-400';
  };

  const hasAIData = () => {
    return opportunity.ai_confidence !== undefined || 
           opportunity.ai_recommendations !== undefined ||
           opportunity.execution_strategy !== undefined;
  };

  const getProfitTier = (profit: number) => {
    if (profit >= 1000) return 'legendary';
    if (profit >= 500) return 'high';
    if (profit >= 200) return 'medium';
    if (profit >= 50) return 'low';
    return 'minimal';
  };

  const getProfitTierConfig = (tier: string) => {
    switch (tier) {
      case 'legendary': 
        return {
          color: 'text-purple-400 bg-purple-400/10 border-purple-400/30',
          icon: '👑',
          label: 'Legendary',
          glow: 'shadow-purple-500/20'
        };
      case 'high': 
        return {
          color: 'text-emerald-400 bg-emerald-400/10 border-emerald-400/30',
          icon: '💎',
          label: 'High Value',
          glow: 'shadow-emerald-500/15'
        };
      case 'medium': 
        return {
          color: 'text-blue-400 bg-blue-400/10 border-blue-400/30',
          icon: '⚡',
          label: 'Good',
          glow: 'shadow-blue-500/10'
        };
      case 'low': 
        return {
          color: 'text-yellow-400 bg-yellow-400/10 border-yellow-400/30',
          icon: '💰',
          label: 'Decent',
          glow: 'shadow-yellow-500/5'
        };
      default: 
        return {
          color: 'text-gray-400 bg-gray-400/10 border-gray-400/30',
          icon: '🪙',
          label: 'Basic',
          glow: ''
        };
    }
  };

  // Calculate doses per conversion (e.g., 4→1 gives 4 doses)
  const dosesPerConversion = opportunity.from_dose;
  
  // Get tax-aware recommendation (overrides misleading backend data)
  const taxAwareRec = getTaxAwareRecommendation(opportunity);
  
  // Calculate tax-adjusted profits
  const taxedCalculation = calculateTaxedProfit(
    calculatorQuantity,
    opportunity.from_dose_price,
    opportunity.to_dose_price,
    dosesPerConversion
  );
  
  const breakEvenQuantity = calculateBreakEven(
    opportunity.from_dose_price,
    opportunity.to_dose_price,
    dosesPerConversion
  );

  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      className={`bg-gray-800/50 backdrop-blur-sm border ${
        taxAwareRec.status === 'not_recommended' ? 'border-red-500/30 shadow-red-500/5' :
        taxAwareRec.status === 'marginal' ? 'border-yellow-500/30 shadow-yellow-500/5' :
        taxAwareRec.status === 'arbitrage' ? 'border-yellow-400/50 shadow-yellow-400/10' :
        taxAwareRec.status === 'excellent' ? 'border-purple-500/30 shadow-purple-500/5' :
        taxAwareRec.status === 'high' ? 'border-emerald-500/30 shadow-emerald-500/5' :
        'border-blue-500/30 shadow-blue-500/5'
      } rounded-xl p-6 cursor-pointer transition-all duration-200 hover:border-blue-500/50 hover:shadow-lg hover:shadow-blue-500/10 ${className}`}
      onClick={onClick}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <BeakerIcon className="w-5 h-5 text-blue-400" />
            <h3 className="text-lg font-semibold text-gray-100">
              {opportunity.item_name}
            </h3>
            <div className="flex items-center gap-2">
              {/* Real-time Status Indicator */}
              <motion.div 
                className={`flex items-center gap-1 px-2 py-0.5 rounded-full border text-xs font-medium ${
                  socketState?.isConnected 
                    ? 'text-green-400 bg-green-400/10 border-green-400/30' 
                    : 'text-red-400 bg-red-400/10 border-red-400/30'
                }`}
                animate={{ 
                  scale: socketState?.isConnected ? [1, 1.05, 1] : 1,
                  opacity: socketState?.isConnected ? [1, 0.8, 1] : 0.7
                }}
                transition={{ 
                  duration: 2, 
                  repeat: socketState?.isConnected ? Infinity : 0,
                  ease: "easeInOut"
                }}
              >
                <div className={`w-1.5 h-1.5 rounded-full ${
                  socketState?.isConnected ? 'bg-green-400' : 'bg-red-400'
                } ${socketState?.isConnected ? 'animate-pulse' : ''}`} />
                <span>
                  {socketState?.isConnected ? 'LIVE' : 'OFFLINE'}
                </span>
              </motion.div>

              {/* Price Change Indicator */}
              <AnimatePresence>
                {priceChange !== null && (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.8 }}
                    className={`flex items-center gap-1 px-2 py-0.5 rounded-full border text-xs font-medium ${
                      priceChange > 0 
                        ? 'text-green-400 bg-green-400/10 border-green-400/30'
                        : priceChange < 0
                        ? 'text-red-400 bg-red-400/10 border-red-400/30'
                        : 'text-gray-400 bg-gray-400/10 border-gray-400/30'
                    }`}
                  >
                    {getPriceChangeIcon(priceChange)}
                    <span>{formatPercentage(priceChange)}</span>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Tax-Aware Profit Badge */}
              <div className={`flex items-center gap-1 px-2 py-0.5 rounded-full border text-xs font-medium ${
                taxAwareRec.status === 'not_recommended' ? 'text-red-400 bg-red-400/10 border-red-400/30' :
                taxAwareRec.status === 'marginal' ? 'text-yellow-400 bg-yellow-400/10 border-yellow-400/30' :
                taxAwareRec.status === 'arbitrage' ? 'text-yellow-300 bg-yellow-400/20 border-yellow-400/40' :
                taxAwareRec.status === 'excellent' ? 'text-purple-400 bg-purple-400/10 border-purple-400/30' :
                taxAwareRec.status === 'high' ? 'text-emerald-400 bg-emerald-400/10 border-emerald-400/30' :
                taxAwareRec.status === 'good' ? 'text-blue-400 bg-blue-400/10 border-blue-400/30' :
                'text-green-400 bg-green-400/10 border-green-400/30'
              }`}>
                <span>{taxAwareRec.icon}</span>
                <span>{taxAwareRec.badge}</span>
              </div>
              
              {/* Tax Verified Badge */}
              <div className="flex items-center gap-1 px-2 py-0.5 bg-blue-400/10 border border-blue-400/30 rounded-full">
                <span className="text-xs">🔍</span>
                <span className="text-xs text-blue-400 font-medium">Tax Verified</span>
              </div>
              
              {hasAIData() && (
                <div className="flex items-center gap-1 px-2 py-0.5 bg-gray-400/10 border border-gray-400/30 rounded-full">
                  <SparklesIcon className="w-3 h-3 text-gray-400" />
                  <span className="text-xs text-gray-400 font-medium">AI</span>
                </div>
              )}

              {/* AI Alerts Indicator */}
              <AnimatePresence>
                {aiAlerts.length > 0 && (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.8 }}
                    className="flex items-center gap-1 px-2 py-0.5 bg-orange-400/10 border border-orange-400/30 rounded-full cursor-pointer"
                    onClick={(e) => {
                      e.stopPropagation();
                      setShowAIInsights(!showAIInsights);
                    }}
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                  >
                    <BoltIcon className="w-3 h-3 text-orange-400" />
                    <span className="text-xs text-orange-400 font-medium">{aiAlerts.length}</span>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className="px-3 py-1.5 rounded-full border bg-blue-400/10 border-blue-400/30 text-blue-400">
              <div className="flex items-center gap-2 text-sm font-semibold">
                <span>{opportunity.from_dose}-dose</span>
                <ArrowRightIcon className="w-3 h-3" />
                <span>{opportunity.to_dose}-dose</span>
              </div>
            </div>
            <div className={`px-2 py-1 rounded-full text-xs font-semibold ${getRiskColor(opportunity.strategy.risk_level)}`}>
              {opportunity.strategy.risk_level_display}
            </div>
          </div>
        </div>
        <div className="flex flex-col items-end gap-2">
          {/* Real-time Timestamp Display */}
          <div className="text-right">
            <div className="flex items-center gap-1 text-xs text-gray-400 mb-1">
              <ClockIcon className="w-3 h-3" />
              <span>Last Update</span>
            </div>
            <div className={`text-xs font-medium ${getRealtimeStatusColor()}`}>
              {formatTimestamp(lastUpdate)}
            </div>
            {socketState?.isConnected && (
              <div className="flex items-center gap-1 text-xs text-green-400">
                <EyeIcon className="w-2 h-2" />
                <span>Monitoring</span>
              </div>
            )}
          </div>

          {hasAIData() && opportunity.ai_confidence !== undefined ? (
            <div className="flex items-center gap-2">
              <div className={`text-right ${getConfidenceColor(opportunity.confidence_score)}`}>
                <div className="text-xs text-gray-400">Volume</div>
                <div className="text-sm font-bold">
                  {opportunity.confidence_score ? opportunity.confidence_score.toFixed(0) : '0'}%
                </div>
              </div>
              <div className={`text-right ${getAIConfidenceColor(opportunity.ai_confidence)}`}>
                <div className="flex items-center gap-1 text-xs text-gray-400">
                  <SparklesIcon className="w-3 h-3" />
                  AI
                </div>
                <div className="text-sm font-bold">
                  {(opportunity.ai_confidence * 100).toFixed(0)}%
                </div>
              </div>
            </div>
          ) : (
            <div className={`text-right ${getConfidenceColor(opportunity.confidence_score)}`}>
              <div className="text-xs text-gray-400">Volume Confidence</div>
              <div className="text-sm font-bold">
                {opportunity.confidence_score ? opportunity.confidence_score.toFixed(0) : '0'}%
              </div>
            </div>
          )}

          {/* Volume Change Indicator */}
          <AnimatePresence>
            {volumeChange !== null && (
              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                className="text-right"
              >
                <div className="text-xs text-gray-400">Volume Δ</div>
                <div className={`text-xs font-medium ${
                  volumeChange > 0 ? 'text-green-400' : 
                  volumeChange < 0 ? 'text-red-400' : 'text-gray-400'
                }`}>
                  {formatPercentage(volumeChange)}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Data Quality Warnings */}
      {(opportunity.confidence_score === 0 || !opportunity.item_name || opportunity.item_name.length < 5) && (
        <div className="mb-4">
          <div className="bg-orange-400/10 border border-orange-400/30 rounded-lg p-3 space-y-2">
            <div className="flex items-center gap-2">
              <span className="text-orange-400 text-sm">⚠️</span>
              <span className="text-orange-300 text-sm font-medium">Data Quality Issues</span>
            </div>
            
            <div className="space-y-1 text-xs text-orange-200">
              {opportunity.confidence_score === 0 && (
                <div>• Volume confidence: 0% - Limited trading data available</div>
              )}
              {(!opportunity.item_name || opportunity.item_name.length < 5) && (
                <div>• Incomplete item name - Verify item details manually</div>
              )}
            </div>
            
            <div className="text-xs text-orange-300">
              💡 Consider verifying prices manually before large investments
            </div>
          </div>
        </div>
      )}

      {/* Real-time AI Insights Panel */}
      <AnimatePresence>
        {showAIInsights && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="mb-4 overflow-hidden"
          >
            <div className="bg-gradient-to-r from-purple-900/20 to-blue-900/20 border border-purple-500/30 rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <SparklesIcon className="w-4 h-4 text-purple-400" />
                  <span className="text-sm font-semibold text-purple-300">Real-time AI Intelligence</span>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setShowAIInsights(false);
                  }}
                  className="text-gray-400 hover:text-gray-200 transition-colors"
                >
                  ✕
                </button>
              </div>

              {/* AI Alerts */}
              {aiAlerts.length > 0 && (
                <div className="mb-3">
                  <div className="text-xs text-orange-400 mb-2">Active Alerts</div>
                  <div className="space-y-2">
                    {aiAlerts.map((alert, index) => (
                      <motion.div
                        key={index}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: index * 0.1 }}
                        className="flex items-center gap-2 p-2 bg-orange-400/10 border border-orange-400/20 rounded-lg"
                      >
                        <BoltIcon className="w-3 h-3 text-orange-400 flex-shrink-0" />
                        <span className="text-xs text-orange-200">{alert.message || alert.type}</span>
                        <span className="text-xs text-orange-400 ml-auto">
                          {alert.confidence && `${(alert.confidence * 100).toFixed(0)}%`}
                        </span>
                      </motion.div>
                    ))}
                  </div>
                </div>
              )}

              {/* AI Pattern Detection */}
              {aiInsights?.pattern_detected && (
                <div className="mb-3">
                  <div className="text-xs text-blue-400 mb-2">Pattern Detection</div>
                  <div className="flex items-center gap-2 p-2 bg-blue-400/10 border border-blue-400/20 rounded-lg">
                    <FireIcon className="w-3 h-3 text-blue-400" />
                    <span className="text-xs text-blue-200">{aiInsights.pattern_detected}</span>
                    {aiInsights.pattern_confidence && (
                      <span className="text-xs text-blue-400 ml-auto">
                        {(aiInsights.pattern_confidence * 100).toFixed(0)}% confidence
                      </span>
                    )}
                  </div>
                </div>
              )}

              {/* AI Recommendations */}
              {realtimeData?.ai_recommendations && (
                <div className="mb-3">
                  <div className="text-xs text-green-400 mb-2">Smart Recommendations</div>
                  <div className="space-y-1">
                    {realtimeData.ai_recommendations.slice(0, 2).map((rec: string, index: number) => (
                      <div key={index} className="flex items-start gap-2 text-xs text-green-200">
                        <span className="text-green-400 mt-0.5">•</span>
                        <span>{rec}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Real-time Market Sentiment */}
              {realtimeData?.market_sentiment && (
                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <span className="text-gray-400">Market Sentiment:</span>
                    <span className={`font-medium ${
                      realtimeData.market_sentiment === 'bullish' ? 'text-green-400' :
                      realtimeData.market_sentiment === 'bearish' ? 'text-red-400' :
                      'text-yellow-400'
                    }`}>
                      {realtimeData.market_sentiment.charAt(0).toUpperCase() + realtimeData.market_sentiment.slice(1)}
                    </span>
                  </div>
                  {realtimeData.sentiment_strength && (
                    <span className="text-gray-400">
                      {(realtimeData.sentiment_strength * 100).toFixed(0)}%
                    </span>
                  )}
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Key Metrics Grid - Tax-Adjusted */}
      <div className="grid grid-cols-3 gap-4 mb-4">
        <div className="text-center">
          <div className="text-xs text-gray-400 mb-1 flex items-center justify-center gap-1">
            <span>{taxedCalculation.isProfit ? '✅' : '❌'}</span>
            <span>Net Profit/Conversion</span>
          </div>
          <div className={`text-lg font-bold ${
            taxedCalculation.isProfit ? 
              (taxAwareRec.status === 'arbitrage' ? 'text-yellow-300' :
               taxAwareRec.status === 'excellent' ? 'text-purple-400' :
               taxAwareRec.status === 'high' ? 'text-emerald-400' :
               taxAwareRec.status === 'good' ? 'text-blue-400' :
               taxAwareRec.status === 'decent' ? 'text-green-400' : 'text-yellow-400')
            : 'text-red-400'
          }`}>
            {taxedCalculation.netProfit >= 0 ? '+' : ''}{formatPrice(taxedCalculation.profitPerConversion)} gp
          </div>
          <div className="text-xs text-gray-500">
            (after 4% GE tax)
          </div>
        </div>
        <div className="text-center">
          <div className="text-xs text-gray-400 mb-1">Est. Per Hour</div>
          <div className={`text-lg font-bold ${taxedCalculation.isProfit ? 'text-emerald-400' : 'text-red-400'}`}>
            {taxedCalculation.netProfit >= 0 ? '+' : ''}{formatPrice(Math.floor(taxedCalculation.profitPerConversion * (opportunity.profit_per_hour / opportunity.profit_per_conversion)))} gp/h
          </div>
          <div className="text-xs text-gray-500">
            (tax-adjusted)
          </div>
        </div>
        <div className="text-center">
          <div className="text-xs text-gray-400 mb-1">True Margin</div>
          <div className={`text-lg font-bold ${taxedCalculation.isProfit ? 'text-blue-400' : 'text-red-400'}`}>
            {formatPercentage(((taxedCalculation.profitPerConversion / opportunity.from_dose_price) * 100))}
          </div>
          <div className="text-xs text-gray-500">
            (after taxes)
          </div>
        </div>
      </div>

      {/* Price Breakdown */}
      <div className="mb-4">
        <div className="text-sm text-gray-400 mb-2">Price Breakdown</div>
        
        {/* Check for arbitrage opportunity */}
        {opportunity.from_dose_price <= opportunity.to_dose_price && (
          <div className="bg-yellow-400/10 border border-yellow-400/30 rounded-lg p-2 mb-3">
            <div className="flex items-center gap-2">
              <span className="text-yellow-400 text-sm">🎯</span>
              <span className="text-yellow-300 text-xs font-medium">
                ARBITRAGE OPPORTUNITY - {opportunity.from_dose}-dose costs ≤ {opportunity.to_dose}-dose price
              </span>
            </div>
          </div>
        )}
        
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-gray-700/30 rounded-lg p-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-300">Buy ({opportunity.from_dose}-dose)</span>
              <span className="text-sm font-semibold text-red-300">
                {formatPrice(opportunity.from_dose_price)} gp
              </span>
            </div>
          </div>
          <div className="bg-gray-700/30 rounded-lg p-3">
            <div className="space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-300">Sell ({opportunity.to_dose}-dose each)</span>
                <span className="text-sm font-semibold text-green-300">
                  {formatPrice(opportunity.to_dose_price)} gp
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-400">Total ({dosesPerConversion}× doses)</span>
                <span className="text-xs font-semibold text-green-400">
                  {formatPrice(opportunity.to_dose_price * dosesPerConversion)} gp
                </span>
              </div>
            </div>
          </div>
        </div>
        
        {/* Arbitrage Explanation */}
        {opportunity.from_dose_price <= opportunity.to_dose_price && (
          <div className="mt-2 text-xs text-gray-400">
            💡 Market inefficiency: You can buy {opportunity.from_dose}-dose for {formatPrice(opportunity.from_dose_price)} gp and sell as {dosesPerConversion}× {opportunity.to_dose}-doses for {formatPrice(opportunity.to_dose_price * dosesPerConversion)} gp total
          </div>
        )}
      </div>

      {/* Profit Calculator */}
      <div className="mb-4">
        <div className="flex items-center gap-2 text-sm text-blue-400 mb-3">
          <CalculatorIcon className="w-4 h-4" />
          <span className="font-semibold">Profit Calculator (with GE Tax)</span>
        </div>
        
        <div className={`rounded-lg border p-4 ${
          taxedCalculation.isProfit 
            ? 'bg-green-400/5 border-green-400/20' 
            : 'bg-red-400/5 border-red-400/20'
        }`}>
          
          {/* Quantity Input */}
          <div className="mb-4">
            <label className="text-sm text-gray-300 mb-2 block">
              Number of {opportunity.from_dose}-dose potions to trade:
            </label>
            <input
              type="number"
              min="1"
              max="2000"
              value={calculatorQuantity}
              onChange={(e) => setCalculatorQuantity(Math.max(1, parseInt(e.target.value) || 1))}
              className="w-full px-3 py-2 bg-gray-700/50 border border-gray-600/50 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50"
            />
            <div className="text-xs text-gray-400 mt-1">
              Max buy limit: 2,000 per 4 hours
            </div>
          </div>

          {/* Calculation Results */}
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <div className="text-xs text-gray-400 mb-1">💰 Capital Needed</div>
              <div className={`text-sm font-semibold ${taxedCalculation.isProfit ? 'text-yellow-300' : 'text-red-300'}`}>
                {formatPrice(taxedCalculation.totalCapitalNeeded)} gp
              </div>
              <div className="text-xs text-gray-500">
                (inc. {formatPrice(taxedCalculation.buyTax)} gp buy tax)
              </div>
            </div>
            
            <div>
              <div className="text-xs text-gray-400 mb-1">💎 Net Revenue</div>
              <div className={`text-sm font-semibold ${taxedCalculation.isProfit ? 'text-green-300' : 'text-red-300'}`}>
                {formatPrice(taxedCalculation.netRevenue)} gp
              </div>
              <div className="text-xs text-gray-500">
                (after {formatPrice(taxedCalculation.sellTax)} gp sell tax)
              </div>
            </div>
            
            <div>
              <div className="text-xs text-gray-400 mb-1">
                {taxedCalculation.isProfit ? '✅ Net Profit' : '❌ Net Loss'}
              </div>
              <div className={`text-lg font-bold ${
                taxedCalculation.isProfit ? 'text-green-400' : 'text-red-400'
              }`}>
                {taxedCalculation.netProfit >= 0 ? '+' : ''}{formatPrice(taxedCalculation.netProfit)} gp
              </div>
              <div className="text-xs text-gray-500">
                ({formatPrice(taxedCalculation.profitPerConversion)} gp per potion)
              </div>
            </div>
            
            <div>
              <div className="text-xs text-gray-400 mb-1">📊 Total Taxes</div>
              <div className="text-sm font-semibold text-red-300">
                -{formatPrice(taxedCalculation.totalTax)} gp
              </div>
              <div className="text-xs text-gray-500">
                (4% of transaction value)
              </div>
            </div>
          </div>

          {/* Break Even Analysis */}
          {breakEvenQuantity !== null ? (
            <div className="border-t border-gray-600/30 pt-3">
              <div className="text-xs text-blue-400 mb-1">🎯 Break-even Analysis</div>
              <div className="text-sm text-gray-300">
                {breakEvenQuantity <= calculatorQuantity ? (
                  <span className="text-green-400">
                    ✅ Profitable - Break-even at {breakEvenQuantity} potions
                  </span>
                ) : (
                  <span className="text-orange-400">
                    ⚠️ Need {breakEvenQuantity} potions minimum for profit
                  </span>
                )}
              </div>
            </div>
          ) : (
            <div className="border-t border-gray-600/30 pt-3">
              <div className="text-xs text-red-400 mb-1">❌ Tax Impact</div>
              <div className="text-sm text-red-300">
                Never profitable due to 4% GE tax exceeding margin
              </div>
            </div>
          )}

          {/* Quick Calculation Steps */}
          <div className="border-t border-gray-600/30 pt-3 mt-3">
            <div className="text-xs text-gray-400 mb-2">📝 Calculation Breakdown:</div>
            <div className="grid grid-cols-1 gap-1 text-xs text-gray-500">
              <div>• Buy {calculatorQuantity}× at {formatPrice(opportunity.from_dose_price)} gp = {formatPrice(calculatorQuantity * opportunity.from_dose_price)} gp</div>
              <div>• Decant to {calculatorQuantity * dosesPerConversion}× {opportunity.to_dose}-doses</div>
              <div>• Sell {calculatorQuantity * dosesPerConversion}× at {formatPrice(opportunity.to_dose_price)} gp = {formatPrice(taxedCalculation.grossRevenue)} gp</div>
              <div>• Taxes: -{formatPrice(taxedCalculation.totalTax)} gp (2% buy + 2% sell)</div>
              <div className={`font-semibold ${taxedCalculation.isProfit ? 'text-green-400' : 'text-red-400'}`}>
                = {taxedCalculation.netProfit >= 0 ? '+' : ''}{formatPrice(taxedCalculation.netProfit)} gp net
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Volume Analysis */}
      <div className="mb-4">
        <div className="text-sm text-gray-400 mb-2">Market Volume Analysis</div>
        <div className="bg-gray-700/20 rounded-lg p-3 space-y-2">
          {/* Trading Activity and Liquidity */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ChartBarIcon className="w-4 h-4 text-blue-400" />
              <span className="text-sm text-gray-300">
                {opportunity.volume_analysis_summary?.volume_description || 
                 `${opportunity.trading_activity_display || opportunity.trading_activity} trading`}
              </span>
            </div>
            {/* Liquidity indicator */}
            <div className="flex items-center gap-1">
              {opportunity.volume_analysis_summary?.liquidity_indicator ? (
                <>
                  <span className="text-lg" title={`${opportunity.volume_analysis_summary.liquidity_indicator.level} liquidity`}>
                    {opportunity.volume_analysis_summary.liquidity_indicator.icon}
                  </span>
                  <span className={`text-xs font-medium capitalize text-${opportunity.volume_analysis_summary.liquidity_indicator.color}-400`}>
                    {opportunity.volume_analysis_summary.liquidity_indicator.level}
                  </span>
                </>
              ) : (
                // Fallback based on trading activity
                opportunity.trading_activity === 'very_active' || opportunity.trading_activity === 'active' ? (
                  <>
                    <span className="text-lg" title="High liquidity">🟢</span>
                    <span className="text-xs font-medium text-green-400">High</span>
                  </>
                ) : opportunity.trading_activity === 'moderate' ? (
                  <>
                    <span className="text-lg" title="Medium liquidity">🟡</span>
                    <span className="text-xs font-medium text-yellow-400">Medium</span>
                  </>
                ) : (
                  <>
                    <span className="text-lg" title="Low liquidity">🔴</span>
                    <span className="text-xs font-medium text-red-400">Low</span>
                  </>
                )
              )}
            </div>
          </div>
          
          {/* Volume Details */}
          {opportunity.volume_analysis_data && (
            <div className="grid grid-cols-2 gap-4 pt-2 border-t border-gray-600/30">
              <div>
                <span className="text-xs text-gray-400">Avg Volume/Hour:</span>
                <div className="text-sm font-medium text-gray-200">
                  {opportunity.volume_analysis_data.avg_volume_per_hour?.toFixed(0) || 'N/A'}
                </div>
              </div>
              <div>
                <span className="text-xs text-gray-400">Price Stability:</span>
                <div className="text-sm font-medium text-gray-200">
                  {opportunity.volume_analysis_data.price_stability ? 
                    `${(opportunity.volume_analysis_data.price_stability * 100).toFixed(1)}%` : 'N/A'}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Tax-Aware Risk Assessment */}
      <div className="mb-4">
        <div className="text-sm text-gray-400 mb-2">Tax-Aware Assessment</div>
        <div className={`bg-${taxAwareRec.color}-400/5 border border-${taxAwareRec.color}-400/20 rounded-lg p-3`}>
          <div className="flex items-start justify-between mb-2">
            <div className="flex items-center gap-2">
              <span className="text-lg">{taxAwareRec.icon}</span>
              <div>
                <div className={`text-sm font-semibold ${
                  taxAwareRec.status === 'arbitrage' ? 'text-yellow-300' : `text-${taxAwareRec.color}-300`
                }`}>
                  {taxAwareRec.status === 'not_recommended' ? '❌ AVOID - Tax Loss Trade' :
                   taxAwareRec.status === 'marginal' ? '⚠️ MARGINAL - Low Tax-Adjusted Profit' :
                   taxAwareRec.status === 'arbitrage' ? '🎯 ARBITRAGE - Market Inefficiency Detected' :
                   taxAwareRec.status === 'excellent' ? '🔥 EXCELLENT - High Profit After Tax' :
                   taxAwareRec.status === 'high' ? '💎 HIGH VALUE - Strong Tax-Adjusted Margin' :
                   taxAwareRec.status === 'good' ? '⚡ GOOD - Solid Profit After Tax' :
                   '💰 DECENT - Modest But Profitable After Tax'}
                </div>
                <div className="text-xs text-gray-400 mt-1">
                  {taxAwareRec.description} • {taxedCalculation.profitPerConversion >= 0 ? '+' : ''}{formatPrice(taxedCalculation.profitPerConversion)} gp per conversion after 4% GE tax
                </div>
              </div>
            </div>
            <div className={`text-right text-${taxAwareRec.color}-400`}>
              <div className="text-xs text-gray-400">Tax Reality</div>
              <div className="text-sm font-bold capitalize">
                {taxAwareRec.status === 'not_recommended' ? 'Loss' :
                 taxAwareRec.status === 'marginal' ? 'Marginal' :
                 'Profitable'}
              </div>
            </div>
          </div>
          
          {/* Show backend assessment if different from tax reality */}
          {opportunity.risk_assessment && taxAwareRec.status === 'not_recommended' && 
           opportunity.risk_assessment.recommendation.includes('✅') && (
            <div className="border-t border-gray-600/30 pt-2 mt-2">
              <div className="text-xs text-orange-400 mb-1">⚠️ Backend vs Reality</div>
              <div className="text-xs text-gray-500">
                Backend says: "{opportunity.risk_assessment.recommendation}" but this ignores 4% GE tax that makes this trade unprofitable
              </div>
            </div>
          )}
        </div>
      </div>

      {/* AI Insights Section */}
      {hasAIData() && (
        <div className="mb-4">
          <div className="flex items-center gap-2 text-sm text-blue-400 mb-3">
            <SparklesIcon className="w-4 h-4" />
            <span className="font-semibold">AI Analysis</span>
          </div>
          
          {/* AI Metrics Grid */}
          <div className="grid grid-cols-2 gap-4 mb-3">
            {opportunity.ai_timing && (
              <div>
                <div className="text-xs text-gray-400 mb-1">Timing Recommendation</div>
                <div className={`inline-flex px-2 py-1 rounded-full text-xs font-semibold ${getAITimingColor(opportunity.ai_timing)}`}>
                  {opportunity.ai_timing.charAt(0).toUpperCase() + opportunity.ai_timing.slice(1)}
                </div>
              </div>
            )}
            
            {opportunity.model_agreement !== undefined && (
              <div>
                <div className="text-xs text-gray-400 mb-1">Model Agreement</div>
                <div className={`text-sm font-semibold ${getModelAgreementColor(opportunity.model_agreement)}`}>
                  {(opportunity.model_agreement * 100).toFixed(0)}%
                </div>
              </div>
            )}
            
            {opportunity.ai_success_probability !== undefined && (
              <div>
                <div className="text-xs text-gray-400 mb-1">Success Probability</div>
                <div className={`text-sm font-semibold ${getAIConfidenceColor(opportunity.ai_success_probability)}`}>
                  {(opportunity.ai_success_probability * 100).toFixed(0)}%
                </div>
              </div>
            )}
            
            {opportunity.ai_risk_level && (
              <div>
                <div className="text-xs text-gray-400 mb-1">AI Risk Assessment</div>
                <div className={`inline-flex px-2 py-1 rounded-full text-xs font-semibold ${getRiskColor(opportunity.ai_risk_level)}`}>
                  {opportunity.ai_risk_level.charAt(0).toUpperCase() + opportunity.ai_risk_level.slice(1)}
                </div>
              </div>
            )}
          </div>

          {/* Execution Strategy */}
          {opportunity.execution_strategy && (
            <div className="bg-blue-400/5 border border-blue-400/20 rounded-lg p-3 mb-3">
              <div className="flex items-center gap-2 text-xs text-blue-400 mb-2">
                <CogIcon className="w-3 h-3" />
                <span className="font-semibold">Execution Strategy</span>
              </div>
              <div className="text-sm text-gray-300">
                {opportunity.execution_strategy}
              </div>
            </div>
          )}

          {/* AI Recommendations */}
          {opportunity.ai_recommendations && opportunity.ai_recommendations.length > 0 && (
            <div className="bg-green-400/5 border border-green-400/20 rounded-lg p-3">
              <div className="flex items-center gap-2 text-xs text-green-400 mb-2">
                <LightBulbIcon className="w-3 h-3" />
                <span className="font-semibold">AI Recommendations</span>
              </div>
              <ul className="text-sm text-gray-300 space-y-1">
                {opportunity.ai_recommendations.slice(0, 3).map((rec, index) => (
                  <li key={index} className="flex items-start gap-2">
                    <span className="text-green-400 mt-1">•</span>
                    <span>{rec}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Uncertainty Factors */}
          {opportunity.uncertainty_factors && opportunity.uncertainty_factors.length > 0 && (
            <div className="bg-orange-400/5 border border-orange-400/20 rounded-lg p-3 mt-3">
              <div className="flex items-center gap-2 text-xs text-orange-400 mb-2">
                <ExclamationTriangleIcon className="w-3 h-3" />
                <span className="font-semibold">Risk Factors</span>
              </div>
              <ul className="text-sm text-gray-300 space-y-1">
                {opportunity.uncertainty_factors.slice(0, 2).map((factor, index) => (
                  <li key={index} className="flex items-start gap-2">
                    <span className="text-orange-400 mt-1">•</span>
                    <span>{factor}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Strategy Details */}
      <div className="mb-4">
        <div className="text-sm text-gray-400 mb-2">Strategy Requirements</div>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-gray-400">Min Capital:</span>
            <span className="ml-2 font-semibold text-gray-200">
              {opportunity.capital_requirement ? formatPrice(opportunity.capital_requirement) : formatPrice(opportunity.strategy.min_capital_required)} gp
            </span>
          </div>
          <div>
            <span className="text-gray-400">Est. Time:</span>
            <span className="ml-2 font-semibold text-gray-200">
              {opportunity.estimated_time_per_conversion ? 
                `${(opportunity.estimated_time_per_conversion / 60).toFixed(1)}min/conversion` : 
                `${opportunity.strategy.estimated_time_minutes}min/conversion`}
            </span>
          </div>
        </div>
      </div>

      {/* ROI and Performance */}
      <div className="border-t border-gray-700/50 pt-3">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <ArrowTrendingUpIcon className="w-4 h-4 text-green-400" />
            <span className="text-sm text-gray-300">
              ROI: <span className="font-semibold text-green-400">
                {safeParseNumber(opportunity.strategy.roi_percentage).toFixed(1)}%
              </span>
            </span>
          </div>
          <div className="flex items-center gap-2">
            <ClockIcon className="w-4 h-4 text-blue-400" />
            <span className="text-sm text-gray-300">
              Updated: <span className="font-semibold">
                {new Date(opportunity.strategy.last_updated).toLocaleDateString()}
              </span>
            </span>
          </div>
        </div>

        {/* AI Data Quality Indicators */}
        {hasAIData() && (
          <div className="flex items-center justify-between text-xs text-gray-400">
            {opportunity.data_freshness && (
              <div className="flex items-center gap-1">
                <ShieldCheckIcon className="w-3 h-3" />
                <span>Data: {opportunity.data_freshness}</span>
              </div>
            )}
            {opportunity.liquidity_score !== undefined && (
              <div className="flex items-center gap-1">
                <ChartBarIcon className="w-3 h-3" />
                <span>Liquidity: {(opportunity.liquidity_score * 100).toFixed(0)}%</span>
              </div>
            )}
            {opportunity.price_spread !== undefined && (
              <div className="flex items-center gap-1">
                <CurrencyDollarIcon className="w-3 h-3" />
                <span>Spread: {opportunity.price_spread.toFixed(1)}%</span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Activity Status */}
      {!opportunity.strategy.is_active && (
        <div className="mt-3 px-3 py-2 bg-orange-400/10 border border-orange-400/30 rounded-lg">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-orange-400 animate-pulse"></div>
            <span className="text-sm text-orange-400 font-medium">
              Strategy Inactive
            </span>
          </div>
        </div>
      )}

      {/* Quick Action Buttons */}
      <div className="mt-4 pt-4 border-t border-gray-700/50 flex gap-2">
        {onCalculateProfit && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onCalculateProfit();
            }}
            className="flex-1 flex items-center justify-center gap-2 py-2 px-3 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors"
          >
            <CalculatorIcon className="w-4 h-4" />
            Calculate Profit
          </button>
        )}
        {onQuickTrade && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onQuickTrade();
            }}
            className="flex-1 flex items-center justify-center gap-2 py-2 px-3 bg-green-600 hover:bg-green-700 text-white text-sm font-medium rounded-lg transition-colors"
          >
            <BoltIcon className="w-4 h-4" />
            Quick Trade
          </button>
        )}
        <button
          onClick={(e) => {
            e.stopPropagation();
            onClick?.();
          }}
          title="View Advanced Price Chart"
          className="flex items-center justify-center gap-2 py-2 px-3 bg-purple-600 hover:bg-purple-700 text-white text-sm font-medium rounded-lg transition-colors"
        >
          <EyeIcon className="w-4 h-4" />
          <span className="hidden sm:inline">Chart</span>
        </button>
      </div>
    </motion.div>
  );
}

export default DecantingOpportunityCard;