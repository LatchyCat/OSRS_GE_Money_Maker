import React from 'react';
import { motion } from 'framer-motion';
import { ArrowTrendingUpIcon, ArrowTrendingDownIcon, ChartBarIcon } from '@heroicons/react/24/outline';
import type { SeasonalForecast } from '../../types/seasonal';

interface SeasonalForecastCardProps {
  forecast: SeasonalForecast;
  onClick?: () => void;
  className?: string;
}

export function SeasonalForecastCard({ forecast, onClick, className = '' }: SeasonalForecastCardProps) {
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

  const getHorizonColor = (horizon: string) => {
    switch (horizon) {
      case '1d': return 'text-red-400 bg-red-400/10';
      case '3d': return 'text-orange-400 bg-orange-400/10';
      case '7d': return 'text-yellow-400 bg-yellow-400/10';
      case '14d': return 'text-green-400 bg-green-400/10';
      case '30d': return 'text-blue-400 bg-blue-400/10';
      case '60d': return 'text-purple-400 bg-purple-400/10';
      case '90d': return 'text-pink-400 bg-pink-400/10';
      default: return 'text-gray-400 bg-gray-400/10';
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-green-400';
    if (confidence >= 0.6) return 'text-yellow-400';
    if (confidence >= 0.4) return 'text-orange-400';
    return 'text-red-400';
  };

  const getPriceChangeColor = (change: number) => {
    if (change > 0) return 'text-green-400';
    if (change < 0) return 'text-red-400';
    return 'text-gray-400';
  };

  const priceChange = ((forecast.forecasted_price - forecast.base_price) / forecast.base_price) * 100;
  const isPositiveForecast = forecast.forecasted_price > forecast.base_price;
  const confidenceLevel = forecast.confidence_level;

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
            {forecast.item_name}
          </h3>
          <div className="flex items-center gap-2">
            <span className={`px-2 py-1 rounded-full text-xs font-semibold ${getHorizonColor(forecast.horizon)}`}>
              {forecast.horizon.toUpperCase()} FORECAST
            </span>
            <span className="text-xs text-gray-400">
              {formatDate(forecast.target_date)}
            </span>
          </div>
        </div>
        <div className="flex flex-col items-end gap-2">
          {isPositiveForecast ? (
            <ArrowTrendingUpIcon className="w-6 h-6 text-green-400" />
          ) : (
            <ArrowTrendingDownIcon className="w-6 h-6 text-red-400" />
          )}
          {forecast.is_validated && (
            <div className="px-2 py-1 rounded-full text-xs font-semibold text-green-400 bg-green-400/10">
              VALIDATED
            </div>
          )}
        </div>
      </div>

      {/* Price Information */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className="text-center">
          <div className="text-xs text-gray-400 mb-1">Current Price</div>
          <div className="text-lg font-bold text-gray-200">
            {formatPrice(forecast.base_price)} gp
          </div>
        </div>
        <div className="text-center">
          <div className="text-xs text-gray-400 mb-1">Forecasted Price</div>
          <div className={`text-lg font-bold ${getPriceChangeColor(priceChange)}`}>
            {formatPrice(forecast.forecasted_price)} gp
          </div>
        </div>
      </div>

      {/* Price Change */}
      <div className="text-center mb-4">
        <div className="text-xs text-gray-400 mb-1">Expected Change</div>
        <div className={`text-xl font-bold ${getPriceChangeColor(priceChange)}`}>
          {formatPercentage(priceChange)}
        </div>
        <div className="text-xs text-gray-500">
          {isPositiveForecast ? '+' : ''}{formatPrice(forecast.forecasted_price - forecast.base_price)} gp
        </div>
      </div>

      {/* Confidence Level */}
      <div className="mb-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-gray-400">Confidence</span>
          <span className={`text-sm font-semibold ${getConfidenceColor(confidenceLevel)}`}>
            {(confidenceLevel * 100).toFixed(0)}%
          </span>
        </div>
        <div className="flex-1 bg-gray-700 rounded-full h-2">
          <div 
            className={`h-full rounded-full transition-all duration-300 ${
              confidenceLevel >= 0.8 ? 'bg-gradient-to-r from-green-500 to-emerald-500' :
              confidenceLevel >= 0.6 ? 'bg-gradient-to-r from-yellow-500 to-amber-500' :
              confidenceLevel >= 0.4 ? 'bg-gradient-to-r from-orange-500 to-red-500' :
              'bg-gradient-to-r from-red-500 to-red-700'
            }`}
            style={{ width: `${confidenceLevel * 100}%` }}
          />
        </div>
      </div>

      {/* Price Range */}
      <div className="mb-4">
        <div className="text-sm text-gray-400 mb-2">Confidence Interval</div>
        <div className="flex items-center justify-between">
          <div className="text-center">
            <div className="text-xs text-red-400">Lower</div>
            <div className="text-sm font-semibold text-gray-300">
              {formatPrice(forecast.lower_bound)}
            </div>
          </div>
          <div className="flex-1 mx-3">
            <div className="relative bg-gray-700 rounded-full h-3">
              <div 
                className="absolute bg-gradient-to-r from-red-400 via-yellow-400 to-green-400 h-full rounded-full"
                style={{ 
                  left: '0%',
                  width: '100%'
                }}
              />
              <div 
                className="absolute w-1 h-5 bg-blue-400 rounded-full -top-1 border border-gray-800"
                style={{ 
                  left: `${((forecast.forecasted_price - forecast.lower_bound) / (forecast.upper_bound - forecast.lower_bound)) * 100}%`,
                  transform: 'translateX(-50%)'
                }}
              />
            </div>
          </div>
          <div className="text-center">
            <div className="text-xs text-green-400">Upper</div>
            <div className="text-sm font-semibold text-gray-300">
              {formatPrice(forecast.upper_bound)}
            </div>
          </div>
        </div>
      </div>

      {/* Forecast Components */}
      <div className="space-y-2 mb-4">
        <div className="flex justify-between items-center">
          <span className="text-xs text-gray-400">Seasonal Factor</span>
          <span className={`text-xs font-semibold ${getPriceChangeColor((forecast.seasonal_factor - 1) * 100)}`}>
            {formatPercentage((forecast.seasonal_factor - 1) * 100)}
          </span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-xs text-gray-400">Trend Adjustment</span>
          <span className={`text-xs font-semibold ${getPriceChangeColor(forecast.trend_adjustment)}`}>
            {formatPercentage(forecast.trend_adjustment)}
          </span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-xs text-gray-400">Pattern Strength</span>
          <span className="text-xs text-blue-400">
            {(forecast.pattern_strength * 100).toFixed(0)}%
          </span>
        </div>
      </div>

      {/* Pattern Type and Method */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <ChartBarIcon className="w-4 h-4 text-gray-400" />
          <span className="text-xs text-gray-400">Pattern:</span>
          <span className="text-xs font-semibold text-blue-400 capitalize">
            {forecast.primary_pattern_type}
          </span>
        </div>
        <span className="text-xs text-gray-500">
          {forecast.forecast_method}
        </span>
      </div>

      {/* Validation Results */}
      {forecast.is_validated && forecast.actual_price && (
        <div className="border-t border-gray-700/50 pt-3">
          <div className="text-xs text-gray-400 mb-2">Validation Results</div>
          <div className="grid grid-cols-2 gap-4">
            <div className="text-center">
              <div className="text-xs text-gray-400">Actual Price</div>
              <div className="text-sm font-semibold text-green-400">
                {formatPrice(forecast.actual_price)}
              </div>
            </div>
            <div className="text-center">
              <div className="text-xs text-gray-400">Accuracy</div>
              <div className={`text-sm font-semibold ${
                forecast.forecast_accuracy && forecast.forecast_accuracy >= 0.8 ? 'text-green-400' :
                forecast.forecast_accuracy && forecast.forecast_accuracy >= 0.6 ? 'text-yellow-400' :
                'text-red-400'
              }`}>
                {forecast.forecast_accuracy ? (forecast.forecast_accuracy * 100).toFixed(0) + '%' : 'N/A'}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between mt-4 pt-3 border-t border-gray-700/50">
        <div className="text-xs text-gray-500">
          {forecast.days_until_target !== null ? 
            forecast.days_until_target >= 0 ? `${forecast.days_until_target} days remaining` : 'Expired'
            : 'Date passed'
          }
        </div>
        <div className="text-xs text-gray-500">
          ID: {forecast.id}
        </div>
      </div>
    </motion.div>
  );
}

export default SeasonalForecastCard;