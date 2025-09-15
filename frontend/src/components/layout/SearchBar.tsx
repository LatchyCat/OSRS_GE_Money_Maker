import React from 'react';
import { motion } from 'framer-motion';
import { SmartSearchBar } from '../ui/SmartSearchBar';

export const SearchBar: React.FC = () => {
  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-gray-800/50 backdrop-blur-sm border-b border-gray-700/50"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3">
        <div className="flex justify-center">
          <SmartSearchBar 
            className="w-full max-w-2xl" 
            placeholder="Search items, strategies, or market data..."
          />
        </div>
      </div>
    </motion.div>
  );
};