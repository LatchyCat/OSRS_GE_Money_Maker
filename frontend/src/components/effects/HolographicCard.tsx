import React, { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Clock, Shield, TrendingUp } from 'lucide-react';
import type { AIRecommendation } from '../../types/aiTypes';

interface HolographicCardProps {
  recommendation: AIRecommendation;
  index: number;
  formatGP: (amount: number) => string;
}

export const HolographicCard: React.FC<HolographicCardProps> = ({ 
  recommendation, 
  index, 
  formatGP 
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
    if (!cardRef.current || isScrolling) return; // Skip during scrolling
    
    const rect = cardRef.current.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;
    
    const rotateX = (event.clientY - centerY) / 10;
    const rotateY = (centerX - event.clientX) / 10;
    
    setMousePosition({ x: rotateY, y: rotateX });
  };

  const handleMouseLeave = () => {
    setMousePosition({ x: 0, y: 0 });
    setIsHovered(false);
  };

  const handleMouseEnter = () => {
    setIsHovered(true);
  };

  // Calculate dynamic colors based on profit levels
  const profitMargin = recommendation.expected_profit_margin_pct;

  const getRiskIndicatorColor = () => {
    switch (recommendation.risk_level) {
      case 'low': return 'text-emerald-400 shadow-emerald-400/50';
      case 'medium': return 'text-yellow-400 shadow-yellow-400/50';
      case 'high': return 'text-red-400 shadow-red-400/50';
      default: return 'text-gray-400 shadow-gray-400/50';
    }
  };

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
          ? 'perspective(1000px) rotateX(0deg) rotateY(0deg)' // Disable 3D during scroll
          : `perspective(1000px) rotateX(${mousePosition.y}deg) rotateY(${mousePosition.x}deg)`,
        transformStyle: 'preserve-3d',
        willChange: isScrolling ? 'auto' : 'transform',
      }}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      onMouseEnter={handleMouseEnter}
      className="group cursor-pointer animate-float"
    >
      {/* Main Card Container */}
      <div className="relative bg-black/40 backdrop-blur-xl border border-white/10 rounded-2xl overflow-hidden shadow-2xl transition-all duration-500 hover:shadow-cyan-500/25 hover:animate-hologram-glow">
        
        {/* Holographic Shimmer Effect */}
        <div 
          className={`absolute inset-0 opacity-0 group-hover:opacity-30 transition-opacity duration-700`}
          style={{
            background: `linear-gradient(135deg, transparent 0%, rgba(0,255,255,0.1) 45%, rgba(255,255,255,0.4) 50%, rgba(0,255,255,0.1) 55%, transparent 100%)`,
            transform: isHovered ? 'translateX(0%) skewX(-20deg)' : 'translateX(-100%) skewX(-20deg)',
            transition: 'transform 0.8s ease-in-out'
          }}
        />
        
        {/* Animated Border Glow */}
        <div className="absolute inset-0 rounded-2xl bg-gradient-to-r from-transparent via-cyan-400/30 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 animate-hologram-shimmer" />
        
        {/* Scan Line Effect */}
        <div className="absolute inset-0 overflow-hidden rounded-2xl">
          <div 
            className="absolute w-full h-0.5 bg-gradient-to-r from-transparent via-cyan-400 to-transparent opacity-0 group-hover:opacity-70 group-hover:animate-scan-line"
            style={{ 
              filter: 'blur(0.5px)',
              boxShadow: '0 0 10px rgba(0,255,255,0.8)'
            }}
          />
        </div>
        
        {/* Card Content */}
        <div className="relative z-10 p-6 transform transition-transform duration-300 group-hover:translate-z-4">
          
          {/* Header with Holographic Title */}
          <div className="flex justify-between items-start mb-6">
            <div className="flex-1 min-w-0">
              <motion.h3 
                className="font-bold text-white text-xl truncate bg-gradient-to-r from-white via-cyan-200 to-blue-200 bg-clip-text text-transparent"
                animate={{ 
                  textShadow: isHovered ? '0 0 20px rgba(0,255,255,0.5)' : '0 0 0px rgba(0,255,255,0)'
                }}
                transition={{ duration: 0.3 }}
              >
                {recommendation.item_name}
              </motion.h3>
              <p className="text-gray-400 text-sm font-mono">#{recommendation.item_id}</p>
            </div>
            <div className="flex items-center space-x-3 ml-4">
              <motion.div
                animate={{ 
                  rotate: isHovered ? 360 : 0,
                  scale: isHovered ? 1.1 : 1
                }}
                transition={{ duration: 0.5 }}
              >
                <Shield className={`w-5 h-5 ${getRiskIndicatorColor()} drop-shadow-lg`} />
              </motion.div>
              <div className="text-right">
                <div className="text-xs text-gray-400 uppercase tracking-wider">Success</div>
                <motion.div 
                  className="text-lg font-bold text-emerald-300 drop-shadow-lg"
                  animate={{ 
                    textShadow: isHovered ? '0 0 15px rgba(16,185,129,0.6)' : '0 0 0px rgba(16,185,129,0)'
                  }}
                >
                  {recommendation.success_probability_pct}%
                </motion.div>
              </div>
            </div>
          </div>

          {/* Holographic Price Display Grid */}
          <div className="grid grid-cols-3 gap-4 mb-6">
            {[
              { label: 'Current', value: formatGP(recommendation.current_price), color: 'text-white' },
              { label: 'Buy At', value: formatGP(recommendation.recommended_buy_price), color: 'text-blue-300' },
              { label: 'Sell At', value: formatGP(recommendation.recommended_sell_price), color: 'text-emerald-300' }
            ].map((price) => (
              <motion.div 
                key={price.label}
                className="text-center p-3 rounded-xl bg-white/5 backdrop-blur-sm border border-white/10 hover:border-cyan-400/30 transition-all duration-300"
                whileHover={{ scale: 1.05, y: -2 }}
                style={{ transformStyle: 'preserve-3d' }}
              >
                <div className="text-xs text-gray-400 uppercase tracking-wider mb-1">{price.label}</div>
                <div className={`font-bold ${price.color} drop-shadow-sm`}>{price.value}</div>
              </motion.div>
            ))}
          </div>

          {/* Profit Metrics with Animated Progress Bars */}
          <div className="bg-black/30 backdrop-blur-sm rounded-xl p-4 mb-4 border border-white/5">
            <div className="space-y-4">
              {/* Profit per Item */}
              <div className="flex justify-between items-center">
                <span className="text-gray-400 text-sm">Profit per Item:</span>
                <motion.span 
                  className="font-bold text-emerald-300 text-lg drop-shadow-lg"
                  animate={{ 
                    textShadow: isHovered ? '0 0 10px rgba(16,185,129,0.8)' : '0 0 0px rgba(16,185,129,0)'
                  }}
                >
                  +{formatGP(recommendation.expected_profit_per_item)}
                </motion.span>
              </div>
              
              {/* Profit Margin with Animated Bar */}
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-gray-400 text-sm">Profit Margin:</span>
                  <span className="font-semibold text-emerald-300">{recommendation.expected_profit_margin_pct.toFixed(1)}%</span>
                </div>
                <div className="h-2 bg-black/50 rounded-full overflow-hidden">
                  <motion.div
                    className="h-full bg-gradient-to-r from-emerald-400 via-cyan-400 to-blue-400 shadow-lg shadow-emerald-400/50"
                    initial={{ width: 0 }}
                    animate={{ width: `${Math.min(recommendation.expected_profit_margin_pct * 4, 100)}%` }}
                    transition={{ duration: 1, delay: 0.2 * index }}
                  />
                </div>
              </div>
              
              {/* Hold Time with Icon */}
              <div className="flex justify-between items-center">
                <div className="flex items-center space-x-2">
                  <Clock className="w-4 h-4 text-blue-400" />
                  <span className="text-gray-400 text-sm">Hold Time:</span>
                </div>
                <span className="text-blue-300 font-medium">{recommendation.estimated_hold_time_hours.toFixed(1)}h</span>
              </div>
              
              {/* Buy Limit */}
              <div className="flex justify-between items-center">
                <span className="text-gray-400 text-sm">Buy Limit:</span>
                <span className="font-semibold text-orange-300">
                  {recommendation.buy_limit ? recommendation.buy_limit.toLocaleString() : 'N/A'}/4hr
                </span>
              </div>
            </div>
          </div>

          {/* Risk Assessment Footer */}
          <div className="flex items-center justify-between pt-2 border-t border-white/10">
            <div className="flex items-center space-x-2">
              <div className={`w-3 h-3 rounded-full ${
                recommendation.risk_level === 'low' ? 'bg-emerald-400 shadow-emerald-400/50' : 
                recommendation.risk_level === 'medium' ? 'bg-yellow-400 shadow-yellow-400/50' : 
                'bg-red-400 shadow-red-400/50'
              } shadow-lg`} />
              <span className="text-sm text-gray-300 capitalize font-medium">
                {recommendation.risk_level} Risk
              </span>
            </div>
            <motion.div 
              className="flex items-center space-x-1 text-cyan-400"
              animate={{ x: isHovered ? 5 : 0 }}
              transition={{ type: "spring", stiffness: 400 }}
            >
              <TrendingUp className="w-4 h-4" />
              <span className="text-sm font-medium">Opportunity</span>
            </motion.div>
          </div>
        </div>

        {/* Corner Accent Lights */}
        <div className="absolute top-2 right-2 w-2 h-2 bg-cyan-400 rounded-full opacity-50 group-hover:opacity-100 transition-opacity duration-300 shadow-lg shadow-cyan-400/75" />
        <div className="absolute bottom-2 left-2 w-2 h-2 bg-purple-400 rounded-full opacity-50 group-hover:opacity-100 transition-opacity duration-300 shadow-lg shadow-purple-400/75" />
      </div>
    </motion.div>
  );
};