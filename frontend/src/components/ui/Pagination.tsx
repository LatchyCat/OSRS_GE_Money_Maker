import React from 'react';
import { motion } from 'framer-motion';
import { ChevronLeft, ChevronRight, MoreHorizontal } from 'lucide-react';
import { Button } from './Button';

interface PaginationProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  showFirstLast?: boolean;
  maxVisiblePages?: number;
  className?: string;
  variant?: 'default' | 'holographic';
}

export const Pagination: React.FC<PaginationProps> = ({
  currentPage,
  totalPages,
  onPageChange,
  showFirstLast = true,
  maxVisiblePages = 5,
  className = '',
  variant = 'default'
}) => {
  if (totalPages <= 1) return null;

  const getVisiblePages = () => {
    const pages: (number | string)[] = [];
    
    if (totalPages <= maxVisiblePages) {
      // Show all pages if total is less than max visible
      for (let i = 1; i <= totalPages; i++) {
        pages.push(i);
      }
    } else {
      // Calculate start and end pages
      let start = Math.max(1, currentPage - Math.floor(maxVisiblePages / 2));
      let end = Math.min(totalPages, start + maxVisiblePages - 1);
      
      // Adjust start if we're near the end
      if (end - start < maxVisiblePages - 1) {
        start = Math.max(1, end - maxVisiblePages + 1);
      }
      
      // Add first page and ellipsis if needed
      if (start > 1) {
        pages.push(1);
        if (start > 2) {
          pages.push('...');
        }
      }
      
      // Add visible pages
      for (let i = start; i <= end; i++) {
        pages.push(i);
      }
      
      // Add ellipsis and last page if needed
      if (end < totalPages) {
        if (end < totalPages - 1) {
          pages.push('...');
        }
        pages.push(totalPages);
      }
    }
    
    return pages;
  };

  const visiblePages = getVisiblePages();

  const getPageButtonClasses = (isActive: boolean) => {
    if (variant === 'holographic') {
      return isActive
        ? 'bg-cyan-500/20 border-cyan-400/60 text-cyan-300 shadow-lg shadow-cyan-400/50'
        : 'bg-black/20 border-cyan-400/20 text-gray-300 hover:bg-cyan-500/10 hover:border-cyan-400/40 hover:text-cyan-300';
    }
    return isActive
      ? 'bg-blue-500 border-blue-400 text-white'
      : 'bg-white/10 border-white/20 text-gray-300 hover:bg-white/20 hover:text-white';
  };

  const getNavigationButtonClasses = () => {
    if (variant === 'holographic') {
      return 'bg-black/20 border-cyan-400/20 text-cyan-300 hover:bg-cyan-500/10 hover:border-cyan-400/40 disabled:opacity-50 disabled:cursor-not-allowed';
    }
    return 'bg-white/10 border-white/20 text-gray-300 hover:bg-white/20 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed';
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`flex items-center justify-center space-x-2 ${className}`}
    >
      {/* First Page Button */}
      {showFirstLast && currentPage > 1 && (
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onPageChange(1)}
          className={getNavigationButtonClasses()}
          title="First page"
        >
          1
        </Button>
      )}

      {/* Previous Button */}
      <Button
        variant="ghost"
        size="sm"
        onClick={() => onPageChange(Math.max(1, currentPage - 1))}
        disabled={currentPage === 1}
        className={getNavigationButtonClasses()}
        icon={<ChevronLeft className="w-4 h-4" />}
        title="Previous page"
      />

      {/* Page Numbers */}
      <div className="flex items-center space-x-1">
        {visiblePages.map((page, index) => {
          if (page === '...') {
            return (
              <div
                key={`ellipsis-${index}`}
                className="px-2 py-1 text-gray-400"
              >
                <MoreHorizontal className="w-4 h-4" />
              </div>
            );
          }

          const pageNum = page as number;
          const isActive = pageNum === currentPage;

          return (
            <motion.button
              key={pageNum}
              onClick={() => onPageChange(pageNum)}
              className={`
                relative px-3 py-1.5 text-sm font-medium rounded-lg border transition-all duration-200
                ${getPageButtonClasses(isActive)}
              `}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              {/* Holographic effects for active page */}
              {variant === 'holographic' && isActive && (
                <>
                  <div 
                    className="absolute inset-0 opacity-30 transition-opacity duration-700 rounded-lg"
                    style={{
                      background: `linear-gradient(135deg, transparent 0%, rgba(6,182,212,0.1) 45%, rgba(255,255,255,0.4) 50%, rgba(6,182,212,0.1) 55%, transparent 100%)`,
                      transform: 'translateX(-100%) skewX(-15deg)',
                      animation: 'hologramShimmer 3s ease-in-out infinite'
                    }}
                  />
                  <div className="absolute top-0.5 right-0.5 w-1 h-1 bg-cyan-400 rounded-full animate-pulse" />
                </>
              )}
              
              <span className="relative z-10">{pageNum}</span>
            </motion.button>
          );
        })}
      </div>

      {/* Next Button */}
      <Button
        variant="ghost"
        size="sm"
        onClick={() => onPageChange(Math.min(totalPages, currentPage + 1))}
        disabled={currentPage === totalPages}
        className={getNavigationButtonClasses()}
        icon={<ChevronRight className="w-4 h-4" />}
        title="Next page"
      />

      {/* Last Page Button */}
      {showFirstLast && currentPage < totalPages && (
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onPageChange(totalPages)}
          className={getNavigationButtonClasses()}
          title="Last page"
        >
          {totalPages}
        </Button>
      )}

      {/* Page Info */}
      <div className={`ml-4 text-sm ${variant === 'holographic' ? 'text-cyan-300' : 'text-gray-400'}`}>
        Page {currentPage} of {totalPages}
      </div>
    </motion.div>
  );
};