import React, { useMemo } from 'react';
import { motion } from 'framer-motion';
import { Clock, Calendar, Sun, Moon, TrendingUp, Activity } from 'lucide-react';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import type { Item } from '../../types';

interface TimeAnalysisProps {
  items: Item[];
}

interface TimeSlot {
  hour: number;
  label: string;
  volume: number;
  profitOpportunity: number;
  intensity: number;
  recommendation: 'poor' | 'fair' | 'good' | 'excellent';
}

export const TimeAnalysis: React.FC<TimeAnalysisProps> = ({ items }) => {
  const formatGP = (amount: number) => {
    if (amount >= 1000000) return `${(amount / 1000000).toFixed(1)}M`;
    if (amount >= 1000) return `${(amount / 1000).toFixed(1)}K`;
    return Math.round(amount).toString();
  };

  // Generate time-based analysis data
  const timeSlots = useMemo(() => {
    const slots: TimeSlot[] = [];
    
    for (let hour = 0; hour < 24; hour++) {
      // Simulate trading patterns based on typical OSRS activity
      const baseVolume = items.reduce((sum, item) => sum + (item.profit_calc?.daily_volume || 0), 0) / 24;
      
      // Peak hours: 12-16 (lunch) and 19-23 (evening)
      let volumeMultiplier = 1;
      if (hour >= 12 && hour <= 16) volumeMultiplier = 1.5;
      else if (hour >= 19 && hour <= 23) volumeMultiplier = 1.8;
      else if (hour >= 6 && hour <= 11) volumeMultiplier = 1.2;
      else if (hour >= 0 && hour <= 5) volumeMultiplier = 0.6;

      // Add some random variation
      volumeMultiplier *= (0.8 + Math.random() * 0.4);

      const volume = baseVolume * volumeMultiplier;
      
      // Calculate profit opportunity (higher volume = more opportunities)
      const avgProfit = items.reduce((sum, item) => sum + (item.current_profit || 0), 0) / items.length || 0;
      const profitOpportunity = avgProfit * volumeMultiplier;
      
      // Calculate intensity (0-100)
      const intensity = Math.min(100, volumeMultiplier * 50);
      
      // Determine recommendation
      let recommendation: TimeSlot['recommendation'];
      if (intensity > 75) recommendation = 'excellent';
      else if (intensity > 60) recommendation = 'good';
      else if (intensity > 40) recommendation = 'fair';
      else recommendation = 'poor';

      slots.push({
        hour,
        label: `${hour.toString().padStart(2, '0')}:00`,
        volume,
        profitOpportunity,
        intensity,
        recommendation
      });
    }

    return slots;
  }, [items]);

  const peakHours = useMemo(() => {
    return timeSlots
      .sort((a, b) => b.intensity - a.intensity)
      .slice(0, 6);
  }, [timeSlots]);

  const bestTradingWindows = useMemo(() => {
    const windows = [];
    
    // Morning window (6-12)
    const morningSlots = timeSlots.filter(slot => slot.hour >= 6 && slot.hour <= 12);
    const morningAvg = morningSlots.reduce((sum, slot) => sum + slot.intensity, 0) / morningSlots.length;
    
    // Afternoon window (12-18)
    const afternoonSlots = timeSlots.filter(slot => slot.hour >= 12 && slot.hour <= 18);
    const afternoonAvg = afternoonSlots.reduce((sum, slot) => sum + slot.intensity, 0) / afternoonSlots.length;
    
    // Evening window (18-24)
    const eveningSlots = timeSlots.filter(slot => slot.hour >= 18 && slot.hour < 24);
    const eveningAvg = eveningSlots.reduce((sum, slot) => sum + slot.intensity, 0) / eveningSlots.length;
    
    // Night window (0-6)
    const nightSlots = timeSlots.filter(slot => slot.hour >= 0 && slot.hour < 6);
    const nightAvg = nightSlots.reduce((sum, slot) => sum + slot.intensity, 0) / nightSlots.length;

    return [
      { name: 'Morning', period: '6AM - 12PM', average: morningAvg, icon: Sun },
      { name: 'Afternoon', period: '12PM - 6PM', average: afternoonAvg, icon: Sun },
      { name: 'Evening', period: '6PM - 12AM', average: eveningAvg, icon: Moon },
      { name: 'Night', period: '12AM - 6AM', average: nightAvg, icon: Moon }
    ].sort((a, b) => b.average - a.average);
  }, [timeSlots]);

  const getIntensityColor = (intensity: number) => {
    if (intensity > 75) return { bg: 'bg-green-500', text: 'text-green-400' };
    if (intensity > 60) return { bg: 'bg-blue-500', text: 'text-blue-400' };
    if (intensity > 40) return { bg: 'bg-yellow-500', text: 'text-yellow-400' };
    return { bg: 'bg-red-500', text: 'text-red-400' };
  };

  const getRecommendationBadge = (recommendation: TimeSlot['recommendation']) => {
    switch (recommendation) {
      case 'excellent': return { variant: 'success' as const, text: 'Prime Time' };
      case 'good': return { variant: 'warning' as const, text: 'Good' };
      case 'fair': return { variant: 'secondary' as const, text: 'Fair' };
      case 'poor': return { variant: 'danger' as const, text: 'Slow' };
    }
  };

  return (
    <Card className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Clock className="w-5 h-5 text-accent-400" />
          <h3 className="text-lg font-semibold text-white">Trading Time Analysis</h3>
        </div>
        <Badge variant="secondary">
          24h Pattern
        </Badge>
      </div>

      {/* Time Chart */}
      <div className="space-y-4">
        <div className="text-sm text-gray-400 text-center">
          Optimal Trading Hours (Higher intensity = Better opportunities)
        </div>
        
        <div className="bg-white/5 rounded-lg p-4">
          <div className="grid grid-cols-12 gap-1">
            {timeSlots.map((slot, index) => {
              const colors = getIntensityColor(slot.intensity);
              return (
                <motion.div
                  key={slot.hour}
                  initial={{ height: 0 }}
                  animate={{ height: 'auto' }}
                  transition={{ delay: 0.05 * index }}
                  className="group relative cursor-pointer"
                >
                  <div
                    className="rounded transition-all hover:scale-110"
                    style={{
                      height: `${Math.max(slot.intensity * 0.8, 8)}px`,
                      backgroundColor: slot.intensity > 75 ? 'rgb(34 197 94)' :
                                     slot.intensity > 60 ? 'rgb(59 130 246)' :
                                     slot.intensity > 40 ? 'rgb(245 158 11)' : 'rgb(239 68 68)'
                    }}
                  />
                  <div className="text-xs text-gray-400 text-center mt-1">
                    {slot.hour}
                  </div>

                  {/* Tooltip */}
                  <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 opacity-0 group-hover:opacity-100 transition-opacity z-10">
                    <div className="bg-gray-800 text-white text-xs rounded py-2 px-3 whitespace-nowrap">
                      <div className="font-medium mb-1">{slot.label}</div>
                      <div>Volume: {formatGP(slot.volume)}</div>
                      <div>Profit Opp: {formatGP(slot.profitOpportunity)} GP</div>
                      <div>Intensity: {slot.intensity.toFixed(0)}%</div>
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </div>
          
          {/* Time labels */}
          <div className="grid grid-cols-6 gap-4 mt-2 text-xs text-gray-400 text-center">
            <div>0:00</div>
            <div>4:00</div>
            <div>8:00</div>
            <div>12:00</div>
            <div>16:00</div>
            <div>20:00</div>
          </div>
        </div>
      </div>

      {/* Peak Hours */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-green-400" />
            <span className="text-sm font-medium text-white">Peak Trading Hours</span>
          </div>
          <div className="space-y-2">
            {peakHours.map((slot, index) => (
              <motion.div
                key={slot.hour}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.1 * index }}
                className="flex items-center justify-between p-3 bg-white/5 rounded-lg"
              >
                <div className="flex items-center gap-3">
                  <div className="text-sm font-medium text-white">
                    {slot.label}
                  </div>
                  <Badge variant={getRecommendationBadge(slot.recommendation).variant} size="sm">
                    {getRecommendationBadge(slot.recommendation).text}
                  </Badge>
                </div>
                <div className="text-right">
                  <div className={`text-sm font-bold ${getIntensityColor(slot.intensity).text}`}>
                    {slot.intensity.toFixed(0)}%
                  </div>
                  <div className="text-xs text-gray-400">
                    {formatGP(slot.volume)} vol
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>

        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-blue-400" />
            <span className="text-sm font-medium text-white">Time Windows</span>
          </div>
          <div className="space-y-2">
            {bestTradingWindows.map((window, index) => {
              const Icon = window.icon;
              const colors = getIntensityColor(window.average);
              return (
                <motion.div
                  key={window.name}
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.1 * index }}
                  className="flex items-center justify-between p-3 bg-white/5 rounded-lg"
                >
                  <div className="flex items-center gap-3">
                    <Icon className="w-4 h-4 text-gray-400" />
                    <div>
                      <div className="text-sm font-medium text-white">
                        {window.name}
                      </div>
                      <div className="text-xs text-gray-400">
                        {window.period}
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className={`text-sm font-bold ${colors.text}`}>
                      {window.average.toFixed(0)}%
                    </div>
                    <div className="text-xs text-gray-400">avg intensity</div>
                  </div>
                </motion.div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Summary & Recommendations */}
      <div className="bg-accent-500/10 border border-accent-500/20 rounded-lg p-4">
        <div className="flex items-start gap-2">
          <Activity className="w-4 h-4 text-accent-400 mt-0.5" />
          <div>
            <div className="text-sm font-medium text-accent-400 mb-2">Trading Recommendations</div>
            <div className="text-xs text-gray-300 space-y-1">
              <div>• Best overall time window: <span className="text-accent-400 font-medium">
                {bestTradingWindows[0]?.name} ({bestTradingWindows[0]?.period})
              </span></div>
              <div>• Peak single hour: <span className="text-accent-400 font-medium">
                {peakHours[0]?.label} with {peakHours[0]?.intensity.toFixed(0)}% intensity
              </span></div>
              <div>• Recommended strategy: Focus trading during evening hours (6PM-12AM) for highest volume</div>
              <div>• Avoid: Early morning hours (12AM-6AM) typically show lowest activity</div>
            </div>
          </div>
        </div>
      </div>

      {/* Statistics */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-3 text-center">
          <div className="text-sm text-gray-400 mb-1">Peak Hour</div>
          <div className="text-lg font-bold text-blue-400">
            {peakHours[0]?.label}
          </div>
        </div>

        <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-3 text-center">
          <div className="text-sm text-gray-400 mb-1">Best Window</div>
          <div className="text-lg font-bold text-green-400">
            {bestTradingWindows[0]?.name}
          </div>
        </div>

        <div className="bg-purple-500/10 border border-purple-500/20 rounded-lg p-3 text-center">
          <div className="text-sm text-gray-400 mb-1">Avg Daily Vol</div>
          <div className="text-lg font-bold text-purple-400">
            {formatGP(timeSlots.reduce((sum, slot) => sum + slot.volume, 0))}
          </div>
        </div>

        <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-3 text-center">
          <div className="text-sm text-gray-400 mb-1">Prime Hours</div>
          <div className="text-lg font-bold text-yellow-400">
            {timeSlots.filter(slot => slot.recommendation === 'excellent').length}
          </div>
        </div>
      </div>
    </Card>
  );
};