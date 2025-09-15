import React from 'react';
import { motion } from 'framer-motion';
import { Zap, Brain, Layers, TrendingUp, Clock } from 'lucide-react';

interface TaskComplexityIndicatorProps {
  complexity: string;
  agentUsed: string;
  processingTime: number;
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

export const TaskComplexityIndicator: React.FC<TaskComplexityIndicatorProps> = ({
  complexity,
  agentUsed,
  processingTime,
  className = '',
  size = 'md'
}) => {
  const getComplexityInfo = (complexity: string) => {
    switch (complexity.toLowerCase()) {
      case 'simple':
        return {
          level: 1,
          label: 'Simple',
          color: '#10B981',
          bgColor: 'bg-green-500/20',
          textColor: 'text-green-300',
          borderColor: 'border-green-500/30',
          description: 'Fast query processing'
        };
      case 'coordination':
        return {
          level: 2,
          label: 'Medium',
          color: '#8B5CF6',
          bgColor: 'bg-purple-500/20',
          textColor: 'text-purple-300',
          borderColor: 'border-purple-500/30',
          description: 'Balanced analysis'
        };
      case 'complex':
        return {
          level: 3,
          label: 'Complex',
          color: '#3B82F6',
          bgColor: 'bg-blue-500/20',
          textColor: 'text-blue-300',
          borderColor: 'border-blue-500/30',
          description: 'Deep analysis required'
        };
      default:
        return {
          level: 2,
          label: complexity,
          color: '#6B7280',
          bgColor: 'bg-gray-500/20',
          textColor: 'text-gray-300',
          borderColor: 'border-gray-500/30',
          description: 'Processing'
        };
    }
  };

  const getAgentInfo = (agentUsed: string) => {
    switch (agentUsed) {
      case 'gemma3_fast':
        return {
          name: 'Gemma',
          icon: Zap,
          fullName: 'Gemma Fast Lane'
        };
      case 'deepseek_smart':
        return {
          name: 'DeepSeek',
          icon: Brain,
          fullName: 'DeepSeek Analysis'
        };
      case 'qwen3_coordinator':
        return {
          name: 'Qwen',
          icon: Layers,
          fullName: 'Qwen Coordinator'
        };
      default:
        return {
          name: 'Multi-Agent',
          icon: TrendingUp,
          fullName: 'Multi-Agent System'
        };
    }
  };

  const formatTime = (ms: number): string => {
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  };

  const complexityInfo = getComplexityInfo(complexity);
  const agentInfo = getAgentInfo(agentUsed);
  const AgentIcon = agentInfo.icon;

  const sizeClasses = {
    sm: {
      container: 'px-2 py-1',
      icon: 'w-3 h-3',
      text: 'text-xs',
      spacing: 'space-x-1'
    },
    md: {
      container: 'px-3 py-2',
      icon: 'w-4 h-4',
      text: 'text-sm',
      spacing: 'space-x-2'
    },
    lg: {
      container: 'px-4 py-3',
      icon: 'w-5 h-5',
      text: 'text-base',
      spacing: 'space-x-3'
    }
  };

  const sizeClass = sizeClasses[size];

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      className={`inline-flex items-center ${sizeClass.spacing} ${complexityInfo.bgColor} ${complexityInfo.borderColor} border rounded-lg ${sizeClass.container} ${className}`}
    >
      {/* Complexity Level Indicator */}
      <div className="flex items-center space-x-1">
        <div className="flex space-x-0.5">
          {[1, 2, 3].map((level) => (
            <div
              key={level}
              className={`w-1 h-3 rounded-full ${
                level <= complexityInfo.level
                  ? complexityInfo.bgColor.replace('/20', '/60')
                  : 'bg-gray-600'
              }`}
            />
          ))}
        </div>
        <span className={`font-medium ${complexityInfo.textColor} ${sizeClass.text}`}>
          {complexityInfo.label}
        </span>
      </div>

      {/* Agent Used */}
      <div className="flex items-center space-x-1">
        <AgentIcon className={`${sizeClass.icon} ${complexityInfo.textColor}`} />
        <span className={`font-medium text-white ${sizeClass.text}`}>
          {agentInfo.name}
        </span>
      </div>

      {/* Processing Time */}
      {processingTime > 0 && (
        <div className="flex items-center space-x-1">
          <Clock className={`${sizeClass.icon} text-gray-400`} />
          <span className={`text-gray-400 ${sizeClass.text}`}>
            {formatTime(processingTime)}
          </span>
        </div>
      )}
    </motion.div>
  );
};