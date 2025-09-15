import React from 'react';
import { motion } from 'framer-motion';
import { 
  ShieldExclamationIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  ChartBarIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  ClockIcon,
  CpuChipIcon
} from '@heroicons/react/24/outline';
import type { MarketConditionSnapshot } from '../../types/tradingStrategies';

interface MarketConditionDisplayProps {
  marketCondition: MarketConditionSnapshot | null;
  isLoading?: boolean;
  className?: string;
}

export function MarketConditionDisplay({ 
  marketCondition, 
  isLoading = false, 
  className = '' 
}: MarketConditionDisplayProps) {
  
  const getMarketConditionColor = (condition: string) => {
    switch (condition) {
      case 'bullish': return 'text-green-400 bg-green-400/10 border-green-400/30';
      case 'stable': return 'text-blue-400 bg-blue-400/10 border-blue-400/30';
      case 'recovering': return 'text-emerald-400 bg-emerald-400/10 border-emerald-400/30';
      case 'volatile': return 'text-yellow-400 bg-yellow-400/10 border-yellow-400/30';
      case 'bearish': return 'text-orange-400 bg-orange-400/10 border-orange-400/30';
      case 'crashing': return 'text-red-400 bg-red-400/10 border-red-400/30';
      default: return 'text-gray-400 bg-gray-400/10 border-gray-400/30';
    }
  };

  const getMarketConditionIcon = (condition: string) => {
    switch (condition) {
      case 'bullish': return <ArrowTrendingUpIcon className="w-5 h-5 text-green-400" />;
      case 'stable': return <CheckCircleIcon className="w-5 h-5 text-blue-400" />;
      case 'recovering': return <ArrowTrendingUpIcon className="w-5 h-5 text-emerald-400" />;
      case 'volatile': return <ChartBarIcon className="w-5 h-5 text-yellow-400" />;
      case 'bearish': return <ArrowTrendingDownIcon className="w-5 h-5 text-orange-400" />;
      case 'crashing': return <ExclamationTriangleIcon className="w-5 h-5 text-red-400" />;
      default: return <ClockIcon className="w-5 h-5 text-gray-400" />;
    }
  };

  const getCrashRiskColor = (riskLevel: string) => {
    switch (riskLevel) {
      case 'low': return 'text-green-400 bg-green-400/10';
      case 'medium': return 'text-yellow-400 bg-yellow-400/10';
      case 'high': return 'text-orange-400 bg-orange-400/10';
      case 'critical': return 'text-red-400 bg-red-400/10';
      default: return 'text-gray-400 bg-gray-400/10';
    }
  };

  const getBotActivityColor = (score: number) => {
    if (score >= 0.8) return 'text-red-400';
    if (score >= 0.6) return 'text-orange-400';
    if (score >= 0.4) return 'text-yellow-400';
    return 'text-green-400';
  };

  const getVolatilityColor = (score: number) => {
    if (score >= 0.3) return 'text-red-400';
    if (score >= 0.2) return 'text-orange-400';
    if (score >= 0.1) return 'text-yellow-400';
    return 'text-green-400';
  };

  const formatPercentage = (value: number) => {
    return `${value > 0 ? '+' : ''}${(value * 100).toFixed(1)}%`;
  };

  if (isLoading) {
    return (
      <div className={`bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6 ${className}`}>
        <div className="animate-pulse">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-8 h-8 bg-gray-700 rounded-lg"></div>
            <div className="h-6 bg-gray-700 rounded w-48"></div>
          </div>
          <div className="space-y-3">
            <div className="h-4 bg-gray-700 rounded w-full"></div>
            <div className="h-4 bg-gray-700 rounded w-3/4"></div>
            <div className="h-4 bg-gray-700 rounded w-1/2"></div>
          </div>
        </div>
      </div>
    );
  }

  if (!marketCondition) {
    return (
      <div className={`bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6 ${className}`}>
        <div className="text-center py-8">
          <ExclamationTriangleIcon className="w-12 h-12 text-yellow-400 mx-auto mb-3" />
          <h3 className="text-lg font-semibold text-gray-300 mb-2">Market Data Unavailable</h3>
          <p className="text-sm text-gray-500">Unable to load current market conditions</p>
        </div>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={`bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6 ${className}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-400/10 rounded-lg">
            <ChartBarIcon className="w-6 h-6 text-blue-400" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-100">Market Conditions</h3>
            <p className="text-sm text-gray-400">
              Updated: {new Date(marketCondition.timestamp).toLocaleString()}
            </p>
          </div>
        </div>
        <div className={`px-3 py-1.5 rounded-full border flex items-center gap-2 ${getMarketConditionColor(marketCondition.market_condition)}`}>
          {getMarketConditionIcon(marketCondition.market_condition)}
          <span className="text-sm font-semibold uppercase">
            {marketCondition.market_condition_display}
          </span>
        </div>
      </div>

      {/* Key Metrics Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="text-center p-4 bg-gray-700/20 rounded-lg">
          <div className="text-xs text-gray-400 mb-1">Bot Activity</div>
          <div className={`text-lg font-bold ${getBotActivityColor(marketCondition.bot_activity_score)}`}>
            {(marketCondition.bot_activity_score * 100).toFixed(0)}%
          </div>
          <div className="flex justify-center mt-2">
            <CpuChipIcon className={`w-4 h-4 ${getBotActivityColor(marketCondition.bot_activity_score)}`} />
          </div>
        </div>

        <div className="text-center p-4 bg-gray-700/20 rounded-lg">
          <div className="text-xs text-gray-400 mb-1">Crash Risk</div>
          <div className={`text-lg font-bold ${getCrashRiskColor(marketCondition.crash_risk_level).split(' ')[0]}`}>
            {marketCondition.crash_risk_level_display}
          </div>
          <div className="flex justify-center mt-2">
            <ShieldExclamationIcon className={`w-4 h-4 ${getCrashRiskColor(marketCondition.crash_risk_level).split(' ')[0]}`} />
          </div>
        </div>

        <div className="text-center p-4 bg-gray-700/20 rounded-lg">
          <div className="text-xs text-gray-400 mb-1">Volatility</div>
          <div className={`text-lg font-bold ${getVolatilityColor(marketCondition.volatility_score)}`}>
            {(marketCondition.volatility_score * 100).toFixed(1)}%
          </div>
          <div className="flex justify-center mt-2">
            <ChartBarIcon className={`w-4 h-4 ${getVolatilityColor(marketCondition.volatility_score)}`} />
          </div>
        </div>

        <div className="text-center p-4 bg-gray-700/20 rounded-lg">
          <div className="text-xs text-gray-400 mb-1">Price Change</div>
          <div className={`text-lg font-bold ${marketCondition.average_price_change_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
            {formatPercentage(marketCondition.average_price_change_pct)}
          </div>
          <div className="flex justify-center mt-2">
            {marketCondition.average_price_change_pct >= 0 ? 
              <ArrowTrendingUpIcon className="w-4 h-4 text-green-400" /> :
              <ArrowTrendingDownIcon className="w-4 h-4 text-red-400" />
            }
          </div>
        </div>
      </div>

      {/* Market Analysis Details */}
      <div className="bg-gray-700/20 rounded-lg p-4">
        <div className="text-sm text-gray-400 mb-3">Market Analysis</div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <span className="text-gray-400">Items Analyzed:</span>
            <span className="ml-2 font-semibold text-gray-200">
              {marketCondition.market_data.items_analyzed.toLocaleString()}
            </span>
          </div>
          <div>
            <span className="text-gray-400">Volume Spikes:</span>
            <span className="ml-2 font-semibold text-yellow-400">
              {marketCondition.market_data.volume_spikes_detected.toLocaleString()}
            </span>
          </div>
          <div>
            <span className="text-gray-400">Price Crashes:</span>
            <span className="ml-2 font-semibold text-red-400">
              {marketCondition.market_data.price_crashes_detected.toLocaleString()}
            </span>
          </div>
          <div>
            <span className="text-gray-400">High Volatility:</span>
            <span className="ml-2 font-semibold text-orange-400">
              {marketCondition.market_data.high_volatility_items.toLocaleString()}
            </span>
          </div>
        </div>
      </div>

      {/* Trading Safety Indicator */}
      <div className={`mt-4 p-3 rounded-lg border ${
        marketCondition.crash_risk_level === 'low' && marketCondition.bot_activity_score < 0.5 
          ? 'bg-green-400/10 border-green-400/30' 
          : marketCondition.crash_risk_level === 'critical' || marketCondition.bot_activity_score > 0.8
          ? 'bg-red-400/10 border-red-400/30'
          : 'bg-yellow-400/10 border-yellow-400/30'
      }`}>
        <div className="flex items-center gap-2">
          {marketCondition.crash_risk_level === 'low' && marketCondition.bot_activity_score < 0.5 ? (
            <>
              <CheckCircleIcon className="w-5 h-5 text-green-400" />
              <span className="text-sm font-medium text-green-400">Market conditions are favorable for trading</span>
            </>
          ) : marketCondition.crash_risk_level === 'critical' || marketCondition.bot_activity_score > 0.8 ? (
            <>
              <ExclamationTriangleIcon className="w-5 h-5 text-red-400" />
              <span className="text-sm font-medium text-red-400">High risk - Consider avoiding large trades</span>
            </>
          ) : (
            <>
              <ExclamationTriangleIcon className="w-5 h-5 text-yellow-400" />
              <span className="text-sm font-medium text-yellow-400">Market conditions require caution</span>
            </>
          )}
        </div>
      </div>
    </motion.div>
  );
}

export default MarketConditionDisplay;