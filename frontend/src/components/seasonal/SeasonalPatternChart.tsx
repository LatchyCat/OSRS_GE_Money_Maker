import React, { useMemo } from 'react';
import { motion } from 'framer-motion';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar
} from 'recharts';
import type { SeasonalPattern } from '../../types/seasonal';

interface SeasonalPatternChartProps {
  pattern: SeasonalPattern;
  chartType?: 'line' | 'area' | 'bar' | 'radar' | 'pie';
  height?: number;
  className?: string;
}

export function SeasonalPatternChart({ 
  pattern, 
  chartType = 'line', 
  height = 300, 
  className = '' 
}: SeasonalPatternChartProps) {
  
  // Process weekly effects data
  const weeklyData = useMemo(() => {
    const dayOrder = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
    
    return dayOrder.map(day => ({
      day: day.substring(0, 3),
      effect: pattern.day_of_week_effects?.[day] || 0,
      isWeekend: day === 'Saturday' || day === 'Sunday',
      isBest: day === pattern.best_day_of_week,
      isWorst: day === pattern.worst_day_of_week
    }));
  }, [pattern]);

  // Process monthly effects data
  const monthlyData = useMemo(() => {
    const months = [
      'January', 'February', 'March', 'April', 'May', 'June',
      'July', 'August', 'September', 'October', 'November', 'December'
    ];
    
    return months.map(month => ({
      month: month.substring(0, 3),
      effect: pattern.monthly_effects?.[month] || 0,
      isBest: month === pattern.best_month,
      isWorst: month === pattern.worst_month
    }));
  }, [pattern]);

  // Process quarterly data
  const quarterlyData = useMemo(() => {
    const quarters = ['Q1', 'Q2', 'Q3', 'Q4'];
    
    return quarters.map(quarter => ({
      quarter,
      effect: pattern.quarterly_effects?.[quarter] || 0
    }));
  }, [pattern]);

  // Pattern strength breakdown for radar chart
  const strengthData = useMemo(() => {
    return [
      { subject: 'Weekly', value: pattern.weekly_pattern_strength * 100, fullMark: 100 },
      { subject: 'Monthly', value: pattern.monthly_pattern_strength * 100, fullMark: 100 },
      { subject: 'Yearly', value: pattern.yearly_pattern_strength * 100, fullMark: 100 },
      { subject: 'Event', value: pattern.event_pattern_strength * 100, fullMark: 100 },
      { subject: 'Overall', value: pattern.overall_pattern_strength * 100, fullMark: 100 }
    ];
  }, [pattern]);

  // Pattern type distribution for pie chart
  const pieData = useMemo(() => {
    const data = [
      { name: 'Weekly', value: pattern.weekly_pattern_strength, color: '#3B82F6' },
      { name: 'Monthly', value: pattern.monthly_pattern_strength, color: '#10B981' },
      { name: 'Yearly', value: pattern.yearly_pattern_strength, color: '#8B5CF6' },
    ];
    
    if (pattern.event_pattern_strength > 0) {
      data.push({ name: 'Event', value: pattern.event_pattern_strength, color: '#F59E0B' });
    }
    
    return data.filter(item => item.value > 0);
  }, [pattern]);

  // Custom tooltip component
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-gray-800 border border-gray-600 rounded-lg p-3 shadow-xl">
          <p className="text-gray-300 text-sm font-semibold">{label}</p>
          {payload.map((entry: any, index: number) => (
            <p key={index} className="text-sm" style={{ color: entry.color }}>
              {entry.name}: {typeof entry.value === 'number' ? entry.value.toFixed(2) : entry.value}
              {entry.name === 'effect' ? '%' : ''}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  // Chart color schemes
  const getBarColor = (dataPoint: any, index: number) => {
    if (dataPoint.isBest) return '#10B981'; // Green for best
    if (dataPoint.isWorst) return '#EF4444'; // Red for worst
    if (dataPoint.isWeekend) return '#F59E0B'; // Orange for weekend
    return '#3B82F6'; // Blue default
  };

  const renderChart = () => {
    switch (chartType) {
      case 'line':
        return (
          <ResponsiveContainer width="100%" height={height}>
            <LineChart data={weeklyData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="day" stroke="#9CA3AF" fontSize={12} />
              <YAxis stroke="#9CA3AF" fontSize={12} />
              <Tooltip content={<CustomTooltip />} />
              <Line 
                type="monotone" 
                dataKey="effect" 
                stroke="#3B82F6" 
                strokeWidth={2}
                dot={{ fill: '#3B82F6', strokeWidth: 2, r: 4 }}
                activeDot={{ r: 6, fill: '#60A5FA' }}
              />
            </LineChart>
          </ResponsiveContainer>
        );

      case 'area':
        return (
          <ResponsiveContainer width="100%" height={height}>
            <AreaChart data={monthlyData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="month" stroke="#9CA3AF" fontSize={12} />
              <YAxis stroke="#9CA3AF" fontSize={12} />
              <Tooltip content={<CustomTooltip />} />
              <Area 
                type="monotone" 
                dataKey="effect" 
                stroke="#10B981" 
                fill="url(#colorGradient)"
                strokeWidth={2}
              />
              <defs>
                <linearGradient id="colorGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10B981" stopOpacity={0.8}/>
                  <stop offset="95%" stopColor="#10B981" stopOpacity={0.1}/>
                </linearGradient>
              </defs>
            </AreaChart>
          </ResponsiveContainer>
        );

      case 'bar':
        return (
          <ResponsiveContainer width="100%" height={height}>
            <BarChart data={weeklyData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="day" stroke="#9CA3AF" fontSize={12} />
              <YAxis stroke="#9CA3AF" fontSize={12} />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="effect" radius={[4, 4, 0, 0]}>
                {weeklyData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={getBarColor(entry, index)} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        );

      case 'radar':
        return (
          <ResponsiveContainer width="100%" height={height}>
            <RadarChart data={strengthData}>
              <PolarGrid stroke="#374151" />
              <PolarAngleAxis dataKey="subject" tick={{ fontSize: 12, fill: '#9CA3AF' }} />
              <PolarRadiusAxis 
                angle={45} 
                domain={[0, 100]} 
                tick={{ fontSize: 10, fill: '#9CA3AF' }}
                tickCount={5}
              />
              <Radar 
                name="Strength" 
                dataKey="value" 
                stroke="#8B5CF6" 
                fill="#8B5CF6" 
                fillOpacity={0.3}
                strokeWidth={2}
                dot={{ fill: '#8B5CF6', strokeWidth: 2, r: 4 }}
              />
              <Tooltip content={<CustomTooltip />} />
            </RadarChart>
          </ResponsiveContainer>
        );

      case 'pie':
        return (
          <ResponsiveContainer width="100%" height={height}>
            <PieChart>
              <Pie
                data={pieData}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={100}
                paddingAngle={5}
                dataKey="value"
                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                labelLine={false}
              >
                {pieData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip 
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    const data = payload[0].payload;
                    return (
                      <div className="bg-gray-800 border border-gray-600 rounded-lg p-3 shadow-xl">
                        <p className="text-gray-300 text-sm font-semibold">{data.name} Pattern</p>
                        <p className="text-sm" style={{ color: data.color }}>
                          Strength: {(data.value * 100).toFixed(1)}%
                        </p>
                      </div>
                    );
                  }
                  return null;
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        );

      default:
        return null;
    }
  };

  const getChartTitle = () => {
    switch (chartType) {
      case 'line': return 'Weekly Pattern Effects';
      case 'area': return 'Monthly Pattern Effects';
      case 'bar': return 'Daily Performance Effects';
      case 'radar': return 'Pattern Strength Analysis';
      case 'pie': return 'Pattern Type Distribution';
      default: return 'Seasonal Analysis';
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={`bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6 ${className}`}
    >
      {/* Chart Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-100">
            {getChartTitle()}
          </h3>
          <p className="text-sm text-gray-400">
            {pattern.item.name} - {pattern.data_points_analyzed} data points
          </p>
        </div>
        
        <div className="flex items-center gap-2">
          <div className="text-xs text-gray-400">
            Signal Quality:
          </div>
          <div className={`px-2 py-1 rounded-full text-xs font-semibold ${
            pattern.signal_quality === 'excellent' ? 'text-green-400 bg-green-400/10' :
            pattern.signal_quality === 'good' ? 'text-blue-400 bg-blue-400/10' :
            pattern.signal_quality === 'fair' ? 'text-yellow-400 bg-yellow-400/10' :
            'text-red-400 bg-red-400/10'
          }`}>
            {pattern.signal_quality.toUpperCase()}
          </div>
        </div>
      </div>

      {/* Chart */}
      <div className="relative">
        {renderChart()}
      </div>

      {/* Chart Legend/Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4 pt-4 border-t border-gray-700/50">
        <div className="text-center">
          <div className="text-xs text-gray-400 mb-1">Overall Strength</div>
          <div className="text-sm font-semibold text-blue-400">
            {(pattern.overall_pattern_strength * 100).toFixed(1)}%
          </div>
        </div>
        <div className="text-center">
          <div className="text-xs text-gray-400 mb-1">Confidence</div>
          <div className="text-sm font-semibold text-green-400">
            {(pattern.forecast_confidence * 100).toFixed(1)}%
          </div>
        </div>
        <div className="text-center">
          <div className="text-xs text-gray-400 mb-1">Weekend Effect</div>
          <div className="text-sm font-semibold text-orange-400">
            {pattern.weekend_effect_pct.toFixed(1)}%
          </div>
        </div>
        <div className="text-center">
          <div className="text-xs text-gray-400 mb-1">Dominant Type</div>
          <div className="text-sm font-semibold text-purple-400 capitalize">
            {pattern.dominant_pattern_type}
          </div>
        </div>
      </div>
    </motion.div>
  );
}

export default SeasonalPatternChart;