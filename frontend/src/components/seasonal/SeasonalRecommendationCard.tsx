import React from 'react';
import { motion } from 'framer-motion';
import { 
  ArrowUpIcon, 
  ArrowDownIcon, 
  EyeIcon, 
  ExclamationTriangleIcon,
  PauseIcon,
  ClockIcon,
  CheckCircleIcon 
} from '@heroicons/react/24/outline';
import type { SeasonalRecommendation } from '../../types/seasonal';

interface SeasonalRecommendationCardProps {
  recommendation: SeasonalRecommendation;
  onClick?: () => void;
  className?: string;
}

export function SeasonalRecommendationCard({ recommendation, onClick, className = '' }: SeasonalRecommendationCardProps) {
  const formatPrice = (price: number) => {
    return price.toLocaleString();
  };

  const formatPercentage = (value: number) => {
    return `${value > 0 ? '+' : ''}${value.toFixed(1)}%`;
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffTime = date.getTime() - now.getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Tomorrow';
    if (diffDays > 0) return `${diffDays} days`;
    if (diffDays === -1) return 'Yesterday';
    return `${Math.abs(diffDays)} days ago`;
  };

  const getRecommendationIcon = (type: string) => {
    switch (type) {
      case 'buy': return <ArrowUpIcon className="w-5 h-5" />;
      case 'sell': return <ArrowDownIcon className="w-5 h-5" />;
      case 'hold': return <PauseIcon className="w-5 h-5" />;
      case 'avoid': return <ExclamationTriangleIcon className="w-5 h-5" />;
      case 'monitor': return <EyeIcon className="w-5 h-5" />;
      default: return <ClockIcon className="w-5 h-5" />;
    }
  };

  const getRecommendationColor = (type: string) => {
    switch (type) {
      case 'buy': return 'text-green-400 bg-green-400/10 border-green-400/30';
      case 'sell': return 'text-red-400 bg-red-400/10 border-red-400/30';
      case 'hold': return 'text-blue-400 bg-blue-400/10 border-blue-400/30';
      case 'avoid': return 'text-orange-400 bg-orange-400/10 border-orange-400/30';
      case 'monitor': return 'text-yellow-400 bg-yellow-400/10 border-yellow-400/30';
      default: return 'text-gray-400 bg-gray-400/10 border-gray-400/30';
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-green-400';
    if (confidence >= 0.6) return 'text-yellow-400';
    if (confidence >= 0.4) return 'text-orange-400';
    return 'text-red-400';
  };

  const getPerformanceColor = (performance: number) => {
    if (performance > 2) return 'text-green-400';
    if (performance > 0) return 'text-green-300';
    if (performance === 0) return 'text-gray-400';
    if (performance > -2) return 'text-red-300';
    return 'text-red-400';
  };

  const confidenceScore = recommendation.confidence_score;
  const isExpired = new Date(recommendation.valid_until) < new Date();
  const daysRemaining = recommendation.days_remaining;

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
          <h3 className="text-lg font-semibold text-gray-100 mb-1">
            {recommendation.item_name}
          </h3>
          <div className="flex items-center gap-2">
            <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full border ${getRecommendationColor(recommendation.recommendation_type)}`}>
              {getRecommendationIcon(recommendation.recommendation_type)}
              <span className="text-sm font-semibold uppercase">
                {recommendation.recommendation_type}
              </span>
            </div>
            {recommendation.is_high_confidence && (
              <div className="px-2 py-1 rounded-full text-xs font-semibold text-yellow-400 bg-yellow-400/10">
                HIGH CONFIDENCE
              </div>
            )}
          </div>
        </div>
        <div className="flex flex-col items-end gap-2">
          {recommendation.is_executed && (
            <CheckCircleIcon className="w-6 h-6 text-green-400" />
          )}
          {isExpired && (
            <div className="px-2 py-1 rounded-full text-xs font-semibold text-red-400 bg-red-400/10">
              EXPIRED
            </div>
          )}
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-3 gap-4 mb-4">
        <div className="text-center">
          <div className="text-xs text-gray-400 mb-1">Confidence</div>
          <div className={`text-lg font-bold ${getConfidenceColor(confidenceScore)}`}>
            {(confidenceScore * 100).toFixed(0)}%
          </div>
        </div>
        <div className="text-center">
          <div className="text-xs text-gray-400 mb-1">Expected Impact</div>
          <div className={`text-lg font-bold ${getPerformanceColor(recommendation.expected_impact_pct)}`}>
            {formatPercentage(recommendation.expected_impact_pct)}
          </div>
        </div>
        <div className="text-center">
          <div className="text-xs text-gray-400 mb-1">Position Size</div>
          <div className="text-lg font-bold text-blue-400">
            {recommendation.suggested_position_size_pct.toFixed(0)}%
          </div>
        </div>
      </div>

      {/* Confidence Bar */}
      <div className="mb-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-gray-400">Confidence Level</span>
          <span className={`text-sm font-semibold ${getConfidenceColor(confidenceScore)}`}>
            {(confidenceScore * 100).toFixed(0)}%
          </span>
        </div>
        <div className="flex-1 bg-gray-700 rounded-full h-2">
          <div 
            className={`h-full rounded-full transition-all duration-300 ${
              confidenceScore >= 0.8 ? 'bg-gradient-to-r from-green-500 to-emerald-500' :
              confidenceScore >= 0.6 ? 'bg-gradient-to-r from-yellow-500 to-amber-500' :
              confidenceScore >= 0.4 ? 'bg-gradient-to-r from-orange-500 to-red-500' :
              'bg-gradient-to-r from-red-500 to-red-700'
            }`}
            style={{ width: `${confidenceScore * 100}%` }}
          />
        </div>
      </div>

      {/* Performance Tracking */}
      {(recommendation.current_performance_pct !== 0 || recommendation.is_executed) && (
        <div className="mb-4">
          <div className="text-sm text-gray-400 mb-2">Performance Tracking</div>
          <div className="grid grid-cols-3 gap-2 text-center">
            <div>
              <div className="text-xs text-gray-500">Current</div>
              <div className={`text-sm font-semibold ${getPerformanceColor(recommendation.current_performance_pct)}`}>
                {formatPercentage(recommendation.current_performance_pct)}
              </div>
            </div>
            <div>
              <div className="text-xs text-gray-500">Best</div>
              <div className={`text-sm font-semibold ${getPerformanceColor(recommendation.max_performance_pct)}`}>
                {formatPercentage(recommendation.max_performance_pct)}
              </div>
            </div>
            <div>
              <div className="text-xs text-gray-500">Worst</div>
              <div className={`text-sm font-semibold ${getPerformanceColor(recommendation.min_performance_pct)}`}>
                {formatPercentage(recommendation.min_performance_pct)}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Risk Management */}
      {(recommendation.stop_loss_pct || recommendation.take_profit_pct) && (
        <div className="mb-4">
          <div className="text-sm text-gray-400 mb-2">Risk Management</div>
          <div className="grid grid-cols-2 gap-4">
            {recommendation.stop_loss_pct && (
              <div className="text-center">
                <div className="text-xs text-red-400">Stop Loss</div>
                <div className="text-sm font-semibold text-red-400">
                  {formatPercentage(recommendation.stop_loss_pct)}
                </div>
              </div>
            )}
            {recommendation.take_profit_pct && (
              <div className="text-center">
                <div className="text-xs text-green-400">Take Profit</div>
                <div className="text-sm font-semibold text-green-400">
                  {formatPercentage(recommendation.take_profit_pct)}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Primary Pattern */}
      <div className="mb-4">
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-400">Primary Pattern:</span>
          <span className="text-sm font-semibold text-blue-400 capitalize">
            {recommendation.primary_pattern}
          </span>
        </div>
      </div>

      {/* Recommendation Text */}
      <div className="mb-4">
        <div className="text-sm text-gray-300 leading-relaxed">
          {recommendation.recommendation_text}
        </div>
      </div>

      {/* Supporting Factors */}
      {recommendation.supporting_factors.length > 0 && (
        <div className="mb-4">
          <div className="text-sm text-gray-400 mb-2">Supporting Factors</div>
          <div className="space-y-1">
            {recommendation.supporting_factors.slice(0, 3).map((factor, index) => (
              <div key={index} className="text-xs text-gray-300 flex items-start gap-2">
                <div className="w-1 h-1 rounded-full bg-blue-400 mt-1.5 flex-shrink-0"></div>
                <span>{factor}</span>
              </div>
            ))}
            {recommendation.supporting_factors.length > 3 && (
              <div className="text-xs text-blue-400">
                +{recommendation.supporting_factors.length - 3} more factors...
              </div>
            )}
          </div>
        </div>
      )}

      {/* Execution Info */}
      {recommendation.is_executed && recommendation.execution_price && (
        <div className="mb-4 border-t border-gray-700/50 pt-3">
          <div className="text-sm text-gray-400 mb-2">Execution Details</div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="text-xs text-gray-400">Execution Price</div>
              <div className="text-sm font-semibold text-green-400">
                {formatPrice(recommendation.execution_price)} gp
              </div>
            </div>
            {recommendation.final_performance_pct !== undefined && (
              <div>
                <div className="text-xs text-gray-400">Final Performance</div>
                <div className={`text-sm font-semibold ${getPerformanceColor(recommendation.final_performance_pct)}`}>
                  {formatPercentage(recommendation.final_performance_pct)}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between mt-4 pt-3 border-t border-gray-700/50">
        <div className="text-xs text-gray-500">
          {daysRemaining > 0 ? `${daysRemaining} days remaining` : 
           daysRemaining === 0 ? 'Expires today' : 
           'Expired'}
        </div>
        <div className="text-xs text-gray-500">
          Max hold: {recommendation.max_hold_days} days
        </div>
      </div>

      {/* Time Range */}
      {recommendation.target_date && (
        <div className="mt-2 pt-2 border-t border-gray-700/50">
          <div className="text-xs text-gray-500 text-center">
            Target: {formatDate(recommendation.target_date)}
          </div>
        </div>
      )}
    </motion.div>
  );
}

export default SeasonalRecommendationCard;