import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  X, 
  Trash2, 
  AlertTriangle,
  Target,
  Calendar,
  TrendingUp
} from 'lucide-react';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import type { GoalPlan } from '../../types';

interface DeleteConfirmModalProps {
  plan: GoalPlan;
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => Promise<void>;
}

export const DeleteConfirmModal: React.FC<DeleteConfirmModalProps> = ({
  plan,
  isOpen,
  onClose,
  onConfirm
}) => {
  const [loading, setLoading] = useState(false);
  const [confirmText, setConfirmText] = useState('');

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
      month: 'long',
      day: 'numeric',
      year: 'numeric'
    });
  };

  const handleDelete = async () => {
    setLoading(true);
    try {
      await onConfirm();
      onClose();
    } catch (error) {
      console.error('Error deleting plan:', error);
    } finally {
      setLoading(false);
    }
  };

  const isConfirmValid = confirmText.toLowerCase() === 'delete';
  const planId = plan.plan_id.slice(0, 8);

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
                <div className="p-2 bg-red-500/20 rounded-lg">
                  <Trash2 className="w-6 h-6 text-red-400" />
                </div>
                <div>
                  <h2 className="text-xl font-semibold text-white">Delete Goal Plan</h2>
                  <p className="text-gray-400 text-sm">
                    This action cannot be undone
                  </p>
                </div>
              </div>
              <Button
                variant="ghost"
                onClick={onClose}
                icon={<X className="w-4 h-4" />}
              />
            </div>

            {/* Warning */}
            <div className="bg-red-500/10 border-2 border-red-500/20 rounded-lg p-4 flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
              <div>
                <div className="text-red-400 font-semibold text-sm mb-2">
                  Permanent Deletion Warning
                </div>
                <div className="text-gray-300 text-sm space-y-1">
                  <p>You are about to permanently delete this goal plan and all associated data:</p>
                  <ul className="list-disc list-inside ml-4 space-y-1">
                    <li>All investment strategies ({plan.strategies?.length || 0} strategies)</li>
                    <li>Progress history and tracking data</li>
                    <li>Market analysis and recommendations</li>
                    <li>Time-based performance metrics</li>
                  </ul>
                </div>
              </div>
            </div>

            {/* Plan Summary */}
            <div className="bg-white/5 border border-white/10 rounded-lg p-4 space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Target className="w-4 h-4 text-accent-400" />
                  <span className="text-white font-medium">Plan #{planId}</span>
                </div>
                <Badge variant={
                  plan.completion_percentage >= 100 ? 'success' :
                  plan.is_active ? 'warning' : 'secondary'
                }>
                  {plan.completion_percentage >= 100 ? 'Completed' :
                   plan.is_active ? 'Active' : 'Inactive'}
                </Badge>
              </div>

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

              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-400">Progress</span>
                  <span className="text-white font-semibold">
                    {plan.completion_percentage.toFixed(1)}%
                  </span>
                </div>
                <div className="w-full bg-white/10 rounded-full h-2">
                  <div 
                    className="bg-accent-500 h-2 rounded-full"
                    style={{ width: `${Math.min(plan.completion_percentage, 100)}%` }}
                  />
                </div>
              </div>

              <div className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2 text-gray-400">
                  <Calendar className="w-3 h-3" />
                  <span>Created</span>
                </div>
                <span className="text-white">{formatDate(plan.created_at)}</span>
              </div>

              {plan.strategies && plan.strategies.length > 0 && (
                <div className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-2 text-gray-400">
                    <TrendingUp className="w-3 h-3" />
                    <span>Strategies</span>
                  </div>
                  <span className="text-white">{plan.strategies.length} generated</span>
                </div>
              )}

              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-400">Risk Tolerance</span>
                <span className={`font-medium ${
                  plan.risk_tolerance === 'conservative' ? 'text-green-400' :
                  plan.risk_tolerance === 'moderate' ? 'text-yellow-400' : 'text-red-400'
                }`}>
                  {plan.risk_tolerance}
                </span>
              </div>
            </div>

            {/* Confirmation Input */}
            <div className="space-y-3">
              <label className="block text-sm font-medium text-gray-300">
                Type <span className="text-red-400 font-bold">DELETE</span> to confirm deletion:
              </label>
              <input
                type="text"
                value={confirmText}
                onChange={(e) => setConfirmText(e.target.value)}
                placeholder="Type DELETE to confirm"
                className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent"
                autoComplete="off"
              />
              {confirmText && !isConfirmValid && (
                <p className="text-red-400 text-sm">
                  Please type "DELETE" exactly to confirm
                </p>
              )}
            </div>

            {/* Impact Notice */}
            <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-3 flex items-start gap-3">
              <AlertTriangle className="w-4 h-4 text-yellow-400 flex-shrink-0 mt-0.5" />
              <div className="text-sm text-gray-300">
                <div className="text-yellow-400 font-semibold mb-1">
                  Consider These Alternatives
                </div>
                <ul className="space-y-1 text-xs">
                  <li>• Mark the plan as inactive instead of deleting</li>
                  <li>• Export your progress data before deletion</li>
                  <li>• Create a new plan based on this one's successful strategies</li>
                </ul>
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center justify-between">
              <Button
                variant="secondary"
                onClick={onClose}
              >
                Cancel
              </Button>

              <Button
                variant="danger"
                onClick={handleDelete}
                loading={loading}
                disabled={!isConfirmValid || loading}
                icon={<Trash2 className="w-4 h-4" />}
              >
                Delete Plan Permanently
              </Button>
            </div>
          </Card>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};