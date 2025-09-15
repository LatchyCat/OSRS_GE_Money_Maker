import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  ResponsiveContainer,
  ReferenceLine,
  Tooltip,
  Area,
  AreaChart
} from 'recharts';
import {
  ChartBarIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  ClockIcon,
  EyeIcon
} from '@heroicons/react/24/outline';

interface PriceDataPoint {
  timestamp: string;
  price: number;
  volume: number;
  time: string; // Human readable time
}

interface MiniPriceChartProps {
  itemId: number;
  itemName: string;
  currentPrice: number;
  timeframe: '5m' | '1h' | '1d';
  onTimeframeChange?: (timeframe: '5m' | '1h' | '1d') => void;
  isExpanded?: boolean;
  onToggleExpand?: () => void;
  className?: string;
}

export const MiniPriceChart: React.FC<MiniPriceChartProps> = ({
  itemId,
  itemName,
  currentPrice,
  timeframe = '5m',
  onTimeframeChange,
  isExpanded = false,
  onToggleExpand,
  className = ''
}) => {
  const [priceData, setPriceData] = useState<PriceDataPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [trend, setTrend] = useState<'up' | 'down' | 'stable'>('stable');
  const [volatility, setVolatility] = useState(0);

  // Mock data generation for demonstration (replace with actual API calls)
  useEffect(() => {
    const generateMockData = () => {
      setLoading(true);
      
      // Simulate API delay
      setTimeout(() => {
        const dataPoints = timeframe === '5m' ? 24 : timeframe === '1h' ? 24 : 48;
        const basePrice = currentPrice;
        const mockData: PriceDataPoint[] = [];
        
        let currentMockPrice = basePrice * (0.9 + Math.random() * 0.2); // Start within ±10% of current
        
        for (let i = dataPoints - 1; i >= 0; i--) {
          // Add some realistic price movement
          const change = (Math.random() - 0.5) * 0.05 * currentMockPrice; // ±5% change
          currentMockPrice = Math.max(currentMockPrice + change, basePrice * 0.8); // Floor at 80% of base
          currentMockPrice = Math.min(currentMockPrice, basePrice * 1.2); // Ceiling at 120% of base
          
          const minutesAgo = i * (timeframe === '5m' ? 5 : timeframe === '1h' ? 60 : 1440);
          const timestamp = new Date(Date.now() - minutesAgo * 60 * 1000).toISOString();
          const timeDisplay = timeframe === '5m' 
            ? `${i * 5}m ago`
            : timeframe === '1h'
            ? `${i}h ago`
            : `${i}d ago`;
          
          mockData.unshift({
            timestamp,
            price: Math.round(currentMockPrice),
            volume: Math.round(1000 + Math.random() * 10000),
            time: timeDisplay
          });
        }
        
        // Calculate trend and volatility
        if (mockData.length > 1) {
          const firstPrice = mockData[0].price;
          const lastPrice = mockData[mockData.length - 1].price;
          const change = (lastPrice - firstPrice) / firstPrice;
          
          if (change > 0.02) setTrend('up');
          else if (change < -0.02) setTrend('down');
          else setTrend('stable');
          
          // Calculate volatility (standard deviation of price changes)
          const priceChanges = mockData.slice(1).map((point, index) => 
            (point.price - mockData[index].price) / mockData[index].price
          );
          const avgChange = priceChanges.reduce((sum, change) => sum + change, 0) / priceChanges.length;
          const variance = priceChanges.reduce((sum, change) => sum + Math.pow(change - avgChange, 2), 0) / priceChanges.length;
          setVolatility(Math.sqrt(variance) * 100); // Convert to percentage
        }
        
        setPriceData(mockData);
        setLoading(false);
      }, 800);
    };

    generateMockData();
  }, [itemId, timeframe, currentPrice]);

  const formatPrice = (price: number) => {
    if (price >= 1000000) return `${(price / 1000000).toFixed(1)}M`;
    if (price >= 1000) return `${(price / 1000).toFixed(1)}K`;
    return price.toString();
  };

  const getTrendColor = () => {
    switch (trend) {
      case 'up': return 'text-green-400';
      case 'down': return 'text-red-400';
      default: return 'text-gray-400';
    }
  };

  const getTrendIcon = () => {
    switch (trend) {
      case 'up': return <ArrowTrendingUpIcon className="w-4 h-4" />;
      case 'down': return <ArrowTrendingDownIcon className="w-4 h-4" />;
      default: return <ClockIcon className="w-4 h-4" />;
    }
  };

  const getLineColor = () => {
    switch (trend) {
      case 'up': return '#10b981'; // green-500
      case 'down': return '#ef4444'; // red-500
      default: return '#6b7280'; // gray-500
    }
  };

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-gray-800/95 backdrop-blur-sm border border-gray-700/50 rounded-lg p-3 shadow-lg">
          <p className="text-sm text-gray-300 mb-1">{data.time}</p>
          <p className="text-sm font-medium text-white">
            Price: {formatPrice(data.price)} GP
          </p>
          <p className="text-sm text-gray-400">
            Volume: {data.volume.toLocaleString()}
          </p>
        </div>
      );
    }
    return null;
  };

  if (loading) {
    return (
      <div className={`bg-gray-800/40 rounded-lg p-4 ${className}`}>
        <div className="flex items-center justify-center h-24">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-purple-400"></div>
          <span className="ml-2 text-sm text-gray-400">Loading chart...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`bg-gray-800/40 rounded-lg p-4 ${className}`}>
        <div className="flex items-center justify-center h-24 text-red-400">
          <span className="text-sm">Failed to load price data</span>
        </div>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`bg-gradient-to-br from-gray-800/30 to-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-lg overflow-hidden ${className}`}
    >
      {/* Chart Header */}
      <div className="flex items-center justify-between p-3 border-b border-gray-700/50">
        <div className="flex items-center gap-2">
          <ChartBarIcon className="w-4 h-4 text-gray-400" />
          <span className="text-sm font-medium text-gray-200 truncate">
            {itemName}
          </span>
          <div className={`flex items-center gap-1 ${getTrendColor()}`}>
            {getTrendIcon()}
            <span className="text-xs">
              {trend === 'up' ? 'Trending Up' : trend === 'down' ? 'Trending Down' : 'Stable'}
            </span>
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          {/* Timeframe Selector */}
          <div className="flex bg-gray-700/50 rounded-lg p-1">
            {(['5m', '1h', '1d'] as const).map((tf) => (
              <button
                key={tf}
                onClick={() => onTimeframeChange?.(tf)}
                className={`px-2 py-1 text-xs rounded transition-colors ${
                  timeframe === tf
                    ? 'bg-purple-600 text-white'
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                {tf}
              </button>
            ))}
          </div>
          
          {/* Expand/Collapse Button */}
          {onToggleExpand && (
            <button
              onClick={onToggleExpand}
              className="p-1 text-gray-400 hover:text-white transition-colors"
            >
              <EyeIcon className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Chart Area */}
      <div className="p-3">
        <div className="flex items-center justify-between mb-2">
          <div className="text-sm text-gray-400">
            Current: <span className="text-white font-medium">{formatPrice(currentPrice)} GP</span>
          </div>
          <div className="text-xs text-gray-400">
            Volatility: <span className={`font-medium ${volatility > 5 ? 'text-red-400' : volatility > 2 ? 'text-yellow-400' : 'text-green-400'}`}>
              {volatility.toFixed(1)}%
            </span>
          </div>
        </div>
        
        <div style={{ width: '100%', height: isExpanded ? '200px' : '120px' }}>
          <ResponsiveContainer>
            <AreaChart data={priceData} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
              <defs>
                <linearGradient id="priceGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={getLineColor()} stopOpacity={0.3}/>
                  <stop offset="95%" stopColor={getLineColor()} stopOpacity={0}/>
                </linearGradient>
              </defs>
              
              <XAxis 
                dataKey="time" 
                axisLine={false}
                tickLine={false}
                tick={{ fontSize: 10, fill: '#9ca3af' }}
                interval="preserveStartEnd"
              />
              
              <YAxis
                domain={['dataMin - 5', 'dataMax + 5']}
                axisLine={false}
                tickLine={false}
                tick={{ fontSize: 10, fill: '#9ca3af' }}
                tickFormatter={formatPrice}
                width={40}
              />
              
              <Tooltip content={<CustomTooltip />} />
              
              {/* Current price reference line */}
              <ReferenceLine 
                y={currentPrice} 
                stroke="#8b5cf6" 
                strokeDasharray="3 3"
                strokeWidth={1}
                opacity={0.7}
              />
              
              <Area
                type="monotone"
                dataKey="price"
                stroke={getLineColor()}
                strokeWidth={2}
                fill="url(#priceGradient)"
                dot={false}
                activeDot={{ 
                  r: 3, 
                  fill: getLineColor(),
                  stroke: '#1f2937',
                  strokeWidth: 2 
                }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
        
        {/* Additional Info (when expanded) */}
        <AnimatePresence>
          {isExpanded && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="border-t border-gray-700/50 pt-3 mt-3"
            >
              <div className="grid grid-cols-3 gap-4 text-xs">
                <div className="text-center">
                  <div className="text-gray-400">Min</div>
                  <div className="text-white font-medium">
                    {formatPrice(Math.min(...priceData.map(p => p.price)))} GP
                  </div>
                </div>
                <div className="text-center">
                  <div className="text-gray-400">Max</div>
                  <div className="text-white font-medium">
                    {formatPrice(Math.max(...priceData.map(p => p.price)))} GP
                  </div>
                </div>
                <div className="text-center">
                  <div className="text-gray-400">Avg Vol</div>
                  <div className="text-white font-medium">
                    {Math.round(priceData.reduce((sum, p) => sum + p.volume, 0) / priceData.length).toLocaleString()}
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
};

export default MiniPriceChart;