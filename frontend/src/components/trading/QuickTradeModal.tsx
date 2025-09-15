import React, { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  XMarkIcon,
  BoltIcon,
  CurrencyDollarIcon,
  ChartBarIcon,
  ClockIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  BeakerIcon,
  ArrowRightIcon,
  SparklesIcon,
  TrophyIcon
} from '@heroicons/react/24/outline';
import type { DecantingOpportunity } from '../../types/tradingStrategies';

interface QuickTradeModalProps {
  isOpen: boolean;
  onClose: () => void;
  opportunity: DecantingOpportunity;
  currentCapital: number;
  onTradeComplete: (tradeResult: {
    profit: number;
    quantity: number;
    success: boolean;
    experience?: number;
  }) => void;
}

export const QuickTradeModal: React.FC<QuickTradeModalProps> = ({
  isOpen,
  onClose,
  opportunity,
  currentCapital,
  onTradeComplete
}) => {
  const [quantity, setQuantity] = useState(1);
  const [isExecuting, setIsExecuting] = useState(false);
  const [executionStep, setExecutionStep] = useState(0);
  const [tradeResult, setTradeResult] = useState<any>(null);

  // Calculate trade metrics
  const tradeMetrics = useMemo(() => {
    const investmentPerUnit = opportunity.from_dose_price;
    const profitPerUnit = opportunity.profit_per_conversion;
    const totalInvestment = investmentPerUnit * quantity;
    const totalProfit = profitPerUnit * quantity;
    const totalRevenue = totalInvestment + totalProfit;
    const profitMargin = (totalProfit / totalInvestment) * 100;
    
    // Calculate max quantity based on capital
    const maxQuantity = Math.floor(currentCapital / investmentPerUnit);
    const capitalUsed = (totalInvestment / currentCapital) * 100;
    
    // Estimate execution time (mock)
    const executionTime = quantity * 10; // 10 seconds per conversion
    
    return {
      investmentPerUnit,
      profitPerUnit,
      totalInvestment,
      totalProfit,
      totalRevenue,
      profitMargin,
      maxQuantity,
      capitalUsed,
      executionTime,
      canAfford: totalInvestment <= currentCapital
    };
  }, [quantity, opportunity, currentCapital]);

  const formatGP = (amount: number) => {
    if (amount >= 1000000000) return `${(amount / 1000000000).toFixed(1)}B GP`;
    if (amount >= 1000000) return `${(amount / 1000000).toFixed(1)}M GP`;
    if (amount >= 1000) return `${(amount / 1000).toFixed(1)}K GP`;
    return `${Math.round(amount)} GP`;
  };

  const formatTime = (seconds: number) => {
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds}s`;
  };

  const executeQuickTrade = async () => {
    if (!tradeMetrics.canAfford || quantity < 1) return;
    
    setIsExecuting(true);
    setExecutionStep(0);

    // Simulate trade execution steps
    const steps = [
      { name: 'Preparing trade...', delay: 500 },
      { name: 'Buying items from Grand Exchange...', delay: 1000 },
      { name: 'Processing decanting...', delay: 1500 },
      { name: 'Selling converted items...', delay: 1000 },
      { name: 'Calculating profits...', delay: 800 }
    ];

    for (let i = 0; i < steps.length; i++) {
      setExecutionStep(i);
      await new Promise(resolve => setTimeout(resolve, steps[i].delay));
    }

    // Simulate trade success/failure (95% success rate)
    const success = Math.random() > 0.05;
    const actualProfit = success ? tradeMetrics.totalProfit : -Math.round(tradeMetrics.totalInvestment * 0.1);
    const experience = success ? quantity * 25 : 0; // XP for successful trades

    const result = {
      profit: actualProfit,
      quantity,
      success,
      experience,
      executionTime: tradeMetrics.executionTime
    };

    setTradeResult(result);
    onTradeComplete(result);
    setIsExecuting(false);
  };

  const closeModal = () => {
    setTradeResult(null);
    setExecutionStep(0);
    setIsExecuting(false);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
        onClick={closeModal}
      >
        <motion.div
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.9, opacity: 0 }}
          className="bg-gray-900 border border-gray-700 rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="p-6 border-b border-gray-700 bg-gradient-to-r from-green-900/20 to-emerald-900/20">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-green-500/20 rounded-lg">
                  <BoltIcon className="w-6 h-6 text-green-400" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-white">Quick Trade</h2>
                  <p className="text-gray-400">
                    {opportunity.item_name} • {opportunity.from_dose}→{opportunity.to_dose} dose
                  </p>
                </div>
              </div>
              <button
                onClick={closeModal}
                disabled={isExecuting}
                className="p-2 hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50"
              >
                <XMarkIcon className="w-6 h-6 text-gray-400" />
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="p-6">
            {!tradeResult && !isExecuting && (
              <>
                {/* Quantity Selector */}
                <div className="mb-6">
                  <div className="flex items-center justify-between mb-3">
                    <label className="text-lg font-semibold text-white">Quantity</label>
                    <span className="text-sm text-gray-400">
                      Max: {tradeMetrics.maxQuantity.toLocaleString()}
                    </span>
                  </div>
                  <div className="flex items-center gap-4">
                    <input
                      type="range"
                      min="1"
                      max={tradeMetrics.maxQuantity}
                      value={quantity}
                      onChange={(e) => setQuantity(parseInt(e.target.value))}
                      className="flex-1 h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer slider"
                    />
                    <div className="flex items-center gap-2">
                      <input
                        type="number"
                        min="1"
                        max={tradeMetrics.maxQuantity}
                        value={quantity}
                        onChange={(e) => setQuantity(Math.max(1, Math.min(tradeMetrics.maxQuantity, parseInt(e.target.value) || 1)))}
                        className="w-24 px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white text-center"
                      />
                      <button
                        onClick={() => setQuantity(tradeMetrics.maxQuantity)}
                        className="px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-lg transition-colors"
                      >
                        Max
                      </button>
                    </div>
                  </div>
                </div>

                {/* Trade Summary */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                  <div className="bg-gray-800/50 rounded-xl p-4">
                    <h3 className="text-sm font-medium text-gray-400 mb-3">Investment</h3>
                    <div className="space-y-2">
                      <div className="flex justify-between">
                        <span className="text-gray-300">Per Unit</span>
                        <span className="text-white">{formatGP(tradeMetrics.investmentPerUnit)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-300">Total</span>
                        <span className="text-orange-400 font-bold">{formatGP(tradeMetrics.totalInvestment)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-300">Capital Used</span>
                        <span className="text-blue-400">{tradeMetrics.capitalUsed.toFixed(1)}%</span>
                      </div>
                    </div>
                  </div>

                  <div className="bg-gray-800/50 rounded-xl p-4">
                    <h3 className="text-sm font-medium text-gray-400 mb-3">Returns</h3>
                    <div className="space-y-2">
                      <div className="flex justify-between">
                        <span className="text-gray-300">Per Unit</span>
                        <span className="text-white">{formatGP(tradeMetrics.profitPerUnit)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-300">Total Profit</span>
                        <span className="text-green-400 font-bold">{formatGP(tradeMetrics.totalProfit)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-300">Margin</span>
                        <span className="text-purple-400">{tradeMetrics.profitMargin.toFixed(1)}%</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Trade Process */}
                <div className="bg-gray-800/30 rounded-xl p-4 mb-6">
                  <h3 className="text-sm font-medium text-gray-400 mb-3">Trade Process</h3>
                  <div className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                      <BeakerIcon className="w-4 h-4 text-blue-400" />
                      <span className="text-gray-300">Buy {opportunity.from_dose}-dose</span>
                    </div>
                    <ArrowRightIcon className="w-4 h-4 text-gray-500" />
                    <div className="flex items-center gap-2">
                      <SparklesIcon className="w-4 h-4 text-yellow-400" />
                      <span className="text-gray-300">Decant</span>
                    </div>
                    <ArrowRightIcon className="w-4 h-4 text-gray-500" />
                    <div className="flex items-center gap-2">
                      <CurrencyDollarIcon className="w-4 h-4 text-green-400" />
                      <span className="text-gray-300">Sell {opportunity.to_dose}-dose</span>
                    </div>
                  </div>
                  <div className="mt-3 text-center text-xs text-gray-500">
                    Estimated time: {formatTime(tradeMetrics.executionTime)}
                  </div>
                </div>

                {/* Execute Button */}
                <div className="flex gap-3">
                  <button
                    onClick={executeQuickTrade}
                    disabled={!tradeMetrics.canAfford || quantity < 1}
                    className="flex-1 flex items-center justify-center gap-3 py-4 bg-green-600 hover:bg-green-700 disabled:bg-gray-700 disabled:opacity-50 text-white font-bold rounded-xl transition-colors"
                  >
                    <BoltIcon className="w-5 h-5" />
                    Execute Trade • {formatGP(tradeMetrics.totalProfit)} profit
                  </button>
                  <button
                    onClick={closeModal}
                    className="px-6 py-4 bg-gray-700 hover:bg-gray-600 text-white font-medium rounded-xl transition-colors"
                  >
                    Cancel
                  </button>
                </div>

                {!tradeMetrics.canAfford && (
                  <div className="mt-4 p-3 bg-red-900/20 border border-red-500/30 rounded-lg flex items-center gap-2">
                    <ExclamationTriangleIcon className="w-5 h-5 text-red-400 flex-shrink-0" />
                    <span className="text-red-300 text-sm">
                      Insufficient capital. Need {formatGP(tradeMetrics.totalInvestment - currentCapital)} more GP.
                    </span>
                  </div>
                )}
              </>
            )}

            {/* Execution Progress */}
            {isExecuting && (
              <div className="text-center py-8">
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                  className="w-16 h-16 mx-auto mb-4"
                >
                  <BoltIcon className="w-16 h-16 text-green-400" />
                </motion.div>
                <h3 className="text-xl font-bold text-white mb-2">Executing Trade</h3>
                <div className="space-y-2">
                  {['Preparing trade...', 'Buying items...', 'Processing...', 'Selling items...', 'Finalizing...'].map((step, index) => (
                    <div 
                      key={index}
                      className={`text-sm ${index === executionStep ? 'text-green-400' : index < executionStep ? 'text-green-300' : 'text-gray-500'}`}
                    >
                      {index === executionStep && '⚡ '}{step}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Trade Result */}
            {tradeResult && (
              <div className="text-center py-8">
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  className="w-16 h-16 mx-auto mb-4"
                >
                  {tradeResult.success ? (
                    <CheckCircleIcon className="w-16 h-16 text-green-400" />
                  ) : (
                    <ExclamationTriangleIcon className="w-16 h-16 text-red-400" />
                  )}
                </motion.div>
                
                <h3 className="text-2xl font-bold text-white mb-2">
                  {tradeResult.success ? 'Trade Successful!' : 'Trade Failed'}
                </h3>
                
                <div className="grid grid-cols-2 gap-4 max-w-md mx-auto mb-6">
                  <div className="bg-gray-800/50 rounded-lg p-3">
                    <div className="text-sm text-gray-400">Profit/Loss</div>
                    <div className={`text-lg font-bold ${tradeResult.success ? 'text-green-400' : 'text-red-400'}`}>
                      {tradeResult.success ? '+' : ''}{formatGP(tradeResult.profit)}
                    </div>
                  </div>
                  <div className="bg-gray-800/50 rounded-lg p-3">
                    <div className="text-sm text-gray-400">Quantity</div>
                    <div className="text-lg font-bold text-white">
                      {tradeResult.quantity.toLocaleString()}
                    </div>
                  </div>
                  {tradeResult.success && tradeResult.experience && (
                    <div className="col-span-2 bg-gradient-to-r from-purple-900/20 to-blue-900/20 border border-purple-500/30 rounded-lg p-3">
                      <div className="flex items-center justify-center gap-2">
                        <TrophyIcon className="w-5 h-5 text-purple-400" />
                        <span className="text-sm text-gray-300">Experience Gained</span>
                        <span className="text-lg font-bold text-purple-400">+{tradeResult.experience} XP</span>
                      </div>
                    </div>
                  )}
                </div>

                <button
                  onClick={closeModal}
                  className="px-8 py-3 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-xl transition-colors"
                >
                  Continue Trading
                </button>
              </div>
            )}
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};

export default QuickTradeModal;