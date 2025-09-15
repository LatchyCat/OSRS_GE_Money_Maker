import React from 'react';
import { motion } from 'framer-motion';
import { RefreshCw, Plus } from 'lucide-react';
import { Button } from '../ui/Button';
import { useNavigate } from 'react-router-dom';

interface DashboardHeaderProps {
  onRefresh?: () => void;
  refreshing?: boolean;
  className?: string;
}

export const DashboardHeader: React.FC<DashboardHeaderProps> = ({
  onRefresh,
  refreshing = false,
  className = ''
}) => {
  const navigate = useNavigate();

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={`flex items-center justify-between ${className}`}
    >
      {/* Title Section */}
      <div>
        <motion.h1 
          className="text-3xl font-bold bg-gradient-to-r from-white via-cyan-200 to-blue-200 bg-clip-text text-transparent"
          animate={{ 
            textShadow: '0 0 20px rgba(6,182,212,0.3)'
          }}
        >
          Dashboard
        </motion.h1>
        <motion.p 
          className="text-gray-400 mt-2"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
        >
          Welcome to your OSRS High Alch profit tracking center
        </motion.p>
      </div>

      {/* Action Buttons */}
      <motion.div
        className="flex items-center space-x-4"
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: 0.1 }}
      >
        {/* Refresh Button */}
        <Button
          variant="secondary"
          onClick={onRefresh}
          loading={refreshing}
          icon={<RefreshCw className="w-4 h-4" />}
          className="bg-black/20 border-cyan-400/20 text-cyan-300 hover:bg-cyan-500/10 hover:border-cyan-400/40"
        >
          Refresh Data
        </Button>

        {/* New Goal Plan Button */}
        <Button
          variant="primary"
          onClick={() => navigate('/planning/create')}
          icon={<Plus className="w-4 h-4" />}
          className="bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700 shadow-lg shadow-cyan-400/30"
        >
          New Goal Plan
        </Button>
      </motion.div>
    </motion.div>
  );
};