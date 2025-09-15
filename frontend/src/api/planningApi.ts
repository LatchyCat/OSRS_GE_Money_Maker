import { apiClient } from './client';
import type { 
  GoalPlan, 
  Strategy, 
  MarketAnalysis, 
  GoalPlanStats,
  CreateGoalPlanRequest,
  UpdateProgressRequest,
  ProgressUpdate
} from '../types';

export const planningApi = {
  // Goal Plan Management
  getGoalPlans: async (): Promise<GoalPlan[]> => {
    const response = await apiClient.get<GoalPlan[]>('/planning/goal-plans/');
    return response.data;
  },

  createGoalPlan: async (data: CreateGoalPlanRequest): Promise<GoalPlan> => {
    const response = await apiClient.post<GoalPlan>('/planning/goal-plans/', data);
    return response.data;
  },

  getGoalPlan: async (planId: string): Promise<GoalPlan> => {
    const response = await apiClient.get<GoalPlan>(`/planning/goal-plans/${planId}/`);
    return response.data;
  },

  updateGoalPlan: async (planId: string, data: Partial<GoalPlan>): Promise<GoalPlan> => {
    const response = await apiClient.patch<GoalPlan>(`/planning/goal-plans/${planId}/`, data);
    return response.data;
  },

  deleteGoalPlan: async (planId: string): Promise<void> => {
    await apiClient.delete(`/planning/goal-plans/${planId}/`);
  },

  // Goal Plan Actions
  getStrategies: async (planId: string): Promise<Strategy[]> => {
    const response = await apiClient.get<Strategy[]>(`/planning/goal-plans/${planId}/strategies/`);
    return response.data;
  },

  getRecommendedStrategy: async (planId: string): Promise<Strategy> => {
    const response = await apiClient.get<Strategy>(`/planning/goal-plans/${planId}/recommended_strategy/`);
    return response.data;
  },

  updateProgress: async (planId: string, data: UpdateProgressRequest): Promise<ProgressUpdate> => {
    const response = await apiClient.post<ProgressUpdate>(`/planning/goal-plans/${planId}/update_progress/`, data);
    return response.data;
  },

  getProgressHistory: async (planId: string): Promise<ProgressUpdate[]> => {
    const response = await apiClient.get<ProgressUpdate[]>(`/planning/goal-plans/${planId}/progress_history/`);
    return response.data;
  },

  regenerateStrategies: async (planId: string): Promise<GoalPlan> => {
    const response = await apiClient.post<GoalPlan>(`/planning/goal-plans/${planId}/regenerate_strategies/`);
    return response.data;
  },

  // Strategy Analysis
  getStrategy: async (strategyId: number): Promise<Strategy> => {
    const response = await apiClient.get<Strategy>(`/planning/strategies/${strategyId}/`);
    return response.data;
  },

  compareStrategies: async (planId: string): Promise<any[]> => {
    const response = await apiClient.get(`/planning/goal-plans/${planId}/compare/`);
    return response.data;
  },

  getTimeAnalysis: async (strategyId: number): Promise<any> => {
    const response = await apiClient.get(`/planning/strategies/${strategyId}/time-analysis/`);
    return response.data;
  },

  // Market & Portfolio
  getMarketAnalysis: async (): Promise<MarketAnalysis> => {
    const response = await apiClient.get<MarketAnalysis>('/planning/market-analysis/');
    return response.data;
  },

  optimizePortfolio: async (data: {
    available_capital: number;
    required_profit: number;
    risk_tolerance: string;
    max_items?: number;
  }): Promise<any> => {
    const response = await apiClient.post('/planning/portfolio-optimization/', data);
    return response.data;
  },

  // Statistics
  getGoalPlanStats: async (): Promise<GoalPlanStats> => {
    const response = await apiClient.get<GoalPlanStats>('/planning/stats/');
    return response.data;
  }
};