import React from 'react';
import { motion } from 'framer-motion';
import { 
  TrendingUp, 
  Shield, 
  Clock, 
  DollarSign,
  Package,
  BarChart3,
  Star,
  AlertCircle,
  CheckCircle,
  ArrowRight
} from 'lucide-react';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import type { Strategy } from '../../types';

interface StrategyCardProps {
  strategy: Strategy;
  onClick?: () => void;
  onViewDetails?: () => void;
  isRecommended?: boolean;
  showActions?: boolean;
}

export const StrategyCard: React.FC<StrategyCardProps> = ({ 
  strategy,
  onClick,
  onViewDetails,
  isRecommended = false,
  showActions = true
}) => {
  const formatGP = (amount: number) => {
    if (amount >= 1000000000) {
      return `${(amount / 1000000000).toFixed(1)}B GP`;
    } else if (amount >= 1000000) {
      return `${(amount / 1000000).toFixed(1)}M GP`;
    } else if (amount >= 1000) {
      return `${(amount / 1000).toFixed(1)}K GP`;
    }
    return `${amount.toLocaleString()} GP`;
  };

  const getRiskColor = (risk: string) => {
    switch (risk) {
      case 'conservative': return 'text-green-400';
      case 'moderate': return 'text-yellow-400';
      case 'aggressive': return 'text-red-400';
      default: return 'text-gray-400';
    }
  };

  const getFeasibilityColor = (score: number) => {
    if (score >= 0.8) return 'text-green-400';
    if (score >= 0.6) return 'text-yellow-400';
    if (score >= 0.4) return 'text-orange-400';
    return 'text-red-400';
  };

  const getFeasibilityIcon = (score: number) => {
    if (score >= 0.7) return <CheckCircle className="w-4 h-4 text-green-400" />;
    if (score >= 0.4) return <AlertCircle className="w-4 h-4 text-yellow-400" />;
    return <AlertCircle className="w-4 h-4 text-red-400" />;
  };

  const getROIColor = (roi: number) => {
    if (roi >= 50) return 'text-green-400';
    if (roi >= 25) return 'text-blue-400';
    if (roi >= 10) return 'text-yellow-400';
    return 'text-orange-400';
  };

  const getTimelineColor = (days: number) => {
    if (days <= 7) return 'text-green-400';
    if (days <= 30) return 'text-blue-400';
    if (days <= 90) return 'text-yellow-400';
    return 'text-orange-400';
  };

  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      className="h-full"
    >
      <Card 
        className={`p-6 space-y-4 cursor-pointer hover:border-accent-500/50 transition-all h-full flex flex-col ${
          (isRecommended || strategy.is_recommended) ? 'ring-2 ring-yellow-500/50 bg-yellow-500/5' : ''
        }`}
        onClick={onClick}
      >
        {/* Header */}
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-3 flex-1">
            <div className="p-2 bg-accent-500/20 rounded-lg flex-shrink-0">
              <TrendingUp className="w-5 h-5 text-accent-400" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2 mb-1">
                <h3 className="text-lg font-semibold text-white truncate">
                  {strategy.name}
                </h3>
                {(isRecommended || strategy.is_recommended) && (
                  <Star className="w-4 h-4 text-yellow-400 fill-current flex-shrink-0" />
                )}
              </div>
              <p className="text-sm text-gray-400 mb-2">
                {strategy.strategy_type}
              </p>
              <div className="flex items-center gap-2">
                <Badge variant={strategy.is_active ? 'success' : 'secondary'} size="sm">
                  {strategy.is_active ? 'Active' : 'Available'}
                </Badge>
                {(isRecommended || strategy.is_recommended) && (
                  <Badge variant="warning" size="sm">
                    Recommended
                  </Badge>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Key Metrics Grid */}
        <div className="grid grid-cols-2 gap-3">
          {/* ROI */}
          <div className="bg-gradient-to-br from-green-500/10 to-green-600/5 border border-green-500/20 rounded-lg p-3">
            <div className="flex items-center gap-2 mb-1">
              <TrendingUp className="w-4 h-4 text-green-400" />
              <span className="text-xs text-gray-400 uppercase tracking-wider">ROI</span>
            </div>
            <div className={`text-xl font-bold ${getROIColor(strategy.roi_percentage)}`}>
              {strategy.roi_percentage.toFixed(1)}%
            </div>
          </div>

          {/* Profit */}
          <div className="bg-gradient-to-br from-blue-500/10 to-blue-600/5 border border-blue-500/20 rounded-lg p-3">
            <div className="flex items-center gap-2 mb-1">
              <DollarSign className="w-4 h-4 text-blue-400" />
              <span className="text-xs text-gray-400 uppercase tracking-wider">Profit</span>
            </div>
            <div className="text-lg font-bold text-blue-400 truncate">
              {formatGP(strategy.estimated_profit)}
            </div>
          </div>
        </div>

        {/* Details Grid */}
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div className="flex items-center justify-between">
            <span className="text-gray-400 flex items-center gap-1">
              <Shield className="w-3 h-3" />
              Risk
            </span>
            <span className={`font-medium ${getRiskColor(strategy.risk_level)}`}>
              {strategy.risk_level}
            </span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-gray-400 flex items-center gap-1">
              <Clock className="w-3 h-3" />
              Time
            </span>
            <span className={`font-medium ${getTimelineColor(strategy.estimated_days)}`}>
              {strategy.estimated_days}d
            </span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-gray-400 flex items-center gap-1">
              <DollarSign className="w-3 h-3" />
              Investment
            </span>
            <span className="text-purple-400 font-medium truncate">
              {formatGP(strategy.required_initial_investment)}
            </span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-gray-400 flex items-center gap-1">
              <BarChart3 className="w-3 h-3" />
              Feasible
            </span>
            <div className="flex items-center gap-1">
              <span className={`font-medium ${getFeasibilityColor(strategy.feasibility_score)}`}>
                {(strategy.feasibility_score * 100).toFixed(0)}%
              </span>
              {getFeasibilityIcon(strategy.feasibility_score)}
            </div>
          </div>
        </div>

        {/* Items Preview */}
        {strategy.items && strategy.items.length > 0 && (
          <div className="bg-white/5 rounded-lg p-3">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Package className="w-4 h-4 text-accent-400" />
                <span className="text-sm font-semibold text-white">
                  Items ({strategy.items.length})
                </span>
              </div>
              {strategy.items.length > 3 && (
                <span className="text-xs text-gray-400">
                  +{strategy.items.length - 3} more
                </span>
              )}
            </div>
            <div className="space-y-1">
              {strategy.items.slice(0, 3).map((item, i) => (
                <div key={i} className="flex items-center justify-between text-xs">
                  <span className="text-gray-300 truncate pr-2">
                    {item.item?.name || `Item ${item.item_id}`}
                  </span>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <span className="text-accent-400 font-medium">
                      {item.units_to_buy}x
                    </span>
                    <span className="text-green-400 font-medium">
                      {formatGP(item.total_profit)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Description */}
        {strategy.description && (
          <div className="bg-white/5 rounded-lg p-3">
            <p className="text-sm text-gray-300 line-clamp-2">
              {strategy.description}
            </p>
          </div>
        )}

        {/* Actions */}
        {showActions && (
          <div className="mt-auto pt-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={(e) => {
                e.stopPropagation();
                onViewDetails?.();
              }}
              icon={<ArrowRight className="w-4 h-4" />}
              className="w-full"
            >
              View Strategy Details
            </Button>
          </div>
        )}

        {/* Performance Indicator */}
        <div className="flex items-center justify-center pt-2 border-t border-white/10">
          <div className="flex items-center gap-4 text-xs">
            <div className="flex items-center gap-1">
              <div className={`w-2 h-2 rounded-full ${
                strategy.roi_percentage >= 30 ? 'bg-green-400' :
                strategy.roi_percentage >= 15 ? 'bg-yellow-400' : 'bg-red-400'
              }`} />
              <span className="text-gray-400">
                {strategy.roi_percentage >= 30 ? 'High Return' :
                 strategy.roi_percentage >= 15 ? 'Good Return' : 'Low Return'}
              </span>
            </div>
            <div className="flex items-center gap-1">
              <div className={`w-2 h-2 rounded-full ${
                strategy.feasibility_score >= 0.7 ? 'bg-green-400' :
                strategy.feasibility_score >= 0.4 ? 'bg-yellow-400' : 'bg-red-400'
              }`} />
              <span className="text-gray-400">
                {strategy.feasibility_score >= 0.7 ? 'High Confidence' :
                 strategy.feasibility_score >= 0.4 ? 'Medium Risk' : 'High Risk'}
              </span>
            </div>
          </div>
        </div>
      </Card>
    </motion.div>
  );
};