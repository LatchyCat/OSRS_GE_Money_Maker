import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  X, 
  TrendingUp, 
  DollarSign, 
  MessageSquare,
  Save,
  Calculator,
  AlertCircle,
  CheckCircle
} from 'lucide-react';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Badge } from '../ui/Badge';
import type { GoalPlan, UpdateProgressRequest } from '../../types';

interface UpdateProgressModalProps {
  plan: GoalPlan;
  isOpen: boolean;
  onClose: () => void;
  onUpdate: (data: UpdateProgressRequest) => Promise<void>;
}

export const UpdateProgressModal: React.FC<UpdateProgressModalProps> = ({
  plan,
  isOpen,
  onClose,
  onUpdate
}) => {
  const [formData, setFormData] = useState({
    current_gp: plan.current_gp.toString(),
    market_notes: ''
  });
  const [loading, setLoading] = useState(false);

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

  const calculateProgress = () => {
    const currentGP = parseInt(formData.current_gp) || 0;
    const profitMade = currentGP - plan.current_gp;
    const totalNeeded = plan.goal_gp - plan.current_gp;
    const newCompletionPercentage = totalNeeded > 0 ? (profitMade / totalNeeded) * 100 : 0;
    const remainingProfit = Math.max(0, plan.goal_gp - currentGP);

    return {
      profitMade,
      newCompletionPercentage: Math.min(Math.max(newCompletionPercentage, 0), 100),
      remainingProfit,
      isProgressPositive: profitMade > 0,
      isGoalReached: currentGP >= plan.goal_gp
    };
  };

  const progress = calculateProgress();

  const handleSubmit = async () => {
    setLoading(true);
    try {
      await onUpdate({
        current_gp: parseInt(formData.current_gp),
        market_notes: formData.market_notes.trim() || undefined
      });
      onClose();
    } catch (error) {
      console.error('Error updating progress:', error);
    } finally {
      setLoading(false);
    }
  };

  const getProgressIndicator = () => {
    if (progress.isGoalReached) {
      return {
        icon: <CheckCircle className="w-5 h-5 text-green-400" />,
        text: 'Goal Achieved!',
        color: 'text-green-400',
        bgColor: 'bg-green-500/10 border-green-500/20'
      };
    } else if (progress.isProgressPositive) {
      return {
        icon: <TrendingUp className="w-5 h-5 text-blue-400" />,
        text: 'Making Progress',
        color: 'text-blue-400',
        bgColor: 'bg-blue-500/10 border-blue-500/20'
      };
    } else if (progress.profitMade < 0) {
      return {
        icon: <AlertCircle className="w-5 h-5 text-red-400" />,
        text: 'Losses Recorded',
        color: 'text-red-400',
        bgColor: 'bg-red-500/10 border-red-500/20'
      };
    } else {
      return {
        icon: <Calculator className="w-5 h-5 text-gray-400" />,
        text: 'No Change',
        color: 'text-gray-400',
        bgColor: 'bg-gray-500/10 border-gray-500/20'
      };
    }
  };

  const indicator = getProgressIndicator();

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.9 }}
          className="w-full max-w-lg max-h-[90vh] overflow-y-auto"
        >
          <Card className="p-6 space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <TrendingUp className="w-6 h-6 text-accent-400" />
                <div>
                  <h2 className="text-xl font-semibold text-white">Update Progress</h2>
                  <p className="text-gray-400 text-sm">
                    Record your current GP and track your progress
                  </p>
                </div>
              </div>
              <Button
                variant="ghost"
                onClick={onClose}
                icon={<X className="w-4 h-4" />}
              />
            </div>

            {/* Current Status */}
            <div className="bg-white/5 rounded-lg p-4 space-y-3">
              <div className="text-sm text-gray-400 text-center">Current Plan Status</div>
              <div className="grid grid-cols-3 gap-4 text-center">
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
                <div>
                  <div className="text-xs text-gray-400 uppercase tracking-wider mb-1">
                    Progress
                  </div>
                  <div className="text-sm font-semibold text-purple-400">
                    {plan.completion_percentage.toFixed(1)}%
                  </div>
                </div>
              </div>
            </div>

            {/* Form */}
            <div className="space-y-6">
              {/* New Current GP */}
              <div>
                <Input
                  label="Updated Current GP"
                  type="number"
                  value={formData.current_gp}
                  onChange={(e) => setFormData(prev => ({ ...prev, current_gp: e.target.value }))}
                  placeholder={plan.current_gp.toString()}
                  min="0"
                />
                {formData.current_gp && (
                  <div className="mt-2 text-sm text-blue-400">
                    {formatGP(parseInt(formData.current_gp))}
                  </div>
                )}
              </div>

              {/* Market Notes */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Market Notes (Optional)
                </label>
                <textarea
                  value={formData.market_notes}
                  onChange={(e) => setFormData(prev => ({ ...prev, market_notes: e.target.value }))}
                  placeholder="Any observations about market conditions, successful strategies, or challenges faced..."
                  rows={3}
                  className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-accent-500 focus:border-transparent resize-none"
                />
                <div className="text-xs text-gray-400 mt-1">
                  {formData.market_notes.length}/500 characters
                </div>
              </div>
            </div>

            {/* Progress Preview */}
            <div className={`rounded-lg border-2 p-4 space-y-4 ${indicator.bgColor}`}>
              <div className="flex items-center gap-2">
                {indicator.icon}
                <span className={`font-semibold ${indicator.color}`}>
                  {indicator.text}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="text-xs text-gray-400 uppercase tracking-wider mb-1">
                    Profit Made
                  </div>
                  <div className={`text-lg font-bold ${
                    progress.profitMade > 0 ? 'text-green-400' : 
                    progress.profitMade < 0 ? 'text-red-400' : 'text-gray-400'
                  }`}>
                    {progress.profitMade > 0 ? '+' : ''}{formatGP(progress.profitMade)}
                  </div>
                </div>

                <div>
                  <div className="text-xs text-gray-400 uppercase tracking-wider mb-1">
                    New Progress
                  </div>
                  <div className="text-lg font-bold text-accent-400">
                    {progress.newCompletionPercentage.toFixed(1)}%
                  </div>
                </div>
              </div>

              <div>
                <div className="text-xs text-gray-400 uppercase tracking-wider mb-2">
                  Remaining to Goal
                </div>
                <div className="text-lg font-bold text-purple-400">
                  {formatGP(progress.remainingProfit)}
                </div>
              </div>

              {/* Progress Bar */}
              <div className="space-y-2">
                <div className="flex justify-between text-xs">
                  <span className="text-gray-400">Progress</span>
                  <span className="text-white font-semibold">
                    {progress.newCompletionPercentage.toFixed(1)}%
                  </span>
                </div>
                <div className="w-full bg-white/10 rounded-full h-2">
                  <motion.div 
                    className="bg-accent-500 h-2 rounded-full transition-all"
                    initial={{ width: `${plan.completion_percentage}%` }}
                    animate={{ width: `${Math.min(progress.newCompletionPercentage, 100)}%` }}
                    transition={{ duration: 0.5, ease: "easeOut" }}
                  />
                </div>
              </div>
            </div>

            {/* Achievement Badge */}
            {progress.isGoalReached && (
              <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                className="text-center p-4 bg-green-500/10 border border-green-500/20 rounded-lg"
              >
                <CheckCircle className="w-12 h-12 text-green-400 mx-auto mb-2" />
                <h3 className="text-lg font-bold text-green-400 mb-1">
                  Congratulations!
                </h3>
                <p className="text-sm text-gray-300">
                  You've reached your GP goal! Time to set a new target.
                </p>
              </motion.div>
            )}

            {/* Actions */}
            <div className="flex items-center justify-between">
              <Button
                variant="secondary"
                onClick={onClose}
              >
                Cancel
              </Button>

              <Button
                variant="primary"
                onClick={handleSubmit}
                loading={loading}
                disabled={loading || formData.current_gp === plan.current_gp.toString()}
                icon={<Save className="w-4 h-4" />}
              >
                Update Progress
              </Button>
            </div>
          </Card>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};