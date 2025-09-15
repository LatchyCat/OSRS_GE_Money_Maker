import React, { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  ChartBarIcon, 
  AdjustmentsHorizontalIcon,
  ArrowPathIcon,
  EyeIcon,
  FunnelIcon,
  Squares2X2Icon,
  ListBulletIcon,
  ChartPieIcon,
  CalendarIcon
} from '@heroicons/react/24/outline';
import { useSeasonalPatterns, useSeasonalAnalytics, useForecastAccuracyStats } from '../../hooks/useSeasonalData';
import SeasonalMetricsGrid from './SeasonalMetricsGrid';
import SeasonalPatternChart from './SeasonalPatternChart';
import SeasonalHeatmap from './SeasonalHeatmap';
import SeasonalPatternCard from './SeasonalPatternCard';
import SeasonalForecastCard from './SeasonalForecastCard';
import SeasonalRecommendationCard from './SeasonalRecommendationCard';
import SeasonalEventCard from './SeasonalEventCard';

interface SeasonalAnalyticsViewProps {
  className?: string;
}

type ViewMode = 'overview' | 'patterns' | 'heatmaps' | 'charts' | 'forecasts';
type FilterType = 'all' | 'strong' | 'weekly' | 'monthly' | 'yearly' | 'events';
type SortType = 'strength' | 'confidence' | 'profit' | 'recent';

export function SeasonalAnalyticsView({ className = '' }: SeasonalAnalyticsViewProps) {
  const [viewMode, setViewMode] = useState<ViewMode>('overview');
  const [filterType, setFilterType] = useState<FilterType>('all');
  const [sortType, setSortType] = useState<SortType>('strength');
  const [selectedPatternId, setSelectedPatternId] = useState<number | null>(null);
  const [showFilters, setShowFilters] = useState(false);

  // Data hooks
  const { data: patterns, loading: patternsLoading, refetch: refetchPatterns } = useSeasonalPatterns({
    min_strength: filterType === 'strong' ? 0.6 : undefined,
    pattern_type: filterType === 'weekly' || filterType === 'monthly' || filterType === 'yearly' ? filterType : undefined,
    ordering: sortType === 'strength' ? '-overall_pattern_strength' : 
              sortType === 'confidence' ? '-forecast_confidence' :
              sortType === 'profit' ? '-item__profit_margin' :
              '-analysis_timestamp',
    page_size: 50
  });

  const { data: analytics, loading: analyticsLoading } = useSeasonalAnalytics();
  const { data: forecastStats, loading: statsLoading } = useForecastAccuracyStats();

  // Filtered and sorted data
  const filteredPatterns = useMemo(() => {
    if (!patterns) return [];
    
    let filtered = patterns;
    
    // Apply filters
    if (filterType === 'strong') {
      filtered = patterns.filter(p => p.overall_pattern_strength >= 0.6);
    } else if (filterType === 'weekly') {
      filtered = patterns.filter(p => p.dominant_pattern_type === 'weekly');
    } else if (filterType === 'monthly') {
      filtered = patterns.filter(p => p.dominant_pattern_type === 'monthly');
    } else if (filterType === 'yearly') {
      filtered = patterns.filter(p => p.dominant_pattern_type === 'yearly');
    } else if (filterType === 'events') {
      filtered = patterns.filter(p => p.event_pattern_strength > 0);
    }
    
    return filtered;
  }, [patterns, filterType]);

  const selectedPattern = useMemo(() => {
    if (!selectedPatternId || !patterns) return null;
    return patterns.find(p => p.id === selectedPatternId) || null;
  }, [selectedPatternId, patterns]);

  const viewModes = [
    { id: 'overview', label: 'Overview', icon: Squares2X2Icon },
    { id: 'patterns', label: 'Pattern Analysis', icon: ChartBarIcon },
    { id: 'heatmaps', label: 'Heatmaps', icon: ChartPieIcon },
    { id: 'charts', label: 'Charts', icon: EyeIcon },
    { id: 'forecasts', label: 'Forecasts', icon: CalendarIcon },
  ] as const;

  const filterOptions = [
    { id: 'all', label: 'All Patterns' },
    { id: 'strong', label: 'Strong Patterns' },
    { id: 'weekly', label: 'Weekly Patterns' },
    { id: 'monthly', label: 'Monthly Patterns' },
    { id: 'yearly', label: 'Yearly Patterns' },
    { id: 'events', label: 'Event Patterns' },
  ] as const;

  const sortOptions = [
    { id: 'strength', label: 'Pattern Strength' },
    { id: 'confidence', label: 'Forecast Confidence' },
    { id: 'profit', label: 'Profit Margin' },
    { id: 'recent', label: 'Most Recent' },
  ] as const;

  const handleRefresh = async () => {
    await refetchPatterns();
  };

  const renderOverview = () => (
    <div className="space-y-8">
      {/* Metrics Grid */}
      <SeasonalMetricsGrid
        marketOverview={analytics?.generated_at ? {
          total_items_analyzed: filteredPatterns.length,
          strong_patterns_count: filteredPatterns.filter(p => p.overall_pattern_strength >= 0.6).length,
          active_recommendations: analytics?.active_recommendations?.length || 0,
          upcoming_events: analytics?.upcoming_events?.length || 0,
          forecast_accuracy: forecastStats?.overall_ci_hit_rate || 0,
          market_sentiment: 'positive',
          last_updated: analytics.generated_at
        } : undefined}
        seasonalAnalytics={analytics}
        forecastAccuracy={forecastStats}
      />

      {/* Top Patterns Summary */}
      <section>
        <h3 className="text-xl font-semibold text-gray-100 mb-4">
          Strongest Patterns ({filteredPatterns.slice(0, 6).length})
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredPatterns.slice(0, 6).map((pattern) => (
            <SeasonalPatternCard
              key={pattern.id}
              pattern={pattern}
              onClick={() => setSelectedPatternId(pattern.id)}
            />
          ))}
        </div>
      </section>

      {/* Recent Forecasts */}
      {analytics?.upcoming_forecasts && (
        <section>
          <h3 className="text-xl font-semibold text-gray-100 mb-4">
            Upcoming Forecasts ({analytics.upcoming_forecasts.length})
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {analytics.upcoming_forecasts.slice(0, 6).map((forecast) => (
              <SeasonalForecastCard
                key={forecast.id}
                forecast={forecast}
              />
            ))}
          </div>
        </section>
      )}
    </div>
  );

  const renderPatterns = () => (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredPatterns.map((pattern) => (
          <SeasonalPatternCard
            key={pattern.id}
            pattern={pattern}
            onClick={() => setSelectedPatternId(pattern.id)}
          />
        ))}
      </div>
      
      {filteredPatterns.length === 0 && !patternsLoading && (
        <div className="text-center py-12">
          <ChartBarIcon className="w-16 h-16 text-gray-600 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-300 mb-2">
            No patterns found
          </h3>
          <p className="text-gray-500">
            Try adjusting your filters or check back later for new patterns.
          </p>
        </div>
      )}
    </div>
  );

  const renderHeatmaps = () => (
    <div className="space-y-8">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <SeasonalHeatmap
          patterns={filteredPatterns}
          type="monthly"
          metric="strength"
        />
        <SeasonalHeatmap
          patterns={filteredPatterns}
          type="weekly"
          metric="strength"
        />
      </div>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <SeasonalHeatmap
          patterns={filteredPatterns}
          type="monthly"
          metric="profit"
        />
        <SeasonalHeatmap
          patterns={filteredPatterns}
          type="hourly"
          metric="volume"
        />
      </div>
    </div>
  );

  const renderCharts = () => (
    <div className="space-y-8">
      {selectedPattern && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <SeasonalPatternChart pattern={selectedPattern} chartType="line" />
          <SeasonalPatternChart pattern={selectedPattern} chartType="bar" />
          <SeasonalPatternChart pattern={selectedPattern} chartType="radar" />
          <SeasonalPatternChart pattern={selectedPattern} chartType="pie" />
        </div>
      )}
      
      {!selectedPattern && (
        <div className="text-center py-12">
          <EyeIcon className="w-16 h-16 text-gray-600 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-300 mb-2">
            Select a pattern to view charts
          </h3>
          <p className="text-gray-500">
            Click on any pattern card to see detailed visualization charts.
          </p>
        </div>
      )}
    </div>
  );

  const renderForecasts = () => (
    <div className="space-y-6">
      {analytics?.upcoming_forecasts && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {analytics.upcoming_forecasts.map((forecast) => (
            <SeasonalForecastCard
              key={forecast.id}
              forecast={forecast}
            />
          ))}
        </div>
      )}
      
      {(!analytics?.upcoming_forecasts || analytics.upcoming_forecasts.length === 0) && (
        <div className="text-center py-12">
          <CalendarIcon className="w-16 h-16 text-gray-600 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-300 mb-2">
            No upcoming forecasts
          </h3>
          <p className="text-gray-500">
            Forecasts will appear here once the prediction engine generates new forecasts.
          </p>
        </div>
      )}
    </div>
  );

  return (
    <div className={`min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 ${className}`}>
      {/* Header */}
      <div className="bg-gray-800/50 backdrop-blur-sm border-b border-gray-700/50 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-3xl font-bold text-gray-100 mb-2">
                Advanced Seasonal Analytics
              </h1>
              <p className="text-gray-400">
                Deep dive into seasonal patterns, forecasts, and market insights
              </p>
            </div>
            
            <div className="flex items-center gap-4">
              <button
                onClick={() => setShowFilters(!showFilters)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                  showFilters 
                    ? 'bg-blue-600/30 text-blue-400' 
                    : 'bg-gray-700/50 text-gray-400 hover:text-gray-200'
                }`}
              >
                <FunnelIcon className="w-4 h-4" />
                Filters
              </button>
              
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={handleRefresh}
                disabled={patternsLoading}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600/20 text-blue-400 rounded-lg hover:bg-blue-600/30 transition-colors disabled:opacity-50"
              >
                <ArrowPathIcon className={`w-4 h-4 ${patternsLoading ? 'animate-spin' : ''}`} />
                Refresh
              </motion.button>
            </div>
          </div>

          {/* View Mode Tabs */}
          <div className="flex items-center gap-1 bg-gray-700/30 rounded-lg p-1">
            {viewModes.map((mode) => (
              <button
                key={mode.id}
                onClick={() => setViewMode(mode.id as ViewMode)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-all ${
                  viewMode === mode.id
                    ? 'bg-blue-600/30 text-blue-400 shadow-sm'
                    : 'text-gray-400 hover:text-gray-200 hover:bg-gray-600/30'
                }`}
              >
                <mode.icon className="w-4 h-4" />
                {mode.label}
              </button>
            ))}
          </div>

          {/* Filters Panel */}
          <AnimatePresence>
            {showFilters && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="mt-4 p-4 bg-gray-700/30 rounded-lg"
              >
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Filter Type
                    </label>
                    <select
                      value={filterType}
                      onChange={(e) => setFilterType(e.target.value as FilterType)}
                      className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-gray-200 focus:border-blue-500 focus:outline-none"
                    >
                      {filterOptions.map((option) => (
                        <option key={option.id} value={option.id}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Sort By
                    </label>
                    <select
                      value={sortType}
                      onChange={(e) => setSortType(e.target.value as SortType)}
                      className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-gray-200 focus:border-blue-500 focus:outline-none"
                    >
                      {sortOptions.map((option) => (
                        <option key={option.id} value={option.id}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  
                  <div className="flex items-end">
                    <div className="text-sm text-gray-400">
                      {filteredPatterns.length} patterns found
                    </div>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-6 py-8">
        <AnimatePresence mode="wait">
          <motion.div
            key={viewMode}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.2 }}
          >
            {viewMode === 'overview' && renderOverview()}
            {viewMode === 'patterns' && renderPatterns()}
            {viewMode === 'heatmaps' && renderHeatmaps()}
            {viewMode === 'charts' && renderCharts()}
            {viewMode === 'forecasts' && renderForecasts()}
          </motion.div>
        </AnimatePresence>

        {/* Loading State */}
        {patternsLoading && (
          <div className="flex items-center justify-center py-12">
            <div className="flex items-center gap-3 text-gray-400">
              <ArrowPathIcon className="w-5 h-5 animate-spin" />
              Loading seasonal analytics...
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default SeasonalAnalyticsView;