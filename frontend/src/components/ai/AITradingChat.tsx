import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Send, Copy, RotateCcw, ThumbsUp, Brain, TrendingUp } from 'lucide-react';
import { useLocation } from 'react-router-dom';

interface Message {
  id: string;
  text: string;
  sender: 'user' | 'assistant';
  timestamp: Date;
  opportunities?: PrecisionOpportunity[];
  signals?: MarketSignal[];
  confidence_score?: number;
  processing_time?: number;
  query_intent?: string;
  ai_model_used?: string;
  relevant_items?: any[];
  trading_recommendations?: any[];
  market_insights?: any[];
  suggested_follow_ups?: string[];
  warning_flags?: string[];
}

interface PrecisionOpportunity {
  item_id: number;
  item_name: string;
  current_price: number;
  recommended_buy_price: number;
  recommended_sell_price: number;
  expected_profit_per_item: number;
  expected_profit_margin_pct: number;
  success_probability_pct: number;
  risk_level: string;
  estimated_hold_time_hours: number;
}

interface MarketSignal {
  signal_type: string;
  item_name: string;
  strength: string;
  reasoning: string;
  target_price?: number;
}

const AITradingChat: React.FC = () => {
  const location = useLocation();
  
  // Determine current trading view from URL path
  const getCurrentTradingView = useCallback(() => {
    const path = location.pathname;
    if (path.includes('high-alchemy')) return 'high-alchemy';
    if (path.includes('flipping')) return 'flipping';
    if (path.includes('decanting')) return 'decanting';
    if (path.includes('crafting')) return 'crafting';
    if (path.includes('set-combining')) return 'set-combining';
    if (path.includes('bond-flipping')) return 'bond-flipping';
    if (path.includes('magic-runes')) return 'magic-runes';
    return 'general';
  }, [location.pathname]);

  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      text: `🧠 **Context-Aware AI Trading Assistant Ready!**

I provide intelligent, context-aware analysis using:

🎯 **FAISS Similarity Search:** Find similar profitable opportunities
🧮 **Volume Analysis:** Real trading volume and confidence scoring  
📊 **Market Intelligence:** Deep insights from RuneScape Wiki data
🤖 **Multi-Model AI:** Powered by local Ollama models (Deepseek-R1, Gemma2)
🔍 **Context Awareness:** Tailored responses based on your current trading view

*I understand your current trading strategy and provide relevant, actionable advice!*`,
      sender: 'assistant',
      timestamp: new Date(),
      confidence_score: 1.0,
      ai_model_used: 'context-aware-system'
    }
  ]);
  
  const [currentMessage, setCurrentMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(scrollToBottom, [messages]);

  const adjustTextareaHeight = () => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      const newHeight = Math.min(textarea.scrollHeight, 120);
      textarea.style.height = newHeight + 'px';
    }
  };

  useEffect(() => {
    adjustTextareaHeight();
  }, [currentMessage]);

  const formatGP = (amount: number): string => {
    if (amount >= 1000000) {
      return (amount / 1000000).toFixed(1) + 'M GP';
    } else if (amount >= 1000) {
      return (amount / 1000).toFixed(1) + 'K GP';
    }
    return amount.toLocaleString() + ' GP';
  };

  const sendMessage = async (messageText?: string) => {
    const text = messageText || currentMessage.trim();
    if (!text || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      text,
      sender: 'user',
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setCurrentMessage('');
    setIsLoading(true);

    try {
      // Use the new context-aware chat API
      const currentView = getCurrentTradingView();
      const response = await fetch('/api/ai/chat/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          message: text,
          current_view: currentView,
          session_id: `session-${Date.now()}`,
          include_volume_analysis: true,
          max_results: 10,
          confidence_threshold: 0.6
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: data.message || 'No response generated',
        sender: 'assistant',
        timestamp: new Date(),
        confidence_score: data.confidence_score,
        processing_time: data.processing_time,
        query_intent: data.query_intent,
        ai_model_used: data.ai_model_used,
        relevant_items: data.relevant_items || [],
        trading_recommendations: data.trading_recommendations || [],
        market_insights: data.market_insights || [],
        suggested_follow_ups: data.suggested_follow_ups || [],
        warning_flags: data.warning_flags || [],
        // Keep backward compatibility with existing display logic
        opportunities: data.trading_recommendations || [],
        signals: data.market_insights || []
      };

      setMessages(prev => [...prev, aiMessage]);

    } catch (error) {
      console.error('Error:', error);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: '❌ Sorry, I encountered an error processing your request. The AI system may be initializing. Please try again in a moment.',
        sender: 'assistant',
        timestamp: new Date(),
        confidence_score: 0.1
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const copyMessage = async (text: string, buttonId: string) => {
    try {
      await navigator.clipboard.writeText(text);
      // Visual feedback could be added here
    } catch (error) {
      console.error('Failed to copy:', error);
    }
  };

  const regenerateMessage = (messageId: string) => {
    const messageIndex = messages.findIndex(m => m.id === messageId);
    const previousMessage = messages[messageIndex - 1];
    
    if (previousMessage && previousMessage.sender === 'user') {
      sendMessage(previousMessage.text);
    }
  };

  const getContextualQuickMessages = useCallback(() => {
    const currentView = getCurrentTradingView();
    
    const baseMessages = [
      'What are the best opportunities right now?',
      'Show me items with high confidence scores',
      'Find similar items to profitable ones I should know about'
    ];
    
    const viewSpecificMessages = {
      'high-alchemy': [
        'What items have the best high alchemy profit margins?',
        'Show me nature rune costs vs high alch profits',
        'Which items are profitable to alch with current prices?'
      ],
      'flipping': [
        'What are the best flipping opportunities right now?',
        'Show me items with high volume and good margins',
        'Find items with predictable price patterns'
      ],
      'decanting': [
        'What potions are best for decanting profit?',
        'Show me current decanting margins and volumes',
        'Which decantable items have the highest profit per hour?'
      ],
      'crafting': [
        'What are the most profitable crafting methods?',
        'Show me materials vs finished product profits',
        'Which crafting items have consistent demand?'
      ],
      'set-combining': [
        'What armor sets are profitable to combine right now?',
        'Show me individual piece prices vs set prices',
        'Which sets have the best profit margins?'
      ],
      'magic-runes': [
        'What runes are most profitable for magic training?',
        'Show me rune costs vs spell profitability',
        'Which magical methods give best GP/XP?'
      ],
      'general': baseMessages
    };
    
    return [...baseMessages, ...(viewSpecificMessages[currentView] || baseMessages)];
  }, [getCurrentTradingView]);

  const suggestionTags = [
    'Analyze market trends and give me 3 recommendations with confidence scores',
    'Show me volume-weighted opportunities similar to profitable items',
    'What should I know about current market conditions?',
    'Find opportunities with 80%+ confidence and explain your reasoning'
  ];

  return (
    <div className="flex flex-col h-full bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900 relative overflow-hidden">
      {/* Background Effects */}
      <div className="absolute inset-0 bg-gradient-to-br from-blue-500/10 via-purple-500/10 to-cyan-500/10"></div>
      <div className="absolute top-20 left-20 w-32 h-32 bg-blue-500/20 rounded-full blur-xl animate-pulse"></div>
      <div className="absolute bottom-40 right-20 w-40 h-40 bg-purple-500/20 rounded-full blur-xl animate-pulse delay-700"></div>
      
      {/* Chat Container */}
      <div className="relative z-10 flex flex-col h-full bg-white/5 backdrop-blur-3xl border border-white/10 rounded-2xl m-4 overflow-hidden shadow-2xl">
        
        {/* Header */}
        <div className="relative px-6 py-4 bg-gradient-to-r from-blue-500/20 to-purple-500/20 backdrop-blur-3xl border-b border-white/10 overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-r from-blue-500/10 to-purple-500/10 animate-pulse"></div>
          <div className="relative z-10 text-center">
            <h2 className="text-xl font-bold bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">
              🧠 Context-Aware AI Assistant
            </h2>
            <div className="flex items-center justify-center gap-2 mt-1">
              <span className="text-sm text-blue-200/80">Current View:</span>
              <span className="px-2 py-1 text-xs bg-blue-500/20 border border-blue-400/30 rounded-full text-blue-300 font-semibold">
                {getCurrentTradingView().replace('-', ' ').toUpperCase()}
              </span>
            </div>
            <p className="text-xs text-blue-200/60 mt-1">
              Powered by FAISS similarity search & local AI models
            </p>
          </div>
        </div>

        {/* Suggestions */}
        <div className="px-6 py-3 bg-gradient-to-r from-blue-500/5 to-purple-500/5 border-b border-white/10">
          <div className="text-xs text-blue-200/70 mb-2">💡 Try asking complex questions like:</div>
          <div className="flex flex-wrap gap-2">
            {suggestionTags.map((tag, index) => (
              <button
                key={index}
                onClick={() => sendMessage(tag)}
                className="px-2 py-1 text-xs bg-white/10 backdrop-blur-sm border border-white/20 rounded-lg text-blue-200 hover:bg-blue-500/20 hover:border-blue-400/30 transition-all duration-300 hover:scale-105"
              >
                {tag.length > 40 ? tag.substring(0, 40) + '...' : tag}
              </button>
            ))}
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4 scrollbar-thin scrollbar-thumb-white/20 scrollbar-track-transparent">
          {messages.map((message) => (
            <div key={message.id} className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-4xl ${message.sender === 'user' ? 'text-right' : 'text-left'}`}>
                <div
                  className={`inline-block px-4 py-3 rounded-2xl backdrop-blur-sm transition-all duration-300 hover:scale-[1.02] ${
                    message.sender === 'user'
                      ? 'bg-gradient-to-r from-blue-500/20 to-purple-500/20 border border-blue-400/30 text-blue-100'
                      : 'bg-white/10 border border-white/20 text-white'
                  }`}
                >
                  <div className="whitespace-pre-wrap text-sm leading-relaxed">
                    {message.text.split('**').map((part, index) => 
                      index % 2 === 0 ? part : <strong key={index} className="font-semibold text-blue-300">{part}</strong>
                    )}
                  </div>
                  
                  {/* Opportunities */}
                  {message.opportunities && message.opportunities.length > 0 && (
                    <div className="mt-4 space-y-3">
                      {message.opportunities.map((opp, index) => (
                        <div key={index} className="bg-white/5 backdrop-blur-sm border border-green-400/30 rounded-xl p-4">
                          <div className="flex justify-between items-center mb-3">
                            <h4 className="font-semibold text-green-300">{opp.item_name}</h4>
                            <span className="text-xs bg-green-500/20 text-green-300 px-2 py-1 rounded-full">
                              {opp.success_probability_pct}% Success
                            </span>
                          </div>
                          <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-xs">
                            <div className="text-center">
                              <div className="text-gray-400">Current Price</div>
                              <div className="font-semibold text-white">{formatGP(opp.current_price)}</div>
                            </div>
                            <div className="text-center">
                              <div className="text-gray-400">Buy At</div>
                              <div className="font-semibold text-green-300">{formatGP(opp.recommended_buy_price)}</div>
                            </div>
                            <div className="text-center">
                              <div className="text-gray-400">Sell At</div>
                              <div className="font-semibold text-green-300">{formatGP(opp.recommended_sell_price)}</div>
                            </div>
                            <div className="text-center">
                              <div className="text-gray-400">Profit Per Item</div>
                              <div className="font-semibold text-green-300">+{formatGP(opp.expected_profit_per_item)}</div>
                            </div>
                            <div className="text-center">
                              <div className="text-gray-400">Risk Level</div>
                              <div className={`font-semibold ${opp.risk_level === 'low' ? 'text-green-300' : opp.risk_level === 'medium' ? 'text-yellow-300' : 'text-red-300'}`}>
                                {opp.risk_level.toUpperCase()}
                              </div>
                            </div>
                            <div className="text-center">
                              <div className="text-gray-400">Hold Time</div>
                              <div className="font-semibold text-white">{opp.estimated_hold_time_hours.toFixed(1)}h</div>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Market Signals */}
                  {message.signals && message.signals.length > 0 && (
                    <div className="mt-4 space-y-2">
                      {message.signals.map((signal, index) => (
                        <div key={index} className="bg-white/5 backdrop-blur-sm border border-blue-400/30 rounded-xl p-3">
                          <div className="flex justify-between items-center mb-1">
                            <span className="font-semibold text-blue-300">{signal.signal_type}: {signal.item_name}</span>
                            <span className={`text-xs px-2 py-1 rounded-full ${
                              signal.strength === 'Strong' ? 'bg-green-500/20 text-green-300' :
                              signal.strength === 'Moderate' ? 'bg-yellow-500/20 text-yellow-300' :
                              'bg-blue-500/20 text-blue-300'
                            }`}>
                              {signal.strength}
                            </span>
                          </div>
                          <div className="text-xs text-gray-300">{signal.reasoning}</div>
                          {signal.target_price && (
                            <div className="text-xs text-blue-300 mt-1">Target: {formatGP(signal.target_price)}</div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Enhanced AI Features */}
                  {message.sender === 'assistant' && (
                    <div className="mt-4 space-y-3">
                      {/* AI Metadata */}
                      {(message.confidence_score || message.processing_time || message.ai_model_used) && (
                        <div className="bg-white/5 backdrop-blur-sm border border-purple-400/30 rounded-xl p-3">
                          <div className="flex items-center gap-2 mb-2">
                            <Brain className="w-4 h-4 text-purple-400" />
                            <span className="text-sm font-semibold text-purple-300">AI Analysis</span>
                          </div>
                          <div className="grid grid-cols-1 md:grid-cols-3 gap-2 text-xs">
                            {message.confidence_score && (
                              <div className="text-center">
                                <div className="text-gray-400">Confidence</div>
                                <div className={`font-semibold ${
                                  message.confidence_score >= 0.8 ? 'text-green-300' :
                                  message.confidence_score >= 0.6 ? 'text-yellow-300' : 'text-red-300'
                                }`}>
                                  {(message.confidence_score * 100).toFixed(1)}%
                                </div>
                              </div>
                            )}
                            {message.processing_time && (
                              <div className="text-center">
                                <div className="text-gray-400">Processing Time</div>
                                <div className="font-semibold text-white">{message.processing_time.toFixed(2)}s</div>
                              </div>
                            )}
                            {message.ai_model_used && (
                              <div className="text-center">
                                <div className="text-gray-400">AI Model</div>
                                <div className="font-semibold text-blue-300">{message.ai_model_used}</div>
                              </div>
                            )}
                          </div>
                          {message.query_intent && (
                            <div className="mt-2 text-xs text-purple-200">
                              <span className="text-gray-400">Intent:</span> {message.query_intent}
                            </div>
                          )}
                        </div>
                      )}

                      {/* Trading Recommendations */}
                      {message.trading_recommendations && message.trading_recommendations.length > 0 && (
                        <div className="bg-white/5 backdrop-blur-sm border border-green-400/30 rounded-xl p-3">
                          <div className="flex items-center gap-2 mb-2">
                            <TrendingUp className="w-4 h-4 text-green-400" />
                            <span className="text-sm font-semibold text-green-300">Smart Recommendations</span>
                          </div>
                          <div className="space-y-2">
                            {message.trading_recommendations.slice(0, 3).map((rec, index) => (
                              <div key={index} className="text-xs bg-green-500/10 rounded-lg p-2">
                                <div className="font-semibold text-green-200">{rec.title || rec.item_name}</div>
                                <div className="text-green-100">{rec.description || rec.reasoning}</div>
                                {rec.profit_potential && (
                                  <div className="text-green-300 mt-1">Potential: {formatGP(rec.profit_potential)}</div>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Warning Flags */}
                      {message.warning_flags && message.warning_flags.length > 0 && (
                        <div className="bg-red-500/10 border border-red-400/30 rounded-xl p-3">
                          <div className="text-sm font-semibold text-red-300 mb-2">⚠️ Important Considerations</div>
                          <div className="space-y-1">
                            {message.warning_flags.map((warning, index) => (
                              <div key={index} className="text-xs text-red-200">• {warning}</div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Suggested Follow-ups */}
                      {message.suggested_follow_ups && message.suggested_follow_ups.length > 0 && (
                        <div className="bg-white/5 backdrop-blur-sm border border-cyan-400/30 rounded-xl p-3">
                          <div className="text-sm font-semibold text-cyan-300 mb-2">💡 Ask me next:</div>
                          <div className="flex flex-wrap gap-2">
                            {message.suggested_follow_ups.slice(0, 4).map((followUp, index) => (
                              <button
                                key={index}
                                onClick={() => sendMessage(followUp)}
                                className="px-2 py-1 text-xs bg-cyan-500/20 border border-cyan-400/30 rounded-lg text-cyan-200 hover:bg-cyan-500/30 transition-colors"
                              >
                                {followUp.length > 30 ? followUp.substring(0, 30) + '...' : followUp}
                              </button>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
                
                {/* Message Actions */}
                {message.sender === 'assistant' && (
                  <div className="flex gap-2 mt-2 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={() => copyMessage(message.text, `copy-${message.id}`)}
                      className="flex items-center gap-1 px-2 py-1 text-xs bg-white/10 backdrop-blur-sm border border-white/20 rounded-lg text-gray-300 hover:bg-white/20 hover:text-white transition-colors"
                    >
                      <Copy className="w-3 h-3" />
                      Copy
                    </button>
                    <button
                      onClick={() => regenerateMessage(message.id)}
                      className="flex items-center gap-1 px-2 py-1 text-xs bg-white/10 backdrop-blur-sm border border-white/20 rounded-lg text-gray-300 hover:bg-white/20 hover:text-white transition-colors"
                    >
                      <RotateCcw className="w-3 h-3" />
                      Regenerate
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}
          
          {/* Loading Indicator */}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-white/10 backdrop-blur-sm border border-white/20 rounded-2xl px-4 py-3">
                <div className="flex items-center gap-2 text-blue-200">
                  <Brain className="w-4 h-4 animate-pulse text-purple-400" />
                  <div className="w-2 h-2 bg-blue-400 rounded-full animate-pulse"></div>
                  <div className="w-2 h-2 bg-purple-400 rounded-full animate-pulse delay-100"></div>
                  <div className="w-2 h-2 bg-cyan-400 rounded-full animate-pulse delay-200"></div>
                  <span className="text-sm ml-2">AI is searching embeddings & analyzing patterns...</span>
                </div>
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="p-6 bg-gradient-to-r from-blue-500/10 to-purple-500/10 backdrop-blur-3xl border-t border-white/10">
          {/* Quick Actions */}
          <div className="flex flex-wrap gap-2 mb-4">
            {getContextualQuickMessages().slice(0, 3).map((msg, index) => (
              <button
                key={index}
                onClick={() => sendMessage(msg)}
                className="px-3 py-1 text-xs bg-white/10 backdrop-blur-sm border border-white/20 rounded-full text-blue-200 hover:bg-blue-500/20 hover:border-blue-400/30 transition-all duration-300 hover:scale-105"
              >
                {msg.length > 35 ? msg.substring(0, 35) + '...' : msg}
              </button>
            ))}
          </div>
          
          <form onSubmit={(e) => { e.preventDefault(); sendMessage(); }} className="flex gap-3">
            <textarea
              ref={textareaRef}
              value={currentMessage}
              onChange={(e) => setCurrentMessage(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  sendMessage();
                }
              }}
              placeholder="Ask me about trading opportunities... (e.g., 'I have 50M GP, what should I buy at 1k to sell at 1.5k?')"
              className="flex-1 min-h-[48px] max-h-[120px] px-4 py-3 bg-white/10 backdrop-blur-sm border border-white/20 rounded-xl text-white placeholder-gray-400 resize-none focus:outline-none focus:border-blue-400/50 focus:bg-white/15 transition-all duration-300"
              rows={1}
              disabled={isLoading}
            />
            <button
              type="submit"
              disabled={!currentMessage.trim() || isLoading}
              className="px-6 py-3 bg-gradient-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-xl transition-all duration-300 hover:scale-105 backdrop-blur-sm shadow-lg"
            >
              <Send className="w-5 h-5" />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default AITradingChat;