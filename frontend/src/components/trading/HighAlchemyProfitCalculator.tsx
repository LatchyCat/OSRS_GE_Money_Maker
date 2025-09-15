import React, { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  CurrencyDollarIcon,
  ClockIcon,
  ChartBarIcon,
  ArrowTrendingUpIcon,
  CalculatorIcon,
  BanknotesIcon,
  BoltIcon,
  BeakerIcon,
  SparklesIcon,
  XMarkIcon,
  AcademicCapIcon
} from '@heroicons/react/24/outline';
import { Wand2 } from 'lucide-react';
import { itemsApi } from '../../api/itemsApi';
import type { Item } from '../../types';

interface HighAlchemyItem extends Item {
  profit_per_cast?: number;
  nature_rune_cost?: number;
}

interface HighAlchemyProfitCalculatorProps {
  item: HighAlchemyItem;
  onClose: () => void;
  onStartTrading?: (item: HighAlchemyItem, capital: number) => void;
  onSaveStrategy?: (item: HighAlchemyItem, calculations: any) => void;
  currentCapital?: number;
  natureRunePrice?: number;
}

export const HighAlchemyProfitCalculator: React.FC<HighAlchemyProfitCalculatorProps> = ({ 
  item, 
  onClose, 
  onStartTrading, 
  onSaveStrategy,
  currentCapital = 1000000,
  natureRunePrice = 180
}) => {
  const [capital, setCapital] = useState(currentCapital);
  const [hoursPerDay, setHoursPerDay] = useState(2); // 2 hours default
  const [daysPerWeek, setDaysPerWeek] = useState(5); // 5 days default
  const [customBuyPrice, setCustomBuyPrice] = useState(item.current_buy_price || 0);
  const [customNatureRunePrice, setCustomNatureRunePrice] = useState(natureRunePrice);
  const [realTimeNatureRunePrice, setRealTimeNatureRunePrice] = useState(natureRunePrice);
  const [isLoadingNatureRune, setIsLoadingNatureRune] = useState(false);
  const [targetMagicLevel, setTargetMagicLevel] = useState(99);
  const [currentMagicLevel, setCurrentMagicLevel] = useState(55);
  
  // High Alchemy specific constants
  const XP_PER_CAST = 65;
  const CASTS_PER_HOUR = 1200;
  const HIGH_ALCH_VALUE = item.high_alch || 0;
  
  // Nature rune item ID (commonly 561 in OSRS)
  const NATURE_RUNE_ITEM_ID = 561;
  
  // Function to fetch real-time nature rune price
  const fetchNatureRunePrice = async () => {
    setIsLoadingNatureRune(true);
    try {
      // Search for nature rune by name first
      const searchResult = await itemsApi.getItems({ 
        search: 'nature rune', 
        page_size: 1 
      });
      
      if (searchResult.results && searchResult.results.length > 0) {
        const natureRune = searchResult.results[0];
        const currentPrice = natureRune.current_buy_price || natureRune.latest_price?.high_price || 180;
        setRealTimeNatureRunePrice(currentPrice);
        
        // Update the custom price if it hasn't been manually changed
        if (customNatureRunePrice === natureRunePrice) {
          setCustomNatureRunePrice(currentPrice);
        }
        
        console.log('✅ Nature rune price updated:', currentPrice, 'GP');
      }
    } catch (error) {
      console.warn('Failed to fetch nature rune price:', error);
      // Keep the current price as fallback
    } finally {
      setIsLoadingNatureRune(false);
    }
  };
  
  // Load real-time nature rune price on component mount
  React.useEffect(() => {
    fetchNatureRunePrice();
    // Refresh nature rune price every 5 minutes
    const interval = setInterval(fetchNatureRunePrice, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);
  
  // Calculate tax-adjusted high alchemy profit
  const calculateAlchemyProfit = useMemo(() => {
    const buyPrice = customBuyPrice || item.current_buy_price || 0;
    const alchValue = HIGH_ALCH_VALUE;
    const runePrice = customNatureRunePrice;
    
    // GE taxes (2% on buy and sell)
    const buyTax = buyPrice * 0.02;
    const totalBuyCost = buyPrice + buyTax;
    
    // High alchemy gives exact alch value (no tax on alchemy)
    const netProfit = alchValue - totalBuyCost - runePrice;
    const profitMargin = totalBuyCost > 0 ? (netProfit / totalBuyCost) * 100 : 0;
    
    return {
      netProfit: Math.floor(netProfit),
      profitMargin: profitMargin,
      buyTax,
      totalBuyCost,
      alchValue,
      runePrice,
      breakEvenBuyPrice: Math.floor(alchValue - runePrice) // Max buy price for 0 profit
    };
  }, [customBuyPrice, item.current_buy_price, HIGH_ALCH_VALUE, customNatureRunePrice]);

  // Helper function to get XP required for a level
  const getXPForLevel = (level: number): number => {
    if (level <= 1) return 0;
    let xp = 0;
    for (let i = 1; i < level; i++) {
      xp += Math.floor(i + 300 * Math.pow(2, i / 7));
    }
    return Math.floor(xp / 4);
  };

  // Calculate trading metrics
  const calculations = useMemo(() => {
    const { netProfit, profitMargin, totalBuyCost } = calculateAlchemyProfit;
    
    if (totalBuyCost <= 0 || netProfit <= 0) {
      return {
        maxCasts: 0,
        totalProfit: 0,
        totalXP: 0,
        profitPerHour: 0,
        xpPerHour: 0,
        timeToTarget: 0,
        hoursToBreakEven: 0,
        weeklyProfit: 0,
        natureRunesNeeded: 0,
        totalInvestment: 0
      };
    }
    
    const maxCasts = Math.floor(capital / totalBuyCost);
    const totalProfit = maxCasts * netProfit;
    const totalXP = maxCasts * XP_PER_CAST;
    const profitPerHour = netProfit * CASTS_PER_HOUR;
    const xpPerHour = XP_PER_CAST * CASTS_PER_HOUR;
    const hoursToCompleteAllCasts = maxCasts / CASTS_PER_HOUR;
    
    // XP calculations for leveling with error handling
    let xpNeeded = 0;
    let castsNeededForLevel = 0;
    let timeToTarget = 0;
    
    try {
      if (targetMagicLevel > currentMagicLevel && targetMagicLevel <= 99 && currentMagicLevel >= 1) {
        xpNeeded = Math.max(0, getXPForLevel(targetMagicLevel) - getXPForLevel(currentMagicLevel));
        castsNeededForLevel = Math.ceil(xpNeeded / XP_PER_CAST);
        timeToTarget = castsNeededForLevel / CASTS_PER_HOUR;
      }
    } catch (error) {
      console.warn('Error calculating XP requirements:', error);
      xpNeeded = 0;
      castsNeededForLevel = 0;
      timeToTarget = 0;
    }
    
    // Weekly projections
    const totalHoursPerWeek = hoursPerDay * daysPerWeek;
    const castsPerWeek = totalHoursPerWeek * CASTS_PER_HOUR;
    const weeklyProfit = castsPerWeek * netProfit;
    
    // Resource requirements
    const natureRunesNeeded = maxCasts;
    const totalInvestment = (maxCasts * totalBuyCost) + (natureRunesNeeded * customNatureRunePrice);
    
    return {
      maxCasts,
      totalProfit,
      totalXP,
      profitPerHour,
      xpPerHour,
      timeToTarget,
      hoursToBreakEven: totalInvestment / Math.max(profitPerHour, 1),
      weeklyProfit,
      natureRunesNeeded,
      totalInvestment,
      hoursToCompleteAllCasts,
      castsNeededForLevel,
      xpNeeded
    };
  }, [calculateAlchemyProfit, capital, hoursPerDay, daysPerWeek, targetMagicLevel, currentMagicLevel, customNatureRunePrice]);

  const formatGP = (amount: number) => {
    if (amount >= 1000000000) return `${(amount / 1000000000).toFixed(1)}B GP`;
    if (amount >= 1000000) return `${(amount / 1000000).toFixed(1)}M GP`;
    if (amount >= 1000) return `${(amount / 1000).toFixed(1)}K GP`;
    return `${Math.round(amount)} GP`;
  };

  const formatTime = (hours: number) => {
    if (hours >= 24) return `${(hours / 24).toFixed(1)} days`;
    return `${hours.toFixed(1)} hours`;
  };

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
        onClick={onClose}
      >
        <motion.div
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.9, opacity: 0 }}
          className="bg-gray-900 border border-gray-700 rounded-2xl w-[90rem] max-w-[95vw] h-[50rem] max-h-[90vh] flex flex-col shadow-2xl overflow-hidden"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="p-6 border-b border-gray-700 bg-gradient-to-r from-yellow-900/20 to-orange-900/20">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-yellow-500/20 rounded-xl">
                  <CalculatorIcon className="w-8 h-8 text-yellow-400" />
                </div>
                <div>
                  <h2 className="text-2xl font-bold text-white">High Alchemy Calculator</h2>
                  <p className="text-gray-400 text-lg">{item.name}</p>
                </div>
              </div>
              <button
                onClick={onClose}
                className="p-2 hover:bg-gray-700 rounded-lg transition-colors"
              >
                <XMarkIcon className="w-6 h-6 text-gray-400" />
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 p-6">
              
              {/* Left Column - Input Controls */}
              <div className="space-y-6">
                
                {/* Capital & Pricing */}
                <div className="bg-gray-800/50 rounded-xl p-6">
                  <h3 className="text-xl font-semibold text-gray-200 mb-4 flex items-center gap-2">
                    <BanknotesIcon className="w-6 h-6 text-green-400" />
                    Capital & Pricing
                  </h3>
                  
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        Available Capital
                      </label>
                      <input
                        type="number"
                        value={capital}
                        onChange={(e) => setCapital(parseInt(e.target.value) || 0)}
                        className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-yellow-500"
                        placeholder="1000000"
                      />
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        Buy Price (GP)
                      </label>
                      <input
                        type="number"
                        value={customBuyPrice}
                        onChange={(e) => setCustomBuyPrice(parseInt(e.target.value) || 0)}
                        className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-yellow-500"
                        placeholder={String(item.current_buy_price || 0)}
                      />
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2 flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <BeakerIcon className="w-4 h-4 text-orange-400" />
                          Nature Rune Price (GP)
                        </div>
                        {isLoadingNatureRune ? (
                          <div className="flex items-center gap-1 text-xs text-yellow-400">
                            <div className="animate-spin w-3 h-3 border border-yellow-400 border-t-transparent rounded-full"></div>
                            Updating...
                          </div>
                        ) : (
                          <div className="text-xs text-green-400">
                            Live: {realTimeNatureRunePrice} GP
                          </div>
                        )}
                      </label>
                      <div className="relative">
                        <input
                          type="number"
                          value={customNatureRunePrice}
                          onChange={(e) => setCustomNatureRunePrice(parseInt(e.target.value) || 180)}
                          className="w-full px-4 py-2 pr-20 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-yellow-500"
                          placeholder="180"
                        />
                        <button
                          onClick={() => setCustomNatureRunePrice(realTimeNatureRunePrice)}
                          className="absolute right-2 top-1/2 transform -translate-y-1/2 px-2 py-1 text-xs bg-orange-600 hover:bg-orange-700 text-white rounded transition-colors"
                          title="Use live price"
                        >
                          Live
                        </button>
                      </div>
                      <p className="text-xs text-gray-500 mt-1">
                        Real-time price updates every 5 minutes
                      </p>
                    </div>
                  </div>
                </div>

                {/* Magic Level Goals */}
                <div className="bg-gray-800/50 rounded-xl p-6">
                  <h3 className="text-xl font-semibold text-gray-200 mb-4 flex items-center gap-2">
                    <AcademicCapIcon className="w-6 h-6 text-purple-400" />
                    Magic Level Goals
                  </h3>
                  
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        Current Magic Level
                      </label>
                      <input
                        type="number"
                        value={currentMagicLevel}
                        onChange={(e) => setCurrentMagicLevel(Math.max(1, parseInt(e.target.value) || 1))}
                        min="1"
                        max="99"
                        className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
                      />
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        Target Magic Level
                      </label>
                      <input
                        type="number"
                        value={targetMagicLevel}
                        onChange={(e) => setTargetMagicLevel(Math.max(currentMagicLevel + 1, parseInt(e.target.value) || 99))}
                        min={currentMagicLevel + 1}
                        max="99"
                        className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
                      />
                    </div>
                  </div>
                </div>

                {/* Time Investment */}
                <div className="bg-gray-800/50 rounded-xl p-6">
                  <h3 className="text-xl font-semibold text-gray-200 mb-4 flex items-center gap-2">
                    <ClockIcon className="w-6 h-6 text-blue-400" />
                    Time Investment
                  </h3>
                  
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        Hours/Day
                      </label>
                      <input
                        type="number"
                        value={hoursPerDay}
                        onChange={(e) => setHoursPerDay(Math.max(0.1, parseFloat(e.target.value) || 0.1))}
                        step="0.5"
                        min="0.1"
                        max="24"
                        className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        Days/Week
                      </label>
                      <input
                        type="number"
                        value={daysPerWeek}
                        onChange={(e) => setDaysPerWeek(Math.max(1, parseInt(e.target.value) || 1))}
                        min="1"
                        max="7"
                        className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                  </div>
                </div>
              </div>

              {/* Right Column - Results & Analysis */}
              <div className="space-y-6">
                
                {/* Profit Analysis */}
                <div className="bg-gradient-to-br from-green-900/20 to-emerald-900/20 border border-green-700/30 rounded-xl p-6">
                  <h3 className="text-xl font-semibold text-green-200 mb-4 flex items-center gap-2">
                    <CurrencyDollarIcon className="w-6 h-6 text-green-400" />
                    Profit Analysis
                  </h3>
                  
                  <div className="grid grid-cols-2 gap-4">
                    <div className="bg-gray-800/50 rounded-lg p-4">
                      <div className="text-sm text-gray-400">Profit per Cast</div>
                      <div className={`text-2xl font-bold ${calculateAlchemyProfit.netProfit > 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {calculateAlchemyProfit.netProfit > 0 ? '+' : ''}{formatGP(calculateAlchemyProfit.netProfit)}
                      </div>
                    </div>
                    
                    <div className="bg-gray-800/50 rounded-lg p-4">
                      <div className="text-sm text-gray-400">Profit Margin</div>
                      <div className={`text-2xl font-bold ${calculateAlchemyProfit.profitMargin > 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {calculateAlchemyProfit.profitMargin.toFixed(1)}%
                      </div>
                    </div>
                    
                    <div className="bg-gray-800/50 rounded-lg p-4">
                      <div className="text-sm text-gray-400">GP per Hour</div>
                      <div className="text-2xl font-bold text-emerald-400">
                        {formatGP(calculations.profitPerHour)}
                      </div>
                    </div>
                    
                    <div className="bg-gray-800/50 rounded-lg p-4">
                      <div className="text-sm text-gray-400">Weekly Profit</div>
                      <div className="text-2xl font-bold text-emerald-400">
                        {formatGP(calculations.weeklyProfit)}
                      </div>
                    </div>
                  </div>
                  
                  <div className="mt-4 p-4 bg-gray-800/30 rounded-lg">
                    <div className="text-sm text-gray-400 mb-2">Break-even Buy Price</div>
                    <div className="text-lg font-semibold text-yellow-400">
                      {formatGP(calculateAlchemyProfit.breakEvenBuyPrice)} GP
                    </div>
                    <div className="text-xs text-gray-500">
                      Buy above this price and you'll lose money
                    </div>
                  </div>
                </div>

                {/* XP Analysis */}
                <div className="bg-gradient-to-br from-purple-900/20 to-blue-900/20 border border-purple-700/30 rounded-xl p-6">
                  <h3 className="text-xl font-semibold text-purple-200 mb-4 flex items-center gap-2">
                    <SparklesIcon className="w-6 h-6 text-purple-400" />
                    XP Analysis
                  </h3>
                  
                  <div className="grid grid-cols-2 gap-4">
                    <div className="bg-gray-800/50 rounded-lg p-4">
                      <div className="text-sm text-gray-400">XP per Hour</div>
                      <div className="text-2xl font-bold text-purple-400">
                        {calculations.xpPerHour.toLocaleString()}
                      </div>
                    </div>
                    
                    <div className="bg-gray-800/50 rounded-lg p-4">
                      <div className="text-sm text-gray-400">XP Needed</div>
                      <div className="text-2xl font-bold text-blue-400">
                        {(calculations.xpNeeded || 0).toLocaleString()}
                      </div>
                    </div>
                    
                    <div className="bg-gray-800/50 rounded-lg p-4">
                      <div className="text-sm text-gray-400">Time to Target</div>
                      <div className="text-2xl font-bold text-purple-400">
                        {formatTime(calculations.timeToTarget || 0)}
                      </div>
                    </div>
                    
                    <div className="bg-gray-800/50 rounded-lg p-4">
                      <div className="text-sm text-gray-400">Casts Needed</div>
                      <div className="text-2xl font-bold text-blue-400">
                        {(calculations.castsNeededForLevel || 0).toLocaleString()}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Resource Requirements */}
                <div className="bg-gray-800/50 rounded-xl p-6">
                  <h3 className="text-xl font-semibold text-gray-200 mb-4 flex items-center gap-2">
                    <ChartBarIcon className="w-6 h-6 text-orange-400" />
                    Resource Requirements
                  </h3>
                  
                  <div className="space-y-4">
                    <div className="flex justify-between items-center py-2 border-b border-gray-700">
                      <span className="text-gray-300">Maximum Casts with Capital</span>
                      <span className="font-semibold text-white">{calculations.maxCasts.toLocaleString()}</span>
                    </div>
                    
                    <div className="flex justify-between items-center py-2 border-b border-gray-700">
                      <span className="text-gray-300 flex items-center gap-2">
                        <BeakerIcon className="w-4 h-4 text-orange-400" />
                        Nature Runes Needed
                      </span>
                      <span className="font-semibold text-white">{calculations.natureRunesNeeded.toLocaleString()}</span>
                    </div>
                    
                    <div className="flex justify-between items-center py-2 border-b border-gray-700">
                      <span className="text-gray-300">Total Investment</span>
                      <span className="font-semibold text-yellow-400">{formatGP(calculations.totalInvestment)}</span>
                    </div>
                    
                    <div className="flex justify-between items-center py-2">
                      <span className="text-gray-300">Total Potential Profit</span>
                      <span className={`font-bold text-xl ${calculations.totalProfit > 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {calculations.totalProfit > 0 ? '+' : ''}{formatGP(calculations.totalProfit)}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Footer Actions */}
          <div className="p-6 border-t border-gray-700 bg-gray-800/50">
            <div className="flex justify-between items-center">
              <div className="text-sm text-gray-400">
                {calculations.totalProfit > 0 ? (
                  <span className="text-green-400">✅ Profitable Strategy</span>
                ) : (
                  <span className="text-red-400">⚠️ Unprofitable - Adjust pricing</span>
                )}
              </div>
              
              <div className="flex gap-3">
                <button
                  onClick={onClose}
                  className="px-6 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
                >
                  Close
                </button>
                
                {onSaveStrategy && (
                  <button
                    onClick={() => onSaveStrategy(item, calculations)}
                    className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
                  >
                    Save Strategy
                  </button>
                )}
                
                {onStartTrading && calculations.totalProfit > 0 && (
                  <button
                    onClick={() => onStartTrading(item, capital)}
                    className="px-6 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors flex items-center gap-2"
                  >
                    <Wand2 className="w-4 h-4" />
                    Start Alching
                  </button>
                )}
              </div>
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};

export default HighAlchemyProfitCalculator;