import React, { useState, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ChartBarIcon,
  ClockIcon,
  TrendingUpIcon,
  TrendingDownIcon,
  BoltIcon,
  EyeIcon,
  CpuChipIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  SparklesIcon,
  CalendarDaysIcon
} from '@heroicons/react/24/outline';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  BarChart,
  Bar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar
} from 'recharts';

interface VolumePrediction {
  timestamp: string;
  predicted_volume: number;
  confidence: number;
  historical_average: number;
  time_label: string;
  factors: {
    day_of_week: number;
    hour_of_day: number;
    seasonal: number;
    trend: number;
    events: number;
  };
}

interface MarketEvent {
  timestamp: string;
  event_type: 'update' | 'spike' | 'crash' | 'seasonal';
  impact_level: 'low' | 'medium' | 'high';
  description: string;
  affected_items: number[];
}

interface VolumeInsight {
  insight_type: 'opportunity' | 'warning' | 'trend';
  title: string;
  description: string;
  confidence: number;
  timeframe: string;
  action: string;
}

interface PredictiveVolumeDashboardProps {
  opportunities: any[];
  selectedTimeframe: '1h' | '6h' | '24h' | '7d';
  onTimeframeChange: (timeframe: '1h' | '6h' | '24h' | '7d') => void;
  className?: string;
}

export const PredictiveVolumeDashboard: React.FC<PredictiveVolumeDashboardProps> = ({
  opportunities,
  selectedTimeframe,
  onTimeframeChange,
  className = ''
}) => {
  const [volumePredictions, setVolumePredictions] = useState<VolumePrediction[]>([]);
  const [marketEvents, setMarketEvents] = useState<MarketEvent[]>([]);
  const [insights, setInsights] = useState<VolumeInsight[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedItem, setSelectedItem] = useState<number | null>(null);
  const [showDetailedView, setShowDetailedView] = useState(false);

  // Generate mock predictions (replace with actual ML predictions)
  useEffect(() => {
    setLoading(true);
    
    setTimeout(() => {
      const now = new Date();
      const predictions: VolumePrediction[] = [];
      const events: MarketEvent[] = [];
      const generatedInsights: VolumeInsight[] = [];
      
      // Generate predictions based on timeframe
      const intervals = selectedTimeframe === '1h' ? 12 : 
                       selectedTimeframe === '6h' ? 24 : 
                       selectedTimeframe === '24h' ? 24 : 168;
      const stepSize = selectedTimeframe === '1h' ? 5 : 
                      selectedTimeframe === '6h' ? 15 : 
                      selectedTimeframe === '24h' ? 60 : 1440;
      
      for (let i = 0; i < intervals; i++) {
        const timestamp = new Date(now.getTime() + (i * stepSize * 60 * 1000));
        const hour = timestamp.getHours();
        const dayOfWeek = timestamp.getDay();
        
        // Simulate realistic volume patterns
        const baseVolume = 5000 + Math.random() * 15000;
        const hourMultiplier = hour >= 18 && hour <= 23 ? 1.5 : // Peak evening hours
                              hour >= 12 && hour <= 17 ? 1.2 : // Afternoon activity
                              hour >= 6 && hour <= 11 ? 0.9 : // Morning
                              0.6; // Late night
        const dayMultiplier = dayOfWeek === 0 || dayOfWeek === 6 ? 1.3 : 1.0; // Weekends
        
        const predictedVolume = Math.round(baseVolume * hourMultiplier * dayMultiplier * (0.8 + Math.random() * 0.4));
        const historicalAverage = Math.round(baseVolume * hourMultiplier * dayMultiplier * 0.9);
        
        predictions.push({
          timestamp: timestamp.toISOString(),
          predicted_volume: predictedVolume,
          confidence: 75 + Math.random() * 20,
          historical_average: historicalAverage,
          time_label: selectedTimeframe === '7d' 
            ? timestamp.toLocaleDateString(undefined, { weekday: 'short' })
            : timestamp.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' }),
          factors: {
            day_of_week: dayMultiplier,
            hour_of_day: hourMultiplier,
            seasonal: 1.0 + Math.sin((timestamp.getTime() / (1000 * 60 * 60 * 24)) * Math.PI / 30) * 0.1,
            trend: 0.95 + Math.random() * 0.1,
            events: Math.random() > 0.8 ? 1.2 : 1.0
          }
        });
      }
      
      // Generate market events
      if (Math.random() > 0.3) {
        events.push({
          timestamp: new Date(now.getTime() + Math.random() * 24 * 60 * 60 * 1000).toISOString(),
          event_type: 'update',
          impact_level: 'medium',
          description: 'OSRS Game Update - Expected volume increase',
          affected_items: opportunities.slice(0, 5).map(o => o.item_id)
        });
      }
      
      if (Math.random() > 0.7) {
        events.push({
          timestamp: new Date(now.getTime() + Math.random() * 6 * 60 * 60 * 1000).toISOString(),
          event_type: 'spike',
          impact_level: 'high',
          description: 'Content creator showcase - High volume spike expected',
          affected_items: opportunities.slice(2, 8).map(o => o.item_id)
        });
      }
      
      // Generate insights
      generatedInsights.push(
        {
          insight_type: 'opportunity',
          title: 'Peak Volume Window Identified',
          description: `Expected ${selectedTimeframe === '7d' ? 'weekend' : 'evening'} volume surge of 40-60% above average`,
          confidence: 82,
          timeframe: selectedTimeframe === '7d' ? 'Saturday-Sunday' : '6-10 PM',
          action: 'Consider increasing position sizes during this window'
        },
        {
          insight_type: 'trend',
          title: 'Volume Trend Analysis',
          description: 'Market showing consistent upward volume trend over the past period',
          confidence: 76,
          timeframe: 'Next 24 hours',
          action: 'Maintain current strategy with slight bias toward volume plays'
        },
        {
          insight_type: 'warning',
          title: 'Low Volume Period Approaching',
          description: `${selectedTimeframe === '7d' ? 'Weekday' : 'Late night'} volume typically drops by 30-45%`,
          confidence: 89,
          timeframe: selectedTimeframe === '7d' ? 'Monday-Friday' : '2-6 AM',
          action: 'Reduce exposure or focus on high-liquidity items'
        }
      );
      
      setVolumePredictions(predictions);
      setMarketEvents(events);
      setInsights(generatedInsights);
      setLoading(false);
    }, 1500);
    
  }, [selectedTimeframe, opportunities]);

  const aggregateStats = useMemo(() => {
    if (volumePredictions.length === 0) return null;
    
    const totalPredicted = volumePredictions.reduce((sum, p) => sum + p.predicted_volume, 0);
    const totalHistorical = volumePredictions.reduce((sum, p) => sum + p.historical_average, 0);
    const avgConfidence = volumePredictions.reduce((sum, p) => sum + p.confidence, 0) / volumePredictions.length;
    
    const peakVolume = Math.max(...volumePredictions.map(p => p.predicted_volume));
    const peakTime = volumePredictions.find(p => p.predicted_volume === peakVolume)?.time_label || 'Unknown';
    
    const trend = totalPredicted > totalHistorical ? 'up' : totalPredicted < totalHistorical ? 'down' : 'stable';
    const changePercent = ((totalPredicted - totalHistorical) / totalHistorical) * 100;
    
    return {
      totalPredicted,
      totalHistorical,
      avgConfidence,
      peakVolume,
      peakTime,
      trend,
      changePercent
    };
  }, [volumePredictions]);

  const formatVolume = (volume: number): string => {
    if (volume >= 1000000) return `${(volume / 1000000).toFixed(1)}M`;
    if (volume >= 1000) return `${(volume / 1000).toFixed(1)}K`;
    return volume.toString();
  };

  const getInsightIcon = (type: string) => {
    switch (type) {
      case 'opportunity': return <CheckCircleIcon className="w-5 h-5 text-green-400" />;
      case 'warning': return <ExclamationTriangleIcon className="w-5 h-5 text-yellow-400" />;
      case 'trend': return <TrendingUpIcon className="w-5 h-5 text-blue-400" />;
      default: return <EyeIcon className="w-5 h-5 text-gray-400" />;
    }
  };

  const getInsightColor = (type: string) => {
    switch (type) {
      case 'opportunity': return 'border-green-500/30 bg-green-900/20';
      case 'warning': return 'border-yellow-500/30 bg-yellow-900/20';
      case 'trend': return 'border-blue-500/30 bg-blue-900/20';
      default: return 'border-gray-500/30 bg-gray-900/20';
    }
  };

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-gray-800/95 backdrop-blur-sm border border-gray-700/50 rounded-lg p-4 shadow-lg">
          <p className="text-sm text-gray-300 mb-2">{label}</p>
          <div className="space-y-1">
            <p className="text-sm">
              <span className="text-purple-400">Predicted:</span> {formatVolume(data.predicted_volume)}
            </p>
            <p className="text-sm">
              <span className="text-gray-400">Historical:</span> {formatVolume(data.historical_average)}
            </p>
            <p className="text-sm">
              <span className="text-blue-400">Confidence:</span> {data.confidence.toFixed(1)}%
            </p>
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={`bg-gradient-to-br from-purple-900/20 to-pink-900/30 backdrop-blur-sm border border-purple-500/30 rounded-xl overflow-hidden ${className}`}
    >
      {/* Header */}
      <div className="p-4 border-b border-purple-500/30">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-purple-500/20 rounded-lg">
              <CpuChipIcon className="w-6 h-6 text-purple-400" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-purple-400">🔮 Predictive Volume Intelligence</h3>
              <p className="text-sm text-gray-400">ML-powered trading volume forecasting</p>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            <div className="flex bg-gray-700/30 rounded-lg p-1">
              {(['1h', '6h', '24h', '7d'] as const).map((tf) => (
                <button
                  key={tf}
                  onClick={() => onTimeframeChange(tf)}
                  className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${
                    selectedTimeframe === tf
                      ? 'bg-purple-600 text-white'
                      : 'text-gray-400 hover:text-white'
                  }`}
                >
                  {tf}
                </button>
              ))}
            </div>
            
            <button
              onClick={() => setShowDetailedView(!showDetailedView)}
              className={`p-2 rounded-lg transition-colors ${
                showDetailedView 
                  ? 'bg-purple-600 text-white' 
                  : 'bg-gray-700/50 text-gray-400 hover:text-white'
              }`}
            >
              <EyeIcon className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Stats Overview */}
        {aggregateStats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="bg-gray-800/40 rounded-lg p-3 text-center">
              <div className="text-lg font-bold text-purple-400">{formatVolume(aggregateStats.peakVolume)}</div>
              <div className="text-xs text-gray-400">Peak Volume</div>
              <div className="text-xs text-purple-300">@ {aggregateStats.peakTime}</div>
            </div>
            
            <div className="bg-gray-800/40 rounded-lg p-3 text-center">
              <div className={`text-lg font-bold flex items-center justify-center gap-1 ${
                aggregateStats.trend === 'up' ? 'text-green-400' :
                aggregateStats.trend === 'down' ? 'text-red-400' :
                'text-gray-400'
              }`}>
                {aggregateStats.trend === 'up' ? (
                  <>
                    <TrendingUpIcon className="w-4 h-4" />
                    +{Math.abs(aggregateStats.changePercent).toFixed(1)}%
                  </>
                ) : aggregateStats.trend === 'down' ? (
                  <>
                    <TrendingDownIcon className="w-4 h-4" />
                    -{Math.abs(aggregateStats.changePercent).toFixed(1)}%
                  </>
                ) : (
                  <>
                    <ClockIcon className="w-4 h-4" />
                    Stable
                  </>
                )}
              </div>
              <div className="text-xs text-gray-400">vs Historical</div>
            </div>
            
            <div className="bg-gray-800/40 rounded-lg p-3 text-center">
              <div className={`text-lg font-bold ${
                aggregateStats.avgConfidence >= 80 ? 'text-green-400' :
                aggregateStats.avgConfidence >= 60 ? 'text-yellow-400' :
                'text-red-400'
              }`}>
                {aggregateStats.avgConfidence.toFixed(1)}%
              </div>
              <div className="text-xs text-gray-400">Avg Confidence</div>
            </div>
            
            <div className="bg-gray-800/40 rounded-lg p-3 text-center">
              <div className="text-lg font-bold text-pink-400">{formatVolume(aggregateStats.totalPredicted)}</div>
              <div className="text-xs text-gray-400">Total Forecast</div>
              <div className="text-xs text-pink-300">{selectedTimeframe} period</div>
            </div>
          </div>
        )}
      </div>

      {/* Main Chart */}
      <div className="p-4">
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-400 mx-auto mb-3"></div>
              <p className="text-gray-400">Analyzing market patterns...</p>
              <p className="text-xs text-gray-500 mt-1">Running ML predictions</p>
            </div>
          </div>
        ) : (
          <div style={{ width: '100%', height: showDetailedView ? '350px' : '250px' }}>
            <ResponsiveContainer>
              <AreaChart data={volumePredictions} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                <defs>
                  <linearGradient id="volumeGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="historicalGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6b7280" stopOpacity={0.2}/>
                    <stop offset="95%" stopColor="#6b7280" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />
                
                <XAxis 
                  dataKey="time_label" 
                  stroke="#9ca3af" 
                  fontSize={11}
                  interval="preserveStartEnd"
                />
                
                <YAxis 
                  stroke="#9ca3af" 
                  fontSize={11}
                  tickFormatter={formatVolume}
                />
                
                <Tooltip content={<CustomTooltip />} />
                
                {/* Historical average baseline */}
                <Area
                  type="monotone"
                  dataKey="historical_average"
                  stroke="#6b7280"
                  strokeWidth={1}
                  strokeDasharray="5 5"
                  fill="url(#historicalGradient)"
                  fillOpacity={0.3}
                />
                
                {/* Predicted volume */}
                <Area
                  type="monotone"
                  dataKey="predicted_volume"
                  stroke="#8b5cf6"
                  strokeWidth={3}
                  fill="url(#volumeGradient)"
                  dot={false}
                  activeDot={{ r: 4, fill: '#8b5cf6' }}
                />
                
                {/* Mark current time */}
                <ReferenceLine 
                  x={volumePredictions[0]?.time_label} 
                  stroke="#f59e0b" 
                  strokeDasharray="3 3"
                  strokeWidth={2}
                  label={{ value: "Now", position: "topLeft", fontSize: 10, fill: "#f59e0b" }}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Insights and Events */}
      <div className="border-t border-purple-500/30 p-4 space-y-4">
        {/* Market Events */}
        {marketEvents.length > 0 && (
          <div>
            <div className="flex items-center gap-2 mb-3">
              <CalendarDaysIcon className="w-4 h-4 text-pink-400" />
              <span className="text-sm font-medium text-pink-400">Upcoming Market Events</span>
            </div>
            <div className="space-y-2">
              {marketEvents.map((event, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.1 }}
                  className={`p-3 rounded-lg border ${
                    event.impact_level === 'high' ? 'border-red-500/30 bg-red-900/20' :
                    event.impact_level === 'medium' ? 'border-yellow-500/30 bg-yellow-900/20' :
                    'border-blue-500/30 bg-blue-900/20'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <BoltIcon className={`w-4 h-4 ${
                          event.impact_level === 'high' ? 'text-red-400' :
                          event.impact_level === 'medium' ? 'text-yellow-400' :
                          'text-blue-400'
                        }`} />
                        <span className="text-sm font-medium text-gray-200">{event.description}</span>
                      </div>
                      <div className="text-xs text-gray-400">
                        Affects {event.affected_items.length} items • {new Date(event.timestamp).toLocaleString()}
                      </div>
                    </div>
                    <div className={`px-2 py-1 rounded-full text-xs font-medium ${
                      event.impact_level === 'high' ? 'bg-red-500/20 text-red-400' :
                      event.impact_level === 'medium' ? 'bg-yellow-500/20 text-yellow-400' :
                      'bg-blue-500/20 text-blue-400'
                    }`}>
                      {event.impact_level.toUpperCase()}
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        )}

        {/* AI Insights */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <SparklesIcon className="w-4 h-4 text-purple-400" />
            <span className="text-sm font-medium text-purple-400">AI Trading Insights</span>
          </div>
          <div className="grid gap-3">
            {insights.map((insight, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                className={`p-3 rounded-lg border ${getInsightColor(insight.insight_type)}`}
              >
                <div className="flex items-start gap-3">
                  {getInsightIcon(insight.insight_type)}
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-1">
                      <h4 className="text-sm font-medium text-gray-200">{insight.title}</h4>
                      <div className="text-xs text-gray-400">{insight.confidence}% confidence</div>
                    </div>
                    <p className="text-xs text-gray-300 mb-2">{insight.description}</p>
                    <div className="flex items-center justify-between">
                      <div className="text-xs text-gray-400">
                        <ClockIcon className="w-3 h-3 inline mr-1" />
                        {insight.timeframe}
                      </div>
                      <div className="text-xs text-purple-300 font-medium">{insight.action}</div>
                    </div>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </div>

      {/* Detailed Analysis (when expanded) */}
      <AnimatePresence>
        {showDetailedView && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="border-t border-purple-500/30 p-4 bg-purple-900/10"
          >
            <h4 className="text-sm font-medium text-purple-400 mb-3">Volume Factor Analysis</h4>
            
            {volumePredictions.length > 0 && (
              <div style={{ width: '100%', height: '200px' }}>
                <ResponsiveContainer>
                  <RadarChart data={[{
                    factor: 'Day of Week',
                    impact: volumePredictions[0]?.factors.day_of_week * 100 || 100,
                  }, {
                    factor: 'Hour of Day',
                    impact: volumePredictions[0]?.factors.hour_of_day * 100 || 100,
                  }, {
                    factor: 'Seasonal',
                    impact: volumePredictions[0]?.factors.seasonal * 100 || 100,
                  }, {
                    factor: 'Trend',
                    impact: volumePredictions[0]?.factors.trend * 100 || 100,
                  }, {
                    factor: 'Events',
                    impact: volumePredictions[0]?.factors.events * 100 || 100,
                  }]}>
                    <PolarGrid stroke="#4b5563" />
                    <PolarAngleAxis dataKey="factor" tick={{ fill: '#9ca3af', fontSize: 11 }} />
                    <PolarRadiusAxis 
                      angle={90} 
                      domain={[0, 150]} 
                      tick={{ fill: '#6b7280', fontSize: 10 }} 
                    />
                    <Radar
                      name="Impact"
                      dataKey="impact"
                      stroke="#8b5cf6"
                      fill="#8b5cf6"
                      fillOpacity={0.3}
                      strokeWidth={2}
                    />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

export default PredictiveVolumeDashboard;