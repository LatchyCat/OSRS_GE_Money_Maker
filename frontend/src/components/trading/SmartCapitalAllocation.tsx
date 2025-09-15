import React, { useState, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  WalletIcon,
  ChartPieIcon,
  SparklesIcon,
  BoltIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  ArrowRightIcon,
  CpuChipIcon,
  AdjustmentsHorizontalIcon
} from '@heroicons/react/24/outline';
import type { FlippingOpportunity } from '../../types/tradingStrategies';

interface AllocationRecommendation {
  opportunity: FlippingOpportunity & { 
    aiConfidence: number;
    riskScore: number;
    competitionLevel: 'low' | 'medium' | 'high';
    volumeQuality: 'excellent' | 'good' | 'fair' | 'poor';
  };
  recommendedAmount: number;
  expectedProfit: number;
  riskLevel: 'low' | 'medium' | 'high';
  percentage: number;
  reasoning: string;
}

interface PortfolioStats {
  totalAllocated: number;
  expectedReturn: number;
  riskScore: number;
  diversificationScore: number;
  timeToComplete: number;
}

interface SmartCapitalAllocationProps {
  opportunities: (FlippingOpportunity & { 
    aiConfidence: number;
    riskScore: number;
    competitionLevel: 'low' | 'medium' | 'high';
    volumeQuality: 'excellent' | 'good' | 'fair' | 'poor';
  })[];
  totalCapital: number;
  onCapitalChange: (capital: number) => void;
  className?: string;
}

export const SmartCapitalAllocation: React.FC<SmartCapitalAllocationProps> = ({
  opportunities,
  totalCapital,
  onCapitalChange,
  className = ''
}) => {
  const [riskTolerance, setRiskTolerance] = useState<'conservative' | 'moderate' | 'aggressive'>('moderate');
  const [maxPositions, setMaxPositions] = useState(5);
  const [minInvestmentPerPosition, setMinInvestmentPerPosition] = useState(50000); // 50K GP minimum
  const [showDetails, setShowDetails] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  // AI-powered portfolio optimization
  const portfolioRecommendations = useMemo(() => {
    if (opportunities.length === 0 || totalCapital === 0) return [];

    // Filter and score opportunities
    const scoredOpportunities = opportunities
      .filter(opp => {
        // Basic filters
        const requiredCapital = opp.buy_price * opp.recommended_quantity;
        return requiredCapital >= minInvestmentPerPosition && 
               requiredCapital <= totalCapital * 0.4; // Max 40% in single position
      })
      .map(opp => {
        const requiredCapital = opp.buy_price * opp.recommended_quantity;
        const expectedProfit = opp.total_profit_potential;
        const profitRatio = expectedProfit / requiredCapital;
        
        // Calculate composite score based on multiple factors
        const confidenceWeight = 0.3;
        const profitWeight = 0.25;
        const riskWeight = 0.2;
        const volumeWeight = 0.15;
        const competitionWeight = 0.1;

        const confidenceScore = opp.aiConfidence / 100;
        const profitScore = Math.min(profitRatio * 10, 1); // Normalize to 0-1
        const riskScore = opp.riskScore / 10;
        const volumeScore = { 'excellent': 1, 'good': 0.8, 'fair': 0.6, 'poor': 0.3 }[opp.volumeQuality];
        const competitionScore = { 'low': 1, 'medium': 0.7, 'high': 0.4 }[opp.competitionLevel];

        const compositeScore = (
          confidenceScore * confidenceWeight +
          profitScore * profitWeight +
          riskScore * riskWeight +
          volumeScore * volumeWeight +
          competitionScore * competitionWeight
        );

        // Adjust for risk tolerance
        const riskAdjustment = riskTolerance === 'conservative' 
          ? riskScore * 1.5 
          : riskTolerance === 'aggressive' 
          ? profitScore * 1.2 
          : 1;

        return {
          ...opp,
          compositeScore: compositeScore * riskAdjustment,
          requiredCapital,
          expectedProfit,
          profitRatio
        };
      })
      .sort((a, b) => b.compositeScore - a.compositeScore)
      .slice(0, maxPositions);

    // Optimize allocation using modified Kelly criterion with risk adjustments
    const recommendations: AllocationRecommendation[] = [];
    let remainingCapital = totalCapital;
    const totalScore = scoredOpportunities.reduce((sum, opp) => sum + opp.compositeScore, 0);

    scoredOpportunities.forEach(opp => {
      if (remainingCapital < minInvestmentPerPosition) return;

      // Calculate initial allocation based on composite score
      const baseAllocation = (opp.compositeScore / totalScore) * totalCapital;
      
      // Apply Kelly criterion adjustments
      const winProbability = opp.aiConfidence / 100;
      const averageWin = opp.profitRatio;
      const averageLoss = 0.05; // Assume 5% loss on failed flips
      
      const kellyPercentage = (winProbability * averageWin - (1 - winProbability) * averageLoss) / averageWin;
      const kellyAdjustedAllocation = Math.max(0, Math.min(kellyPercentage * totalCapital, totalCapital * 0.25));

      // Combine base allocation with Kelly criterion (weighted average)
      const combinedAllocation = (baseAllocation * 0.7) + (kellyAdjustedAllocation * 0.3);
      
      // Ensure allocation constraints
      const finalAllocation = Math.min(
        Math.max(combinedAllocation, minInvestmentPerPosition),
        remainingCapital,
        opp.requiredCapital,
        totalCapital * 0.3 // Max 30% in single position for diversification
      );

      if (finalAllocation >= minInvestmentPerPosition) {
        const quantity = Math.floor(finalAllocation / opp.buy_price);
        const actualAllocation = quantity * opp.buy_price;
        const expectedProfit = quantity * (opp.sell_price - opp.buy_price);
        
        const getRiskLevel = (riskScore: number): 'low' | 'medium' | 'high' => {
          if (riskScore >= 7) return 'low';
          if (riskScore >= 4) return 'medium';
          return 'high';
        };

        const generateReasoning = (opp: any, allocation: number): string => {
          const factors = [];
          if (opp.aiConfidence >= 80) factors.push('high AI confidence');
          if (opp.competitionLevel === 'low') factors.push('low competition');
          if (opp.volumeQuality === 'excellent') factors.push('excellent volume');
          if (opp.profitRatio > 0.1) factors.push('strong profit margins');
          if (opp.estimated_flip_time_minutes <= 30) factors.push('fast flip time');
          
          return `Recommended due to ${factors.slice(0, 3).join(', ')}${factors.length > 3 ? ' and other factors' : ''}.`;
        };

        recommendations.push({
          opportunity: opp,
          recommendedAmount: actualAllocation,
          expectedProfit,
          riskLevel: getRiskLevel(opp.riskScore),
          percentage: (actualAllocation / totalCapital) * 100,
          reasoning: generateReasoning(opp, actualAllocation)
        });

        remainingCapital -= actualAllocation;
      }
    });

    return recommendations;
  }, [opportunities, totalCapital, riskTolerance, maxPositions, minInvestmentPerPosition, refreshKey]);

  // Calculate portfolio statistics
  const portfolioStats: PortfolioStats = useMemo(() => {
    const totalAllocated = portfolioRecommendations.reduce((sum, rec) => sum + rec.recommendedAmount, 0);
    const expectedReturn = portfolioRecommendations.reduce((sum, rec) => sum + rec.expectedProfit, 0);
    const weightedRiskScore = portfolioRecommendations.reduce((sum, rec) => 
      sum + (rec.opportunity.riskScore * rec.percentage / 100), 0
    );
    
    // Diversification score based on number of positions and balance
    const numPositions = portfolioRecommendations.length;
    const maxPercentage = Math.max(...portfolioRecommendations.map(r => r.percentage));
    const diversificationScore = numPositions > 1 
      ? Math.min(10, (numPositions * 2) - (maxPercentage / 10))
      : 1;
    
    // Estimate time to complete (weighted average)
    const timeToComplete = portfolioRecommendations.length > 0
      ? portfolioRecommendations.reduce((sum, rec) => 
          sum + (rec.opportunity.estimated_flip_time_minutes * rec.percentage / 100), 0
        )
      : 0;

    return {
      totalAllocated,
      expectedReturn,
      riskScore: weightedRiskScore,
      diversificationScore,
      timeToComplete
    };
  }, [portfolioRecommendations]);

  const formatGP = (amount: number): string => {
    if (amount >= 1000000) return `${(amount / 1000000).toFixed(1)}M`;
    if (amount >= 1000) return `${(amount / 1000).toFixed(1)}K`;
    return Math.round(amount).toLocaleString();
  };

  const getRiskColor = (level: 'low' | 'medium' | 'high'): string => {
    switch (level) {
      case 'low': return 'text-green-400 bg-green-400/10 border-green-400/30';
      case 'medium': return 'text-yellow-400 bg-yellow-400/10 border-yellow-400/30';
      case 'high': return 'text-red-400 bg-red-400/10 border-red-400/30';
    }
  };

  const getScoreColor = (score: number, max: number = 10): string => {
    const percentage = (score / max) * 100;
    if (percentage >= 80) return 'text-green-400';
    if (percentage >= 60) return 'text-yellow-400';
    return 'text-red-400';
  };

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      className={`bg-gradient-to-br from-indigo-900/20 to-purple-900/30 backdrop-blur-sm border border-indigo-500/30 rounded-xl overflow-hidden ${className}`}
    >
      {/* Header */}
      <div className="p-4 border-b border-indigo-500/30">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-indigo-500/20 rounded-lg">
              <CpuChipIcon className="w-6 h-6 text-indigo-400" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-indigo-400">🧠 Smart Capital Allocation</h3>
              <p className="text-sm text-gray-400">AI-optimized portfolio distribution</p>
            </div>
          </div>
          <button
            onClick={() => setShowDetails(!showDetails)}
            className="px-3 py-1 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm transition-colors"
          >
            <AdjustmentsHorizontalIcon className="w-4 h-4 inline mr-1" />
            Settings
          </button>
        </div>

        {/* Capital Input */}
        <div className="flex items-center gap-4">
          <div className="flex-1">
            <label className="text-sm text-gray-400 mb-1 block">Available Capital</label>
            <div className="relative">
              <WalletIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="number"
                value={totalCapital}
                onChange={(e) => onCapitalChange(parseInt(e.target.value) || 0)}
                className="w-full pl-10 pr-4 py-2 bg-gray-700/50 border border-gray-600/50 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-indigo-500/50"
                placeholder="1000000"
              />
              <span className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 text-sm">GP</span>
            </div>
          </div>
          
          <div>
            <label className="text-sm text-gray-400 mb-1 block">Risk Tolerance</label>
            <select
              value={riskTolerance}
              onChange={(e) => setRiskTolerance(e.target.value as any)}
              className="px-3 py-2 bg-gray-700/50 border border-gray-600/50 rounded-lg text-white text-sm focus:outline-none focus:ring-1 focus:ring-indigo-500/50"
            >
              <option value="conservative">🟢 Conservative</option>
              <option value="moderate">🟡 Moderate</option>
              <option value="aggressive">🔴 Aggressive</option>
            </select>
          </div>
        </div>
      </div>

      {/* Settings Panel */}
      <AnimatePresence>
        {showDetails && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="border-b border-indigo-500/30 p-4 bg-indigo-900/10"
          >
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm text-gray-400 mb-1 block">Max Positions</label>
                <input
                  type="number"
                  min="1"
                  max="10"
                  value={maxPositions}
                  onChange={(e) => setMaxPositions(parseInt(e.target.value) || 5)}
                  className="w-full px-3 py-2 bg-gray-700/50 border border-gray-600/50 rounded-lg text-white text-sm focus:outline-none focus:ring-1 focus:ring-indigo-500/50"
                />
              </div>
              <div>
                <label className="text-sm text-gray-400 mb-1 block">Min Position Size</label>
                <input
                  type="number"
                  value={minInvestmentPerPosition}
                  onChange={(e) => setMinInvestmentPerPosition(parseInt(e.target.value) || 50000)}
                  className="w-full px-3 py-2 bg-gray-700/50 border border-gray-600/50 rounded-lg text-white text-sm focus:outline-none focus:ring-1 focus:ring-indigo-500/50"
                />
              </div>
            </div>
            
            <div className="flex justify-end mt-3">
              <button
                onClick={() => setRefreshKey(prev => prev + 1)}
                className="px-3 py-1 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm transition-colors"
              >
                <SparklesIcon className="w-4 h-4 inline mr-1" />
                Recalculate
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Portfolio Overview */}
      <div className="p-4">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
          <div className="bg-gray-800/40 rounded-lg p-3 text-center">
            <div className="text-lg font-bold text-indigo-400">{formatGP(portfolioStats.totalAllocated)}</div>
            <div className="text-xs text-gray-400">Allocated</div>
            <div className="text-xs text-indigo-300">
              {((portfolioStats.totalAllocated / totalCapital) * 100).toFixed(1)}%
            </div>
          </div>
          
          <div className="bg-gray-800/40 rounded-lg p-3 text-center">
            <div className="text-lg font-bold text-green-400">+{formatGP(portfolioStats.expectedReturn)}</div>
            <div className="text-xs text-gray-400">Expected</div>
            <div className="text-xs text-green-300">
              {((portfolioStats.expectedReturn / portfolioStats.totalAllocated) * 100).toFixed(1)}% ROI
            </div>
          </div>
          
          <div className="bg-gray-800/40 rounded-lg p-3 text-center">
            <div className={`text-lg font-bold ${getScoreColor(portfolioStats.riskScore)}`}>
              {portfolioStats.riskScore.toFixed(1)}/10
            </div>
            <div className="text-xs text-gray-400">Risk Score</div>
            <div className="text-xs text-gray-300">Portfolio Risk</div>
          </div>
          
          <div className="bg-gray-800/40 rounded-lg p-3 text-center">
            <div className="text-lg font-bold text-purple-400">{Math.round(portfolioStats.timeToComplete)}m</div>
            <div className="text-xs text-gray-400">Avg Time</div>
            <div className="text-xs text-purple-300">To Complete</div>
          </div>
        </div>

        {/* Diversification Score */}
        <div className="mb-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-400">Portfolio Diversification</span>
            <span className={`text-sm font-medium ${getScoreColor(portfolioStats.diversificationScore)}`}>
              {portfolioStats.diversificationScore.toFixed(1)}/10
            </span>
          </div>
          <div className="w-full bg-gray-700 rounded-full h-2">
            <div 
              className={`h-2 rounded-full transition-all ${
                portfolioStats.diversificationScore >= 8 ? 'bg-green-400' :
                portfolioStats.diversificationScore >= 6 ? 'bg-yellow-400' :
                'bg-red-400'
              }`}
              style={{ width: `${(portfolioStats.diversificationScore / 10) * 100}%` }}
            />
          </div>
        </div>

        {/* Recommendations */}
        <div className="space-y-3">
          <div className="flex items-center gap-2 mb-3">
            <ChartPieIcon className="w-4 h-4 text-indigo-400" />
            <span className="text-sm font-medium text-indigo-400">
              Recommended Allocations ({portfolioRecommendations.length})
            </span>
          </div>
          
          {portfolioRecommendations.length === 0 ? (
            <div className="text-center py-6 text-gray-400">
              <ExclamationTriangleIcon className="w-8 h-8 mx-auto mb-2" />
              <p className="text-sm">No suitable opportunities for current capital and settings</p>
              <p className="text-xs mt-1">Try adjusting your capital amount or risk tolerance</p>
            </div>
          ) : (
            portfolioRecommendations.map((rec, index) => (
              <motion.div
                key={rec.opportunity.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                className="bg-gray-800/30 rounded-lg p-3 border-l-4 border-indigo-400/50"
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-1 min-w-0">
                    <h4 className="font-medium text-gray-200 truncate">
                      {rec.opportunity.item_name}
                    </h4>
                    <p className="text-xs text-gray-400 mt-1">{rec.reasoning}</p>
                  </div>
                  <div className={`px-2 py-1 rounded-full text-xs font-medium border ${getRiskColor(rec.riskLevel)}`}>
                    {rec.riskLevel.toUpperCase()}
                  </div>
                </div>
                
                <div className="grid grid-cols-3 gap-3 text-sm">
                  <div>
                    <div className="text-gray-400 text-xs">Allocation</div>
                    <div className="text-white font-medium">
                      {formatGP(rec.recommendedAmount)}
                      <span className="text-indigo-400 text-xs ml-1">
                        ({rec.percentage.toFixed(1)}%)
                      </span>
                    </div>
                  </div>
                  
                  <div>
                    <div className="text-gray-400 text-xs">Expected Profit</div>
                    <div className="text-green-400 font-medium">
                      +{formatGP(rec.expectedProfit)}
                    </div>
                  </div>
                  
                  <div>
                    <div className="text-gray-400 text-xs">AI Score</div>
                    <div className={`font-medium ${
                      rec.opportunity.aiConfidence >= 80 ? 'text-green-400' :
                      rec.opportunity.aiConfidence >= 60 ? 'text-yellow-400' :
                      'text-red-400'
                    }`}>
                      {rec.opportunity.aiConfidence}%
                    </div>
                  </div>
                </div>
              </motion.div>
            ))
          )}
        </div>

        {/* Action Buttons */}
        {portfolioRecommendations.length > 0 && (
          <div className="flex gap-3 mt-4 pt-4 border-t border-indigo-500/30">
            <button className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg transition-colors">
              <CheckCircleIcon className="w-4 h-4" />
              Apply Allocation
            </button>
            <button className="px-4 py-2 border border-indigo-500/50 text-indigo-400 hover:bg-indigo-600/20 rounded-lg transition-colors">
              Export Strategy
            </button>
          </div>
        )}
        
        {/* Cash Remaining */}
        {totalCapital > portfolioStats.totalAllocated && (
          <div className="mt-3 p-3 bg-yellow-900/20 border border-yellow-500/30 rounded-lg">
            <div className="flex items-center gap-2">
              <BoltIcon className="w-4 h-4 text-yellow-400" />
              <span className="text-sm text-yellow-400 font-medium">
                {formatGP(totalCapital - portfolioStats.totalAllocated)} GP remaining
              </span>
            </div>
            <p className="text-xs text-yellow-300 mt-1">
              Consider increasing position sizes or finding more opportunities
            </p>
          </div>
        )}
      </div>
    </motion.div>
  );
};

export default SmartCapitalAllocation;