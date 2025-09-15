import React, { useMemo } from 'react';
import { motion } from 'framer-motion';
import { BarChart3, TrendingUp, Package } from 'lucide-react';
import { Card } from '../ui/Card';
import type { Item } from '../../types';

interface ProfitDistributionProps {
  items: Item[];
}

export const ProfitDistribution: React.FC<ProfitDistributionProps> = ({ items }) => {
  const formatGP = (amount: number) => {
    if (amount >= 1000000) return `${(amount / 1000000).toFixed(1)}M`;
    if (amount >= 1000) return `${(amount / 1000).toFixed(1)}K`;
    return amount.toString();
  };

  const distributionData = useMemo(() => {
    const bins = [
      { min: 0, max: 50, label: '0-50', color: 'rgb(239 68 68)', items: [] as Item[] },
      { min: 50, max: 100, label: '50-100', color: 'rgb(245 158 11)', items: [] as Item[] },
      { min: 100, max: 250, label: '100-250', color: 'rgb(34 197 94)', items: [] as Item[] },
      { min: 250, max: 500, label: '250-500', color: 'rgb(59 130 246)', items: [] as Item[] },
      { min: 500, max: 1000, label: '500-1K', color: 'rgb(147 51 234)', items: [] as Item[] },
      { min: 1000, max: Infinity, label: '1K+', color: 'rgb(99 102 241)', items: [] as Item[] }
    ];

    items.forEach(item => {
      const profit = item.current_profit || 0;
      const bin = bins.find(b => profit >= b.min && profit < b.max);
      if (bin) bin.items.push(item);
    });

    const maxCount = Math.max(...bins.map(b => b.items.length));

    return bins.map(bin => ({
      ...bin,
      count: bin.items.length,
      percentage: items.length > 0 ? (bin.items.length / items.length) * 100 : 0,
      height: maxCount > 0 ? (bin.items.length / maxCount) * 100 : 0
    }));
  }, [items]);

  const stats = useMemo(() => {
    const profitableItems = items.filter(item => (item.current_profit || 0) > 0);
    const totalProfit = profitableItems.reduce((sum, item) => sum + (item.current_profit || 0), 0);
    const averageProfit = profitableItems.length > 0 ? totalProfit / profitableItems.length : 0;
    const medianProfit = profitableItems.length > 0 ? 
      profitableItems.sort((a, b) => (a.current_profit || 0) - (b.current_profit || 0))[Math.floor(profitableItems.length / 2)]?.current_profit || 0 : 0;

    return {
      totalItems: items.length,
      profitableItems: profitableItems.length,
      totalProfit,
      averageProfit,
      medianProfit,
      profitabilityRate: items.length > 0 ? (profitableItems.length / items.length) * 100 : 0
    };
  }, [items]);

  return (
    <Card className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-accent-400" />
          <h3 className="text-lg font-semibold text-white">Profit Distribution</h3>
        </div>
        <div className="text-sm text-gray-400">
          {stats.profitableItems} of {stats.totalItems} items profitable
        </div>
      </div>

      {/* Histogram */}
      <div className="space-y-4">
        <div className="relative bg-white/5 rounded-lg p-4">
          <div className="flex items-end justify-between gap-2 h-32">
            {distributionData.map((bin, index) => (
              <motion.div
                key={bin.label}
                className="flex-1 flex flex-col items-center gap-1"
                initial={{ height: 0 }}
                animate={{ height: 'auto' }}
                transition={{ delay: 0.1 * index }}
              >
                <div className="text-xs text-gray-400 text-center">
                  {bin.count}
                </div>
                <div 
                  className="w-full rounded-t transition-all hover:opacity-80 cursor-pointer relative group"
                  style={{ 
                    height: `${bin.height}%`,
                    backgroundColor: bin.color,
                    minHeight: bin.count > 0 ? '8px' : '2px'
                  }}
                >
                  {/* Tooltip */}
                  <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 opacity-0 group-hover:opacity-100 transition-opacity z-10">
                    <div className="bg-gray-800 text-white text-xs rounded py-1 px-2 whitespace-nowrap">
                      {bin.count} items ({bin.percentage.toFixed(1)}%)
                    </div>
                  </div>
                </div>
                <div className="text-xs text-gray-400 text-center">
                  {bin.label}
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </div>

      {/* Statistics */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-3 text-center">
          <div className="text-sm text-gray-400 mb-1">Average</div>
          <div className="text-lg font-bold text-blue-400">
            {formatGP(stats.averageProfit)} GP
          </div>
        </div>

        <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-3 text-center">
          <div className="text-sm text-gray-400 mb-1">Median</div>
          <div className="text-lg font-bold text-green-400">
            {formatGP(stats.medianProfit)} GP
          </div>
        </div>

        <div className="bg-purple-500/10 border border-purple-500/20 rounded-lg p-3 text-center">
          <div className="text-sm text-gray-400 mb-1">Total Potential</div>
          <div className="text-lg font-bold text-purple-400">
            {formatGP(stats.totalProfit)} GP
          </div>
        </div>

        <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-3 text-center">
          <div className="text-sm text-gray-400 mb-1">Success Rate</div>
          <div className="text-lg font-bold text-yellow-400">
            {stats.profitabilityRate.toFixed(1)}%
          </div>
        </div>
      </div>

      {/* Breakdown by Category */}
      <div className="space-y-3">
        <div className="text-sm font-medium text-gray-300">Distribution Analysis</div>
        <div className="space-y-2">
          {distributionData.filter(bin => bin.count > 0).map((bin, index) => (
            <motion.div
              key={bin.label}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.1 * index }}
              className="flex items-center justify-between p-2 bg-white/5 rounded"
            >
              <div className="flex items-center gap-3">
                <div 
                  className="w-3 h-3 rounded"
                  style={{ backgroundColor: bin.color }}
                />
                <span className="text-sm text-white">{bin.label} GP</span>
              </div>
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-1 text-xs text-gray-400">
                  <Package className="w-3 h-3" />
                  {bin.count} items
                </div>
                <div className="text-sm font-medium text-white min-w-12 text-right">
                  {bin.percentage.toFixed(1)}%
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>

      {/* Insights */}
      {distributionData.some(bin => bin.count > 0) && (
        <div className="bg-accent-500/10 border border-accent-500/20 rounded-lg p-4">
          <div className="flex items-start gap-2">
            <TrendingUp className="w-4 h-4 text-accent-400 mt-0.5" />
            <div>
              <div className="text-sm font-medium text-accent-400 mb-1">Key Insights</div>
              <div className="text-xs text-gray-300 space-y-1">
                {stats.profitabilityRate > 50 && (
                  <div>• High profitability rate ({stats.profitabilityRate.toFixed(1)}%) indicates healthy market</div>
                )}
                {stats.averageProfit > 500 && (
                  <div>• Strong average profit ({formatGP(stats.averageProfit)} GP) suggests good opportunities</div>
                )}
                {distributionData.find(b => b.label === '1K+')?.count > 0 && (
                  <div>• {distributionData.find(b => b.label === '1K+')?.count} high-value opportunities (1K+ GP) available</div>
                )}
                {distributionData.find(b => b.label === '0-50')?.percentage > 30 && (
                  <div>• {distributionData.find(b => b.label === '0-50')?.percentage.toFixed(0)}% low-profit items may need attention</div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </Card>
  );
};