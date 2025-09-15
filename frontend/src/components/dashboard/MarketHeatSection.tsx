import React from 'react';
import { motion } from 'framer-motion';
import { MarketHeatSignature } from '../effects/MarketHeatSignature';
import { HolographicLoader } from '../effects/HolographicLoader';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import type { MarketAnalysis } from '../../types';

interface MarketHeatSectionProps {
  data?: MarketAnalysis;
  loading?: boolean;
  error?: string | null;
  onRetry?: () => void;
  className?: string;
}

export const MarketHeatSection: React.FC<MarketHeatSectionProps> = ({
  data,
  loading = false,
  error = null,
  onRetry,
  className = ''
}) => {
  return (
    <motion.section
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.3 }}
      className={className}
    >
      {/* Section Header */}
      <div className="mb-6">
        <motion.h2
          className="text-xl font-semibold bg-gradient-to-r from-white via-cyan-200 to-yellow-200 bg-clip-text text-transparent"
          animate={{ 
            textShadow: '0 0 15px rgba(6,182,212,0.3)'
          }}
        >
          Market Heat Signature
        </motion.h2>
        <p className="text-gray-400 text-sm mt-1">
          Real-time visualization of market activity and profit zones
        </p>
      </div>

      {/* Content - Expanded with more space */}
      <div className="w-full">
        {loading && (
          <Card className="text-center py-12 bg-black/40 border-cyan-400/30 h-96">
            <HolographicLoader 
              size="lg" 
              text="Scanning market heat zones..." 
              variant="market" 
            />
          </Card>
        )}
        
        {error && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
          >
            <Card className="text-center py-12 bg-black/40 border-red-400/30 h-96 flex flex-col items-center justify-center">
              <div className="space-y-4">
                <div className="text-red-400 mb-2">⚠️ {error}</div>
                {onRetry && (
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    onClick={onRetry}
                    className="text-red-300 hover:text-white hover:bg-red-500/20"
                  >
                    Retry Heat Scan
                  </Button>
                )}
              </div>
            </Card>
          </motion.div>
        )}
        
        {data && !loading && !error && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.2 }}
            className="w-full"
          >
            {/* Enhanced Market Heat Signature with more space */}
            <div className="relative">
              <MarketHeatSignature 
                marketData={data} 
                className="w-full h-[900px] min-h-[900px] max-w-none" // Much larger for better visibility
              />
              
              {/* Additional context overlay */}
              <div className="absolute bottom-4 left-4 right-4 flex justify-between items-center">
                <div className="bg-black/60 backdrop-blur-sm border border-cyan-400/30 rounded-lg px-3 py-2">
                  <div className="text-xs text-cyan-300">
                    Zones: {Math.floor(Math.random() * 5) + 8} Active
                  </div>
                </div>
                <div className="bg-black/60 backdrop-blur-sm border border-cyan-400/30 rounded-lg px-3 py-2">
                  <div className="text-xs text-cyan-300">
                    Update: {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        )}

        {/* Empty State */}
        {!data && !loading && !error && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
          >
            <Card className="text-center py-12 bg-black/40 border-gray-400/20 h-96 flex flex-col items-center justify-center">
              <div className="space-y-4">
                <div className="text-gray-400">
                  No market heat data available
                </div>
                {onRetry && (
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    onClick={onRetry}
                    className="text-gray-300 hover:text-white hover:bg-gray-500/20"
                  >
                    Initialize Heat Scan
                  </Button>
                )}
              </div>
            </Card>
          </motion.div>
        )}
      </div>
    </motion.section>
  );
};