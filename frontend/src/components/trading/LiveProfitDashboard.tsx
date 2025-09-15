import React, { useState, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  BanknotesIcon,
  ArrowTrendingUpIcon,
  ClockIcon,
  FireIcon,
  ChartBarIcon,
  CurrencyDollarIcon,
  SparklesIcon
} from '@heroicons/react/24/outline';
import type { DecantingOpportunity } from '../../types/tradingStrategies';

interface LiveProfitDashboardProps {
  opportunities: DecantingOpportunity[];
  currentCapital: number;
  onCapitalChange: (capital: number) => void;
}

interface ProfitSession {
  startTime: Date;
  totalProfit: number;
  tradesExecuted: number;
  bestOpportunity: string;
  hoursActive: number;
}

export const LiveProfitDashboard: React.FC<LiveProfitDashboardProps> = ({
  opportunities,
  currentCapital,
  onCapitalChange
}) => {
  const [session, setSession] = useState<ProfitSession>({
    startTime: new Date(),
    totalProfit: 0,
    tradesExecuted: 0,
    bestOpportunity: '',
    hoursActive: 0
  });
  
  const [animatedValues, setAnimatedValues] = useState({
    totalPotential: 0,
    hourlyRate: 0,
    bestProfit: 0,
    averageMargin: 0
  });

  // Calculate comprehensive profit metrics
  const profitMetrics = useMemo(() => {
    if (opportunities.length === 0) return null;

    // Find best opportunities
    const bestProfitOpp = opportunities.reduce((best, opp) => 
      opp.profit_per_conversion > best.profit_per_conversion ? opp : best
    );

    const bestHourlyOpp = opportunities.reduce((best, opp) => 
      opp.profit_per_hour > best.profit_per_hour ? opp : best
    );

    // Calculate total potential profits
    const totalPotentialProfit = opportunities.reduce((sum, opp) => {
      const maxConversions = Math.floor(currentCapital / opp.from_dose_price);
      return sum + (maxConversions * opp.profit_per_conversion);
    }, 0);

    // Calculate weighted average hourly rate
    const totalHourlyPotential = opportunities.reduce((sum, opp) => {
      const maxConversions = Math.floor(currentCapital / opp.from_dose_price);
      const conversionsPerHour = Math.min(360, maxConversions); // 10 seconds per conversion
      return sum + (conversionsPerHour * opp.profit_per_conversion);
    }, 0);

    // Calculate average profit margin
    const avgMargin = opportunities.reduce((sum, opp) => {
      const margin = (opp.profit_per_conversion / opp.from_dose_price) * 100;
      return sum + margin;
    }, 0) / opportunities.length;

    // Top 5 opportunities by profit
    const topOpportunities = [...opportunities]
      .sort((a, b) => b.profit_per_conversion - a.profit_per_conversion)
      .slice(0, 5);

    return {
      totalPotentialProfit,
      hourlyRate: totalHourlyPotential,
      bestProfit: bestProfitOpp.profit_per_conversion,
      averageMargin: avgMargin,
      bestProfitOpp,
      bestHourlyOpp,
      topOpportunities,
      capitalEfficiency: (totalPotentialProfit / currentCapital) * 100
    };
  }, [opportunities, currentCapital]);

  // Animate values when they change
  useEffect(() => {
    if (!profitMetrics) return;

    const animateValue = (start: number, end: number, setter: (value: number) => void) => {
      const duration = 1500;
      const startTime = Date.now();
      
      const animate = () => {
        const elapsed = Date.now() - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        // Easing function for smooth animation
        const easeOut = 1 - Math.pow(1 - progress, 3);
        const currentValue = start + (end - start) * easeOut;
        
        setter(currentValue);
        
        if (progress < 1) {
          requestAnimationFrame(animate);
        }
      };
      
      requestAnimationFrame(animate);
    };

    // Animate all values
    animateValue(animatedValues.totalPotential, profitMetrics.totalPotentialProfit, 
      (value) => setAnimatedValues(prev => ({ ...prev, totalPotential: value })));
    
    animateValue(animatedValues.hourlyRate, profitMetrics.hourlyRate, 
      (value) => setAnimatedValues(prev => ({ ...prev, hourlyRate: value })));
    
    animateValue(animatedValues.bestProfit, profitMetrics.bestProfit, 
      (value) => setAnimatedValues(prev => ({ ...prev, bestProfit: value })));
    
    animateValue(animatedValues.averageMargin, profitMetrics.averageMargin, 
      (value) => setAnimatedValues(prev => ({ ...prev, averageMargin: value })));
    
  }, [profitMetrics]);

  // Update session timer
  useEffect(() => {
    const interval = setInterval(() => {
      setSession(prev => ({
        ...prev,
        hoursActive: (Date.now() - prev.startTime.getTime()) / (1000 * 60 * 60)
      }));
    }, 30000); // Update every 30 seconds

    return () => clearInterval(interval);
  }, []);

  const formatGP = (amount: number) => {
    if (amount >= 1000000000) return `${(amount / 1000000000).toFixed(1)}B GP`;
    if (amount >= 1000000) return `${(amount / 1000000).toFixed(1)}M GP`;
    if (amount >= 1000) return `${(amount / 1000).toFixed(1)}K GP`;
    return `${Math.round(amount)} GP`;
  };

  const formatNumber = (num: number) => {
    return new Intl.NumberFormat('en-US').format(Math.round(num));
  };

  if (!profitMetrics) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-gradient-to-r from-emerald-900/20 via-green-900/20 to-emerald-900/20 border border-green-500/30 rounded-2xl p-6 mb-6"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <motion.div 
            className="p-3 bg-green-500/20 rounded-xl"
            animate={{ rotate: [0, 360] }}
            transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
          >
            <BanknotesIcon className="w-8 h-8 text-green-400" />
          </motion.div>
          <div>
            <h2 className="text-2xl font-bold text-white flex items-center gap-2">
              Live Profit Dashboard
              <motion.div
                animate={{ scale: [1, 1.2, 1] }}
                transition={{ duration: 2, repeat: Infinity }}
                className="w-3 h-3 bg-green-400 rounded-full"
              />
            </h2>
            <p className="text-green-400">Real-time market analysis & profit tracking</p>
          </div>
        </div>
        
        <div className="text-right">
          <div className="text-sm text-gray-400">Session Active</div>
          <div className="text-lg font-bold text-green-400">
            {session.hoursActive < 1 ? 
              `${Math.round(session.hoursActive * 60)}m` : 
              `${session.hoursActive.toFixed(1)}h`
            }
          </div>
        </div>
      </div>

      {/* Main Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
        {/* Total Potential Profit */}
        <motion.div 
          className="bg-gray-900/50 backdrop-blur-sm border border-green-500/20 rounded-xl p-6"
          whileHover={{ scale: 1.02 }}
        >
          <div className="flex items-center gap-3 mb-3">
            <ArrowTrendingUpIcon className="w-6 h-6 text-green-400" />
            <span className="text-sm font-medium text-gray-400">Total Potential</span>
          </div>
          <motion.div 
            className="text-3xl font-bold text-green-400"
            animate={{ textShadow: "0 0 20px rgba(34, 197, 94, 0.3)" }}
          >
            {formatGP(animatedValues.totalPotential)}
          </motion.div>
          <div className="text-xs text-gray-500 mt-1">With current capital</div>
        </motion.div>

        {/* Hourly Rate */}
        <motion.div 
          className="bg-gray-900/50 backdrop-blur-sm border border-blue-500/20 rounded-xl p-6"
          whileHover={{ scale: 1.02 }}
        >
          <div className="flex items-center gap-3 mb-3">
            <ClockIcon className="w-6 h-6 text-blue-400" />
            <span className="text-sm font-medium text-gray-400">Hourly Rate</span>
          </div>
          <motion.div 
            className="text-3xl font-bold text-blue-400"
            animate={{ textShadow: "0 0 20px rgba(59, 130, 246, 0.3)" }}
          >
            {formatGP(animatedValues.hourlyRate)}
          </motion.div>
          <div className="text-xs text-gray-500 mt-1">Peak theoretical</div>
        </motion.div>

        {/* Best Single Profit */}
        <motion.div 
          className="bg-gray-900/50 backdrop-blur-sm border border-purple-500/20 rounded-xl p-6"
          whileHover={{ scale: 1.02 }}
        >
          <div className="flex items-center gap-3 mb-3">
            <FireIcon className="w-6 h-6 text-purple-400" />
            <span className="text-sm font-medium text-gray-400">Best Single</span>
          </div>
          <motion.div 
            className="text-3xl font-bold text-purple-400"
            animate={{ textShadow: "0 0 20px rgba(168, 85, 247, 0.3)" }}
          >
            {formatGP(animatedValues.bestProfit)}
          </motion.div>
          <div className="text-xs text-gray-500 mt-1 truncate">
            {profitMetrics.bestProfitOpp.item_name}
          </div>
        </motion.div>

        {/* Average Margin */}
        <motion.div 
          className="bg-gray-900/50 backdrop-blur-sm border border-orange-500/20 rounded-xl p-6"
          whileHover={{ scale: 1.02 }}
        >
          <div className="flex items-center gap-3 mb-3">
            <ChartBarIcon className="w-6 h-6 text-orange-400" />
            <span className="text-sm font-medium text-gray-400">Avg Margin</span>
          </div>
          <motion.div 
            className="text-3xl font-bold text-orange-400"
            animate={{ textShadow: "0 0 20px rgba(251, 146, 60, 0.3)" }}
          >
            {animatedValues.averageMargin.toFixed(1)}%
          </motion.div>
          <div className="text-xs text-gray-500 mt-1">Profit margin</div>
        </motion.div>
      </div>

      {/* Capital Adjustment & Quick Stats */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Capital Slider */}
        <div className="bg-gray-900/30 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <span className="text-lg font-semibold text-white">Available Capital</span>
            <motion.span 
              className="text-2xl font-bold text-green-400"
              key={currentCapital}
              initial={{ scale: 1.2 }}
              animate={{ scale: 1 }}
            >
              {formatGP(currentCapital)}
            </motion.span>
          </div>
          <input
            type="range"
            min="100000"
            max="100000000"
            step="100000"
            value={currentCapital}
            onChange={(e) => onCapitalChange(parseInt(e.target.value))}
            className="w-full h-3 bg-gray-700 rounded-lg appearance-none cursor-pointer slider"
          />
          <div className="flex justify-between text-xs text-gray-500 mt-2">
            <span>100K</span>
            <span className="text-center">Capital Efficiency: {profitMetrics.capitalEfficiency.toFixed(1)}%</span>
            <span>100M</span>
          </div>
        </div>

        {/* Top Opportunities Preview */}
        <div className="bg-gray-900/30 rounded-xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <SparklesIcon className="w-5 h-5 text-yellow-400" />
            <span className="text-lg font-semibold text-white">Top Opportunities</span>
          </div>
          <div className="space-y-2">
            {profitMetrics.topOpportunities.slice(0, 3).map((opp, index) => (
              <motion.div
                key={opp.item_name}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.1 }}
                className="flex items-center justify-between p-2 bg-gray-800/50 rounded-lg"
              >
                <div className="flex items-center gap-2">
                  <span className="w-6 h-6 bg-green-500/20 rounded-full flex items-center justify-center text-xs font-bold text-green-400">
                    {index + 1}
                  </span>
                  <span className="text-sm text-white font-medium truncate">
                    {opp.item_name}
                  </span>
                </div>
                <span className="text-sm font-bold text-green-400">
                  {formatGP(opp.profit_per_conversion)}
                </span>
              </motion.div>
            ))}
          </div>
        </div>
      </div>

      {/* Session Stats Footer */}
      <motion.div 
        className="mt-6 p-4 bg-gradient-to-r from-gray-800/50 to-gray-900/50 rounded-xl border-t border-green-500/20"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1 }}
      >
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
          <div>
            <div className="text-2xl font-bold text-blue-400">{session.tradesExecuted}</div>
            <div className="text-xs text-gray-400">Trades Executed</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-green-400">{formatGP(session.totalProfit)}</div>
            <div className="text-xs text-gray-400">Session Profit</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-purple-400">{opportunities.length}</div>
            <div className="text-xs text-gray-400">Active Opportunities</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-orange-400">
              {session.totalProfit > 0 ? formatGP(session.totalProfit / Math.max(session.hoursActive, 0.1)) : '0 GP'}
            </div>
            <div className="text-xs text-gray-400">Actual GP/Hour</div>
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
};

export default LiveProfitDashboard;