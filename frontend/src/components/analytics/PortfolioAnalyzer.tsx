import React, { useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { 
  PieChart, 
  BarChart3, 
  TrendingUp, 
  Target, 
  Shield, 
  Zap,
  Package,
  DollarSign,
  AlertCircle,
  CheckCircle
} from 'lucide-react';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import type { Item } from '../../types';

interface PortfolioAnalyzerProps {
  items: Item[];
  selectedItems?: Item[];
  onSelectionChange?: (items: Item[]) => void;
}

interface PortfolioMetrics {
  totalValue: number;
  totalProfit: number;
  avgProfit: number;
  profitabilityRate: number;
  riskScore: number;
  diversificationScore: number;
  volatilityIndex: number;
  maxDrawdown: number;
}

interface AllocationCategory {
  name: string;
  value: number;
  percentage: number;
  items: Item[];
  color: string;
  risk: 'low' | 'medium' | 'high';
}

export const PortfolioAnalyzer: React.FC<PortfolioAnalyzerProps> = ({
  items,
  selectedItems = [],
  onSelectionChange
}) => {
  const [viewMode, setViewMode] = useState<'allocation' | 'risk' | 'performance'>('allocation');

  const formatGP = (amount: number) => {
    if (amount >= 1000000) return `${(amount / 1000000).toFixed(1)}M`;
    if (amount >= 1000) return `${(amount / 1000).toFixed(1)}K`;
    return amount.toString();
  };

  const portfolioMetrics = useMemo((): PortfolioMetrics => {
    const analysisItems = selectedItems.length > 0 ? selectedItems : items;
    const profitableItems = analysisItems.filter(item => (item.current_profit || 0) > 0);

    const totalProfit = profitableItems.reduce((sum, item) => sum + (item.current_profit || 0), 0);
    const totalValue = analysisItems.reduce((sum, item) => sum + (item.high_alch_profit || 0), 0);
    const avgProfit = profitableItems.length > 0 ? totalProfit / profitableItems.length : 0;
    const profitabilityRate = analysisItems.length > 0 ? (profitableItems.length / analysisItems.length) * 100 : 0;

    // Risk calculations
    const volatilities = analysisItems.map(item => item.profit_calc?.price_volatility || 0);
    const avgVolatility = volatilities.reduce((sum, v) => sum + v, 0) / volatilities.length;
    const riskScore = Math.min(100, avgVolatility * 100);

    // Diversification score based on item variety and profit distribution
    const uniqueCategories = new Set(analysisItems.map(item => item.name.split(' ')[0])).size;
    const diversificationScore = Math.min(100, (uniqueCategories / Math.max(analysisItems.length * 0.1, 5)) * 100);

    // Volatility index
    const profits = profitableItems.map(item => item.current_profit || 0);
    const profitStdDev = profits.length > 0 ? 
      Math.sqrt(profits.reduce((sum, p) => sum + Math.pow(p - avgProfit, 2), 0) / profits.length) : 0;
    const volatilityIndex = avgProfit > 0 ? (profitStdDev / avgProfit) * 100 : 0;

    // Max drawdown (simulated)
    const maxDrawdown = Math.min(50, riskScore * 0.5);

    return {
      totalValue,
      totalProfit,
      avgProfit,
      profitabilityRate,
      riskScore,
      diversificationScore,
      volatilityIndex,
      maxDrawdown
    };
  }, [items, selectedItems]);

  const allocationData = useMemo((): AllocationCategory[] => {
    const analysisItems = selectedItems.length > 0 ? selectedItems : items;
    const profitableItems = analysisItems.filter(item => (item.current_profit || 0) > 0);

    // Group items by profit ranges
    const categories: AllocationCategory[] = [
      {
        name: 'High Profit (500+ GP)',
        value: 0,
        percentage: 0,
        items: [],
        color: 'rgb(34 197 94)',
        risk: 'medium'
      },
      {
        name: 'Medium Profit (100-500 GP)',
        value: 0,
        percentage: 0,
        items: [],
        color: 'rgb(59 130 246)',
        risk: 'low'
      },
      {
        name: 'Low Profit (50-100 GP)',
        value: 0,
        percentage: 0,
        items: [],
        color: 'rgb(245 158 11)',
        risk: 'low'
      },
      {
        name: 'Minimal Profit (0-50 GP)',
        value: 0,
        percentage: 0,
        items: [],
        color: 'rgb(107 114 128)',
        risk: 'high'
      }
    ];

    profitableItems.forEach(item => {
      const profit = item.current_profit || 0;
      if (profit >= 500) {
        categories[0].items.push(item);
        categories[0].value += profit;
      } else if (profit >= 100) {
        categories[1].items.push(item);
        categories[1].value += profit;
      } else if (profit >= 50) {
        categories[2].items.push(item);
        categories[2].value += profit;
      } else {
        categories[3].items.push(item);
        categories[3].value += profit;
      }
    });

    const totalValue = categories.reduce((sum, cat) => sum + cat.value, 0);
    categories.forEach(cat => {
      cat.percentage = totalValue > 0 ? (cat.value / totalValue) * 100 : 0;
    });

    return categories.filter(cat => cat.items.length > 0);
  }, [items, selectedItems]);

  const getHealthStatus = () => {
    const { profitabilityRate, riskScore, diversificationScore } = portfolioMetrics;
    
    if (profitabilityRate >= 60 && riskScore < 40 && diversificationScore >= 60) {
      return { status: 'excellent', color: 'text-green-400', icon: CheckCircle };
    } else if (profitabilityRate >= 40 && riskScore < 60) {
      return { status: 'good', color: 'text-blue-400', icon: TrendingUp };
    } else if (profitabilityRate >= 25) {
      return { status: 'fair', color: 'text-yellow-400', icon: AlertCircle };
    } else {
      return { status: 'poor', color: 'text-red-400', icon: AlertCircle };
    }
  };

  const healthStatus = getHealthStatus();
  const HealthIcon = healthStatus.icon;

  const topPerformers = (selectedItems.length > 0 ? selectedItems : items)
    .filter(item => (item.current_profit || 0) > 0)
    .sort((a, b) => (b.current_profit || 0) - (a.current_profit || 0))
    .slice(0, 5);

  const suggestions = useMemo(() => {
    const suggestions = [];
    const { profitabilityRate, riskScore, diversificationScore } = portfolioMetrics;

    if (profitabilityRate < 50) {
      suggestions.push({
        type: 'improvement',
        title: 'Low Profitability',
        description: 'Consider filtering out items with profits below 100 GP',
        action: 'Remove low-profit items'
      });
    }

    if (riskScore > 60) {
      suggestions.push({
        type: 'warning',
        title: 'High Risk Portfolio',
        description: 'Portfolio has high volatility - consider adding stable items',
        action: 'Add low-volatility items'
      });
    }

    if (diversificationScore < 40) {
      suggestions.push({
        type: 'improvement',
        title: 'Poor Diversification',
        description: 'Portfolio is too concentrated - spread across more item types',
        action: 'Diversify holdings'
      });
    }

    if (allocationData[0]?.percentage > 70) {
      suggestions.push({
        type: 'warning',
        title: 'Over-concentration',
        description: 'Too much allocation in single category creates risk',
        action: 'Rebalance allocation'
      });
    }

    return suggestions;
  }, [portfolioMetrics, allocationData]);

  return (
    <div className="space-y-6">
      {/* Portfolio Overview */}
      <Card className="p-6 space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <PieChart className="w-5 h-5 text-accent-400" />
            <h3 className="text-lg font-semibold text-white">Portfolio Analysis</h3>
          </div>
          <div className="flex items-center gap-2">
            <HealthIcon className={`w-5 h-5 ${healthStatus.color}`} />
            <Badge variant={
              healthStatus.status === 'excellent' ? 'success' :
              healthStatus.status === 'good' ? 'warning' :
              healthStatus.status === 'fair' ? 'secondary' : 'danger'
            }>
              {healthStatus.status.charAt(0).toUpperCase() + healthStatus.status.slice(1)}
            </Badge>
          </div>
        </div>

        {/* Key Metrics */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="text-center p-3 bg-white/5 rounded-lg">
            <div className="text-sm text-gray-400 mb-1">Total Profit</div>
            <div className="text-xl font-bold text-green-400">
              {formatGP(portfolioMetrics.totalProfit)} GP
            </div>
          </div>
          <div className="text-center p-3 bg-white/5 rounded-lg">
            <div className="text-sm text-gray-400 mb-1">Avg Profit</div>
            <div className="text-xl font-bold text-blue-400">
              {formatGP(portfolioMetrics.avgProfit)} GP
            </div>
          </div>
          <div className="text-center p-3 bg-white/5 rounded-lg">
            <div className="text-sm text-gray-400 mb-1">Success Rate</div>
            <div className="text-xl font-bold text-purple-400">
              {portfolioMetrics.profitabilityRate.toFixed(1)}%
            </div>
          </div>
          <div className="text-center p-3 bg-white/5 rounded-lg">
            <div className="text-sm text-gray-400 mb-1">Risk Score</div>
            <div className={`text-xl font-bold ${
              portfolioMetrics.riskScore < 40 ? 'text-green-400' :
              portfolioMetrics.riskScore < 60 ? 'text-yellow-400' : 'text-red-400'
            }`}>
              {portfolioMetrics.riskScore.toFixed(0)}
            </div>
          </div>
        </div>
      </Card>

      {/* View Mode Selector */}
      <div className="flex items-center gap-2">
        {[
          { key: 'allocation', label: 'Allocation', icon: PieChart },
          { key: 'risk', label: 'Risk Analysis', icon: Shield },
          { key: 'performance', label: 'Performance', icon: BarChart3 }
        ].map(({ key, label, icon: Icon }) => (
          <Button
            key={key}
            variant={viewMode === key ? 'primary' : 'outline'}
            size="sm"
            onClick={() => setViewMode(key as any)}
            className="flex items-center gap-2"
          >
            <Icon className="w-4 h-4" />
            {label}
          </Button>
        ))}
      </div>

      {/* Allocation View */}
      {viewMode === 'allocation' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card className="p-6 space-y-4">
            <h4 className="font-semibold text-white flex items-center gap-2">
              <Target className="w-4 h-4" />
              Portfolio Allocation
            </h4>
            
            <div className="space-y-3">
              {allocationData.map((category, index) => (
                <motion.div
                  key={category.name}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.1 * index }}
                  className="space-y-2"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div 
                        className="w-3 h-3 rounded-full"
                        style={{ backgroundColor: category.color }}
                      />
                      <span className="text-sm font-medium text-white">{category.name}</span>
                    </div>
                    <div className="text-sm text-gray-400">
                      {category.percentage.toFixed(1)}%
                    </div>
                  </div>
                  <div className="w-full bg-white/10 rounded-full h-2">
                    <div 
                      className="h-2 rounded-full transition-all"
                      style={{
                        width: `${category.percentage}%`,
                        backgroundColor: category.color
                      }}
                    />
                  </div>
                  <div className="flex items-center justify-between text-xs text-gray-400">
                    <span>{category.items.length} items</span>
                    <span>{formatGP(category.value)} GP</span>
                  </div>
                </motion.div>
              ))}
            </div>
          </Card>

          <Card className="p-6 space-y-4">
            <h4 className="font-semibold text-white flex items-center gap-2">
              <TrendingUp className="w-4 h-4" />
              Top Performers
            </h4>
            
            <div className="space-y-3">
              {topPerformers.map((item, index) => (
                <div key={item.item_id} className="flex items-center justify-between p-3 bg-white/5 rounded-lg">
                  <div>
                    <div className="font-medium text-white truncate max-w-32">{item.name}</div>
                    <div className="text-xs text-gray-400">
                      {((item.current_profit_margin || 0) * 100).toFixed(1)}% margin
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-bold text-green-400">
                      {formatGP(item.current_profit || 0)} GP
                    </div>
                    <div className="text-xs text-gray-400">
                      #{index + 1}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}

      {/* Risk Analysis View */}
      {viewMode === 'risk' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card className="p-6 space-y-4">
            <h4 className="font-semibold text-white flex items-center gap-2">
              <Shield className="w-4 h-4" />
              Risk Metrics
            </h4>
            
            <div className="space-y-4">
              {[
                { label: 'Volatility Index', value: portfolioMetrics.volatilityIndex, max: 100, unit: '%' },
                { label: 'Diversification Score', value: portfolioMetrics.diversificationScore, max: 100, unit: '%' },
                { label: 'Max Drawdown', value: portfolioMetrics.maxDrawdown, max: 50, unit: '%' }
              ].map((metric) => (
                <div key={metric.label}>
                  <div className="flex justify-between mb-2">
                    <span className="text-sm text-gray-300">{metric.label}</span>
                    <span className="text-sm font-medium text-white">
                      {metric.value.toFixed(1)}{metric.unit}
                    </span>
                  </div>
                  <div className="w-full bg-white/10 rounded-full h-2">
                    <div 
                      className="h-2 rounded-full transition-all"
                      style={{
                        width: `${(metric.value / metric.max) * 100}%`,
                        backgroundColor: metric.value > metric.max * 0.7 ? 'rgb(239 68 68)' :
                                       metric.value > metric.max * 0.4 ? 'rgb(245 158 11)' : 'rgb(34 197 94)'
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </Card>

          <Card className="p-6 space-y-4">
            <h4 className="font-semibold text-white flex items-center gap-2">
              <Zap className="w-4 h-4" />
              Optimization Suggestions
            </h4>
            
            <div className="space-y-3">
              {suggestions.map((suggestion, index) => (
                <div key={index} className={`p-3 rounded-lg border ${
                  suggestion.type === 'warning' ? 'bg-yellow-500/10 border-yellow-500/20' :
                  'bg-blue-500/10 border-blue-500/20'
                }`}>
                  <div className={`font-medium mb-1 ${
                    suggestion.type === 'warning' ? 'text-yellow-400' : 'text-blue-400'
                  }`}>
                    {suggestion.title}
                  </div>
                  <div className="text-sm text-gray-300 mb-2">
                    {suggestion.description}
                  </div>
                  <Badge size="sm" variant={suggestion.type === 'warning' ? 'warning' : 'secondary'}>
                    {suggestion.action}
                  </Badge>
                </div>
              ))}
              
              {suggestions.length === 0 && (
                <div className="text-center py-4 text-green-400 bg-green-500/10 border border-green-500/20 rounded-lg">
                  <CheckCircle className="w-8 h-8 mx-auto mb-2" />
                  <div className="font-medium">Portfolio looks healthy!</div>
                  <div className="text-sm text-gray-300">No major issues detected</div>
                </div>
              )}
            </div>
          </Card>
        </div>
      )}

      {/* Performance View */}
      {viewMode === 'performance' && (
        <Card className="p-6 space-y-6">
          <h4 className="font-semibold text-white flex items-center gap-2">
            <BarChart3 className="w-4 h-4" />
            Performance Summary
          </h4>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              {
                title: 'Total Items',
                value: (selectedItems.length > 0 ? selectedItems : items).length,
                subtitle: 'In portfolio',
                icon: Package,
                color: 'text-blue-400'
              },
              {
                title: 'Profitable Items',
                value: (selectedItems.length > 0 ? selectedItems : items).filter(i => (i.current_profit || 0) > 0).length,
                subtitle: `${portfolioMetrics.profitabilityRate.toFixed(1)}% success`,
                icon: TrendingUp,
                color: 'text-green-400'
              },
              {
                title: 'Total Profit',
                value: formatGP(portfolioMetrics.totalProfit),
                subtitle: 'Combined profit',
                icon: DollarSign,
                color: 'text-purple-400'
              },
              {
                title: 'Risk Level',
                value: portfolioMetrics.riskScore < 40 ? 'Low' : portfolioMetrics.riskScore < 60 ? 'Medium' : 'High',
                subtitle: `${portfolioMetrics.riskScore.toFixed(0)} risk score`,
                icon: Shield,
                color: portfolioMetrics.riskScore < 40 ? 'text-green-400' : 
                       portfolioMetrics.riskScore < 60 ? 'text-yellow-400' : 'text-red-400'
              }
            ].map((stat, index) => {
              const Icon = stat.icon;
              return (
                <motion.div
                  key={stat.title}
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: 0.1 * index }}
                  className="text-center p-4 bg-white/5 rounded-lg"
                >
                  <Icon className={`w-8 h-8 mx-auto mb-2 ${stat.color}`} />
                  <div className={`text-2xl font-bold mb-1 ${stat.color}`}>
                    {stat.value}
                  </div>
                  <div className="text-sm text-gray-400">{stat.subtitle}</div>
                </motion.div>
              );
            })}
          </div>
        </Card>
      )}
    </div>
  );
};