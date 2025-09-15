import React from 'react';
import { motion } from 'framer-motion';
import { Database, Activity } from 'lucide-react';
import { WealthVisualization } from '../effects/WealthVisualization';
import type { Item } from '../../types';

interface ItemsTrackedSectionProps {
  topItems: Item[];
  totalItems?: number;
  className?: string;
}

export const ItemsTrackedSection: React.FC<ItemsTrackedSectionProps> = ({
  topItems,
  totalItems = 4307,
  className = ''
}) => {
  const calculateProfitLevel = (): number => {
    if (topItems.length === 0) return 0.5;
    const avgProfit = topItems.reduce((sum, item) => sum + (item.current_profit || 0), 0) / topItems.length;
    return Math.min(Math.max(avgProfit / 50000, 0), 1);
  };

  const getTotalRecentProfit = (): number => {
    return topItems.reduce((sum, item) => sum + (item.current_profit || 0), 0);
  };

  return (
    <motion.section
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.15 }}
      className={className}
    >
      {/* Section Header */}
      <div className="mb-4">
        <motion.h2
          className="text-lg font-semibold bg-gradient-to-r from-white via-blue-200 to-cyan-200 bg-clip-text text-transparent"
          animate={{ 
            textShadow: '0 0 15px rgba(59,130,246,0.3)'
          }}
        >
          Items Database
        </motion.h2>
        <p className="text-gray-400 text-sm mt-1">
          Tracking profitable opportunities across OSRS
        </p>
      </div>

      {/* Items Tracked Card */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="relative bg-black/40 backdrop-blur-xl border border-blue-400/30 hover:border-blue-400/60 rounded-xl overflow-hidden shadow-2xl shadow-blue-400/25 transition-all duration-500 hover:animate-hologram-glow group"
      >
        {/* Holographic Effects */}
        <div 
          className="absolute inset-0 opacity-0 group-hover:opacity-30 transition-opacity duration-700"
          style={{
            background: `linear-gradient(135deg, transparent 0%, rgba(0,255,255,0.1) 45%, rgba(255,255,255,0.4) 50%, rgba(0,255,255,0.1) 55%, transparent 100%)`,
            transform: 'translateX(-100%) skewX(-15deg)',
            animation: 'hologramShimmer 3s ease-in-out infinite'
          }}
        />
        
        <div className="absolute inset-0 rounded-xl bg-gradient-to-r from-transparent via-cyan-400/30 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 animate-hologram-shimmer" />
        
        <div className="absolute inset-0 overflow-hidden rounded-xl">
          <div 
            className="absolute w-full h-0.5 bg-gradient-to-r from-transparent via-cyan-400 to-transparent opacity-0 group-hover:opacity-60"
            style={{ 
              filter: 'blur(0.3px)',
              boxShadow: '0 0 8px rgba(0,255,255,0.8)',
              animation: 'scanLine 4s linear infinite'
            }}
          />
        </div>
        
        {/* Card Content */}
        <div className="relative z-10 p-6 space-y-4">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <motion.div
                animate={{ 
                  rotate: [0, 360],
                  scale: [1, 1.1, 1]
                }}
                transition={{ 
                  duration: 3,
                  repeat: Infinity,
                  ease: "easeInOut"
                }}
              >
                <Database className="w-5 h-5 text-blue-400 drop-shadow-lg" />
              </motion.div>
              <h3 className="font-semibold text-white bg-gradient-to-r from-white to-blue-200 bg-clip-text text-transparent">
                Items Tracked
              </h3>
            </div>
            <div className="w-2 h-2 bg-cyan-400 rounded-full animate-pulse shadow-lg shadow-cyan-400/75" />
          </div>
          
          {/* Main Content */}
          <div className="space-y-3">
            {/* Total Items Counter */}
            <WealthVisualization
              totalValue={totalItems * 1000} // Simulating total tracked item value
              recentProfit={getTotalRecentProfit()}
              intensity={calculateProfitLevel()}
              className="text-2xl"
            />
            
            <div className="space-y-2">
              <p className="text-sm text-gray-400">
                Active OSRS items in database
              </p>
              
              {/* Progress indicator */}
              <div className="w-full h-1.5 bg-black/50 rounded-full overflow-hidden">
                <motion.div
                  className="h-full bg-gradient-to-r from-blue-400 via-cyan-400 to-emerald-400 shadow-lg shadow-blue-400/50"
                  initial={{ width: 0 }}
                  animate={{ width: '92%' }}
                  transition={{ duration: 2, delay: 0.5 }}
                />
              </div>
              
              {/* Stats */}
              <div className="grid grid-cols-2 gap-4 mt-3">
                <div className="text-center">
                  <div className="text-lg font-bold text-emerald-400 drop-shadow-lg">
                    {topItems.length}
                  </div>
                  <div className="text-xs text-gray-400">Top Profitable</div>
                </div>
                <div className="text-center">
                  <div className="text-lg font-bold text-blue-400 drop-shadow-lg">
                    {Math.round(calculateProfitLevel() * 100)}%
                  </div>
                  <div className="text-xs text-gray-400">Opportunity Level</div>
                </div>
              </div>
            </div>
          </div>

          {/* Data Quality Indicator */}
          <div className="flex items-center justify-between pt-2 border-t border-white/10">
            <div className="flex items-center space-x-1">
              <Activity className="w-3 h-3 text-cyan-400" />
              <span className="text-xs text-cyan-300">Live Sync</span>
            </div>
            
            <div className="text-xs text-gray-400">
              Updated {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </div>
          </div>
        </div>
        
        {/* Corner Accent Lights */}
        <div className="absolute top-2 right-2 w-1.5 h-1.5 bg-cyan-400 rounded-full opacity-50 group-hover:opacity-100 transition-opacity duration-300 shadow-lg shadow-cyan-400/75" />
        <div className="absolute bottom-2 left-2 w-1.5 h-1.5 bg-blue-400 rounded-full opacity-50 group-hover:opacity-100 transition-opacity duration-300 shadow-lg shadow-blue-400/75" />
      </motion.div>
    </motion.section>
  );
};