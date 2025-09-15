import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  ArrowLeft, 
  TrendingUp, 
  TrendingDown, 
  Crown, 
  Users, 
  Calculator,
  AlertTriangle,
  Target,
  Plus,
  Coins
} from 'lucide-react';
import { itemsApi } from '../api/itemsApi';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { Input } from '../components/ui/Input';
import { useItemSeasonalData } from '../hooks/useSeasonalData';
import { SeasonalPatternCard } from '../components/seasonal/SeasonalPatternCard';
import { SeasonalForecastCard } from '../components/seasonal/SeasonalForecastCard';
import { SeasonalRecommendationCard } from '../components/seasonal/SeasonalRecommendationCard';
import { SeasonalPatternChart } from '../components/seasonal/SeasonalPatternChart';
import type { Item } from '../types';

export const ItemDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [item, setItem] = useState<Item | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [calculatorAmount, setCalculatorAmount] = useState<string>('1');
  const [showSeasonalDetails, setShowSeasonalDetails] = useState(false);

  // Get seasonal data for this item
  const itemId = id ? parseInt(id) : 0;
  const seasonalData = useItemSeasonalData(itemId);

  useEffect(() => {
    const fetchItem = async () => {
      if (!id) return;
      
      try {
        setLoading(true);
        setError(null);
        const itemId = parseInt(id);
        
        // Validate item ID
        if (isNaN(itemId) || itemId <= 0) {
          setError('Invalid item ID format');
          setItem(null);
          return;
        }
        
        // Use the proper single item endpoint
        const item = await itemsApi.getItem(itemId);
        setItem(item);
      } catch (error: any) {
        console.error('Error fetching item:', error);
        setItem(null);
        
        // Provide specific error messages based on error type
        if (error.response?.status === 404) {
          setError('Item not found. This item may not exist or may have been removed.');
        } else if (error.response?.status >= 500) {
          setError('Server error. Please try again later.');
        } else if (error.message?.includes('Network Error')) {
          setError('Network error. Please check your connection and try again.');
        } else {
          setError('Unable to load item details. Please try again.');
        }
      } finally {
        setLoading(false);
      }
    };

    fetchItem();
  }, [id]);

  const formatGP = (amount: number | null | undefined) => {
    // Handle null, undefined, or invalid numbers
    if (amount == null || isNaN(Number(amount))) {
      return '0 GP';
    }
    
    const num = Number(amount);
    if (num >= 1000000) {
      return `${(num / 1000000).toFixed(1)}M GP`;
    } else if (num >= 1000) {
      return `${(num / 1000).toFixed(1)}K GP`;
    }
    return `${num.toLocaleString()} GP`;
  };

  // Utility functions to safely access nested profit data
  const getCurrentBuyPrice = (item: Item) => {
    return item.profit_calc?.current_buy_price ?? item.current_buy_price ?? 0;
  };

  const getCurrentProfit = (item: Item) => {
    return item.profit_calc?.current_profit ?? item.current_profit ?? 0;
  };

  const getCurrentProfitMargin = (item: Item) => {
    return item.profit_calc?.current_profit_margin ?? item.current_profit_margin ?? 0;
  };

  const getRecommendationScore = (item: Item) => {
    return item.profit_calc?.recommendation_score ?? item.recommendation_score ?? 0;
  };

  const getProfitColor = (profit: number) => {
    if (profit > 0) return 'text-green-400';
    if (profit < 0) return 'text-red-400';
    return 'text-gray-400';
  };

  const getMarginColor = (margin: number) => {
    if (margin >= 10) return 'text-green-400';
    if (margin >= 5) return 'text-yellow-400';
    return 'text-red-400';
  };

  const getRecommendationBadge = (score: number) => {
    if (score >= 0.8) return { variant: 'success' as const, text: 'Excellent', color: 'border-green-500/50 bg-green-500/20' };
    if (score >= 0.6) return { variant: 'info' as const, text: 'Good', color: 'border-blue-500/50 bg-blue-500/20' };
    if (score >= 0.4) return { variant: 'warning' as const, text: 'Fair', color: 'border-yellow-500/50 bg-yellow-500/20' };
    return { variant: 'neutral' as const, text: 'Low', color: 'border-gray-500/50 bg-gray-500/20' };
  };

  const calculateProfit = () => {
    if (!item || !calculatorAmount) return { total: 0, perItem: 0 };
    const amount = parseInt(calculatorAmount) || 0;
    const perItem = getCurrentProfit(item);
    const total = perItem * amount;
    return { total, perItem };
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <LoadingSpinner size="lg" text="Loading item details..." />
      </div>
    );
  }

  if (!item) {
    return (
      <div className="space-y-6">
        <Button 
          variant="secondary" 
          onClick={() => navigate('/items')}
          icon={<ArrowLeft className="w-4 h-4" />}
        >
          Back to Items
        </Button>
        <Card className="text-center py-12">
          <div className="space-y-4">
            <AlertTriangle className="w-16 h-16 text-red-400 mx-auto" />
            <div>
              <h3 className="text-lg font-semibold text-white">Unable to Load Item</h3>
              <p className="text-gray-400 mt-2">
                {error || 'The item you\'re looking for doesn\'t exist or couldn\'t be loaded.'}
              </p>
              {error && (
                <Button 
                  variant="primary" 
                  className="mt-4"
                  onClick={() => window.location.reload()}
                >
                  Try Again
                </Button>
              )}
            </div>
          </div>
        </Card>
      </div>
    );
  }

  const recommendation = getRecommendationBadge(getRecommendationScore(item));
  const profit = calculateProfit();

  return (
    <div className="space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between"
      >
        <Button 
          variant="secondary" 
          onClick={() => navigate('/items')}
          icon={<ArrowLeft className="w-4 h-4" />}
        >
          Back to Items
        </Button>
        <Button variant="primary" icon={<Plus className="w-4 h-4" />}>
          Add to Goal Plan
        </Button>
      </motion.div>

      {/* Item Header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
      >
        <Card className="space-y-6">
          <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-6">
            <div className="flex-1 space-y-4">
              <div className="flex items-start justify-between">
                <div>
                  <h1 className="text-3xl font-bold text-white flex items-center gap-3">
                    {item.name}
                    {item.members && (
                      <Crown className="w-6 h-6 text-yellow-400" title="Members Only" />
                    )}
                  </h1>
                  <p className="text-gray-400 mt-2 text-lg">
                    {item.examine}
                  </p>
                </div>
                <Badge variant={recommendation.variant} size="lg">
                  {recommendation.text}
                </Badge>
              </div>

              <div className="flex items-center gap-4">
                <div className="text-sm text-gray-400">
                  Item ID: <span className="text-white font-mono">{item.item_id}</span>
                </div>
                <div className="text-sm text-gray-400 flex items-center gap-1">
                  <Users className="w-4 h-4" />
                  Trade Limit: <span className="text-white">{item.limit || 'Unlimited'}</span>
                </div>
              </div>
            </div>

            {/* Quick Stats */}
            <div className="grid grid-cols-2 lg:grid-cols-1 gap-4 min-w-[300px]">
              <div className="backdrop-blur-md bg-white/10 border border-white/20 rounded-xl p-4">
                <div className="text-sm text-gray-400 uppercase tracking-wider mb-2">
                  Recommendation Score
                </div>
                <div className="text-2xl font-bold text-purple-400">
                  {(getRecommendationScore(item) * 100).toFixed(0)}%
                </div>
              </div>
              <div className="backdrop-blur-md bg-white/10 border border-white/20 rounded-xl p-4">
                <div className="text-sm text-gray-400 uppercase tracking-wider mb-2">
                  High Alch Value
                </div>
                <div className="text-2xl font-bold text-yellow-400">
                  {formatGP(item.high_alch)}
                </div>
              </div>
            </div>
          </div>
        </Card>
      </motion.div>

      {/* Main Stats Grid */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6"
      >
        {/* Current Buy Price */}
        <Card className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="text-sm font-medium text-gray-400">
              Current Buy Price
            </div>
            <Coins className="w-5 h-5 text-blue-400" />
          </div>
          <div className="text-xl sm:text-2xl font-bold text-blue-400">
            {formatGP(getCurrentBuyPrice(item))}
          </div>
          <div className="text-xs text-gray-400">
            Instant-buy (GE)
          </div>
          <div className="text-xs text-blue-400">
            ✓ Fixed pricing logic
          </div>
        </Card>

        {/* Profit per Item */}
        <Card className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="text-sm font-medium text-gray-400">
              Profit per Item
            </div>
            {getCurrentProfit(item) > 0 ? (
              <TrendingUp className="w-5 h-5 text-green-400" />
            ) : (
              <TrendingDown className="w-5 h-5 text-red-400" />
            )}
          </div>
          <div className={`text-xl sm:text-2xl font-bold ${getProfitColor(getCurrentProfit(item))}`}>
            {getCurrentProfit(item) > 0 ? '+' : ''}{formatGP(getCurrentProfit(item))}
          </div>
          <div className="text-xs text-gray-400">
            After high alch
          </div>
        </Card>

        {/* Profit Margin */}
        <Card className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="text-sm font-medium text-gray-400">
              Profit Margin
            </div>
            <Target className="w-5 h-5 text-yellow-400" />
          </div>
          <div className={`text-xl sm:text-2xl font-bold ${getMarginColor(getCurrentProfitMargin(item))}`}>
            {getCurrentProfitMargin(item).toFixed(2)}%
          </div>
          <div className="text-xs text-gray-400">
            Return on investment
          </div>
        </Card>

        {/* Investment Required */}
        <Card className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="text-sm font-medium text-gray-400">
              Max Investment
            </div>
            <Calculator className="w-5 h-5 text-purple-400" />
          </div>
          <div className="text-xl sm:text-2xl font-bold text-purple-400">
            {formatGP(getCurrentBuyPrice(item) * (item.limit || 1000))}
          </div>
          <div className="text-xs text-gray-400">
            Based on buy limit
          </div>
        </Card>
      </motion.div>

      {/* Profit Calculator */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
      >
        <Card className="space-y-6">
          <div className="flex items-center gap-3">
            <Calculator className="w-6 h-6 text-accent-400" />
            <h3 className="text-xl font-semibold text-white">Profit Calculator</h3>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6">
            <div className="space-y-4">
              <Input
                label="Number of Items"
                type="number"
                value={calculatorAmount}
                onChange={(e) => setCalculatorAmount(e.target.value)}
                placeholder="Enter quantity"
                min="1"
                max={item.limit?.toString()}
              />
              {item.limit && parseInt(calculatorAmount) > item.limit && (
                <div className="flex items-center gap-2 text-yellow-400 text-sm">
                  <AlertTriangle className="w-4 h-4" />
                  Exceeds buy limit of {item.limit.toLocaleString()}
                </div>
              )}
            </div>

            <div className="backdrop-blur-md bg-gradient-to-r from-green-500/10 to-blue-500/10 border border-green-500/20 rounded-xl p-4 sm:p-6 space-y-4">
              <h4 className="text-lg font-semibold text-white">Profit Breakdown</h4>
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-gray-400">Investment Required:</span>
                  <span className="text-blue-400 font-semibold">
                    {formatGP(getCurrentBuyPrice(item) * (parseInt(calculatorAmount) || 0))}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Profit per Item:</span>
                  <span className={`font-semibold ${getProfitColor(profit.perItem)}`}>
                    {profit.perItem > 0 ? '+' : ''}{formatGP(profit.perItem)}
                  </span>
                </div>
                <div className="border-t border-white/20 pt-3">
                  <div className="flex justify-between">
                    <span className="text-white font-semibold">Total Profit:</span>
                    <span className={`font-bold text-xl ${getProfitColor(profit.total)}`}>
                      {profit.total > 0 ? '+' : ''}{formatGP(profit.total)}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </Card>
      </motion.div>

      {/* Market Analysis */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
      >
        <Card className="space-y-6">
          <h3 className="text-xl font-semibold text-white">Market Analysis</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
            <div className="space-y-3">
              <div className="text-sm text-gray-400">Risk Level</div>
              <div className={`${recommendation.color} border rounded-lg p-3`}>
                <div className="font-semibold text-white capitalize">
                  {recommendation.text}
                </div>
                <div className="text-sm text-gray-300 mt-1">
                  Based on volatility & volume
                </div>
              </div>
            </div>
            
            <div className="space-y-3">
              <div className="text-sm text-gray-400">Opportunity Rating</div>
              <div className="border-accent-500/50 bg-accent-500/20 border rounded-lg p-3">
                <div className="font-semibold text-accent-400">
                  {getCurrentProfit(item) > 100 ? 'High' : getCurrentProfit(item) > 50 ? 'Medium' : 'Low'}
                </div>
                <div className="text-sm text-gray-300 mt-1">
                  Profit potential assessment
                </div>
              </div>
            </div>

            <div className="space-y-3">
              <div className="text-sm text-gray-400">Volume Indicator</div>
              <div className="border-yellow-500/50 bg-yellow-500/20 border rounded-lg p-3">
                <div className="font-semibold text-yellow-400">
                  {item.limit && item.limit > 1000 ? 'High Volume' : item.limit && item.limit > 100 ? 'Medium Volume' : 'Low Volume'}
                </div>
                <div className="text-sm text-gray-300 mt-1">
                  Trading capacity
                </div>
              </div>
            </div>
          </div>
        </Card>
      </motion.div>

      {/* Seasonal Analysis Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
      >
        <Card className="space-y-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Target className="w-6 h-6 text-purple-400" />
              <h3 className="text-xl font-semibold text-white">Seasonal Market Analysis</h3>
            </div>
            <div className="flex items-center gap-3">
              <div className={`w-3 h-3 rounded-full ${
                seasonalData.loading ? 'bg-yellow-400 animate-pulse' : 
                seasonalData.error ? 'bg-red-400' : 
                seasonalData.pattern.data ? 'bg-green-400' : 'bg-gray-400'
              }`} />
              <span className="text-sm text-gray-400">
                {seasonalData.loading ? 'Loading...' : 
                 seasonalData.error ? 'No data' : 
                 seasonalData.pattern.data ? 'Active' : 'No patterns'}
              </span>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setShowSeasonalDetails(!showSeasonalDetails)}
              >
                {showSeasonalDetails ? 'Hide Details' : 'Show Details'}
              </Button>
            </div>
          </div>

          {/* Seasonal Summary Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-4 text-center">
              <div className="text-sm text-gray-400 mb-1">Pattern Strength</div>
              <div className="text-xl font-bold text-blue-400">
                {seasonalData.pattern.data 
                  ? `${(seasonalData.pattern.data.overall_pattern_strength * 100).toFixed(1)}%`
                  : 'N/A'
                }
              </div>
              <div className="text-xs text-gray-400">
                {seasonalData.pattern.data?.signal_quality || 'No data'}
              </div>
            </div>

            <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-4 text-center">
              <div className="text-sm text-gray-400 mb-1">Forecasts</div>
              <div className="text-xl font-bold text-green-400">
                {seasonalData.forecasts.data?.length || 0}
              </div>
              <div className="text-xs text-gray-400">
                {seasonalData.forecasts.data?.length 
                  ? `Next ${seasonalData.forecasts.data.length} periods`
                  : 'No forecasts'
                }
              </div>
            </div>

            <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-4 text-center">
              <div className="text-sm text-gray-400 mb-1">Recommendations</div>
              <div className="text-xl font-bold text-yellow-400">
                {seasonalData.recommendations.data?.length || 0}
              </div>
              <div className="text-xs text-gray-400">
                {seasonalData.recommendations.data?.filter(r => r.is_active).length 
                  ? `${seasonalData.recommendations.data.filter(r => r.is_active).length} active`
                  : 'No active signals'
                }
              </div>
            </div>

            <div className="bg-purple-500/10 border border-purple-500/20 rounded-lg p-4 text-center">
              <div className="text-sm text-gray-400 mb-1">Best Period</div>
              <div className="text-xl font-bold text-purple-400">
                {seasonalData.pattern.data?.best_day_of_week || 'Unknown'}
              </div>
              <div className="text-xs text-gray-400">
                {seasonalData.pattern.data?.best_month || 'No data'}
              </div>
            </div>
          </div>

          {/* Seasonal Details */}
          {showSeasonalDetails && (
            <div className="space-y-6 border-t border-gray-700 pt-6">
              {/* Pattern Analysis */}
              {seasonalData.pattern.data && (
                <div className="space-y-4">
                  <h4 className="text-lg font-semibold text-white">Pattern Analysis</h4>
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <SeasonalPatternCard 
                      pattern={seasonalData.pattern.data}
                      className="h-full"
                    />
                    <SeasonalPatternChart 
                      pattern={seasonalData.pattern.data}
                      chartType="radar"
                      height={250}
                    />
                  </div>
                </div>
              )}

              {/* Forecasts */}
              {seasonalData.forecasts.data && seasonalData.forecasts.data.length > 0 && (
                <div className="space-y-4">
                  <h4 className="text-lg font-semibold text-white">Price Forecasts</h4>
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {seasonalData.forecasts.data.slice(0, 2).map((forecast) => (
                      <SeasonalForecastCard 
                        key={forecast.id}
                        forecast={forecast}
                      />
                    ))}
                  </div>
                </div>
              )}

              {/* Recommendations */}
              {seasonalData.recommendations.data && seasonalData.recommendations.data.length > 0 && (
                <div className="space-y-4">
                  <h4 className="text-lg font-semibold text-white">Trading Recommendations</h4>
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {seasonalData.recommendations.data.slice(0, 2).map((recommendation) => (
                      <SeasonalRecommendationCard 
                        key={recommendation.id}
                        recommendation={recommendation}
                      />
                    ))}
                  </div>
                </div>
              )}

              {/* No Seasonal Data */}
              {!seasonalData.pattern.data && !seasonalData.loading && (
                <div className="text-center py-8">
                  <Target className="w-16 h-16 text-gray-600 mx-auto mb-4" />
                  <h4 className="text-lg font-semibold text-gray-300 mb-2">
                    No Seasonal Patterns Found
                  </h4>
                  <p className="text-gray-500 mb-4">
                    This item hasn't been analyzed for seasonal patterns yet, or doesn't have sufficient trading history.
                  </p>
                  <Button
                    variant="secondary"
                    onClick={() => seasonalData.refetchAll()}
                    disabled={seasonalData.loading}
                  >
                    Check Again
                  </Button>
                </div>
              )}

              {/* Error State */}
              {seasonalData.error && (
                <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <AlertTriangle className="w-5 h-5 text-red-400" />
                    <span className="text-red-400 font-medium">Seasonal Data Unavailable</span>
                  </div>
                  <p className="text-sm text-gray-300 mb-3">
                    Unable to load seasonal analysis for this item. This could be due to:
                  </p>
                  <ul className="text-sm text-gray-400 space-y-1 mb-4">
                    <li>• Seasonal analytics engine not running</li>
                    <li>• Insufficient trading data for analysis</li>
                    <li>• Item not yet processed by pattern detection</li>
                    <li>• Temporary API connectivity issues</li>
                  </ul>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => seasonalData.refetchAll()}
                    disabled={seasonalData.loading}
                  >
                    Retry Loading
                  </Button>
                </div>
              )}
            </div>
          )}

          {/* Integration Info */}
          <div className="bg-gradient-to-r from-blue-500/10 to-purple-500/10 border border-blue-500/20 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <Target className="w-4 h-4 text-blue-400" />
              <span className="text-blue-400 font-medium">Advanced Market Intelligence</span>
            </div>
            <p className="text-sm text-gray-300">
              Seasonal analysis combines traditional profit calculations with advanced pattern detection to identify 
              optimal trading windows, predict price movements, and generate automated trading recommendations.
            </p>
          </div>
        </Card>
      </motion.div>
    </div>
  );
};