import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  ChartBarIcon, 
  ClockIcon, 
  CalendarDaysIcon, 
  LightBulbIcon,
  ArrowPathIcon,
  ExclamationTriangleIcon
} from '@heroicons/react/24/outline';
import { useSeasonalDashboard } from '../../hooks/useSeasonalData';
import { useDashboardRealtimeSync } from '../../hooks/useRealtimeSync';
import SeasonalPatternCard from './SeasonalPatternCard';
import SeasonalForecastCard from './SeasonalForecastCard';
import SeasonalRecommendationCard from './SeasonalRecommendationCard';
import SeasonalEventCard from './SeasonalEventCard';

interface SeasonalDashboardProps {
  className?: string;
}

type DashboardTab = 'overview' | 'patterns' | 'forecasts' | 'recommendations' | 'events';

export function SeasonalDashboard({ className = '' }: SeasonalDashboardProps) {
  const [activeTab, setActiveTab] = useState<DashboardTab>('overview');
  const [autoRefreshEnabled, setAutoRefreshEnabled] = useState(true);

  const {
    marketOverview,
    seasonalAnalytics,
    strongPatterns,
    upcomingEvents,
    activeRecommendations,
    tradingRecommendations,
    loading,
    error,
    refetchAll
  } = useSeasonalDashboard();

  const realtimeSync = useDashboardRealtimeSync(autoRefreshEnabled);

  const tabs = [
    { id: 'overview', label: 'Overview', icon: ChartBarIcon },
    { id: 'patterns', label: 'Patterns', icon: ChartBarIcon },
    { id: 'forecasts', label: 'Forecasts', icon: ClockIcon },
    { id: 'recommendations', label: 'Recommendations', icon: LightBulbIcon },
    { id: 'events', label: 'Events', icon: CalendarDaysIcon },
  ] as const;

  const formatNumber = (num: number) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
  };

  const formatPercentage = (value: number) => {
    return `${(value * 100).toFixed(1)}%`;
  };

  const handleRefresh = async () => {
    await refetchAll();
    await realtimeSync.actions.forceSync();
  };

  return (
    <div className={`min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 ${className}`}>
      {/* Header */}
      <div className="bg-gray-800/50 backdrop-blur-sm border-b border-gray-700/50 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-100 mb-2">
                Seasonal Analytics
              </h1>
              <p className="text-gray-400">
                Real-time seasonal pattern analysis for OSRS market trading
              </p>
            </div>
            
            <div className="flex items-center gap-4">
              {/* Connection Status */}
              <div className="flex items-center gap-2">
                <div className={`w-3 h-3 rounded-full ${
                  realtimeSync.state.connectionStatus === 'connected' ? 'bg-green-400 animate-pulse' :
                  realtimeSync.state.connectionStatus === 'connecting' ? 'bg-yellow-400 animate-pulse' :
                  realtimeSync.state.connectionStatus === 'error' ? 'bg-red-400' :
                  'bg-gray-400'
                }`} />
                <span className="text-xs text-gray-400">
                  {realtimeSync.state.connectionStatus === 'connected' ? 'Live' :
                   realtimeSync.state.connectionStatus === 'connecting' ? 'Connecting...' :
                   realtimeSync.state.connectionStatus === 'error' ? 'Error' :
                   'Disconnected'}
                </span>
              </div>

              {/* Auto Refresh Toggle */}
              <button
                onClick={() => setAutoRefreshEnabled(!autoRefreshEnabled)}
                className={`px-3 py-1 rounded-full text-xs font-semibold transition-colors ${
                  autoRefreshEnabled 
                    ? 'bg-green-400/20 text-green-400' 
                    : 'bg-gray-400/20 text-gray-400'
                }`}
              >
                Auto Refresh {autoRefreshEnabled ? 'ON' : 'OFF'}
              </button>

              {/* Manual Refresh */}
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={handleRefresh}
                disabled={loading}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600/20 text-blue-400 rounded-lg hover:bg-blue-600/30 transition-colors disabled:opacity-50"
              >
                <ArrowPathIcon className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                Refresh
              </motion.button>
            </div>
          </div>

          {/* Quick Stats */}
          {marketOverview.data && (
            <div className="grid grid-cols-2 md:grid-cols-6 gap-4 mt-6">
              <div className="bg-gray-700/30 rounded-lg p-3">
                <div className="text-xs text-gray-400 mb-1">Items Analyzed</div>
                <div className="text-lg font-bold text-green-400">
                  {formatNumber(marketOverview.data.total_items_analyzed)}
                </div>
              </div>
              <div className="bg-gray-700/30 rounded-lg p-3">
                <div className="text-xs text-gray-400 mb-1">Strong Patterns</div>
                <div className="text-lg font-bold text-blue-400">
                  {marketOverview.data.strong_patterns_count}
                </div>
              </div>
              <div className="bg-gray-700/30 rounded-lg p-3">
                <div className="text-xs text-gray-400 mb-1">Active Recs</div>
                <div className="text-lg font-bold text-yellow-400">
                  {marketOverview.data.active_recommendations}
                </div>
              </div>
              <div className="bg-gray-700/30 rounded-lg p-3">
                <div className="text-xs text-gray-400 mb-1">Events</div>
                <div className="text-lg font-bold text-purple-400">
                  {marketOverview.data.upcoming_events}
                </div>
              </div>
              <div className="bg-gray-700/30 rounded-lg p-3">
                <div className="text-xs text-gray-400 mb-1">Accuracy</div>
                <div className="text-lg font-bold text-green-400">
                  {formatPercentage(marketOverview.data.forecast_accuracy)}
                </div>
              </div>
              <div className="bg-gray-700/30 rounded-lg p-3">
                <div className="text-xs text-gray-400 mb-1">Sentiment</div>
                <div className={`text-lg font-bold capitalize ${
                  marketOverview.data.market_sentiment === 'positive' ? 'text-green-400' :
                  marketOverview.data.market_sentiment === 'negative' ? 'text-red-400' :
                  'text-gray-400'
                }`}>
                  {marketOverview.data.market_sentiment}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Error Banner */}
      {(error || realtimeSync.state.errors.length > 0) && (
        <div className="bg-red-400/10 border border-red-400/30 rounded-lg mx-6 mt-4 p-4">
          <div className="flex items-center gap-2">
            <ExclamationTriangleIcon className="w-5 h-5 text-red-400 flex-shrink-0" />
            <div>
              <div className="text-sm font-semibold text-red-400 mb-1">
                Connection Issues
              </div>
              <div className="text-xs text-red-300">
                {error || realtimeSync.state.errors[realtimeSync.state.errors.length - 1] || 'Unknown error occurred'}
              </div>
            </div>
            <button
              onClick={() => realtimeSync.actions.clearErrors()}
              className="ml-auto text-xs text-red-400 hover:text-red-300"
            >
              Dismiss
            </button>
          </div>
        </div>
      )}

      {/* Navigation Tabs */}
      <div className="max-w-7xl mx-auto px-6 py-6">
        <div className="flex items-center gap-1 bg-gray-800/30 rounded-lg p-1 mb-8">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as DashboardTab)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-all ${
                activeTab === tab.id
                  ? 'bg-blue-600/30 text-blue-400 shadow-sm'
                  : 'text-gray-400 hover:text-gray-200 hover:bg-gray-700/30'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.2 }}
          >
            {activeTab === 'overview' && (
              <div className="space-y-8">
                {/* Top Recommendations */}
                <section>
                  <h2 className="text-xl font-semibold text-gray-100 mb-4">
                    Active Trading Recommendations
                  </h2>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {tradingRecommendations.data?.slice(0, 6).map((recommendation) => (
                      <SeasonalRecommendationCard
                        key={recommendation.id}
                        recommendation={recommendation}
                      />
                    ))}
                  </div>
                </section>

                {/* Upcoming Events */}
                <section>
                  <h2 className="text-xl font-semibold text-gray-100 mb-4">
                    Upcoming Market Events
                  </h2>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {upcomingEvents.data?.slice(0, 3).map((event) => (
                      <SeasonalEventCard
                        key={event.id}
                        event={event}
                      />
                    ))}
                  </div>
                </section>

                {/* Strong Patterns */}
                <section>
                  <h2 className="text-xl font-semibold text-gray-100 mb-4">
                    Strongest Seasonal Patterns
                  </h2>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {strongPatterns.data?.slice(0, 6).map((pattern) => (
                      <SeasonalPatternCard
                        key={pattern.id}
                        pattern={pattern}
                      />
                    ))}
                  </div>
                </section>
              </div>
            )}

            {activeTab === 'patterns' && (
              <div>
                <h2 className="text-xl font-semibold text-gray-100 mb-6">
                  All Seasonal Patterns
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {strongPatterns.data?.map((pattern) => (
                    <SeasonalPatternCard
                      key={pattern.id}
                      pattern={pattern}
                    />
                  ))}
                </div>
              </div>
            )}

            {activeTab === 'forecasts' && (
              <div>
                <h2 className="text-xl font-semibold text-gray-100 mb-6">
                  Upcoming Forecasts
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {seasonalAnalytics.data?.upcoming_forecasts?.map((forecast) => (
                    <SeasonalForecastCard
                      key={forecast.id}
                      forecast={forecast}
                    />
                  ))}
                </div>
              </div>
            )}

            {activeTab === 'recommendations' && (
              <div>
                <h2 className="text-xl font-semibold text-gray-100 mb-6">
                  All Active Recommendations
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {activeRecommendations.data?.map((recommendation) => (
                    <SeasonalRecommendationCard
                      key={recommendation.id}
                      recommendation={recommendation}
                    />
                  ))}
                </div>
              </div>
            )}

            {activeTab === 'events' && (
              <div>
                <h2 className="text-xl font-semibold text-gray-100 mb-6">
                  All Upcoming Events
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {upcomingEvents.data?.map((event) => (
                    <SeasonalEventCard
                      key={event.id}
                      event={event}
                    />
                  ))}
                </div>
              </div>
            )}
          </motion.div>
        </AnimatePresence>

        {/* Loading State */}
        {loading && (
          <div className="flex items-center justify-center py-12">
            <div className="flex items-center gap-3 text-gray-400">
              <ArrowPathIcon className="w-5 h-5 animate-spin" />
              Loading seasonal data...
            </div>
          </div>
        )}

        {/* Empty State */}
        {!loading && activeTab === 'patterns' && strongPatterns.data?.length === 0 && (
          <div className="text-center py-12">
            <ChartBarIcon className="w-16 h-16 text-gray-600 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-300 mb-2">
              No Seasonal Patterns Found
            </h3>
            <p className="text-gray-500">
              Seasonal patterns will appear here once the analysis engine processes market data.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

export default SeasonalDashboard;