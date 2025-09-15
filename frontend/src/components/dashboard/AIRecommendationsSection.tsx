import React from 'react';
import { motion } from 'framer-motion';
import { AIRecommendationCard } from '../ai/AIRecommendationCard';

interface AIRecommendationsSectionProps {
  className?: string;
}

export const AIRecommendationsSection: React.FC<AIRecommendationsSectionProps> = ({
  className = ''
}) => {
  return (
    <motion.section
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.25 }}
      className={className}
    >
      {/* Section Header */}
      <div className="mb-6">
        <motion.h2
          className="text-xl font-semibold bg-gradient-to-r from-white via-purple-200 to-blue-200 bg-clip-text text-transparent"
          animate={{ 
            textShadow: '0 0 15px rgba(147,51,234,0.3)'
          }}
        >
          AI Trading Recommendations
        </motion.h2>
        <p className="text-gray-400 text-sm mt-1">
          Intelligent profit opportunities tailored to your capital and risk preferences
        </p>
      </div>

      {/* AI Recommendations Card */}
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 0.3 }}
      >
        <AIRecommendationCard />
      </motion.div>
    </motion.section>
  );
};