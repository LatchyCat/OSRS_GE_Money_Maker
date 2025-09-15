import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { 
  Plus, 
  RefreshCw, 
  Target, 
  TrendingUp, 
  Filter,
  Clock,
  DollarSign,
  Activity
} from 'lucide-react';
import { planningApi } from '../api/planningApi';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { PlanCard } from '../components/planning/PlanCard';
import type { GoalPlan, MarketAnalysis } from '../types';

export const Planning: React.FC = () => {
  const navigate = useNavigate();
  const [goalPlans, setGoalPlans] = useState<GoalPlan[]>([]);
  const [marketAnalysis, setMarketAnalysis] = useState<MarketAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [filter, setFilter] = useState<'all' | 'active' | 'completed'>('all');

  const fetchPlanningData = async (showRefreshSpinner = false) => {
    try {
      if (showRefreshSpinner) setRefreshing(true);
      
      const [plansResult, marketResult] = await Promise.allSettled([
        planningApi.getGoalPlans(),
        planningApi.getMarketAnalysis()
      ]);

      if (plansResult.status === 'fulfilled') {
        setGoalPlans(Array.isArray(plansResult.value) ? plansResult.value : []);
      } else {
        console.error('Failed to fetch goal plans:', plansResult.reason);
        setGoalPlans([]);
      }

      if (marketResult.status === 'fulfilled') {
        setMarketAnalysis(marketResult.value);
      }
    } catch (error) {
      console.error('Error fetching planning data:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchPlanningData();
  }, []);

  const handleRefresh = () => {
    fetchPlanningData(true);
  };

  const filteredPlans = Array.isArray(goalPlans) ? goalPlans.filter(plan => {
    switch (filter) {
      case 'active': return plan.is_active && plan.completion_percentage < 100;
      case 'completed': return plan.completion_percentage >= 100;
      default: return true;
    }
  }) : [];

  const getFilterColor = (currentFilter: typeof filter) => {
    return filter === currentFilter 
      ? 'bg-accent-500 text-white' 
      : 'bg-white/10 text-gray-300 hover:bg-white/20';
  };

  const formatGP = (amount: number) => {
    if (amount >= 1000000000) {
      return `${(amount / 1000000000).toFixed(1)}B GP`;
    } else if (amount >= 1000000) {
      return `${(amount / 1000000).toFixed(1)}M GP`;
    } else if (amount >= 1000) {
      return `${(amount / 1000).toFixed(1)}K GP`;
    }
    return `${amount.toLocaleString()} GP`;
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <LoadingSpinner size="lg" text="Loading your goal plans..." />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4"
      >
        <div>
          <h1 className="text-3xl font-bold text-white">Goal Planning</h1>
          <p className="text-gray-400 mt-2">
            Track your wealth-building progress and optimize your strategies
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button
            variant="secondary"
            onClick={handleRefresh}
            loading={refreshing}
            icon={<RefreshCw className="w-4 h-4" />}
          >
            Refresh
          </Button>
          <Button
            variant="primary"
            onClick={() => navigate('/planning/create')}
            icon={<Plus className="w-4 h-4" />}
          >
            New Goal Plan
          </Button>
        </div>
      </motion.div>

      {/* Market Summary */}
      {marketAnalysis && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          <Card className="p-4 sm:p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                <Activity className="w-5 h-5 text-accent-400" />
                Market Overview
              </h2>
              <Badge variant={
                marketAnalysis.data_age_hours === 0 ? 'success' :
                marketAnalysis.data_age_hours < 1 ? 'warning' : 'danger'
              }>
                {marketAnalysis.data_age_hours === 0 ? 'Live Data' :
                 marketAnalysis.data_age_hours < 1 ? 'Recent' : `${marketAnalysis.data_age_hours}h old`}
              </Badge>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-accent-400">
                  {marketAnalysis.total_profitable_items}
                </div>
                <div className="text-sm text-gray-400">Profitable Items</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-green-400">
                  {marketAnalysis.average_profit_margin.toFixed(1)}%
                </div>
                <div className="text-sm text-gray-400">Avg Margin</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-purple-400">
                  {formatGP(marketAnalysis.highest_profit_amount)}
                </div>
                <div className="text-sm text-gray-400">Top Profit</div>
              </div>
              <div className="text-center">
                <div className={`text-2xl font-bold ${
                  marketAnalysis.recommended_risk_level === 'aggressive' ? 'text-red-400' :
                  marketAnalysis.recommended_risk_level === 'moderate' ? 'text-yellow-400' : 'text-green-400'
                }`}>
                  {marketAnalysis.recommended_risk_level}
                </div>
                <div className="text-sm text-gray-400">Risk Level</div>
              </div>
            </div>
          </Card>
        </motion.div>
      )}

      {/* Filter Tabs */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="flex items-center gap-2"
      >
        <Filter className="w-4 h-4 text-gray-400" />
        <div className="flex items-center gap-1">
          {(['all', 'active', 'completed'] as const).map((filterOption) => (
            <button
              key={filterOption}
              onClick={() => setFilter(filterOption)}
              className={`px-3 py-1 rounded-lg text-sm font-medium transition-all ${getFilterColor(filterOption)}`}
            >
              {filterOption.charAt(0).toUpperCase() + filterOption.slice(1)}
              {filterOption === 'all' && ` (${Array.isArray(goalPlans) ? goalPlans.length : 0})`}
              {filterOption === 'active' && ` (${Array.isArray(goalPlans) ? goalPlans.filter(p => p.is_active && p.completion_percentage < 100).length : 0})`}
              {filterOption === 'completed' && ` (${Array.isArray(goalPlans) ? goalPlans.filter(p => p.completion_percentage >= 100).length : 0})`}
            </button>
          ))}
        </div>
      </motion.div>

      {/* Goal Plans */}
      {filteredPlans.length === 0 ? (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
        >
          <Card className="text-center py-12">
            <div className="space-y-4">
              <div className="w-16 h-16 bg-accent-500/20 rounded-full flex items-center justify-center mx-auto">
                <Target className="w-8 h-8 text-accent-500" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-white">
                  {filter === 'all' ? 'No Goal Plans Yet' : `No ${filter.charAt(0).toUpperCase() + filter.slice(1)} Plans`}
                </h3>
                <p className="text-gray-400 mt-2">
                  {filter === 'all' 
                    ? 'Create your first goal plan to start tracking your OSRS wealth building progress'
                    : `You don't have any ${filter} plans at the moment`
                  }
                </p>
              </div>
              {filter === 'all' && (
                <Button 
                  variant="primary"
                  onClick={() => navigate('/planning/create')}
                  icon={<Plus className="w-4 h-4" />}
                >
                  Create Your First Goal Plan
                </Button>
              )}
            </div>
          </Card>
        </motion.div>
      ) : (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6"
        >
          {filteredPlans.map((plan, index) => (
            <motion.div
              key={plan.plan_id}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.1 * index }}
            >
              <PlanCard 
                plan={plan}
                onClick={() => navigate(`/planning/${plan.plan_id}`)}
              />
            </motion.div>
          ))}
        </motion.div>
      )}

      {/* Quick Stats */}
      {goalPlans.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="grid grid-cols-1 sm:grid-cols-3 gap-4 sm:gap-6"
        >
          <Card className="p-4 sm:p-6 space-y-3">
            <div className="flex items-center space-x-2">
              <Target className="w-5 h-5 text-blue-400" />
              <h3 className="text-lg font-semibold text-white">Total Plans</h3>
            </div>
            <div className="text-2xl font-bold text-blue-400">
              {goalPlans.length}
            </div>
            <p className="text-sm text-gray-400">
              Goal plans created
            </p>
          </Card>

          <Card className="p-4 sm:p-6 space-y-3">
            <div className="flex items-center space-x-2">
              <TrendingUp className="w-5 h-5 text-green-400" />
              <h3 className="text-lg font-semibold text-white">Active Plans</h3>
            </div>
            <div className="text-2xl font-bold text-green-400">
              {Array.isArray(goalPlans) ? goalPlans.filter(p => p.is_active && p.completion_percentage < 100).length : 0}
            </div>
            <p className="text-sm text-gray-400">
              Currently in progress
            </p>
          </Card>

          <Card className="p-4 sm:p-6 space-y-3">
            <div className="flex items-center space-x-2">
              <DollarSign className="w-5 h-5 text-purple-400" />
              <h3 className="text-lg font-semibold text-white">Total Goal Value</h3>
            </div>
            <div className="text-2xl font-bold text-purple-400">
              {formatGP(Array.isArray(goalPlans) ? goalPlans.reduce((sum, plan) => sum + plan.goal_gp, 0) : 0)}
            </div>
            <p className="text-sm text-gray-400">
              Combined goal amount
            </p>
          </Card>
        </motion.div>
      )}
    </div>
  );
};