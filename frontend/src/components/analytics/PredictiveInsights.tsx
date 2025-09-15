import React, { useMemo } from 'react';
import { motion } from 'framer-motion';
import { TrendingUp, TrendingDown, Brain, Zap, Target, AlertTriangle, Lightbulb } from 'lucide-react';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import type { Item } from '../../types';

interface PredictiveInsightsProps {
  items: Item[];
  timeRange: '24h' | '7d' | '30d' | '90d';
}

interface Prediction {
  type: 'price_increase' | 'price_decrease' | 'volume_spike' | 'opportunity' | 'risk_warning';
  confidence: number;
  item: Item;
  prediction: string;
  reasoning: string;
  timeframe: string;
  impact: 'low' | 'medium' | 'high';
}

interface MarketTrend {
  direction: 'bullish' | 'bearish' | 'sideways';
  strength: number;
  duration: string;
  confidence: number;
}

export const PredictiveInsights: React.FC<PredictiveInsightsProps> = ({ items, timeRange }) => {
  const formatGP = (amount: number) => {
    if (amount >= 1000000) return `${(amount / 1000000).toFixed(1)}M`;
    if (amount >= 1000) return `${(amount / 1000).toFixed(1)}K`;
    return amount.toString();
  };

  const predictions = useMemo(() => {
    const profitableItems = items.filter(item => (item.current_profit || 0) > 0);
    const predictions: Prediction[] = [];

    // Generate various types of predictions
    profitableItems.forEach(item => {
      const profit = item.current_profit || 0;
      const volume = item.profit_calc?.daily_volume || 0;
      const volatility = item.profit_calc?.price_volatility || 0;
      const margin = item.current_profit_margin || 0;

      // Price increase predictions (based on volume and low volatility)
      if (volume > 5000 && volatility < 0.3 && profit > 100) {
        predictions.push({
          type: 'price_increase',
          confidence: Math.min(95, 60 + (volume / 1000) * 2 + (profit / 10)),
          item,
          prediction: `Price expected to rise by 15-25%`,
          reasoning: `High volume (${volume.toLocaleString()}) with low volatility indicates strong demand`,
          timeframe: timeRange === '24h' ? '2-4 hours' : timeRange === '7d' ? '1-2 days' : '3-7 days',
          impact: profit > 500 ? 'high' : profit > 200 ? 'medium' : 'low'
        });
      }

      // Volume spike predictions (based on recent profit changes)
      if (margin > 0.2 && profit > 200) {
        predictions.push({
          type: 'volume_spike',
          confidence: Math.min(90, 50 + margin * 100),
          item,
          prediction: `Trading volume expected to increase 40-60%`,
          reasoning: `High profit margin (${margin.toFixed(1)}%) attracting more traders`,
          timeframe: timeRange === '24h' ? '1-2 hours' : timeRange === '7d' ? '6-12 hours' : '1-3 days',
          impact: 'medium'
        });
      }

      // Risk warnings (high volatility items)
      if (volatility > 0.6 && profit > 300) {
        predictions.push({
          type: 'risk_warning',
          confidence: Math.min(85, 70 + volatility * 20),
          item,
          prediction: `Price volatility may increase`,
          reasoning: `Current volatility (${(volatility * 100).toFixed(0)}%) above safe threshold`,
          timeframe: 'Next 24 hours',
          impact: 'high'
        });
      }

      // Opportunity predictions (undervalued items)
      if (profit > 150 && volume < 2000 && volatility < 0.4) {
        predictions.push({
          type: 'opportunity',
          confidence: Math.min(80, 45 + profit / 5),
          item,
          prediction: `Hidden gem - low competition opportunity`,
          reasoning: `Good profit (${formatGP(profit)} GP) with low volume suggests undiscovered potential`,
          timeframe: 'Next 2-7 days',
          impact: profit > 400 ? 'high' : 'medium'
        });
      }
    });

    // Sort by confidence and limit to top 8 predictions
    return predictions.sort((a, b) => b.confidence - a.confidence).slice(0, 8);
  }, [items, timeRange]);

  const marketTrend = useMemo((): MarketTrend => {
    const profitableItems = items.filter(item => (item.current_profit || 0) > 0);
    const totalProfit = profitableItems.reduce((sum, item) => sum + (item.current_profit || 0), 0);
    const avgVolatility = profitableItems.reduce((sum, item) => sum + (item.profit_calc?.price_volatility || 0), 0) / profitableItems.length;
    
    const profitabilityRatio = items.length > 0 ? profitableItems.length / items.length : 0;
    const avgProfit = profitableItems.length > 0 ? totalProfit / profitableItems.length : 0;

    let direction: MarketTrend['direction'] = 'sideways';
    let strength = 50;

    if (profitabilityRatio > 0.6 && avgProfit > 300) {
      direction = 'bullish';
      strength = 65 + profitabilityRatio * 20 + Math.min(avgProfit / 20, 15);
    } else if (profitabilityRatio < 0.3 || avgVolatility > 0.7) {
      direction = 'bearish';
      strength = 35 - profitabilityRatio * 20 + avgVolatility * 30;
    }

    return {
      direction,
      strength: Math.min(100, Math.max(0, strength)),
      duration: timeRange === '24h' ? '2-6 hours' : timeRange === '7d' ? '1-3 days' : '1-2 weeks',
      confidence: Math.min(95, 60 + (profitableItems.length / items.length) * 30)
    };
  }, [items, timeRange]);

  const getPredictionIcon = (type: Prediction['type']) => {
    switch (type) {
      case 'price_increase': return TrendingUp;
      case 'price_decrease': return TrendingDown;
      case 'volume_spike': return Zap;
      case 'opportunity': return Target;
      case 'risk_warning': return AlertTriangle;
      default: return Lightbulb;
    }
  };

  const getPredictionColor = (type: Prediction['type']) => {
    switch (type) {
      case 'price_increase': return { text: 'text-green-400', bg: 'bg-green-500/10 border-green-500/20' };
      case 'price_decrease': return { text: 'text-red-400', bg: 'bg-red-500/10 border-red-500/20' };
      case 'volume_spike': return { text: 'text-blue-400', bg: 'bg-blue-500/10 border-blue-500/20' };
      case 'opportunity': return { text: 'text-purple-400', bg: 'bg-purple-500/10 border-purple-500/20' };
      case 'risk_warning': return { text: 'text-yellow-400', bg: 'bg-yellow-500/10 border-yellow-500/20' };
      default: return { text: 'text-gray-400', bg: 'bg-gray-500/10 border-gray-500/20' };
    }
  };

  const getConfidenceBadge = (confidence: number) => {
    if (confidence >= 80) return { variant: 'success' as const, text: 'High' };
    if (confidence >= 60) return { variant: 'warning' as const, text: 'Medium' };
    return { variant: 'secondary' as const, text: 'Low' };
  };

  const getImpactColor = (impact: 'low' | 'medium' | 'high') => {
    switch (impact) {
      case 'high': return 'text-red-400';
      case 'medium': return 'text-yellow-400';
      case 'low': return 'text-green-400';
    }
  };

  const getTrendColor = (direction: MarketTrend['direction']) => {
    switch (direction) {
      case 'bullish': return { text: 'text-green-400', bg: 'bg-green-500/10 border-green-500/20' };
      case 'bearish': return { text: 'text-red-400', bg: 'bg-red-500/10 border-red-500/20' };
      case 'sideways': return { text: 'text-gray-400', bg: 'bg-gray-500/10 border-gray-500/20' };
    }
  };

  const trendColors = getTrendColor(marketTrend.direction);

  return (
    <div className="space-y-6">
      {/* Market Trend Analysis */}
      <Card className={`p-6 border ${trendColors.bg}`}>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Brain className="w-5 h-5 text-accent-400" />
            <h3 className="text-lg font-semibold text-white">Market Trend Analysis</h3>
          </div>
          <Badge variant={marketTrend.direction === 'bullish' ? 'success' : marketTrend.direction === 'bearish' ? 'danger' : 'secondary'}>
            {marketTrend.direction.charAt(0).toUpperCase() + marketTrend.direction.slice(1)}
          </Badge>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
          <div className="text-center">
            <div className="text-sm text-gray-400 mb-1">Trend Strength</div>
            <div className={`text-2xl font-bold ${trendColors.text} mb-2`}>
              {marketTrend.strength.toFixed(0)}%
            </div>
            <div className="w-full bg-white/10 rounded-full h-2">
              <div 
                className="h-2 rounded-full transition-all"
                style={{
                  width: `${marketTrend.strength}%`,
                  backgroundColor: marketTrend.direction === 'bullish' ? 'rgb(34 197 94)' : 
                                 marketTrend.direction === 'bearish' ? 'rgb(239 68 68)' : 'rgb(107 114 128)'
                }}
              />
            </div>
          </div>

          <div className="text-center">
            <div className="text-sm text-gray-400 mb-1">Confidence</div>
            <div className="text-2xl font-bold text-blue-400 mb-2">
              {marketTrend.confidence.toFixed(0)}%
            </div>
            <div className="text-xs text-gray-400">
              Based on {items.length} items
            </div>
          </div>

          <div className="text-center">
            <div className="text-sm text-gray-400 mb-1">Expected Duration</div>
            <div className="text-lg font-medium text-white mb-2">
              {marketTrend.duration}
            </div>
            <div className="text-xs text-gray-400">
              For current trend
            </div>
          </div>
        </div>
      </Card>

      {/* AI Predictions */}
      <Card className="p-6 space-y-6">
        <div className="flex items-center gap-2">
          <Lightbulb className="w-5 h-5 text-accent-400" />
          <h3 className="text-lg font-semibold text-white">AI Predictions</h3>
          <Badge variant="accent" size="sm">
            {predictions.length} insights
          </Badge>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {predictions.map((prediction, index) => {
            const Icon = getPredictionIcon(prediction.type);
            const colors = getPredictionColor(prediction.type);
            const confidenceBadge = getConfidenceBadge(prediction.confidence);

            return (
              <motion.div
                key={`${prediction.item.item_id}-${prediction.type}`}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 * index }}
                className={`p-4 rounded-lg border ${colors.bg}`}
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <Icon className={`w-4 h-4 ${colors.text}`} />
                    <div className="font-medium text-white truncate max-w-24">
                      {prediction.item.name}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant={confidenceBadge.variant} size="sm">
                      {confidenceBadge.text}
                    </Badge>
                    <div className={`text-xs ${getImpactColor(prediction.impact)}`}>
                      {prediction.impact} impact
                    </div>
                  </div>
                </div>

                <div className="space-y-2">
                  <div className={`font-medium ${colors.text}`}>
                    {prediction.prediction}
                  </div>
                  <div className="text-sm text-gray-300">
                    {prediction.reasoning}
                  </div>
                  <div className="flex items-center justify-between text-xs text-gray-400">
                    <span>Timeframe: {prediction.timeframe}</span>
                    <span>Confidence: {prediction.confidence.toFixed(0)}%</span>
                  </div>
                </div>
              </motion.div>
            );
          })}

          {predictions.length === 0 && (
            <div className="col-span-2 text-center py-8 text-gray-400">
              <Brain className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <div className="font-medium mb-2">No predictions available</div>
              <div className="text-sm">
                Add more items to your analysis to generate AI insights
              </div>
            </div>
          )}
        </div>
      </Card>

      {/* Quick Insights Summary */}
      {predictions.length > 0 && (
        <Card className="p-6 space-y-4">
          <div className="flex items-center gap-2">
            <Target className="w-5 h-5 text-purple-400" />
            <h3 className="text-lg font-semibold text-white">Key Insights Summary</h3>
          </div>

          <div className="bg-white/5 rounded-lg p-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
              <div className="space-y-2">
                <div className="font-medium text-purple-400">High-Confidence Predictions</div>
                <div className="text-gray-300">
                  {predictions.filter(p => p.confidence >= 80).length} predictions above 80% confidence
                </div>
              </div>
              <div className="space-y-2">
                <div className="font-medium text-purple-400">Opportunity Alerts</div>
                <div className="text-gray-300">
                  {predictions.filter(p => p.type === 'opportunity').length} potential opportunities identified
                </div>
              </div>
              <div className="space-y-2">
                <div className="font-medium text-purple-400">Risk Warnings</div>
                <div className="text-gray-300">
                  {predictions.filter(p => p.type === 'risk_warning').length} items require attention
                </div>
              </div>
            </div>
          </div>

          <div className="text-xs text-gray-400 bg-blue-500/10 border border-blue-500/20 rounded-lg p-3">
            <div className="font-medium text-blue-400 mb-1">AI Analysis Disclaimer</div>
            <div>
              Predictions are based on historical data patterns and market analysis. 
              Always consider multiple factors and your own research before making trading decisions. 
              Past performance does not guarantee future results.
            </div>
          </div>
        </Card>
      )}
    </div>
  );
};