import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  X, 
  Target, 
  DollarSign, 
  Shield, 
  AlertTriangle,
  Save
} from 'lucide-react';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Badge } from '../ui/Badge';
import type { GoalPlan, RiskLevel } from '../../types';

interface EditPlanModalProps {
  plan: GoalPlan;
  isOpen: boolean;
  onClose: () => void;
  onSave: (updates: Partial<GoalPlan>) => Promise<void>;
}

export const EditPlanModal: React.FC<EditPlanModalProps> = ({
  plan,
  isOpen,
  onClose,
  onSave
}) => {
  const [formData, setFormData] = useState({
    current_gp: plan.current_gp.toString(),
    goal_gp: plan.goal_gp.toString(),
    risk_tolerance: plan.risk_tolerance as RiskLevel,
    preferred_timeframe_days: plan.preferred_timeframe_days?.toString() || ''
  });
  const [loading, setSaving] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);

  useEffect(() => {
    const changes = 
      formData.current_gp !== plan.current_gp.toString() ||
      formData.goal_gp !== plan.goal_gp.toString() ||
      formData.risk_tolerance !== plan.risk_tolerance ||
      formData.preferred_timeframe_days !== (plan.preferred_timeframe_days?.toString() || '');
    
    setHasChanges(changes);
  }, [formData, plan]);

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

  const getRiskColor = (risk: RiskLevel) => {
    switch (risk) {
      case 'conservative': return 'text-green-400 border-green-500/50 bg-green-500/20';
      case 'moderate': return 'text-yellow-400 border-yellow-500/50 bg-yellow-500/20';
      case 'aggressive': return 'text-red-400 border-red-500/50 bg-red-500/20';
    }
  };

  const getRiskDescription = (risk: RiskLevel) => {
    switch (risk) {
      case 'conservative': return 'Lower risk, stable returns. Focus on proven profitable items.';
      case 'moderate': return 'Balanced approach with moderate risk tolerance.';
      case 'aggressive': return 'Higher risk, higher reward. Maximum profit potential.';
    }
  };

  const calculateNewProfit = () => {
    const current = parseInt(formData.current_gp) || 0;
    const goal = parseInt(formData.goal_gp) || 0;
    return Math.max(0, goal - current);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const updates: Partial<GoalPlan> = {
        current_gp: parseInt(formData.current_gp),
        goal_gp: parseInt(formData.goal_gp),
        risk_tolerance: formData.risk_tolerance,
        preferred_timeframe_days: formData.preferred_timeframe_days ? parseInt(formData.preferred_timeframe_days) : undefined
      };

      await onSave(updates);
      onClose();
    } catch (error) {
      console.error('Error updating plan:', error);
    } finally {
      setSaving(false);
    }
  };

  const handleClose = () => {
    if (hasChanges) {
      if (confirm('You have unsaved changes. Are you sure you want to close?')) {
        onClose();
      }
    } else {
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.9 }}
          className="w-full max-w-2xl max-h-[90vh] overflow-y-auto"
        >
          <Card className="p-6 space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Target className="w-6 h-6 text-accent-400" />
                <div>
                  <h2 className="text-xl font-semibold text-white">Edit Goal Plan</h2>
                  <p className="text-gray-400 text-sm">
                    Modify your plan parameters and regenerate strategies
                  </p>
                </div>
              </div>
              <Button
                variant="ghost"
                onClick={handleClose}
                icon={<X className="w-4 h-4" />}
              />
            </div>

            {/* Current vs New Comparison */}
            <div className="grid grid-cols-2 gap-4 p-4 bg-white/5 rounded-lg">
              <div className="text-center">
                <div className="text-sm text-gray-400 mb-2">Current Plan</div>
                <div className="space-y-2">
                  <div className="text-blue-400">{formatGP(plan.current_gp)}</div>
                  <div className="text-green-400">{formatGP(plan.goal_gp)}</div>
                  <div className="text-purple-400">{formatGP(plan.profit_needed)}</div>
                </div>
              </div>
              <div className="text-center">
                <div className="text-sm text-gray-400 mb-2">Updated Plan</div>
                <div className="space-y-2">
                  <div className="text-blue-400">{formatGP(parseInt(formData.current_gp) || 0)}</div>
                  <div className="text-green-400">{formatGP(parseInt(formData.goal_gp) || 0)}</div>
                  <div className="text-purple-400">{formatGP(calculateNewProfit())}</div>
                </div>
              </div>
            </div>

            {/* Form Fields */}
            <div className="space-y-6">
              {/* Current GP */}
              <div>
                <Input
                  label="Current GP"
                  type="number"
                  value={formData.current_gp}
                  onChange={(e) => setFormData(prev => ({ ...prev, current_gp: e.target.value }))}
                  placeholder="0"
                  min="0"
                />
                {formData.current_gp && (
                  <div className="mt-2 text-sm text-blue-400">
                    {formatGP(parseInt(formData.current_gp))}
                  </div>
                )}
              </div>

              {/* Goal GP */}
              <div>
                <Input
                  label="Goal GP"
                  type="number"
                  value={formData.goal_gp}
                  onChange={(e) => setFormData(prev => ({ ...prev, goal_gp: e.target.value }))}
                  placeholder="1000000"
                  min={parseInt(formData.current_gp) + 1 || 1}
                />
                {formData.goal_gp && (
                  <div className="mt-2 space-y-1">
                    <div className="text-sm text-green-400">
                      {formatGP(parseInt(formData.goal_gp))}
                    </div>
                    <div className="text-xs text-gray-400">
                      Profit needed: <span className="text-accent-400 font-semibold">
                        {formatGP(calculateNewProfit())}
                      </span>
                    </div>
                  </div>
                )}
              </div>

              {/* Risk Tolerance */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-3">
                  Risk Tolerance
                </label>
                <div className="grid gap-3">
                  {(['conservative', 'moderate', 'aggressive'] as RiskLevel[]).map((risk) => (
                    <motion.div
                      key={risk}
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      className={`border-2 rounded-xl p-4 cursor-pointer transition-all ${
                        formData.risk_tolerance === risk
                          ? getRiskColor(risk) + ' border-opacity-100'
                          : 'border-white/20 hover:border-white/40'
                      }`}
                      onClick={() => setFormData(prev => ({ ...prev, risk_tolerance: risk }))}
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <h3 className={`text-base font-semibold ${
                            formData.risk_tolerance === risk ? '' : 'text-white'
                          } capitalize`}>
                            {risk}
                          </h3>
                          <p className="text-gray-400 mt-1 text-sm">
                            {getRiskDescription(risk)}
                          </p>
                        </div>
                        {formData.risk_tolerance === risk && (
                          <Shield className="w-5 h-5 text-current" />
                        )}
                      </div>
                    </motion.div>
                  ))}
                </div>
              </div>

              {/* Optional Timeframe */}
              <div>
                <Input
                  label="Preferred Timeframe (days)"
                  type="number"
                  value={formData.preferred_timeframe_days}
                  onChange={(e) => setFormData(prev => ({ ...prev, preferred_timeframe_days: e.target.value }))}
                  placeholder="Optional - let AI determine optimal timeframe"
                  min="1"
                />
                <p className="text-xs text-gray-400 mt-1">
                  Leave empty to let the system determine the optimal timeframe based on your risk tolerance
                </p>
              </div>
            </div>

            {/* Impact Warning */}
            {hasChanges && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-4 flex items-start gap-3"
              >
                <AlertTriangle className="w-5 h-5 text-yellow-400 flex-shrink-0 mt-0.5" />
                <div>
                  <div className="text-yellow-400 font-semibold text-sm">
                    Strategy Regeneration Required
                  </div>
                  <div className="text-gray-300 text-sm mt-1">
                    Changing plan parameters will require regenerating investment strategies. 
                    This may take a moment to complete.
                  </div>
                </div>
              </motion.div>
            )}

            {/* Actions */}
            <div className="flex items-center justify-between">
              <Button
                variant="secondary"
                onClick={handleClose}
              >
                Cancel
              </Button>

              <div className="flex items-center gap-3">
                {hasChanges && (
                  <Badge variant="warning">
                    Unsaved Changes
                  </Badge>
                )}
                <Button
                  variant="primary"
                  onClick={handleSave}
                  loading={loading}
                  disabled={!hasChanges || loading}
                  icon={<Save className="w-4 h-4" />}
                >
                  Save Changes
                </Button>
              </div>
            </div>
          </Card>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};