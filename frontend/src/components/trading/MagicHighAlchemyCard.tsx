import React from 'react';
import { motion } from 'framer-motion';
import { 
  BoltIcon,
  ClockIcon,
  SparklesIcon,
  ChartBarIcon,
  StarIcon,
  AcademicCapIcon
} from '@heroicons/react/24/outline';
import { Zap } from 'lucide-react';

interface HighAlchemyOpportunity {
  item_id: number;
  item_name: string;
  buy_price: number;
  alch_value: number;
  profit_per_alch: number;
  nature_rune_cost: number;
  magic_level_required: number;
  hourly_profit_potential: number;
}

interface MagicHighAlchemyCardProps {
  opportunity: HighAlchemyOpportunity;
  onClick?: () => void;
  className?: string;
}

export function MagicHighAlchemyCard({ 
  opportunity, 
  onClick, 
  className = '' 
}: MagicHighAlchemyCardProps) {
  const formatPrice = (price: number) => {
    if (price >= 1000000) {
      return `${(price / 1000000).toFixed(1)}M`;
    } else if (price >= 1000) {
      return `${(price / 1000).toFixed(1)}K`;
    }
    return price.toLocaleString();
  };

  const getLevelColor = (level: number) => {
    if (level >= 75) return 'text-purple-400';
    if (level >= 55) return 'text-blue-400';
    if (level >= 35) return 'text-yellow-400';
    return 'text-green-400';
  };

  const getProfitColor = (profit: number) => {
    if (profit >= 500) return 'text-emerald-400';
    if (profit >= 200) return 'text-green-400';
    if (profit >= 50) return 'text-yellow-400';
    return 'text-red-400';
  };

  const isHighProfit = opportunity.profit_per_alch >= 200;
  const isVeryHighProfit = opportunity.profit_per_alch >= 500;

  // Calculate casts per hour (standard is ~1200)
  const castsPerHour = 1200;
  const xpPerCast = 65; // High alchemy XP
  const xpPerHour = castsPerHour * xpPerCast;

  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      className={`bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6 cursor-pointer transition-all duration-200 hover:border-yellow-500/50 hover:shadow-lg hover:shadow-yellow-500/10 ${className}`}
      onClick={onClick}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <Zap className="w-5 h-5 text-yellow-400" />
            <h3 className="text-lg font-semibold text-gray-100">
              {opportunity.item_name}
            </h3>
          </div>
          <div className="flex items-center gap-2">
            <div className="px-3 py-1.5 rounded-full border bg-yellow-400/10 border-yellow-400/30 text-yellow-400">
              <div className="flex items-center gap-2 text-sm font-semibold">
                <BoltIcon className="w-3 h-3" />
                <span>HIGH ALCH</span>
              </div>
            </div>
            {isVeryHighProfit && (
              <div className="px-2 py-1 rounded-full text-xs font-semibold text-green-400 bg-green-400/10 border border-green-400/30">
                HOT
              </div>
            )}
          </div>
        </div>
        <div className="flex flex-col items-end gap-2">
          <div className={`text-right ${getLevelColor(opportunity.magic_level_required)}`}>
            <div className="text-xs text-gray-400">Magic Level</div>
            <div className="text-sm font-bold">
              {opportunity.magic_level_required}
            </div>
          </div>
        </div>
      </div>

      {/* Key Metrics Grid */}
      <div className="grid grid-cols-3 gap-4 mb-4">
        <div className="text-center">
          <div className="text-xs text-gray-400 mb-1">Profit/Cast</div>
          <div className={`text-lg font-bold ${getProfitColor(opportunity.profit_per_alch)}`}>
            +{formatPrice(opportunity.profit_per_alch)} gp
          </div>
        </div>
        <div className="text-center">
          <div className="text-xs text-gray-400 mb-1">GP/Hour</div>
          <div className="text-lg font-bold text-emerald-400">
            {formatPrice(opportunity.hourly_profit_potential)} gp/h
          </div>
        </div>
        <div className="text-center">
          <div className="text-xs text-gray-400 mb-1">XP/Hour</div>
          <div className="text-lg font-bold text-blue-400">
            {formatPrice(xpPerHour)} xp/h
          </div>
        </div>
      </div>

      {/* Price Breakdown */}
      <div className="mb-4">
        <div className="text-sm text-gray-400 mb-2">Price Analysis</div>
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-gray-700/30 rounded-lg p-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-300">Buy Price</span>
              <span className="text-sm font-semibold text-red-300">
                {formatPrice(opportunity.buy_price)} gp
              </span>
            </div>
          </div>
          <div className="bg-gray-700/30 rounded-lg p-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-300">Alch Value</span>
              <span className="text-sm font-semibold text-green-300">
                {formatPrice(opportunity.alch_value)} gp
              </span>
            </div>
          </div>
        </div>
        <div className="mt-2 bg-gray-700/20 rounded-lg p-3">
          <div className="flex items-center justify-between text-xs">
            <span className="text-gray-400">Nature Rune Cost:</span>
            <span className="text-orange-300">{formatPrice(opportunity.nature_rune_cost)} gp</span>
          </div>
        </div>
      </div>

      {/* Profit Calculation */}
      <div className="mb-4">
        <div className="text-sm text-gray-400 mb-2">Profit Breakdown</div>
        <div className="bg-gray-700/20 rounded-lg p-3 space-y-1 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-400">Alch Value:</span>
            <span className="text-green-400">+{formatPrice(opportunity.alch_value)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Buy Price:</span>
            <span className="text-red-400">-{formatPrice(opportunity.buy_price)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Nature Rune:</span>
            <span className="text-orange-400">-{formatPrice(opportunity.nature_rune_cost)}</span>
          </div>
          <div className="border-t border-gray-600 pt-1 flex justify-between font-semibold">
            <span className="text-gray-300">Net Profit:</span>
            <span className={getProfitColor(opportunity.profit_per_alch)}>
              +{formatPrice(opportunity.profit_per_alch)} gp
            </span>
          </div>
        </div>
      </div>

      {/* Casting Rate */}
      <div className="mb-4">
        <div className="text-sm text-gray-400 mb-2">Casting Information</div>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div className="bg-gray-700/20 rounded-lg p-3">
            <div className="text-xs text-gray-400 mb-1">Rate per Hour</div>
            <div className="text-sm font-semibold text-gray-200">
              {castsPerHour.toLocaleString()} casts
            </div>
          </div>
          <div className="bg-gray-700/20 rounded-lg p-3">
            <div className="text-xs text-gray-400 mb-1">Magic XP/Cast</div>
            <div className="text-sm font-semibold text-gray-200">
              {xpPerCast} xp
            </div>
          </div>
        </div>
      </div>

      {/* Item ID and Requirements */}
      <div className="mb-4">
        <div className="text-sm text-gray-400 mb-2">Requirements</div>
        <div className="flex items-center justify-between bg-gray-700/20 rounded-lg p-3">
          <div className="flex items-center gap-2">
            <AcademicCapIcon className="w-4 h-4 text-blue-400" />
            <span className="text-sm text-gray-300">
              Magic Level {opportunity.magic_level_required}+
            </span>
          </div>
          <div className="text-sm">
            <span className="text-gray-400">Item ID: </span>
            <span className="font-semibold text-gray-300">
              {opportunity.item_id}
            </span>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="border-t border-gray-700/50 pt-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ChartBarIcon className="w-4 h-4 text-green-400" />
            <span className="text-sm text-gray-300">
              High Alchemy Method
            </span>
          </div>
          <div className="flex items-center gap-2">
            <ClockIcon className="w-4 h-4 text-blue-400" />
            <span className="text-sm text-gray-300">
              ~3s per cast
            </span>
          </div>
        </div>
      </div>

      {/* Profit Quality Indicators */}
      {isHighProfit && (
        <div className={`mt-3 px-3 py-2 rounded-lg ${isVeryHighProfit 
          ? 'bg-green-400/10 border border-green-400/30' 
          : 'bg-yellow-400/10 border border-yellow-400/30'
        }`}>
          <div className="flex items-center gap-2">
            <StarIcon className={`w-4 h-4 ${isVeryHighProfit ? 'text-green-400' : 'text-yellow-400'}`} />
            <span className={`text-sm font-medium ${isVeryHighProfit ? 'text-green-400' : 'text-yellow-400'}`}>
              {isVeryHighProfit ? 'Excellent Profit' : 'Good Profit'}
            </span>
          </div>
        </div>
      )}
    </motion.div>
  );
}

export default MagicHighAlchemyCard;