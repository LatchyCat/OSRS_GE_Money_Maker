import React, { useMemo } from 'react';
import { motion } from 'framer-motion';
import { Shield, AlertTriangle, TrendingUp, Target, Activity, Zap } from 'lucide-react';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import type { Item } from '../../types';

interface RiskAnalysisProps {
  items: Item[];
}

interface RiskProfile {
  level: 'low' | 'medium' | 'high';
  score: number;
  factors: string[];
  recommendation: string;
}

interface RiskMetric {
  name: string;
  value: number;
  risk: 'low' | 'medium' | 'high';
  description: string;
}

export const RiskAnalysis: React.FC<RiskAnalysisProps> = ({ items }) => {
  const formatGP = (amount: number) => {
    if (amount >= 1000000) return `${(amount / 1000000).toFixed(1)}M`;
    if (amount >= 1000) return `${(amount / 1000).toFixed(1)}K`;
    return amount.toString();
  };

  const riskAnalysis = useMemo(() => {
    const profitableItems = items.filter(item => (item.current_profit || 0) > 0);
    
    if (profitableItems.length === 0) {
      return {
        overallRisk: { level: 'high' as const, score: 85 },
        metrics: [],
        portfolioRisk: 'high' as const,
        diversification: 0
      };
    }

    // Calculate various risk metrics
    const profits = profitableItems.map(item => item.current_profit || 0);
    const volumes = profitableItems.map(item => item.profit_calc?.daily_volume || 0);
    const volatilities = profitableItems.map(item => item.profit_calc?.price_volatility || 0);

    // Price volatility risk
    const avgVolatility = volatilities.reduce((a, b) => a + b, 0) / volatilities.length;
    const volatilityRisk = avgVolatility > 0.7 ? 'high' : avgVolatility > 0.4 ? 'medium' : 'low';

    // Volume concentration risk
    const totalVolume = volumes.reduce((a, b) => a + b, 0);
    const maxVolume = Math.max(...volumes);
    const volumeConcentration = totalVolume > 0 ? (maxVolume / totalVolume) : 0;
    const concentrationRisk = volumeConcentration > 0.5 ? 'high' : volumeConcentration > 0.3 ? 'medium' : 'low';

    // Profit consistency risk
    const avgProfit = profits.reduce((a, b) => a + b, 0) / profits.length;
    const profitStdDev = Math.sqrt(profits.reduce((sum, p) => sum + Math.pow(p - avgProfit, 2), 0) / profits.length);
    const coefficientOfVariation = avgProfit > 0 ? (profitStdDev / avgProfit) : 1;
    const consistencyRisk = coefficientOfVariation > 1.5 ? 'high' : coefficientOfVariation > 1 ? 'medium' : 'low';

    // Market depth risk (based on volume)
    const avgVolume = volumes.reduce((a, b) => a + b, 0) / volumes.length;
    const depthRisk = avgVolume < 1000 ? 'high' : avgVolume < 5000 ? 'medium' : 'low';

    // Diversification score
    const diversificationScore = Math.min(100, (profitableItems.length / 20) * 100);
    const diversificationRisk = diversificationScore < 30 ? 'high' : diversificationScore < 60 ? 'medium' : 'low';

    const metrics: RiskMetric[] = [
      {
        name: 'Price Volatility',
        value: avgVolatility * 100,
        risk: volatilityRisk,
        description: 'Average price volatility across all items'
      },
      {
        name: 'Volume Concentration',
        value: volumeConcentration * 100,
        risk: concentrationRisk,
        description: 'Percentage of volume concentrated in top item'
      },
      {
        name: 'Profit Consistency',
        value: coefficientOfVariation * 100,
        risk: consistencyRisk,
        description: 'Variability in profit margins'
      },
      {
        name: 'Market Depth',
        value: avgVolume,
        risk: depthRisk,
        description: 'Average daily trading volume'
      },
      {
        name: 'Diversification',
        value: diversificationScore,
        risk: diversificationRisk,
        description: 'Portfolio diversification score'
      }
    ];

    // Calculate overall risk score
    const riskScores = {
      low: 0,
      medium: 50,
      high: 100
    };

    const overallScore = metrics.reduce((sum, metric) => sum + riskScores[metric.risk], 0) / metrics.length;
    const overallLevel = overallScore > 70 ? 'high' : overallScore > 40 ? 'medium' : 'low';

    return {
      overallRisk: { level: overallLevel, score: overallScore },
      metrics,
      portfolioRisk: overallLevel,
      diversification: diversificationScore
    };
  }, [items]);

  const getRiskProfile = (level: 'low' | 'medium' | 'high'): RiskProfile => {
    switch (level) {
      case 'low':
        return {
          level,
          score: riskAnalysis.overallRisk.score,
          factors: ['Stable price movements', 'Consistent volumes', 'Good diversification'],
          recommendation: 'Conservative strategy - focus on steady profits with minimal risk'
        };
      case 'medium':
        return {
          level,
          score: riskAnalysis.overallRisk.score,
          factors: ['Moderate volatility', 'Mixed volume patterns', 'Partial diversification'],
          recommendation: 'Balanced strategy - mix of safe and opportunistic trades'
        };
      case 'high':
        return {
          level,
          score: riskAnalysis.overallRisk.score,
          factors: ['High price volatility', 'Concentrated positions', 'Limited diversification'],
          recommendation: 'Aggressive strategy - requires careful monitoring and risk management'
        };
    }
  };

  const getRiskColor = (risk: 'low' | 'medium' | 'high') => {
    switch (risk) {
      case 'low': return { text: 'text-green-400', bg: 'bg-green-500/10 border-green-500/20' };
      case 'medium': return { text: 'text-yellow-400', bg: 'bg-yellow-500/10 border-yellow-500/20' };
      case 'high': return { text: 'text-red-400', bg: 'bg-red-500/10 border-red-500/20' };
    }
  };

  const riskProfile = getRiskProfile(riskAnalysis.overallRisk.level);
  const overallColors = getRiskColor(riskAnalysis.overallRisk.level);

  const highRiskItems = items
    .filter(item => (item.profit_calc?.price_volatility || 0) > 0.6)
    .sort((a, b) => (b.profit_calc?.price_volatility || 0) - (a.profit_calc?.price_volatility || 0))
    .slice(0, 5);

  const safeItems = items
    .filter(item => (item.profit_calc?.price_volatility || 0) < 0.3 && (item.current_profit || 0) > 0)
    .sort((a, b) => (b.current_profit || 0) - (a.current_profit || 0))
    .slice(0, 5);

  return (
    <div className="space-y-6">
      {/* Overall Risk Assessment */}
      <Card className={`p-6 border ${overallColors.bg}`}>
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <Shield className="w-5 h-5 text-accent-400" />
            <h3 className="text-lg font-semibold text-white">Risk Assessment</h3>
          </div>
          <Badge variant={riskProfile.level === 'low' ? 'success' : riskProfile.level === 'medium' ? 'warning' : 'danger'}>
            {riskProfile.level.charAt(0).toUpperCase() + riskProfile.level.slice(1)} Risk
          </Badge>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="space-y-4">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-gray-400">Overall Risk Score</span>
                <span className={`font-bold ${overallColors.text}`}>
                  {riskProfile.score.toFixed(0)}/100
                </span>
              </div>
              <div className="w-full bg-white/10 rounded-full h-2">
                <div 
                  className="h-2 rounded-full transition-all"
                  style={{
                    width: `${riskProfile.score}%`,
                    backgroundColor: riskProfile.level === 'low' ? 'rgb(34 197 94)' : 
                                   riskProfile.level === 'medium' ? 'rgb(245 158 11)' : 'rgb(239 68 68)'
                  }}
                />
              </div>
            </div>

            <div className="space-y-2">
              <div className="text-sm font-medium text-gray-300">Key Risk Factors</div>
              <div className="space-y-1">
                {riskProfile.factors.map((factor, index) => (
                  <div key={index} className="flex items-center gap-2 text-sm text-gray-400">
                    <div className="w-1.5 h-1.5 rounded-full bg-gray-500" />
                    {factor}
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="space-y-4">
            <div>
              <div className="text-sm font-medium text-gray-300 mb-2">Recommendation</div>
              <div className="text-sm text-gray-400 leading-relaxed">
                {riskProfile.recommendation}
              </div>
            </div>

            <div className="flex items-center gap-4">
              <div className="text-center">
                <div className="text-xs text-gray-400 mb-1">Diversification</div>
                <div className={`text-lg font-bold ${
                  riskAnalysis.diversification > 60 ? 'text-green-400' :
                  riskAnalysis.diversification > 30 ? 'text-yellow-400' : 'text-red-400'
                }`}>
                  {riskAnalysis.diversification.toFixed(0)}%
                </div>
              </div>
              <div className="text-center">
                <div className="text-xs text-gray-400 mb-1">Items Tracked</div>
                <div className="text-lg font-bold text-blue-400">
                  {items.length}
                </div>
              </div>
            </div>
          </div>
        </div>
      </Card>

      {/* Risk Metrics */}
      <Card className="p-6 space-y-6">
        <div className="flex items-center gap-2">
          <Activity className="w-5 h-5 text-blue-400" />
          <h3 className="text-lg font-semibold text-white">Risk Metrics</h3>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {riskAnalysis.metrics.map((metric, index) => {
            const colors = getRiskColor(metric.risk);
            const Icon = metric.name === 'Price Volatility' ? TrendingUp :
                        metric.name === 'Volume Concentration' ? Target :
                        metric.name === 'Profit Consistency' ? Activity :
                        metric.name === 'Market Depth' ? Zap : Shield;

            return (
              <motion.div
                key={metric.name}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.1 * index }}
                className={`p-4 rounded-lg border ${colors.bg}`}
              >
                <div className="flex items-center justify-between mb-2">
                  <Icon className={`w-4 h-4 ${colors.text}`} />
                  <Badge variant={metric.risk === 'low' ? 'success' : metric.risk === 'medium' ? 'warning' : 'danger'} size="sm">
                    {metric.risk}
                  </Badge>
                </div>
                <div className="space-y-1">
                  <div className="text-sm font-medium text-white">{metric.name}</div>
                  <div className={`text-lg font-bold ${colors.text}`}>
                    {metric.name === 'Market Depth' ? formatGP(metric.value) : `${metric.value.toFixed(0)}%`}
                  </div>
                  <div className="text-xs text-gray-400 leading-tight">
                    {metric.description}
                  </div>
                </div>
              </motion.div>
            );
          })}
        </div>
      </Card>

      {/* High Risk & Safe Items */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="p-6 space-y-4">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-red-400" />
            <h3 className="text-lg font-semibold text-white">High Risk Items</h3>
          </div>
          <div className="space-y-3">
            {highRiskItems.map((item) => (
              <div key={item.item_id} className="flex items-center justify-between p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
                <div>
                  <div className="font-medium text-white truncate max-w-32">{item.name}</div>
                  <div className="text-xs text-red-400">High volatility</div>
                </div>
                <div className="text-right">
                  <div className="font-bold text-red-400">
                    {((item.profit_calc?.price_volatility || 0) * 100).toFixed(0)}%
                  </div>
                  <div className="text-xs text-gray-400">
                    {formatGP(item.current_profit || 0)} GP
                  </div>
                </div>
              </div>
            ))}
            {highRiskItems.length === 0 && (
              <div className="text-center py-4 text-gray-400 bg-green-500/10 border border-green-500/20 rounded-lg">
                No high-risk items detected
              </div>
            )}
          </div>
        </Card>

        <Card className="p-6 space-y-4">
          <div className="flex items-center gap-2">
            <Shield className="w-5 h-5 text-green-400" />
            <h3 className="text-lg font-semibold text-white">Safe Investments</h3>
          </div>
          <div className="space-y-3">
            {safeItems.map((item) => (
              <div key={item.item_id} className="flex items-center justify-between p-3 bg-green-500/10 border border-green-500/20 rounded-lg">
                <div>
                  <div className="font-medium text-white truncate max-w-32">{item.name}</div>
                  <div className="text-xs text-green-400">Low volatility</div>
                </div>
                <div className="text-right">
                  <div className="font-bold text-green-400">
                    {formatGP(item.current_profit || 0)} GP
                  </div>
                  <div className="text-xs text-gray-400">
                    {((item.profit_calc?.price_volatility || 0) * 100).toFixed(0)}% vol
                  </div>
                </div>
              </div>
            ))}
            {safeItems.length === 0 && (
              <div className="text-center py-4 text-gray-400">
                No safe items with profits found
              </div>
            )}
          </div>
        </Card>
      </div>

      {/* Risk Management Tips */}
      <Card className="p-6 space-y-4">
        <div className="flex items-center gap-2">
          <Target className="w-5 h-5 text-purple-400" />
          <h3 className="text-lg font-semibold text-white">Risk Management Tips</h3>
        </div>
        
        <div className="bg-white/5 rounded-lg p-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-gray-300">
            <div className="space-y-2">
              <div className="font-medium text-accent-400">Portfolio Management</div>
              <ul className="space-y-1">
                <li>• Diversify across different item categories</li>
                <li>• Limit exposure to high-volatility items</li>
                <li>• Monitor volume concentration regularly</li>
              </ul>
            </div>
            <div className="space-y-2">
              <div className="font-medium text-accent-400">Trading Strategy</div>
              <ul className="space-y-1">
                <li>• Set stop-loss limits for volatile items</li>
                <li>• Focus on consistent profit margins</li>
                <li>• Adjust position sizes based on risk level</li>
              </ul>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
};