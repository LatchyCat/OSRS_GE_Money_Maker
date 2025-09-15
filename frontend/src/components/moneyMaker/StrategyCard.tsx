import React from 'react';
import { motion } from 'framer-motion';
import { 
  TrendingUp, 
  Clock, 
  Target, 
  AlertTriangle, 
  Crown,
  DollarSign,
  Percent,
  Activity
} from 'lucide-react';
import * as MoneyMakerTypes from '../../types/moneyMaker';

interface StrategyCardProps {
  strategy: MoneyMakerTypes.MoneyMakerStrategy;
  rank?: number;
  showDetails?: boolean;
  onClick?: () => void;
}

export const StrategyCard: React.FC<StrategyCardProps> = ({
  strategy,
  rank,
  showDetails = false,
  onClick
}) => {
  const strategyTypeColor = MoneyMakerTypes.getStrategyTypeColor(strategy.strategy.strategy_type);
  const riskLevelColor = MoneyMakerTypes.RISK_LEVEL_COLORS[strategy.strategy.risk_level];
  
  const hourlyProfitFormatted = MoneyMakerTypes.formatGP(strategy.hourly_profit_gp);
  const capitalFormatted = MoneyMakerTypes.formatGP(strategy.starting_capital);
  const targetFormatted = MoneyMakerTypes.formatGP(strategy.target_capital);
  
  const profitEfficiency = strategy.profit_efficiency_score;
  const successRate = parseFloat(strategy.success_rate_percentage.toString());
  const capitalGrowthRate = strategy.capital_growth_rate;

  const getEfficiencyRating = (score: number): { label: string; color: string } => {
    if (score >= 0.1) return { label: 'Excellent', color: 'text-green-400' };
    if (score >= 0.05) return { label: 'Good', color: 'text-yellow-400' };
    if (score >= 0.02) return { label: 'Fair', color: 'text-orange-400' };
    return { label: 'Poor', color: 'text-red-400' };
  };

  const efficiencyRating = getEfficiencyRating(profitEfficiency);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -2 }}
      transition={{ duration: 0.2 }}
      onClick={onClick}
      className={`
        relative bg-gray-900 rounded-lg p-4 border border-gray-700
        ${onClick ? 'cursor-pointer hover:border-gray-600' : ''}
        ${rank === 1 ? 'border-yellow-500/50 bg-gradient-to-br from-yellow-900/10 to-gray-900' : ''}
        ${rank === 2 ? 'border-gray-400/50 bg-gradient-to-br from-gray-700/10 to-gray-900' : ''}
        ${rank === 3 ? 'border-orange-500/50 bg-gradient-to-br from-orange-900/10 to-gray-900' : ''}
      `}
    >
      {/* Rank Badge */}
      {rank && rank <= 3 && (
        <div className="absolute -top-2 -right-2 z-10">
          <div className={`
            w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold
            ${rank === 1 ? 'bg-yellow-500 text-yellow-900' : ''}
            ${rank === 2 ? 'bg-gray-400 text-gray-900' : ''}
            ${rank === 3 ? 'bg-orange-500 text-orange-900' : ''}
          `}>
            {rank === 1 && <Crown className="h-4 w-4" />}
            {rank !== 1 && rank}
          </div>
        </div>
      )}

      {/* Strategy Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1 min-w-0">
          <h4 className="text-lg font-semibold text-white truncate mb-1">
            {strategy.strategy.name}
          </h4>
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`text-sm font-medium ${strategyTypeColor}`}>
              {MoneyMakerTypes.STRATEGY_TYPE_DISPLAY[strategy.strategy.strategy_type]}
            </span>
            <span className="text-gray-400">•</span>
            <span className={`text-sm ${riskLevelColor} capitalize`}>
              {strategy.strategy.risk_level} Risk
            </span>
          </div>
        </div>
        
        {/* Key Metrics */}
        <div className="text-right flex-shrink-0 ml-3">
          <p className="text-xl font-bold text-green-400">{hourlyProfitFormatted}</p>
          <p className="text-xs text-gray-400">per hour</p>
        </div>
      </div>

      {/* Core Stats Grid */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="bg-gray-800/50 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-1">
            <DollarSign className="h-4 w-4 text-blue-400" />
            <span className="text-xs text-gray-400">Capital Required</span>
          </div>
          <p className="text-sm font-semibold text-white">{capitalFormatted}</p>
        </div>

        <div className="bg-gray-800/50 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-1">
            <Target className="h-4 w-4 text-purple-400" />
            <span className="text-xs text-gray-400">Target Goal</span>
          </div>
          <p className="text-sm font-semibold text-white">{targetFormatted}</p>
        </div>

        <div className="bg-gray-800/50 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-1">
            <Percent className="h-4 w-4 text-yellow-400" />
            <span className="text-xs text-gray-400">Success Rate</span>
          </div>
          <p className="text-sm font-semibold text-white">{successRate.toFixed(1)}%</p>
        </div>

        <div className="bg-gray-800/50 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-1">
            <Activity className={`h-4 w-4 ${efficiencyRating.color}`} />
            <span className="text-xs text-gray-400">Efficiency</span>
          </div>
          <p className={`text-sm font-semibold ${efficiencyRating.color}`}>
            {efficiencyRating.label}
          </p>
        </div>
      </div>

      {/* Growth & Time Metrics */}
      {(capitalGrowthRate > 0 || strategy.estimated_time_to_target) && (
        <div className="grid grid-cols-2 gap-3 mb-4">
          {capitalGrowthRate > 0 && (
            <div className="flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-green-400" />
              <div>
                <p className="text-xs text-gray-400">Daily Growth</p>
                <p className="text-sm font-medium text-green-400">{capitalGrowthRate.toFixed(1)}%</p>
              </div>
            </div>
          )}
          
          {strategy.estimated_time_to_target && (
            <div className="flex items-center gap-2">
              <Clock className="h-4 w-4 text-blue-400" />
              <div>
                <p className="text-xs text-gray-400">Est. Time to Goal</p>
                <p className="text-sm font-medium text-blue-400">
                  {strategy.estimated_time_to_target < 24 
                    ? `${strategy.estimated_time_to_target}h`
                    : `${Math.ceil(strategy.estimated_time_to_target / 24)}d`
                  }
                </p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Special Features */}
      <div className="space-y-2">
        {/* Lazy Tax Exploitation */}
        {strategy.exploits_lazy_tax && strategy.lazy_tax_exploitation.exploits_lazy_tax && (
          <div className="flex items-center gap-2 p-2 bg-purple-900/20 rounded border border-purple-700/30">
            <Crown className="h-4 w-4 text-purple-400 flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-purple-300">Lazy Tax Exploitation</p>
              <p className="text-xs text-purple-400 truncate">
                {strategy.lazy_tax_exploitation.premium_percentage?.toFixed(1)}% premium from convenience
              </p>
            </div>
          </div>
        )}

        {/* GE Tax Impact */}
        {strategy.ge_tax_impact_analysis.tax_efficiency_rating && (
          <div className={`flex items-center gap-2 p-2 rounded border ${
            strategy.ge_tax_impact_analysis.tax_efficiency_rating === 'high'
              ? 'bg-green-900/20 border-green-700/30'
              : strategy.ge_tax_impact_analysis.tax_efficiency_rating === 'medium'
                ? 'bg-yellow-900/20 border-yellow-700/30'
                : 'bg-red-900/20 border-red-700/30'
          }`}>
            <DollarSign className={`h-4 w-4 flex-shrink-0 ${
              strategy.ge_tax_impact_analysis.tax_efficiency_rating === 'high'
                ? 'text-green-400'
                : strategy.ge_tax_impact_analysis.tax_efficiency_rating === 'medium'
                  ? 'text-yellow-400'
                  : 'text-red-400'
            }`} />
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-gray-300">GE Tax Efficiency</p>
              <p className={`text-xs capitalize ${
                strategy.ge_tax_impact_analysis.tax_efficiency_rating === 'high'
                  ? 'text-green-400'
                  : strategy.ge_tax_impact_analysis.tax_efficiency_rating === 'medium'
                    ? 'text-yellow-400'
                    : 'text-red-400'
              }`}>
                {strategy.ge_tax_impact_analysis.tax_efficiency_rating} efficiency
              </p>
            </div>
          </div>
        )}

        {/* Capital Scaling */}
        {strategy.scales_with_capital && (
          <div className="flex items-center gap-2 p-2 bg-blue-900/20 rounded border border-blue-700/30">
            <TrendingUp className="h-4 w-4 text-blue-400 flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-blue-300">Capital Scalable</p>
              <p className="text-xs text-blue-400">
                {parseFloat(strategy.capital_efficiency_multiplier.toString()).toFixed(1)}x efficiency multiplier
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Extended Details */}
      {showDetails && strategy.strategy.description && (
        <div className="mt-4 pt-4 border-t border-gray-700">
          <p className="text-sm text-gray-300 leading-relaxed">
            {strategy.strategy.description}
          </p>
          
          {/* Performance Stats */}
          <div className="mt-3 grid grid-cols-2 gap-4 text-xs">
            <div>
              <p className="text-gray-400">Total Trades:</p>
              <p className="text-white font-medium">{strategy.total_trades_executed.toLocaleString()}</p>
            </div>
            <div>
              <p className="text-gray-400">Total Profit:</p>
              <p className="text-green-400 font-medium">{MoneyMakerTypes.formatGP(strategy.total_profit_realized)}</p>
            </div>
          </div>
        </div>
      )}

      {/* Click Hint */}
      {onClick && (
        <div className="absolute inset-0 bg-gradient-to-r from-blue-900/5 to-purple-900/5 rounded-lg opacity-0 hover:opacity-100 transition-opacity pointer-events-none" />
      )}
    </motion.div>
  );
};