import React, { useState, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { Bot, TrendingUp, Clock, Shield, AlertTriangle, RefreshCw, Filter, Target, BarChart3, Send, MessageSquare, User, History } from 'lucide-react';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { TaskComplexityIndicator } from '../components/ai/TaskComplexityIndicator';
import { AgentPerformanceCard } from '../components/ai/AgentPerformanceCard';
import { CSSParticleBackground } from '../components/effects/CSSParticleBackground';
import { HolographicCard } from '../components/effects/HolographicCard';
import { aiApi } from '../api/aiApi';
import type { AIRecommendation, MarketSignal, AgentMetadata } from '../types/aiTypes';

// Interface definitions moved to aiApi.ts

export const AIRecommendations: React.FC = () => {
  const [recommendations, setRecommendations] = useState<AIRecommendation[]>([]);
  const [marketSignals, setMarketSignals] = useState<MarketSignal[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [strategyChanging, setStrategyChanging] = useState(false);
  const [selectedStrategy, setSelectedStrategy] = useState<string>('high_alchemy');
  const [customCapital, setCustomCapital] = useState<string>('1M');
  const [riskFilter, setRiskFilter] = useState<string>('all');
  const [sortBy, setSortBy] = useState<string>('profit');
  const [agentMetadata, setAgentMetadata] = useState<AgentMetadata | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [aiResponseText, setAiResponseText] = useState<string>('');
  const [showAiAnalysis, setShowAiAnalysis] = useState<boolean>(false);
  
  // Chat interface state
  const [customQuery, setCustomQuery] = useState<string>('');
  const [chatHistory, setChatHistory] = useState<Array<{query: string, response: string, timestamp: string}>>([]);
  const [processingCustomQuery, setProcessingCustomQuery] = useState<boolean>(false);
  const [chatHeight, setChatHeight] = useState<number>(500); // Dynamic chat height - increased default
  const chatHistoryRef = useRef<HTMLDivElement>(null);
  
  // Calculate profit level for particle effects (0-1 scale)
  const profitLevel = recommendations.length > 0 ? 
    Math.min(recommendations.reduce((sum, rec) => sum + rec.expected_profit_margin_pct, 0) / (recommendations.length * 20), 1) : 0.5;
  
  // Calculate particle intensity based on data richness (0-1 scale)
  const particleIntensity = Math.min((recommendations.length + marketSignals.length) / 20, 1);

  // Calculate dynamic chat height based on conversation length
  const calculateChatHeight = (): number => {
    const minHeight = 500; // Increased minimum height for better readability
    const maxHeight = Math.min(800, window.innerHeight * 0.75); // Max 75% of viewport or 800px (increased)
    const baseEntryHeight = 180; // Increased height per conversation entry
    const headerHeight = 100; // Increased chat header height
    
    if (chatHistory.length === 0) return minHeight;
    
    // Calculate height based on number of entries
    const calculatedHeight = headerHeight + (chatHistory.length * baseEntryHeight);
    
    // Ensure it's within min/max bounds
    return Math.min(Math.max(calculatedHeight, minHeight), maxHeight);
  };

  // Update chat height and scroll to bottom when conversation changes
  useEffect(() => {
    const newHeight = calculateChatHeight();
    setChatHeight(newHeight);
    
    // Auto-scroll to bottom when new messages are added
    if (chatHistoryRef.current && chatHistory.length > 0) {
      setTimeout(() => {
        chatHistoryRef.current?.scrollTo({
          top: chatHistoryRef.current.scrollHeight,
          behavior: 'smooth'
        });
      }, 100); // Small delay to ensure height transition completes
    }
  }, [chatHistory.length]);

  // Handle window resize for responsive max height
  useEffect(() => {
    const handleResize = () => {
      const newHeight = calculateChatHeight();
      setChatHeight(newHeight);
    };
    
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [chatHistory.length]);

  const formatGP = (amount: number): string => {
    if (amount >= 1000000) {
      return (amount / 1000000).toFixed(1) + 'M GP';
    } else if (amount >= 1000) {
      return (amount / 1000).toFixed(1) + 'K GP';
    }
    return amount.toLocaleString() + ' GP';
  };

  const strategies = {
    high_alchemy: {
      name: 'High Alchemy',
      icon: '⚡',
      color: 'from-yellow-500/10 to-yellow-600/20 border-yellow-500/30',
      hoverColor: 'hover:from-yellow-500/20 hover:to-yellow-600/30',
      description: 'Magic XP + GP',
      details: 'Combine Magic training with profit through optimal high alchemy targets'
    },
    decanting: {
      name: 'Decanting',
      icon: '🧪',
      color: 'from-blue-500/10 to-blue-600/20 border-blue-500/30',
      hoverColor: 'hover:from-blue-500/20 hover:to-blue-600/30',
      description: 'Potion Profits',
      details: 'Convert barbarian potions into individual doses for maximum profit'
    },
    flipping: {
      name: 'Item Flipping',
      icon: '📈',
      color: 'from-purple-500/10 to-purple-600/20 border-purple-500/30',
      hoverColor: 'hover:from-purple-500/20 hover:to-purple-600/30',
      description: 'Buy Low, Sell High',
      details: 'Profit from Grand Exchange price differences and market inefficiencies'
    },
    crafting: {
      name: 'Crafting',
      icon: '🔨',
      color: 'from-orange-500/10 to-orange-600/20 border-orange-500/30',
      hoverColor: 'hover:from-orange-500/20 hover:to-orange-600/30',
      description: 'Skill + Profit',
      details: 'Combine skill training with profitable crafting methods'
    },
    set_combining: {
      name: 'Set Combining',
      icon: '🛡️',
      color: 'from-green-500/10 to-green-600/20 border-green-500/30',
      hoverColor: 'hover:from-green-500/20 hover:to-green-600/30',
      description: 'Equipment Sets',
      details: 'Assemble equipment sets for premium pricing opportunities'
    },
    mixed_strategy: {
      name: 'Mixed Strategy',
      icon: '🎯',
      color: 'from-indigo-500/10 to-indigo-600/20 border-indigo-500/30',
      hoverColor: 'hover:from-indigo-500/20 hover:to-indigo-600/30',
      description: 'Best of All',
      details: 'Multi-approach recommendations combining all strategies'
    }
  };

  const getStrategySpecificQuery = (strategy: string, capital: string): string => {
    const capitalAmount = parseCapitalString(capital);
    const capitalText = capitalAmount >= 1000000 ? `${(capitalAmount/1000000).toFixed(1)}M GP` : `${(capitalAmount/1000).toFixed(0)}K GP`;
    
    const strategyQueries = {
      high_alchemy: `I have ${capitalText} and want to focus on HIGH ALCHEMY strategies. Find me 12 optimal high alchemy opportunities that combine Magic XP training with profit. Include detailed analysis of:
      - Items with best GP per cast vs Magic XP gained
      - Nature rune costs and profit calculations
      - Volume analysis and buy limits
      - XP efficiency ratings and sustainable methods
      - Risk assessment for consistent profit margins
      Focus on items that provide both solid Magic XP rates (50K+ XP/hour) and profitable returns. Include alching rotation strategies and timing recommendations.`,
      
      decanting: `I have ${capitalText} for DECANTING operations. Analyze 10 high-profit decanting opportunities with comprehensive strategies:
      - Barbarian potion to individual dose conversions
      - Profit margins per decanting operation
      - Volume requirements and scalability potential
      - Timing strategies and market demand patterns
      - Competition analysis and market positioning
      Focus on potions with consistent demand, strong profit margins (15%+), and manageable competition. Include batch processing strategies and efficiency optimization.`,
      
      flipping: `I have ${capitalText} for ITEM FLIPPING strategies. Provide 12 high-probability flip opportunities with detailed market intelligence:
      - Current buy/sell price spreads and profit margins
      - Volume analysis and liquidity assessment
      - Historical price trends and volatility patterns
      - Market timing strategies and demand catalysts
      - Competition levels and market manipulation risks
      Focus on items with reliable price differences, good liquidity, and manageable risk profiles. Target consistent 10-30% margins with fast turnover.`,
      
      crafting: `I have ${capitalText} for CRAFTING profit strategies. Find 10 optimal crafting methods that combine skill training with profit:
      - Material costs vs finished product values
      - XP gains and skill efficiency analysis
      - Market demand for crafted items
      - Seasonal patterns and quest-driven demand
      - Scalability and competition assessment
      Focus on methods providing both skill advancement and consistent profits. Include efficiency calculations and resource optimization strategies.`,
      
      set_combining: `I have ${capitalText} for SET COMBINING operations. Analyze 8 profitable set assembly opportunities:
      - Individual piece costs vs complete set values
      - Set completion premiums and market demand
      - Availability patterns and sourcing strategies
      - Risk assessment for piece price volatility
      - Market timing and seasonal factors
      Focus on sets with consistent premiums (20%+), manageable sourcing risks, and reliable market demand.`,
      
      mixed_strategy: `I have ${capitalText} for DIVERSIFIED OSRS trading. Provide a balanced portfolio of 15 opportunities across all strategies:
      - 3 High Alchemy opportunities for Magic XP + profit
      - 3 Decanting operations for consistent returns
      - 4 Item Flipping targets for quick profits
      - 3 Crafting methods for skill + profit
      - 2 Set Combining opportunities for premium margins
      Include portfolio allocation advice, risk distribution, and strategy rotation recommendations for optimal capital utilization.`
    };

    return strategyQueries[strategy as keyof typeof strategyQueries] || strategyQueries['mixed_strategy'];
  };

  const parseCapitalString = (capital: string): number => {
    const numStr = capital.replace(/[^\d.]/g, '');
    const num = parseFloat(numStr);
    if (capital.toLowerCase().includes('k')) {
      return num * 1000;
    } else if (capital.toLowerCase().includes('m')) {
      return num * 1000000;
    }
    return num * 1000000; // Default to millions
  };

  const fetchRecommendations = async (useStrategy?: string, useCapital?: string) => {
    try {
      setRefreshing(true);
      setError(null); // Clear any previous errors
      const queryStrategy = useStrategy || selectedStrategy;
      const queryCapital = useCapital || customCapital;
      const smartQuery = getStrategySpecificQuery(queryStrategy, queryCapital);
      const capitalAmount = parseCapitalString(queryCapital);
      
      const data = await aiApi.queryTrading({
        query: smartQuery,
        capital: capitalAmount,
        strategy_type: queryStrategy
      });
      
      // Debug: Log what we received
      console.log('AI Response Data:', {
        success: data.success,
        response: data.response?.substring(0, 100) + '...',
        responseLength: data.response?.length,
        opportunitiesCount: data.precision_opportunities?.length,
        hasResponse: !!data.response
      });
      
      // Store AI response text but don't show AI analysis for automatic recommendations
      const responseText = data.response || 'No response received';
      const formattedText = responseText
        .replace(/\\n/g, '\n') // Convert escaped newlines to actual newlines
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>'); // Convert **text** to bold
      setAiResponseText(formattedText);
      // Don't show AI analysis section for automatic recommendations
      setShowAiAnalysis(false);
      
      if (data.success) {
        if (data.precision_opportunities && data.precision_opportunities.length > 0) {
          setRecommendations(data.precision_opportunities);
        } else {
          setRecommendations([]);
        }

        if (data.market_signals && data.market_signals.length > 0) {
          setMarketSignals(data.market_signals);
        } else {
          setMarketSignals([]);
        }

        // Store agent metadata if available
        if (data.agent_metadata) {
          setAgentMetadata(data.agent_metadata);
        }
        
        setError(null); // Clear any previous errors on success
      } else {
        // Handle AI service failures gracefully
        console.error('AI query failed:', data);
        setError(data.ai_error || 'AI service temporarily unavailable');
        setRecommendations([]);
        setMarketSignals([]);
        
        // Still show fallback response if available
        if (data.fallback_response) {
          const formattedFallback = data.fallback_response
            .replace(/\\n/g, '\n')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
          setAiResponseText(formattedFallback);
        }
      }

    } catch (error: any) {
      console.error('Error fetching AI recommendations:', error);
      setError(error.message || 'Failed to connect to AI service');
      setRecommendations([]);
      setMarketSignals([]);
      setAiResponseText('AI analysis temporarily unavailable. Please try again later.');
      setShowAiAnalysis(false); // Don't show AI analysis on error
    } finally {
      setLoading(false);
      setRefreshing(false);
      setCapitalChanging(false);
    }
  };

  const handleStrategyChange = (newStrategy: string) => {
    console.log(`Strategy changing from ${selectedStrategy} to ${newStrategy}`);
    setStrategyChanging(true);
    setSelectedStrategy(newStrategy);
    
    // Clear existing data to show loading state
    setRecommendations([]);
    setMarketSignals([]);
    setAiResponseText('');
    setError(null);
    setShowAiAnalysis(false); // Hide AI analysis when changing strategy
    
    // Fetch new recommendations
    fetchRecommendations(newStrategy, customCapital);
  };

  const handleCapitalChange = (newCapital: string) => {
    setCustomCapital(newCapital);
    // Auto-refresh recommendations when capital changes significantly
    const currentAmount = parseCapitalString(customCapital);
    const newAmount = parseCapitalString(newCapital);
    if (Math.abs(newAmount - currentAmount) / currentAmount > 0.5) {
      fetchRecommendations(selectedStrategy, newCapital);
    }
  };

  const handleCustomQuery = async () => {
    if (!customQuery.trim()) return;

    setProcessingCustomQuery(true);
    setError(null); // Clear any previous errors
    
    // Add realistic AI processing time (30-60 seconds) with progress indication
    
    try {
      const capitalAmount = parseCapitalString(customCapital);
      
      const data = await aiApi.queryTrading({
        query: customQuery,
        capital: capitalAmount,
        strategy_type: selectedStrategy
      });
      
      // Debug: Log custom query response  
      console.log('Custom Query Response:', {
        success: data.success,
        response: data.response?.substring(0, 100) + '...',
        responseLength: data.response?.length,
        opportunitiesCount: data.precision_opportunities?.length
      });
      
      // Update chat history with the response
      const responseText = data.response || data.fallback_response || 'No response received';
      const newChatEntry = {
        query: customQuery,
        response: responseText,
        timestamp: new Date().toLocaleTimeString()
      };
      
      setChatHistory(prev => [...prev, newChatEntry]);
      
      // Update AI response text for display and show AI analysis section
      setAiResponseText(responseText);
      setShowAiAnalysis(true); // Show AI analysis for custom queries
      
      // Update AI response and recommendations if successful
      if (data.success) {
        if (data.precision_opportunities && data.precision_opportunities.length > 0) {
          setRecommendations(data.precision_opportunities);
        }

        if (data.market_signals && data.market_signals.length > 0) {
          setMarketSignals(data.market_signals);
        }

        // Store agent metadata if available
        if (data.agent_metadata) {
          setAgentMetadata(data.agent_metadata);
        }
        
        setError(null); // Clear errors on success
      } else {
        // Set error but still show the response
        setError(data.ai_error || 'AI processing encountered an issue');
      }

      // Clear the input
      setCustomQuery('');
      
    } catch (error: any) {
      console.error('Error processing custom query:', error);
      
      const errorEntry = {
        query: customQuery,
        response: 'Sorry, there was an error connecting to the AI service. Please check your connection and try again.',
        timestamp: new Date().toLocaleTimeString()
      };
      setChatHistory(prev => [...prev, errorEntry]);
      setError(error.message || 'Failed to process AI query');
      setAiResponseText('AI analysis temporarily unavailable. Please try again later.');
      setShowAiAnalysis(false); // Don't show AI analysis on error
    } finally {
      setProcessingCustomQuery(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleCustomQuery();
    }
  };

  const filteredRecommendations = recommendations.filter(rec => {
    if (riskFilter === 'all') return true;
    return rec.risk_level === riskFilter;
  }).sort((a, b) => {
    switch (sortBy) {
      case 'profit':
        return b.expected_profit_per_item - a.expected_profit_per_item;
      case 'margin':
        return b.expected_profit_margin_pct - a.expected_profit_margin_pct;
      case 'success':
        return b.success_probability_pct - a.success_probability_pct;
      case 'time':
        return a.estimated_hold_time_hours - b.estimated_hold_time_hours;
      default:
        return 0;
    }
  });

  useEffect(() => {
    fetchRecommendations();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <LoadingSpinner size="lg" text="AI is analyzing the market..." />
      </div>
    );
  }

  return (
    <div className="relative">
      {/* Interactive Particle Background */}
      <CSSParticleBackground 
        profitLevel={profitLevel}
        intensity={particleIntensity}
        className="fixed inset-0 pointer-events-none z-0"
      />
      
      {/* Main Content with relative positioning */}
      <div className="relative z-10 space-y-8">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between"
      >
        <div>
          <h1 className="text-3xl font-bold text-white">AI Trading Recommendations</h1>
          <p className="text-gray-400 mt-2">
            Intelligent market analysis powered by advanced AI and real-time data
          </p>
        </div>
        <Button
          variant="secondary"
          onClick={() => fetchRecommendations()}
          loading={refreshing}
          icon={<RefreshCw className="w-4 h-4" />}
        >
          Refresh Analysis
        </Button>
      </motion.div>

      {/* Controls */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="backdrop-blur-md bg-white/5 border border-white/10 rounded-xl p-6 space-y-6"
      >
        {/* Strategy Selection */}
        <div className="space-y-4">
          <label className="text-white font-medium text-lg">Choose Your Money-Making Strategy:</label>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Object.entries(strategies).map(([key, strategy]) => (
              <button
                key={key}
                onClick={() => handleStrategyChange(key)}
                disabled={strategyChanging}
                className={`p-4 rounded-lg border transition-all duration-200 bg-gradient-to-br ${
                  selectedStrategy === key
                    ? `${strategy.color} border-current text-white shadow-lg transform scale-105`
                    : 'bg-white/10 border-white/20 text-gray-300 hover:bg-white/20 hover:text-white hover:scale-102'
                } ${strategyChanging ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                <div className="flex items-center space-x-3">
                  <div className="text-2xl">{strategy.icon}</div>
                  <div className="text-left">
                    <div className="font-semibold">{strategy.name}</div>
                    <div className="text-xs opacity-80">{strategy.description}</div>
                  </div>
                  {strategyChanging && selectedStrategy === key && (
                    <div className="ml-auto">
                      <div className="w-4 h-4 border border-white border-t-transparent rounded-full animate-spin"></div>
                    </div>
                  )}
                </div>
                <div className="text-xs opacity-70 mt-2 text-left">
                  {strategy.details}
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Capital Input */}
        <div className="flex flex-wrap items-center gap-4">
          <label className="text-white font-medium">Your Capital:</label>
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={customCapital}
              onChange={(e) => handleCapitalChange(e.target.value)}
              placeholder="e.g., 1M, 500K, 2.5M"
              className="bg-white/10 border border-white/20 rounded-lg px-3 py-2 text-white placeholder-gray-400 text-sm min-w-32"
            />
            <div className="text-gray-400 text-xs">
              Use K for thousands, M for millions
            </div>
          </div>
          <div className="flex gap-1">
            {['500K', '1M', '2M', '5M', '10M'].map((amount) => (
              <button
                key={amount}
                onClick={() => handleCapitalChange(amount)}
                className="px-2 py-1 bg-white/10 hover:bg-white/20 text-gray-300 hover:text-white rounded text-xs transition-colors"
              >
                {amount}
              </button>
            ))}
          </div>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-6">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-gray-400" />
            <label className="text-gray-300">Risk Level:</label>
            <select
              value={riskFilter}
              onChange={(e) => setRiskFilter(e.target.value)}
              className="bg-white/10 border border-white/20 rounded-lg px-3 py-1 text-white text-sm"
            >
              <option value="all">All Levels</option>
              <option value="low">Low Risk</option>
              <option value="medium">Medium Risk</option>
              <option value="high">High Risk</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-gray-400" />
            <label className="text-gray-300">Sort by:</label>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="bg-white/10 border border-white/20 rounded-lg px-3 py-1 text-white text-sm"
            >
              <option value="profit">Highest Profit</option>
              <option value="margin">Best Margin</option>
              <option value="success">Success Rate</option>
              <option value="time">Fastest Return</option>
            </select>
          </div>
        </div>
      </motion.div>

      {/* Error Display */}
      {error && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
          className="bg-red-500/10 border border-red-500/20 rounded-xl p-4"
        >
          <div className="flex items-center space-x-3">
            <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0" />
            <div className="flex-1">
              <h3 className="text-sm font-medium text-red-300">AI Service Error</h3>
              <p className="text-sm text-red-200 mt-1">{error}</p>
            </div>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                setError(null);
                fetchRecommendations();
              }}
              className="bg-red-500/20 hover:bg-red-500/30 text-red-200"
            >
              Retry
            </Button>
          </div>
        </motion.div>
      )}

      {/* AI Response Display */}
      {showAiAnalysis && aiResponseText && !error && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-blue-500/10 border border-blue-500/20 rounded-xl p-6"
        >
          <div className="flex items-center space-x-3 mb-4">
            <Bot className="w-6 h-6 text-blue-400" />
            <h3 className="text-lg font-semibold text-blue-300">AI Analysis</h3>
          </div>
          <div 
            className="text-white text-sm whitespace-pre-wrap leading-relaxed"
            dangerouslySetInnerHTML={{ __html: aiResponseText }}
          />
        </motion.div>
      )}

      {/* Multi-Agent Performance Status */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15 }}
      >
        <AgentPerformanceCard />
      </motion.div>

      {/* Agent Processing Info */}
      {agentMetadata && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.17 }}
          className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-lg p-4"
        >
          <h3 className="text-lg font-semibold text-white mb-3">Current Query Processing</h3>
          <div className="flex items-center justify-between">
            <TaskComplexityIndicator
              complexity={agentMetadata.query_complexity}
              agentUsed={agentMetadata.agent_used}
              processingTime={agentMetadata.processing_time_ms}
              size="md"
            />
            <div className="flex items-center space-x-4 text-sm">
              <div className="flex items-center space-x-2">
                <span className="text-gray-400">Quality:</span>
                <span className="text-green-300 font-medium">
                  {(agentMetadata.data_quality_score * 100).toFixed(0)}%
                </span>
              </div>
              <div className="flex items-center space-x-2">
                <span className="text-gray-400">Confidence:</span>
                <span className="text-blue-300 font-medium">
                  {(agentMetadata.confidence_level * 100).toFixed(0)}%
                </span>
              </div>
            </div>
          </div>
          <div className="mt-2 text-xs text-gray-400">
            Routing: {agentMetadata.task_routing_reason}
          </div>
        </motion.div>
      )}

      {/* Interactive AI Chat Interface */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="backdrop-blur-md bg-gradient-to-br from-purple-500/10 via-blue-500/10 to-cyan-500/10 border border-white/20 rounded-xl overflow-hidden"
      >
        {/* Chat Header */}
        <div className="bg-white/5 border-b border-white/10 p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-blue-600 rounded-lg flex items-center justify-center">
                <MessageSquare className="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-white">AI Trading Assistant</h3>
                <p className="text-sm text-blue-200/80">Ask specific questions about your trading strategy</p>
              </div>
            </div>
            {chatHistory.length > 0 && (
              <button
                onClick={() => setChatHistory([])}
                className="text-gray-400 hover:text-white transition-colors text-sm flex items-center space-x-1"
              >
                <History className="w-4 h-4" />
                <span>Clear</span>
              </button>
            )}
          </div>
        </div>

        {/* Chat History */}
        {chatHistory.length > 0 && (
          <div className="relative">
            <div 
              ref={chatHistoryRef}
              className="overflow-y-auto p-4 space-y-4 bg-white/5 transition-all duration-300 ease-in-out"
              style={{ 
                maxHeight: `${chatHeight}px`,
                scrollbarWidth: 'thin',
                scrollbarColor: 'rgba(255,255,255,0.2) transparent'
              }}
            >
              {chatHistory.map((chat, index) => (
              <div key={index} className="space-y-3">
                {/* User Query */}
                <div className="flex items-start space-x-3">
                  <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center flex-shrink-0">
                    <User className="w-4 h-4 text-white" />
                  </div>
                  <div className="flex-1">
                    <div className="bg-blue-500/20 border border-blue-500/30 rounded-lg p-3">
                      <p className="text-white text-sm">{chat.query}</p>
                      <span className="text-blue-300 text-xs">{chat.timestamp}</span>
                    </div>
                  </div>
                </div>
                
                {/* AI Response */}
                <div className="flex items-start space-x-3">
                  <div className="w-8 h-8 bg-gradient-to-br from-purple-500 to-blue-600 rounded-lg flex items-center justify-center flex-shrink-0">
                    <Bot className="w-4 h-4 text-white" />
                  </div>
                  <div className="flex-1">
                    <div className="bg-white/10 border border-white/20 rounded-lg p-3">
                      <div className="text-white text-sm whitespace-pre-wrap">{chat.response}</div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
            </div>
            {/* Fade indicator when scrollable */}
            {chatHistory.length > 3 && (
              <div className="absolute bottom-0 left-0 right-0 h-8 bg-gradient-to-t from-gray-900/40 to-transparent pointer-events-none" />
            )}
          </div>
        )}

        {/* Chat Input */}
        <div className="p-4 border-t border-white/10">
          <div className="flex items-center space-x-3">
            <div className="flex-1 relative">
              <textarea
                value={customQuery}
                onChange={(e) => setCustomQuery(e.target.value)}
                onKeyDown={handleKeyPress}
                placeholder="Ask me anything: 'How do I turn 500K into 1M GP?' or 'What are the best potions to flip?'"
                className="w-full bg-white/10 border border-white/20 rounded-lg p-3 text-white placeholder-gray-400 resize-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                rows={2}
              />
              <div className="absolute bottom-2 right-2 text-xs text-gray-400">
                Press Enter to send, Shift+Enter for new line
              </div>
            </div>
            <Button
              variant="primary"
              onClick={handleCustomQuery}
              loading={processingCustomQuery}
              disabled={!customQuery.trim() || processingCustomQuery}
              icon={<Send className="w-4 h-4" />}
              className="bg-gradient-to-r from-purple-500 to-blue-600 hover:from-purple-600 hover:to-blue-700 px-6"
            >
              Ask AI
            </Button>
          </div>
          
          {/* Quick Examples */}
          <div className="mt-3 flex flex-wrap gap-2">
            <span className="text-gray-400 text-xs">Strategy examples:</span>
            {(() => {
              const strategyExamples = {
                high_alchemy: [
                  `Best high alch items for ${customCapital} GP`,
                  "Magic XP efficiency with profit analysis",
                  "Nature rune cost optimization strategies",
                  "Sustainable alching methods for long-term profit"
                ],
                decanting: [
                  `Decanting operations with ${customCapital} capital`,
                  "Best barbarian potions for profit margins",
                  "Volume scaling strategies for decanting",
                  "Competition analysis in potion markets"
                ],
                flipping: [
                  `${customCapital} flipping opportunities today`,
                  "Fast turnover items with reliable margins",
                  "Market timing strategies for max profit",
                  "Risk management for consistent flipping"
                ],
                crafting: [
                  `Profitable crafting with ${customCapital} budget`,
                  "Skill training methods that make profit",
                  "Material sourcing optimization",
                  "Seasonal crafting demand patterns"
                ],
                set_combining: [
                  `Set combining profits with ${customCapital}`,
                  "Equipment set assembly strategies",
                  "Premium pricing opportunities analysis",
                  "Market demand for complete sets"
                ],
                mixed_strategy: [
                  `Diversified portfolio with ${customCapital}`,
                  "Multi-strategy risk distribution",
                  "Portfolio optimization across all methods",
                  "Capital allocation recommendations"
                ]
              };
              
              return (strategyExamples[selectedStrategy as keyof typeof strategyExamples] || strategyExamples.mixed_strategy)
                .map((example, index) => (
                  <button
                    key={index}
                    onClick={() => setCustomQuery(example)}
                    className="text-xs bg-white/10 hover:bg-white/20 text-blue-300 px-2 py-1 rounded-lg transition-colors"
                  >
                    {example}
                  </button>
                ));
            })()}
          </div>
        </div>
      </motion.div>


      {/* Market Signals */}
      {marketSignals.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="space-y-4"
        >
          <h2 className="text-xl font-semibold text-white">Market Signals</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {marketSignals.map((signal, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.1 * index }}
              >
                <Card className="bg-white/5 border-white/10 hover:bg-white/10 transition-colors">
                  <div className="flex justify-between items-start mb-3">
                    <h4 className="font-semibold text-blue-300">{signal.signal_type}</h4>
                    <span className={`text-xs px-2 py-1 rounded-full ${
                      signal.strength === 'Strong' ? 'bg-green-500/20 text-green-300' :
                      signal.strength === 'Moderate' ? 'bg-yellow-500/20 text-yellow-300' :
                      'bg-blue-500/20 text-blue-300'
                    }`}>
                      {signal.strength}
                    </span>
                  </div>
                  <p className="text-white font-medium mb-2">{signal.item_name}</p>
                  <p className="text-gray-400 text-sm mb-2">{signal.reasoning}</p>
                  {signal.target_price && (
                    <p className="text-green-300 text-sm">Target: {formatGP(signal.target_price)}</p>
                  )}
                </Card>
              </motion.div>
            ))}
          </div>
        </motion.div>
      )}

      {/* Recommendations */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="space-y-6"
      >
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-white">
            Recommendations ({filteredRecommendations.length})
          </h2>
          <div className="text-sm text-gray-400">
            Strategy: {strategies[selectedStrategy as keyof typeof strategies]?.name} • Capital: {customCapital} GP • {riskFilter !== 'all' ? `${riskFilter} risk` : 'All risks'}
          </div>
        </div>

        {filteredRecommendations.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <div className="w-16 h-16 bg-blue-500/20 rounded-full flex items-center justify-center mb-4">
              <Target className="w-8 h-8 text-blue-400" />
            </div>
            <h3 className="text-lg font-semibold text-white mb-2">No Recommendations Found</h3>
            <p className="text-gray-400 mb-4">
              Try adjusting your capital amount or risk filter settings
            </p>
            <Button
              variant="primary"
              onClick={() => fetchRecommendations()}
              loading={refreshing}
              icon={<RefreshCw className="w-4 h-4" />}
            >
              Refresh Analysis
            </Button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-8">
            {filteredRecommendations.map((rec, index) => (
              <HolographicCard
                key={rec.item_id}
                recommendation={rec}
                index={index}
                formatGP={formatGP}
              />
            ))}
          </div>
        )}
      </motion.div>
      </div>
    </div>
  );
};