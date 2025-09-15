import React from 'react';
import { motion } from 'framer-motion';

interface FuturisticGridProps {
  className?: string;
  animated?: boolean;
  opacity?: number;
}

export const FuturisticGrid: React.FC<FuturisticGridProps> = ({
  className = '',
  animated = true,
  opacity = 0.1
}) => {
  const gridLines = Array.from({ length: 20 }, (_, i) => i);
  
  return (
    <div className={`absolute inset-0 pointer-events-none ${className}`}>
      {/* SVG Grid Pattern */}
      <svg 
        className="absolute inset-0 w-full h-full" 
        style={{ opacity }}
        viewBox="0 0 100 100" 
        preserveAspectRatio="none"
      >
        <defs>
          {/* Grid Pattern Definition */}
          <pattern 
            id="futuristicGrid" 
            width="10" 
            height="10" 
            patternUnits="userSpaceOnUse"
          >
            <path 
              d="M 10 0 L 0 0 0 10" 
              fill="none" 
              stroke="rgba(6, 182, 212, 0.5)" 
              strokeWidth="0.2"
            />
          </pattern>
          
          {/* Major Grid Lines Pattern */}
          <pattern 
            id="majorGrid" 
            width="50" 
            height="50" 
            patternUnits="userSpaceOnUse"
          >
            <path 
              d="M 50 0 L 0 0 0 50" 
              fill="none" 
              stroke="rgba(6, 182, 212, 0.8)" 
              strokeWidth="0.4"
            />
          </pattern>

          {/* Animated Scan Lines */}
          <linearGradient id="scanGradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="rgba(6, 182, 212, 0)" />
            <stop offset="50%" stopColor="rgba(6, 182, 212, 0.8)" />
            <stop offset="100%" stopColor="rgba(6, 182, 212, 0)" />
          </linearGradient>
        </defs>
        
        {/* Base Grid */}
        <rect width="100%" height="100%" fill="url(#futuristicGrid)" />
        
        {/* Major Grid Lines */}
        <rect width="100%" height="100%" fill="url(#majorGrid)" />
        
        {/* Corner Markers */}
        <g stroke="rgba(6, 182, 212, 0.8)" strokeWidth="0.5" fill="none">
          {/* Top Left */}
          <path d="M 0 5 L 0 0 L 5 0" />
          {/* Top Right */}
          <path d="M 95 0 L 100 0 L 100 5" />
          {/* Bottom Left */}
          <path d="M 0 95 L 0 100 L 5 100" />
          {/* Bottom Right */}
          <path d="M 95 100 L 100 100 L 100 95" />
        </g>

        {/* Animated Elements */}
        {animated && (
          <>
            {/* Horizontal Scan Lines */}
            <motion.rect
              width="100%"
              height="0.5"
              fill="url(#scanGradient)"
              animate={{
                y: ['0%', '100%', '0%']
              }}
              transition={{
                duration: 8,
                repeat: Infinity,
                ease: "easeInOut"
              }}
            />
            
            {/* Vertical Scan Lines */}
            <motion.rect
              width="0.5"
              height="100%"
              fill="url(#scanGradient)"
              animate={{
                x: ['0%', '100%', '0%']
              }}
              transition={{
                duration: 6,
                repeat: Infinity,
                ease: "easeInOut",
                delay: 2
              }}
            />
          </>
        )}
      </svg>

      {/* CSS Grid Overlay for Visual Enhancement */}
      <div className="absolute inset-0 grid grid-cols-12 grid-rows-12 gap-0">
        {Array.from({ length: 144 }, (_, i) => (
          <div
            key={i}
            className="border border-cyan-400/5 relative"
          >
            {/* Random active cells with pulsing effect */}
            {Math.random() < 0.05 && (
              <motion.div
                className="absolute inset-0 bg-cyan-400/10"
                animate={{
                  opacity: [0, 0.3, 0]
                }}
                transition={{
                  duration: 2 + Math.random() * 3,
                  repeat: Infinity,
                  delay: Math.random() * 5
                }}
              />
            )}
          </div>
        ))}
      </div>

      {/* Holographic Data Lines */}
      <div className="absolute inset-0">
        {/* Diagonal Data Streams */}
        {[...Array(3)].map((_, i) => (
          <motion.div
            key={`diagonal-${i}`}
            className="absolute w-full h-0.5 bg-gradient-to-r from-transparent via-purple-400/40 to-transparent transform -rotate-45 origin-left"
            style={{
              top: `${20 + i * 30}%`,
              left: '-50%',
              width: '200%'
            }}
            animate={{
              opacity: [0, 0.6, 0],
              scaleX: [0.5, 1, 0.5]
            }}
            transition={{
              duration: 4,
              repeat: Infinity,
              delay: i * 1.5,
              ease: "easeInOut"
            }}
          />
        ))}

        {/* Circuit-like Connection Points */}
        {[...Array(8)].map((_, i) => (
          <motion.div
            key={`node-${i}`}
            className="absolute w-2 h-2 bg-cyan-400/60 rounded-full shadow-lg shadow-cyan-400/50"
            style={{
              left: `${15 + (i % 4) * 25}%`,
              top: `${25 + Math.floor(i / 4) * 50}%`
            }}
            animate={{
              scale: [1, 1.5, 1],
              opacity: [0.6, 1, 0.6]
            }}
            transition={{
              duration: 3,
              repeat: Infinity,
              delay: i * 0.5,
              ease: "easeInOut"
            }}
          />
        ))}
      </div>
    </div>
  );
};