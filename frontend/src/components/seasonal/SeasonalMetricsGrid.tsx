import React from 'react';
import { motion } from 'framer-motion';
import { 
  ChartBarIcon,
  ClockIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  CalendarDaysIcon,
  ArrowPathIcon
} from '@heroicons/react/24/outline';
import type { MarketOverview, SeasonalAnalytics, ForecastAccuracyStats } from '../../types/seasonal';

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ComponentType<{ className?: string }>;
  color: 'blue' | 'green' | 'red' | 'yellow' | 'purple' | 'orange' | 'gray';
  trend?: {
    value: number;
    label: string;
    isPositive: boolean;
  };
  className?: string;
}

function MetricCard({ title, value, subtitle, icon: Icon, color, trend, className = '' }: MetricCardProps) {
  const colorClasses = {
    blue: 'text-blue-400 bg-blue-400/10 border-blue-400/20',
    green: 'text-green-400 bg-green-400/10 border-green-400/20',
    red: 'text-red-400 bg-red-400/10 border-red-400/20',
    yellow: 'text-yellow-400 bg-yellow-400/10 border-yellow-400/20',
    purple: 'text-purple-400 bg-purple-400/10 border-purple-400/20',
    orange: 'text-orange-400 bg-orange-400/10 border-orange-400/20',
    gray: 'text-gray-400 bg-gray-400/10 border-gray-400/20'
  };

  const iconColorClasses = {
    blue: 'text-blue-400',
    green: 'text-green-400',
    red: 'text-red-400',
    yellow: 'text-yellow-400',
    purple: 'text-purple-400',
    orange: 'text-orange-400',
    gray: 'text-gray-400'
  };

  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      className={`bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6 transition-all duration-200 ${className}`}
    >
      <div className="flex items-center justify-between mb-3">
        <div className={`p-3 rounded-full ${colorClasses[color]}`}>
          <Icon className="w-6 h-6" />
        </div>
        {trend && (
          <div className={`flex items-center gap-1 text-sm ${trend.isPositive ? 'text-green-400' : 'text-red-400'}`}>
            {trend.isPositive ? (
              <ArrowTrendingUpIcon className="w-4 h-4" />
            ) : (
              <ArrowTrendingDownIcon className="w-4 h-4" />
            )}
            <span>{trend.value > 0 ? '+' : ''}{trend.value}%</span>
          </div>
        )}
      </div>
      
      <div className="space-y-1">
        <h3 className="text-sm font-medium text-gray-400">{title}</h3>
        <div className={`text-2xl font-bold ${iconColorClasses[color]}`}>
          {typeof value === 'number' ? value.toLocaleString() : value}
        </div>
        {subtitle && (
          <p className="text-xs text-gray-500">{subtitle}</p>
        )}
        {trend && (
          <p className="text-xs text-gray-500">{trend.label}</p>
        )}
      </div>
    </motion.div>
  );
}

interface SeasonalMetricsGridProps {
  marketOverview?: MarketOverview | null;
  seasonalAnalytics?: SeasonalAnalytics | null;
  forecastAccuracy?: ForecastAccuracyStats | null;
  className?: string;
}

export function SeasonalMetricsGrid({ 
  marketOverview, 
  seasonalAnalytics, 
  forecastAccuracy,
  className = '' 
}: SeasonalMetricsGridProps) {
  
  const formatNumber = (num: number) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
  };

  const formatPercentage = (value: number) => {
    return `${(value * 100).toFixed(1)}%`;
  };

  const getSentimentColor = (sentiment: string): 'green' | 'red' | 'gray' => {
    switch (sentiment) {
      case 'positive': return 'green';
      case 'negative': return 'red';
      default: return 'gray';
    }
  };

  const getSentimentIcon = (sentiment: string) => {
    switch (sentiment) {
      case 'positive': return ArrowTrendingUpIcon;
      case 'negative': return ArrowTrendingDownIcon;
      default: return ChartBarIcon;
    }
  };

  return (
    <div className={`grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 ${className}`}>
      {/* Market Overview Metrics */}
      {marketOverview && (
        <>
          <MetricCard
            title="Items Analyzed"
            value={formatNumber(marketOverview.total_items_analyzed)}
            subtitle="Total market coverage"
            icon={ChartBarIcon}
            color="blue"
            trend={{
              value: marketOverview.recent_analyses ? 
                ((marketOverview.recent_analyses / marketOverview.total_items_analyzed) * 100) : 0,
              label: "Recent analysis growth",
              isPositive: true
            }}
          />

          <MetricCard
            title="Strong Patterns"
            value={marketOverview.strong_patterns_count}
            subtitle="High-confidence patterns"
            icon={CheckCircleIcon}
            color="green"
            trend={{
              value: marketOverview.strong_patterns_count > 0 ? 
                ((marketOverview.strong_patterns_count / marketOverview.total_items_analyzed) * 100) : 0,
              label: "Pattern success rate",
              isPositive: true
            }}
          />

          <MetricCard
            title="Active Recommendations"
            value={marketOverview.active_recommendations}
            subtitle="Current trading signals"
            icon={ExclamationTriangleIcon}
            color="yellow"
          />

          <MetricCard
            title="Upcoming Events"
            value={marketOverview.upcoming_events}
            subtitle="Scheduled market events"
            icon={CalendarDaysIcon}
            color="purple"
          />

          <MetricCard
            title="Forecast Accuracy"
            value={formatPercentage(marketOverview.forecast_accuracy)}
            subtitle="Prediction success rate"
            icon={ArrowPathIcon}
            color="green"
            trend={{
              value: (marketOverview.forecast_accuracy - 0.7) * 100,
              label: "vs. 70% baseline",
              isPositive: marketOverview.forecast_accuracy > 0.7
            }}
          />

          <MetricCard
            title="Market Sentiment"
            value={marketOverview.market_sentiment.charAt(0).toUpperCase() + marketOverview.market_sentiment.slice(1)}
            subtitle="Overall market mood"
            icon={getSentimentIcon(marketOverview.market_sentiment)}
            color={getSentimentColor(marketOverview.market_sentiment)}
          />
        </>
      )}

      {/* Seasonal Analytics Metrics */}
      {seasonalAnalytics && (
        <>
          <MetricCard
            title="Top Patterns"
            value={seasonalAnalytics.top_patterns.length}
            subtitle="Strongest seasonal signals"
            icon={ArrowTrendingUpIcon}
            color="blue"
          />

          <MetricCard
            title="Upcoming Forecasts"
            value={seasonalAnalytics.upcoming_forecasts.length}
            subtitle="Next 30 days"
            icon={ClockIcon}
            color="orange"
          />
        </>
      )}

      {/* Forecast Accuracy Metrics */}
      {forecastAccuracy && (
        <>
          <MetricCard
            title="Validated Forecasts"
            value={forecastAccuracy.total_validated_forecasts}
            subtitle={`Over ${forecastAccuracy.period_days} days`}
            icon={CheckCircleIcon}
            color="green"
          />

          <MetricCard
            title="CI Hit Rate"
            value={formatPercentage(forecastAccuracy.overall_ci_hit_rate)}
            subtitle="Confidence interval accuracy"
            icon={ChartBarIcon}
            color="blue"
            trend={{
              value: (forecastAccuracy.overall_ci_hit_rate - 0.8) * 100,
              label: "vs. 80% target",
              isPositive: forecastAccuracy.overall_ci_hit_rate > 0.8
            }}
          />
        </>
      )}

      {/* Horizon-specific accuracy metrics */}
      {forecastAccuracy?.accuracy_by_horizon && (
        <>
          {Object.entries(forecastAccuracy.accuracy_by_horizon).slice(0, 3).map(([horizon, stats]) => (
            <MetricCard
              key={horizon}
              title={`${horizon.toUpperCase()} Accuracy`}
              value={formatPercentage(stats.average_accuracy)}
              subtitle={`${stats.forecast_count} forecasts`}
              icon={ClockIcon}
              color="purple"
              trend={{
                value: (stats.ci_hit_rate - 0.8) * 100,
                label: `CI: ${formatPercentage(stats.ci_hit_rate)}`,
                isPositive: stats.ci_hit_rate > 0.8
              }}
            />
          ))}
        </>
      )}

      {/* Empty state metrics when no data */}
      {!marketOverview && !seasonalAnalytics && !forecastAccuracy && (
        <>
          <MetricCard
            title="Loading Analytics"
            value="..."
            subtitle="Fetching market data"
            icon={ArrowPathIcon}
            color="gray"
          />
          
          <MetricCard
            title="Pattern Analysis"
            value="..."
            subtitle="Processing seasonal data"
            icon={ChartBarIcon}
            color="gray"
          />
          
          <MetricCard
            title="Forecast Engine"
            value="..."
            subtitle="Calculating predictions"
            icon={ClockIcon}
            color="gray"
          />
          
          <MetricCard
            title="Market Events"
            value="..."
            subtitle="Scanning for events"
            icon={CalendarDaysIcon}
            color="gray"
          />
        </>
      )}
    </div>
  );
}

export default SeasonalMetricsGrid;