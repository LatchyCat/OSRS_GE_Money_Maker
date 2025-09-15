import React from 'react';
import { TrendingUp, Package, Target, AlertTriangle } from 'lucide-react';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import type { MarketAnalysis } from '../../types';

interface MarketStatsProps {
  data: MarketAnalysis;
  loading?: boolean;
}

export const MarketStats: React.FC<MarketStatsProps> = ({ data, loading }) => {
  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {[...Array(4)].map((_, i) => (
          <Card key={i} className="animate-pulse">
            <div className="space-y-3">
              <div className="h-4 bg-white/20 rounded" />
              <div className="h-8 bg-white/20 rounded" />
              <div className="h-3 bg-white/20 rounded w-2/3" />
            </div>
          </Card>
        ))}
      </div>
    );
  }

  const formatGP = (amount: number) => {
    if (amount >= 1000000) {
      return `${(amount / 1000000).toFixed(1)}M GP`;
    } else if (amount >= 1000) {
      return `${(amount / 1000).toFixed(1)}K GP`;
    }
    return `${amount} GP`;
  };

  const getRiskBadgeVariant = (riskLevel: string) => {
    switch (riskLevel) {
      case 'conservative':
        return 'success';
      case 'moderate':
        return 'warning';
      case 'aggressive':
        return 'danger';
      default:
        return 'neutral';
    }
  };

  const getVolatilityColor = (score: number) => {
    if (score < 0.3) return 'text-green-400';
    if (score < 0.7) return 'text-yellow-400';
    return 'text-red-400';
  };

  const getVolumeColor = (itemCount: number) => {
    if (itemCount > 1000) return 'text-yellow-400 bg-yellow-500/10 border-yellow-500/20';
    if (itemCount > 500) return 'text-blue-400 bg-blue-500/10 border-blue-500/20';
    return 'text-green-400 bg-green-500/10 border-green-500/20';
  };

  const getProfitColor = (amount: number) => {
    if (amount > 1000) return 'text-orange-400 bg-orange-500/10 border-orange-500/20';
    if (amount > 500) return 'text-yellow-400 bg-yellow-500/10 border-yellow-500/20';
    return 'text-green-400 bg-green-500/10 border-green-500/20';
  };

  const getMarginColor = (margin: number) => {
    if (margin > 15) return 'text-green-400 bg-green-500/10 border-green-500/20';
    if (margin > 8) return 'text-yellow-400 bg-yellow-500/10 border-yellow-500/20';
    return 'text-red-400 bg-red-500/10 border-red-500/20';
  };

  const getVolatilityColorWithBg = (score: number) => {
    if (score < 0.3) return 'text-green-400 bg-green-500/10 border-green-500/20';
    if (score < 0.7) return 'text-yellow-400 bg-yellow-500/10 border-yellow-500/20';
    return 'text-red-400 bg-red-500/10 border-red-500/20';
  };

  const stats = [
    {
      title: 'Profitable Items',
      value: (data.total_profitable_items ?? 0).toLocaleString(),
      subtitle: 'Currently available',
      icon: Package,
      color: 'text-green-400',
      bgColor: getVolumeColor(data.total_profitable_items ?? 0)
    },
    {
      title: 'Average Margin',
      value: `${(data.average_profit_margin ?? 0).toFixed(2)}%`,
      subtitle: 'Profit percentage',
      icon: TrendingUp,
      color: getMarginColor(data.average_profit_margin ?? 0).split(' ')[0],
      bgColor: getMarginColor(data.average_profit_margin ?? 0)
    },
    {
      title: 'Top Profit Item',
      value: formatGP(data.highest_profit_amount ?? 0),
      subtitle: data.highest_profit_item ?? 'N/A',
      icon: Target,
      color: getProfitColor(data.highest_profit_amount ?? 0).split(' ')[0],
      bgColor: getProfitColor(data.highest_profit_amount ?? 0)
    },
    {
      title: 'Market Volatility',
      value: `${((data.market_volatility_score ?? 0) * 100).toFixed(0)}%`,
      subtitle: 'Market stability',
      icon: AlertTriangle,
      color: getVolatilityColor(data.market_volatility_score ?? 0),
      bgColor: getVolatilityColorWithBg(data.market_volatility_score ?? 0)
    }
  ];

  return (
    <div className="space-y-6">
      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
        {stats.map((stat, index) => {
          const Icon = stat.icon;
          return (
            <div key={index} className={`backdrop-blur-md border rounded-xl p-4 sm:p-6 space-y-3 ${stat.bgColor}`}>
              <div className="flex items-center justify-between">
                <div className="text-sm font-medium text-gray-400">
                  {stat.title}
                </div>
                <Icon className={`w-5 h-5 ${stat.color}`} />
              </div>
              <div className={`text-xl sm:text-2xl font-bold ${stat.color}`}>
                {stat.value}
              </div>
              <div className="text-xs text-gray-400 truncate">
                {stat.subtitle}
              </div>
            </div>
          );
        })}
      </div>

      {/* Market Summary */}
      <Card className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-white">Market Summary</h3>
          {data.data_freshness && (
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${
                data.data_freshness === 'fresh' ? 'bg-green-400' :
                data.data_freshness === 'recent' ? 'bg-yellow-400' :
                data.data_freshness === 'mock' ? 'bg-purple-400' :
                'bg-red-400'
              }`} />
              <span className="text-xs text-gray-400 capitalize">
                {data.data_freshness === 'mock' ? 'Demo Data' : 
                 data.data_age_hours !== undefined ? `${data.data_age_hours.toFixed(1)}h old` : 
                 data.data_freshness}
              </span>
              {data.data_freshness !== 'mock' && (
                <span className="text-xs text-blue-400">
                  Multi-source
                </span>
              )}
            </div>
          )}
        </div>
        
        {data.message && data.data_freshness === 'mock' && (
          <div className="backdrop-blur-md bg-purple-500/10 border border-purple-500/20 rounded-lg p-3 mb-4">
            <div className="flex items-start gap-2">
              <div className="text-purple-400 text-sm font-semibold">Demo Mode</div>
            </div>
            <div className="text-xs text-gray-300 mt-1">
              Showing sample data for demonstration. Connect to live market data for real-time analysis.
            </div>
          </div>
        )}
        
        {/* Multi-source data quality information */}
        {data.data_freshness && data.data_freshness !== 'mock' && (
          <div className="backdrop-blur-md bg-blue-500/10 border border-blue-500/20 rounded-lg p-3 mb-4">
            <div className="flex items-start gap-2">
              <div className="text-blue-400 text-sm font-semibold">Multi-Source Intelligence</div>
            </div>
            <div className="text-xs text-gray-300 mt-1">
              Price data aggregated from Weird Gloop API, RuneScape Wiki timeseries, and fallback sources for maximum accuracy and freshness.
            </div>
            {data.data_age_hours !== undefined && data.data_age_hours > 24 && (
              <div className="text-xs text-yellow-400 mt-1">
                ⚠️ Some price data may be stale. Consider refreshing for latest market conditions.
              </div>
            )}
          </div>
        )}
        
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
          <div className="space-y-2">
            <div className="text-sm text-gray-400">Market Condition</div>
            <Badge 
              variant={getRiskBadgeVariant(data.recommended_risk_level ?? 'conservative')} 
              className="capitalize"
            >
              {data.recommended_risk_level ?? 'N/A'}
            </Badge>
          </div>
          <div className="space-y-2">
            <div className="text-sm text-gray-400">Volatility Level</div>
            <div className={`font-medium ${getVolatilityColor(data.market_volatility_score ?? 0)}`}>
              {(data.market_volatility_score ?? 0) < 0.3 ? 'Low' : 
               (data.market_volatility_score ?? 0) < 0.7 ? 'Medium' : 'High'}
            </div>
          </div>
          <div className="space-y-2">
            <div className="text-sm text-gray-400">Recommendation</div>
            <div className="text-sm text-white">
              {(data.recommended_risk_level ?? 'conservative') === 'conservative' ? 
                'Focus on stable, low-risk items' :
               (data.recommended_risk_level ?? 'conservative') === 'moderate' ?
                'Balance risk with profit potential' :
                'High-risk, high-reward opportunities'}
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
};