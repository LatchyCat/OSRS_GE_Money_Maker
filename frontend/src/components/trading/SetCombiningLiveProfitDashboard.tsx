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
import type { SetCombiningOpportunity } from '../../types/tradingStrategies';

interface SetCombiningLiveProfitDashboardProps {
  opportunities: SetCombiningOpportunity[];
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

export const SetCombiningLiveProfitDashboard: React.FC<SetCombiningLiveProfitDashboardProps> = ({
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

  // Calculate comprehensive profit metrics for set combining
  const profitMetrics = useMemo(() => {
    if (opportunities.length === 0) return null;

    // Find best opportunities
    const bestProfitOpp = opportunities.reduce((best, opp) => 
      (opp.lazy_tax_profit || 0) > (best.lazy_tax_profit || 0) ? opp : best
    );

    // Calculate profit per hour for each opportunity
    const opportunitiesWithHourly = opportunities.map(opp => {
      const setsPerHour = Math.min(12, opp.set_volume || 6); // Max 12 sets per hour, default 6
      const profitPerHour = setsPerHour * (opp.lazy_tax_profit || 0);
      return { ...opp, profitPerHour };
    });

    const bestHourlyOpp = opportunitiesWithHourly.reduce((best, opp) => 
      opp.profitPerHour > best.profitPerHour ? opp : best
    );

    // Calculate total potential profits based on capital constraints
    const totalPotentialProfit = opportunities.reduce((sum, opp) => {
      const costPerSet = opp.individual_pieces_total_cost || opp.complete_set_price || 0;
      if (costPerSet === 0) return sum;
      
      const maxSets = Math.floor(currentCapital / costPerSet);
      return sum + (maxSets * (opp.lazy_tax_profit || 0));
    }, 0);

    // Calculate weighted average hourly rate
    const totalHourlyPotential = opportunities.reduce((sum, opp) => {
      const costPerSet = opp.individual_pieces_total_cost || opp.complete_set_price || 0;
      if (costPerSet === 0) return sum;
      
      const maxSets = Math.floor(currentCapital / costPerSet);
      const setsPerHour = Math.min(12, opp.set_volume || 6);
      const actualSetsPerHour = Math.min(setsPerHour, maxSets); // Can't trade more than capital allows
      
      return sum + (actualSetsPerHour * (opp.lazy_tax_profit || 0));
    }, 0);

    // Calculate average profit margin
    const avgMargin = opportunities.reduce((sum, opp) => {
      const costPerSet = opp.individual_pieces_total_cost || opp.complete_set_price || 1;
      const margin = ((opp.lazy_tax_profit || 0) / costPerSet) * 100;
      return sum + (isFinite(margin) ? margin : 0);
    }, 0) / opportunities.length;

    // Top 5 opportunities by profit
    const topOpportunities = [...opportunities]
      .sort((a, b) => (b.lazy_tax_profit || 0) - (a.lazy_tax_profit || 0))
      .slice(0, 5);

    return {
      totalPotentialProfit,
      hourlyRate: totalHourlyPotential,
      bestProfit: bestProfitOpp.lazy_tax_profit || 0,
      averageMargin: isFinite(avgMargin) ? avgMargin : 0,
      bestProfitOpp,
      bestHourlyOpp,
      topOpportunities,
      capitalEfficiency: currentCapital > 0 ? (totalPotentialProfit / currentCapital) * 100 : 0
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
    const timer = setInterval(() => {
      const now = new Date();
      const hoursActive = (now.getTime() - session.startTime.getTime()) / (1000 * 60 * 60);
      setSession(prev => ({ ...prev, hoursActive }));
    }, 60000); // Update every minute

    return () => clearInterval(timer);
  }, [session.startTime]);

  const formatGP = (value: number) => {
    if (value >= 1000000000) {
      return `${(value / 1000000000).toFixed(1)}B`;
    } else if (value >= 1000000) {
      return `${(value / 1000000).toFixed(1)}M`;
    } else if (value >= 1000) {
      return `${(value / 1000).toFixed(1)}K`;
    }
    return Math.round(value).toString();
  };

  const formatNumber = (value: number) => {
    return new Intl.NumberFormat().format(Math.round(value));
  };

  const formatPercentage = (value: number) => {
    return isFinite(value) ? `${value.toFixed(1)}%` : '0.0%';
  };

  if (!profitMetrics) {
    return (
      <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
        <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
          <SparklesIcon className="w-6 h-6 text-yellow-400" />
          Live Profit Dashboard
        </h2>
        <div className="text-slate-400 text-center py-8">
          No set combining opportunities available
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gradient-to-br from-slate-800 via-slate-800 to-slate-900 rounded-xl p-6 border border-slate-700/50 shadow-2xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <SparklesIcon className="w-6 h-6 text-yellow-400" />
            Live Profit Dashboard
          </h2>
          <p className="text-slate-400 text-sm">Real-time market analysis & profit tracking</p>
        </div>
        
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-sm">
            <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
            <span className="text-slate-300">Session Active</span>
          </div>
          <div className="text-slate-400 text-sm">
            {Math.floor(session.hoursActive)}h {Math.floor((session.hoursActive % 1) * 60)}m
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <motion.div 
          className="bg-slate-700/50 rounded-lg p-4 border border-slate-600/50"
          whileHover={{ scale: 1.02 }}
        >
          <div className="flex items-center gap-3 mb-2">
            <BanknotesIcon className="w-5 h-5 text-green-400" />
            <span className="text-slate-300 text-sm">Total Potential</span>
          </div>
          <div className="text-2xl font-bold text-white">
            {formatGP(animatedValues.totalPotential)} GP
          </div>
          <div className="text-xs text-slate-400">With current capital</div>
        </motion.div>

        <motion.div 
          className="bg-slate-700/50 rounded-lg p-4 border border-slate-600/50"
          whileHover={{ scale: 1.02 }}
        >
          <div className="flex items-center gap-3 mb-2">
            <ClockIcon className="w-5 h-5 text-blue-400" />
            <span className="text-slate-300 text-sm">Hourly Rate</span>
          </div>
          <div className="text-2xl font-bold text-white">
            {formatGP(animatedValues.hourlyRate)} GP
          </div>
          <div className="text-xs text-slate-400">Peak theoretical</div>
        </motion.div>

        <motion.div 
          className="bg-slate-700/50 rounded-lg p-4 border border-slate-600/50"
          whileHover={{ scale: 1.02 }}
        >
          <div className="flex items-center gap-3 mb-2">
            <FireIcon className="w-5 h-5 text-orange-400" />
            <span className="text-slate-300 text-sm">Best Single</span>
          </div>
          <div className="text-2xl font-bold text-white">
            {formatGP(animatedValues.bestProfit)} GP
          </div>
          <div className="text-xs text-slate-400">{profitMetrics.bestProfitOpp.set_name}</div>
        </motion.div>

        <motion.div 
          className="bg-slate-700/50 rounded-lg p-4 border border-slate-600/50"
          whileHover={{ scale: 1.02 }}
        >
          <div className="flex items-center gap-3 mb-2">
            <ArrowTrendingUpIcon className="w-5 h-5 text-purple-400" />
            <span className="text-slate-300 text-sm">Avg Margin</span>
          </div>
          <div className="text-2xl font-bold text-white">
            {formatPercentage(animatedValues.averageMargin)}
          </div>
          <div className="text-xs text-slate-400">Profit margin</div>
        </motion.div>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        <div>
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-lg font-semibold text-white">Available Capital</h3>
            <span className="text-lg font-bold text-green-400">{formatGP(currentCapital)} GP</span>
          </div>
          
          <div className="space-y-2">
            <input
              type="range"
              min="100000"
              max="100000000"
              step="1000000"
              value={currentCapital}
              onChange={(e) => onCapitalChange(Number(e.target.value))}
              className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer"
            />
            <div className="flex justify-between text-xs text-slate-400">
              <span>100K</span>
              <div className="text-center">
                <div className="text-slate-300">Capital Efficiency: {formatPercentage(profitMetrics.capitalEfficiency)}</div>
              </div>
              <span>100M</span>
            </div>
          </div>
        </div>

        <div>
          <h3 className="text-lg font-semibold text-white mb-3">Top Opportunities</h3>
          <div className="space-y-2">
            {profitMetrics.topOpportunities.slice(0, 3).map((opp, index) => (
              <div key={opp.id} className="flex items-center justify-between bg-slate-700/30 rounded p-2">
                <div className="flex items-center gap-3">
                  <div className="w-6 h-6 bg-gradient-to-br from-yellow-400 to-orange-500 rounded text-white text-xs flex items-center justify-center font-bold">
                    {index + 1}
                  </div>
                  <span className="text-slate-300 text-sm font-medium">{opp.set_name}</span>
                </div>
                <span className="text-green-400 font-bold text-sm">{formatGP(opp.lazy_tax_profit || 0)} GP</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-6 pt-4 border-t border-slate-600/50">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 text-center">
          <div>
            <div className="text-2xl font-bold text-white">{session.tradesExecuted}</div>
            <div className="text-xs text-slate-400">Trades Executed</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-green-400">{formatGP(session.totalProfit)} GP</div>
            <div className="text-xs text-slate-400">Session Profit</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-blue-400">{opportunities.length}</div>
            <div className="text-xs text-slate-400">Active Opportunities</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-purple-400">{formatGP(session.totalProfit / Math.max(session.hoursActive, 0.1))} GP</div>
            <div className="text-xs text-slate-400">Actual GP/Hour</div>
          </div>
        </div>
      </div>
    </div>
  );
};