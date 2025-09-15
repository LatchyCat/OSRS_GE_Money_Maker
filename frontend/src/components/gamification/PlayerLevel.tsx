import React from 'react';
import { motion } from 'framer-motion';
import {
  SparklesIcon,
  TrophyIcon,
  FireIcon,
  BoltIcon,
  StarIcon
} from '@heroicons/react/24/outline';

interface PlayerLevelProps {
  currentXP: number;
  level: number;
  xpToNextLevel: number;
  totalXPForNextLevel: number;
  playerTitle?: string;
  achievements: number;
  className?: string;
  showDetailed?: boolean;
}

export const PlayerLevel: React.FC<PlayerLevelProps> = ({
  currentXP,
  level,
  xpToNextLevel,
  totalXPForNextLevel,
  playerTitle = "Novice Trader",
  achievements = 0,
  className = "",
  showDetailed = false
}) => {
  const progressPercent = ((totalXPForNextLevel - xpToNextLevel) / totalXPForNextLevel) * 100;
  
  const getRankInfo = (level: number) => {
    if (level >= 100) return { name: "Legendary Master", color: "text-purple-400", bgColor: "from-purple-900/40 to-pink-900/40" };
    if (level >= 75) return { name: "Grand Master", color: "text-yellow-400", bgColor: "from-yellow-900/40 to-orange-900/40" };
    if (level >= 50) return { name: "Expert", color: "text-blue-400", bgColor: "from-blue-900/40 to-cyan-900/40" };
    if (level >= 25) return { name: "Journeyman", color: "text-green-400", bgColor: "from-green-900/40 to-emerald-900/40" };
    if (level >= 10) return { name: "Apprentice", color: "text-orange-400", bgColor: "from-orange-900/40 to-red-900/40" };
    return { name: "Novice", color: "text-gray-400", bgColor: "from-gray-800/40 to-gray-700/40" };
  };

  const rankInfo = getRankInfo(level);

  const getLevelIcon = (level: number) => {
    if (level >= 100) return SparklesIcon;
    if (level >= 75) return TrophyIcon;
    if (level >= 50) return StarIcon;
    if (level >= 25) return BoltIcon;
    if (level >= 10) return FireIcon;
    return SparklesIcon;
  };

  const LevelIcon = getLevelIcon(level);

  if (!showDetailed) {
    // Compact version for header/toolbar
    return (
      <div className={`flex items-center gap-3 ${className}`}>
        <div className={`p-2 bg-gradient-to-br ${rankInfo.bgColor} border border-current/30 rounded-lg`}>
          <LevelIcon className={`w-5 h-5 ${rankInfo.color}`} />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <span className={`text-lg font-bold ${rankInfo.color}`}>Level {level}</span>
            <span className="text-xs text-gray-400">•</span>
            <span className="text-sm text-gray-300">{playerTitle}</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-24 bg-gray-700 rounded-full h-1.5">
              <motion.div
                className={`bg-gradient-to-r ${rankInfo.bgColor.replace('40', '100')} h-1.5 rounded-full`}
                initial={{ width: 0 }}
                animate={{ width: `${progressPercent}%` }}
                transition={{ duration: 1, ease: "easeOut" }}
              />
            </div>
            <span className="text-xs text-gray-500">{xpToNextLevel} XP</span>
          </div>
        </div>
      </div>
    );
  }

  // Detailed version for profile/modal
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={`bg-gradient-to-r ${rankInfo.bgColor} backdrop-blur-sm border border-current/20 rounded-2xl p-6 ${className}`}
    >
      <div className="flex items-center gap-4 mb-4">
        <motion.div 
          className={`p-4 bg-gradient-to-br ${rankInfo.bgColor} border-2 border-current/40 rounded-xl shadow-lg`}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
        >
          <LevelIcon className={`w-12 h-12 ${rankInfo.color}`} />
        </motion.div>
        
        <div>
          <div className="flex items-center gap-3 mb-1">
            <h2 className={`text-3xl font-bold ${rankInfo.color}`}>Level {level}</h2>
            <div className="px-3 py-1 bg-black/30 rounded-full">
              <span className={`text-sm font-medium ${rankInfo.color}`}>{rankInfo.name}</span>
            </div>
          </div>
          <p className="text-lg text-white font-medium">{playerTitle}</p>
          <p className="text-sm text-gray-300">
            {achievements} achievements unlocked • {currentXP.toLocaleString()} total XP
          </p>
        </div>
      </div>

      {/* Detailed Progress */}
      <div className="space-y-3">
        <div className="flex justify-between items-center">
          <span className="text-sm font-medium text-white">Progress to Level {level + 1}</span>
          <span className="text-sm text-gray-300">
            {(totalXPForNextLevel - xpToNextLevel).toLocaleString()} / {totalXPForNextLevel.toLocaleString()} XP
          </span>
        </div>
        
        <div className="relative">
          <div className="w-full bg-black/30 rounded-full h-3 overflow-hidden">
            <motion.div
              className={`bg-gradient-to-r ${rankInfo.color === 'text-purple-400' 
                ? 'from-purple-500 to-pink-500'
                : rankInfo.color === 'text-yellow-400'
                ? 'from-yellow-500 to-orange-500'
                : rankInfo.color === 'text-blue-400'
                ? 'from-blue-500 to-cyan-500'
                : rankInfo.color === 'text-green-400'
                ? 'from-green-500 to-emerald-500'
                : 'from-orange-500 to-red-500'
              } h-3 rounded-full shadow-lg`}
              initial={{ width: 0 }}
              animate={{ width: `${progressPercent}%` }}
              transition={{ duration: 2, ease: "easeOut" }}
            />
          </div>
          
          {/* Progress indicators */}
          <div className="absolute inset-0 flex items-center justify-between px-1">
            {Array.from({ length: 5 }, (_, i) => (
              <div
                key={i}
                className={`w-1 h-1 rounded-full ${
                  (i / 4) * 100 <= progressPercent ? 'bg-white' : 'bg-gray-600'
                }`}
              />
            ))}
          </div>
        </div>
        
        <div className="text-center">
          <span className="text-xs text-gray-400">
            {xpToNextLevel.toLocaleString()} XP until next level
          </span>
        </div>
      </div>

      {/* Next rank preview */}
      {level < 100 && (
        <div className="mt-4 p-3 bg-black/20 rounded-lg border border-white/10">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-400">Next Rank:</span>
            <span className={`text-sm font-medium ${getRankInfo(level + (level >= 75 ? 25 : level >= 50 ? 25 : level >= 25 ? 25 : level >= 10 ? 15 : 10)).color}`}>
              {getRankInfo(level + (level >= 75 ? 25 : level >= 50 ? 25 : level >= 25 ? 25 : level >= 10 ? 15 : 10)).name}
            </span>
          </div>
        </div>
      )}
    </motion.div>
  );
};

export default PlayerLevel;