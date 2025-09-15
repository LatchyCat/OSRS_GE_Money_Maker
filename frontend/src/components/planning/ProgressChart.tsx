import React from 'react';
import { motion } from 'framer-motion';
import { 
  TrendingUp, 
  Calendar, 
  Target, 
  Clock,
  CheckCircle,
  AlertCircle,
  Activity
} from 'lucide-react';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import type { GoalPlan, ProgressUpdate } from '../../types';

interface ProgressChartProps {
  plan: GoalPlan;
  progressHistory?: ProgressUpdate[];
}

export const ProgressChart: React.FC<ProgressChartProps> = ({ 
  plan, 
  progressHistory = [] 
}) => {
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

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric'
    });
  };

  const getProgressColor = () => {
    if (plan.completion_percentage >= 100) return 'bg-green-500';
    if (plan.completion_percentage >= 75) return 'bg-blue-500';
    if (plan.completion_percentage >= 50) return 'bg-yellow-500';
    if (plan.completion_percentage >= 25) return 'bg-orange-500';
    return 'bg-red-500';
  };

  const getStatusIndicator = () => {
    if (plan.completion_percentage >= 100) {
      return {
        icon: <CheckCircle className="w-5 h-5 text-green-400" />,
        text: 'Goal Achieved!',
        color: 'text-green-400'
      };
    } else if (plan.is_active) {
      return {
        icon: <Activity className="w-5 h-5 text-blue-400" />,
        text: 'In Progress',
        color: 'text-blue-400'
      };
    } else {
      return {
        icon: <AlertCircle className="w-5 h-5 text-yellow-400" />,
        text: 'Inactive',
        color: 'text-yellow-400'
      };
    }
  };

  const status = getStatusIndicator();
  const daysElapsed = Math.floor((new Date().getTime() - new Date(plan.created_at).getTime()) / (1000 * 60 * 60 * 24));
  const recommendedStrategy = plan.strategies?.find(s => s.is_recommended);

  // Create progress milestones
  const milestones = [
    { percentage: 25, label: '25%', achieved: plan.completion_percentage >= 25 },
    { percentage: 50, label: '50%', achieved: plan.completion_percentage >= 50 },
    { percentage: 75, label: '75%', achieved: plan.completion_percentage >= 75 },
    { percentage: 100, label: 'Goal!', achieved: plan.completion_percentage >= 100 }
  ];

  return (
    <div className="space-y-6">
      {/* Progress Overview */}
      <Card className="p-6 space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Target className="w-6 h-6 text-accent-400" />
            <h2 className="text-xl font-semibold text-white">Progress Overview</h2>
          </div>
          <div className="flex items-center gap-2">
            {status.icon}
            <span className={`font-medium ${status.color}`}>{status.text}</span>
          </div>
        </div>

        {/* Main Progress Bar */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-gray-400">Overall Progress</span>
            <span className="text-xl font-bold text-white">
              {plan.completion_percentage.toFixed(1)}%
            </span>
          </div>
          
          <div className="relative">
            <div className="w-full bg-white/10 rounded-full h-4">
              <motion.div 
                className={`h-4 rounded-full transition-all ${getProgressColor()}`}
                initial={{ width: 0 }}
                animate={{ width: `${Math.min(plan.completion_percentage, 100)}%` }}
                transition={{ duration: 1, ease: "easeOut" }}
              />
            </div>
            
            {/* Progress Milestones */}
            <div className="flex justify-between mt-2">
              {milestones.map((milestone, index) => (
                <div key={index} className="flex flex-col items-center">
                  <div className={`w-3 h-3 rounded-full border-2 ${
                    milestone.achieved 
                      ? 'bg-green-400 border-green-400' 
                      : 'bg-transparent border-white/30'
                  }`} />
                  <span className={`text-xs mt-1 ${
                    milestone.achieved ? 'text-green-400' : 'text-gray-400'
                  }`}>
                    {milestone.label}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Key Metrics */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-3 text-center">
            <div className="text-xs text-gray-400 uppercase tracking-wider mb-1">
              Current GP
            </div>
            <div className="text-lg font-bold text-blue-400">
              {formatGP(plan.current_gp)}
            </div>
          </div>

          <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-3 text-center">
            <div className="text-xs text-gray-400 uppercase tracking-wider mb-1">
              Goal GP
            </div>
            <div className="text-lg font-bold text-green-400">
              {formatGP(plan.goal_gp)}
            </div>
          </div>

          <div className="bg-purple-500/10 border border-purple-500/20 rounded-lg p-3 text-center">
            <div className="text-xs text-gray-400 uppercase tracking-wider mb-1">
              Remaining
            </div>
            <div className="text-lg font-bold text-purple-400">
              {formatGP(plan.profit_needed)}
            </div>
          </div>

          <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-3 text-center">
            <div className="text-xs text-gray-400 uppercase tracking-wider mb-1">
              Days Active
            </div>
            <div className="text-lg font-bold text-yellow-400">
              {daysElapsed}
            </div>
          </div>
        </div>
      </Card>

      {/* Timeline & Strategy Info */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Timeline */}
        <Card className="p-6 space-y-4">
          <div className="flex items-center gap-2">
            <Calendar className="w-5 h-5 text-accent-400" />
            <h3 className="text-lg font-semibold text-white">Timeline</h3>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-gray-400">Created</span>
              <span className="text-white">{formatDate(plan.created_at)}</span>
            </div>
            
            <div className="flex items-center justify-between">
              <span className="text-gray-400">Last Updated</span>
              <span className="text-white">{formatDate(plan.updated_at)}</span>
            </div>
            
            {recommendedStrategy && (
              <div className="flex items-center justify-between">
                <span className="text-gray-400">Est. Completion</span>
                <div className="flex items-center gap-2">
                  <Clock className="w-4 h-4 text-blue-400" />
                  <span className="text-blue-400 font-medium">
                    {recommendedStrategy.estimated_days} days
                  </span>
                </div>
              </div>
            )}

            <div className="flex items-center justify-between">
              <span className="text-gray-400">Status</span>
              <Badge variant={
                plan.completion_percentage >= 100 ? 'success' :
                plan.is_active ? 'warning' : 'secondary'
              }>
                {plan.completion_percentage >= 100 ? 'Completed' :
                 plan.is_active ? 'Active' : 'Inactive'}
              </Badge>
            </div>
          </div>
        </Card>

        {/* Strategy Performance */}
        {recommendedStrategy && (
          <Card className="p-6 space-y-4">
            <div className="flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-accent-400" />
              <h3 className="text-lg font-semibold text-white">Current Strategy</h3>
            </div>

            <div className="space-y-3">
              <div>
                <div className="text-sm text-gray-400">Strategy Type</div>
                <div className="text-white font-medium">{recommendedStrategy.strategy_type}</div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="text-sm text-gray-400">Expected ROI</div>
                  <div className="text-green-400 font-bold">
                    {recommendedStrategy.roi_percentage.toFixed(1)}%
                  </div>
                </div>
                <div>
                  <div className="text-sm text-gray-400">Risk Level</div>
                  <div className={`font-medium ${
                    recommendedStrategy.risk_level === 'conservative' ? 'text-green-400' :
                    recommendedStrategy.risk_level === 'moderate' ? 'text-yellow-400' : 'text-red-400'
                  }`}>
                    {recommendedStrategy.risk_level}
                  </div>
                </div>
              </div>

              <div>
                <div className="text-sm text-gray-400">Feasibility Score</div>
                <div className="flex items-center gap-2">
                  <div className="flex-1 bg-white/10 rounded-full h-2">
                    <div 
                      className="bg-accent-500 h-2 rounded-full transition-all"
                      style={{ width: `${recommendedStrategy.feasibility_score * 100}%` }}
                    />
                  </div>
                  <span className="text-accent-400 font-medium">
                    {(recommendedStrategy.feasibility_score * 100).toFixed(0)}%
                  </span>
                </div>
              </div>
            </div>
          </Card>
        )}
      </div>

      {/* Recent Progress Updates */}
      {progressHistory.length > 0 && (
        <Card className="p-6 space-y-4">
          <h3 className="text-lg font-semibold text-white flex items-center gap-2">
            <Activity className="w-5 h-5 text-accent-400" />
            Recent Updates
          </h3>

          <div className="space-y-3">
            {progressHistory.slice(0, 5).map((update, index) => (
              <motion.div
                key={update.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.1 * index }}
                className="flex items-start gap-3 p-3 bg-white/5 rounded-lg"
              >
                <div className={`w-2 h-2 rounded-full mt-2 ${
                  update.is_on_track ? 'bg-green-400' : 'bg-yellow-400'
                }`} />
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <span className="text-white font-medium">
                      {formatGP(update.profit_made)} profit made
                    </span>
                    <span className="text-gray-400 text-sm">
                      {formatDate(update.created_at)}
                    </span>
                  </div>
                  <div className="text-sm text-gray-400 mt-1">
                    {update.completion_percentage.toFixed(1)}% complete • 
                    {update.is_on_track ? ' On track' : ' Behind schedule'}
                  </div>
                  {update.market_notes && (
                    <div className="text-sm text-gray-300 mt-2 italic">
                      "{update.market_notes}"
                    </div>
                  )}
                </div>
              </motion.div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
};