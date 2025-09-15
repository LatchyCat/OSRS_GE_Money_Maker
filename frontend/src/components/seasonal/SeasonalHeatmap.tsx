import React, { useMemo } from 'react';
import { motion } from 'framer-motion';
import type { SeasonalPattern } from '../../types/seasonal';

interface SeasonalHeatmapProps {
  patterns: SeasonalPattern[];
  type: 'monthly' | 'weekly' | 'hourly';
  metric: 'strength' | 'volume' | 'profit';
  className?: string;
}

interface HeatmapCell {
  x: number;
  y: number;
  value: number;
  label: string;
  count: number;
  intensity: number;
}

export function SeasonalHeatmap({ patterns, type, metric, className = '' }: SeasonalHeatmapProps) {
  
  const heatmapData = useMemo(() => {
    if (type === 'monthly') {
      const months = [
        'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
        'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
      ];
      
      const data: HeatmapCell[] = [];
      const monthlyData: Record<string, { value: number; count: number }> = {};
      
      // Aggregate data by month
      patterns.forEach(pattern => {
        if (pattern.monthly_effects) {
          Object.entries(pattern.monthly_effects).forEach(([month, effect]) => {
            const monthKey = month.substring(0, 3);
            if (!monthlyData[monthKey]) {
              monthlyData[monthKey] = { value: 0, count: 0 };
            }
            
            let cellValue = 0;
            switch (metric) {
              case 'strength':
                cellValue = pattern.monthly_pattern_strength * 100;
                break;
              case 'volume':
                cellValue = Math.abs(effect as number) * 100;
                break;
              case 'profit':
                cellValue = pattern.item.profit_margin * 100;
                break;
            }
            
            monthlyData[monthKey].value += cellValue;
            monthlyData[monthKey].count++;
          });
        }
      });
      
      // Create heatmap cells
      months.forEach((month, index) => {
        const monthData = monthlyData[month] || { value: 0, count: 0 };
        const avgValue = monthData.count > 0 ? monthData.value / monthData.count : 0;
        
        data.push({
          x: index,
          y: 0,
          value: avgValue,
          label: month,
          count: monthData.count,
          intensity: Math.min(avgValue / 50, 1) // Normalize to 0-1
        });
      });
      
      return { data, rows: 1, cols: 12 };
    }
    
    if (type === 'weekly') {
      const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
      
      const data: HeatmapCell[] = [];
      const dailyData: Record<string, { value: number; count: number }> = {};
      
      // Aggregate data by day
      patterns.forEach(pattern => {
        if (pattern.day_of_week_effects) {
          Object.entries(pattern.day_of_week_effects).forEach(([day, effect]) => {
            const dayKey = day.substring(0, 3);
            if (!dailyData[dayKey]) {
              dailyData[dayKey] = { value: 0, count: 0 };
            }
            
            let cellValue = 0;
            switch (metric) {
              case 'strength':
                cellValue = pattern.weekly_pattern_strength * 100;
                break;
              case 'volume':
                cellValue = Math.abs(effect as number) * 100;
                break;
              case 'profit':
                cellValue = pattern.item.profit_margin * 100;
                break;
            }
            
            dailyData[dayKey].value += cellValue;
            dailyData[dayKey].count++;
          });
        }
      });
      
      // Create heatmap cells
      days.forEach((day, index) => {
        const dayData = dailyData[day] || { value: 0, count: 0 };
        const avgValue = dayData.count > 0 ? dayData.value / dayData.count : 0;
        
        data.push({
          x: index,
          y: 0,
          value: avgValue,
          label: day,
          count: dayData.count,
          intensity: Math.min(avgValue / 30, 1) // Normalize to 0-1
        });
      });
      
      return { data, rows: 1, cols: 7 };
    }
    
    if (type === 'hourly') {
      // Create 24-hour heatmap (simulate data since we don't have hourly effects)
      const data: HeatmapCell[] = [];
      const hours = Array.from({ length: 24 }, (_, i) => i);
      
      hours.forEach((hour, index) => {
        // Simulate hourly patterns based on typical trading patterns
        let simulatedValue = 0;
        if (hour >= 12 && hour <= 18) { // Peak trading hours
          simulatedValue = 60 + Math.random() * 30;
        } else if (hour >= 8 && hour <= 11) { // Morning activity
          simulatedValue = 40 + Math.random() * 20;
        } else if (hour >= 19 && hour <= 23) { // Evening activity
          simulatedValue = 30 + Math.random() * 20;
        } else { // Night/early morning
          simulatedValue = 10 + Math.random() * 15;
        }
        
        data.push({
          x: index % 12,
          y: Math.floor(index / 12),
          value: simulatedValue,
          label: `${hour.toString().padStart(2, '0')}:00`,
          count: patterns.length,
          intensity: Math.min(simulatedValue / 90, 1)
        });
      });
      
      return { data, rows: 2, cols: 12 };
    }
    
    return { data: [], rows: 0, cols: 0 };
  }, [patterns, type, metric]);

  const getIntensityColor = (intensity: number) => {
    if (intensity === 0) return 'bg-gray-700/30';
    
    const hue = metric === 'profit' ? 120 : metric === 'strength' ? 240 : 200; // Green for profit, blue for strength, cyan for volume
    const saturation = 70;
    const lightness = 30 + (intensity * 40); // 30% to 70%
    
    return `hsl(${hue}, ${saturation}%, ${lightness}%)`;
  };

  const getMetricLabel = () => {
    switch (metric) {
      case 'strength': return 'Pattern Strength (%)';
      case 'volume': return 'Volume Impact (%)';
      case 'profit': return 'Profit Margin (%)';
    }
  };

  const getTypeLabel = () => {
    switch (type) {
      case 'monthly': return 'Monthly Patterns';
      case 'weekly': return 'Weekly Patterns';
      case 'hourly': return 'Hourly Activity (Simulated)';
    }
  };

  if (!patterns.length) {
    return (
      <div className={`bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6 ${className}`}>
        <div className="text-center py-8">
          <div className="text-gray-400 mb-2">No pattern data available</div>
          <div className="text-sm text-gray-500">Heatmap will appear once seasonal patterns are detected</div>
        </div>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className={`bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6 ${className}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold text-gray-100">
            {getTypeLabel()}
          </h3>
          <p className="text-sm text-gray-400">
            {getMetricLabel()} • {patterns.length} patterns analyzed
          </p>
        </div>
        
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 text-xs text-gray-400">
            <span>Low</span>
            <div className="flex gap-1">
              {[0.2, 0.4, 0.6, 0.8, 1.0].map((intensity, index) => (
                <div
                  key={index}
                  className="w-4 h-4 rounded"
                  style={{ backgroundColor: getIntensityColor(intensity) }}
                />
              ))}
            </div>
            <span>High</span>
          </div>
        </div>
      </div>

      {/* Heatmap Grid */}
      <div className="relative">
        <div 
          className="grid gap-1"
          style={{ 
            gridTemplateColumns: `repeat(${heatmapData.cols}, minmax(0, 1fr))`,
            gridTemplateRows: `repeat(${heatmapData.rows}, minmax(0, 1fr))`
          }}
        >
          {heatmapData.data.map((cell, index) => (
            <motion.div
              key={index}
              whileHover={{ scale: 1.1, zIndex: 10 }}
              className="relative aspect-square rounded-lg cursor-pointer transition-all duration-200 group"
              style={{ backgroundColor: getIntensityColor(cell.intensity) }}
            >
              {/* Cell Label */}
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-xs font-medium text-gray-200 opacity-80">
                  {cell.label}
                </span>
              </div>

              {/* Tooltip on Hover */}
              <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 border border-gray-600 rounded-lg shadow-xl opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none z-20 whitespace-nowrap">
                <div className="text-sm font-semibold text-gray-100">{cell.label}</div>
                <div className="text-xs text-gray-300">
                  {getMetricLabel().split(' (')[0]}: {cell.value.toFixed(1)}%
                </div>
                <div className="text-xs text-gray-400">
                  Patterns: {cell.count}
                </div>
                {/* Arrow */}
                <div className="absolute top-full left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-900"></div>
              </div>
            </motion.div>
          ))}
        </div>

        {/* Additional labels for hourly view */}
        {type === 'hourly' && (
          <div className="mt-4 flex justify-between text-xs text-gray-400">
            <span>12 AM - 11 AM</span>
            <span>12 PM - 11 PM</span>
          </div>
        )}
      </div>

      {/* Stats Summary */}
      <div className="mt-6 pt-4 border-t border-gray-700/50">
        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <div className="text-xs text-gray-400 mb-1">Average {getMetricLabel().split(' (')[0]}</div>
            <div className="text-sm font-semibold text-blue-400">
              {heatmapData.data.length > 0 
                ? (heatmapData.data.reduce((sum, cell) => sum + cell.value, 0) / heatmapData.data.length).toFixed(1) + '%'
                : 'N/A'
              }
            </div>
          </div>
          <div>
            <div className="text-xs text-gray-400 mb-1">Peak Period</div>
            <div className="text-sm font-semibold text-green-400">
              {heatmapData.data.length > 0
                ? heatmapData.data.reduce((max, cell) => cell.value > max.value ? cell : max, heatmapData.data[0]).label
                : 'N/A'
              }
            </div>
          </div>
          <div>
            <div className="text-xs text-gray-400 mb-1">Total Patterns</div>
            <div className="text-sm font-semibold text-purple-400">
              {patterns.length}
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}

export default SeasonalHeatmap;