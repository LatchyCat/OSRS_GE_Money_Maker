import React from 'react';
import { motion } from 'framer-motion';
import { 
  SparklesIcon,
  ClockIcon,
  CurrencyDollarIcon,
  ChartBarIcon,
  AcademicCapIcon,
  BeakerIcon
} from '@heroicons/react/24/outline';
import { Sparkles } from 'lucide-react';
import type { RuneMagicStrategy } from '../../types/moneyMaker';

interface RunecraftingOpportunityCardProps {
  strategy: RuneMagicStrategy;
  onClick?: () => void;
  className?: string;
}

export function RunecraftingOpportunityCard({ 
  strategy, 
  onClick, 
  className = '' 
}: RunecraftingOpportunityCardProps) {
  const formatPrice = (price: number) => {
    if (price >= 1000000) {
      return `${(price / 1000000).toFixed(1)}M`;
    } else if (price >= 1000) {
      return `${(price / 1000).toFixed(1)}K`;
    }
    return price.toLocaleString();
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

  const getLevelColor = (level: number) => {
    if (level >= 75) return 'text-purple-400';
    if (level >= 50) return 'text-blue-400';
    if (level >= 25) return 'text-yellow-400';
    return 'text-green-400';
  };

  const primaryRune = strategy.target_runes?.[0];
  const totalSupplies = strategy.magic_supplies?.length || 0;
  const hasHighAlchOpps = strategy.high_alch_opportunities && strategy.high_alch_opportunities.length > 0;

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
            <SparklesIcon className="w-5 h-5 text-purple-400" />
            <h3 className="text-lg font-semibold text-gray-100">
              {strategy.money_maker.strategy.name}
            </h3>
          </div>
          <div className="flex items-center gap-2">
            <div className="px-3 py-1.5 rounded-full border bg-purple-400/10 border-purple-400/30 text-purple-400">
              <div className="flex items-center gap-2 text-sm font-semibold">
                <Sparkles className="w-3 h-3" />
                <span>RUNES</span>
              </div>
            </div>
            <div className={`px-2 py-1 rounded-full text-xs font-semibold ${getRiskColor(strategy.money_maker.strategy.risk_level)}`}>
              {strategy.money_maker.strategy.risk_level_display}
            </div>
          </div>
        </div>
        <div className="flex flex-col items-end gap-2">
          <div className={`text-right ${getConfidenceColor(strategy.money_maker.strategy.confidence_score)}`}>
            <div className="text-xs text-gray-400">Confidence</div>
            <div className="text-sm font-bold">
              {(strategy.money_maker.strategy.confidence_score * 100).toFixed(0)}%
            </div>
          </div>
        </div>
      </div>

      {/* Key Metrics Grid */}
      <div className="grid grid-cols-3 gap-4 mb-4">
        <div className="text-center">
          <div className="text-xs text-gray-400 mb-1">Hourly Profit</div>
          <div className="text-lg font-bold text-green-400">
            {formatPrice(strategy.money_maker.hourly_profit_gp)} gp
          </div>
        </div>
        <div className="text-center">
          <div className="text-xs text-gray-400 mb-1">Runes/Hour</div>
          <div className="text-lg font-bold text-blue-400">
            {strategy.runes_per_hour?.toLocaleString() || '0'}
          </div>
        </div>
        <div className="text-center">
          <div className="text-xs text-gray-400 mb-1">Level Required</div>
          <div className={`text-lg font-bold ${getLevelColor(strategy.runecrafting_level_required)}`}>
            {strategy.runecrafting_level_required}
          </div>
        </div>
      </div>

      {/* Primary Rune */}
      {primaryRune && (
        <div className="mb-4">
          <div className="text-sm text-gray-400 mb-2">Primary Rune</div>
          <div className="bg-gray-700/30 rounded-lg p-3">
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold text-purple-300">
                {primaryRune.type}
              </span>
              <span className="text-sm font-semibold text-green-300">
                +{formatPrice(primaryRune.profit)} gp profit
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Magic Supplies */}
      {strategy.magic_supplies && strategy.magic_supplies.length > 0 && (
        <div className="mb-4">
          <div className="text-sm text-gray-400 mb-2">Magic Supplies ({totalSupplies})</div>
          <div className="space-y-2">
            {strategy.magic_supplies.slice(0, 2).map((supply, index) => (
              <div key={index} className="bg-gray-700/20 rounded-lg p-3">
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="text-sm font-semibold text-gray-200">{supply.name}</div>
                    <div className="text-xs text-gray-400">{supply.usage}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm font-semibold text-green-400">
                      +{formatPrice(supply.profit)} gp
                    </div>
                    <div className="text-xs text-gray-400">
                      {supply.margin_pct.toFixed(1)}% margin
                    </div>
                  </div>
                </div>
              </div>
            ))}
            {totalSupplies > 2 && (
              <div className="text-center text-xs text-gray-500 py-1">
                +{totalSupplies - 2} more supplies...
              </div>
            )}
          </div>
        </div>
      )}

      {/* High Alchemy Opportunities */}
      {hasHighAlchOpps && (
        <div className="mb-4">
          <div className="text-sm text-gray-400 mb-2">High Alchemy</div>
          <div className="bg-yellow-400/10 border border-yellow-400/30 rounded-lg p-3">
            <div className="flex items-center gap-2">
              <BeakerIcon className="w-4 h-4 text-yellow-400" />
              <span className="text-sm text-yellow-400 font-medium">
                {strategy.high_alch_opportunities.length} alchemy opportunities available
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Capital Requirements */}
      <div className="mb-4">
        <div className="text-sm text-gray-400 mb-2">Capital Requirements</div>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-gray-400">Min Capital:</span>
            <span className="ml-2 font-semibold text-gray-200">
              {formatPrice(strategy.money_maker.strategy.min_capital_required)} gp
            </span>
          </div>
          <div>
            <span className="text-gray-400">Recommended:</span>
            <span className="ml-2 font-semibold text-gray-200">
              {formatPrice(strategy.money_maker.strategy.recommended_capital)} gp
            </span>
          </div>
        </div>
      </div>

      {/* Essence Costs */}
      {strategy.essence_costs && Object.keys(strategy.essence_costs).length > 0 && (
        <div className="mb-4">
          <div className="text-sm text-gray-400 mb-2">Essence Costs</div>
          <div className="grid grid-cols-2 gap-2 text-sm">
            {Object.entries(strategy.essence_costs).slice(0, 2).map(([essence, cost]) => (
              <div key={essence} className="bg-gray-700/20 rounded p-2">
                <div className="text-xs text-gray-400 capitalize">{essence.replace('_', ' ')}</div>
                <div className="text-sm font-semibold text-gray-200">{cost} gp</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Footer Stats */}
      <div className="border-t border-gray-700/50 pt-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ChartBarIcon className="w-4 h-4 text-green-400" />
            <span className="text-sm text-gray-300">
              Profit Margin: <span className="font-semibold text-green-400">
                {strategy.money_maker.strategy.profit_margin_pct}%
              </span>
            </span>
          </div>
          <div className="flex items-center gap-2">
            <ClockIcon className="w-4 h-4 text-blue-400" />
            <span className="text-sm text-gray-300">
              Per Hour Method
            </span>
          </div>
        </div>
      </div>

      {/* Activity Status */}
      {!strategy.money_maker.strategy.is_active && (
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

export default RunecraftingOpportunityCard;