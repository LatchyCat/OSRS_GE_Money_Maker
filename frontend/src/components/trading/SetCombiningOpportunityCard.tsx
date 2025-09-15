import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { 
  ArrowTrendingUpIcon,
  ClockIcon,
  CurrencyDollarIcon,
  PuzzlePieceIcon,
  ChartBarIcon,
  SparklesIcon,
  ExclamationTriangleIcon,
  LightBulbIcon,
  CogIcon,
  ShieldCheckIcon,
  StarIcon,
  ArchiveBoxIcon,
  CalculatorIcon
} from '@heroicons/react/24/outline';
import { Shield, TrendingUp, Clock, AlertTriangle, CheckCircle } from 'lucide-react';
import type { SetCombiningOpportunity } from '../../types/tradingStrategies';

interface SetCombiningOpportunityCardProps {
  opportunity: SetCombiningOpportunity;
  onClick?: () => void;
  onOpenCalculator?: () => void;
  className?: string;
}

export function SetCombiningOpportunityCard({ 
  opportunity, 
  onClick,
  onOpenCalculator,
  className = '' 
}: SetCombiningOpportunityCardProps) {
  
  // Debug logging for piece data (minimal but comprehensive)
  React.useEffect(() => {
    if (opportunity.set_name.includes('Guthan') || opportunity.set_name.includes('Dragon') || opportunity.set_name.includes('Dharok')) {
      console.log(`🔍 ${opportunity.set_name} volume debug:`, {
        piece_volumes: opportunity.piece_volumes,
        piece_volumes_type: Array.isArray(opportunity.piece_volumes) ? 'array' : typeof opportunity.piece_volumes,
        piece_ids: opportunity.piece_ids,
        first_volume: opportunity.piece_volumes ? (
          Array.isArray(opportunity.piece_volumes) 
            ? opportunity.piece_volumes[0] 
            : opportunity.piece_volumes[opportunity.piece_ids?.[0]?.toString()]
        ) : 'none'
      });
    }
  }, [opportunity]);
  const formatPrice = (price: number) => {
    if (price >= 1000000) {
      return `${(price / 1000000).toFixed(1)}M`;
    } else if (price >= 1000) {
      return `${(price / 1000).toFixed(1)}K`;
    }
    return price.toLocaleString();
  };

  const formatTime = (hours: number) => {
    if (hours < 1) {
      return `${Math.round(hours * 60)}m ago`;
    } else if (hours < 24) {
      return `${hours.toFixed(1)}h ago`;
    } else {
      return `${(hours / 24).toFixed(1)}d ago`;
    }
  };

  // Get volume confidence indicator
  const getVolumeIndicator = (score: number) => {
    if (score >= 0.7) return { icon: CheckCircle, color: 'text-green-500', label: 'High' };
    if (score >= 0.4) return { icon: Clock, color: 'text-yellow-500', label: 'Med' };
    return { icon: AlertTriangle, color: 'text-red-500', label: 'Low' };
  };

  // Get risk level styling
  const getRiskStyling = (risk: string) => {
    switch (risk) {
      case 'low': return 'bg-green-100 text-green-800 border-green-200';
      case 'medium': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'high': return 'bg-red-100 text-red-800 border-red-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  // Check if this opportunity has real-time OSRS Wiki data
  const hasRealTimeData = opportunity.data_source === 'osrs_wiki_real_time_analysis' || 
                          opportunity.pricing_source?.includes('osrs_wiki') ||
                          opportunity.avg_data_age_hours !== undefined;

  const volumeIndicator = getVolumeIndicator(opportunity.volume_score || 0);
  const VolIcon = volumeIndicator.icon;

  // Helper function for getting piece prices with better error handling
  const getPiecePrice = (prices: number[] | undefined, index: number): string => {
    // Check if prices is a valid array
    if (!prices || !Array.isArray(prices)) {
      // If no piece_prices array, estimate from total cost
      if (opportunity.individual_pieces_total_cost && opportunity.piece_names) {
        const avgPiecePrice = opportunity.individual_pieces_total_cost / opportunity.piece_names.length;
        return formatPrice(avgPiecePrice);
      }
      return 'N/A';
    }
    
    // Check if index is valid
    if (index < 0 || index >= prices.length) {
      return 'N/A';
    }
    
    const price = prices[index];
    
    // Validate the price value
    if (typeof price !== 'number' || price < 0 || isNaN(price)) {
      return 'N/A';
    }
    
    return formatPrice(price);
  };

  // Helper function for getting piece volumes with proper mapping from item IDs
  const getPieceVolume = (
    volumes: { [key: string]: number } | number[] | undefined, 
    piece_ids: number[] | undefined, 
    index: number
  ): string => {
    // If volumes is an array (legacy format), use array index
    if (Array.isArray(volumes)) {
      if (index >= 0 && index < volumes.length && volumes[index] != null) {
        const volume = volumes[index];
        return volume >= 0 ? formatPrice(volume) : 'N/A';
      }
      return 'N/A';
    }
    
    // If volumes is an object (new format with item IDs as keys)
    if (volumes && typeof volumes === 'object' && piece_ids && Array.isArray(piece_ids)) {
      if (index >= 0 && index < piece_ids.length) {
        const item_id = piece_ids[index];
        // Try both string and number keys for robustness
        const volume = volumes[item_id.toString()] ?? volumes[item_id];
        if (volume != null && volume >= 0) {
          return formatPrice(volume);
        }
      }
      return 'N/A';
    }
    
    return 'N/A';
  };

  // Helper function for volume tooltips
  const getVolumeTooltip = (
    volumes: { [key: string]: number } | number[] | undefined,
    piece_ids: number[] | undefined,
    index: number
  ): string => {
    let volume = 0;
    let hasData = false;

    if (Array.isArray(volumes)) {
      if (index >= 0 && index < volumes.length && volumes[index] != null) {
        volume = volumes[index];
        hasData = true;
      }
    } else if (volumes && typeof volumes === 'object' && piece_ids && Array.isArray(piece_ids)) {
      if (index >= 0 && index < piece_ids.length) {
        const item_id = piece_ids[index];
        // Try both string and number keys for robustness
        const vol = volumes[item_id.toString()] ?? volumes[item_id];
        if (vol != null) {
          volume = vol;
          hasData = true;
        }
      }
    }

    if (!hasData) {
      return 'No recent trading volume data available for this item';
    }
    
    if (volume === 0) {
      return 'No trading activity in recent price data';
    }
    
    return `Trading volume: ${formatPrice(volume)} transactions`;
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

  const getVolumeScoreColor = (score?: number) => {
    if (!score) return 'text-gray-400';
    if (score >= 0.8) return 'text-purple-400';
    if (score >= 0.6) return 'text-green-400';
    if (score >= 0.4) return 'text-yellow-400';
    if (score >= 0.2) return 'text-orange-400';
    return 'text-red-400';
  };

  const hasAIData = () => {
    return (opportunity as any).volume_score !== undefined || 
           (opportunity as any).confidence_score !== undefined ||
           (opportunity as any).ai_risk_level !== undefined;
  };

  const getProfitTier = (profit: number) => {
    if (profit >= 50000) return 'legendary';
    if (profit >= 25000) return 'high';
    if (profit >= 10000) return 'medium';
    if (profit >= 5000) return 'low';
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

  const profitTier = getProfitTier(opportunity.lazy_tax_profit);
  const tierConfig = getProfitTierConfig(profitTier);

  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      className={`bg-gray-800/50 backdrop-blur-sm border ${
        hasAIData() ? 'border-indigo-500/30 shadow-indigo-500/5' : 'border-gray-700/50'
      } ${tierConfig.glow} rounded-xl p-6 cursor-pointer transition-all duration-200 hover:border-indigo-500/50 hover:shadow-lg hover:shadow-indigo-500/10 ${className}`}
      onClick={onClick}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2 flex-wrap">
            <Shield className="w-5 h-5 text-indigo-400 flex-shrink-0" />
            <h3 className="text-lg font-semibold text-gray-100 truncate flex-1 min-w-0">
              {opportunity.set_name}
            </h3>
            {hasRealTimeData && (
              <div className="flex items-center gap-1 px-2 py-1 bg-green-500/10 border border-green-500/30 rounded-full">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                <span className="text-xs text-green-400 font-medium">LIVE</span>
              </div>
            )}
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            {/* Profit Tier Badge */}
            <div className={`flex items-center gap-1 px-2 py-0.5 rounded-full border text-xs font-medium ${tierConfig.color} flex-shrink-0`}>
              <span>{tierConfig.icon}</span>
              <span>{tierConfig.label}</span>
            </div>
            
            {/* Volume Indicator */}
            {(opportunity as any).volume_score !== undefined && (
              <div className="flex items-center gap-1 px-2 py-0.5 bg-blue-400/10 border border-blue-400/30 rounded-full flex-shrink-0">
                <VolIcon className={`w-3 h-3 ${volumeIndicator.color}`} />
                <span className="text-xs text-blue-400 font-medium">{volumeIndicator.label} Vol</span>
              </div>
            )}
            
            {hasAIData() && (
              <div className="flex items-center gap-1 px-2 py-0.5 bg-indigo-400/10 border border-indigo-400/30 rounded-full flex-shrink-0">
                <SparklesIcon className="w-3 h-3 text-indigo-400" />
                <span className="text-xs text-indigo-400 font-medium">AI</span>
              </div>
            )}
          </div>
          <div className="flex items-center gap-2">
            <div className="px-3 py-1.5 rounded-full border border-indigo-400/30 bg-indigo-400/10 text-indigo-400 text-sm font-semibold">
              {opportunity.piece_names.length} Piece Set
            </div>
            <div className={`px-2 py-1 rounded-full text-xs font-semibold ${getRiskColor((opportunity as any).ai_risk_level || opportunity.risk_level || opportunity.strategy?.risk_level)}`}>
              {((opportunity as any).ai_risk_level || opportunity.risk_level || opportunity.strategy?.risk_level || 'medium').charAt(0).toUpperCase() + ((opportunity as any).ai_risk_level || opportunity.risk_level || opportunity.strategy?.risk_level || 'medium').slice(1)} Risk
            </div>
          </div>
        </div>
        <div className="flex flex-col items-end gap-2">
          {/* Calculator Button */}
          <button
            onClick={(e) => {
              e.stopPropagation();
              console.log('🧮 Calculator button clicked for:', opportunity.set_name);
              onOpenCalculator?.();
            }}
            className="flex items-center gap-1 px-3 py-1.5 bg-blue-500/10 hover:bg-blue-500/20 border border-blue-500/30 rounded-lg text-blue-400 text-sm font-medium transition-colors"
          >
            <CalculatorIcon className="w-4 h-4" />
            Calculator
          </button>

          {/* Data Freshness */}
          {hasRealTimeData && (opportunity as any).avg_data_age_hours !== undefined && (
            <div className="text-right text-gray-400">
              <div className="text-xs">Updated</div>
              <div className="text-xs font-medium">{formatTime((opportunity as any).avg_data_age_hours)}</div>
            </div>
          )}

          {/* Metrics */}
          {hasAIData() && (opportunity as any).volume_score !== undefined ? (
            <div className="flex items-center gap-2">
              <div className="text-right text-gray-300">
                <div className="text-xs text-gray-400">Confidence</div>
                <div className="text-sm font-bold">
                  {(((opportunity as any).confidence_score || 0) * 100).toFixed(0)}%
                </div>
              </div>
              <div className={`text-right ${getVolumeScoreColor((opportunity as any).volume_score)}`}>
                <div className="flex items-center gap-1 text-xs text-gray-400">
                  <SparklesIcon className="w-3 h-3" />
                  Volume Score
                </div>
                <div className="text-sm font-bold">
                  {(((opportunity as any).volume_score || 0) * 100).toFixed(0)}%
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
            <span>Lazy Tax Profit</span>
          </div>
          <div className={`text-lg font-bold ${
            profitTier === 'legendary' ? 'text-purple-400' :
            profitTier === 'high' ? 'text-emerald-400' :
            profitTier === 'medium' ? 'text-blue-400' :
            profitTier === 'low' ? 'text-yellow-400' : 'text-gray-400'
          }`}>
            {formatPrice(opportunity.lazy_tax_profit)} gp
          </div>
        </div>
        <div className="text-center">
          <div className="text-xs text-gray-400 mb-1">Per Hour Potential</div>
          <div className="text-lg font-bold text-emerald-400">
            {formatPrice((opportunity as any).estimated_sets_per_hour ? 
              opportunity.lazy_tax_profit * (opportunity as any).estimated_sets_per_hour :
              opportunity.lazy_tax_profit * Math.min(12, opportunity.set_volume || 6)
            )} gp/h
          </div>
        </div>
        <div className="text-center">
          <div className="text-xs text-gray-400 mb-1">Set Volume</div>
          <div className="text-lg font-bold text-blue-400">
            {opportunity.set_volume || 0}
          </div>
        </div>
      </div>


      {/* Individual Piece Prices */}
      <div className="mb-4">
        <div className="text-sm text-gray-400 mb-2 flex items-center gap-2">
          <PuzzlePieceIcon className="w-4 h-4" />
          <span>Individual Pieces ({opportunity.piece_names.length} items)</span>
        </div>
        <div className="bg-gray-700/20 rounded-lg p-3">
          <div className="space-y-2">
            {opportunity.piece_names.slice(0, 4).map((piece, index) => (
              <div key={index} className="flex items-center justify-between text-xs">
                <span className="text-gray-300 truncate flex-1 min-w-0 mr-2" title={piece}>
                  {piece}
                </span>
                <div className="flex items-center gap-3 flex-shrink-0">
                  <span className="text-emerald-400 font-medium">
                    {getPiecePrice(opportunity.piece_prices, index)} gp
                  </span>
                  <span className="text-gray-400 text-xs" title={getVolumeTooltip(opportunity.piece_volumes, opportunity.piece_ids, index)}>
                    Vol: {getPieceVolume(opportunity.piece_volumes, opportunity.piece_ids, index)}
                  </span>
                </div>
              </div>
            ))}
            {opportunity.piece_names.length > 4 && (
              <div className="text-xs text-gray-500 text-center pt-1">
                +{opportunity.piece_names.length - 4} more pieces... (click to view all)
              </div>
            )}
            
            {/* Strategy & Profit Calculation */}
            <div className="mt-3 pt-2 border-t border-gray-600/30">
              <div className="bg-green-400/10 border border-green-400/20 rounded p-2 mb-2">
                <div className="text-xs font-medium text-green-400 mb-1 flex items-center gap-1">
                  💰 <span>Profitable Strategy:</span>
                </div>
                <div className="text-xs text-gray-300">
                  Buy complete set → Sell individual pieces
                </div>
              </div>
              
              <div className="flex items-center justify-between text-xs font-medium">
                <span className="text-gray-300">📦 Buy Complete Set:</span>
                <span className="text-blue-400">{formatPrice(opportunity.complete_set_price)} gp</span>
              </div>
              <div className="flex items-center justify-between text-xs font-medium mt-1">
                <span className="text-gray-300">💎 Sell Pieces Total:</span>
                <span className="text-emerald-400">{formatPrice(opportunity.individual_pieces_total_cost)} gp</span>
              </div>
              <div className="flex items-center justify-between text-xs font-semibold mt-1 pt-1 border-t border-gray-600/30">
                <span className="text-gray-200">✨ Your Profit:</span>
                <span className="text-green-400">+{formatPrice(opportunity.lazy_tax_profit)} gp</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* AI Analysis */}
      {hasAIData() && (
        <div className="mb-4">
          <div className="text-sm text-gray-400 mb-2 flex items-center gap-2">
            <SparklesIcon className="w-4 h-4 text-indigo-400" />
            <span>AI Analysis</span>
          </div>
          <div className="bg-indigo-400/5 border border-indigo-400/20 rounded-lg p-3">
            <div className="grid grid-cols-3 gap-3 text-xs">
              <div className="text-center">
                <div className="text-gray-400 mb-1">Volume</div>
                <div className={`font-medium ${getVolumeScoreColor((opportunity as any).volume_score)}`}>
                  {(((opportunity as any).volume_score || 0) * 100).toFixed(0)}%
                </div>
              </div>
              <div className="text-center">
                <div className="text-gray-400 mb-1">Confidence</div>
                <div className={`font-medium ${getVolumeScoreColor((opportunity as any).confidence_score)}`}>
                  {(((opportunity as any).confidence_score || 0) * 100).toFixed(0)}%
                </div>
              </div>
              <div className="text-center">
                <div className="text-gray-400 mb-1">Data Age</div>
                <div className={`font-medium ${
                  (opportunity as any).avg_data_age_hours < 2 ? 'text-green-400' :
                  (opportunity as any).avg_data_age_hours < 12 ? 'text-yellow-400' : 'text-red-400'
                }`}>
                  {(opportunity as any).avg_data_age_hours ? 
                    `${(opportunity as any).avg_data_age_hours.toFixed(1)}h` : 'N/A'}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Strategy Requirements */}
      <div className="mb-4">
        <div className="text-sm text-gray-400 mb-2">Requirements & ROI</div>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-gray-400">Capital Required:</span>
            <span className="ml-2 font-semibold text-gray-200">
              {formatPrice(opportunity.capital_required || opportunity.individual_pieces_total_cost)} gp
            </span>
          </div>
          <div>
            <span className="text-gray-400">ROI per Set:</span>
            <span className="ml-2 font-semibold text-green-400">
              {(opportunity as any).roi_per_set ? 
                formatPercentage((opportunity as any).roi_per_set) :
                formatPercentage(opportunity.profit_margin_pct)
              }
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
                {formatPercentage(opportunity.profit_margin_pct)}
              </span>
            </span>
          </div>
          <div className="flex items-center gap-2">
            <ArchiveBoxIcon className="w-4 h-4 text-blue-400" />
            <span className="text-sm text-gray-300">
              Set ID: <span className="font-semibold">
                {opportunity.set_item_id}
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
            {(opportunity as any).volume_score !== undefined && (
              <div className="flex items-center gap-1">
                <StarIcon className="w-3 h-3" />
                <span>Volume Score: {(((opportunity as any).volume_score || 0) * 100).toFixed(0)}%</span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Activity Status */}
      {!(opportunity.strategy?.is_active ?? true) && (
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

export default SetCombiningOpportunityCard;