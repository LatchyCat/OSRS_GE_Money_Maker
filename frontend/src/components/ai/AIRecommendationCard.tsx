import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Bot, TrendingUp, Clock, Shield, AlertTriangle, CheckCircle, RefreshCw } from 'lucide-react';
import { Button } from '../ui/Button';
import { useNavigate } from 'react-router-dom';
import { TaskComplexityIndicator } from './TaskComplexityIndicator';
import { aiApi } from '../../api/aiApi';

interface AIRecommendation {
  item_name: string;
  recommended_buy_price: number;
  recommended_sell_price: number;
  expected_profit_per_item: number;
  expected_profit_margin_pct: number;
  success_probability_pct: number;
  risk_level: string;
  estimated_hold_time_hours: number;
  data_age_hours?: number;
  freshness_status?: 'fresh' | 'acceptable' | 'stale';
  freshness_warnings?: string[];
  last_updated?: string;
  source?: string;
}

interface AgentMetadata {
  query_complexity: string;
  agent_used: string;
  processing_time_ms: number;
  task_routing_reason: string;
  data_quality_score: number;
  confidence_level: number;
}

export const AIRecommendationCard: React.FC = () => {
  const navigate = useNavigate();
  const [recommendations, setRecommendations] = useState<AIRecommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [capital, setCapital] = useState<string>('300K');
  const [refreshing, setRefreshing] = useState(false);
  const [capitalChanging, setCapitalChanging] = useState(false);
  const [agentMetadata, setAgentMetadata] = useState<AgentMetadata | null>(null);

  const formatGP = (amount: number): string => {
    if (amount >= 1000000) {
      return (amount / 1000000).toFixed(1) + 'M GP';
    } else if (amount >= 1000) {
      return (amount / 1000).toFixed(1) + 'K GP';
    }
    return amount.toLocaleString() + ' GP';
  };

  const getFreshnessIndicator = (rec: AIRecommendation) => {
    if (!rec.data_age_hours) return null;
    
    if (rec.freshness_status === 'stale') {
      return (
        <div className="flex items-center space-x-1 text-red-400" title={`Data is ${rec.data_age_hours.toFixed(1)}h old`}>
          <AlertTriangle className="w-3 h-3" />
          <span className="text-xs">Stale</span>
        </div>
      );
    } else if (rec.freshness_status === 'acceptable') {
      return (
        <div className="flex items-center space-x-1 text-yellow-400" title={`Data is ${rec.data_age_hours.toFixed(1)}h old`}>
          <Clock className="w-3 h-3" />
          <span className="text-xs">Old</span>
        </div>
      );
    } else if (rec.freshness_status === 'fresh') {
      return (
        <div className="flex items-center space-x-1 text-green-400" title={`Data is ${rec.data_age_hours.toFixed(1)}h old`}>
          <CheckCircle className="w-3 h-3" />
          <span className="text-xs">Fresh</span>
        </div>
      );
    }
    
    return null;
  };

  const getCapitalSpecificQuery = (queryCapital: string): string => {
    const capitalQueries = {
      '300K': `I have 300K GP and want to grow it to 5M GP. Find me 8 high-probability trading opportunities with detailed flip strategies. Focus on items under 30K each with strong profit margins, fast turnover, and reliable demand. Include specific buy/sell prices and risk management for aggressive but safe growth.`,
      
      '1M': `I have 1M GP capital for conservative trading. Find me 8 high-volume, low-risk items under 50K each with 80%+ success rates. Focus on fast-moving consumables, crafting materials, and common equipment. I need quick flips with minimal market risk and good liquidity.`,
      
      '5M': `I have 5M GP for medium-risk diversified trading. Show me 8 opportunities mixing item values from 10K-200K. Include a balanced portfolio of equipment upgrades, quest items, and seasonal goods. Target 70%+ success rates with 5-15% profit margins.`,
      
      '10M': `I have 10M GP for balanced trading strategies. Find me 8 opportunities including mid-tier weapons, armor pieces, and luxury items in the 50K-500K range. Mix stable profits with growth potential. Target items with strong demand drivers and 65%+ success rates.`,
      
      '25M': `I have 25M GP for advanced trading with higher-value items. Show me 8 opportunities in rare equipment, boss drops, and limited items (100K-2M range). Include market timing insights and seasonal trends. Accept moderate risk for 10-25% profit margins.`,
      
      '50M': `I have 50M GP for premium trading strategies. Find me 8 high-value opportunities in rare weapons, premium armor, and collector items (500K-5M range). Focus on items with strong fundamentals, upcoming game updates impact, and exclusive market positioning.`,
      
      '100M': `I have 100M GP for elite trading operations. Show me 8 high-end opportunities in extremely rare items, bulk commodity plays, and market manipulation strategies (1M-10M+ range). Include portfolio-level risk management and long-term market trends analysis.`
    };

    return capitalQueries[queryCapital as keyof typeof capitalQueries] || capitalQueries['10M'];
  };

  const fetchQuickRecommendations = async (useCapital?: string) => {
    try {
      setRefreshing(true);
      const queryCapital = useCapital || capital;
      const smartQuery = getCapitalSpecificQuery(queryCapital);
      // Convert capital string to actual GP amount
      let capitalAmount;
      if (queryCapital.includes('K')) {
        capitalAmount = parseInt(queryCapital.replace(/[^\d]/g, '')) * 1000;
      } else if (queryCapital.includes('M')) {
        capitalAmount = parseInt(queryCapital.replace(/[^\d]/g, '')) * 1000000;
      } else {
        capitalAmount = parseInt(queryCapital.replace(/[^\d]/g, '')) * 1000000; // Default to millions
      }
      
      const data = await aiApi.queryTrading({
        query: smartQuery,
        capital: capitalAmount
      });

      if (data.success && data.precision_opportunities && data.precision_opportunities.length > 0) {
        setRecommendations(data.precision_opportunities.slice(0, 8));
      } else {
        // No AI recommendations available - show empty state
        setRecommendations([]);
      }
      
      // Store agent metadata if available
      if (data.agent_metadata) {
        setAgentMetadata(data.agent_metadata);
      }
    } catch (error) {
      console.error('Error fetching AI recommendations:', error);
      // Show empty state on error instead of fallback data
      setRecommendations([]);
    } finally {
      setLoading(false);
      setRefreshing(false);
      setCapitalChanging(false);
    }
  };

  const handleCapitalChange = (newCapital: string) => {
    console.log(`Dashboard capital changing from ${capital} to ${newCapital}`);
    setCapitalChanging(true);
    setCapital(newCapital);
    
    // Clear existing data to show loading state
    setRecommendations([]);
    
    // Fetch new recommendations
    fetchQuickRecommendations(newCapital);
  };

  useEffect(() => {
    fetchQuickRecommendations();
  }, []);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.15 }}
      className="relative bg-black/40 backdrop-blur-xl border border-purple-400/30 hover:border-purple-400/60 rounded-xl overflow-hidden shadow-2xl shadow-purple-400/25 transition-all duration-500 hover:animate-hologram-glow group"
    >
      {/* Holographic Effects */}
      <div 
        className="absolute inset-0 opacity-0 group-hover:opacity-30 transition-opacity duration-700"
        style={{
          background: `linear-gradient(135deg, transparent 0%, rgba(147,51,234,0.1) 45%, rgba(255,255,255,0.4) 50%, rgba(147,51,234,0.1) 55%, transparent 100%)`,
          transform: 'translateX(-100%) skewX(-15deg)',
          animation: 'hologramShimmer 3s ease-in-out infinite'
        }}
      />
      
      <div className="absolute inset-0 rounded-xl bg-gradient-to-r from-transparent via-purple-400/30 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 animate-hologram-shimmer" />
      
      <div className="absolute inset-0 overflow-hidden rounded-xl">
        <div 
          className="absolute w-full h-0.5 bg-gradient-to-r from-transparent via-purple-400 to-transparent opacity-0 group-hover:opacity-60"
          style={{ 
            filter: 'blur(0.3px)',
            boxShadow: '0 0 8px rgba(147,51,234,0.8)',
            animation: 'scanLine 4s linear infinite'
          }}
        />
      </div>

      {/* Header */}
      <div className="relative z-10 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <motion.div 
              className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center border border-purple-400/30 shadow-lg shadow-purple-400/50"
              animate={{ 
                rotate: [0, 360],
                scale: [1, 1.05, 1]
              }}
              transition={{ 
                duration: 3,
                repeat: Infinity,
                ease: "easeInOut"
              }}
            >
              <Bot className="w-5 h-5 text-white drop-shadow-lg" />
            </motion.div>
            <div>
              <motion.h3 
                className="text-lg font-semibold bg-gradient-to-r from-white via-purple-200 to-blue-200 bg-clip-text text-transparent"
                animate={{ 
                  textShadow: '0 0 15px rgba(147,51,234,0.4)'
                }}
              >
                AI Trading Recommendations
              </motion.h3>
              <p className="text-sm text-purple-200/80">Smart profit opportunities</p>
            </div>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate('/recommendations')}
            className="text-blue-300 hover:text-white hover:bg-blue-500/20"
          >
            View All
          </Button>
        </div>

        {/* Capital Input */}
        <div className="flex items-center space-x-3 bg-black/20 backdrop-blur-sm border border-purple-400/20 rounded-lg p-3 shadow-lg shadow-purple-400/10">
          <label className="text-sm text-white font-medium">Capital:</label>
          <div className="flex space-x-2">
            {['300K', '1M', '5M', '10M', '25M', '50M', '100M'].map((amount) => (
              <button
                key={amount}
                onClick={() => handleCapitalChange(amount)}
                disabled={capitalChanging}
                className={`px-3 py-1 text-xs rounded-lg border transition-all duration-200 ${
                  capital === amount
                    ? 'bg-purple-500 border-purple-400 text-white shadow-lg shadow-purple-400/50'
                    : 'bg-black/20 border-purple-400/20 text-gray-300 hover:bg-purple-500/20 hover:text-white hover:border-purple-400/40'
                } ${capitalChanging ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                {amount}
                {capitalChanging && capital === amount && (
                  <span className="ml-1">
                    <div className="inline-block w-2 h-2 border border-white border-t-transparent rounded-full animate-spin"></div>
                  </span>
                )}
              </button>
            ))}
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => fetchQuickRecommendations()}
            loading={refreshing}
            icon={<RefreshCw className="w-3 h-3" />}
            className="text-purple-300 hover:text-white hover:bg-purple-500/20 ml-auto border border-purple-400/20 hover:border-purple-400/40"
          >
            Refresh
          </Button>
        </div>

        {/* Agent Processing Info */}
        {agentMetadata && (
          <div className="bg-black/20 backdrop-blur-sm border border-purple-400/20 rounded-lg p-3 shadow-lg shadow-purple-400/10">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <TaskComplexityIndicator
                  complexity={agentMetadata.query_complexity}
                  agentUsed={agentMetadata.agent_used}
                  processingTime={agentMetadata.processing_time_ms}
                  size="sm"
                />
              </div>
              <div className="flex items-center space-x-3 text-xs">
                <div className="flex items-center space-x-1">
                  <span className="text-gray-400">Quality:</span>
                  <span className="text-green-300 font-medium">
                    {(agentMetadata.data_quality_score * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="flex items-center space-x-1">
                  <span className="text-gray-400">Confidence:</span>
                  <span className="text-blue-300 font-medium">
                    {(agentMetadata.confidence_level * 100).toFixed(0)}%
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Recommendations */}
      <div className="relative z-10">
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <div className="w-6 h-6 border-2 border-blue-400 border-t-transparent rounded-full animate-spin"></div>
            <span className="ml-2 text-blue-200">Loading recommendations...</span>
          </div>
        ) : recommendations.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <div className="w-16 h-16 bg-blue-500/20 rounded-full flex items-center justify-center mb-4">
              <Bot className="w-8 h-8 text-blue-400" />
            </div>
            <h3 className="text-lg font-semibold text-white mb-2">Generating AI Recommendations</h3>
            <p className="text-gray-400 mb-4">
              Our AI is analyzing market data for your {capital} GP capital...
            </p>
            <Button
              variant="primary"
              size="sm"
              onClick={() => fetchQuickRecommendations()}
              loading={refreshing}
              icon={<RefreshCw className="w-4 h-4" />}
            >
              Try Again
            </Button>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {recommendations.map((rec, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.1 * index }}
                className="bg-black/30 backdrop-blur-sm border border-purple-400/20 rounded-lg p-4 hover:bg-purple-500/10 hover:border-purple-400/40 transition-all duration-300 cursor-pointer shadow-lg shadow-purple-400/5"
                onClick={() => navigate('/recommendations')}
              >
                <div className="flex justify-between items-start mb-3">
                  <div className="flex-1 min-w-0">
                    <h4 className="font-semibold text-white text-sm truncate">{rec.item_name}</h4>
                    {rec.source && (
                      <div className="text-xs text-gray-400 mt-1">
                        Source: {rec.source === 'database' ? 'Live DB' : rec.source}
                      </div>
                    )}
                  </div>
                  <div className="flex flex-col items-end space-y-1 ml-2">
                    <div className="flex items-center space-x-1">
                      <Shield className={`w-3 h-3 ${
                        rec.risk_level === 'low' ? 'text-green-400' : 
                        rec.risk_level === 'medium' ? 'text-yellow-400' : 'text-red-400'
                      }`} />
                      <span className="text-xs text-green-300">{rec.success_probability_pct}%</span>
                    </div>
                    {getFreshnessIndicator(rec)}
                  </div>
                </div>
                
                <div className="space-y-2 text-xs">
                  <div className="flex justify-between">
                    <span className="text-gray-400">Buy:</span>
                    <span className="text-blue-300 font-semibold">{formatGP(rec.recommended_buy_price)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Sell:</span>
                    <span className="text-green-300 font-semibold">{formatGP(rec.recommended_sell_price)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Profit:</span>
                    <span className="text-green-300 font-semibold">+{formatGP(rec.expected_profit_per_item)}</span>
                  </div>
                </div>
                
                <div className="flex items-center justify-between mt-3 pt-2 border-t border-white/10">
                  <div className="flex items-center space-x-1">
                    <TrendingUp className="w-3 h-3 text-green-400" />
                    <span className="text-xs text-green-300">{rec.expected_profit_margin_pct.toFixed(1)}%</span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <Clock className="w-3 h-3 text-blue-400" />
                    <span className="text-xs text-blue-300">{rec.estimated_hold_time_hours.toFixed(1)}h</span>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>

      {/* Quick Action */}
      <div className="relative z-10 pt-2 border-t border-white/10">
        <Button
          variant="primary"
          size="sm"
          onClick={() => navigate('/recommendations')}
          className="w-full bg-gradient-to-r from-purple-500 to-blue-600 hover:from-purple-600 hover:to-blue-700 shadow-lg shadow-purple-400/50"
          icon={<Bot className="w-4 h-4" />}
        >
          Ask AI Trading Assistant
        </Button>
      </div>
      
      {/* Corner Accent Lights */}
      <div className="absolute top-2 right-2 w-1.5 h-1.5 bg-purple-400 rounded-full opacity-50 group-hover:opacity-100 transition-opacity duration-300 shadow-lg shadow-purple-400/75" />
      <div className="absolute bottom-2 left-2 w-1.5 h-1.5 bg-blue-400 rounded-full opacity-50 group-hover:opacity-100 transition-opacity duration-300 shadow-lg shadow-blue-400/75" />
    </motion.div>
  );
};