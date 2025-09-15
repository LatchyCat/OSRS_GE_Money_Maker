import React from 'react';
import { motion } from 'framer-motion';
import { AgentPerformanceCard } from '../ai/AgentPerformanceCard';

interface AgentPerformanceSectionProps {
  className?: string;
}

export const AgentPerformanceSection: React.FC<AgentPerformanceSectionProps> = ({
  className = ''
}) => {
  return (
    <motion.section
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.2 }}
      className={className}
    >
      {/* Section Header */}
      <div className="mb-6">
        <motion.h2
          className="text-xl font-semibold bg-gradient-to-r from-white via-purple-200 to-cyan-200 bg-clip-text text-transparent"
          animate={{ 
            textShadow: '0 0 15px rgba(147,51,234,0.3)'
          }}
        >
          Multi-Agent System
        </motion.h2>
        <p className="text-gray-400 text-sm mt-1">
          AI agents working together to optimize your trading strategies
        </p>
      </div>

      {/* Agent Performance Card */}
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 0.3 }}
      >
        <AgentPerformanceCard />
      </motion.div>
    </motion.section>
  );
};