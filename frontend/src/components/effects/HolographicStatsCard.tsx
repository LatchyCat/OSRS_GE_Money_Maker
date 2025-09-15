import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { TrendingUp, Package, Target, AlertTriangle, Activity, BarChart3 } from 'lucide-react';
import type { MarketAnalysis } from '../../types';

interface HolographicStatsCardProps {
  data: MarketAnalysis;
  loading?: boolean;
}

export const HolographicStatsCard: React.FC<HolographicStatsCardProps> = ({ data, loading }) => {
  const [isScrolling, setIsScrolling] = useState(false);
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });

  // Scroll detection for performance optimization
  useEffect(() => {
    const handleScroll = () => {
      setIsScrolling(true);
      
      const timeout = setTimeout(() => {
        setIsScrolling(false);
      }, 150);
      
      return () => clearTimeout(timeout);
    };

    const handleMouseMove = (event: MouseEvent) => {
      if (isScrolling) return;
      setMousePosition({
        x: (event.clientX / window.innerWidth) * 2 - 1,
        y: -(event.clientY / window.innerHeight) * 2 + 1
      });
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    window.addEventListener('mousemove', handleMouseMove, { passive: true });
    
    return () => {
      window.removeEventListener('scroll', handleScroll);
      window.removeEventListener('mousemove', handleMouseMove);
    };
  }, [isScrolling]);

  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {[...Array(4)].map((_, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.1 * i }}
            className="relative bg-black/40 backdrop-blur-xl border border-white/10 rounded-xl p-6 animate-pulse"
          >
            <div className="space-y-3">
              <div className="h-4 bg-white/20 rounded animate-hologram-shimmer" />
              <div className="h-8 bg-white/20 rounded" />
              <div className="h-3 bg-white/20 rounded w-2/3" />
            </div>
            
            {/* Loading scan lines */}
            <div className="absolute inset-0 overflow-hidden rounded-xl">
              <div className="absolute w-full h-0.5 bg-gradient-to-r from-transparent via-cyan-400/50 to-transparent animate-scan-line" />
            </div>
          </motion.div>
        ))}
      </div>
    );
  }

  const formatGP = (amount: number) => {
    if (amount >= 1000000) {
      return `${(amount / 1000000).toFixed(1)}M GP`;
    } else if (amount >= 1000) {
      return `${(amount / 1000).toFixed(1)}K GP`;
    }
    return `${amount} GP`;
  };

  const getRiskBadgeColor = (riskLevel: string) => {
    switch (riskLevel) {
      case 'conservative':
        return 'text-emerald-400 shadow-emerald-400/50';
      case 'moderate':
        return 'text-yellow-400 shadow-yellow-400/50';
      case 'aggressive':
        return 'text-red-400 shadow-red-400/50';
      default:
        return 'text-gray-400 shadow-gray-400/50';
    }
  };

  const statsCards = [
    {
      icon: TrendingUp,
      title: "Average Profit",
      value: formatGP(data.average_profit),
      subtitle: "Per item opportunity",
      color: "emerald",
      glow: "shadow-emerald-400/25",
      border: "border-emerald-400/30 hover:border-emerald-400/60"
    },
    {
      icon: Package,
      title: "Top Opportunities",
      value: data.top_opportunities?.toString() || "0",
      subtitle: "High-value items",
      color: "blue",
      glow: "shadow-blue-400/25", 
      border: "border-blue-400/30 hover:border-blue-400/60"
    },
    {
      icon: Target,
      title: "Success Rate",
      value: `${data.success_rate || 85}%`,
      subtitle: "Profit predictions",
      color: "purple",
      glow: "shadow-purple-400/25",
      border: "border-purple-400/30 hover:border-purple-400/60"
    },
    {
      icon: AlertTriangle,
      title: "Risk Level",
      value: data.market_risk_level || "Moderate",
      subtitle: "Current market",
      color: "yellow",
      glow: "shadow-yellow-400/25",
      border: "border-yellow-400/30 hover:border-yellow-400/60"
    }
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      {statsCards.map((stat, index) => {
        const IconComponent = stat.icon;
        
        return (
          <motion.div
            key={stat.title}
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
                : `perspective(800px) rotateX(${mousePosition.y * 2}deg) rotateY(${mousePosition.x * 2}deg)`,
              transformStyle: 'preserve-3d',
            }}
            className="group cursor-pointer"
          >
            {/* Main Card Container */}
            <div className={`relative bg-black/40 backdrop-blur-xl border ${stat.border} rounded-xl overflow-hidden shadow-2xl ${stat.glow} transition-all duration-500 hover:animate-hologram-glow h-full`}>
              
              {/* Holographic Shimmer Effect */}
              <div 
                className="absolute inset-0 opacity-0 group-hover:opacity-30 transition-opacity duration-700"
                style={{
                  background: `linear-gradient(135deg, transparent 0%, rgba(0,255,255,0.1) 45%, rgba(255,255,255,0.4) 50%, rgba(0,255,255,0.1) 55%, transparent 100%)`,
                  transform: 'translateX(-100%) skewX(-15deg)',
                  animation: 'hologramShimmer 3s ease-in-out infinite'
                }}
              />
              
              {/* Animated Border Glow */}
              <div className="absolute inset-0 rounded-xl bg-gradient-to-r from-transparent via-cyan-400/30 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 animate-hologram-shimmer" />
              
              {/* Scan Line Effect */}
              <div className="absolute inset-0 overflow-hidden rounded-xl">
                <div 
                  className="absolute w-full h-0.5 bg-gradient-to-r from-transparent via-cyan-400 to-transparent opacity-0 group-hover:opacity-60"
                  style={{ 
                    filter: 'blur(0.3px)',
                    boxShadow: '0 0 8px rgba(0,255,255,0.8)',
                    animation: 'scanLine 4s linear infinite'
                  }}
                />
              </div>

              {/* Card Content */}
              <div className="relative z-10 p-6">
                
                {/* Header with Icon */}
                <div className="flex items-center justify-between mb-4">
                  <motion.div
                    animate={{ 
                      rotate: [0, 360],
                      scale: [1, 1.1, 1]
                    }}
                    transition={{ 
                      duration: 2,
                      repeat: Infinity,
                      ease: "easeInOut"
                    }}
                  >
                    <IconComponent className={`w-6 h-6 text-${stat.color}-400 drop-shadow-lg`} />
                  </motion.div>
                  
                  <div className="w-2 h-2 bg-cyan-400 rounded-full animate-pulse shadow-lg shadow-cyan-400/75" />
                </div>

                {/* Title */}
                <motion.h3 
                  className="text-sm font-medium text-gray-300 mb-2"
                  animate={{ 
                    textShadow: '0 0 8px rgba(0,255,255,0.3)'
                  }}
                >
                  {stat.title}
                </motion.h3>

                {/* Main Value */}
                <motion.div 
                  className={`text-2xl font-bold text-${stat.color}-400 mb-2 drop-shadow-lg`}
                  animate={{ 
                    textShadow: `0 0 15px rgba(${stat.color === 'emerald' ? '16,185,129' : stat.color === 'blue' ? '59,130,246' : stat.color === 'purple' ? '147,51,234' : '251,191,36'},0.6)`
                  }}
                >
                  {stat.value}
                </motion.div>

                {/* Subtitle */}
                <p className="text-xs text-gray-400">
                  {stat.subtitle}
                </p>

                {/* Data Quality Indicator */}
                <div className="mt-3 flex items-center justify-between">
                  <div className="flex items-center space-x-1">
                    <Activity className="w-3 h-3 text-cyan-400" />
                    <span className="text-xs text-cyan-300">Live Data</span>
                  </div>
                  
                  {/* Holographic Progress Bar */}
                  <div className="w-16 h-1 bg-black/50 rounded-full overflow-hidden">
                    <motion.div
                      className={`h-full bg-${stat.color}-400 shadow-lg`}
                      initial={{ width: 0 }}
                      animate={{ width: '85%' }}
                      transition={{ duration: 1.5, delay: 0.3 * index }}
                    />
                  </div>
                </div>
              </div>

              {/* Corner Accent Lights */}
              <div className="absolute top-2 right-2 w-1.5 h-1.5 bg-cyan-400 rounded-full opacity-50 group-hover:opacity-100 transition-opacity duration-300 shadow-lg shadow-cyan-400/75" />
              <div className="absolute bottom-2 left-2 w-1.5 h-1.5 bg-purple-400 rounded-full opacity-50 group-hover:opacity-100 transition-opacity duration-300 shadow-lg shadow-purple-400/75" />
            </div>
          </motion.div>
        );
      })}
    </div>
  );
};