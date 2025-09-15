import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  TrophyIcon,
  SparklesIcon,
  FireIcon,
  BoltIcon,
  StarIcon,
  ChartBarIcon,
  ClockIcon,
  CurrencyDollarIcon,
  RocketLaunchIcon,
  ShieldCheckIcon,
  AcademicCapIcon,
  LightBulbIcon,
  BeakerIcon,
  GiftIcon
} from '@heroicons/react/24/outline';
import {
  TrophyIcon as TrophyIconSolid,
  StarIcon as StarIconSolid,
  FireIcon as FireIconSolid
} from '@heroicons/react/24/solid';

interface Achievement {
  id: string;
  title: string;
  description: string;
  category: 'profit' | 'trades' | 'streak' | 'discovery' | 'mastery' | 'milestone';
  tier: 'bronze' | 'silver' | 'gold' | 'platinum' | 'legendary';
  progress: number;
  maxProgress: number;
  isUnlocked: boolean;
  unlockedAt?: Date;
  reward: {
    type: 'xp' | 'title' | 'badge' | 'bonus';
    value: number | string;
  };
  icon: React.ComponentType<{ className?: string }>;
  rarity: number; // 1-5 stars
}

interface AchievementSystemProps {
  isOpen: boolean;
  onClose: () => void;
  playerStats: {
    totalProfit: number;
    tradesExecuted: number;
    currentStreak: number;
    bestStreak: number;
    sessionsPlayed: number;
    totalPlayTime: number;
    opportunitiesDiscovered: number;
    perfectTrades: number;
  };
  onAchievementUnlocked?: (achievement: Achievement) => void;
}

export const AchievementSystem: React.FC<AchievementSystemProps> = ({
  isOpen,
  onClose,
  playerStats,
  onAchievementUnlocked
}) => {
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [newUnlocks, setNewUnlocks] = useState<Achievement[]>([]);
  const processedAchievements = React.useRef<Set<string>>(new Set());
  
  // Define all achievements
  const achievements: Achievement[] = [
    // Profit Category
    {
      id: 'first_million',
      title: 'Millionaire',
      description: 'Earn your first 1M GP profit from decanting',
      category: 'profit',
      tier: 'bronze',
      progress: Math.min(playerStats.totalProfit, 1000000),
      maxProgress: 1000000,
      isUnlocked: playerStats.totalProfit >= 1000000,
      reward: { type: 'xp', value: 100 },
      icon: CurrencyDollarIcon,
      rarity: 1
    },
    {
      id: 'ten_million',
      title: 'Wealthy Trader',
      description: 'Accumulate 10M GP in total profits',
      category: 'profit',
      tier: 'silver',
      progress: Math.min(playerStats.totalProfit, 10000000),
      maxProgress: 10000000,
      isUnlocked: playerStats.totalProfit >= 10000000,
      reward: { type: 'title', value: 'Wealthy Trader' },
      icon: BoltIcon,
      rarity: 2
    },
    {
      id: 'hundred_million',
      title: 'Grand Exchange Mogul',
      description: 'Reach 100M GP in lifetime profits',
      category: 'profit',
      tier: 'gold',
      progress: Math.min(playerStats.totalProfit, 100000000),
      maxProgress: 100000000,
      isUnlocked: playerStats.totalProfit >= 100000000,
      reward: { type: 'badge', value: 'Mogul Badge' },
      icon: RocketLaunchIcon,
      rarity: 4
    },

    // Trading Category
    {
      id: 'first_trade',
      title: 'Getting Started',
      description: 'Complete your first decanting trade',
      category: 'trades',
      tier: 'bronze',
      progress: Math.min(playerStats.tradesExecuted, 1),
      maxProgress: 1,
      isUnlocked: playerStats.tradesExecuted >= 1,
      reward: { type: 'xp', value: 25 },
      icon: BeakerIcon,
      rarity: 1
    },
    {
      id: 'hundred_trades',
      title: 'Experienced Decanter',
      description: 'Execute 100 successful trades',
      category: 'trades',
      tier: 'silver',
      progress: Math.min(playerStats.tradesExecuted, 100),
      maxProgress: 100,
      isUnlocked: playerStats.tradesExecuted >= 100,
      reward: { type: 'bonus', value: '5% profit boost for next 10 trades' },
      icon: ChartBarIcon,
      rarity: 2
    },
    {
      id: 'thousand_trades',
      title: 'Master Trader',
      description: 'Complete 1,000 trading operations',
      category: 'trades',
      tier: 'gold',
      progress: Math.min(playerStats.tradesExecuted, 1000),
      maxProgress: 1000,
      isUnlocked: playerStats.tradesExecuted >= 1000,
      reward: { type: 'title', value: 'Master Trader' },
      icon: TrophyIcon,
      rarity: 3
    },

    // Streak Category
    {
      id: 'five_streak',
      title: 'Hot Streak',
      description: 'Achieve 5 profitable trades in a row',
      category: 'streak',
      tier: 'bronze',
      progress: Math.min(playerStats.bestStreak, 5),
      maxProgress: 5,
      isUnlocked: playerStats.bestStreak >= 5,
      reward: { type: 'xp', value: 50 },
      icon: FireIcon,
      rarity: 2
    },
    {
      id: 'twenty_streak',
      title: 'Unstoppable',
      description: 'Maintain a 20-trade profit streak',
      category: 'streak',
      tier: 'gold',
      progress: Math.min(playerStats.bestStreak, 20),
      maxProgress: 20,
      isUnlocked: playerStats.bestStreak >= 20,
      reward: { type: 'badge', value: 'Unstoppable Badge' },
      icon: FireIcon,
      rarity: 4
    },

    // Discovery Category
    {
      id: 'explorer',
      title: 'Market Explorer',
      description: 'Discover 50 unique trading opportunities',
      category: 'discovery',
      tier: 'silver',
      progress: Math.min(playerStats.opportunitiesDiscovered, 50),
      maxProgress: 50,
      isUnlocked: playerStats.opportunitiesDiscovered >= 50,
      reward: { type: 'xp', value: 75 },
      icon: LightBulbIcon,
      rarity: 2
    },

    // Mastery Category
    {
      id: 'perfectionist',
      title: 'Perfect Precision',
      description: 'Execute 10 perfect trades (maximum profit achieved)',
      category: 'mastery',
      tier: 'platinum',
      progress: Math.min(playerStats.perfectTrades, 10),
      maxProgress: 10,
      isUnlocked: playerStats.perfectTrades >= 10,
      reward: { type: 'title', value: 'Perfectionist' },
      icon: StarIcon,
      rarity: 5
    },

    // Milestone Category
    {
      id: 'dedication',
      title: 'Dedicated Trader',
      description: 'Play for 10+ hours total',
      category: 'milestone',
      tier: 'silver',
      progress: Math.min(playerStats.totalPlayTime, 36000), // 10 hours in seconds
      maxProgress: 36000,
      isUnlocked: playerStats.totalPlayTime >= 36000,
      reward: { type: 'badge', value: 'Dedication Badge' },
      icon: ClockIcon,
      rarity: 3
    }
  ];

  // Check for new achievements
  useEffect(() => {
    const newlyUnlocked = achievements.filter(achievement => {
      return achievement.isUnlocked && 
             achievement.progress === achievement.maxProgress &&
             !processedAchievements.current.has(achievement.id);
    });
    
    newlyUnlocked.forEach(achievement => {
      // Mark as processed to prevent duplicates
      processedAchievements.current.add(achievement.id);
      
      setNewUnlocks(prev => [...prev, achievement]);
      onAchievementUnlocked?.(achievement);
      
      // Remove from new unlocks after 5 seconds
      setTimeout(() => {
        setNewUnlocks(prev => prev.filter(unlock => unlock.id !== achievement.id));
      }, 5000);
    });
  }, [playerStats.totalProfit, playerStats.tradesExecuted, playerStats.bestStreak, playerStats.opportunitiesDiscovered, playerStats.perfectTrades, playerStats.totalPlayTime]);

  const categories = [
    { id: 'all', name: 'All', icon: TrophyIcon },
    { id: 'profit', name: 'Profit', icon: CurrencyDollarIcon },
    { id: 'trades', name: 'Trading', icon: ChartBarIcon },
    { id: 'streak', name: 'Streaks', icon: FireIcon },
    { id: 'discovery', name: 'Discovery', icon: LightBulbIcon },
    { id: 'mastery', name: 'Mastery', icon: StarIcon },
    { id: 'milestone', name: 'Milestones', icon: ClockIcon }
  ];

  const filteredAchievements = selectedCategory === 'all' 
    ? achievements 
    : achievements.filter(a => a.category === selectedCategory);

  const unlockedCount = achievements.filter(a => a.isUnlocked).length;
  const totalXP = achievements
    .filter(a => a.isUnlocked && a.reward.type === 'xp')
    .reduce((sum, a) => sum + (a.reward.value as number), 0);

  const getTierColor = (tier: Achievement['tier']) => {
    switch (tier) {
      case 'bronze': return 'text-orange-400 border-orange-400/30 bg-orange-900/20';
      case 'silver': return 'text-gray-300 border-gray-300/30 bg-gray-800/40';
      case 'gold': return 'text-yellow-400 border-yellow-400/30 bg-yellow-900/20';
      case 'platinum': return 'text-blue-400 border-blue-400/30 bg-blue-900/20';
      case 'legendary': return 'text-purple-400 border-purple-400/30 bg-purple-900/20';
    }
  };

  const getRarityStars = (rarity: number) => {
    return Array.from({ length: 5 }, (_, i) => (
      <StarIconSolid 
        key={i}
        className={`w-3 h-3 ${i < rarity ? 'text-yellow-400' : 'text-gray-600'}`}
      />
    ));
  };

  if (!isOpen) return null;

  return (
    <>
      {/* Achievement Unlock Notifications */}
      <AnimatePresence>
        {newUnlocks.map((achievement, index) => (
          <motion.div
            key={achievement.id}
            initial={{ opacity: 0, x: 300, scale: 0.8 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: 300, scale: 0.8 }}
            className="fixed top-20 right-6 z-[100] pointer-events-none"
            style={{ top: `${80 + index * 120}px` }}
          >
            <div className="bg-gradient-to-r from-yellow-900/90 to-orange-900/90 backdrop-blur-lg border border-yellow-400/30 rounded-xl p-4 shadow-2xl max-w-sm">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-yellow-400/20 rounded-lg">
                  <TrophyIconSolid className="w-8 h-8 text-yellow-400" />
                </div>
                <div>
                  <div className="text-yellow-300 font-bold">Achievement Unlocked!</div>
                  <div className="text-white font-medium">{achievement.title}</div>
                  <div className="text-yellow-200/80 text-sm">{achievement.description}</div>
                  <div className="flex items-center gap-1 mt-1">
                    {getRarityStars(achievement.rarity)}
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        ))}
      </AnimatePresence>

      {/* Main Achievement Modal */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
        onClick={onClose}
      >
        <motion.div
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.9, opacity: 0 }}
          className="bg-gray-900 border border-gray-700 rounded-2xl max-w-6xl w-full max-h-[90vh] overflow-hidden"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="p-6 border-b border-gray-700 bg-gradient-to-r from-yellow-900/20 to-orange-900/20">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-yellow-500/20 rounded-lg">
                  <TrophyIcon className="w-8 h-8 text-yellow-400" />
                </div>
                <div>
                  <h2 className="text-2xl font-bold text-white">Achievements</h2>
                  <p className="text-gray-400">
                    {unlockedCount}/{achievements.length} unlocked • {totalXP} XP earned
                  </p>
                </div>
              </div>
              <button
                onClick={onClose}
                className="p-2 hover:bg-gray-700 rounded-lg transition-colors"
              >
                <span className="text-gray-400 text-2xl">×</span>
              </button>
            </div>

            {/* Progress Bar */}
            <div className="mt-4">
              <div className="flex justify-between text-sm text-gray-400 mb-2">
                <span>Overall Progress</span>
                <span>{Math.round((unlockedCount / achievements.length) * 100)}%</span>
              </div>
              <div className="w-full bg-gray-700 rounded-full h-2">
                <motion.div
                  className="bg-gradient-to-r from-yellow-400 to-orange-400 h-2 rounded-full"
                  initial={{ width: 0 }}
                  animate={{ width: `${(unlockedCount / achievements.length) * 100}%` }}
                  transition={{ duration: 1, ease: "easeOut" }}
                />
              </div>
            </div>
          </div>

          <div className="flex h-[calc(90vh-200px)]">
            {/* Category Sidebar */}
            <div className="w-64 border-r border-gray-700 p-4">
              <div className="space-y-2">
                {categories.map((category) => (
                  <button
                    key={category.id}
                    onClick={() => setSelectedCategory(category.id)}
                    className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                      selectedCategory === category.id
                        ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30'
                        : 'text-gray-400 hover:bg-gray-800/50'
                    }`}
                  >
                    <category.icon className="w-5 h-5" />
                    <span>{category.name}</span>
                    <span className="ml-auto text-xs">
                      {category.id === 'all' 
                        ? unlockedCount 
                        : achievements.filter(a => a.category === category.id && a.isUnlocked).length}
                    </span>
                  </button>
                ))}
              </div>
            </div>

            {/* Achievements Grid */}
            <div className="flex-1 p-6 overflow-y-auto">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {filteredAchievements.map((achievement) => (
                  <motion.div
                    key={achievement.id}
                    layout
                    className={`relative border rounded-xl p-4 transition-all duration-300 ${
                      achievement.isUnlocked
                        ? getTierColor(achievement.tier)
                        : 'border-gray-700 bg-gray-800/30 text-gray-500'
                    } ${achievement.isUnlocked ? 'hover:scale-105' : ''}`}
                  >
                    {achievement.isUnlocked && (
                      <motion.div
                        initial={{ scale: 0, rotate: -180 }}
                        animate={{ scale: 1, rotate: 0 }}
                        className="absolute -top-2 -right-2 p-1 bg-yellow-500 rounded-full"
                      >
                        <TrophyIconSolid className="w-4 h-4 text-white" />
                      </motion.div>
                    )}

                    <div className="flex items-start gap-3">
                      <div className={`p-2 rounded-lg ${
                        achievement.isUnlocked
                          ? 'bg-current/20'
                          : 'bg-gray-700/50'
                      }`}>
                        <achievement.icon className={`w-6 h-6 ${
                          achievement.isUnlocked ? 'text-current' : 'text-gray-500'
                        }`} />
                      </div>
                      
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <h3 className={`font-semibold ${
                            achievement.isUnlocked ? 'text-current' : 'text-gray-500'
                          }`}>
                            {achievement.title}
                          </h3>
                          <div className="flex items-center gap-0.5">
                            {getRarityStars(achievement.rarity)}
                          </div>
                        </div>
                        
                        <p className={`text-sm mb-3 ${
                          achievement.isUnlocked ? 'text-current/80' : 'text-gray-600'
                        }`}>
                          {achievement.description}
                        </p>

                        {/* Progress Bar */}
                        {!achievement.isUnlocked && (
                          <div className="mb-3">
                            <div className="flex justify-between text-xs text-gray-500 mb-1">
                              <span>Progress</span>
                              <span>{achievement.progress.toLocaleString()}/{achievement.maxProgress.toLocaleString()}</span>
                            </div>
                            <div className="w-full bg-gray-700 rounded-full h-1.5">
                              <div
                                className="bg-blue-500 h-1.5 rounded-full transition-all duration-300"
                                style={{ width: `${(achievement.progress / achievement.maxProgress) * 100}%` }}
                              />
                            </div>
                          </div>
                        )}

                        {/* Reward */}
                        <div className={`text-xs flex items-center gap-1 ${
                          achievement.isUnlocked ? 'text-current/60' : 'text-gray-600'
                        }`}>
                          <GiftIcon className="w-3 h-3" />
                          <span>
                            Reward: {achievement.reward.type === 'xp' 
                              ? `${achievement.reward.value} XP`
                              : achievement.reward.value}
                          </span>
                        </div>

                        {achievement.isUnlocked && achievement.unlockedAt && (
                          <div className="text-xs text-current/40 mt-1">
                            Unlocked: {achievement.unlockedAt.toLocaleDateString()}
                          </div>
                        )}
                      </div>
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>
          </div>
        </motion.div>
      </motion.div>
    </>
  );
};

export default AchievementSystem;