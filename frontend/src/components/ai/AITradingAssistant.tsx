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
  CheckCircleIcon
} from '@heroicons/react/24/outline';
import type { DecantingOpportunity } from '../../types/tradingStrategies';

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
  type?: 'suggestion' | 'warning' | 'celebration' | 'analysis';
  data?: any; // Additional context data
}

interface ConversationContext {
  userBudget?: number;
  mentionedItems?: string[];
  askedAboutBest?: boolean;
  askedAboutRisk?: boolean;
  askedAboutSteps?: boolean;
  userName?: string;
  conversationStage: 'greeting' | 'exploring' | 'detailed' | 'advanced';
}

interface AITradingAssistantProps {
  isOpen: boolean;
  onClose: () => void;
  opportunities: DecantingOpportunity[];
  currentCapital?: number;
}

export const AITradingAssistant: React.FC<AITradingAssistantProps> = ({
  isOpen,
  onClose,
  opportunities,
  currentCapital = 1000000
}) => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: `Hey there! I'm here to help you make sense of these ${opportunities.length} decanting opportunities. I can see you have ${formatGP(currentCapital)} to work with - that's a solid budget to start with. What's on your mind?`,
      timestamp: new Date(),
      type: 'suggestion'
    }
  ]);
  
  const [conversationContext, setConversationContext] = useState<ConversationContext>({
    userBudget: currentCapital,
    mentionedItems: [],
    askedAboutBest: false,
    askedAboutRisk: false,
    askedAboutSteps: false,
    conversationStage: 'greeting'
  });
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

  // Natural AI responses with conversation context
  const generateAIResponse = (userMessage: string): Message => {
    const lowerMessage = userMessage.toLowerCase();
    
    // Find best opportunities
    const bestProfitOpp = opportunities.reduce((best, opp) => 
      opp.profit_per_conversion > best.profit_per_conversion ? opp : best
    );
    
    const bestGpPerHour = opportunities.reduce((best, opp) => 
      opp.profit_per_hour > best.profit_per_hour ? opp : best
    );

    // Calculate some stats
    const avgProfit = opportunities.reduce((sum, opp) => sum + opp.profit_per_conversion, 0) / opportunities.length;
    
    let response = '';
    let type: Message['type'] = 'analysis';
    let newContext = { ...conversationContext };

    // Handle specific item mentions (like "super dive potions" → "divine potions")
    if (lowerMessage.includes('super dive') || lowerMessage.includes('divine')) {
      const divineOpp = opportunities.find(opp => 
        opp.item_name.toLowerCase().includes('divine')
      );
      
      if (divineOpp) {
        if (lowerMessage.includes('1m') || lowerMessage.includes('1 m')) {
          newContext.userBudget = 1000000;
          const conversions = Math.floor(1000000 / divineOpp.from_dose_price);
          const totalProfit = conversions * divineOpp.profit_per_conversion;
          
          response = `I see you're interested in divine potions with a 1M budget. Looking at ${divineOpp.item_name}, you could do about ${conversions} conversions for around ${formatGP(totalProfit)} profit.

The setup is straightforward - buy the 3-dose versions, decant to 1-dose, and sell. Each conversion gives you about ${formatGP(divineOpp.profit_per_conversion)}. 

Want me to walk through the actual steps, or are you curious about other divine potion options?`;
          type = 'suggestion';
        } else {
          response = `Ah, divine potions! ${divineOpp.item_name} is actually looking pretty decent right now. You'd make about ${formatGP(divineOpp.profit_per_conversion)} per conversion.

How much were you thinking of investing? That'll help me figure out if this is the right move for you.`;
          type = 'analysis';
        }
      } else {
        response = `I don't see any divine potion opportunities in the current market data. The prices might not be favorable right now, or they're not showing up as profitable decanting options.

Would you like me to suggest some similar alternatives that are working well today?`;
        type = 'warning';
      }
    } else if ((lowerMessage.includes('best') || lowerMessage.includes('recommend')) && !conversationContext.askedAboutBest) {
      newContext.askedAboutBest = true;
      response = `For your budget, I'd go with ${bestProfitOpp.item_name}. It's giving ${formatGP(bestProfitOpp.profit_per_conversion)} per conversion right now.

With ${formatGP(conversationContext.userBudget || currentCapital)}, you could probably run this about ${Math.floor((conversationContext.userBudget || currentCapital) / bestProfitOpp.from_dose_price)} times. That's potentially ${formatGP(Math.floor((conversationContext.userBudget || currentCapital) / bestProfitOpp.from_dose_price) * bestProfitOpp.profit_per_conversion)} if everything goes smoothly.

The nice thing about ${bestProfitOpp.item_name} is it usually has decent volume, so you won't get stuck waiting to buy or sell.`;
      type = 'suggestion';
    } else if (lowerMessage.includes('profit') || lowerMessage.includes('money') || lowerMessage.includes('gp')) {
      response = `Currently seeing profits ranging from ${formatGP(Math.min(...opportunities.map(o => o.profit_per_conversion)))} to ${formatGP(Math.max(...opportunities.map(o => o.profit_per_conversion)))} per conversion.

The sweet spot seems to be around ${formatGP(avgProfit)} on average. ${bestProfitOpp.item_name} is the standout at ${formatGP(bestProfitOpp.profit_per_conversion)}.

Are you looking for quick, smaller profits or willing to invest more time for bigger returns?`;
      type = 'analysis';
    } else if ((lowerMessage.includes('risk') || lowerMessage.includes('safe')) && !conversationContext.askedAboutRisk) {
      newContext.askedAboutRisk = true;
      const lowRiskOpps = opportunities.filter(opp => 
        opp.profit_per_conversion < avgProfit * 1.2 // More conservative than 1.5x
      );
      
      response = `For safer plays, I'd stick with the more modest profit opportunities. They're usually more predictable.

${lowRiskOpps.slice(0, 2).map(opp => `${opp.item_name} at ${formatGP(opp.profit_per_conversion)} per conversion`).join(' and ')} are both pretty stable choices.

The rule of thumb is: if the profit looks too good, double-check the volume and recent price history. Sometimes those high-margin opportunities disappear quickly.`;
      type = 'warning';
    } else if ((lowerMessage.includes('how') || lowerMessage.includes('start') || lowerMessage.includes('steps')) && !conversationContext.askedAboutSteps) {
      newContext.askedAboutSteps = true;
      response = `Here's how decanting works in practice:

1. Head to the Grand Exchange and buy ${bestProfitOpp.from_dose}-dose ${bestProfitOpp.item_name}
2. Go to Nardah (or Barbarian Herblore if you've unlocked it)  
3. Use the decanting service to convert to ${bestProfitOpp.to_dose}-dose
4. Return to GE and sell the converted potions

Each round trip should net you about ${formatGP(bestProfitOpp.profit_per_conversion)} after taxes. The key is buying and selling at the right prices - don't just hit the instant buy/sell buttons.

Want me to explain how to place good buy/sell offers?`;
      type = 'suggestion';
    } else if (lowerMessage.includes('tax') || lowerMessage.includes('ge')) {
      response = `The GE takes 2% on both ends - when you buy and when you sell. So that's 4% total coming off your margins.

For ${bestProfitOpp.item_name}, if you're buying at ${formatGP(bestProfitOpp.from_dose_price)} and selling at ${formatGP(bestProfitOpp.to_dose_price)}, the tax is already factored into that ${formatGP(bestProfitOpp.profit_per_conversion)} profit figure.

That's one less thing to worry about - the numbers you're seeing are what you actually get.`;
      type = 'analysis';
    } else if (lowerMessage.includes('hello') || lowerMessage.includes('hi') || lowerMessage.includes('hey')) {
      response = `Hey! Good to see you. I've been looking at the current decanting market, and there are some decent opportunities out there.

What's your situation? Are you looking to make some quick GP, or trying to figure out a longer-term strategy?`;
      type = 'suggestion';
    } else {
      // Default contextual response - much more natural
      const responses = [
        `Let me think about that. Looking at the current market, ${bestProfitOpp.item_name} stands out at ${formatGP(bestProfitOpp.profit_per_conversion)} per conversion. What specifically were you wondering about?`,
        `That's an interesting question. The market's showing ${opportunities.length} different options right now. Are you looking for something specific, or should I just point you toward the most profitable ones?`,
        `I'm not sure I caught exactly what you're asking, but I can see some good opportunities in the data. ${bestProfitOpp.item_name} and ${bestGpPerHour.item_name} are both looking solid. What would be most helpful?`
      ];
      
      response = responses[Math.floor(Math.random() * responses.length)];
      type = 'analysis';
    }

    // Update conversation context
    setConversationContext(newContext);

    return {
      id: Date.now().toString(),
      role: 'assistant',
      content: response,
      timestamp: new Date(),
      type
    };
  };

  const handleSendMessage = async () => {
    if (!inputValue.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: inputValue,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsTyping(true);

    // Simulate AI thinking time
    setTimeout(() => {
      const aiResponse = generateAIResponse(inputValue);
      setMessages(prev => [...prev, aiResponse]);
      setIsTyping(false);
    }, 1500 + Math.random() * 1000); // 1.5-2.5s delay for realism
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
      default:
        return <SparklesIcon className="w-4 h-4 text-purple-400" />;
    }
  };

  const quickActions = [
    { text: "What's the best opportunity right now?", icon: ArrowTrendingUpIcon },
    { text: "I want to flip super dive potions with 1m starting", icon: CurrencyDollarIcon },
    { text: "Show me the safest options", icon: ExclamationCircleIcon },
    { text: "How do I actually start?", icon: BoltIcon }
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
          <div className="p-4 border-b border-gray-700 bg-gradient-to-r from-blue-900/20 to-purple-900/20 rounded-t-2xl">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-500/20 rounded-lg">
                  <ChatBubbleLeftRightIcon className="w-6 h-6 text-blue-400" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-white">AI Trading Assistant</h3>
                  <p className="text-sm text-gray-400">Your personal OSRS profit guide</p>
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
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-800 text-gray-100'
                } rounded-2xl px-6 py-4 shadow-lg`}>
                  {message.role === 'assistant' && (
                    <div className="flex items-center gap-2 mb-2 text-xs opacity-75">
                      {getMessageIcon(message.type)}
                      <span>AI Assistant</span>
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
                    <SparklesIcon className="w-4 h-4 animate-pulse" />
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
                placeholder="What would you like to know about these opportunities?"
                className="flex-1 bg-gray-800 border border-gray-600 rounded-xl px-4 py-3 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50"
                disabled={isTyping}
              />
              <button
                onClick={handleSendMessage}
                disabled={!inputValue.trim() || isTyping}
                className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:opacity-50 text-white p-3 rounded-xl transition-colors"
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

export default AITradingAssistant;