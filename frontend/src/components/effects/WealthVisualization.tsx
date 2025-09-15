import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { TrendingUp, Coins, DollarSign } from 'lucide-react';

interface WealthParticle {
  id: number;
  value: number;
  x: number;
  y: number;
  delay: number;
  color: string;
}

interface WealthVisualizationProps {
  totalValue: number;
  recentProfit: number;
  className?: string;
  intensity?: number; // 0-1 for how many particles to show
}

export const WealthVisualization: React.FC<WealthVisualizationProps> = ({
  totalValue,
  recentProfit,
  className = '',
  intensity = 0.5
}) => {
  const [particles, setParticles] = useState<WealthParticle[]>([]);
  const [isActive, setIsActive] = useState(false);

  const formatGP = (amount: number): string => {
    if (amount >= 1000000) {
      return `${(amount / 1000000).toFixed(1)}M GP`;
    } else if (amount >= 1000) {
      return `${(amount / 1000).toFixed(1)}K GP`;
    }
    return `${amount} GP`;
  };

  const generateParticles = () => {
    const particleCount = Math.max(3, Math.floor(intensity * 8));
    const newParticles: WealthParticle[] = [];
    
    for (let i = 0; i < particleCount; i++) {
      const profit = Math.floor(Math.random() * (recentProfit / particleCount) + 1000);
      newParticles.push({
        id: Date.now() + i,
        value: profit,
        x: Math.random() * 100,
        y: 100 + Math.random() * 20,
        delay: i * 0.3,
        color: profit > 50000 ? 'emerald' : profit > 20000 ? 'yellow' : 'blue'
      });
    }
    
    setParticles(newParticles);
    
    // Clear particles after animation
    setTimeout(() => {
      setParticles([]);
    }, 4000);
  };

  // Auto-generate particles periodically when wealth is growing
  useEffect(() => {
    if (recentProfit > 0 && intensity > 0.3) {
      const interval = setInterval(() => {
        if (Math.random() < intensity) {
          generateParticles();
        }
      }, 3000 + Math.random() * 2000);
      
      return () => clearInterval(interval);
    }
  }, [recentProfit, intensity]);

  // Manual trigger on hover
  const handleMouseEnter = () => {
    setIsActive(true);
    generateParticles();
  };

  const handleMouseLeave = () => {
    setIsActive(false);
  };

  const getWealthColor = () => {
    if (totalValue > 50000000) return 'from-yellow-400 to-orange-500'; // 50M+
    if (totalValue > 10000000) return 'from-emerald-400 to-green-500'; // 10M+
    if (totalValue > 1000000) return 'from-blue-400 to-purple-500'; // 1M+
    return 'from-gray-400 to-slate-500'; // Under 1M
  };

  const getWealthGlow = () => {
    if (totalValue > 50000000) return 'shadow-yellow-400/50';
    if (totalValue > 10000000) return 'shadow-emerald-400/50';
    if (totalValue > 1000000) return 'shadow-blue-400/50';
    return 'shadow-gray-400/30';
  };

  return (
    <div 
      className={`relative overflow-hidden ${className}`}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      {/* Main Wealth Display */}
      <motion.div
        className={`relative z-10 bg-gradient-to-r ${getWealthColor()} bg-clip-text text-transparent font-bold`}
        animate={{
          textShadow: isActive ? '0 0 20px rgba(59, 130, 246, 0.8)' : '0 0 0px rgba(59, 130, 246, 0)'
        }}
        transition={{ duration: 0.3 }}
      >
        {formatGP(totalValue)}
      </motion.div>

      {/* Wealth Status Indicator */}
      <div className="flex items-center space-x-1 mt-1">
        <motion.div
          animate={{
            scale: isActive ? [1, 1.2, 1] : 1,
            opacity: [0.5, 1, 0.5]
          }}
          transition={{
            duration: 2,
            repeat: Infinity,
            ease: "easeInOut"
          }}
        >
          <Coins className={`w-3 h-3 text-yellow-400 drop-shadow-lg ${getWealthGlow()}`} />
        </motion.div>
        <span className="text-xs text-gray-400">Wealth Level</span>
      </div>

      {/* Floating GP Particles */}
      <AnimatePresence>
        {particles.map((particle) => (
          <motion.div
            key={particle.id}
            initial={{
              opacity: 0,
              scale: 0,
              x: `${particle.x}%`,
              y: `${particle.y}%`
            }}
            animate={{
              opacity: [0, 1, 1, 0],
              scale: [0, 1.2, 1, 0.8],
              y: `${particle.y - 100}%`,
              x: `${particle.x + (Math.random() - 0.5) * 20}%`,
            }}
            exit={{
              opacity: 0,
              scale: 0
            }}
            transition={{
              duration: 3,
              delay: particle.delay,
              ease: "easeOut"
            }}
            className="absolute pointer-events-none"
          >
            <div className={`
              flex items-center space-x-1 px-2 py-1 rounded-full text-xs font-semibold
              ${particle.color === 'emerald' ? 'bg-emerald-500/20 text-emerald-300 shadow-emerald-400/50' :
                particle.color === 'yellow' ? 'bg-yellow-500/20 text-yellow-300 shadow-yellow-400/50' :
                'bg-blue-500/20 text-blue-300 shadow-blue-400/50'
              }
              backdrop-blur-sm border border-white/20 shadow-lg
            `}>
              <TrendingUp className="w-3 h-3" />
              <span>+{formatGP(particle.value)}</span>
            </div>
          </motion.div>
        ))}
      </AnimatePresence>

      {/* Wealth Aura Effect */}
      <motion.div
        className={`absolute inset-0 rounded-lg bg-gradient-to-r ${getWealthColor()} opacity-0`}
        animate={{
          opacity: isActive ? [0, 0.1, 0] : 0
        }}
        transition={{
          duration: 2,
          repeat: isActive ? Infinity : 0
        }}
      />

      {/* Background Sparkle Effects */}
      {totalValue > 1000000 && (
        <div className="absolute inset-0 pointer-events-none">
          {[...Array(3)].map((_, i) => (
            <motion.div
              key={i}
              className="absolute w-1 h-1 bg-white rounded-full"
              style={{
                left: `${20 + i * 30}%`,
                top: `${20 + i * 15}%`,
              }}
              animate={{
                opacity: [0, 1, 0],
                scale: [0, 1, 0]
              }}
              transition={{
                duration: 2,
                delay: i * 0.5,
                repeat: Infinity,
                repeatDelay: 3
              }}
            />
          ))}
        </div>
      )}
    </div>
  );
};