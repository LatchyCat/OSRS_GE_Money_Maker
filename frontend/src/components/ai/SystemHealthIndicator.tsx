import React from 'react';
import { motion } from 'framer-motion';
import { Activity, CheckCircle, AlertTriangle, XCircle, Wifi, WifiOff } from 'lucide-react';

interface SystemHealthProps {
  systemHealthy: boolean;
  agentsAvailable: {
    gemma3_fast: boolean;
    deepseek_smart: boolean;
    qwen3_coordinator: boolean;
  };
  timestamp: string;
  className?: string;
}

export const SystemHealthIndicator: React.FC<SystemHealthProps> = ({
  systemHealthy,
  agentsAvailable,
  timestamp,
  className = ''
}) => {
  const getOverallStatus = () => {
    const availableCount = Object.values(agentsAvailable).filter(Boolean).length;
    const totalAgents = Object.keys(agentsAvailable).length;
    
    if (availableCount === totalAgents && systemHealthy) {
      return {
        status: 'healthy',
        icon: CheckCircle,
        color: 'text-green-400',
        bgColor: 'bg-green-500/20',
        borderColor: 'border-green-500/30',
        label: 'System Healthy',
        description: 'All agents operational'
      };
    } else if (availableCount >= totalAgents / 2) {
      return {
        status: 'degraded',
        icon: AlertTriangle,
        color: 'text-yellow-400',
        bgColor: 'bg-yellow-500/20',
        borderColor: 'border-yellow-500/30',
        label: 'Partial Service',
        description: `${availableCount}/${totalAgents} agents available`
      };
    } else {
      return {
        status: 'unhealthy',
        icon: XCircle,
        color: 'text-red-400',
        bgColor: 'bg-red-500/20',
        borderColor: 'border-red-500/30',
        label: 'System Issues',
        description: 'Multiple agents offline'
      };
    }
  };

  const getAgentStatus = (agentKey: string, available: boolean) => {
    const agentNames = {
      gemma3_fast: 'Gemma Fast',
      deepseek_smart: 'DeepSeek',
      qwen3_coordinator: 'Qwen Coord'
    };

    return {
      name: agentNames[agentKey as keyof typeof agentNames] || agentKey,
      available,
      icon: available ? Wifi : WifiOff,
      color: available ? 'text-green-400' : 'text-red-400'
    };
  };

  const overallStatus = getOverallStatus();
  const StatusIcon = overallStatus.icon;

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      className={`${overallStatus.bgColor} ${overallStatus.borderColor} border rounded-lg p-4 ${className}`}
    >
      {/* Main Status */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-3">
          <StatusIcon className={`w-5 h-5 ${overallStatus.color}`} />
          <div>
            <h4 className={`font-semibold ${overallStatus.color}`}>{overallStatus.label}</h4>
            <p className="text-sm text-gray-400">{overallStatus.description}</p>
          </div>
        </div>
        <div className="text-xs text-gray-500">
          {new Date(timestamp).toLocaleTimeString()}
        </div>
      </div>

      {/* Agent Status Grid */}
      <div className="grid grid-cols-3 gap-2">
        {Object.entries(agentsAvailable).map(([agentKey, available]) => {
          const agentStatus = getAgentStatus(agentKey, available);
          const AgentIcon = agentStatus.icon;

          return (
            <div
              key={agentKey}
              className="flex items-center space-x-2 px-2 py-1 bg-white/5 rounded-lg"
            >
              <AgentIcon className={`w-3 h-3 ${agentStatus.color}`} />
              <span className="text-xs text-gray-300">{agentStatus.name}</span>
            </div>
          );
        })}
      </div>
    </motion.div>
  );
};