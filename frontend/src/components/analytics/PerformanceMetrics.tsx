import React from 'react';
import { motion } from 'framer-motion';
import { 
  Package, 
  TrendingUp, 
  DollarSign, 
  Activity,
  AlertTriangle,
  Clock,
  Target,
  BarChart3
} from 'lucide-react';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';

interface PerformanceData {
  totalItems: number;
  profitableItems: number;
  averageProfit: number;
  totalVolume: number;
  marketVolatility: number;
  dataAge: number;
}

interface PerformanceMetricsProps {
  data: PerformanceData;
}

export const PerformanceMetrics: React.FC<PerformanceMetricsProps> = ({ data }) => {
  const formatGP = (amount: number) => {
    if (amount >= 1000000000) {
      return `${(amount / 1000000000).toFixed(1)}B GP`;
    } else if (amount >= 1000000) {
      return `${(amount / 1000000).toFixed(1)}M GP`;
    } else if (amount >= 1000) {
      return `${(amount / 1000).toFixed(1)}K GP`;
    }
    return `${Math.round(amount)} GP`;
  };

  const formatVolume = (volume: number) => {
    if (volume >= 1000000) {
      return `${(volume / 1000000).toFixed(1)}M`;
    } else if (volume >= 1000) {
      return `${(volume / 1000).toFixed(1)}K`;
    }
    return volume.toString();
  };

  const getProfitabilityRatio = () => {
    return data.totalItems > 0 ? (data.profitableItems / data.totalItems) * 100 : 0;
  };

  const getVolatilityStatus = () => {
    if (data.marketVolatility < 0.3) return { text: 'Low', color: 'text-green-400', bgColor: 'bg-green-500/10 border-green-500/20' };
    if (data.marketVolatility < 0.7) return { text: 'Moderate', color: 'text-yellow-400', bgColor: 'bg-yellow-500/10 border-yellow-500/20' };
    return { text: 'High', color: 'text-red-400', bgColor: 'bg-red-500/10 border-red-500/20' };
  };

  const getDataFreshness = () => {
    if (data.dataAge === 0) return { text: 'Live', variant: 'success' as const };
    if (data.dataAge < 1) return { text: 'Recent', variant: 'warning' as const };
    return { text: `${data.dataAge}h old`, variant: 'danger' as const };
  };

  const volatilityStatus = getVolatilityStatus();
  const dataFreshness = getDataFreshness();

  const metrics = [
    {
      title: 'Total Items Tracked',
      value: data.totalItems.toLocaleString(),
      subtitle: 'In database',
      icon: Package,
      color: 'text-blue-400',
      bgColor: 'bg-blue-500/10 border-blue-500/20',
      trend: null
    },
    {
      title: 'Profitable Items',
      value: data.profitableItems.toLocaleString(),
      subtitle: `${getProfitabilityRatio().toFixed(1)}% profitable`,
      icon: TrendingUp,
      color: 'text-green-400',
      bgColor: 'bg-green-500/10 border-green-500/20',
      trend: getProfitabilityRatio() >= 50 ? '+' : getProfitabilityRatio() >= 25 ? '=' : '-'
    },
    {
      title: 'Average Profit',
      value: formatGP(data.averageProfit),
      subtitle: 'Per profitable item',
      icon: DollarSign,
      color: 'text-purple-400',
      bgColor: 'bg-purple-500/10 border-purple-500/20',
      trend: data.averageProfit > 500 ? '+' : data.averageProfit > 100 ? '=' : '-'
    },
    {
      title: 'Total Volume',
      value: formatVolume(data.totalVolume),
      subtitle: 'Daily transactions',
      icon: Activity,
      color: 'text-orange-400',
      bgColor: 'bg-orange-500/10 border-orange-500/20',
      trend: data.totalVolume > 100000 ? '+' : data.totalVolume > 50000 ? '=' : '-'
    },
    {
      title: 'Market Volatility',
      value: `${(data.marketVolatility * 100).toFixed(0)}%`,
      subtitle: `${volatilityStatus.text} volatility`,
      icon: AlertTriangle,
      color: volatilityStatus.color,
      bgColor: volatilityStatus.bgColor,
      trend: data.marketVolatility < 0.3 ? '+' : data.marketVolatility < 0.7 ? '=' : '-'
    },
    {
      title: 'Data Freshness',
      value: dataFreshness.text,
      subtitle: 'Last updated',
      icon: Clock,
      color: dataFreshness.variant === 'success' ? 'text-green-400' : 
             dataFreshness.variant === 'warning' ? 'text-yellow-400' : 'text-red-400',
      bgColor: dataFreshness.variant === 'success' ? 'bg-green-500/10 border-green-500/20' :
               dataFreshness.variant === 'warning' ? 'bg-yellow-500/10 border-yellow-500/20' :
               'bg-red-500/10 border-red-500/20',
      trend: data.dataAge === 0 ? '+' : data.dataAge < 1 ? '=' : '-'
    }
  ];

  const getTrendIcon = (trend: string | null) => {
    if (trend === '+') return <div className="w-2 h-2 bg-green-400 rounded-full" />;
    if (trend === '=') return <div className="w-2 h-2 bg-yellow-400 rounded-full" />;
    if (trend === '-') return <div className="w-2 h-2 bg-red-400 rounded-full" />;
    return null;
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <BarChart3 className="w-5 h-5 text-accent-400" />
        <h2 className="text-xl font-semibold text-white">Performance Overview</h2>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
        {metrics.map((metric, index) => {
          const Icon = metric.icon;
          return (
            <motion.div
              key={index}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.1 * index }}
            >
              <Card className={`p-4 sm:p-6 space-y-3 border ${metric.bgColor}`}>
                <div className="flex items-center justify-between">
                  <div className="text-sm font-medium text-gray-400">
                    {metric.title}
                  </div>
                  <div className="flex items-center gap-2">
                    {getTrendIcon(metric.trend)}
                    <Icon className={`w-5 h-5 ${metric.color}`} />
                  </div>
                </div>
                <div className={`text-2xl font-bold ${metric.color}`}>
                  {metric.value}
                </div>
                <div className="text-xs text-gray-400">
                  {metric.subtitle}
                </div>
              </Card>
            </motion.div>
          );
        })}
      </div>

      {/* Summary Card */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6 }}
      >
        <Card className="p-6 space-y-4">
          <div className="flex items-center gap-2">
            <Target className="w-5 h-5 text-accent-400" />
            <h3 className="text-lg font-semibold text-white">Market Health Summary</h3>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-2">
              <div className="text-sm text-gray-400">Market Status</div>
              <Badge variant={
                getProfitabilityRatio() >= 50 && data.marketVolatility < 0.5 ? 'success' :
                getProfitabilityRatio() >= 25 || data.marketVolatility < 0.7 ? 'warning' : 'danger'
              }>
                {getProfitabilityRatio() >= 50 && data.marketVolatility < 0.5 ? 'Healthy' :
                 getProfitabilityRatio() >= 25 || data.marketVolatility < 0.7 ? 'Moderate' : 'Caution'}
              </Badge>
            </div>

            <div className="space-y-2">
              <div className="text-sm text-gray-400">Recommended Strategy</div>
              <div className="text-sm text-white">
                {data.marketVolatility < 0.3 ? 'Conservative - Focus on stable items' :
                 data.marketVolatility < 0.7 ? 'Balanced - Mix high and low risk' :
                 'Aggressive - High-risk opportunities'}
              </div>
            </div>

            <div className="space-y-2">
              <div className="text-sm text-gray-400">Trading Volume</div>
              <div className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${
                  data.totalVolume > 100000 ? 'bg-green-400' :
                  data.totalVolume > 50000 ? 'bg-yellow-400' : 'bg-red-400'
                }`} />
                <span className="text-sm text-white">
                  {data.totalVolume > 100000 ? 'High Activity' :
                   data.totalVolume > 50000 ? 'Moderate Activity' : 'Low Activity'}
                </span>
              </div>
            </div>
          </div>

          {/* Performance Indicators */}
          <div className="bg-white/5 rounded-lg p-4 space-y-3">
            <div className="text-sm font-medium text-gray-300">Key Performance Indicators</div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
              <div>
                <div className="text-xs text-gray-400 mb-1">Profit Ratio</div>
                <div className={`text-lg font-bold ${
                  getProfitabilityRatio() >= 50 ? 'text-green-400' :
                  getProfitabilityRatio() >= 25 ? 'text-yellow-400' : 'text-red-400'
                }`}>
                  {getProfitabilityRatio().toFixed(0)}%
                </div>
              </div>
              <div>
                <div className="text-xs text-gray-400 mb-1">Avg Profit</div>
                <div className={`text-lg font-bold ${
                  data.averageProfit > 500 ? 'text-green-400' :
                  data.averageProfit > 100 ? 'text-yellow-400' : 'text-red-400'
                }`}>
                  {formatGP(data.averageProfit)}
                </div>
              </div>
              <div>
                <div className="text-xs text-gray-400 mb-1">Market Risk</div>
                <div className={`text-lg font-bold ${volatilityStatus.color}`}>
                  {volatilityStatus.text}
                </div>
              </div>
              <div>
                <div className="text-xs text-gray-400 mb-1">Data Quality</div>
                <div className={`text-lg font-bold ${
                  data.dataAge === 0 ? 'text-green-400' :
                  data.dataAge < 1 ? 'text-yellow-400' : 'text-red-400'
                }`}>
                  {dataFreshness.text}
                </div>
              </div>
            </div>
          </div>
        </Card>
      </motion.div>
    </div>
  );
};