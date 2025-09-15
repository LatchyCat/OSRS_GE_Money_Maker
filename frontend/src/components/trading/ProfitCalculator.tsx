import React, { useState, useMemo } from 'react';
import { motion } from 'framer-motion';
import {
  CurrencyDollarIcon,
  ClockIcon,
  ChartBarIcon,
  ArrowTrendingUpIcon,
  CalculatorIcon,
  BanknotesIcon,
  BoltIcon
} from '@heroicons/react/24/outline';
import type { DecantingOpportunity } from '../../types/tradingStrategies';

interface ProfitCalculatorProps {
  opportunity: DecantingOpportunity;
  onClose: () => void;
  onStartTrading?: (opportunity: DecantingOpportunity, capital: number) => void;
  onSaveStrategy?: (opportunity: DecantingOpportunity, calculations: any) => void;
}

export const ProfitCalculator: React.FC<ProfitCalculatorProps> = ({ 
  opportunity, 
  onClose, 
  onStartTrading, 
  onSaveStrategy 
}) => {
  const [capital, setCapital] = useState(1000000); // 1M GP default
  const [hoursPerDay, setHoursPerDay] = useState(2); // 2 hours default
  const [daysPerWeek, setDaysPerWeek] = useState(5); // 5 days default
  
  // Calculate tax-adjusted profit
  const calculateTaxedProfit = (opp: DecantingOpportunity) => {
    const buyPrice = opp.from_dose_price;
    const sellPrice = opp.to_dose_price;
    const dosesPerConversion = opp.from_dose;
    
    const totalBuyCost = buyPrice;
    const buyTax = totalBuyCost * 0.02;
    const totalBuyCostWithTax = totalBuyCost + buyTax;
    
    const totalSellRevenue = sellPrice * dosesPerConversion;
    const sellTax = totalSellRevenue * 0.02;
    const totalSellRevenueAfterTax = totalSellRevenue - sellTax;
    
    const netProfit = totalSellRevenueAfterTax - totalBuyCostWithTax;
    
    return {
      netProfit: Math.floor(netProfit),
      profitMargin: (netProfit / totalBuyCostWithTax) * 100,
      buyTax,
      sellTax,
      totalTax: buyTax + sellTax
    };
  };

  // Comprehensive calculations
  const calculations = useMemo(() => {
    const taxedResult = calculateTaxedProfit(opportunity);
    
    // Basic metrics
    const investmentPerConversion = opportunity.from_dose_price + taxedResult.buyTax;
    const maxConversions = Math.floor(capital / investmentPerConversion);
    const actualCapitalUsed = maxConversions * investmentPerConversion;
    const capitalEfficiency = (actualCapitalUsed / capital) * 100;
    
    // Profit calculations
    const profitPerConversion = taxedResult.netProfit;
    const totalProfitPerBatch = profitPerConversion * maxConversions;
    
    // Time-based calculations
    const conversionsPerHour = Math.floor(3600 / 10); // Assume 10 seconds per conversion
    const maxConversionsPerHour = Math.min(conversionsPerHour, maxConversions);
    const hourlyProfit = maxConversionsPerHour * profitPerConversion;
    
    // Daily and weekly projections
    const dailyProfit = hourlyProfit * hoursPerDay;
    const weeklyProfit = dailyProfit * daysPerWeek;
    const monthlyProfit = dailyProfit * 30;
    
    // ROI calculations
    const roiPerHour = (hourlyProfit / capital) * 100;
    const paybackTimeHours = capital > 0 ? capital / hourlyProfit : Infinity;
    
    // Risk assessment
    const riskLevel = opportunity.risk_assessment?.risk_level || 'medium';
    const marketCap = (opportunity.from_dose_high_volume + opportunity.to_dose_high_volume) * 
                     (opportunity.from_dose_price + opportunity.to_dose_price) / 2;
    
    return {
      // Investment
      investmentPerConversion,
      maxConversions,
      actualCapitalUsed,
      capitalEfficiency,
      unusedCapital: capital - actualCapitalUsed,
      
      // Profit
      profitPerConversion,
      totalProfitPerBatch,
      hourlyProfit,
      dailyProfit,
      weeklyProfit,
      monthlyProfit,
      
      // Performance
      roiPerHour,
      paybackTimeHours,
      profitMargin: taxedResult.profitMargin,
      
      // Tax breakdown
      taxPerConversion: taxedResult.totalTax,
      totalTaxDaily: taxedResult.totalTax * maxConversionsPerHour * hoursPerDay,
      
      // Risk & Market
      riskLevel,
      marketCap,
      volumeSupport: Math.min(
        opportunity.from_dose_high_volume / maxConversions,
        opportunity.to_dose_high_volume / maxConversions
      )
    };
  }, [opportunity, capital, hoursPerDay, daysPerWeek]);

  const formatGP = (amount: number) => {
    if (amount >= 1000000000) return `${(amount / 1000000000).toFixed(1)}B GP`;
    if (amount >= 1000000) return `${(amount / 1000000).toFixed(1)}M GP`;
    if (amount >= 1000) return `${(amount / 1000).toFixed(1)}K GP`;
    return `${Math.round(amount)} GP`;
  };

  const formatTime = (hours: number) => {
    if (hours >= 24) return `${(hours / 24).toFixed(1)} days`;
    if (hours >= 1) return `${hours.toFixed(1)} hours`;
    return `${(hours * 60).toFixed(0)} minutes`;
  };

  const getRiskColor = (risk: string) => {
    switch (risk) {
      case 'low': return 'text-green-400';
      case 'medium': return 'text-yellow-400';
      case 'high': return 'text-red-400';
      default: return 'text-gray-400';
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.9, opacity: 0 }}
        className="bg-gray-900 border border-gray-700 rounded-2xl max-w-6xl w-full max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-6 border-b border-gray-700 bg-gradient-to-r from-blue-900/20 to-purple-900/20">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-500/20 rounded-lg">
                <CalculatorIcon className="w-6 h-6 text-blue-400" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-white">Profit Calculator</h2>
                <p className="text-gray-400">{opportunity.item_name} • {opportunity.from_dose}→{opportunity.to_dose} dose</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-700 rounded-lg transition-colors"
            >
              <span className="text-gray-400 text-xl">×</span>
            </button>
          </div>
        </div>

        <div className="p-6 grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Input Controls */}
          <div className="space-y-6">
            <div className="bg-gray-800/50 rounded-xl p-6">
              <h3 className="text-lg font-semibold text-white mb-4">Investment Parameters</h3>
              
              {/* Capital Slider */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium text-gray-300">Available Capital</label>
                  <span className="text-lg font-bold text-blue-400">{formatGP(capital)}</span>
                </div>
                <input
                  type="range"
                  min="100000"
                  max="50000000"
                  step="100000"
                  value={capital}
                  onChange={(e) => setCapital(parseInt(e.target.value))}
                  className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer slider"
                />
                <div className="flex justify-between text-xs text-gray-500">
                  <span>100K</span>
                  <span>50M</span>
                </div>
              </div>

              {/* Hours per Day */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium text-gray-300">Hours per Day</label>
                  <span className="text-lg font-bold text-green-400">{hoursPerDay}h</span>
                </div>
                <input
                  type="range"
                  min="0.5"
                  max="12"
                  step="0.5"
                  value={hoursPerDay}
                  onChange={(e) => setHoursPerDay(parseFloat(e.target.value))}
                  className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer slider"
                />
                <div className="flex justify-between text-xs text-gray-500">
                  <span>30min</span>
                  <span>12h</span>
                </div>
              </div>

              {/* Days per Week */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium text-gray-300">Days per Week</label>
                  <span className="text-lg font-bold text-purple-400">{daysPerWeek} days</span>
                </div>
                <input
                  type="range"
                  min="1"
                  max="7"
                  step="1"
                  value={daysPerWeek}
                  onChange={(e) => setDaysPerWeek(parseInt(e.target.value))}
                  className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer slider"
                />
                <div className="flex justify-between text-xs text-gray-500">
                  <span>1 day</span>
                  <span>7 days</span>
                </div>
              </div>
            </div>

            {/* Quick Presets */}
            <div className="bg-gray-800/50 rounded-xl p-6">
              <h3 className="text-lg font-semibold text-white mb-4">Quick Presets</h3>
              <div className="grid grid-cols-2 gap-3">
                <button
                  onClick={() => { setCapital(1000000); setHoursPerDay(1); setDaysPerWeek(7); }}
                  className="p-3 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm transition-colors"
                >
                  <div className="text-green-400 font-medium">Casual</div>
                  <div className="text-gray-400">1M • 1h/day</div>
                </button>
                <button
                  onClick={() => { setCapital(5000000); setHoursPerDay(3); setDaysPerWeek(5); }}
                  className="p-3 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm transition-colors"
                >
                  <div className="text-blue-400 font-medium">Regular</div>
                  <div className="text-gray-400">5M • 3h/day</div>
                </button>
                <button
                  onClick={() => { setCapital(20000000); setHoursPerDay(6); setDaysPerWeek(6); }}
                  className="p-3 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm transition-colors"
                >
                  <div className="text-purple-400 font-medium">Dedicated</div>
                  <div className="text-gray-400">20M • 6h/day</div>
                </button>
                <button
                  onClick={() => { setCapital(50000000); setHoursPerDay(8); setDaysPerWeek(7); }}
                  className="p-3 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm transition-colors"
                >
                  <div className="text-orange-400 font-medium">Hardcore</div>
                  <div className="text-gray-400">50M • 8h/day</div>
                </button>
              </div>
            </div>
          </div>

          {/* Results */}
          <div className="space-y-6">
            {/* Profit Overview */}
            <div className="bg-gradient-to-r from-green-900/20 to-emerald-900/20 border border-green-500/30 rounded-xl p-6">
              <h3 className="text-lg font-semibold text-green-400 mb-4 flex items-center gap-2">
                <BanknotesIcon className="w-5 h-5" />
                Profit Projections
              </h3>
              <div className="grid grid-cols-2 gap-4">
                <div className="text-center">
                  <div className="text-2xl font-bold text-green-400">{formatGP(calculations.hourlyProfit)}</div>
                  <div className="text-sm text-gray-400">Per Hour</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-green-400">{formatGP(calculations.dailyProfit)}</div>
                  <div className="text-sm text-gray-400">Per Day</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-green-400">{formatGP(calculations.weeklyProfit)}</div>
                  <div className="text-sm text-gray-400">Per Week</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-green-400">{formatGP(calculations.monthlyProfit)}</div>
                  <div className="text-sm text-gray-400">Per Month</div>
                </div>
              </div>
            </div>

            {/* Investment Details */}
            <div className="bg-gray-800/50 rounded-xl p-6">
              <h3 className="text-lg font-semibold text-white mb-4">Investment Analysis</h3>
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-gray-400">Max Conversions</span>
                  <span className="text-white font-medium">{calculations.maxConversions.toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Capital Efficiency</span>
                  <span className="text-blue-400 font-medium">{calculations.capitalEfficiency.toFixed(1)}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">ROI per Hour</span>
                  <span className="text-green-400 font-medium">{calculations.roiPerHour.toFixed(2)}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Payback Time</span>
                  <span className="text-purple-400 font-medium">
                    {calculations.paybackTimeHours === Infinity ? 'Never' : formatTime(calculations.paybackTimeHours)}
                  </span>
                </div>
              </div>
            </div>

            {/* Risk & Market Analysis */}
            <div className="bg-gray-800/50 rounded-xl p-6">
              <h3 className="text-lg font-semibold text-white mb-4">Risk Assessment</h3>
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-gray-400">Risk Level</span>
                  <span className={`font-medium capitalize ${getRiskColor(calculations.riskLevel)}`}>
                    {calculations.riskLevel}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Volume Support</span>
                  <span className="text-white font-medium">{calculations.volumeSupport.toFixed(1)}x</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Daily Tax Cost</span>
                  <span className="text-red-400 font-medium">{formatGP(calculations.totalTaxDaily)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Profit Margin</span>
                  <span className="text-yellow-400 font-medium">{calculations.profitMargin.toFixed(1)}%</span>
                </div>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-3">
              <button 
                onClick={() => {
                  onStartTrading?.(opportunity, capital);
                  onClose();
                }}
                className="flex-1 bg-blue-600 hover:bg-blue-700 text-white py-3 px-4 rounded-lg font-medium transition-colors flex items-center justify-center gap-2"
              >
                <BoltIcon className="w-4 h-4" />
                Start Trading
              </button>
              <button 
                onClick={() => {
                  const strategyData = {
                    ...calculations,
                    capital,
                    hoursPerDay,
                    daysPerWeek,
                    timestamp: new Date().toISOString()
                  };
                  onSaveStrategy?.(opportunity, strategyData);
                  
                  // Also save to localStorage for persistence
                  const savedStrategies = JSON.parse(localStorage.getItem('savedStrategies') || '[]');
                  savedStrategies.push({
                    id: `strategy_${Date.now()}`,
                    itemName: opportunity.item_name,
                    opportunity,
                    strategy: strategyData
                  });
                  localStorage.setItem('savedStrategies', JSON.stringify(savedStrategies));
                  
                  // Show feedback (could be a toast notification)
                  alert('Strategy saved successfully!');
                }}
                className="flex-1 bg-gray-700 hover:bg-gray-600 text-white py-3 px-4 rounded-lg font-medium transition-colors flex items-center justify-center gap-2"
              >
                <BanknotesIcon className="w-4 h-4" />
                Save Strategy
              </button>
            </div>
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
};

export default ProfitCalculator;