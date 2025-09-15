import React from 'react';
import { motion } from 'framer-motion';
import { TrendingUp, Target, Clock, Award } from 'lucide-react';
import * as MoneyMakerTypes from '../../types/moneyMaker';

interface CapitalProgressionCardProps {
  tiers: Record<string, MoneyMakerTypes.CapitalTier>;
  currentCapital: number;
}

export const CapitalProgressionCard: React.FC<CapitalProgressionCardProps> = ({
  tiers,
  currentCapital
}) => {
  const currentTierName = MoneyMakerTypes.getCapitalTier(currentCapital);
  const currentTierData = tiers[currentTierName];
  const nextTier = MoneyMakerTypes.CAPITAL_TIERS.find(t => t.min > currentCapital);
  const nextTierData = nextTier ? tiers[nextTier.name] : null;

  const progressToNextTier = nextTier 
    ? ((currentCapital - (MoneyMakerTypes.CAPITAL_TIERS.find(t => t.name === currentTierName)?.min || 0)) / 
       (nextTier.min - (MoneyMakerTypes.CAPITAL_TIERS.find(t => t.name === currentTierName)?.min || 0))) * 100
    : 100;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-gradient-to-r from-gray-800 to-gray-900 rounded-lg p-6 border border-gray-700"
    >
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-xl font-semibold text-white">Capital Progression</h3>
        <div className="flex items-center gap-2 text-sm text-gray-300">
          <Target className="h-4 w-4" />
          <span>Your Friend's 50M → 100M Method</span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Current Tier Status */}
        <div className="space-y-4">
          <div className="text-center p-4 bg-blue-900/20 rounded-lg border border-blue-700/50">
            <Award className="h-8 w-8 text-blue-400 mx-auto mb-2" />
            <h4 className="text-lg font-medium text-blue-300 mb-1">Current Tier</h4>
            <p className="text-2xl font-bold text-white">
              {MoneyMakerTypes.CAPITAL_TIERS.find(t => t.name === currentTierName)?.display || 'Starter'}
            </p>
            <p className="text-blue-400 text-sm mt-1">{MoneyMakerTypes.formatGP(currentCapital)}</p>
          </div>

          {currentTierData && (
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-400">Active Strategies:</span>
                <span className="text-white">{currentTierData.count}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Avg Hourly Profit:</span>
                <span className="text-green-400">{MoneyMakerTypes.formatGP(currentTierData.avg_hourly_profit)}</span>
              </div>
            </div>
          )}
        </div>

        {/* Progress to Next Tier */}
        {nextTier && (
          <div className="space-y-4">
            <div className="text-center">
              <h4 className="text-lg font-medium text-white mb-2">Next Tier</h4>
              <p className="text-xl font-semibold text-purple-400">{nextTier.display}</p>
              <p className="text-sm text-gray-400 mt-1">
                {MoneyMakerTypes.formatGP(nextTier.min - currentCapital)} needed
              </p>
            </div>

            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-gray-400">Progress</span>
                <span className="text-white">{progressToNextTier.toFixed(1)}%</span>
              </div>
              <div className="w-full bg-gray-700 rounded-full h-2">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${Math.min(progressToNextTier, 100)}%` }}
                  transition={{ duration: 1, ease: "easeOut" }}
                  className="bg-gradient-to-r from-purple-500 to-blue-500 h-2 rounded-full"
                />
              </div>
            </div>

            {nextTierData && (
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-400">Strategies Available:</span>
                  <span className="text-white">{nextTierData.count}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Potential Hourly:</span>
                  <span className="text-green-400">{MoneyMakerTypes.formatGP(nextTierData.avg_hourly_profit)}</span>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tier Benefits */}
        <div className="space-y-4">
          <h4 className="text-lg font-medium text-white">Tier Benefits</h4>
          <div className="space-y-3">
            {MoneyMakerTypes.CAPITAL_TIERS.map((tier, index) => {
              const isUnlocked = currentCapital >= tier.min;
              const isCurrent = tier.name === currentTierName;
              const tierData = tiers[tier.name];

              return (
                <motion.div
                  key={tier.name}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.1 }}
                  className={`flex items-center gap-3 p-2 rounded-lg transition-all ${
                    isCurrent 
                      ? 'bg-blue-900/30 border border-blue-700/50' 
                      : isUnlocked 
                        ? 'bg-green-900/20 border border-green-700/30'
                        : 'bg-gray-800/50 border border-gray-700/50 opacity-60'
                  }`}
                >
                  <div className={`w-2 h-2 rounded-full ${
                    isCurrent 
                      ? 'bg-blue-400' 
                      : isUnlocked 
                        ? 'bg-green-400'
                        : 'bg-gray-500'
                  }`} />
                  <div className="flex-1 min-w-0">
                    <p className={`text-sm font-medium truncate ${
                      isCurrent ? 'text-blue-300' : isUnlocked ? 'text-green-300' : 'text-gray-400'
                    }`}>
                      {tier.display}
                    </p>
                    {tierData && (
                      <p className="text-xs text-gray-500">
                        {tierData.count} strategies, {MoneyMakerTypes.formatGP(tierData.avg_hourly_profit)}/hr
                      </p>
                    )}
                  </div>
                  {isCurrent && (
                    <TrendingUp className="h-4 w-4 text-blue-400 flex-shrink-0" />
                  )}
                </motion.div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="mt-6 pt-6 border-t border-gray-700">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="text-center">
            <p className="text-2xl font-bold text-white">{Object.keys(tiers).length}</p>
            <p className="text-xs text-gray-400">Available Tiers</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-green-400">
              {Object.values(tiers).reduce((sum, tier) => sum + tier.count, 0)}
            </p>
            <p className="text-xs text-gray-400">Total Strategies</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-yellow-400">
              {MoneyMakerTypes.formatGP(
                Object.values(tiers).reduce((sum, tier) => sum + tier.avg_hourly_profit, 0) / Object.keys(tiers).length
              )}
            </p>
            <p className="text-xs text-gray-400">Avg Hourly Profit</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-purple-400">
              {nextTier ? MoneyMakerTypes.formatGP(nextTier.min) : 'Max'}
            </p>
            <p className="text-xs text-gray-400">Next Milestone</p>
          </div>
        </div>
      </div>

      {/* Your Friend's Method Callout */}
      <div className="mt-6 p-4 bg-gradient-to-r from-green-900/20 to-blue-900/20 rounded-lg border border-green-700/30">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-8 h-8 bg-green-600 rounded-full flex items-center justify-center flex-shrink-0">
            <TrendingUp className="h-4 w-4 text-white" />
          </div>
          <div>
            <h5 className="text-sm font-semibold text-green-300">Proven Success Path</h5>
            <p className="text-xs text-green-400">Your friend's 50M → 100M method</p>
          </div>
        </div>
        <p className="text-sm text-gray-300">
          <strong className="text-white">Bonds → Flipping → Decanting (40M profit) → Set Combining</strong>
          <br />
          This dashboard implements the exact strategies your friend used to double their capital.
        </p>
      </div>
    </motion.div>
  );
};