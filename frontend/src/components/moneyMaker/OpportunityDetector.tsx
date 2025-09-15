import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Search, 
  RefreshCw, 
  TrendingUp, 
  AlertTriangle, 
  CheckCircle,
  Clock,
  DollarSign,
  Target,
  Zap
} from 'lucide-react';
import { moneyMakerApi } from '../../api/moneyMaker';
import * as MoneyMakerTypes from '../../types/moneyMaker';
import { LoadingSpinner } from '../common/LoadingSpinner';

interface OpportunityDetectorProps {
  capital: number;
  autoRefresh?: boolean;
  refreshInterval?: number; // in seconds
}

export const OpportunityDetector: React.FC<OpportunityDetectorProps> = ({
  capital,
  autoRefresh = true,
  refreshInterval = 60 // 1 minute
}) => {
  const [opportunities, setOpportunities] = useState<Record<MoneyMakerTypes.StrategyType, MoneyMakerTypes.MoneyMakerOpportunity[]>>({} as Record<MoneyMakerTypes.StrategyType, MoneyMakerTypes.MoneyMakerOpportunity[]>);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [detecting, setDetecting] = useState(false);
  const [selectedType, setSelectedType] = useState<MoneyMakerTypes.StrategyType | 'all'>('all');

  useEffect(() => {
    detectOpportunities();
    
    if (autoRefresh) {
      const interval = setInterval(detectOpportunities, refreshInterval * 1000);
      return () => clearInterval(interval);
    }
  }, [capital, autoRefresh, refreshInterval]);

  const detectOpportunities = async () => {
    try {
      setDetecting(true);
      setError(null);
      
      const response = await moneyMakerApi.detectAllOpportunities(capital);
      setOpportunities(response.opportunities_by_type);
      setLastUpdated(new Date(response.detection_timestamp));
      
      if (loading) setLoading(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to detect opportunities');
      if (loading) setLoading(false);
    } finally {
      setDetecting(false);
    }
  };

  const getAllOpportunities = (): MoneyMakerTypes.MoneyMakerOpportunity[] => {
    return Object.values(opportunities).flat();
  };

  const getFilteredOpportunities = (): MoneyMakerTypes.MoneyMakerOpportunity[] => {
    if (selectedType === 'all') {
      return getAllOpportunities();
    }
    return opportunities[selectedType] || [];
  };

  const getTopOpportunities = (limit: number = 5): MoneyMakerTypes.MoneyMakerOpportunity[] => {
    return getFilteredOpportunities()
      .sort((a, b) => b.profit_per_item - a.profit_per_item)
      .slice(0, limit);
  };

  const getTotalPotentialProfit = (): number => {
    return getFilteredOpportunities().reduce((sum, opp) => 
      sum + (opp.profit_per_item * Math.min(opp.max_trades_with_capital, 10)), 0
    );
  };

  const strategyTypes = Object.keys(opportunities) as MoneyMakerTypes.StrategyType[];

  if (loading) {
    return (
      <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
        <div className="flex items-center justify-center h-32">
          <LoadingSpinner size="md" />
          <span className="ml-3 text-gray-300">Detecting opportunities...</span>
        </div>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-gray-800 rounded-lg p-6 border border-gray-700"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-green-600 rounded-lg">
            <Search className="h-5 w-5 text-white" />
          </div>
          <div>
            <h3 className="text-xl font-semibold text-white">Real-Time Opportunities</h3>
            <p className="text-sm text-gray-400">
              Scanning {MoneyMakerTypes.formatGP(capital)} capital range
            </p>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          {/* Last Updated */}
          {lastUpdated && (
            <div className="text-right">
              <p className="text-xs text-gray-400">Last updated</p>
              <p className="text-sm text-green-400">
                {lastUpdated.toLocaleTimeString()}
              </p>
            </div>
          )}
          
          {/* Refresh Button */}
          <button
            onClick={detectOpportunities}
            disabled={detecting}
            className="flex items-center gap-2 px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${detecting ? 'animate-spin' : ''}`} />
            <span className="text-sm">Refresh</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-900/20 border border-red-700 rounded-lg">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-red-400" />
            <span className="text-red-300">Detection Error</span>
          </div>
          <p className="text-red-400 text-sm mt-1">{error}</p>
        </div>
      )}

      {/* Strategy Type Filter */}
      <div className="mb-6">
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setSelectedType('all')}
            className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
              selectedType === 'all'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            All Types ({getAllOpportunities().length})
          </button>
          
          {strategyTypes.map(type => (
            <button
              key={type}
              onClick={() => setSelectedType(type)}
              className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                selectedType === type
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              <span className={MoneyMakerTypes.getStrategyTypeColor(type)}>
                {MoneyMakerTypes.STRATEGY_TYPE_DISPLAY[type]}
              </span>
              <span className="ml-1 text-gray-400">
                ({opportunities[type]?.length || 0})
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-gray-900 rounded-lg p-4 border border-gray-700">
          <div className="flex items-center gap-2 mb-2">
            <Target className="h-4 w-4 text-green-400" />
            <span className="text-sm text-gray-400">Opportunities Found</span>
          </div>
          <p className="text-2xl font-bold text-white">
            {getFilteredOpportunities().length}
          </p>
        </div>
        
        <div className="bg-gray-900 rounded-lg p-4 border border-gray-700">
          <div className="flex items-center gap-2 mb-2">
            <DollarSign className="h-4 w-4 text-yellow-400" />
            <span className="text-sm text-gray-400">Total Potential</span>
          </div>
          <p className="text-2xl font-bold text-yellow-400">
            {MoneyMakerTypes.formatGP(getTotalPotentialProfit())}
          </p>
        </div>
        
        <div className="bg-gray-900 rounded-lg p-4 border border-gray-700">
          <div className="flex items-center gap-2 mb-2">
            <Zap className="h-4 w-4 text-purple-400" />
            <span className="text-sm text-gray-400">Strategy Types</span>
          </div>
          <p className="text-2xl font-bold text-white">
            {strategyTypes.length}
          </p>
        </div>
      </div>

      {/* Top Opportunities */}
      <div>
        <h4 className="text-lg font-semibold text-white mb-4">
          Top Opportunities
          {selectedType !== 'all' && (
            <span className={`ml-2 text-sm ${MoneyMakerTypes.getStrategyTypeColor(selectedType)}`}>
              ({MoneyMakerTypes.STRATEGY_TYPE_DISPLAY[selectedType]})
            </span>
          )}
        </h4>
        
        <AnimatePresence mode="wait">
          {getTopOpportunities().length === 0 ? (
            <motion.div
              key="no-opportunities"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="text-center py-8 text-gray-400"
            >
              <Search className="h-8 w-8 mx-auto mb-2 opacity-50" />
              <p>No opportunities found for current filters</p>
              <p className="text-sm mt-1">Try adjusting your capital or strategy type</p>
            </motion.div>
          ) : (
            <motion.div
              key="opportunities-list"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="space-y-3"
            >
              {getTopOpportunities().map((opportunity, index) => (
                <OpportunityCard
                  key={`${opportunity.strategy_type}-${opportunity.item_id}`}
                  opportunity={opportunity}
                  rank={index + 1}
                  capital={capital}
                />
              ))}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Auto Refresh Indicator */}
      {autoRefresh && (
        <div className="mt-4 pt-4 border-t border-gray-700">
          <div className="flex items-center gap-2 text-sm text-gray-400">
            <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
            <span>Auto-refreshing every {refreshInterval} seconds</span>
          </div>
        </div>
      )}
    </motion.div>
  );
};

// Opportunity Card Component
interface OpportunityCardProps {
  opportunity: MoneyMakerTypes.MoneyMakerOpportunity;
  rank: number;
  capital: number;
}

const OpportunityCard: React.FC<OpportunityCardProps> = ({ opportunity, rank, capital }) => {
  const strategyColor = MoneyMakerTypes.getStrategyTypeColor(opportunity.strategy_type);
  const profitPerItem = MoneyMakerTypes.formatGP(opportunity.profit_per_item);
  const maxTrades = Math.min(opportunity.max_trades_with_capital, 50); // Cap display at 50
  const totalPotentialProfit = opportunity.profit_per_item * maxTrades;
  
  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: rank * 0.05 }}
      className="bg-gray-900 rounded-lg p-4 border border-gray-700 hover:border-gray-600 transition-colors"
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          {/* Rank */}
          <div className={`
            w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold
            ${rank === 1 ? 'bg-yellow-500 text-yellow-900' : 
              rank === 2 ? 'bg-gray-400 text-gray-900' :
              rank === 3 ? 'bg-orange-500 text-orange-900' :
              'bg-gray-600 text-white'
            }
          `}>
            {rank}
          </div>
          
          <div className="flex-1 min-w-0">
            <h5 className="text-white font-medium truncate">{opportunity.item_name}</h5>
            <div className="flex items-center gap-2 mt-1">
              <span className={`text-xs font-medium ${strategyColor}`}>
                {MoneyMakerTypes.STRATEGY_TYPE_DISPLAY[opportunity.strategy_type]}
              </span>
              {opportunity.tax_exempt && (
                <span className="px-2 py-1 bg-green-900/30 border border-green-700/50 rounded text-xs text-green-400">
                  Tax Exempt
                </span>
              )}
            </div>
          </div>
        </div>
        
        <div className="text-right flex-shrink-0">
          <p className="text-lg font-bold text-green-400">{profitPerItem}</p>
          <p className="text-xs text-gray-400">per item</p>
        </div>
      </div>
      
      {/* Metrics Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
        <div>
          <p className="text-gray-400">Buy Price</p>
          <p className="text-white font-medium">{MoneyMakerTypes.formatGP(opportunity.buy_price)}</p>
        </div>
        
        <div>
          <p className="text-gray-400">Sell Price</p>
          <p className="text-white font-medium">{MoneyMakerTypes.formatGP(opportunity.sell_price)}</p>
        </div>
        
        <div>
          <p className="text-gray-400">Margin</p>
          <p className="text-green-400 font-medium">{opportunity.profit_margin_pct.toFixed(1)}%</p>
        </div>
        
        <div>
          <p className="text-gray-400">Confidence</p>
          <p className={`font-medium ${
            opportunity.confidence_score >= 0.8 ? 'text-green-400' :
            opportunity.confidence_score >= 0.6 ? 'text-yellow-400' :
            'text-red-400'
          }`}>
            {(opportunity.confidence_score * 100).toFixed(0)}%
          </p>
        </div>
      </div>
      
      {/* Potential Profit */}
      <div className="mt-3 pt-3 border-t border-gray-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-green-400" />
            <span className="text-sm text-gray-400">
              Max {maxTrades} trades with {MoneyMakerTypes.formatGP(capital)}
            </span>
          </div>
          <div className="text-right">
            <p className="text-green-400 font-semibold">
              {MoneyMakerTypes.formatGP(totalPotentialProfit)} potential
            </p>
          </div>
        </div>
        
        {/* GE Tax Impact */}
        {opportunity.ge_tax_cost > 0 && (
          <div className="flex items-center justify-between mt-2 text-xs">
            <span className="text-gray-400">GE Tax Cost:</span>
            <span className="text-red-400">-{MoneyMakerTypes.formatGP(opportunity.ge_tax_cost * maxTrades)}</span>
          </div>
        )}
      </div>
    </motion.div>
  );
};