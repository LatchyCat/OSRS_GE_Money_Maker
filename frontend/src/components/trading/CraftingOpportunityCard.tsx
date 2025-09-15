import React from 'react';
import { motion } from 'framer-motion';
import { 
  ArrowTrendingUpIcon,
  ClockIcon,
  CurrencyDollarIcon,
  WrenchScrewdriverIcon,
  ChartBarIcon,
  SparklesIcon,
  ExclamationTriangleIcon,
  LightBulbIcon,
  CogIcon,
  ShieldCheckIcon,
  StarIcon
} from '@heroicons/react/24/outline';
import { Hammer } from 'lucide-react';
import type { CraftingOpportunity } from '../../types/tradingStrategies';

interface CraftingOpportunityCardProps {
  opportunity: CraftingOpportunity;
  onClick?: () => void;
  className?: string;
}

export function CraftingOpportunityCard({ 
  opportunity, 
  onClick, 
  className = '' 
}: CraftingOpportunityCardProps) {
  const formatPrice = (price: number) => {
    if (price >= 1000000) {
      return `${(price / 1000000).toFixed(1)}M`;
    } else if (price >= 1000) {
      return `${(price / 1000).toFixed(1)}K`;
    }
    return price.toLocaleString();
  };

  const formatPercentage = (value: number) => {
    if (isNaN(value)) return '0.0%';
    return `${value > 0 ? '+' : ''}${value.toFixed(1)}%`;
  };

  const getRiskColor = (riskLevel: string) => {
    switch (riskLevel) {
      case 'low': return 'text-green-400 bg-green-400/10 border-green-400/30';
      case 'medium': return 'text-yellow-400 bg-yellow-400/10 border-yellow-400/30';
      case 'high': return 'text-red-400 bg-red-400/10 border-red-400/30';
      case 'extreme': return 'text-purple-400 bg-purple-400/10 border-purple-400/30';
      default: return 'text-gray-400 bg-gray-400/10 border-gray-400/30';
    }
  };

  const getSkillColor = (skillName: string) => {
    switch (skillName) {
      case 'Crafting': return 'text-brown-400 bg-orange-400/10 border-orange-400/30';
      case 'Fletching': return 'text-green-400 bg-green-400/10 border-green-400/30';
      case 'Smithing': return 'text-gray-400 bg-gray-400/10 border-gray-400/30';
      case 'Cooking': return 'text-red-400 bg-red-400/10 border-red-400/30';
      default: return 'text-blue-400 bg-blue-400/10 border-blue-400/30';
    }
  };

  const getAIScoreColor = (score?: number) => {
    if (!score) return 'text-gray-400';
    if (score >= 0.8) return 'text-purple-400';
    if (score >= 0.6) return 'text-green-400';
    if (score >= 0.4) return 'text-yellow-400';
    if (score >= 0.2) return 'text-orange-400';
    return 'text-red-400';
  };

  const hasAIData = () => {
    return (opportunity as any).ai_volume_score !== undefined || 
           (opportunity as any).ai_weighted_profit_per_hour !== undefined ||
           (opportunity as any).market_confidence !== undefined;
  };

  const getProfitTier = (profit: number) => {
    if (profit >= 10000) return 'legendary';
    if (profit >= 5000) return 'high';
    if (profit >= 2000) return 'medium';
    if (profit >= 1000) return 'low';
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

  const profitTier = getProfitTier(opportunity.profit_per_craft);
  const tierConfig = getProfitTierConfig(profitTier);

  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      className={`bg-gray-800/50 backdrop-blur-sm border ${
        hasAIData() ? 'border-orange-500/30 shadow-orange-500/5' : 'border-gray-700/50'
      } ${tierConfig.glow} rounded-xl p-6 cursor-pointer transition-all duration-200 hover:border-orange-500/50 hover:shadow-lg hover:shadow-orange-500/10 ${className}`}
      onClick={onClick}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <Hammer className="w-5 h-5 text-orange-400" />
            <h3 className="text-lg font-semibold text-gray-100">
              {opportunity.product_name}
            </h3>
            <div className="flex items-center gap-2">
              {/* Profit Tier Badge */}
              <div className={`flex items-center gap-1 px-2 py-0.5 rounded-full border text-xs font-medium ${tierConfig.color}`}>
                <span>{tierConfig.icon}</span>
                <span>{tierConfig.label}</span>
              </div>
              
              {hasAIData() && (
                <div className="flex items-center gap-1 px-2 py-0.5 bg-orange-400/10 border border-orange-400/30 rounded-full">
                  <SparklesIcon className="w-3 h-3 text-orange-400" />
                  <span className="text-xs text-orange-400 font-medium">AI</span>
                </div>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className={`px-3 py-1.5 rounded-full border ${getSkillColor(opportunity.skill_name)} text-sm font-semibold`}>
              {opportunity.skill_name} Level {opportunity.required_skill_level}
            </div>
            <div className={`px-2 py-1 rounded-full text-xs font-semibold ${getRiskColor((opportunity as any).enhanced_risk_level || opportunity.strategy.risk_level)}`}>
              {((opportunity as any).enhanced_risk_level || opportunity.strategy.risk_level).charAt(0).toUpperCase() + ((opportunity as any).enhanced_risk_level || opportunity.strategy.risk_level).slice(1)} Risk
            </div>
          </div>
        </div>
        <div className="flex flex-col items-end gap-2">
          {hasAIData() && (opportunity as any).ai_volume_score !== undefined ? (
            <div className="flex items-center gap-2">
              <div className="text-right text-gray-300">
                <div className="text-xs text-gray-400">Confidence</div>
                <div className="text-sm font-bold">
                  {((opportunity as any).market_confidence || 0).toFixed(0)}%
                </div>
              </div>
              <div className={`text-right ${getAIScoreColor((opportunity as any).ai_volume_score)}`}>
                <div className="flex items-center gap-1 text-xs text-gray-400">
                  <SparklesIcon className="w-3 h-3" />
                  AI Score
                </div>
                <div className="text-sm font-bold">
                  {(((opportunity as any).ai_volume_score || 0) * 100).toFixed(0)}%
                </div>
              </div>
            </div>
          ) : (
            <div className="text-right text-gray-300">
              <div className="text-xs text-gray-400">Profit Margin</div>
              <div className="text-sm font-bold">
                {formatPercentage(opportunity.profit_margin_pct)}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Key Metrics Grid */}
      <div className="grid grid-cols-3 gap-4 mb-4">
        <div className="text-center">
          <div className="text-xs text-gray-400 mb-1 flex items-center justify-center gap-1">
            <span>{tierConfig.icon}</span>
            <span>Profit/Craft</span>
          </div>
          <div className={`text-lg font-bold ${
            profitTier === 'legendary' ? 'text-purple-400' :
            profitTier === 'high' ? 'text-emerald-400' :
            profitTier === 'medium' ? 'text-blue-400' :
            profitTier === 'low' ? 'text-yellow-400' : 'text-gray-400'
          }`}>
            {formatPrice(opportunity.profit_per_craft)} gp
          </div>
        </div>
        <div className="text-center">
          <div className="text-xs text-gray-400 mb-1">Per Hour</div>
          <div className="text-lg font-bold text-emerald-400">
            {formatPrice((opportunity as any).ai_weighted_profit_per_hour || (opportunity.profit_per_craft * opportunity.max_crafts_per_hour))} gp/h
          </div>
        </div>
        <div className="text-center">
          <div className="text-xs text-gray-400 mb-1">Crafts/Hour</div>
          <div className="text-lg font-bold text-blue-400">
            {opportunity.max_crafts_per_hour}
          </div>
        </div>
      </div>

      {/* Materials Breakdown */}
      <div className="mb-4">
        <div className="text-sm text-gray-400 mb-2">Materials & Costs</div>
        <div className="bg-gray-700/20 rounded-lg p-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-300">Materials Cost</span>
            <span className="text-sm font-semibold text-red-300">
              {formatPrice(opportunity.materials_cost)} gp
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-300">Product Price</span>
            <span className="text-sm font-semibold text-green-300">
              {formatPrice(opportunity.product_price)} gp
            </span>
          </div>
          {opportunity.materials_data && opportunity.materials_data.length > 0 && (
            <div className="mt-3 pt-2 border-t border-gray-600/30">
              <div className="text-xs text-gray-400 mb-2">Required Materials:</div>
              <div className="space-y-1">
                {opportunity.materials_data.slice(0, 3).map((material, index) => (
                  <div key={index} className="flex items-center justify-between text-xs">
                    <span className="text-gray-300">{material.quantity}x {material.name}</span>
                    <span className="text-gray-400">{formatPrice(material.total_cost)} gp</span>
                  </div>
                ))}
                {opportunity.materials_data.length > 3 && (
                  <div className="text-xs text-gray-500">
                    +{opportunity.materials_data.length - 3} more materials...
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* AI Volume Analysis */}
      {hasAIData() && (opportunity as any).volume_analysis && (
        <div className="mb-4">
          <div className="text-sm text-gray-400 mb-2">AI Volume Analysis</div>
          <div className="bg-orange-400/5 border border-orange-400/20 rounded-lg p-3">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <div className="flex items-center gap-1">
                  <ChartBarIcon className="w-3 h-3 text-orange-400" />
                  <span className="text-xs text-gray-400">Product Liquidity:</span>
                </div>
                <div className={`font-medium ${getAIScoreColor((opportunity as any).liquidity_score)}`}>
                  {(((opportunity as any).liquidity_score || 0) * 100).toFixed(0)}%
                </div>
              </div>
              <div>
                <div className="flex items-center gap-1">
                  <SparklesIcon className="w-3 h-3 text-orange-400" />
                  <span className="text-xs text-gray-400">AI Weighting:</span>
                </div>
                <div className={`font-medium ${getAIScoreColor((opportunity as any).ai_volume_score)}`}>
                  {(((opportunity as any).ai_volume_score || 0) * 100).toFixed(0)}%
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Strategy Requirements */}
      <div className="mb-4">
        <div className="text-sm text-gray-400 mb-2">Requirements & Timing</div>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-gray-400">Capital Required:</span>
            <span className="ml-2 font-semibold text-gray-200">
              {formatPrice(opportunity.strategy.min_capital_required)} gp
            </span>
          </div>
          <div>
            <span className="text-gray-400">Craft Time:</span>
            <span className="ml-2 font-semibold text-gray-200">
              {opportunity.crafting_time_seconds}s
            </span>
          </div>
        </div>
      </div>

      {/* AI Insights Section */}
      {hasAIData() && (
        <div className="mb-4">
          <div className="flex items-center gap-2 text-sm text-orange-400 mb-3">
            <SparklesIcon className="w-4 h-4" />
            <span className="font-semibold">AI Enhanced Analysis</span>
          </div>
          
          {/* AI Metrics Grid */}
          <div className="grid grid-cols-2 gap-4 mb-3">
            {(opportunity as any).enhanced_risk_level && (
              <div>
                <div className="text-xs text-gray-400 mb-1">Enhanced Risk</div>
                <div className={`inline-flex px-2 py-1 rounded-full text-xs font-semibold ${getRiskColor((opportunity as any).enhanced_risk_level)}`}>
                  {(opportunity as any).enhanced_risk_level.charAt(0).toUpperCase() + (opportunity as any).enhanced_risk_level.slice(1)}
                </div>
              </div>
            )}
            
            {(opportunity as any).market_confidence !== undefined && (
              <div>
                <div className="text-xs text-gray-400 mb-1">Market Confidence</div>
                <div className={`text-sm font-semibold ${getAIScoreColor((opportunity as any).market_confidence / 100)}`}>
                  {(opportunity as any).market_confidence.toFixed(0)}%
                </div>
              </div>
            )}
          </div>

          {/* Volume Analysis Details */}
          {(opportunity as any).volume_analysis && (
            <div className="bg-orange-400/5 border border-orange-400/20 rounded-lg p-3">
              <div className="flex items-center gap-2 text-xs text-orange-400 mb-2">
                <CogIcon className="w-3 h-3" />
                <span className="font-semibold">Volume Data Quality</span>
              </div>
              <div className="grid grid-cols-3 gap-2 text-xs">
                {(opportunity as any).volume_analysis.product_volume?.trading_activity && (
                  <div>
                    <span className="text-gray-400">Product Activity:</span>
                    <div className="font-medium text-gray-200 capitalize">
                      {(opportunity as any).volume_analysis.product_volume.trading_activity.replace('_', ' ')}
                    </div>
                  </div>
                )}
                {(opportunity as any).volume_analysis.overall_liquidity_score !== undefined && (
                  <div>
                    <span className="text-gray-400">Overall Liquidity:</span>
                    <div className={`font-medium ${getAIScoreColor((opportunity as any).volume_analysis.overall_liquidity_score)}`}>
                      {((opportunity as any).volume_analysis.overall_liquidity_score * 100).toFixed(0)}%
                    </div>
                  </div>
                )}
                {(opportunity as any).volume_analysis.ai_volume_score !== undefined && (
                  <div>
                    <span className="text-gray-400">AI Score:</span>
                    <div className={`font-medium ${getAIScoreColor((opportunity as any).volume_analysis.ai_volume_score)}`}>
                      {((opportunity as any).volume_analysis.ai_volume_score * 100).toFixed(0)}%
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ROI and Performance */}
      <div className="border-t border-gray-700/50 pt-3">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <ArrowTrendingUpIcon className="w-4 h-4 text-green-400" />
            <span className="text-sm text-gray-300">
              ROI: <span className="font-semibold text-green-400">
                {formatPercentage(opportunity.profit_margin_pct)}
              </span>
            </span>
          </div>
          <div className="flex items-center gap-2">
            <ClockIcon className="w-4 h-4 text-blue-400" />
            <span className="text-sm text-gray-300">
              Updated: <span className="font-semibold">
                {new Date().toLocaleDateString()}
              </span>
            </span>
          </div>
        </div>

        {/* AI Data Quality Indicators */}
        {hasAIData() && (
          <div className="flex items-center justify-between text-xs text-gray-400">
            <div className="flex items-center gap-1">
              <ShieldCheckIcon className="w-3 h-3" />
              <span>Real-time OSRS Wiki pricing</span>
            </div>
            {(opportunity as any).ai_volume_score !== undefined && (
              <div className="flex items-center gap-1">
                <StarIcon className="w-3 h-3" />
                <span>AI Volume Score: {(((opportunity as any).ai_volume_score || 0) * 100).toFixed(0)}%</span>
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
    </motion.div>
  );
}

export default CraftingOpportunityCard;