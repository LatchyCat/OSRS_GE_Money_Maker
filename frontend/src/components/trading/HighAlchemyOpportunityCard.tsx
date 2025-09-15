import React from 'react';
import { motion } from 'framer-motion';
import { 
  ArrowTrendingUpIcon,
  ClockIcon,
  SparklesIcon,
  BoltIcon,
  ChartBarIcon,
  StarIcon,
  HeartIcon,
  EyeIcon,
  FireIcon,
  BeakerIcon,
  CurrencyDollarIcon,
  ExclamationTriangleIcon,
  CalculatorIcon
} from '@heroicons/react/24/outline';
import { HeartIcon as HeartSolidIcon } from '@heroicons/react/24/solid';
import { Wand2, TrendingUp, TrendingDown } from 'lucide-react';
import type { Item } from '../../types';

interface HighAlchemyOpportunityCardProps {
  item: Item & {
    profit_per_cast?: number;
    nature_rune_cost?: number;
    is_favorite?: boolean;
    real_time_data?: any;
    ai_insights?: any;
    ai_confidence?: number;
    ai_timing?: string;
    ai_recommendations?: string[];
  };
  onClick?: () => void;
  onToggleFavorite?: () => void;
  onQuickTrade?: () => void;
  onOpenCalculator?: () => void;
  onOpenChart?: () => void;
  className?: string;
}

export function HighAlchemyOpportunityCard({ 
  item, 
  onClick,
  onToggleFavorite,
  onQuickTrade,
  onOpenCalculator,
  onOpenChart, 
  className = '' 
}: HighAlchemyOpportunityCardProps) {
  const formatPrice = (price: number) => {
    return price.toLocaleString();
  };

  const formatPercentage = (value: number) => {
    return `${(value * 100).toFixed(1)}%`;
  };

  const getScoreColor = (score: number) => {
    if (score >= 0.8) return 'text-green-400';
    if (score >= 0.6) return 'text-yellow-400';
    if (score >= 0.4) return 'text-orange-400';
    return 'text-red-400';
  };

  const getScoreGradient = (score: number) => {
    if (score >= 0.8) return 'from-green-500 to-emerald-500';
    if (score >= 0.6) return 'from-yellow-500 to-amber-500';
    if (score >= 0.4) return 'from-orange-500 to-red-500';
    return 'from-red-500 to-red-700';
  };

  // Calculate profit per cast (high alch value - nature rune cost - item cost)
  const natureRuneCost = 180; // Approximate nature rune cost
  const buyPrice = item.current_buy_price || 0;
  const profitPerCast = (item.high_alch || 0) - buyPrice - natureRuneCost;
  const isProfit = profitPerCast > 0;
  const profitMargin = buyPrice > 0 ? (profitPerCast / buyPrice) * 100 : 0;

  // Calculate XP per hour (assuming 1200 casts per hour)
  const castsPerHour = 1200;
  const xpPerCast = 65; // High alchemy XP
  const xpPerHour = castsPerHour * xpPerCast;
  const profitPerHour = profitPerCast * castsPerHour;

  // Calculate scores with fallbacks when profit_calc data is missing
  const viabilityScore = item.profit_calc?.high_alch_viability_score || 
    (isProfit ? Math.min(profitMargin / 20, 1) : 0); // Scale 0-100% margin to 0-1 viability
  
  const efficiencyRating = item.profit_calc?.alch_efficiency_rating || 
    (buyPrice > 0 ? Math.min((profitPerCast / Math.max(buyPrice, 1)) * 2, 1) : 0); // Profit ratio scaled
  
  const xpEfficiency = item.profit_calc?.magic_xp_efficiency || 
    (item.high_alch ? Math.min((item.high_alch / 10000), 1) : 0); // Higher alch value = better XP efficiency

  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      className={`bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6 cursor-pointer transition-all duration-200 hover:border-yellow-500/50 hover:shadow-lg hover:shadow-yellow-500/10 ${className}`}
      onClick={onClick}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <Wand2 className="w-5 h-5 text-yellow-400" />
            <h3 className="text-lg font-semibold text-gray-100">
              {item.name}
            </h3>
          </div>
          <div className="flex items-center gap-2">
            <div className="px-3 py-1.5 rounded-full border bg-yellow-400/10 border-yellow-400/30 text-yellow-400">
              <div className="flex items-center gap-2 text-sm font-semibold">
                <BoltIcon className="w-3 h-3" />
                <span>HIGH ALCH</span>
              </div>
            </div>
            {viabilityScore >= 0.7 && (
              <div className="px-2 py-1 rounded-full text-xs font-semibold text-green-400 bg-green-400/10 border border-green-400/30">
                HOT
              </div>
            )}
          </div>
        </div>
        <div className="flex flex-col items-end gap-2">
          <div className={`text-right ${getScoreColor(viabilityScore)}`}>
            <div className="text-xs text-gray-400">Viability</div>
            <div className="text-sm font-bold">
              {formatPercentage(viabilityScore)}
            </div>
          </div>
        </div>
      </div>

      {/* Key Metrics Grid */}
      <div className="grid grid-cols-3 gap-4 mb-4">
        <div className="text-center">
          <div className="text-xs text-gray-400 mb-1">Profit/Cast</div>
          <div className={`text-lg font-bold ${isProfit ? 'text-green-400' : 'text-red-400'}`}>
            {isProfit ? '+' : ''}{formatPrice(profitPerCast)} gp
          </div>
        </div>
        <div className="text-center">
          <div className="text-xs text-gray-400 mb-1">GP/Hour</div>
          <div className={`text-lg font-bold ${isProfit ? 'text-emerald-400' : 'text-red-400'}`}>
            {isProfit ? '+' : ''}{formatPrice(profitPerHour)} gp/h
          </div>
        </div>
        <div className="text-center">
          <div className="text-xs text-gray-400 mb-1">XP/Hour</div>
          <div className="text-lg font-bold text-blue-400">
            {formatPrice(xpPerHour)} xp/h
          </div>
        </div>
      </div>

      {/* Price Breakdown */}
      <div className="mb-4">
        <div className="text-sm text-gray-400 mb-2">Price Analysis</div>
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-gray-700/30 rounded-lg p-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-300">Buy Price</span>
              <span className="text-sm font-semibold text-red-300">
                {formatPrice(item.current_buy_price || 0)} gp
              </span>
            </div>
          </div>
          <div className="bg-gray-700/30 rounded-lg p-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-300">High Alch</span>
              <span className="text-sm font-semibold text-green-300">
                {formatPrice(item.high_alch || 0)} gp
              </span>
            </div>
          </div>
        </div>
        <div className="mt-2 bg-gray-700/20 rounded-lg p-3">
          <div className="flex items-center justify-between text-xs">
            <span className="text-gray-400">Nature Rune Cost:</span>
            <span className="text-orange-300">{formatPrice(natureRuneCost)} gp</span>
          </div>
        </div>
      </div>

      {/* Efficiency Metrics */}
      <div className="mb-4">
        <div className="text-sm text-gray-400 mb-2">Efficiency Scores</div>
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-400">Efficiency Rating</span>
            <div className="flex items-center gap-2">
              <div className="w-16 bg-gray-700 rounded-full h-2">
                <div 
                  className={`h-full rounded-full transition-all duration-300 bg-gradient-to-r ${getScoreGradient(efficiencyRating)}`}
                  style={{ width: `${efficiencyRating * 100}%` }}
                />
              </div>
              <span className={`text-xs font-semibold ${getScoreColor(efficiencyRating)}`}>
                {formatPercentage(efficiencyRating)}
              </span>
            </div>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-400">XP Efficiency</span>
            <div className="flex items-center gap-2">
              <div className="w-16 bg-gray-700 rounded-full h-2">
                <div 
                  className={`h-full rounded-full transition-all duration-300 bg-gradient-to-r ${getScoreGradient(xpEfficiency)}`}
                  style={{ width: `${xpEfficiency * 100}%` }}
                />
              </div>
              <span className={`text-xs font-semibold ${getScoreColor(xpEfficiency)}`}>
                {formatPercentage(xpEfficiency)}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Trading Information */}
      <div className="mb-4">
        <div className="text-sm text-gray-400 mb-2">Trading Details</div>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-gray-400">GE Limit:</span>
            <span className="ml-2 font-semibold text-gray-200">
              {item.limit?.toLocaleString() || 'N/A'}
            </span>
          </div>
          <div>
            <span className="text-gray-400">Members:</span>
            <span className="ml-2 font-semibold text-gray-200">
              {item.members ? 'Yes' : 'No'}
            </span>
          </div>
        </div>
      </div>

      {/* Volume and Risk */}
      <div className="mb-4">
        <div className="text-sm text-gray-400 mb-2">Market Data</div>
        <div className="flex items-center justify-between bg-gray-700/20 rounded-lg p-3">
          <div className="flex items-center gap-2">
            <ChartBarIcon className="w-4 h-4 text-blue-400" />
            <span className="text-sm text-gray-300">
              Daily Vol: {(item.daily_volume || 0).toLocaleString()}
            </span>
          </div>
          <div className="text-sm">
            <span className="text-gray-400">Score: </span>
            <span className={`font-semibold ${getScoreColor(item.recommendation_score || 0)}`}>
              {formatPercentage(item.recommendation_score || 0)}
            </span>
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="grid grid-cols-2 gap-2 mb-4">
        <button
          onClick={(e) => {
            e.stopPropagation();
            onOpenChart?.();
          }}
          className="flex items-center justify-center gap-1 px-2 py-2 bg-yellow-600 hover:bg-yellow-700 text-white rounded-lg transition-colors text-xs font-medium"
        >
          <EyeIcon className="w-3 h-3" />
          <span className="hidden sm:inline">View Chart</span>
          <span className="sm:hidden">Chart</span>
        </button>
        
        <button
          onClick={(e) => {
            e.stopPropagation();
            onOpenCalculator?.();
          }}
          className="flex items-center justify-center gap-1 px-2 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors text-xs font-medium"
        >
          <CalculatorIcon className="w-3 h-3" />
          <span className="hidden sm:inline">Calculator</span>
          <span className="sm:hidden">Calc</span>
        </button>
        
        <button
          onClick={(e) => {
            e.stopPropagation();
            onOpenChart?.();
          }}
          className="flex items-center justify-center gap-1 px-2 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors text-xs font-medium"
        >
          <ChartBarIcon className="w-3 h-3" />
          <span className="hidden sm:inline">History</span>
          <span className="sm:hidden">Hist</span>
        </button>
        
        <button
          onClick={(e) => {
            e.stopPropagation();
            onQuickTrade?.();
          }}
          className="flex items-center justify-center gap-1 px-2 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors text-xs font-medium"
        >
          <CurrencyDollarIcon className="w-3 h-3" />
          <span className="hidden sm:inline">Trade</span>
          <span className="sm:hidden">Trade</span>
        </button>
      </div>

      {/* Footer with Last Updated */}
      <div className="border-t border-gray-700/50 pt-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ArrowTrendingUpIcon className="w-4 h-4 text-green-400" />
            <span className="text-sm text-gray-300">
              Trend: <span className="font-semibold text-green-400">
                {item.profit_calc?.price_trend || 'Stable'}
              </span>
            </span>
          </div>
          <div className="flex items-center gap-2">
            <ClockIcon className="w-4 h-4 text-blue-400" />
            <span className="text-sm text-gray-300">
              <span className="font-semibold">
                {item.updated_at 
                  ? new Date(item.updated_at).toLocaleDateString() 
                  : new Date().toLocaleDateString()}
              </span>
            </span>
          </div>
        </div>
      </div>

      {/* Profitability Indicator */}
      {!isProfit && (
        <div className="mt-3 px-3 py-2 bg-red-400/10 border border-red-400/30 rounded-lg">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-red-400 animate-pulse"></div>
            <span className="text-sm text-red-400 font-medium">
              Currently Unprofitable
            </span>
          </div>
        </div>
      )}
      
      {isProfit && profitPerHour > 100000 && (
        <div className="mt-3 px-3 py-2 bg-green-400/10 border border-green-400/30 rounded-lg">
          <div className="flex items-center gap-2">
            <StarIcon className="w-4 h-4 text-green-400" />
            <span className="text-sm text-green-400 font-medium">
              High Profit Opportunity
            </span>
          </div>
        </div>
      )}
    </motion.div>
  );
}

export default HighAlchemyOpportunityCard;