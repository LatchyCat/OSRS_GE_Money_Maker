import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  XMarkIcon, 
  PaperAirplaneIcon,
  SparklesIcon,
  LightBulbIcon,
  ChartBarIcon,
  CurrencyDollarIcon
} from '@heroicons/react/24/outline';
import { Shield, TrendingUp, AlertTriangle, CheckCircle } from 'lucide-react';
import type { SetCombiningOpportunity } from '../../types/tradingStrategies';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  type?: 'analysis' | 'recommendation' | 'warning' | 'success';
  metadata?: {
    recommendation_confidence?: number;
    risk_assessment?: string;
    suggested_items?: string[];
    market_conditions?: string;
  };
}

interface AISetCombiningAssistantProps {
  isOpen: boolean;
  onClose: () => void;
  opportunities: SetCombiningOpportunity[];
  currentCapital: number;
}

export function AISetCombiningAssistant({
  isOpen,
  onClose,
  opportunities,
  currentCapital
}: AISetCombiningAssistantProps) {
  // Helper function - must be declared before use in initial state
  const formatGP = (amount: number) => {
    if (amount >= 1000000) {
      return `${(amount / 1000000).toFixed(1)}M`;
    } else if (amount >= 1000) {
      return `${(amount / 1000).toFixed(1)}K`;
    }
    return Math.round(amount).toLocaleString();
  };

  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: `Welcome to your Set Combining AI Assistant! 🛡️

I'm here to help you maximize profits from armor set combining strategies. I can analyze:

• **Real-time Opportunities** - Current profitable set combinations
• **Risk Assessment** - Evaluate market volatility and trading risks  
• **Capital Optimization** - Best allocation of your ${formatGP(currentCapital)} GP
• **Timing Strategies** - When to buy sets vs individual pieces
• **Market Intelligence** - Price trends and volume analysis

Currently analyzing **${opportunities.length} active opportunities**. What would you like to know?`,
      timestamp: new Date(),
      type: 'analysis'
    }
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const callSetCombiningAI = async (userMessage: string): Promise<Message> => {
    try {
      // Add timeout to prevent long waits
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 120000); // 120 second timeout for small local models
      
      const response = await fetch('/api/ai/set-combining-chat/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        signal: controller.signal,
        body: JSON.stringify({
          query: userMessage,
          current_capital: currentCapital,
          opportunities: opportunities.slice(0, 20).map(opp => ({
            id: opp.id,
            set_name: opp.set_name,
            set_item_id: opp.set_item_id,
            lazy_tax_profit: opp.lazy_tax_profit,
            complete_set_price: opp.complete_set_price,
            individual_pieces_total_cost: opp.individual_pieces_total_cost,
            profit_margin_pct: opp.profit_margin_pct,
            piece_count: opp.piece_names.length,
            volume_score: (opp as any).volume_score,
            confidence_score: (opp as any).confidence_score,
            ai_risk_level: (opp as any).ai_risk_level,
            strategy_type: (opp as any).strategy_description?.includes('Buy individual pieces') ? 'combining' : 'decombining'
          }))
        })
      });
      
      clearTimeout(timeoutId);

      const data = await response.json();
      
      if (data.success) {
        return {
          id: Date.now().toString(),
          role: 'assistant',
          content: data.response,
          timestamp: new Date(),
          type: data.type || 'analysis',
          metadata: data.metadata
        };
      } else {
        throw new Error(data.error || 'AI response failed');
      }
    } catch (error) {
      console.error('Set Combining AI Error:', error);
      
      // Enhanced error handling with different messages based on error type
      let errorMessage = '';
      let errorType = 'analysis';
      
      if (error.name === 'AbortError') {
        errorMessage = `⏰ **Request Timeout**\n\nThe AI service is taking longer than expected. Here's some immediate guidance while we work on it:`;
        errorType = 'warning';
      } else if (error.message?.includes('500') || error.response?.status === 500) {
        errorMessage = `🔧 **AI Service Temporarily Unavailable**\n\nOur AI models are being optimized. Meanwhile, here's expert analysis:`;
        errorType = 'warning';
      } else if (error.message?.includes('Network Error') || error.code === 'ERR_NETWORK') {
        errorMessage = `📡 **Connection Issue**\n\nUnable to reach AI service. Here's offline guidance:`;
        errorType = 'warning';
      } else {
        errorMessage = `🤖 **AI Analysis Unavailable**\n\nDon't worry! I can still provide valuable insights:`;
        errorType = 'analysis';
      }
      
      return {
        id: Date.now().toString(),
        role: 'assistant',
        content: `${errorMessage}

**📊 Current Market Analysis:**
${opportunities.slice(0, 5).map((opp, i) => 
  `${i + 1}. **${opp.set_name}** - ${formatGP(opp.lazy_tax_profit)} GP profit (${opp.profit_margin_pct.toFixed(1)}% margin)`
).join('\n')}

**💡 Expert Trading Tips:**
• **Profit Threshold**: Focus on sets with 10%+ margins for safety
• **Volume Analysis**: Check trading activity before committing large capital
• **Risk Management**: Start with Barrows sets - they're stable and liquid
• **Market Timing**: Monitor price patterns for 1-2 hours before trading
• **Capital Allocation**: Never invest more than 30% in a single set type

**🎯 Quick Questions I Can Help With:**
• "What's the safest set to start with?"
• "How should I split my ${formatGP(currentCapital)} capital?"
• "Which sets have the best volume right now?"

Try asking a specific question - I'll do my best to help! 🚀`,
        timestamp: new Date(),
        type: errorType
      };
    }
  };

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: inputMessage.trim(),
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);

    try {
      const aiResponse = await callSetCombiningAI(userMessage.content);
      setMessages(prev => [...prev, aiResponse]);
    } catch (error) {
      console.error('Error sending message:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const getMessageIcon = (type?: string) => {
    switch (type) {
      case 'recommendation': return <LightBulbIcon className="w-5 h-5 text-yellow-400" />;
      case 'warning': return <AlertTriangle className="w-5 h-5 text-orange-400" />;
      case 'success': return <CheckCircle className="w-5 h-5 text-green-400" />;
      default: return <SparklesIcon className="w-5 h-5 text-blue-400" />;
    }
  };

  const getMessageBorder = (type?: string) => {
    switch (type) {
      case 'recommendation': return 'border-yellow-500/30';
      case 'warning': return 'border-orange-500/30';
      case 'success': return 'border-green-500/30';
      default: return 'border-blue-500/30';
    }
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
        onClick={onClose}
      >
        <motion.div
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.9, opacity: 0 }}
          onClick={(e) => e.stopPropagation()}
          className="bg-gray-900 border border-gray-700 rounded-2xl w-full max-w-4xl h-[80vh] flex flex-col shadow-2xl"
        >
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-gray-700">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-indigo-500/20 rounded-lg">
                <Shield className="w-6 h-6 text-indigo-400" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-white">Set Combining AI Assistant</h2>
                <p className="text-sm text-gray-400">
                  Specialized guidance for armor set trading strategies
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
            >
              <XMarkIcon className="w-6 h-6 text-gray-400" />
            </button>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            {messages.map((message) => (
              <motion.div
                key={message.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className={`flex gap-3 ${
                  message.role === 'user' ? 'justify-end' : 'justify-start'
                }`}
              >
                {message.role === 'assistant' && (
                  <div className="flex-shrink-0 p-2 bg-indigo-500/20 rounded-lg">
                    {getMessageIcon(message.type)}
                  </div>
                )}
                
                <div
                  className={`max-w-[70%] rounded-xl p-4 ${
                    message.role === 'user'
                      ? 'bg-indigo-600 text-white'
                      : `bg-gray-800 border ${getMessageBorder(message.type)} text-gray-100`
                  }`}
                >
                  <div className="whitespace-pre-wrap text-sm leading-relaxed">
                    {message.content}
                  </div>
                  
                  {message.metadata && (
                    <div className="mt-3 pt-3 border-t border-gray-600/50 space-y-2">
                      {message.metadata.recommendation_confidence && (
                        <div className="flex items-center gap-2 text-xs">
                          <ChartBarIcon className="w-4 h-4 text-blue-400" />
                          <span className="text-gray-400">Confidence:</span>
                          <span className="text-blue-400">
                            {Math.round(message.metadata.recommendation_confidence * 100)}%
                          </span>
                        </div>
                      )}
                      {message.metadata.risk_assessment && (
                        <div className="flex items-center gap-2 text-xs">
                          <Shield className="w-4 h-4 text-yellow-400" />
                          <span className="text-gray-400">Risk Level:</span>
                          <span className="text-yellow-400">{message.metadata.risk_assessment}</span>
                        </div>
                      )}
                    </div>
                  )}
                  
                  <div className="flex items-center justify-between mt-2 text-xs text-gray-500">
                    <span>{message.timestamp.toLocaleTimeString()}</span>
                  </div>
                </div>

                {message.role === 'user' && (
                  <div className="flex-shrink-0 w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center">
                    <span className="text-white text-sm font-medium">You</span>
                  </div>
                )}
              </motion.div>
            ))}
            
            {isLoading && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex gap-3 justify-start"
              >
                <div className="flex-shrink-0 p-2 bg-indigo-500/20 rounded-lg">
                  <SparklesIcon className="w-5 h-5 text-blue-400 animate-pulse" />
                </div>
                <div className="bg-gray-800 border border-blue-500/30 rounded-xl p-4">
                  <div className="flex items-center gap-2 text-sm text-gray-400">
                    <div className="flex space-x-1">
                      <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce"></div>
                      <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                      <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                    </div>
                    <span>Analyzing set combining strategies...</span>
                  </div>
                </div>
              </motion.div>
            )}
          </div>

          {/* Input */}
          <div className="border-t border-gray-700 p-6">
            <div className="flex gap-3">
              <div className="flex-1 relative">
                <textarea
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Ask about set combining strategies, risk analysis, or specific opportunities..."
                  className="w-full px-4 py-3 bg-gray-800 border border-gray-600 rounded-xl text-white placeholder-gray-400 resize-none focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500/50"
                  rows={2}
                  disabled={isLoading}
                />
              </div>
              <button
                onClick={handleSendMessage}
                disabled={!inputMessage.trim() || isLoading}
                className="flex items-center justify-center px-6 py-3 bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-800 disabled:opacity-50 text-white rounded-xl transition-colors"
              >
                <PaperAirplaneIcon className="w-5 h-5" />
              </button>
            </div>
            
            {/* Quick Actions */}
            <div className="flex gap-2 mt-4 flex-wrap">
              <button
                onClick={() => setInputMessage('What are the most profitable armor sets to trade right now?')}
                className="px-3 py-1.5 bg-gray-700/50 hover:bg-gray-600/50 border border-gray-600/50 rounded-lg text-sm text-gray-300 transition-colors"
              >
                💰 Top Profits
              </button>
              <button
                onClick={() => setInputMessage('How should I allocate my capital across different sets?')}
                className="px-3 py-1.5 bg-gray-700/50 hover:bg-gray-600/50 border border-gray-600/50 rounded-lg text-sm text-gray-300 transition-colors"
              >
                📊 Capital Strategy
              </button>
              <button
                onClick={() => setInputMessage('What are the risks with current market conditions?')}
                className="px-3 py-1.5 bg-gray-700/50 hover:bg-gray-600/50 border border-gray-600/50 rounded-lg text-sm text-gray-300 transition-colors"
              >
                ⚠️ Risk Analysis
              </button>
              <button
                onClick={() => setInputMessage('Should I focus on combining pieces or decombining sets?')}
                className="px-3 py-1.5 bg-gray-700/50 hover:bg-gray-600/50 border border-gray-600/50 rounded-lg text-sm text-gray-300 transition-colors"
              >
                🔄 Strategy Choice
              </button>
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}

export default AISetCombiningAssistant;