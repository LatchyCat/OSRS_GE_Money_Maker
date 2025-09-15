import React from 'react';
import { motion } from 'framer-motion';
import { HolographicStatsCard } from '../effects/HolographicStatsCard';
import { HolographicLoader } from '../effects/HolographicLoader';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import type { MarketAnalysis } from '../../types';

interface MarketStatsSectionProps {
  data?: MarketAnalysis;
  loading?: boolean;
  error?: string | null;
  onRetry?: () => void;
  className?: string;
}

export const MarketStatsSection: React.FC<MarketStatsSectionProps> = ({
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
      transition={{ delay: 0.1 }}
      className={className}
    >
      {/* Section Header */}
      <div className="mb-6">
        <motion.h2
          className="text-xl font-semibold bg-gradient-to-r from-white via-emerald-200 to-cyan-200 bg-clip-text text-transparent"
          animate={{ 
            textShadow: '0 0 15px rgba(16,185,129,0.3)'
          }}
        >
          Market Analysis
        </motion.h2>
        <p className="text-gray-400 text-sm mt-1">
          Real-time market insights and profit opportunities
        </p>
      </div>

      {/* Content */}
      {loading && (
        <Card className="text-center py-8 bg-black/40 border-emerald-400/30">
          <HolographicLoader 
            size="md" 
            text="Analyzing market data..." 
            variant="data" 
          />
        </Card>
      )}
      
      {error && (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
        >
          <Card className="text-center py-8 bg-black/40 border-red-400/30">
            <div className="space-y-4">
              <div className="text-red-400 mb-2">⚠️ {error}</div>
              {onRetry && (
                <Button 
                  variant="ghost" 
                  size="sm" 
                  onClick={onRetry}
                  className="text-red-300 hover:text-white hover:bg-red-500/20"
                >
                  Retry Analysis
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
        >
          <HolographicStatsCard data={data} />
        </motion.div>
      )}

      {/* Empty State */}
      {!data && !loading && !error && (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
        >
          <Card className="text-center py-12 bg-black/40 border-gray-400/20">
            <div className="space-y-4">
              <div className="text-gray-400">
                No market analysis data available
              </div>
              {onRetry && (
                <Button 
                  variant="ghost" 
                  size="sm" 
                  onClick={onRetry}
                  className="text-gray-300 hover:text-white hover:bg-gray-500/20"
                >
                  Load Data
                </Button>
              )}
            </div>
          </Card>
        </motion.div>
      )}
    </motion.section>
  );
};