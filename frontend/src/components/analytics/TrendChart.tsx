import React, { useMemo } from 'react';
import { motion } from 'framer-motion';
import { TrendingUp, TrendingDown, Activity, AlertCircle } from 'lucide-react';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import type { Item } from '../../types';

interface TrendChartProps {
  items: Item[];
  timeRange: '24h' | '7d' | '30d' | '90d';
  title?: string;
}

export const TrendChart: React.FC<TrendChartProps> = ({ 
  items, 
  timeRange, 
  title = 'Market Trends' 
}) => {
  const formatGP = (amount: number) => {
    if (amount >= 1000000) return `${(amount / 1000000).toFixed(1)}M`;
    if (amount >= 1000) return `${(amount / 1000).toFixed(1)}K`;
    return amount.toString();
  };

  // Generate mock trend data based on current items
  const trendData = useMemo(() => {
    const periods = timeRange === '24h' ? 24 : timeRange === '7d' ? 7 : timeRange === '30d' ? 30 : 90;
    const dataPoints = [];

    for (let i = 0; i < periods; i++) {
      const baseValue = items.reduce((sum, item) => sum + (item.current_profit || 0), 0) / items.length || 0;
      const variance = baseValue * 0.2; // 20% variance
      const trend = Math.sin((i / periods) * Math.PI * 2) * variance;
      const noise = (Math.random() - 0.5) * variance * 0.5;
      
      dataPoints.push({
        period: i,
        value: Math.max(0, baseValue + trend + noise),
        volume: Math.floor(Math.random() * 10000) + 1000,
        label: timeRange === '24h' ? `${i}:00` : 
               timeRange === '7d' ? `Day ${i + 1}` :
               `Period ${i + 1}`
      });
    }

    return dataPoints;
  }, [items, timeRange]);

  const { maxValue, minValue, averageValue, totalChange } = useMemo(() => {
    if (trendData.length === 0) return { maxValue: 0, minValue: 0, averageValue: 0, totalChange: 0 };
    
    const values = trendData.map(d => d.value);
    const max = Math.max(...values);
    const min = Math.min(...values);
    const avg = values.reduce((a, b) => a + b, 0) / values.length;
    const change = ((values[values.length - 1] - values[0]) / values[0]) * 100;

    return { maxValue: max, minValue: min, averageValue: avg, totalChange: change };
  }, [trendData]);

  const getPathData = () => {
    if (trendData.length === 0) return '';
    
    const width = 400;
    const height = 200;
    const padding = 20;
    
    const xStep = (width - padding * 2) / (trendData.length - 1);
    const yRange = maxValue - minValue || 1;
    
    const points = trendData.map((point, index) => {
      const x = padding + index * xStep;
      const y = height - padding - ((point.value - minValue) / yRange) * (height - padding * 2);
      return `${x},${y}`;
    });

    return `M ${points.join(' L ')}`;
  };

  const getAreaPath = () => {
    if (trendData.length === 0) return '';
    
    const linePath = getPathData();
    const width = 400;
    const height = 200;
    const padding = 20;
    
    const lastX = padding + (trendData.length - 1) * ((width - padding * 2) / (trendData.length - 1));
    const firstX = padding;
    const bottom = height - padding;
    
    return `${linePath} L ${lastX},${bottom} L ${firstX},${bottom} Z`;
  };

  const topPerformers = items
    .filter(item => (item.current_profit || 0) > 0)
    .sort((a, b) => (b.current_profit || 0) - (a.current_profit || 0))
    .slice(0, 5);

  const volatileItems = items
    .filter(item => (item.profit_calc?.price_volatility || 0) > 0.3)
    .sort((a, b) => (b.profit_calc?.price_volatility || 0) - (a.profit_calc?.price_volatility || 0))
    .slice(0, 3);

  return (
    <div className="space-y-6">
      <Card className="p-6 space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-accent-400" />
            <h3 className="text-lg font-semibold text-white">{title}</h3>
          </div>
          <Badge variant={totalChange >= 0 ? 'success' : 'danger'}>
            {totalChange >= 0 ? '+' : ''}{totalChange.toFixed(1)}%
          </Badge>
        </div>

        {/* Chart Area */}
        <div className="relative bg-white/5 rounded-lg p-6 overflow-hidden">
          <svg
            viewBox="0 0 400 200"
            className="w-full h-48"
            preserveAspectRatio="xMidYMid meet"
          >
            {/* Grid Lines */}
            <defs>
              <linearGradient id="chartGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" stopColor="rgb(99 102 241)" stopOpacity="0.3" />
                <stop offset="100%" stopColor="rgb(99 102 241)" stopOpacity="0.1" />
              </linearGradient>
            </defs>
            
            {/* Horizontal grid lines */}
            {[0, 1, 2, 3, 4].map(i => (
              <line
                key={i}
                x1="20"
                y1={20 + (i * (160 / 4))}
                x2="380"
                y2={20 + (i * (160 / 4))}
                stroke="rgba(255,255,255,0.1)"
                strokeWidth="1"
              />
            ))}

            {/* Area under curve */}
            <path
              d={getAreaPath()}
              fill="url(#chartGradient)"
            />

            {/* Main trend line */}
            <path
              d={getPathData()}
              fill="none"
              stroke="rgb(99 102 241)"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />

            {/* Data points */}
            {trendData.map((point, index) => {
              const width = 400;
              const height = 200;
              const padding = 20;
              const xStep = (width - padding * 2) / (trendData.length - 1);
              const yRange = maxValue - minValue || 1;
              const x = padding + index * xStep;
              const y = height - padding - ((point.value - minValue) / yRange) * (height - padding * 2);
              
              return (
                <circle
                  key={index}
                  cx={x}
                  cy={y}
                  r="3"
                  fill="rgb(99 102 241)"
                  className="hover:r-4 transition-all cursor-pointer"
                >
                  <title>{`${point.label}: ${formatGP(point.value)} GP`}</title>
                </circle>
              );
            })}
          </svg>

          {/* Y-axis labels */}
          <div className="absolute left-2 top-6 h-36 flex flex-col justify-between text-xs text-gray-400">
            <span>{formatGP(maxValue)}</span>
            <span>{formatGP((maxValue + minValue) / 2)}</span>
            <span>{formatGP(minValue)}</span>
          </div>
        </div>

        {/* Chart Stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="text-center">
            <div className="text-sm text-gray-400">Average</div>
            <div className="text-lg font-bold text-blue-400">
              {formatGP(averageValue)} GP
            </div>
          </div>
          <div className="text-center">
            <div className="text-sm text-gray-400">Peak</div>
            <div className="text-lg font-bold text-green-400">
              {formatGP(maxValue)} GP
            </div>
          </div>
          <div className="text-center">
            <div className="text-sm text-gray-400">Low</div>
            <div className="text-lg font-bold text-red-400">
              {formatGP(minValue)} GP
            </div>
          </div>
          <div className="text-center">
            <div className="text-sm text-gray-400">Change</div>
            <div className={`text-lg font-bold flex items-center justify-center gap-1 ${
              totalChange >= 0 ? 'text-green-400' : 'text-red-400'
            }`}>
              {totalChange >= 0 ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
              {Math.abs(totalChange).toFixed(1)}%
            </div>
          </div>
        </div>
      </Card>

      {/* Top Performers & Market Alerts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="p-6 space-y-4">
          <div className="flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-green-400" />
            <h3 className="text-lg font-semibold text-white">Top Performers</h3>
          </div>
          <div className="space-y-3">
            {topPerformers.map((item, index) => (
              <div key={item.item_id} className="flex items-center justify-between p-3 bg-white/5 rounded-lg">
                <div>
                  <div className="font-medium text-white truncate max-w-32">{item.name}</div>
                  <div className="text-xs text-gray-400">
                    {item.profit_calc?.volume_category || 'low'} volume
                  </div>
                </div>
                <div className="text-right">
                  <div className="font-bold text-green-400">
                    +{formatGP(item.current_profit || 0)} GP
                  </div>
                  <div className="text-xs text-gray-400">
                    {((item.current_profit_margin || 0)).toFixed(1)}% margin
                  </div>
                </div>
              </div>
            ))}
            {topPerformers.length === 0 && (
              <div className="text-center py-4 text-gray-400">
                No profitable items found
              </div>
            )}
          </div>
        </Card>

        <Card className="p-6 space-y-4">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-5 h-5 text-yellow-400" />
            <h3 className="text-lg font-semibold text-white">Market Alerts</h3>
          </div>
          <div className="space-y-3">
            {volatileItems.map((item) => (
              <div key={item.item_id} className="flex items-center justify-between p-3 bg-yellow-500/10 border border-yellow-500/20 rounded-lg">
                <div>
                  <div className="font-medium text-white truncate max-w-32">{item.name}</div>
                  <div className="text-xs text-yellow-400">High volatility</div>
                </div>
                <div className="text-right">
                  <div className="font-bold text-yellow-400">
                    {((item.profit_calc?.price_volatility || 0) * 100).toFixed(0)}%
                  </div>
                  <div className="text-xs text-gray-400">volatility</div>
                </div>
              </div>
            ))}
            {volatileItems.length === 0 && (
              <div className="text-center py-4 text-gray-400 bg-green-500/10 border border-green-500/20 rounded-lg">
                <div className="flex items-center justify-center gap-2">
                  <Activity className="w-4 h-4 text-green-400" />
                  <span>Market is stable</span>
                </div>
              </div>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
};