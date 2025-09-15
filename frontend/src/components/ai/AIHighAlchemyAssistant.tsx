import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ChatBubbleLeftRightIcon,
  PaperAirplaneIcon,
  XMarkIcon,
  SparklesIcon,
  BoltIcon,
  CurrencyDollarIcon,
  ChartBarIcon,
  LightBulbIcon,
  ArrowTrendingUpIcon,
  ExclamationCircleIcon,
  CheckCircleIcon,
  BeakerIcon,
  FireIcon
} from '@heroicons/react/24/outline';
import { Wand2 } from 'lucide-react';
import type { Item } from '../../types';

// Helper function to format GP values
const formatGP = (amount: number) => {
  if (amount >= 1000000000) return `${(amount / 1000000000).toFixed(1)}B GP`;
  if (amount >= 1000000) return `${(amount / 1000000).toFixed(1)}M GP`;
  if (amount >= 1000) return `${(amount / 1000).toFixed(1)}K GP`;
  return `${Math.round(amount)} GP`;
};

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  type?: 'suggestion' | 'warning' | 'celebration' | 'analysis' | 'alchemy';
  data?: any;
  metadata?: {
    model_used?: string;
    context_items?: number;
    profitable_items?: number;
    capital?: number;
    nature_rune_price?: number;
  };
}


interface AIHighAlchemyAssistantProps {
  isOpen: boolean;
  onClose: () => void;
  items: Item[];
  currentCapital?: number;
  natureRunePrice?: number;
}

export const AIHighAlchemyAssistant: React.FC<AIHighAlchemyAssistantProps> = ({
  isOpen,
  onClose,
  items,
  currentCapital = 1000000,
  natureRunePrice = 180
}) => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: `Welcome to the High Alchemy Intelligence Center! 🔥 I'm your expert advisor for all things high alchemy!

I have access to current market data for ${items.length} potential alchemy targets. Nature runes are currently ${natureRunePrice} GP each - I'll factor that into all my calculations.

What would you like to explore? I can help with:
• **Item Analysis** - Finding the most profitable items
• **Strategy Planning** - XP efficiency vs profit optimization  
• **Market Insights** - Understanding price trends and timing
• **Budget Planning** - Maximizing your available capital (just tell me your budget!)

Ask me anything about high alchemy!`,
      timestamp: new Date(),
      type: 'alchemy'
    }
  ]);
  
  // Removed conversation context - AI now handles context intelligently
  
  const [inputValue, setInputValue] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  // Simple fallback stats calculation (only used when AI is unavailable)
  const getBasicStats = () => {
    const profitableItems = items.filter(item => {
      const profit = (item.high_alch || 0) - (item.current_buy_price || 0) - natureRunePrice;
      return profit > 0;
    });
    
    const bestProfitItem = items.reduce((best, item) => {
      const itemProfit = (item.high_alch || 0) - (item.current_buy_price || 0) - natureRunePrice;
      const bestProfit = (best.high_alch || 0) - (best.current_buy_price || 0) - natureRunePrice;
      return itemProfit > bestProfit ? item : best;
    });
    
    return { profitableCount: profitableItems.length, bestProfitItem };
  };

  // AI API call function using local models
  const callHighAlchemyAI = async (userMessage: string): Promise<Message> => {
    try {
      const response = await fetch('/api/high-alchemy-chat/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: userMessage,
          // Don't send budget unless user explicitly mentions one
          // currentCapital,
          natureRunePrice,
          items: items.map(item => ({
            id: item.item_id || 0,
            name: item.name || 'Unknown',
            current_buy_price: item.current_buy_price || 0,
            high_alch: item.high_alch || 0,
            limit: item.limit || 0,
            members: item.members || false,
            recommendation_score: item.recommendation_score || 0,
            daily_volume: item.daily_volume || 0
          }))
        })
      });

      const data = await response.json();
      
      if (data.success) {
        return {
          id: Date.now().toString(),
          role: 'assistant',
          content: data.response,
          timestamp: new Date(),
          type: 'analysis',
          metadata: data.metadata
        };
      } else {
        throw new Error(data.error || 'AI response failed');
      }
    } catch (error) {
      console.error('High Alchemy AI Error:', error);
      
      // Fallback response if AI fails
      const stats = getBasicStats();
      return {
        id: Date.now().toString(),
        role: 'assistant',
        content: `I'm having trouble connecting to my AI brain right now! 🤔 But I can still help with basic info:

**Quick Analysis:**
• ${stats.profitableCount} items are currently profitable
• Best profit: ${stats.bestProfitItem.name} (${formatGP((stats.bestProfitItem.high_alch || 0) - (stats.bestProfitItem.current_buy_price || 0) - natureRunePrice)}/cast)
• Your budget: ${formatGP(currentCapital)}
• Nature runes: ${formatGP(natureRunePrice)} each

Try asking again in a moment - I should be back online soon!`,
        timestamp: new Date(),
        type: 'warning'
      };
    }
  };

  const handleSendMessage = async () => {
    if (!inputValue.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: inputValue,
      timestamp: new Date()
    };

    const queryText = inputValue;
    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsTyping(true);

    try {
      // Call intelligent AI instead of template responses
      const aiResponse = await callHighAlchemyAI(queryText);
      setMessages(prev => [...prev, aiResponse]);
    } catch (error) {
      console.error('AI chat error:', error);
      const errorMessage: Message = {
        id: Date.now().toString(),
        role: 'assistant',
        content: 'Sorry, I encountered an error processing your request. Please try again.',
        timestamp: new Date(),
        type: 'warning'
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const getMessageIcon = (type?: Message['type']) => {
    switch (type) {
      case 'suggestion':
        return <LightBulbIcon className="w-4 h-4 text-yellow-400" />;
      case 'warning':
        return <ExclamationCircleIcon className="w-4 h-4 text-orange-400" />;
      case 'celebration':
        return <CheckCircleIcon className="w-4 h-4 text-green-400" />;
      case 'analysis':
        return <ChartBarIcon className="w-4 h-4 text-blue-400" />;
      case 'alchemy':
        return <Wand2 className="w-4 h-4 text-purple-400" />;
      default:
        return <SparklesIcon className="w-4 h-4 text-purple-400" />;
    }
  };

  const quickActions = [
    { text: "What's the most profitable item right now?", icon: CurrencyDollarIcon },
    { text: "How much XP can I get with 1M budget?", icon: BoltIcon },
    { text: "Show me the safest alchemy options", icon: ExclamationCircleIcon },
    { text: "How do I start high alching efficiently?", icon: FireIcon }
  ];

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
          className="bg-gray-900 border border-gray-700 rounded-2xl w-[72rem] max-w-[90vw] h-[50rem] max-h-[90vh] flex flex-col shadow-2xl"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="p-4 border-b border-gray-700 bg-gradient-to-r from-yellow-900/20 to-orange-900/20 rounded-t-2xl">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-yellow-500/20 rounded-lg">
                  <Wand2 className="w-6 h-6 text-yellow-400" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-white">AI High Alchemy Master</h3>
                  <p className="text-sm text-gray-400">Your personal OSRS alchemy optimization expert</p>
                </div>
              </div>
              <button
                onClick={onClose}
                className="p-2 hover:bg-gray-700 rounded-lg transition-colors"
              >
                <XMarkIcon className="w-5 h-5 text-gray-400" />
              </button>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.map((message) => (
              <motion.div
                key={message.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div className={`max-w-[75%] ${
                  message.role === 'user'
                    ? 'bg-yellow-600 text-white'
                    : 'bg-gray-800 text-gray-100'
                } rounded-2xl px-6 py-4 shadow-lg`}>
                  {message.role === 'assistant' && (
                    <div className="flex items-center gap-2 mb-2 text-xs opacity-75">
                      {getMessageIcon(message.type)}
                      <span>Alchemy AI</span>
                    </div>
                  )}
                  <div className="whitespace-pre-wrap text-base leading-relaxed">
                    {message.content}
                  </div>
                  <div className="text-xs opacity-50 mt-2">
                    {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </div>
                </div>
              </motion.div>
            ))}
            
            {/* Typing Indicator */}
            {isTyping && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex justify-start"
              >
                <div className="bg-gray-800 rounded-2xl px-4 py-3 shadow-lg">
                  <div className="flex items-center gap-2 text-gray-400">
                    <Wand2 className="w-4 h-4 animate-pulse" />
                    <div className="flex gap-1">
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }} />
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
                    </div>
                  </div>
                </div>
              </motion.div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Quick Actions */}
          {messages.length <= 2 && (
            <div className="px-6 py-4 border-t border-gray-700/50">
              <div className="text-sm text-gray-500 mb-3">Try asking:</div>
              <div className="grid grid-cols-2 gap-3">
                {quickActions.map((action, index) => (
                  <button
                    key={index}
                    onClick={() => setInputValue(action.text)}
                    className="flex items-center gap-2 px-4 py-3 bg-gray-800 hover:bg-gray-700 rounded-xl text-sm text-gray-300 transition-colors text-left"
                  >
                    <action.icon className="w-4 h-4 flex-shrink-0" />
                    <span>{action.text}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Input */}
          <div className="p-6 border-t border-gray-700">
            <div className="flex gap-3">
              <input
                ref={inputRef}
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Ask about high alchemy strategies, profits, or XP rates..."
                className="flex-1 bg-gray-800 border border-gray-600 rounded-xl px-4 py-3 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-yellow-500/50 focus:border-yellow-500/50"
                disabled={isTyping}
              />
              <button
                onClick={handleSendMessage}
                disabled={!inputValue.trim() || isTyping}
                className="bg-yellow-600 hover:bg-yellow-700 disabled:bg-gray-700 disabled:opacity-50 text-white p-3 rounded-xl transition-colors"
              >
                <PaperAirplaneIcon className="w-5 h-5" />
              </button>
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};

export default AIHighAlchemyAssistant;