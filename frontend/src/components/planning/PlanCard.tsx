import React from 'react';
import { motion } from 'framer-motion';
import { 
  Target, 
  TrendingUp, 
  Clock, 
  DollarSign,
  CheckCircle,
  AlertCircle,
  Activity,
  Calendar
} from 'lucide-react';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import type { GoalPlan } from '../../types';

interface PlanCardProps {
  plan: GoalPlan;
  onClick?: () => void;
}

export const PlanCard: React.FC<PlanCardProps> = ({ plan, onClick }) => {
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

  const getRiskColor = (risk: string) => {
    switch (risk) {
      case 'conservative': return 'text-green-400';
      case 'moderate': return 'text-yellow-400';
      case 'aggressive': return 'text-red-400';
      default: return 'text-gray-400';
    }
  };

  const getStatusBadge = () => {
    if (plan.completion_percentage >= 100) {
      return <Badge variant="success">Completed</Badge>;
    } else if (plan.is_active) {
      return <Badge variant="warning">Active</Badge>;
    } else {
      return <Badge variant="secondary">Inactive</Badge>;
    }
  };

  const getProgressColor = () => {
    if (plan.completion_percentage >= 100) return 'bg-green-500';
    if (plan.completion_percentage >= 75) return 'bg-blue-500';
    if (plan.completion_percentage >= 50) return 'bg-yellow-500';
    if (plan.completion_percentage >= 25) return 'bg-orange-500';
    return 'bg-red-500';
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  };

  const getRecommendedStrategy = () => {
    return plan.strategies?.find(s => s.is_recommended);
  };

  const recommendedStrategy = getRecommendedStrategy();

  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      className="h-full"
    >
      <Card 
        className="p-6 space-y-4 cursor-pointer hover:border-accent-500/50 transition-all h-full flex flex-col"
        onClick={onClick}
      >
        {/* Header */}
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2">
            <Target className="w-5 h-5 text-accent-400" />
            <h3 className="text-lg font-semibold text-white">
              Goal Plan #{plan.plan_id.slice(0, 8)}
            </h3>
          </div>
          {getStatusBadge()}
        </div>

        {/* Progress */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-400">Progress</span>
            <span className="text-white font-semibold">
              {plan.completion_percentage.toFixed(1)}%
            </span>
          </div>
          <div className="w-full bg-white/10 rounded-full h-2">
            <div 
              className={`h-2 rounded-full transition-all ${getProgressColor()}`}
              style={{ width: `${Math.min(plan.completion_percentage, 100)}%` }}
            />
          </div>
        </div>

        {/* GP Information */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <div className="text-xs text-gray-400 uppercase tracking-wider mb-1">
              Current GP
            </div>
            <div className="text-sm font-semibold text-blue-400">
              {formatGP(plan.current_gp)}
            </div>
          </div>
          <div>
            <div className="text-xs text-gray-400 uppercase tracking-wider mb-1">
              Goal GP
            </div>
            <div className="text-sm font-semibold text-green-400">
              {formatGP(plan.goal_gp)}
            </div>
          </div>
        </div>

        {/* Profit Needed */}
        <div className="bg-accent-500/10 border border-accent-500/20 rounded-lg p-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <DollarSign className="w-4 h-4 text-accent-400" />
              <span className="text-sm text-gray-400">Profit Needed</span>
            </div>
            <span className="text-sm font-bold text-accent-400">
              {formatGP(plan.profit_needed)}
            </span>
          </div>
        </div>

        {/* Strategy Info */}
        {recommendedStrategy && (
          <div className="bg-white/5 rounded-lg p-3 space-y-2">
            <div className="flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-purple-400" />
              <span className="text-sm font-semibold text-white">
                Recommended Strategy
              </span>
            </div>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div>
                <span className="text-gray-400">Type:</span>
                <span className="text-white ml-1 font-medium">
                  {recommendedStrategy.strategy_type}
                </span>
              </div>
              <div>
                <span className="text-gray-400">ROI:</span>
                <span className="text-green-400 ml-1 font-medium">
                  {recommendedStrategy.roi_percentage.toFixed(1)}%
                </span>
              </div>
              <div>
                <span className="text-gray-400">Risk:</span>
                <span className={`ml-1 font-medium ${getRiskColor(recommendedStrategy.risk_level)}`}>
                  {recommendedStrategy.risk_level}
                </span>
              </div>
              <div>
                <span className="text-gray-400">Timeline:</span>
                <span className="text-blue-400 ml-1 font-medium">
                  {recommendedStrategy.estimated_days}d
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Risk Tolerance */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${
              plan.risk_tolerance === 'conservative' ? 'bg-green-400' :
              plan.risk_tolerance === 'moderate' ? 'bg-yellow-400' : 'bg-red-400'
            }`} />
            <span className="text-sm text-gray-400">Risk Tolerance</span>
          </div>
          <span className={`text-sm font-medium ${getRiskColor(plan.risk_tolerance)}`}>
            {plan.risk_tolerance}
          </span>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between pt-2 border-t border-white/10 mt-auto">
          <div className="flex items-center gap-2 text-xs text-gray-400">
            <Calendar className="w-3 h-3" />
            <span>Created {formatDate(plan.created_at)}</span>
          </div>
          
          <div className="flex items-center gap-1">
            {plan.is_achievable ? (
              <CheckCircle className="w-4 h-4 text-green-400" />
            ) : (
              <AlertCircle className="w-4 h-4 text-yellow-400" />
            )}
            <span className="text-xs text-gray-400">
              {plan.is_achievable ? 'Achievable' : 'Challenging'}
            </span>
          </div>
        </div>
      </Card>
    </motion.div>
  );
};