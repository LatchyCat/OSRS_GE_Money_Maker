import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  ArrowLeft, 
  Edit, 
  Trash2,
  Plus,
  RefreshCw,
  Target,
  TrendingUp,
  Activity,
  Settings
} from 'lucide-react';
import { planningApi } from '../api/planningApi';
import { Button } from '../components/ui/Button';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { ProgressChart } from '../components/planning/ProgressChart';
import { StrategyList } from '../components/planning/StrategyList';
import { EditPlanModal } from '../components/planning/EditPlanModal';
import { UpdateProgressModal } from '../components/planning/UpdateProgressModal';
import { DeleteConfirmModal } from '../components/planning/DeleteConfirmModal';
import type { GoalPlan, ProgressUpdate } from '../types';

export const PlanDetail: React.FC = () => {
  const { planId } = useParams<{ planId: string }>();
  const navigate = useNavigate();
  
  const [plan, setPlan] = useState<GoalPlan | null>(null);
  const [progressHistory, setProgressHistory] = useState<ProgressUpdate[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  
  // Modal states
  const [showEditModal, setShowEditModal] = useState(false);
  const [showProgressModal, setShowProgressModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);

  const fetchPlanData = async (showRefreshSpinner = false) => {
    if (!planId) return;

    try {
      if (showRefreshSpinner) setRefreshing(true);
      
      const [planResult, progressResult] = await Promise.allSettled([
        planningApi.getGoalPlan(planId),
        planningApi.getProgressHistory(planId)
      ]);

      if (planResult.status === 'fulfilled') {
        setPlan(planResult.value);
      } else {
        console.error('Failed to load plan:', planResult.reason);
        navigate('/planning'); // Redirect if plan not found
        return;
      }

      if (progressResult.status === 'fulfilled') {
        setProgressHistory(progressResult.value);
      }
    } catch (error) {
      console.error('Error fetching plan data:', error);
      navigate('/planning');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchPlanData();
  }, [planId]);

  const handleEditPlan = async (updates: Partial<GoalPlan>) => {
    if (!plan || !planId) return;
    
    try {
      const updatedPlan = await planningApi.updateGoalPlan(planId, updates);
      setPlan(updatedPlan);
      
      // Regenerate strategies if significant changes
      if (updates.risk_tolerance !== plan.risk_tolerance || 
          updates.goal_gp !== plan.goal_gp || 
          updates.current_gp !== plan.current_gp) {
        await planningApi.regenerateStrategies(planId);
        fetchPlanData(); // Reload to get new strategies
      }
    } catch (error) {
      console.error('Error updating plan:', error);
      throw error;
    }
  };

  const handleUpdateProgress = async (data: { current_gp: number; market_notes?: string }) => {
    if (!planId) return;
    
    try {
      await planningApi.updateProgress(planId, data);
      fetchPlanData(); // Reload to get updated progress
    } catch (error) {
      console.error('Error updating progress:', error);
      throw error;
    }
  };

  const handleDeletePlan = async () => {
    if (!planId) return;
    
    try {
      await planningApi.deleteGoalPlan(planId);
      navigate('/planning');
    } catch (error) {
      console.error('Error deleting plan:', error);
      throw error;
    }
  };

  const handleRegenerateStrategies = async () => {
    if (!planId) return;
    
    try {
      setRefreshing(true);
      await planningApi.regenerateStrategies(planId);
      fetchPlanData();
    } catch (error) {
      console.error('Error regenerating strategies:', error);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <LoadingSpinner size="lg" text="Loading plan details..." />
      </div>
    );
  }

  if (!plan) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center space-y-4">
          <Target className="w-16 h-16 text-gray-400 mx-auto" />
          <h2 className="text-xl font-semibold text-white">Plan Not Found</h2>
          <p className="text-gray-400">The requested plan could not be found.</p>
          <Button 
            variant="primary"
            onClick={() => navigate('/planning')}
            icon={<ArrowLeft className="w-4 h-4" />}
          >
            Back to Planning
          </Button>
        </div>
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
        <div className="flex items-center gap-4">
          <Button
            variant="secondary"
            onClick={() => navigate('/planning')}
            icon={<ArrowLeft className="w-4 h-4" />}
          >
            Back
          </Button>
          <div>
            <h1 className="text-3xl font-bold text-white">
              Goal Plan #{plan.plan_id.slice(0, 8)}
            </h1>
            <p className="text-gray-400 mt-1">
              Track progress and manage your wealth-building strategy
            </p>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          <Button
            variant="secondary"
            onClick={() => fetchPlanData(true)}
            loading={refreshing}
            icon={<RefreshCw className="w-4 h-4" />}
            size="sm"
          >
            Refresh
          </Button>
          <Button
            variant="secondary"
            onClick={() => setShowProgressModal(true)}
            icon={<Plus className="w-4 h-4" />}
            size="sm"
          >
            Update Progress
          </Button>
          <div className="relative group">
            <Button
              variant="secondary"
              icon={<Settings className="w-4 h-4" />}
              size="sm"
            >
              Actions
            </Button>
            <div className="absolute right-0 top-full mt-2 w-48 bg-gray-800 border border-white/20 rounded-lg shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-10">
              <button
                onClick={() => setShowEditModal(true)}
                className="flex items-center gap-2 w-full px-3 py-2 text-sm text-white hover:bg-white/10 rounded-t-lg"
              >
                <Edit className="w-4 h-4" />
                Edit Plan
              </button>
              <button
                onClick={handleRegenerateStrategies}
                className="flex items-center gap-2 w-full px-3 py-2 text-sm text-white hover:bg-white/10"
              >
                <TrendingUp className="w-4 h-4" />
                Regenerate Strategies
              </button>
              <div className="border-t border-white/20 my-1" />
              <button
                onClick={() => setShowDeleteModal(true)}
                className="flex items-center gap-2 w-full px-3 py-2 text-sm text-red-400 hover:bg-red-500/10 rounded-b-lg"
              >
                <Trash2 className="w-4 h-4" />
                Delete Plan
              </button>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Progress Overview */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
      >
        <ProgressChart 
          plan={plan} 
          progressHistory={progressHistory}
        />
      </motion.div>

      {/* Strategies */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
      >
        <StrategyList 
          strategies={plan.strategies || []}
          onStrategySelect={(strategy) => {
            // Navigate to strategy detail view (could be implemented later)
            console.log('Selected strategy:', strategy);
          }}
          onCompareStrategies={() => {
            // Navigate to strategy comparison view (could be implemented later)
            console.log('Compare strategies');
          }}
        />
      </motion.div>

      {/* Modals */}
      <EditPlanModal
        plan={plan}
        isOpen={showEditModal}
        onClose={() => setShowEditModal(false)}
        onSave={handleEditPlan}
      />

      <UpdateProgressModal
        plan={plan}
        isOpen={showProgressModal}
        onClose={() => setShowProgressModal(false)}
        onUpdate={handleUpdateProgress}
      />

      <DeleteConfirmModal
        plan={plan}
        isOpen={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        onConfirm={handleDeletePlan}
      />
    </div>
  );
};