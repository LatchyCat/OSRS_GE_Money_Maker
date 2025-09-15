import React from 'react';
import { motion } from 'framer-motion';
import type { SeasonalPattern } from '../../types/seasonal';

interface SeasonalPatternCardProps {
  pattern: SeasonalPattern;
  onClick?: () => void;
  className?: string;
}

export function SeasonalPatternCard({ pattern, onClick, className = '' }: SeasonalPatternCardProps) {
  const getPatternTypeColor = (type: string) => {
    switch (type) {
      case 'weekly': return 'text-blue-400';
      case 'monthly': return 'text-green-400';
      case 'yearly': return 'text-purple-400';
      case 'event': return 'text-orange-400';
      default: return 'text-gray-400';
    }
  };

  const getSignalQualityColor = (quality: string) => {
    switch (quality) {
      case 'excellent': return 'text-green-400 bg-green-400/10';
      case 'good': return 'text-blue-400 bg-blue-400/10';
      case 'fair': return 'text-yellow-400 bg-yellow-400/10';
      case 'poor': return 'text-red-400 bg-red-400/10';
      default: return 'text-gray-400 bg-gray-400/10';
    }
  };

  const formatPercentage = (value: number) => {
    return `${(value * 100).toFixed(1)}%`;
  };

  const formatPrice = (price: number) => {
    return price.toLocaleString();
  };

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
          <h3 className="text-xl font-semibold text-gray-100 mb-1">
            {pattern.item.name}
          </h3>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-lg font-bold text-green-400">
              {formatPrice(pattern.item.current_price)} gp
            </span>
            <span className="text-sm text-gray-400">
              • {formatPercentage(pattern.item.profit_margin)} margin
            </span>
          </div>
        </div>
        <div className="flex flex-col items-end gap-2">
          <div className={`px-3 py-1 rounded-full text-xs font-semibold ${getSignalQualityColor(pattern.signal_quality)}`}>
            {pattern.signal_quality.toUpperCase()}
          </div>
          {pattern.is_high_conviction && (
            <div className="px-2 py-1 rounded-full text-xs font-semibold text-yellow-400 bg-yellow-400/10">
              HIGH CONVICTION
            </div>
          )}
        </div>
      </div>

      {/* Pattern Strength Indicators */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div>
          <div className="text-sm text-gray-400 mb-1">Overall Strength</div>
          <div className="flex items-center gap-2">
            <div className="flex-1 bg-gray-700 rounded-full h-2">
              <div 
                className="bg-gradient-to-r from-blue-500 to-green-500 h-full rounded-full transition-all duration-300"
                style={{ width: `${pattern.overall_pattern_strength * 100}%` }}
              />
            </div>
            <span className="text-sm font-semibold text-gray-200">
              {formatPercentage(pattern.overall_pattern_strength)}
            </span>
          </div>
        </div>
        
        <div>
          <div className="text-sm text-gray-400 mb-1">Forecast Confidence</div>
          <div className="flex items-center gap-2">
            <div className="flex-1 bg-gray-700 rounded-full h-2">
              <div 
                className="bg-gradient-to-r from-purple-500 to-pink-500 h-full rounded-full transition-all duration-300"
                style={{ width: `${pattern.forecast_confidence * 100}%` }}
              />
            </div>
            <span className="text-sm font-semibold text-gray-200">
              {formatPercentage(pattern.forecast_confidence)}
            </span>
          </div>
        </div>
      </div>

      {/* Dominant Pattern */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-400">Dominant Pattern:</span>
          <span className={`text-sm font-semibold capitalize ${getPatternTypeColor(pattern.dominant_pattern_type)}`}>
            {pattern.dominant_pattern_type}
          </span>
        </div>
        
        {pattern.has_significant_weekend_effect && (
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-full bg-orange-400"></div>
            <span className="text-xs text-orange-400">Weekend Effect</span>
          </div>
        )}
      </div>

      {/* Best/Worst Timing */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className="text-center">
          <div className="text-xs text-gray-400 mb-1">Best Day</div>
          <div className="text-sm font-semibold text-green-400">
            {pattern.best_day_of_week}
          </div>
        </div>
        <div className="text-center">
          <div className="text-xs text-gray-400 mb-1">Best Month</div>
          <div className="text-sm font-semibold text-green-400">
            {pattern.best_month}
          </div>
        </div>
      </div>

      {/* Pattern Breakdown */}
      <div className="space-y-2 mb-4">
        <div className="flex justify-between items-center">
          <span className="text-xs text-gray-400">Weekly</span>
          <span className="text-xs text-blue-400">
            {formatPercentage(pattern.weekly_pattern_strength)}
          </span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-xs text-gray-400">Monthly</span>
          <span className="text-xs text-green-400">
            {formatPercentage(pattern.monthly_pattern_strength)}
          </span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-xs text-gray-400">Yearly</span>
          <span className="text-xs text-purple-400">
            {formatPercentage(pattern.yearly_pattern_strength)}
          </span>
        </div>
        {pattern.event_pattern_strength > 0 && (
          <div className="flex justify-between items-center">
            <span className="text-xs text-gray-400">Events</span>
            <span className="text-xs text-orange-400">
              {formatPercentage(pattern.event_pattern_strength)}
            </span>
          </div>
        )}
      </div>

      {/* Recommendations Preview */}
      {pattern.recommendations.length > 0 && (
        <div className="border-t border-gray-700/50 pt-3">
          <div className="text-xs text-gray-400 mb-2">Top Recommendations</div>
          <div className="space-y-1">
            {pattern.recommendations.slice(0, 2).map((rec, index) => (
              <div key={index} className="text-xs text-gray-300 truncate">
                • {rec}
              </div>
            ))}
            {pattern.recommendations.length > 2 && (
              <div className="text-xs text-blue-400">
                +{pattern.recommendations.length - 2} more...
              </div>
            )}
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between mt-4 pt-3 border-t border-gray-700/50">
        <div className="text-xs text-gray-500">
          {pattern.data_points_analyzed} data points
        </div>
        <div className="text-xs text-gray-500">
          {Math.round(pattern.analysis_duration_seconds * 100) / 100}s analysis
        </div>
      </div>
    </motion.div>
  );
}

export default SeasonalPatternCard;