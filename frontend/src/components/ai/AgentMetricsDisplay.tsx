import React from 'react';
import { motion } from 'framer-motion';
import { Zap, Brain, Layers, Clock, TrendingUp, Activity, CheckCircle } from 'lucide-react';

interface AgentMetadata {
  query_complexity: string;
  agent_used: string;
  processing_time_ms: number;
  task_routing_reason: string;
  system_load: any;
  data_quality_score: number;
  confidence_level: number;
}

interface AgentMetricsDisplayProps {
  metadata: AgentMetadata;
  className?: string;
  compact?: boolean;
}

export const AgentMetricsDisplay: React.FC<AgentMetricsDisplayProps> = ({ 
  metadata, 
  className = '', 
  compact = false 
}) => {
  const getAgentInfo = (agentUsed: string) => {
    switch (agentUsed) {
      case 'gemma3_fast':
        return {
          name: 'Gemma Fast',
          icon: Zap,
          color: '#10B981',
          bgColor: 'bg-green-500/20',
          textColor: 'text-green-300',
          borderColor: 'border-green-500/30',
          description: 'High-speed processing'
        };
      case 'deepseek_smart':
        return {
          name: 'DeepSeek Analysis',
          icon: Brain,
          color: '#3B82F6',
          bgColor: 'bg-blue-500/20',
          textColor: 'text-blue-300',
          borderColor: 'border-blue-500/30',
          description: 'Complex market analysis'
        };
      case 'qwen3_coordinator':
        return {
          name: 'Qwen Coordinator',
          icon: Layers,
          color: '#8B5CF6',
          bgColor: 'bg-purple-500/20',
          textColor: 'text-purple-300',
          borderColor: 'border-purple-500/30',
          description: 'Balanced coordination'
        };
      default:
        return {
          name: 'Multi-Agent',
          icon: Activity,
          color: '#6B7280',
          bgColor: 'bg-gray-500/20',
          textColor: 'text-gray-300',
          borderColor: 'border-gray-500/30',
          description: 'Distributed processing'
        };
    }
  };

  const getComplexityInfo = (complexity: string) => {
    switch (complexity.toLowerCase()) {
      case 'simple':
        return { 
          label: 'Simple', 
          color: 'text-green-300',
          bgColor: 'bg-green-500/20',
          description: 'Fast query processing'
        };
      case 'coordination':
        return { 
          label: 'Medium', 
          color: 'text-purple-300',
          bgColor: 'bg-purple-500/20',
          description: 'Balanced analysis'
        };
      case 'complex':
        return { 
          label: 'Complex', 
          color: 'text-blue-300',
          bgColor: 'bg-blue-500/20',
          description: 'Deep analysis'
        };
      default:
        return { 
          label: complexity, 
          color: 'text-gray-300',
          bgColor: 'bg-gray-500/20',
          description: 'Analysis'
        };
    }
  };

  const formatProcessingTime = (ms: number): string => {
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`;
  };

  const agentInfo = getAgentInfo(metadata.agent_used);
  const complexityInfo = getComplexityInfo(metadata.query_complexity);
  const AgentIcon = agentInfo.icon;

  if (compact) {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className={`inline-flex items-center space-x-2 ${agentInfo.bgColor} ${agentInfo.borderColor} border rounded-lg px-3 py-1.5 ${className}`}
      >
        <AgentIcon className={`w-4 h-4 ${agentInfo.textColor}`} />
        <div className="flex items-center space-x-2">
          <span className={`text-sm font-medium ${agentInfo.textColor}`}>
            {agentInfo.name}
          </span>
          <div className="text-xs text-gray-400">
            {formatProcessingTime(metadata.processing_time_ms)}
          </div>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`bg-white/5 backdrop-blur-sm border border-white/10 rounded-lg p-4 space-y-3 ${className}`}
    >
      {/* Header with Agent Info */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className={`w-10 h-10 ${agentInfo.bgColor} ${agentInfo.borderColor} border rounded-lg flex items-center justify-center`}>
            <AgentIcon className={`w-5 h-5 ${agentInfo.textColor}`} />
          </div>
          <div>
            <h4 className={`font-semibold ${agentInfo.textColor} text-sm`}>{agentInfo.name}</h4>
            <p className="text-xs text-gray-400">{agentInfo.description}</p>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <CheckCircle className="w-4 h-4 text-green-400" />
          <span className="text-xs text-green-300">Processed</span>
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 gap-3 text-xs">
        <div className="space-y-1">
          <div className="flex items-center space-x-2">
            <TrendingUp className="w-3 h-3 text-blue-400" />
            <span className="text-gray-400">Complexity:</span>
          </div>
          <div className={`inline-flex items-center px-2 py-1 ${complexityInfo.bgColor} rounded-lg`}>
            <span className={`font-medium ${complexityInfo.color}`}>{complexityInfo.label}</span>
          </div>
        </div>

        <div className="space-y-1">
          <div className="flex items-center space-x-2">
            <Clock className="w-3 h-3 text-purple-400" />
            <span className="text-gray-400">Processing Time:</span>
          </div>
          <div className="font-medium text-white">
            {formatProcessingTime(metadata.processing_time_ms)}
          </div>
        </div>

        <div className="space-y-1">
          <span className="text-gray-400">Data Quality:</span>
          <div className="flex items-center space-x-2">
            <div className="flex-1 bg-gray-700 rounded-full h-2">
              <div 
                className="bg-gradient-to-r from-green-500 to-blue-500 h-2 rounded-full transition-all duration-300"
                style={{ width: `${metadata.data_quality_score * 100}%` }}
              />
            </div>
            <span className="text-green-300 font-medium">{(metadata.data_quality_score * 100).toFixed(0)}%</span>
          </div>
        </div>

        <div className="space-y-1">
          <span className="text-gray-400">Confidence:</span>
          <div className="flex items-center space-x-2">
            <div className="flex-1 bg-gray-700 rounded-full h-2">
              <div 
                className="bg-gradient-to-r from-yellow-500 to-green-500 h-2 rounded-full transition-all duration-300"
                style={{ width: `${metadata.confidence_level * 100}%` }}
              />
            </div>
            <span className="text-yellow-300 font-medium">{(metadata.confidence_level * 100).toFixed(0)}%</span>
          </div>
        </div>
      </div>

      {/* Routing Reason */}
      <div className="pt-2 border-t border-white/10">
        <div className="flex items-start space-x-2">
          <Activity className="w-3 h-3 text-gray-400 mt-0.5" />
          <div>
            <p className="text-xs text-gray-400">Routing Logic:</p>
            <p className="text-xs text-gray-300 leading-relaxed">{metadata.task_routing_reason}</p>
          </div>
        </div>
      </div>
    </motion.div>
  );
};