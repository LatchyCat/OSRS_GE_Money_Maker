import React from 'react';
import { motion } from 'framer-motion';
import {
  FireIcon,
  BoltIcon,
  SparklesIcon,
  TrophyIcon
} from '@heroicons/react/24/outline';
import {
  FireIcon as FireIconSolid
} from '@heroicons/react/24/solid';

interface StreakCounterProps {
  currentStreak: number;
  bestStreak: number;
  streakType: 'profit' | 'trades' | 'sessions' | 'perfect';
  className?: string;
  showAnimation?: boolean;
  onStreakMilestone?: (streak: number) => void;
}

export const StreakCounter: React.FC<StreakCounterProps> = ({
  currentStreak,
  bestStreak,
  streakType = 'profit',
  className = '',
  showAnimation = true,
  onStreakMilestone
}) => {
  const getStreakLevel = (streak: number) => {
    if (streak >= 50) return { level: 'legendary', color: 'text-purple-400', bgColor: 'bg-purple-500/20', label: 'Legendary' };
    if (streak >= 25) return { level: 'epic', color: 'text-yellow-400', bgColor: 'bg-yellow-500/20', label: 'Epic' };
    if (streak >= 15) return { level: 'hot', color: 'text-orange-400', bgColor: 'bg-orange-500/20', label: 'Hot' };
    if (streak >= 10) return { level: 'good', color: 'text-blue-400', bgColor: 'bg-blue-500/20', label: 'Good' };
    if (streak >= 5) return { level: 'warm', color: 'text-green-400', bgColor: 'bg-green-500/20', label: 'Warm' };
    return { level: 'starting', color: 'text-gray-400', bgColor: 'bg-gray-500/20', label: 'Building' };
  };

  const currentLevel = getStreakLevel(currentStreak);
  const bestLevel = getStreakLevel(bestStreak);

  const getStreakIcon = (streak: number) => {
    if (streak >= 25) return TrophyIcon;
    if (streak >= 15) return SparklesIcon;
    if (streak >= 10) return BoltIcon;
    if (streak >= 5) return FireIcon;
    return FireIcon;
  };

  const CurrentIcon = getStreakIcon(currentStreak);

  const getStreakMessage = (streak: number, type: string) => {
    if (streak === 0) return `Start your ${type} streak!`;
    if (streak >= 50) return 'LEGENDARY STREAK! 🏆';
    if (streak >= 25) return 'Epic streak going! 🔥';
    if (streak >= 15) return 'You\'re on fire! 🚀';
    if (streak >= 10) return 'Great momentum! ⚡';
    if (streak >= 5) return 'Building momentum! 📈';
    return 'Keep it going! 💪';
  };

  const getNextMilestone = (streak: number) => {
    const milestones = [5, 10, 15, 25, 50, 100];
    return milestones.find(milestone => milestone > streak) || null;
  };

  const nextMilestone = getNextMilestone(currentStreak);

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      className={`${currentLevel.bgColor} backdrop-blur-sm border border-current/30 rounded-xl p-4 ${className}`}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <motion.div
            animate={showAnimation && currentStreak >= 5 ? {
              scale: [1, 1.1, 1],
              rotate: [0, 5, -5, 0]
            } : {}}
            transition={{ duration: 2, repeat: Infinity }}
            className={`p-2 ${currentLevel.bgColor} rounded-lg`}
          >
            {currentStreak >= 5 ? (
              <FireIconSolid className={`w-6 h-6 ${currentLevel.color}`} />
            ) : (
              <CurrentIcon className={`w-6 h-6 ${currentLevel.color}`} />
            )}
          </motion.div>
          <div>
            <h3 className={`text-lg font-bold ${currentLevel.color}`}>
              {currentStreak} {streakType} streak
            </h3>
            <p className="text-sm text-gray-400 capitalize">
              {currentLevel.label} • {getStreakMessage(currentStreak, streakType)}
            </p>
          </div>
        </div>

        {/* Best streak badge */}
        {bestStreak > currentStreak && (
          <div className="text-center">
            <div className={`text-sm font-bold ${bestLevel.color}`}>Best</div>
            <div className={`text-lg font-bold ${bestLevel.color}`}>{bestStreak}</div>
          </div>
        )}
      </div>

      {/* Progress to next milestone */}
      {nextMilestone && (
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-gray-400">Next milestone</span>
            <span className={currentLevel.color}>
              {currentStreak}/{nextMilestone}
            </span>
          </div>
          <div className="w-full bg-gray-700/50 rounded-full h-2">
            <motion.div
              className={`bg-gradient-to-r ${
                nextMilestone >= 50 ? 'from-purple-500 to-pink-500' :
                nextMilestone >= 25 ? 'from-yellow-500 to-orange-500' :
                nextMilestone >= 15 ? 'from-orange-500 to-red-500' :
                nextMilestone >= 10 ? 'from-blue-500 to-cyan-500' :
                'from-green-500 to-emerald-500'
              } h-2 rounded-full`}
              initial={{ width: 0 }}
              animate={{ width: `${(currentStreak / nextMilestone) * 100}%` }}
              transition={{ duration: 1, ease: "easeOut" }}
            />
          </div>
          <div className="text-xs text-gray-500 text-center">
            {nextMilestone - currentStreak} more to reach {getStreakLevel(nextMilestone).label}
          </div>
        </div>
      )}

      {/* Streak effects */}
      {currentStreak >= 10 && showAnimation && (
        <div className="absolute -top-1 -right-1 pointer-events-none">
          <motion.div
            animate={{
              scale: [1, 1.2, 1],
              opacity: [0.5, 1, 0.5]
            }}
            transition={{ duration: 1.5, repeat: Infinity }}
            className="w-4 h-4 bg-yellow-400 rounded-full blur-sm"
          />
        </div>
      )}
    </motion.div>
  );
};

export default StreakCounter;