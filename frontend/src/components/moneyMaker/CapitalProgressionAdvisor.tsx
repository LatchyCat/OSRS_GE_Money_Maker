import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Brain, 
  Target, 
  TrendingUp, 
  Clock, 
  Shield, 
  AlertTriangle,
  CheckCircle,
  Lightbulb,
  ArrowRight,
  Star
} from 'lucide-react';
import { moneyMakerApi } from '../../api/moneyMaker';
import * as MoneyMakerTypes from '../../types/moneyMaker';
import { LoadingSpinner } from '../common/LoadingSpinner';

interface CapitalProgressionAdvisorProps {
  currentCapital: number;
  targetCapital?: number;
  riskTolerance?: 'low' | 'medium' | 'high';
}

export const CapitalProgressionAdvisor: React.FC<CapitalProgressionAdvisorProps> = ({
  currentCapital,
  targetCapital = 100_000_000,
  riskTolerance = 'medium'
}) => {
  const [advice, setAdvice] = useState<MoneyMakerTypes.CapitalProgressionAdvice | null>(null);
  const [roadmap, setRoadmap] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedRisk, setSelectedRisk] = useState<string>(riskTolerance);
  const [selectedTarget, setSelectedTarget] = useState<number>(targetCapital);
  const [activeTab, setActiveTab] = useState<'advice' | 'roadmap'>('advice');

  useEffect(() => {
    loadAdvice();
  }, [currentCapital, selectedTarget, selectedRisk]);

  const loadAdvice = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const [adviceData, roadmapData] = await Promise.all([
        moneyMakerApi.getProgressionAdvice(currentCapital, selectedTarget, selectedRisk),
        moneyMakerApi.getProgressionRoadmap(currentCapital, selectedTarget)
      ]);
      
      setAdvice(adviceData);
      setRoadmap(roadmapData.roadmap);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load progression advice');
    } finally {
      setLoading(false);
    }
  };

  const riskOptions = [
    { value: 'low', label: 'Conservative', color: 'text-green-400', icon: Shield },
    { value: 'medium', label: 'Balanced', color: 'text-yellow-400', icon: Target },
    { value: 'high', label: 'Aggressive', color: 'text-red-400', icon: TrendingUp }
  ];

  const targetOptions = [
    { value: 75_000_000, label: '75M GP' },
    { value: 100_000_000, label: '100M GP' },
    { value: 250_000_000, label: '250M GP' },
    { value: 500_000_000, label: '500M GP' },
    { value: 1_000_000_000, label: '1B GP' }
  ];

  if (loading) {
    return (
      <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
        <div className="flex items-center justify-center h-40">
          <LoadingSpinner size="md" />
          <span className="ml-3 text-gray-300">Getting AI advice...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
        <div className="text-center py-8">
          <AlertTriangle className="h-12 w-12 text-red-400 mx-auto mb-3" />
          <h3 className="text-lg font-semibold text-red-300 mb-2">Advisor Error</h3>
          <p className="text-red-400 text-sm mb-4">{error}</p>
          <button
            onClick={loadAdvice}
            className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-gray-800 rounded-lg p-6 border border-gray-700"
    >
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 bg-purple-600 rounded-lg">
          <Brain className="h-5 w-5 text-white" />
        </div>
        <div>
          <h3 className="text-xl font-semibold text-white">AI Capital Progression Advisor</h3>
          <p className="text-sm text-gray-400">
            Your friend's proven 50M → 100M method with AI optimization
          </p>
        </div>
      </div>

      {/* Configuration */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        {/* Risk Tolerance */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Risk Tolerance
          </label>
          <div className="flex gap-2">
            {riskOptions.map(option => {
              const IconComponent = option.icon;
              return (
                <button
                  key={option.value}
                  onClick={() => setSelectedRisk(option.value)}
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${
                    selectedRisk === option.value
                      ? 'bg-purple-600 text-white'
                      : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                  }`}
                >
                  <IconComponent className={`h-4 w-4 ${option.color}`} />
                  {option.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* Target Capital */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Target Capital
          </label>
          <select
            value={selectedTarget}
            onChange={(e) => setSelectedTarget(Number(e.target.value))}
            className="w-full px-3 py-2 bg-gray-700 border border-gray-600 text-white rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
          >
            {targetOptions.map(option => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="flex gap-2 mb-6">
        <button
          onClick={() => setActiveTab('advice')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            activeTab === 'advice'
              ? 'bg-purple-600 text-white'
              : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
          }`}
        >
          <Lightbulb className="h-4 w-4" />
          AI Recommendations
        </button>
        
        <button
          onClick={() => setActiveTab('roadmap')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            activeTab === 'roadmap'
              ? 'bg-purple-600 text-white'
              : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
          }`}
        >
          <Target className="h-4 w-4" />
          Progression Roadmap
        </button>
      </div>

      {/* Content */}
      <AnimatePresence mode="wait">
        {activeTab === 'advice' && advice && (
          <motion.div
            key="advice"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            className="space-y-6"
          >
            {/* Current Status */}
            <div className="bg-gray-900 rounded-lg p-4 border border-gray-700">
              <h4 className="text-lg font-semibold text-white mb-3">Current Status</h4>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <p className="text-gray-400">Current Capital</p>
                  <p className="text-white font-semibold">{MoneyMakerTypes.formatGP(currentCapital)}</p>
                </div>
                <div>
                  <p className="text-gray-400">Target Capital</p>
                  <p className="text-white font-semibold">{MoneyMakerTypes.formatGP(selectedTarget)}</p>
                </div>
                <div>
                  <p className="text-gray-400">Tier</p>
                  <p className="text-purple-400 font-semibold capitalize">{advice.current_tier}</p>
                </div>
                <div>
                  <p className="text-gray-400">Target Tier</p>
                  <p className="text-blue-400 font-semibold capitalize">{advice.target_tier}</p>
                </div>
              </div>
            </div>

            {/* Recommended Strategies */}
            <div>
              <h4 className="text-lg font-semibold text-white mb-4">🎯 Recommended Strategies</h4>
              <div className="space-y-3">
                {advice.recommended_strategies.map((strategy, index) => (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.1 }}
                    className="bg-gray-900 rounded-lg p-4 border border-gray-700"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center gap-3">
                        <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                          index === 0 ? 'bg-yellow-600' : 
                          index === 1 ? 'bg-blue-600' :
                          'bg-purple-600'
                        }`}>
                          {index === 0 ? <Star className="h-4 w-4 text-white" /> : index + 1}
                        </div>
                        <div>
                          <h5 className="text-white font-semibold">{strategy.name}</h5>
                          <p className={`text-sm ${MoneyMakerTypes.getStrategyTypeColor(strategy.type)}`}>
                            {MoneyMakerTypes.STRATEGY_TYPE_DISPLAY[strategy.type]}
                          </p>
                        </div>
                      </div>
                      
                      <div className="text-right flex-shrink-0">
                        <p className="text-green-400 font-semibold">
                          {MoneyMakerTypes.formatGP(strategy.expected_hourly_profit)}/hr
                        </p>
                        <p className={`text-sm ${MoneyMakerTypes.RISK_LEVEL_COLORS[strategy.risk_level]} capitalize`}>
                          {strategy.risk_level} risk
                        </p>
                      </div>
                    </div>
                    
                    <p className="text-gray-300 text-sm mb-3">{strategy.why_recommended}</p>
                    
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-xs">
                      <div>
                        <p className="text-gray-400">Capital Required</p>
                        <p className="text-white">{MoneyMakerTypes.formatGP(strategy.capital_required)}</p>
                      </div>
                      <div>
                        <p className="text-gray-400">Success Rate</p>
                        <p className="text-green-400">{(strategy.success_probability * 100).toFixed(0)}%</p>
                      </div>
                      <div>
                        <p className="text-gray-400">Priority</p>
                        <p className={index === 0 ? 'text-yellow-400' : 'text-gray-300'}>
                          {index === 0 ? 'Highest' : index === 1 ? 'High' : 'Medium'}
                        </p>
                      </div>
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>

            {/* Risk Assessment */}
            <div className="bg-gray-900 rounded-lg p-4 border border-gray-700">
              <h4 className="text-lg font-semibold text-white mb-3">🛡️ Risk Assessment</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <p className="text-gray-400 text-sm mb-2">Overall Risk Level</p>
                  <p className={`text-lg font-semibold capitalize ${MoneyMakerTypes.RISK_LEVEL_COLORS[advice.risk_assessment.overall_risk]}`}>
                    {advice.risk_assessment.overall_risk}
                  </p>
                </div>
                
                <div>
                  <p className="text-gray-400 text-sm mb-2">Risk Factors</p>
                  <div className="space-y-1">
                    {advice.risk_assessment.risk_factors.slice(0, 3).map((factor, index) => (
                      <div key={index} className="flex items-center gap-2">
                        <AlertTriangle className="h-3 w-3 text-orange-400 flex-shrink-0" />
                        <span className="text-xs text-gray-300">{factor}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
              
              {advice.risk_assessment.mitigation_strategies.length > 0 && (
                <div className="mt-4">
                  <p className="text-gray-400 text-sm mb-2">Mitigation Strategies</p>
                  <div className="space-y-1">
                    {advice.risk_assessment.mitigation_strategies.slice(0, 2).map((strategy, index) => (
                      <div key={index} className="flex items-center gap-2">
                        <CheckCircle className="h-3 w-3 text-green-400 flex-shrink-0" />
                        <span className="text-xs text-gray-300">{strategy}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Timeline & Market Considerations */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Timeline */}
              <div className="bg-gray-900 rounded-lg p-4 border border-gray-700">
                <div className="flex items-center gap-2 mb-3">
                  <Clock className="h-5 w-5 text-blue-400" />
                  <h4 className="text-lg font-semibold text-white">Timeline</h4>
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-gray-400 text-sm">Estimated Time:</span>
                    <span className="text-white font-medium">
                      {advice.progression_timeline.estimated_hours_to_target < 24
                        ? `${advice.progression_timeline.estimated_hours_to_target}h`
                        : `${Math.ceil(advice.progression_timeline.estimated_hours_to_target / 24)}d`
                      }
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400 text-sm">Milestones:</span>
                    <span className="text-white font-medium">
                      {advice.progression_timeline.milestones.length}
                    </span>
                  </div>
                </div>
              </div>
              
              {/* Market Conditions */}
              <div className="bg-gray-900 rounded-lg p-4 border border-gray-700">
                <div className="flex items-center gap-2 mb-3">
                  <TrendingUp className="h-5 w-5 text-green-400" />
                  <h4 className="text-lg font-semibold text-white">Market</h4>
                </div>
                <div className="space-y-2 text-sm">
                  <div>
                    <p className="text-gray-400">Current Condition</p>
                    <p className="text-white capitalize">
                      {advice.market_considerations.current_market_condition}
                    </p>
                  </div>
                  <div>
                    <p className="text-gray-400">Optimal Hours</p>
                    <p className="text-green-400">
                      {advice.market_considerations.optimal_trading_hours.slice(0, 3).join(':00, ')}:00
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        )}

        {activeTab === 'roadmap' && roadmap && (
          <motion.div
            key="roadmap"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            className="space-y-4"
          >
            <div className="bg-gray-900 rounded-lg p-4 border border-gray-700 mb-4">
              <h4 className="text-lg font-semibold text-white mb-2">🗺️ Progression Roadmap</h4>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <p className="text-gray-400">Total Phases</p>
                  <p className="text-white font-semibold">{roadmap.total_phases}</p>
                </div>
                <div>
                  <p className="text-gray-400">Est. Total Time</p>
                  <p className="text-blue-400 font-semibold">
                    {Math.ceil(roadmap.estimated_total_hours / 24)}d
                  </p>
                </div>
                <div>
                  <p className="text-gray-400">Current Tier</p>
                  <p className="text-purple-400 font-semibold capitalize">{roadmap.current_tier}</p>
                </div>
                <div>
                  <p className="text-gray-400">Target Tier</p>
                  <p className="text-green-400 font-semibold capitalize">{roadmap.target_tier}</p>
                </div>
              </div>
            </div>

            {/* Phases */}
            <div className="space-y-4">
              {roadmap.phases.map((phase: any, index: number) => (
                <motion.div
                  key={phase.phase_number}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.1 }}
                  className="bg-gray-900 rounded-lg p-4 border border-gray-700"
                >
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center text-sm font-bold text-white">
                        {phase.phase_number}
                      </div>
                      <div>
                        <h5 className="text-white font-semibold">
                          Phase {phase.phase_number}
                        </h5>
                        <p className="text-gray-400 text-sm">
                          {MoneyMakerTypes.formatGP(phase.capital_start)} → {MoneyMakerTypes.formatGP(phase.capital_target)}
                        </p>
                      </div>
                    </div>
                    
                    <div className="text-right">
                      <p className="text-blue-400 font-semibold">
                        {phase.estimated_hours < 24 
                          ? `${phase.estimated_hours}h`
                          : `${Math.ceil(phase.estimated_hours / 24)}d`
                        }
                      </p>
                      <p className="text-xs text-gray-400">estimated</p>
                    </div>
                  </div>
                  
                  <div className="mb-3">
                    <p className="text-sm text-gray-400 mb-2">Recommended Strategies:</p>
                    <div className="flex flex-wrap gap-2">
                      {phase.recommended_strategies.map((strategy: string, stratIndex: number) => (
                        <span 
                          key={stratIndex}
                          className="px-2 py-1 bg-blue-900/30 border border-blue-700/50 rounded text-xs text-blue-300"
                        >
                          {strategy}
                        </span>
                      ))}
                    </div>
                  </div>
                  
                  {phase.key_milestones.length > 0 && (
                    <div>
                      <p className="text-sm text-gray-400 mb-2">Key Milestones:</p>
                      <div className="space-y-1">
                        {phase.key_milestones.slice(0, 3).map((milestone: string, milIndex: number) => (
                          <div key={milIndex} className="flex items-center gap-2">
                            <CheckCircle className="h-3 w-3 text-green-400 flex-shrink-0" />
                            <span className="text-xs text-gray-300">{milestone}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Your Friend's Method Callout */}
      <div className="mt-6 p-4 bg-gradient-to-r from-green-900/20 to-purple-900/20 rounded-lg border border-green-700/30">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-8 h-8 bg-gradient-to-r from-green-600 to-blue-600 rounded-full flex items-center justify-center flex-shrink-0">
            <Brain className="h-4 w-4 text-white" />
          </div>
          <div>
            <h5 className="text-sm font-semibold text-green-300">AI-Enhanced Strategy</h5>
            <p className="text-xs text-green-400">Based on your friend's proven 50M → 100M method</p>
          </div>
        </div>
        <p className="text-sm text-gray-300">
          This advisor combines your friend's successful progression path with AI analysis of current market conditions and your risk profile for optimal results.
        </p>
      </div>
    </motion.div>
  );
};