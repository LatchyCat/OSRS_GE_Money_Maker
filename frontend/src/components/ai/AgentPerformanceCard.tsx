import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Zap, Brain, Layers, Activity, Clock, CheckCircle, AlertTriangle, TrendingUp, BarChart3 } from 'lucide-react';
import { Card } from '../ui/Card';
import { LoadingSpinner } from '../ui/LoadingSpinner';
import { aiApi } from '../../api/aiApi';
import type { MultiAgentPerformanceData } from '../../types/aiTypes';

// Using MultiAgentPerformanceData interface from aiApi.ts

interface AgentMetrics {
  active_tasks: number;
  total_completed: number;
  avg_response_time_ms: number;
  error_rate: number;
  capability_rating: number;
  speed_multiplier: number;
}

export const AgentPerformanceCard: React.FC = () => {
  const [performanceData, setPerformanceData] = useState<MultiAgentPerformanceData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchPerformanceData = async () => {
    try {
      const data = await aiApi.getPerformanceMetrics();
      setPerformanceData(data);
      setError(null);
    } catch (err) {
      console.error('Error fetching agent performance data:', err);
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPerformanceData();
    // Refresh every 30 seconds
    const interval = setInterval(fetchPerformanceData, 30000);
    return () => clearInterval(interval);
  }, []);

  const getAgentIcon = (agentKey: string) => {
    switch (agentKey) {
      case 'gemma3_fast':
        return <Zap className="w-5 h-5" />;
      case 'deepseek_smart':
        return <Brain className="w-5 h-5" />;
      case 'qwen3_coordinator':
        return <Layers className="w-5 h-5" />;
      default:
        return <Activity className="w-5 h-5" />;
    }
  };

  const getAgentMetrics = (agentKey: string): AgentMetrics | null => {
    if (!performanceData) return null;
    
    const agentMap = {
      'gemma3_fast': 'gemma3:1b',
      'deepseek_smart': 'deepseek-r1:1.5b',
      'qwen3_coordinator': 'qwen3:4b'
    };
    
    const metricsKey = agentMap[agentKey as keyof typeof agentMap];
    return performanceData.system_status.current_load.agents[metricsKey] || null;
  };

  const formatResponseTime = (ms: number): string => {
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  };

  const getHealthStatus = (agentKey: string) => {
    if (!performanceData) return { healthy: false, icon: AlertTriangle, color: 'text-gray-400' };
    
    const available = performanceData.system_status.agents_available[agentKey as keyof typeof performanceData.system_status.agents_available];
    const metrics = getAgentMetrics(agentKey);
    
    if (!available) {
      return { healthy: false, icon: AlertTriangle, color: 'text-red-400' };
    }
    
    if (metrics && metrics.error_rate < 0.1) {
      return { healthy: true, icon: CheckCircle, color: 'text-green-400' };
    }
    
    return { healthy: false, icon: AlertTriangle, color: 'text-yellow-400' };
  };

  if (loading) {
    return (
      <Card className="bg-gradient-to-br from-purple-500/10 via-blue-500/10 to-cyan-500/10 border-purple-500/20">
        <div className="flex items-center justify-center py-8">
          <LoadingSpinner size="sm" text="Loading agent status..." />
        </div>
      </Card>
    );
  }

  if (error || !performanceData) {
    return (
      <Card className="bg-gradient-to-br from-red-500/10 to-orange-500/10 border-red-500/20">
        <div className="flex items-center space-x-3 text-red-300">
          <AlertTriangle className="w-5 h-5" />
          <div>
            <h3 className="font-semibold">Agent Status Unavailable</h3>
            <p className="text-sm text-red-400">{error || 'Failed to load performance data'}</p>
          </div>
        </div>
      </Card>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="backdrop-blur-md bg-gradient-to-br from-purple-500/10 via-blue-500/10 to-cyan-500/10 border border-purple-500/20 rounded-xl p-6 space-y-6"
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-blue-600 rounded-lg flex items-center justify-center">
            <Activity className="w-5 h-5 text-white" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white">Multi-Agent System</h3>
            <div className="flex items-center space-x-2">
              <div className={`w-2 h-2 rounded-full ${performanceData.system_status.system_healthy ? 'bg-green-400' : 'bg-red-400'}`} />
              <p className="text-sm text-gray-400">
                {performanceData.system_status.system_healthy ? 'System Healthy' : 'System Issues'}
              </p>
            </div>
          </div>
        </div>
        <div className="text-xs text-gray-400">
          Updated: {new Date(performanceData.timestamp).toLocaleTimeString()}
        </div>
      </div>

      {/* Agent Status Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {Object.entries(performanceData.agent_capabilities).map(([agentKey, capability]) => {
          const metrics = getAgentMetrics(agentKey);
          const health = getHealthStatus(agentKey);
          const HealthIcon = health.icon;

          return (
            <motion.div
              key={agentKey}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.1 * Object.keys(performanceData.agent_capabilities).indexOf(agentKey) }}
              className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-lg p-4 space-y-3"
            >
              {/* Agent Header */}
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div 
                    className="w-8 h-8 rounded-lg flex items-center justify-center"
                    style={{ backgroundColor: capability.color + '20', color: capability.color }}
                  >
                    {getAgentIcon(agentKey)}
                  </div>
                  <div>
                    <h4 className="font-semibold text-white text-sm">{capability.name}</h4>
                    <p className="text-xs text-gray-400">{capability.description}</p>
                  </div>
                </div>
                <HealthIcon className={`w-4 h-4 ${health.color}`} />
              </div>

              {/* Agent Metrics */}
              {metrics && (
                <div className="space-y-2">
                  <div className="flex justify-between items-center text-xs">
                    <span className="text-gray-400">Active Tasks:</span>
                    <span className="text-white font-semibold">{metrics.active_tasks}</span>
                  </div>
                  <div className="flex justify-between items-center text-xs">
                    <span className="text-gray-400">Completed:</span>
                    <span className="text-green-300 font-semibold">{metrics.total_completed.toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between items-center text-xs">
                    <span className="text-gray-400">Avg Response:</span>
                    <span className="text-blue-300 font-semibold">{formatResponseTime(metrics.avg_response_time_ms)}</span>
                  </div>
                  <div className="flex justify-between items-center text-xs">
                    <span className="text-gray-400">Speed:</span>
                    <span className="text-purple-300 font-semibold">{capability.speed_multiplier}x</span>
                  </div>
                </div>
              )}

              {/* Specialties */}
              <div className="space-y-2">
                <h5 className="text-xs font-medium text-gray-300">Specialties:</h5>
                <div className="flex flex-wrap gap-1">
                  {capability.specialties.slice(0, 2).map((specialty, index) => (
                    <span
                      key={index}
                      className="px-2 py-1 bg-white/10 text-xs rounded text-gray-300 capitalize"
                    >
                      {specialty.replace(/_/g, ' ')}
                    </span>
                  ))}
                  {capability.specialties.length > 2 && (
                    <span className="px-2 py-1 bg-white/5 text-xs rounded text-gray-400">
                      +{capability.specialties.length - 2} more
                    </span>
                  )}
                </div>
              </div>
            </motion.div>
          );
        })}
      </div>

      {/* System Summary */}
      <div className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-lg p-4">
        <div className="flex items-center space-x-2 mb-3">
          <BarChart3 className="w-4 h-4 text-blue-400" />
          <h4 className="font-semibold text-white text-sm">Routing Logic</h4>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
          <div className="space-y-1">
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-green-400 rounded-full" />
              <span className="text-green-300 font-medium">Fast Queries</span>
            </div>
            <p className="text-gray-400 text-xs">→ {performanceData.agent_capabilities.gemma3_fast.name}</p>
          </div>
          <div className="space-y-1">
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-purple-400 rounded-full" />
              <span className="text-purple-300 font-medium">Balanced Analysis</span>
            </div>
            <p className="text-gray-400 text-xs">→ {performanceData.agent_capabilities.qwen3_coordinator.name}</p>
          </div>
          <div className="space-y-1">
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-blue-400 rounded-full" />
              <span className="text-blue-300 font-medium">Complex Analysis</span>
            </div>
            <p className="text-gray-400 text-xs">→ {performanceData.agent_capabilities.deepseek_smart.name}</p>
          </div>
        </div>
      </div>
    </motion.div>
  );
};