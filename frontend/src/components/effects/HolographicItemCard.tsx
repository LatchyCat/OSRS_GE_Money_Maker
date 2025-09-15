import React, { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { TrendingUp, TrendingDown, Crown, Clock, Shield, Zap, Star } from 'lucide-react';
import type { Item } from '../../types';

interface HolographicItemCardProps {
  item: Item;
  index: number;
  onClick?: () => void;
}

export const HolographicItemCard: React.FC<HolographicItemCardProps> = ({ 
  item, 
  index, 
  onClick 
}) => {
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });
  const [isHovered, setIsHovered] = useState(false);
  const [isScrolling, setIsScrolling] = useState(false);
  const cardRef = useRef<HTMLDivElement>(null);
  const scrollTimeoutRef = useRef<NodeJS.Timeout>();

  // Scroll detection for performance optimization
  useEffect(() => {
    const handleScroll = () => {
      setIsScrolling(true);
      
      if (scrollTimeoutRef.current) {
        clearTimeout(scrollTimeoutRef.current);
      }
      
      scrollTimeoutRef.current = setTimeout(() => {
        setIsScrolling(false);
      }, 150);
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => {
      window.removeEventListener('scroll', handleScroll);
      if (scrollTimeoutRef.current) {
        clearTimeout(scrollTimeoutRef.current);
      }
    };
  }, []);

  const handleMouseMove = (event: React.MouseEvent<HTMLDivElement>) => {
    if (!cardRef.current || isScrolling) return;
    
    const rect = cardRef.current.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;
    
    const rotateX = (event.clientY - centerY) / 15;
    const rotateY = (centerX - event.clientX) / 15;
    
    setMousePosition({ x: rotateY, y: rotateX });
  };

  const handleMouseLeave = () => {
    setMousePosition({ x: 0, y: 0 });
    setIsHovered(false);
  };

  const handleMouseEnter = () => {
    setIsHovered(true);
  };

  // Utility functions for safe data access
  const formatGP = (amount: number | null | undefined) => {
    if (amount == null || isNaN(Number(amount))) {
      return '0';
    }
    
    const num = Number(amount);
    if (num >= 1000000) {
      return `${(num / 1000000).toFixed(1)}M`;
    } else if (num >= 1000) {
      return `${(num / 1000).toFixed(1)}K`;
    }
    return num.toString();
  };

  const getCurrentProfit = () => {
    return item.profit_calc?.current_profit ?? item.current_profit ?? 0;
  };

  const getCurrentProfitMargin = () => {
    return item.profit_calc?.current_profit_margin ?? item.current_profit_margin ?? 0;
  };

  const getRecommendationScore = () => {
    return item.profit_calc?.recommendation_score ?? item.recommendation_score ?? 0;
  };

  // Dynamic color schemes based on profit
  const profit = getCurrentProfit();
  const profitMargin = getCurrentProfitMargin();

  const getHologramColors = () => {
    if (profit > 30000) return {
      border: 'border-emerald-400/30 hover:border-emerald-400/60',
      glow: 'shadow-emerald-400/25',
      text: 'text-emerald-300',
      gradient: 'from-emerald-400/20 via-cyan-400/20 to-blue-400/20'
    };
    if (profit > 15000) return {
      border: 'border-yellow-400/30 hover:border-yellow-400/60',
      glow: 'shadow-yellow-400/25',
      text: 'text-yellow-300',
      gradient: 'from-yellow-400/20 via-orange-400/20 to-red-400/20'
    };
    return {
      border: 'border-purple-400/30 hover:border-purple-400/60',
      glow: 'shadow-purple-400/25',
      text: 'text-purple-300',
      gradient: 'from-purple-400/20 via-pink-400/20 to-indigo-400/20'
    };
  };

  const colors = getHologramColors();

  return (
    <motion.div
      ref={cardRef}
      initial={{ opacity: 0, scale: 0.9, rotateY: -15 }}
      animate={{ opacity: 1, scale: 1, rotateY: 0 }}
      transition={{ 
        delay: 0.1 * index,
        type: "spring",
        stiffness: 100,
        damping: 15
      }}
      style={{
        transform: isScrolling 
          ? 'perspective(800px) rotateX(0deg) rotateY(0deg)'
          : `perspective(800px) rotateX(${mousePosition.y}deg) rotateY(${mousePosition.x}deg)`,
        transformStyle: 'preserve-3d',
        willChange: isScrolling ? 'auto' : 'transform',
      }}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      onMouseEnter={handleMouseEnter}
      onClick={onClick}
      className="group cursor-pointer"
    >
      {/* Main Card Container */}
      <div className={`relative bg-black/40 backdrop-blur-xl border ${colors.border} rounded-xl overflow-hidden shadow-2xl ${colors.glow} transition-all duration-500 hover:animate-hologram-glow h-full`}>
        
        {/* Holographic Shimmer Effect */}
        <div 
          className="absolute inset-0 opacity-0 group-hover:opacity-30 transition-opacity duration-700"
          style={{
            background: `linear-gradient(135deg, transparent 0%, rgba(0,255,255,0.1) 45%, rgba(255,255,255,0.4) 50%, rgba(0,255,255,0.1) 55%, transparent 100%)`,
            transform: isHovered ? 'translateX(0%) skewX(-15deg)' : 'translateX(-100%) skewX(-15deg)',
            transition: 'transform 0.8s ease-in-out'
          }}
        />
        
        {/* Animated Border Glow */}
        <div className="absolute inset-0 rounded-xl bg-gradient-to-r from-transparent via-cyan-400/30 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 animate-hologram-shimmer" />
        
        {/* Scan Line Effect */}
        <div className="absolute inset-0 overflow-hidden rounded-xl">
          <div 
            className="absolute w-full h-0.5 bg-gradient-to-r from-transparent via-cyan-400 to-transparent opacity-0 group-hover:opacity-60 group-hover:animate-scan-line"
            style={{ 
              filter: 'blur(0.3px)',
              boxShadow: '0 0 8px rgba(0,255,255,0.8)'
            }}
          />
        </div>

        {/* Card Content */}
        <div className="relative z-10 p-4 h-full flex flex-col">
          
          {/* Header with Item Name */}
          <div className="flex justify-between items-start mb-3">
            <div className="flex-1 min-w-0">
              <motion.h3 
                className="font-bold text-white text-sm truncate bg-gradient-to-r from-white via-cyan-200 to-blue-200 bg-clip-text text-transparent"
                animate={{ 
                  textShadow: isHovered ? '0 0 15px rgba(0,255,255,0.5)' : '0 0 0px rgba(0,255,255,0)'
                }}
                transition={{ duration: 0.3 }}
              >
                {item.name}
              </motion.h3>
              <p className="text-gray-400 text-xs font-mono">#{item.item_id}</p>
            </div>
            
            {/* Recommendation Score */}
            <motion.div
              animate={{ 
                rotate: isHovered ? 360 : 0,
                scale: isHovered ? 1.1 : 1
              }}
              transition={{ duration: 0.5 }}
              className="flex items-center space-x-1"
            >
              <Star className={`w-4 h-4 ${colors.text} drop-shadow-lg`} />
              <span className="text-xs font-bold text-cyan-300">
                {Math.round(getRecommendationScore())}
              </span>
            </motion.div>
          </div>

          {/* Profit Display with Animated Progress */}
          <div className="mb-3 flex-1">
            <div className="flex justify-between items-center mb-2">
              <span className="text-gray-400 text-xs">Profit:</span>
              <motion.span 
                className={`font-bold text-sm ${colors.text} drop-shadow-lg`}
                animate={{ 
                  textShadow: isHovered ? '0 0 10px rgba(16,185,129,0.8)' : '0 0 0px rgba(16,185,129,0)'
                }}
              >
                +{formatGP(profit)} GP
              </motion.span>
            </div>
            
            {/* Profit Margin Progress Bar */}
            <div className="space-y-1">
              <div className="flex justify-between items-center">
                <span className="text-gray-400 text-xs">Margin:</span>
                <span className={`text-xs ${colors.text}`}>{profitMargin.toFixed(1)}%</span>
              </div>
              <div className="h-1.5 bg-black/50 rounded-full overflow-hidden">
                <motion.div
                  className={`h-full bg-gradient-to-r ${colors.gradient} shadow-lg ${colors.glow}`}
                  initial={{ width: 0 }}
                  animate={{ width: `${Math.min(profitMargin * 2, 100)}%` }}
                  transition={{ duration: 1, delay: 0.2 * index }}
                />
              </div>
            </div>
          </div>

          {/* Additional Metrics */}
          <div className="grid grid-cols-2 gap-2 mb-3 text-xs">
            <div className="flex items-center space-x-1">
              <TrendingUp className="w-3 h-3 text-green-400" />
              <span className="text-gray-300">
                {formatGP(item.current_buy_price || 0)}
              </span>
            </div>
            <div className="flex items-center space-x-1">
              <Clock className="w-3 h-3 text-blue-400" />
              <span className="text-gray-300">
                {item.data_source || 'Live'}
              </span>
            </div>
          </div>

          {/* Footer with High Alch Status */}
          <div className="flex items-center justify-between pt-2 border-t border-white/10">
            <div className="flex items-center space-x-1">
              <div className={`w-2 h-2 rounded-full ${
                profit > 20000 ? 'bg-emerald-400 shadow-emerald-400/50' : 
                profit > 10000 ? 'bg-yellow-400 shadow-yellow-400/50' : 
                'bg-purple-400 shadow-purple-400/50'
              } shadow-lg`} />
              <span className="text-xs text-gray-300 font-medium">
                {profit > 20000 ? 'High' : profit > 10000 ? 'Medium' : 'Low'} Profit
              </span>
            </div>
            <motion.div 
              className="flex items-center space-x-1 text-cyan-400"
              animate={{ x: isHovered ? 3 : 0 }}
              transition={{ type: "spring", stiffness: 400 }}
            >
              <Zap className="w-3 h-3" />
              <span className="text-xs font-medium">Alch</span>
            </motion.div>
          </div>
        </div>

        {/* Corner Accent Lights */}
        <div className="absolute top-2 right-2 w-1.5 h-1.5 bg-cyan-400 rounded-full opacity-50 group-hover:opacity-100 transition-opacity duration-300 shadow-lg shadow-cyan-400/75" />
        <div className="absolute bottom-2 left-2 w-1.5 h-1.5 bg-purple-400 rounded-full opacity-50 group-hover:opacity-100 transition-opacity duration-300 shadow-lg shadow-purple-400/75" />
      </div>
    </motion.div>
  );
};