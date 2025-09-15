import React, { useMemo } from 'react';
import { motion } from 'framer-motion';
import { Grid3X3, Thermometer, Activity } from 'lucide-react';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import type { Item } from '../../types';

interface MarketHeatmapProps {
  items: Item[];
}

interface HeatmapCell {
  id: string;
  name: string;
  profit: number;
  volume: number;
  volatility: number;
  intensity: number;
  risk: 'low' | 'medium' | 'high';
  opportunity: 'poor' | 'fair' | 'good' | 'excellent';
}

export const MarketHeatmap: React.FC<MarketHeatmapProps> = ({ items }) => {
  const formatGP = (amount: number) => {
    if (amount >= 1000000) return `${(amount / 1000000).toFixed(1)}M`;
    if (amount >= 1000) return `${(amount / 1000).toFixed(1)}K`;
    return amount.toString();
  };

  const heatmapData = useMemo(() => {
    // Take top 20 items and organize into grid
    const topItems = items
      .filter(item => (item.current_profit || 0) > 0)
      .sort((a, b) => (b.current_profit || 0) - (a.current_profit || 0))
      .slice(0, 20);

    const maxProfit = Math.max(...topItems.map(item => item.current_profit || 0));
    const maxVolume = Math.max(...topItems.map(item => item.profit_calc?.daily_volume || 0));

    return topItems.map(item => {
      const profit = item.current_profit || 0;
      const volume = item.profit_calc?.daily_volume || 0;
      const volatility = item.profit_calc?.price_volatility || 0;
      
      // Calculate intensity based on profit and volume
      const profitScore = maxProfit > 0 ? (profit / maxProfit) : 0;
      const volumeScore = maxVolume > 0 ? (volume / maxVolume) : 0;
      const intensity = (profitScore * 0.7 + volumeScore * 0.3) * 100;

      // Determine risk level
      const risk = volatility > 0.5 ? 'high' : volatility > 0.2 ? 'medium' : 'low';

      // Determine opportunity level
      let opportunity: HeatmapCell['opportunity'];
      if (intensity > 80) opportunity = 'excellent';
      else if (intensity > 60) opportunity = 'good';
      else if (intensity > 30) opportunity = 'fair';
      else opportunity = 'poor';

      return {
        id: item.item_id.toString(),
        name: item.name.length > 12 ? item.name.substring(0, 12) + '...' : item.name,
        profit,
        volume,
        volatility,
        intensity,
        risk,
        opportunity
      } as HeatmapCell;
    });
  }, [items]);

  const getIntensityColor = (intensity: number) => {
    if (intensity > 80) return 'rgb(34 197 94)'; // green-500
    if (intensity > 60) return 'rgb(59 130 246)'; // blue-500
    if (intensity > 40) return 'rgb(245 158 11)'; // amber-500
    if (intensity > 20) return 'rgb(239 68 68)'; // red-500
    return 'rgb(107 114 128)'; // gray-500
  };

  const getOpportunityBadge = (opportunity: HeatmapCell['opportunity']) => {
    switch (opportunity) {
      case 'excellent': return { variant: 'success' as const, text: 'Excellent' };
      case 'good': return { variant: 'warning' as const, text: 'Good' };
      case 'fair': return { variant: 'secondary' as const, text: 'Fair' };
      case 'poor': return { variant: 'danger' as const, text: 'Poor' };
    }
  };

  const getRiskColor = (risk: HeatmapCell['risk']) => {
    switch (risk) {
      case 'low': return 'text-green-400';
      case 'medium': return 'text-yellow-400';
      case 'high': return 'text-red-400';
    }
  };

  const stats = useMemo(() => {
    const opportunities = heatmapData.reduce((acc, cell) => {
      acc[cell.opportunity] = (acc[cell.opportunity] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    const risks = heatmapData.reduce((acc, cell) => {
      acc[cell.risk] = (acc[cell.risk] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    const avgIntensity = heatmapData.reduce((sum, cell) => sum + cell.intensity, 0) / heatmapData.length || 0;

    return { opportunities, risks, avgIntensity };
  }, [heatmapData]);

  return (
    <Card className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Grid3X3 className="w-5 h-5 text-accent-400" />
          <h3 className="text-lg font-semibold text-white">Market Heatmap</h3>
        </div>
        <div className="flex items-center gap-2">
          <Thermometer className="w-4 h-4 text-gray-400" />
          <span className="text-sm text-gray-400">
            Avg. Intensity: {stats.avgIntensity.toFixed(0)}%
          </span>
        </div>
      </div>

      {/* Heatmap Grid */}
      <div className="space-y-4">
        <div className="grid grid-cols-4 sm:grid-cols-5 gap-2">
          {heatmapData.map((cell, index) => (
            <motion.div
              key={cell.id}
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.05 * index }}
              className="group relative cursor-pointer"
            >
              <div
                className="aspect-square rounded-lg border border-white/10 p-2 transition-all hover:border-white/30 hover:scale-105"
                style={{
                  backgroundColor: `${getIntensityColor(cell.intensity)}20`,
                  borderColor: `${getIntensityColor(cell.intensity)}40`
                }}
              >
                <div className="h-full flex flex-col justify-between">
                  <div 
                    className="text-xs font-medium text-white truncate leading-tight"
                    title={cell.name}
                  >
                    {cell.name}
                  </div>
                  <div className="space-y-1">
                    <div 
                      className="text-xs font-bold"
                      style={{ color: getIntensityColor(cell.intensity) }}
                    >
                      {formatGP(cell.profit)}
                    </div>
                    <div className={`text-xs ${getRiskColor(cell.risk)}`}>
                      {cell.risk}
                    </div>
                  </div>
                </div>

                {/* Tooltip */}
                <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 opacity-0 group-hover:opacity-100 transition-opacity z-10 pointer-events-none">
                  <div className="bg-gray-800 text-white text-xs rounded-lg py-2 px-3 whitespace-nowrap shadow-lg border border-gray-700">
                    <div className="font-medium mb-1">{cell.name.replace('...', '')}</div>
                    <div>Profit: {formatGP(cell.profit)} GP</div>
                    <div>Volume: {cell.volume.toLocaleString()}</div>
                    <div>Risk: {cell.risk}</div>
                    <div>Intensity: {cell.intensity.toFixed(0)}%</div>
                  </div>
                </div>
              </div>
            </motion.div>
          ))}
          
          {/* Fill remaining cells if less than 20 items */}
          {Array.from({ length: Math.max(0, 20 - heatmapData.length) }).map((_, index) => (
            <div
              key={`empty-${index}`}
              className="aspect-square rounded-lg border border-white/5 bg-white/5"
            />
          ))}
        </div>

        {/* Legend */}
        <div className="flex items-center justify-center gap-4 text-xs">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded" style={{ backgroundColor: 'rgb(34 197 94)' }} />
            <span className="text-gray-400">High Opportunity</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded" style={{ backgroundColor: 'rgb(59 130 246)' }} />
            <span className="text-gray-400">Good</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded" style={{ backgroundColor: 'rgb(245 158 11)' }} />
            <span className="text-gray-400">Fair</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded" style={{ backgroundColor: 'rgb(239 68 68)' }} />
            <span className="text-gray-400">Poor</span>
          </div>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white/5 rounded-lg p-4 space-y-2">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-blue-400" />
            <span className="text-sm font-medium text-white">Opportunity Breakdown</span>
          </div>
          <div className="space-y-1">
            {(['excellent', 'good', 'fair', 'poor'] as const).map(level => (
              <div key={level} className="flex justify-between text-xs">
                <span className="text-gray-400 capitalize">{level}:</span>
                <span className="text-white">{stats.opportunities[level] || 0}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white/5 rounded-lg p-4 space-y-2">
          <div className="flex items-center gap-2">
            <Thermometer className="w-4 h-4 text-red-400" />
            <span className="text-sm font-medium text-white">Risk Distribution</span>
          </div>
          <div className="space-y-1">
            {(['low', 'medium', 'high'] as const).map(risk => (
              <div key={risk} className="flex justify-between text-xs">
                <span className={`capitalize ${getRiskColor(risk)}`}>{risk}:</span>
                <span className="text-white">{stats.risks[risk] || 0}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white/5 rounded-lg p-4 space-y-2">
          <div className="flex items-center gap-2">
            <Grid3X3 className="w-4 h-4 text-purple-400" />
            <span className="text-sm font-medium text-white">Market Summary</span>
          </div>
          <div className="space-y-1">
            <div className="flex justify-between text-xs">
              <span className="text-gray-400">Items Analyzed:</span>
              <span className="text-white">{heatmapData.length}</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-gray-400">Avg. Intensity:</span>
              <span className="text-white">{stats.avgIntensity.toFixed(0)}%</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-gray-400">Best Opportunity:</span>
              {heatmapData.length > 0 && (
                <Badge 
                  variant={getOpportunityBadge(heatmapData[0].opportunity).variant}
                  size="sm"
                >
                  {getOpportunityBadge(heatmapData[0].opportunity).text}
                </Badge>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Insights */}
      {heatmapData.length > 0 && (
        <div className="bg-accent-500/10 border border-accent-500/20 rounded-lg p-4">
          <div className="flex items-start gap-2">
            <Grid3X3 className="w-4 h-4 text-accent-400 mt-0.5" />
            <div>
              <div className="text-sm font-medium text-accent-400 mb-2">Market Analysis</div>
              <div className="text-xs text-gray-300 space-y-1">
                {stats.opportunities.excellent > 0 && (
                  <div>• {stats.opportunities.excellent} excellent opportunities with high profit potential</div>
                )}
                {stats.risks.low > stats.risks.high && (
                  <div>• Market shows low risk profile - good for conservative strategies</div>
                )}
                {stats.avgIntensity > 60 && (
                  <div>• High market intensity ({stats.avgIntensity.toFixed(0)}%) indicates strong profit opportunities</div>
                )}
                {stats.avgIntensity < 30 && (
                  <div>• Low market intensity - may need to explore different item categories</div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </Card>
  );
};