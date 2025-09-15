import React from 'react';
import { motion } from 'framer-motion';
import { Loader2, Zap, Activity, Database } from 'lucide-react';

interface HolographicLoaderProps {
  size?: 'sm' | 'md' | 'lg';
  text?: string;
  variant?: 'default' | 'data' | 'system' | 'market';
  className?: string;
}

export const HolographicLoader: React.FC<HolographicLoaderProps> = ({
  size = 'md',
  text = 'Loading...',
  variant = 'default',
  className = ''
}) => {
  const sizeClasses = {
    sm: 'w-6 h-6',
    md: 'w-12 h-12',
    lg: 'w-24 h-24'
  };

  const textSizeClasses = {
    sm: 'text-xs',
    md: 'text-sm',
    lg: 'text-lg'
  };

  const getVariantConfig = () => {
    switch (variant) {
      case 'data':
        return {
          color: 'emerald',
          icon: Database,
          borderColor: 'border-emerald-400/30',
          glowColor: 'shadow-emerald-400/50',
          textColor: 'text-emerald-300'
        };
      case 'system':
        return {
          color: 'purple',
          icon: Activity,
          borderColor: 'border-purple-400/30',
          glowColor: 'shadow-purple-400/50',
          textColor: 'text-purple-300'
        };
      case 'market':
        return {
          color: 'yellow',
          icon: Zap,
          borderColor: 'border-yellow-400/30',
          glowColor: 'shadow-yellow-400/50',
          textColor: 'text-yellow-300'
        };
      default:
        return {
          color: 'cyan',
          icon: Loader2,
          borderColor: 'border-cyan-400/30',
          glowColor: 'shadow-cyan-400/50',
          textColor: 'text-cyan-300'
        };
    }
  };

  const config = getVariantConfig();
  const Icon = config.icon;

  return (
    <div className={`flex flex-col items-center justify-center space-y-4 ${className}`}>
      {/* Main Loader Container */}
      <div className="relative">
        {/* Outer Ring */}
        <motion.div
          className={`relative ${sizeClasses[size]} rounded-full bg-black/40 backdrop-blur-xl border ${config.borderColor} shadow-2xl ${config.glowColor}`}
          animate={{
            rotate: 360
          }}
          transition={{
            duration: 3,
            repeat: Infinity,
            ease: "linear"
          }}
        >
          {/* Inner Ring */}
          <motion.div
            className={`absolute inset-2 rounded-full border ${config.borderColor} opacity-60`}
            animate={{
              rotate: -360
            }}
            transition={{
              duration: 2,
              repeat: Infinity,
              ease: "linear"
            }}
          />

          {/* Center Icon */}
          <div className="absolute inset-0 flex items-center justify-center">
            <motion.div
              animate={{
                scale: [1, 1.1, 1],
                opacity: [0.7, 1, 0.7]
              }}
              transition={{
                duration: 2,
                repeat: Infinity,
                ease: "easeInOut"
              }}
            >
              <Icon className={`${size === 'sm' ? 'w-3 h-3' : size === 'md' ? 'w-6 h-6' : 'w-12 h-12'} ${config.textColor} drop-shadow-lg`} />
            </motion.div>
          </div>

          {/* Scanning Arc */}
          <motion.div
            className="absolute inset-0 rounded-full"
            style={{
              background: `conic-gradient(from 0deg, transparent 0deg, rgba(${
                config.color === 'cyan' ? '6, 182, 212' :
                config.color === 'emerald' ? '16, 185, 129' :
                config.color === 'purple' ? '147, 51, 234' :
                '251, 191, 36'
              }, 0.8) 90deg, transparent 180deg)`
            }}
            animate={{
              rotate: 360
            }}
            transition={{
              duration: 1.5,
              repeat: Infinity,
              ease: "linear"
            }}
          />
        </motion.div>

        {/* Orbital Elements */}
        <motion.div
          className="absolute inset-0 flex items-center justify-center"
          animate={{
            rotate: 360
          }}
          transition={{
            duration: 4,
            repeat: Infinity,
            ease: "linear"
          }}
        >
          {[...Array(3)].map((_, i) => (
            <motion.div
              key={i}
              className={`absolute w-1 h-1 bg-${config.color}-400 rounded-full shadow-lg shadow-${config.color}-400/75`}
              style={{
                transform: `rotate(${i * 120}deg) translateY(-${size === 'sm' ? '20' : size === 'md' ? '35' : '60'}px)`
              }}
              animate={{
                scale: [1, 1.5, 1],
                opacity: [0.5, 1, 0.5]
              }}
              transition={{
                duration: 1,
                repeat: Infinity,
                delay: i * 0.2,
                ease: "easeInOut"
              }}
            />
          ))}
        </motion.div>
      </div>

      {/* Loading Text */}
      {text && (
        <motion.div
          className={`text-center ${textSizeClasses[size]} font-medium ${config.textColor} drop-shadow-lg`}
          animate={{
            opacity: [0.5, 1, 0.5]
          }}
          transition={{
            duration: 2,
            repeat: Infinity,
            ease: "easeInOut"
          }}
        >
          {text}
        </motion.div>
      )}

      {/* Data Stream Lines */}
      <div className="relative">
        {[...Array(3)].map((_, i) => (
          <motion.div
            key={i}
            className={`absolute w-20 h-0.5 bg-gradient-to-r from-transparent via-${config.color}-400/60 to-transparent`}
            style={{
              left: `-10px`,
              top: `${i * 8 - 8}px`
            }}
            animate={{
              scaleX: [0, 1, 0],
              opacity: [0, 0.8, 0]
            }}
            transition={{
              duration: 2,
              repeat: Infinity,
              delay: i * 0.3,
              ease: "easeInOut"
            }}
          />
        ))}
      </div>

      {/* Holographic Shimmer Effect */}
      <motion.div
        className="absolute inset-0 rounded-full opacity-0"
        style={{
          background: `linear-gradient(135deg, transparent 0%, rgba(${
            config.color === 'cyan' ? '6, 182, 212' :
            config.color === 'emerald' ? '16, 185, 129' :
            config.color === 'purple' ? '147, 51, 234' :
            '251, 191, 36'
          }, 0.3) 50%, transparent 100%)`,
          transform: 'skewX(-15deg)'
        }}
        animate={{
          opacity: [0, 0.6, 0],
          x: ['-100%', '100%']
        }}
        transition={{
          duration: 3,
          repeat: Infinity,
          ease: "easeInOut"
        }}
      />
    </div>
  );
};