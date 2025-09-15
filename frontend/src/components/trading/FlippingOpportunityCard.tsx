import React from 'react';
import { motion } from 'framer-motion';
import { 
  ArrowRightIcon,
  ClockIcon,
  CurrencyDollarIcon,
  ArrowTrendingUpIcon,
  ChartBarIcon,
  ShoppingCartIcon
} from '@heroicons/react/24/outline';
import type { FlippingOpportunity } from '../../types/tradingStrategies';

interface FlippingOpportunityCardProps {
  opportunity: FlippingOpportunity;
  onClick?: () => void;
  className?: string;
}

export function FlippingOpportunityCard({ 
  opportunity, 
  onClick, 
  className = '' 
}: FlippingOpportunityCardProps) {
  const formatPrice = (price: number) => {
    return price.toLocaleString();
  };

  const formatPercentage = (value: number | string) => {
    const numValue = typeof value === 'string' ? parseFloat(value) : value;
    return `${numValue > 0 ? '+' : ''}${numValue.toFixed(1)}%`;
  };

  const getRiskColor = (riskLevel: string) => {
    switch (riskLevel) {
      case 'low': return 'text-green-400 bg-green-400/10 border-green-400/30';
      case 'medium': return 'text-yellow-400 bg-yellow-400/10 border-yellow-400/30';
      case 'high': return 'text-red-400 bg-red-400/10 border-red-400/30';
      default: return 'text-gray-400 bg-gray-400/10 border-gray-400/30';
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-green-400';
    if (confidence >= 0.6) return 'text-yellow-400';
    if (confidence >= 0.4) return 'text-orange-400';
    return 'text-red-400';
  };

  const getStabilityColor = (stability: number | string) => {
    const numStability = typeof stability === 'string' ? parseFloat(stability) : stability;
    if (numStability >= 0.8) return 'text-green-400';
    if (numStability >= 0.6) return 'text-blue-400';
    if (numStability >= 0.4) return 'text-yellow-400';
    return 'text-red-400';
  };

  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      className={`bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6 cursor-pointer transition-all duration-200 hover:border-purple-500/50 hover:shadow-lg hover:shadow-purple-500/10 ${className}`}
      onClick={onClick}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <ArrowTrendingUpIcon className="w-5 h-5 text-purple-400" />
            <h3 className="text-lg font-semibold text-gray-100">
              {opportunity.item_name}
            </h3>
          </div>
          <div className="flex items-center gap-2">
            <div className="px-3 py-1.5 rounded-full border bg-purple-400/10 border-purple-400/30 text-purple-400">
              <div className="flex items-center gap-2 text-sm font-semibold">
                <ShoppingCartIcon className="w-3 h-3" />
                <span>FLIP</span>
              </div>
            </div>
            <div className={`px-2 py-1 rounded-full text-xs font-semibold ${getRiskColor(opportunity.strategy.risk_level)}`}>
              {opportunity.strategy.risk_level_display}
            </div>
          </div>
        </div>
        <div className="flex flex-col items-end gap-2">
          <div className={`text-right ${getConfidenceColor(opportunity.strategy.confidence_score)}`}>
            <div className="text-xs text-gray-400">Confidence</div>
            <div className="text-sm font-bold">
              {(opportunity.strategy.confidence_score * 100).toFixed(0)}%
            </div>
          </div>
        </div>
      </div>

      {/* Key Metrics Grid */}
      <div className="grid grid-cols-3 gap-4 mb-4">
        <div className="text-center">
          <div className="text-xs text-gray-400 mb-1">Margin per Item</div>
          <div className="text-lg font-bold text-green-400">
            {formatPrice(opportunity.margin)} gp
          </div>
        </div>
        <div className="text-center">
          <div className="text-xs text-gray-400 mb-1">Total Potential</div>
          <div className="text-lg font-bold text-emerald-400">
            {formatPrice(opportunity.total_profit_potential)} gp
          </div>
        </div>
        <div className="text-center">
          <div className="text-xs text-gray-400 mb-1">Margin %</div>
          <div className="text-lg font-bold text-purple-400">
            {formatPercentage(opportunity.margin_percentage)}
          </div>
        </div>
      </div>

      {/* Buy/Sell Prices */}
      <div className="mb-4">
        <div className="text-sm text-gray-400 mb-2">Price Points</div>
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-gray-700/30 rounded-lg p-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-300">Buy Price</span>
              <span className="text-sm font-semibold text-red-300">
                {formatPrice(opportunity.buy_price)} gp
              </span>
            </div>
          </div>
          <div className="bg-gray-700/30 rounded-lg p-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-300">Sell Price</span>
              <span className="text-sm font-semibold text-green-300">
                {formatPrice(opportunity.sell_price)} gp
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Trading Details */}
      <div className="mb-4">
        <div className="text-sm text-gray-400 mb-2">Trading Details</div>
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-gray-700/20 rounded-lg p-3">
            <div className="text-xs text-gray-400 mb-1">Recommended Qty</div>
            <div className="text-sm font-semibold text-gray-200">
              {opportunity.recommended_quantity.toLocaleString()} items
            </div>
          </div>
          <div className="bg-gray-700/20 rounded-lg p-3">
            <div className="text-xs text-gray-400 mb-1">Est. Flip Time</div>
            <div className="text-sm font-semibold text-gray-200">
              {opportunity.estimated_flip_time_minutes} min
            </div>
          </div>
        </div>
      </div>

      {/* Volume and Stability */}
      <div className="mb-4">
        <div className="text-sm text-gray-400 mb-2">Market Data</div>
        <div className="space-y-2">
          <div className="flex items-center justify-between bg-gray-700/20 rounded-lg p-3">
            <div className="flex items-center gap-2">
              <ChartBarIcon className="w-4 h-4 text-blue-400" />
              <span className="text-sm text-gray-300">
                Buy Vol: {opportunity.buy_volume.toLocaleString()} | 
                Sell Vol: {opportunity.sell_volume.toLocaleString()}
              </span>
            </div>
          </div>
          <div className="flex items-center justify-between bg-gray-700/20 rounded-lg p-3">
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${getStabilityColor(opportunity.price_stability)} animate-pulse`}></div>
              <span className="text-sm text-gray-300">Price Stability:</span>
              <span className={`text-sm font-semibold ${getStabilityColor(opportunity.price_stability)}`}>
                {(parseFloat(opportunity.price_stability.toString()) * 100).toFixed(0)}%
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Capital Requirements */}
      <div className="mb-4">
        <div className="text-sm text-gray-400 mb-2">Capital Requirements</div>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-gray-400">Min Capital:</span>
            <span className="ml-2 font-semibold text-gray-200">
              {formatPrice(opportunity.strategy.min_capital_required)} gp
            </span>
          </div>
          <div>
            <span className="text-gray-400">Recommended:</span>
            <span className="ml-2 font-semibold text-gray-200">
              {formatPrice(opportunity.strategy.recommended_capital)} gp
            </span>
          </div>
        </div>
      </div>

      {/* ROI and Performance */}
      <div className="border-t border-gray-700/50 pt-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ArrowTrendingUpIcon className="w-4 h-4 text-green-400" />
            <span className="text-sm text-gray-300">
              ROI: <span className="font-semibold text-green-400">
                {opportunity.strategy.roi_percentage.toFixed(1)}%
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
    </motion.div>
  );
}

export default FlippingOpportunityCard;