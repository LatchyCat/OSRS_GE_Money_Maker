import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { TrendingUp, Target, Clock, DollarSign, AlertTriangle, RefreshCw } from 'lucide-react';
import { moneyMakerApi } from '../api/moneyMaker';
import * as MoneyMakerTypes from '../types/moneyMaker';
import { CapitalProgressionCard } from '../components/moneyMaker/CapitalProgressionCard';
import { StrategyCard } from '../components/moneyMaker/StrategyCard';
import { GETaxCalculator } from '../components/moneyMaker/GETaxCalculator';
import { CapitalProgressionAdvisor } from '../components/moneyMaker/CapitalProgressionAdvisor';
import { LoadingSpinner } from '../components/common/LoadingSpinner';

interface DashboardStats {
  totalStrategies: number;
  totalHourlyProfit: number;
  averageSuccessRate: number;
  capitalInvested: number;
}

export const MoneyMakerDashboard: React.FC = () => {
  const [strategies, setStrategies] = useState<MoneyMakerTypes.MoneyMakerStrategy[]>([]);
  const [progressionTiers, setProgressionTiers] = useState<Record<string, MoneyMakerTypes.CapitalTier>>({});
  const [stats, setStats] = useState<DashboardStats>({
    totalStrategies: 0,
    totalHourlyProfit: 0,
    averageSuccessRate: 0,
    capitalInvested: 0
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCapital, setSelectedCapital] = useState(50_000_000); // Default 50M GP
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadDashboardData();
  }, [selectedCapital]);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const [strategiesData, tiersData] = await Promise.all([
        moneyMakerApi.getStrategies({ min_capital: selectedCapital }),
        moneyMakerApi.getProgressionTiers()
      ]);

      setStrategies(strategiesData.results || []);
      setProgressionTiers(tiersData);
      
      // Calculate dashboard stats
      const totalHourlyProfit = strategiesData.results?.reduce(
        (sum: number, s: MoneyMakerTypes.MoneyMakerStrategy) => sum + s.hourly_profit_gp, 0
      ) || 0;
      
      const averageSuccessRate = strategiesData.results?.length 
        ? strategiesData.results.reduce((sum: number, s: MoneyMakerTypes.MoneyMakerStrategy) => 
            sum + parseFloat(s.success_rate_percentage.toString()), 0
          ) / strategiesData.results.length 
        : 0;

      const capitalInvested = strategiesData.results?.reduce(
        (sum: number, s: MoneyMakerTypes.MoneyMakerStrategy) => sum + s.starting_capital, 0
      ) || 0;

      setStats({
        totalStrategies: strategiesData.results?.length || 0,
        totalHourlyProfit,
        averageSuccessRate,
        capitalInvested
      });

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  const refreshData = async () => {
    setRefreshing(true);
    await loadDashboardData();
    setRefreshing(false);
  };

  const formatGP = (amount: number) => {
    if (amount >= 1_000_000) {
      return `${(amount / 1_000_000).toFixed(1)}M GP`;
    } else if (amount >= 1_000) {
      return `${(amount / 1_000).toFixed(0)}K GP`;
    }
    return `${amount.toLocaleString()} GP`;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <LoadingSpinner size="lg" />
        <span className="ml-3 text-lg text-gray-300">Loading money maker dashboard...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-900/20 border border-red-700 rounded-lg p-6">
        <div className="flex items-center">
          <AlertTriangle className="h-5 w-5 text-red-400 mr-2" />
          <h3 className="text-lg font-semibold text-red-300">Error Loading Dashboard</h3>
        </div>
        <p className="text-red-400 mt-2">{error}</p>
        <button
          onClick={refreshData}
          className="mt-4 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
        >
          Try Again
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Money Maker Dashboard</h1>
          <p className="text-gray-400">
            Your friend's proven 50M → 100M GP strategies with real-time opportunities
          </p>
        </div>
        
        <div className="flex items-center gap-4">
          {/* Capital Selector */}
          <div className="flex items-center gap-2">
            <label htmlFor="capital" className="text-sm text-gray-300">Available Capital:</label>
            <select
              id="capital"
              value={selectedCapital}
              onChange={(e) => setSelectedCapital(Number(e.target.value))}
              className="bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value={10_000_000}>10M GP</option>
              <option value={25_000_000}>25M GP</option>
              <option value={50_000_000}>50M GP</option>
              <option value={100_000_000}>100M GP</option>
              <option value={250_000_000}>250M GP</option>
            </select>
          </div>
          
          {/* Refresh Button */}
          <button
            onClick={refreshData}
            disabled={refreshing}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Stats Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-gray-800 rounded-lg p-6 border border-gray-700"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">Active Strategies</p>
              <p className="text-2xl font-bold text-white">{stats.totalStrategies}</p>
            </div>
            <TrendingUp className="h-8 w-8 text-green-400" />
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-gray-800 rounded-lg p-6 border border-gray-700"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">Hourly Profit</p>
              <p className="text-2xl font-bold text-green-400">{formatGP(stats.totalHourlyProfit)}</p>
            </div>
            <Clock className="h-8 w-8 text-blue-400" />
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-gray-800 rounded-lg p-6 border border-gray-700"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">Success Rate</p>
              <p className="text-2xl font-bold text-yellow-400">{stats.averageSuccessRate.toFixed(1)}%</p>
            </div>
            <Target className="h-8 w-8 text-yellow-400" />
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="bg-gray-800 rounded-lg p-6 border border-gray-700"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">Capital Invested</p>
              <p className="text-2xl font-bold text-purple-400">{formatGP(stats.capitalInvested)}</p>
            </div>
            <DollarSign className="h-8 w-8 text-purple-400" />
          </div>
        </motion.div>
      </div>

      {/* Capital Progression Overview */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
      >
        <CapitalProgressionCard 
          tiers={progressionTiers}
          currentCapital={selectedCapital}
        />
      </motion.div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Left Column - Strategies and Opportunities */}
        <div className="space-y-6">
          {/* Top Strategies */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.5 }}
            className="bg-gray-800 rounded-lg p-6 border border-gray-700"
          >
            <h3 className="text-xl font-semibold text-white mb-4">Top Money Making Strategies</h3>
            <div className="space-y-4">
              {strategies.slice(0, 3).map((strategy, index) => (
                <StrategyCard
                  key={strategy.id}
                  strategy={strategy}
                  rank={index + 1}
                />
              ))}
            </div>
            {strategies.length === 0 && (
              <p className="text-gray-400 text-center py-4">
                No strategies found for {formatGP(selectedCapital)} capital range
              </p>
            )}
          </motion.div>

        </div>

        {/* Right Column - Tools and Advisor */}
        <div className="space-y-6">
          {/* GE Tax Calculator */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.7 }}
          >
            <GETaxCalculator />
          </motion.div>

          {/* Capital Progression Advisor */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.8 }}
          >
            <CapitalProgressionAdvisor currentCapital={selectedCapital} />
          </motion.div>
        </div>
      </div>

      {/* Additional Features Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.9 }}
        className="bg-gradient-to-r from-blue-900/20 to-purple-900/20 rounded-lg p-6 border border-gray-700"
      >
        <h3 className="text-xl font-semibold text-white mb-4">Advanced Money Making Features</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="text-center p-4">
            <div className="w-12 h-12 bg-green-600 rounded-lg mx-auto mb-3 flex items-center justify-center">
              <TrendingUp className="h-6 w-6 text-white" />
            </div>
            <h4 className="text-lg font-medium text-white mb-2">Bond Flipping</h4>
            <p className="text-gray-400 text-sm">Tax-exempt high-value trades with Old School Bonds</p>
          </div>
          
          <div className="text-center p-4">
            <div className="w-12 h-12 bg-blue-600 rounded-lg mx-auto mb-3 flex items-center justify-center">
              <RefreshCw className="h-6 w-6 text-white" />
            </div>
            <h4 className="text-lg font-medium text-white mb-2">Potion Decanting</h4>
            <p className="text-gray-400 text-sm">40M+ profit from dose arbitrage opportunities</p>
          </div>
          
          <div className="text-center p-4">
            <div className="w-12 h-12 bg-purple-600 rounded-lg mx-auto mb-3 flex items-center justify-center">
              <Target className="h-6 w-6 text-white" />
            </div>
            <h4 className="text-lg font-medium text-white mb-2">Set Combining</h4>
            <p className="text-gray-400 text-sm">Exploit lazy tax from complete armor sets</p>
          </div>
        </div>
      </motion.div>
    </div>
  );
};