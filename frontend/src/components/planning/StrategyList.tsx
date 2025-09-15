import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { 
  TrendingUp, 
  Shield, 
  Clock, 
  DollarSign,
  BarChart3,
  Star,
  ArrowRight,
  Package,
  AlertCircle,
  CheckCircle,
  Filter
} from 'lucide-react';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import type { Strategy } from '../../types';

interface StrategyListProps {
  strategies: Strategy[];
  onStrategySelect?: (strategy: Strategy) => void;
  onCompareStrategies?: () => void;
}

export const StrategyList: React.FC<StrategyListProps> = ({ 
  strategies, 
  onStrategySelect,
  onCompareStrategies 
}) => {
  const [sortBy, setSortBy] = useState<'roi' | 'risk' | 'timeline' | 'feasibility'>('roi');
  const [filterRisk, setFilterRisk] = useState<'all' | 'conservative' | 'moderate' | 'aggressive'>('all');

  const formatGP = (amount: number) => {
    if (amount >= 1000000000) {
      return `${(amount / 1000000000).toFixed(1)}B GP`;
    } else if (amount >= 1000000) {
      return `${(amount / 1000000).toFixed(1)}M GP`;
    } else if (amount >= 1000) {
      return `${(amount / 1000).toFixed(1)}K GP`;
    }
    return `${amount.toLocaleString()} GP`;
  };

  const getRiskColor = (risk: string) => {
    switch (risk) {
      case 'conservative': return 'text-green-400 border-green-500/50 bg-green-500/10';
      case 'moderate': return 'text-yellow-400 border-yellow-500/50 bg-yellow-500/10';
      case 'aggressive': return 'text-red-400 border-red-500/50 bg-red-500/10';
      default: return 'text-gray-400 border-gray-500/50 bg-gray-500/10';
    }
  };

  const getFeasibilityColor = (score: number) => {
    if (score >= 0.8) return 'text-green-400';
    if (score >= 0.6) return 'text-yellow-400';
    if (score >= 0.4) return 'text-orange-400';
    return 'text-red-400';
  };

  const sortedAndFilteredStrategies = strategies
    .filter(strategy => filterRisk === 'all' || strategy.risk_level === filterRisk)
    .sort((a, b) => {
      switch (sortBy) {
        case 'roi': return b.roi_percentage - a.roi_percentage;
        case 'risk': 
          const riskOrder = { conservative: 1, moderate: 2, aggressive: 3 };
          return riskOrder[a.risk_level as keyof typeof riskOrder] - riskOrder[b.risk_level as keyof typeof riskOrder];
        case 'timeline': return a.estimated_days - b.estimated_days;
        case 'feasibility': return b.feasibility_score - a.feasibility_score;
        default: return 0;
      }
    });

  const recommendedStrategy = strategies.find(s => s.is_recommended);

  if (strategies.length === 0) {
    return (
      <Card className="p-8 text-center">
        <div className="space-y-4">
          <div className="w-16 h-16 bg-yellow-500/20 rounded-full flex items-center justify-center mx-auto">
            <BarChart3 className="w-8 h-8 text-yellow-400" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white">No Strategies Available</h3>
            <p className="text-gray-400 mt-2">
              Strategies will be generated when you create a goal plan
            </p>
          </div>
        </div>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold text-white flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-accent-400" />
            Investment Strategies
          </h2>
          <p className="text-gray-400 text-sm mt-1">
            {strategies.length} strategies available • {recommendedStrategy ? 'Recommended strategy highlighted' : 'No recommendation'}
          </p>
        </div>
        
        {strategies.length > 1 && (
          <Button
            variant="secondary"
            onClick={onCompareStrategies}
            icon={<ArrowRight className="w-4 h-4" />}
          >
            Compare All
          </Button>
        )}
      </div>

      {/* Controls */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
        {/* Sort By */}
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-400">Sort by:</span>
          <div className="flex items-center gap-1">
            {(['roi', 'risk', 'timeline', 'feasibility'] as const).map((option) => (
              <button
                key={option}
                onClick={() => setSortBy(option)}
                className={`px-3 py-1 rounded-lg text-sm font-medium transition-all ${
                  sortBy === option 
                    ? 'bg-accent-500 text-white' 
                    : 'bg-white/10 text-gray-300 hover:bg-white/20'
                }`}
              >
                {option === 'roi' ? 'ROI' : option.charAt(0).toUpperCase() + option.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {/* Filter by Risk */}
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-gray-400" />
          <span className="text-sm text-gray-400">Risk:</span>
          <div className="flex items-center gap-1">
            {(['all', 'conservative', 'moderate', 'aggressive'] as const).map((risk) => (
              <button
                key={risk}
                onClick={() => setFilterRisk(risk)}
                className={`px-3 py-1 rounded-lg text-sm font-medium transition-all ${
                  filterRisk === risk 
                    ? 'bg-accent-500 text-white' 
                    : 'bg-white/10 text-gray-300 hover:bg-white/20'
                }`}
              >
                {risk.charAt(0).toUpperCase() + risk.slice(1)}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Strategies Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {sortedAndFilteredStrategies.map((strategy, index) => (
          <motion.div
            key={strategy.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 * index }}
          >
            <Card 
              className={`p-6 space-y-4 hover:border-accent-500/50 transition-all cursor-pointer ${
                strategy.is_recommended ? 'ring-2 ring-accent-500/50 bg-accent-500/5' : ''
              }`}
              onClick={() => onStrategySelect?.(strategy)}
            >
              {/* Header */}
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-3">
                  <div className="p-2 bg-accent-500/20 rounded-lg">
                    <TrendingUp className="w-5 h-5 text-accent-400" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="text-lg font-semibold text-white">
                        {strategy.name}
                      </h3>
                      {strategy.is_recommended && (
                        <Star className="w-4 h-4 text-yellow-400 fill-current" />
                      )}
                    </div>
                    <p className="text-sm text-gray-400 mt-1">
                      {strategy.strategy_type}
                    </p>
                  </div>
                </div>
                
                <Badge variant={strategy.is_active ? 'success' : 'secondary'}>
                  {strategy.is_active ? 'Active' : 'Available'}
                </Badge>
              </div>

              {/* Key Metrics */}
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-3">
                  <div className="flex items-center gap-2 mb-1">
                    <TrendingUp className="w-4 h-4 text-green-400" />
                    <span className="text-xs text-gray-400 uppercase tracking-wider">ROI</span>
                  </div>
                  <div className="text-lg font-bold text-green-400">
                    {strategy.roi_percentage.toFixed(1)}%
                  </div>
                </div>

                <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-3">
                  <div className="flex items-center gap-2 mb-1">
                    <DollarSign className="w-4 h-4 text-blue-400" />
                    <span className="text-xs text-gray-400 uppercase tracking-wider">Profit</span>
                  </div>
                  <div className="text-lg font-bold text-blue-400">
                    {formatGP(strategy.estimated_profit)}
                  </div>
                </div>
              </div>

              {/* Details Grid */}
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div className="flex items-center justify-between">
                  <span className="text-gray-400 flex items-center gap-1">
                    <Shield className="w-3 h-3" />
                    Risk Level
                  </span>
                  <span className={`font-medium ${getRiskColor(strategy.risk_level).split(' ')[0]}`}>
                    {strategy.risk_level}
                  </span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-gray-400 flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    Timeline
                  </span>
                  <span className="text-white font-medium">
                    {strategy.estimated_days}d
                  </span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-gray-400 flex items-center gap-1">
                    <DollarSign className="w-3 h-3" />
                    Investment
                  </span>
                  <span className="text-purple-400 font-medium">
                    {formatGP(strategy.required_initial_investment)}
                  </span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-gray-400 flex items-center gap-1">
                    <BarChart3 className="w-3 h-3" />
                    Feasibility
                  </span>
                  <div className="flex items-center gap-1">
                    <span className={`font-medium ${getFeasibilityColor(strategy.feasibility_score)}`}>
                      {(strategy.feasibility_score * 100).toFixed(0)}%
                    </span>
                    {strategy.feasibility_score >= 0.7 ? (
                      <CheckCircle className="w-3 h-3 text-green-400" />
                    ) : strategy.feasibility_score >= 0.4 ? (
                      <AlertCircle className="w-3 h-3 text-yellow-400" />
                    ) : (
                      <AlertCircle className="w-3 h-3 text-red-400" />
                    )}
                  </div>
                </div>
              </div>

              {/* Items Preview */}
              {strategy.items && strategy.items.length > 0 && (
                <div className="bg-white/5 rounded-lg p-3">
                  <div className="flex items-center gap-2 mb-2">
                    <Package className="w-4 h-4 text-accent-400" />
                    <span className="text-sm font-semibold text-white">
                      Items ({strategy.items.length})
                    </span>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    {strategy.items.slice(0, 4).map((item, i) => (
                      <div key={i} className="flex items-center justify-between">
                        <span className="text-gray-400 truncate">
                          {item.item?.name || `Item ${item.item_id}`}
                        </span>
                        <span className="text-accent-400 font-medium">
                          {item.units_to_buy}x
                        </span>
                      </div>
                    ))}
                    {strategy.items.length > 4 && (
                      <div className="col-span-2 text-center text-gray-400">
                        +{strategy.items.length - 4} more items
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Description */}
              {strategy.description && (
                <p className="text-sm text-gray-400 bg-white/5 rounded-lg p-3">
                  {strategy.description}
                </p>
              )}
            </Card>
          </motion.div>
        ))}
      </div>

      {sortedAndFilteredStrategies.length === 0 && filterRisk !== 'all' && (
        <Card className="p-8 text-center">
          <div className="space-y-4">
            <AlertCircle className="w-12 h-12 text-yellow-400 mx-auto" />
            <div>
              <h3 className="text-lg font-semibold text-white">No Strategies Found</h3>
              <p className="text-gray-400 mt-2">
                No strategies match the selected risk level. Try adjusting your filters.
              </p>
            </div>
            <Button 
              variant="secondary"
              onClick={() => setFilterRisk('all')}
            >
              Show All Strategies
            </Button>
          </div>
        </Card>
      )}
    </div>
  );
};