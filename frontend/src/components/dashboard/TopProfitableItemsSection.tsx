import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { HolographicItemCard } from '../effects/HolographicItemCard';
import { HolographicLoader } from '../effects/HolographicLoader';
import { Pagination } from '../ui/Pagination';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import type { Item } from '../../types';

interface TopProfitableItemsSectionProps {
  items: Item[];
  loading?: boolean;
  error?: string | null;
  onRetry?: () => void;
  itemsPerPage?: number;
  className?: string;
}

export const TopProfitableItemsSection: React.FC<TopProfitableItemsSectionProps> = ({
  items,
  loading = false,
  error = null,
  onRetry,
  itemsPerPage = 8,
  className = ''
}) => {
  const navigate = useNavigate();
  const [currentPage, setCurrentPage] = useState(1);

  // Calculate pagination
  const totalPages = Math.ceil(items.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const currentItems = items.slice(startIndex, startIndex + itemsPerPage);

  // Reset to first page when items change
  React.useEffect(() => {
    setCurrentPage(1);
  }, [items.length]);

  return (
    <motion.section
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.35 }}
      className={`space-y-6 ${className}`}
    >
      {/* Section Header */}
      <div className="flex items-center justify-between">
        <div>
          <motion.h2
            className="text-xl font-semibold bg-gradient-to-r from-white via-emerald-200 to-yellow-200 bg-clip-text text-transparent"
            animate={{ 
              textShadow: '0 0 15px rgba(16,185,129,0.3)'
            }}
          >
            Top Profitable Items
          </motion.h2>
          <p className="text-gray-400 text-sm mt-1">
            Highest profit opportunities right now {items.length > 0 && `(${items.length} total)`}
          </p>
        </div>
        <div className="flex items-center space-x-3">
          {/* Items per page indicator */}
          {items.length > itemsPerPage && (
            <div className="text-sm text-gray-400">
              Showing {currentItems.length} of {items.length}
            </div>
          )}
          <Button 
            variant="ghost" 
            size="sm"
            onClick={() => navigate('/items')}
            className="text-emerald-300 hover:text-white hover:bg-emerald-500/20"
          >
            View All Items
          </Button>
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <Card className="text-center py-12 bg-black/40 border-emerald-400/30">
          <HolographicLoader 
            size="lg" 
            text="Scanning profitable opportunities..." 
            variant="market" 
          />
        </Card>
      )}
      
      {/* Error State */}
      {error && (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
        >
          <Card className="text-center py-12 bg-black/40 border-red-400/30">
            <div className="space-y-4">
              <div className="text-red-400 mb-4">⚠️ {error}</div>
              {onRetry && (
                <Button 
                  variant="primary" 
                  onClick={onRetry}
                  className="bg-red-500 hover:bg-red-600"
                >
                  Retry Loading Items
                </Button>
              )}
            </div>
          </Card>
        </motion.div>
      )}
      
      {/* Items Grid */}
      {!loading && !error && currentItems.length > 0 && (
        <div className="space-y-6">
          {/* Items Grid with synchronized heights */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
            <AnimatePresence>
              {currentItems.map((item, index) => (
                <motion.div
                  key={`${item.item_id}-${currentPage}`} // Include page in key to trigger animation
                  initial={{ opacity: 0, scale: 0.9, y: 20 }}
                  animate={{ opacity: 1, scale: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.9, y: -20 }}
                  transition={{ 
                    delay: 0.1 * (index % itemsPerPage),
                    type: "spring",
                    stiffness: 100,
                    damping: 15
                  }}
                  className="h-full" // Ensure consistent height container
                >
                  <div className="h-full"> {/* Inner container for full height */}
                    <HolographicItemCard 
                      item={item} 
                      index={index}
                      onClick={() => navigate(`/items/${item.item_id}`)}
                    />
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>

          {/* Pagination Controls */}
          {totalPages > 1 && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5 }}
              className="flex justify-center"
            >
              <Pagination
                currentPage={currentPage}
                totalPages={totalPages}
                onPageChange={setCurrentPage}
                variant="holographic"
                className="mt-6"
              />
            </motion.div>
          )}
        </div>
      )}
      
      {/* Empty State */}
      {!loading && !error && items.length === 0 && (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
        >
          <Card className="text-center py-12 bg-black/40 border-gray-400/20">
            <div className="space-y-4">
              <div className="text-gray-400 text-lg">
                No profitable items found
              </div>
              <p className="text-gray-500 text-sm">
                Try refreshing the data or adjusting your filters
              </p>
              {onRetry && (
                <Button 
                  variant="ghost" 
                  size="sm" 
                  onClick={onRetry}
                  className="text-gray-300 hover:text-white hover:bg-gray-500/20"
                >
                  Refresh Items
                </Button>
              )}
            </div>
          </Card>
        </motion.div>
      )}
    </motion.section>
  );
};