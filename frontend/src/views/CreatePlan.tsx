import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { 
  ArrowLeft, 
  ArrowRight, 
  Target, 
  TrendingUp, 
  Shield, 
  AlertTriangle,
  CheckCircle,
  Clock,
  DollarSign
} from 'lucide-react';
import { planningApi } from '../api/planningApi';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Badge } from '../components/ui/Badge';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import type { CreateGoalPlanRequest, RiskLevel } from '../types';

interface FormData {
  current_gp: string;
  goal_gp: string;
  risk_tolerance: RiskLevel;
}

export const CreatePlan: React.FC = () => {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState<FormData>({
    current_gp: '',
    goal_gp: '',
    risk_tolerance: 'moderate'
  });

  const totalSteps = 4;

  const updateFormData = (field: keyof FormData, value: string | RiskLevel) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const formatGP = (amount: number) => {
    if (amount >= 1000000000) {
      return `${(amount / 1000000000).toFixed(1)}B GP`;
    } else if (amount >= 1000000) {
      return `${(amount / 1000000).toFixed(1)}M GP`;
    } else if (amount >= 1000) {
      return `${(amount / 1000).toFixed(1)}K GP`;
    }
    return `${amount.toLocaleString()} GP`;
  };

  const getRiskColor = (risk: RiskLevel) => {
    switch (risk) {
      case 'conservative': return 'text-green-400 border-green-500/50 bg-green-500/20';
      case 'moderate': return 'text-yellow-400 border-yellow-500/50 bg-yellow-500/20';
      case 'aggressive': return 'text-red-400 border-red-500/50 bg-red-500/20';
    }
  };

  const getRiskDescription = (risk: RiskLevel) => {
    switch (risk) {
      case 'conservative': return 'Lower risk, stable returns. Focus on proven profitable items with minimal market volatility.';
      case 'moderate': return 'Balanced approach. Mix of stable and growth opportunities with moderate risk tolerance.';
      case 'aggressive': return 'Higher risk, higher reward. Target maximum profit potential with volatile market opportunities.';
    }
  };

  const calculateRequiredProfit = () => {
    const current = parseInt(formData.current_gp) || 0;
    const goal = parseInt(formData.goal_gp) || 0;
    return Math.max(0, goal - current);
  };

  const getEstimatedTimeframe = () => {
    const requiredProfit = calculateRequiredProfit();
    if (requiredProfit <= 0) return '0 days';
    
    // Rough estimates based on risk level
    const dailyProfitEstimates = {
      conservative: requiredProfit * 0.02, // 2% daily return
      moderate: requiredProfit * 0.05, // 5% daily return  
      aggressive: requiredProfit * 0.10 // 10% daily return
    };

    const dailyProfit = dailyProfitEstimates[formData.risk_tolerance];
    const days = Math.ceil(requiredProfit / dailyProfit);
    
    if (days <= 30) return `${days} days`;
    if (days <= 365) return `${Math.ceil(days / 30)} months`;
    return `${Math.ceil(days / 365)} years`;
  };

  const handleNext = () => {
    if (currentStep < totalSteps) {
      setCurrentStep(prev => prev + 1);
    }
  };

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep(prev => prev - 1);
    }
  };

  const handleSubmit = async () => {
    setLoading(true);
    try {
      const requestData: CreateGoalPlanRequest = {
        current_gp: parseInt(formData.current_gp),
        goal_gp: parseInt(formData.goal_gp),
        risk_tolerance: formData.risk_tolerance
      };

      const plan = await planningApi.createGoalPlan(requestData);
      navigate('/planning');
    } catch (error) {
      console.error('Error creating plan:', error);
    } finally {
      setLoading(false);
    }
  };

  const isStepValid = (step: number) => {
    switch (step) {
      case 1: return formData.current_gp && parseInt(formData.current_gp) >= 0;
      case 2: return formData.goal_gp && parseInt(formData.goal_gp) > parseInt(formData.current_gp);
      case 3: return true; // Risk tolerance always has a default
      case 4: return true; // Review step
      default: return false;
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between"
      >
        <Button 
          variant="secondary" 
          onClick={() => navigate('/')}
          icon={<ArrowLeft className="w-4 h-4" />}
        >
          Back to Dashboard
        </Button>
        
        <div className="flex items-center gap-2">
          {Array.from({ length: totalSteps }, (_, i) => (
            <div
              key={i}
              className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold ${
                i + 1 === currentStep
                  ? 'bg-accent-500 text-white'
                  : i + 1 < currentStep
                  ? 'bg-green-500 text-white'
                  : 'bg-white/10 text-gray-400'
              }`}
            >
              {i + 1 < currentStep ? (
                <CheckCircle className="w-4 h-4" />
              ) : (
                i + 1
              )}
            </div>
          ))}
        </div>
      </motion.div>

      {/* Progress Bar */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.1 }}
        className="w-full bg-white/10 rounded-full h-2"
      >
        <div 
          className="bg-gradient-to-r from-accent-500 to-accent-600 h-2 rounded-full transition-all duration-500"
          style={{ width: `${(currentStep / totalSteps) * 100}%` }}
        />
      </motion.div>

      {/* Step Content */}
      <motion.div
        key={currentStep}
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        exit={{ opacity: 0, x: -20 }}
        transition={{ duration: 0.3 }}
      >
        <Card className="p-4 sm:p-8 space-y-6">
          {/* Step 1: Current GP */}
          {currentStep === 1 && (
            <div className="space-y-6">
              <div className="text-center space-y-3">
                <div className="w-16 h-16 bg-blue-500/20 rounded-full flex items-center justify-center mx-auto">
                  <DollarSign className="w-8 h-8 text-blue-400" />
                </div>
                <h2 className="text-xl sm:text-2xl font-bold text-white">What's your current GP?</h2>
                <p className="text-gray-400">
                  Enter your current gold piece balance to help us create your personalized plan
                </p>
              </div>

              <div className="max-w-md mx-auto">
                <Input
                  label="Current GP"
                  type="number"
                  value={formData.current_gp}
                  onChange={(e) => updateFormData('current_gp', e.target.value)}
                  placeholder="0"
                  min="0"
                />
                {formData.current_gp && (
                  <div className="mt-2 text-center text-accent-400 font-semibold">
                    {formatGP(parseInt(formData.current_gp))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Step 2: Goal GP */}
          {currentStep === 2 && (
            <div className="space-y-6">
              <div className="text-center space-y-3">
                <div className="w-16 h-16 bg-green-500/20 rounded-full flex items-center justify-center mx-auto">
                  <Target className="w-8 h-8 text-green-400" />
                </div>
                <h2 className="text-xl sm:text-2xl font-bold text-white">What's your GP goal?</h2>
                <p className="text-gray-400">
                  Set your target GP amount - we'll help you create a strategy to reach it
                </p>
              </div>

              <div className="max-w-md mx-auto">
                <Input
                  label="Goal GP"
                  type="number"
                  value={formData.goal_gp}
                  onChange={(e) => updateFormData('goal_gp', e.target.value)}
                  placeholder="1000000"
                  min={parseInt(formData.current_gp) + 1 || 1}
                />
                {formData.goal_gp && (
                  <div className="mt-4 space-y-2">
                    <div className="text-center text-green-400 font-semibold">
                      {formatGP(parseInt(formData.goal_gp))}
                    </div>
                    <div className="text-center text-sm text-gray-400">
                      Profit needed: <span className="text-accent-400 font-semibold">
                        {formatGP(calculateRequiredProfit())}
                      </span>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Step 3: Risk Tolerance */}
          {currentStep === 3 && (
            <div className="space-y-6">
              <div className="text-center space-y-3">
                <div className="w-16 h-16 bg-yellow-500/20 rounded-full flex items-center justify-center mx-auto">
                  <Shield className="w-8 h-8 text-yellow-400" />
                </div>
                <h2 className="text-xl sm:text-2xl font-bold text-white">Choose your risk tolerance</h2>
                <p className="text-gray-400">
                  This determines the types of investment strategies we'll recommend
                </p>
              </div>

              <div className="grid gap-4">
                {(['conservative', 'moderate', 'aggressive'] as RiskLevel[]).map((risk) => (
                  <motion.div
                    key={risk}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    className={`border-2 rounded-xl p-4 sm:p-6 cursor-pointer transition-all ${
                      formData.risk_tolerance === risk
                        ? getRiskColor(risk) + ' border-opacity-100'
                        : 'border-white/20 hover:border-white/40'
                    }`}
                    onClick={() => updateFormData('risk_tolerance', risk)}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className={`text-lg font-semibold ${
                          formData.risk_tolerance === risk ? '' : 'text-white'
                        } capitalize`}>
                          {risk}
                        </h3>
                        <p className="text-gray-400 mt-1 text-sm">
                          {getRiskDescription(risk)}
                        </p>
                      </div>
                      {formData.risk_tolerance === risk && (
                        <CheckCircle className="w-6 h-6 text-current" />
                      )}
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>
          )}

          {/* Step 4: Review & Submit */}
          {currentStep === 4 && (
            <div className="space-y-6">
              <div className="text-center space-y-3">
                <div className="w-16 h-16 bg-purple-500/20 rounded-full flex items-center justify-center mx-auto">
                  <TrendingUp className="w-8 h-8 text-purple-400" />
                </div>
                <h2 className="text-xl sm:text-2xl font-bold text-white">Review your goal plan</h2>
                <p className="text-gray-400">
                  Make sure everything looks correct before we create your personalized strategy
                </p>
              </div>

              <div className="grid gap-4 sm:gap-6 max-w-2xl mx-auto">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="backdrop-blur-md bg-blue-500/10 border border-blue-500/20 rounded-xl p-4">
                    <div className="text-sm text-gray-400 uppercase tracking-wider mb-2">
                      Current GP
                    </div>
                    <div className="text-lg sm:text-xl font-bold text-blue-400">
                      {formatGP(parseInt(formData.current_gp))}
                    </div>
                  </div>

                  <div className="backdrop-blur-md bg-green-500/10 border border-green-500/20 rounded-xl p-4">
                    <div className="text-sm text-gray-400 uppercase tracking-wider mb-2">
                      Goal GP
                    </div>
                    <div className="text-lg sm:text-xl font-bold text-green-400">
                      {formatGP(parseInt(formData.goal_gp))}
                    </div>
                  </div>
                </div>

                <div className="backdrop-blur-md bg-accent-500/10 border border-accent-500/20 rounded-xl p-4 sm:p-6 space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-gray-400">Profit Required:</span>
                    <span className="text-accent-400 font-bold text-lg sm:text-xl">
                      {formatGP(calculateRequiredProfit())}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-gray-400">Risk Tolerance:</span>
                    <Badge variant={
                      formData.risk_tolerance === 'conservative' ? 'success' :
                      formData.risk_tolerance === 'moderate' ? 'warning' : 'danger'
                    }>
                      {formData.risk_tolerance}
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-gray-400 flex items-center gap-2">
                      <Clock className="w-4 h-4" />
                      Estimated Timeframe:
                    </span>
                    <span className="text-purple-400 font-semibold">
                      {getEstimatedTimeframe()}
                    </span>
                  </div>
                </div>

                <div className="backdrop-blur-md bg-yellow-500/10 border border-yellow-500/20 rounded-xl p-3 sm:p-4 flex items-start gap-3">
                  <AlertTriangle className="w-5 h-5 text-yellow-400 flex-shrink-0 mt-0.5" />
                  <div>
                    <div className="text-yellow-400 font-semibold text-sm">
                      Important Note
                    </div>
                    <div className="text-gray-300 text-sm mt-1">
                      These are estimates based on historical data. Actual results may vary depending on market conditions and your trading efficiency.
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </Card>
      </motion.div>

      {/* Navigation */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.2 }}
        className="flex items-center justify-between"
      >
        <Button
          variant="secondary"
          onClick={handleBack}
          disabled={currentStep === 1}
          icon={<ArrowLeft className="w-4 h-4" />}
        >
          Back
        </Button>

        {currentStep < totalSteps ? (
          <Button
            variant="primary"
            onClick={handleNext}
            disabled={!isStepValid(currentStep)}
            icon={<ArrowRight className="w-4 h-4" />}
          >
            Next
          </Button>
        ) : (
          <Button
            variant="primary"
            onClick={handleSubmit}
            loading={loading}
            disabled={loading}
            icon={<CheckCircle className="w-4 h-4" />}
          >
            Create Goal Plan
          </Button>
        )}
      </motion.div>
    </div>
  );
};