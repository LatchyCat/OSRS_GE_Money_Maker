import React from 'react';
import { motion } from 'framer-motion';
import { 
  CurrencyDollarIcon,
  ClockIcon,
  ChartBarIcon,
  BeakerIcon,
  AcademicCapIcon,
  BanknotesIcon
} from '@heroicons/react/24/outline';
import { Target, TrendingUp, Zap } from 'lucide-react';

interface RuneTradingOpportunity {
  rune_type: string;
  rune_item_id: number;
  level_required: number;
  essence_buy_price: number;
  rune_sell_price: number;
  profit_per_essence: number;
  profit_per_rune: number;
  runes_per_essence: number;
  hourly_profit_gp: number;
  runes_per_hour: number;
  essences_per_hour: number;
  capital_required: number;
  profit_margin_pct: number;
  volume_score: number;
  last_updated: string;
  data_freshness: string;
}

interface RuneTradingOpportunityCardProps {
  opportunity: RuneTradingOpportunity;
  onClick?: () => void;
  className?: string;
}

export function RuneTradingOpportunityCard({ 
  opportunity, 
  onClick, 
  className = '' 
}: RuneTradingOpportunityCardProps) {
  const formatPrice = (price: number) => {
    if (price >= 1000000) {
      return `${(price / 1000000).toFixed(1)}M`;
    } else if (price >= 1000) {
      return `${(price / 1000).toFixed(1)}K`;
    }
    return price.toLocaleString();
  };

  const getProfitColor = (profit: number) => {
    if (profit > 500) return 'text-green-400';
    if (profit > 100) return 'text-yellow-400';
    if (profit > 0) return 'text-orange-400';
    return 'text-red-400';
  };

  const getLevelColor = (level: number) => {
    if (level >= 77) return 'text-purple-400';
    if (level >= 50) return 'text-blue-400';
    if (level >= 25) return 'text-yellow-400';
    return 'text-green-400';
  };

  const getVolumeColor = (score: number) => {
    if (score >= 0.8) return 'text-green-400';
    if (score >= 0.6) return 'text-yellow-400';
    if (score >= 0.4) return 'text-orange-400';
    return 'text-red-400';
  };

  const getRuneTypeColor = (runeType: string) => {
    switch (runeType.toLowerCase()) {
      case 'blood':
        return 'text-red-400 bg-red-400/10 border-red-400/30';
      case 'soul':
        return 'text-purple-400 bg-purple-400/10 border-purple-400/30';
      case 'death':
        return 'text-gray-300 bg-gray-300/10 border-gray-300/30';
      case 'law':
        return 'text-yellow-400 bg-yellow-400/10 border-yellow-400/30';
      case 'nature':
        return 'text-green-400 bg-green-400/10 border-green-400/30';
      case 'cosmic':
        return 'text-cyan-400 bg-cyan-400/10 border-cyan-400/30';
      default:
        return 'text-blue-400 bg-blue-400/10 border-blue-400/30';
    }
  };

  const isProfitable = opportunity.profit_per_essence > 0;

  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      className={`bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6 cursor-pointer transition-all duration-200 hover:border-blue-500/50 hover:shadow-lg hover:shadow-blue-500/10 ${className}`}
      onClick={onClick}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <Target className="w-5 h-5 text-blue-400" />
            <h3 className="text-lg font-semibold text-gray-100">
              {opportunity.rune_type} Runes
            </h3>
          </div>
          <div className="flex items-center gap-2">
            <div className={`px-3 py-1.5 rounded-full border ${getRuneTypeColor(opportunity.rune_type)}`}>
              <div className="flex items-center gap-2 text-sm font-semibold">
                <Zap className="w-3 h-3" />
                <span>TRADING</span>
              </div>
            </div>
            {!isProfitable && (
              <div className="px-2 py-1 rounded-full text-xs font-semibold text-red-400 bg-red-400/10 border-red-400/30">
                UNPROFITABLE
              </div>
            )}
          </div>
        </div>
        <div className="flex flex-col items-end gap-2">
          <div className={`text-right ${getVolumeColor(opportunity.volume_score)}`}>
            <div className="text-xs text-gray-400">Volume Score</div>
            <div className="text-sm font-bold">
              {(opportunity.volume_score * 100).toFixed(0)}%
            </div>
          </div>
        </div>
      </div>

      {/* Key Metrics Grid */}
      <div className="grid grid-cols-3 gap-4 mb-4">
        <div className="text-center">
          <div className="text-xs text-gray-400 mb-1">Hourly Profit</div>
          <div className={`text-lg font-bold ${getProfitColor(opportunity.hourly_profit_gp)}`}>
            {opportunity.hourly_profit_gp >= 0 ? '+' : ''}{formatPrice(opportunity.hourly_profit_gp)} gp
          </div>
        </div>
        <div className="text-center">
          <div className="text-xs text-gray-400 mb-1">Runes/Hour</div>
          <div className="text-lg font-bold text-blue-400">
            {opportunity.runes_per_hour?.toLocaleString() || '0'}
          </div>
        </div>
        <div className="text-center">
          <div className="text-xs text-gray-400 mb-1">Level Required</div>
          <div className={`text-lg font-bold ${getLevelColor(opportunity.level_required)}`}>
            {opportunity.level_required}
          </div>
        </div>
      </div>

      {/* Profit Breakdown */}
      <div className="mb-4">
        <div className="text-sm text-gray-400 mb-2">Profit Analysis</div>
        <div className="bg-gray-700/30 rounded-lg p-3">
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-gray-400">Per Essence:</span>
              <span className={`ml-2 font-semibold ${getProfitColor(opportunity.profit_per_essence)}`}>
                {opportunity.profit_per_essence >= 0 ? '+' : ''}{formatPrice(opportunity.profit_per_essence)} gp
              </span>
            </div>
            <div>
              <span className="text-gray-400">Per Rune:</span>
              <span className={`ml-2 font-semibold ${getProfitColor(opportunity.profit_per_rune)}`}>
                {opportunity.profit_per_rune >= 0 ? '+' : ''}{formatPrice(opportunity.profit_per_rune)} gp
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Market Data */}
      <div className="mb-4">
        <div className="text-sm text-gray-400 mb-2">Current Market Prices</div>
        <div className="space-y-2">
          <div className="bg-gray-700/20 rounded-lg p-3">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <div className="text-sm font-semibold text-gray-200">Essence Cost</div>
                <div className="text-xs text-gray-400">Buy price per essence</div>
              </div>
              <div className="text-right">
                <div className="text-sm font-semibold text-red-300">
                  {formatPrice(opportunity.essence_buy_price)} gp
                </div>
              </div>
            </div>
          </div>
          <div className="bg-gray-700/20 rounded-lg p-3">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <div className="text-sm font-semibold text-gray-200">Rune Value</div>
                <div className="text-xs text-gray-400">Sell price per rune</div>
              </div>
              <div className="text-right">
                <div className="text-sm font-semibold text-green-300">
                  {formatPrice(opportunity.rune_sell_price)} gp
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Efficiency Metrics */}
      <div className="mb-4">
        <div className="text-sm text-gray-400 mb-2">Efficiency</div>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-gray-400">Multiplier:</span>
            <span className="ml-2 font-semibold text-purple-300">
              {opportunity.runes_per_essence}x
            </span>
          </div>
          <div>
            <span className="text-gray-400">Capital/Hour:</span>
            <span className="ml-2 font-semibold text-gray-200">
              {formatPrice(opportunity.capital_required)} gp
            </span>
          </div>
        </div>
      </div>

      {/* Footer Stats */}
      <div className="border-t border-gray-700/50 pt-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ChartBarIcon className="w-4 h-4 text-green-400" />
            <span className="text-sm text-gray-300">
              Margin: <span className={`font-semibold ${getProfitColor(opportunity.profit_margin_pct)}`}>
                {opportunity.profit_margin_pct >= 0 ? '+' : ''}{opportunity.profit_margin_pct.toFixed(1)}%
              </span>
            </span>
          </div>
          <div className="flex items-center gap-2">
            <ClockIcon className="w-4 h-4 text-blue-400" />
            <span className="text-sm text-gray-300">
              Real-Time Data
            </span>
          </div>
        </div>
      </div>

      {/* Data Freshness */}
      <div className="mt-3 px-3 py-2 bg-blue-400/10 border border-blue-400/30 rounded-lg">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-blue-400 animate-pulse"></div>
          <span className="text-sm text-blue-400 font-medium">
            OSRS Wiki API • {opportunity.data_freshness}
          </span>
        </div>
      </div>

      {/* Warning for unprofitable opportunities */}
      {!isProfitable && (
        <div className="mt-3 px-3 py-2 bg-red-400/10 border border-red-400/30 rounded-lg">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-red-400"></div>
            <span className="text-sm text-red-400 font-medium">
              Currently unprofitable - essence costs exceed rune value
            </span>
          </div>
        </div>
      )}
    </motion.div>
  );
}

export default RuneTradingOpportunityCard;