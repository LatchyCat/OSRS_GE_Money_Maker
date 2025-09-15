import React, { useState, useEffect } from 'react';
import { Calculator, TrendingUp, TrendingDown, Clock, AlertTriangle, CheckCircle } from 'lucide-react';

interface PieceData {
  item_id: number;
  name: string;
  buy_price: number;
  sell_price: number;
  volume_score: number;
  age_hours: number;
}

interface SetCombiningData {
  set_name: string;
  set_item_id: number;
  strategy: 'combining' | 'decombining';
  strategy_description: string;
  piece_ids: number[];
  piece_names: string[];
  individual_pieces_total_cost: number;
  complete_set_price: number;
  lazy_tax_profit: number;
  profit_margin_pct: number;
  required_capital: number;
  volume_score: number;
  confidence_score: number;
  ai_risk_level: 'low' | 'medium' | 'high';
  estimated_sets_per_hour: number;
  pieces_data: PieceData[];
  ge_tax: number;
  avg_data_age_hours: number;
}

interface SetCombiningCalculatorProps {
  initialData?: SetCombiningData;
  onCalculationChange?: (result: any) => void;
}

const SetCombiningCalculator: React.FC<SetCombiningCalculatorProps> = ({
  initialData,
  onCalculationChange
}) => {
  const [data, setData] = useState<SetCombiningData | null>(initialData || null);
  const [quantity, setQuantity] = useState(1);
  const [userCapital, setUserCapital] = useState(50000000); // 50M GP default
  const [isCalculating, setIsCalculating] = useState(false);

  // Debug logging to help troubleshoot calculator data
  React.useEffect(() => {
    if (initialData) {
      console.log('🧮 SetCombiningCalculator received data:', {
        set_name: initialData.set_name,
        has_pieces_data: initialData.pieces_data?.length > 0,
        pieces_count: initialData.pieces_data?.length || 0,
        lazy_tax_profit: initialData.lazy_tax_profit,
        required_capital: initialData.required_capital,
        volume_score: initialData.volume_score,
        confidence_score: initialData.confidence_score
      });
    }
  }, [initialData]);

  // Calculate derived values
  const totalProfit = data ? data.lazy_tax_profit * quantity : 0;
  const totalCapital = data ? data.required_capital * quantity : 0;
  const totalGETax = data ? data.ge_tax * quantity : 0;
  const hourlyProfit = data ? data.lazy_tax_profit * data.estimated_sets_per_hour : 0;
  const maxAffordable = data ? Math.floor(userCapital / data.required_capital) : 0;

  // Risk level colors for dark theme
  const getRiskColor = (risk: string) => {
    switch (risk) {
      case 'low': return 'text-green-400 bg-green-400/10 border-green-400/30';
      case 'medium': return 'text-yellow-400 bg-yellow-400/10 border-yellow-400/30';
      case 'high': return 'text-red-400 bg-red-400/10 border-red-400/30';
      default: return 'text-gray-400 bg-gray-400/10 border-gray-400/30';
    }
  };

  // Volume confidence indicator for dark theme
  const getVolumeIndicator = (score: number) => {
    if (score >= 0.7) return { icon: CheckCircle, color: 'text-green-400', label: 'High Volume' };
    if (score >= 0.4) return { icon: Clock, color: 'text-yellow-400', label: 'Medium Volume' };
    return { icon: AlertTriangle, color: 'text-red-400', label: 'Low Volume' };
  };

  const formatGP = (amount: number) => {
    if (amount >= 1000000) {
      return `${(amount / 1000000).toFixed(1)}M GP`;
    } else if (amount >= 1000) {
      return `${(amount / 1000).toFixed(0)}K GP`;
    }
    return `${amount.toLocaleString()} GP`;
  };

  const formatTime = (hours: number) => {
    if (hours < 1) {
      return `${Math.round(hours * 60)} minutes ago`;
    } else if (hours < 24) {
      return `${hours.toFixed(1)} hours ago`;
    } else {
      return `${(hours / 24).toFixed(1)} days ago`;
    }
  };

  if (!data) {
    return (
      <div className="bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-lg p-6">
        <div className="flex items-center gap-2 mb-4">
          <Calculator className="h-5 w-5 text-blue-400" />
          <h3 className="text-lg font-semibold text-gray-100">Set Combining Calculator</h3>
        </div>
        <p className="text-gray-400">Select a set combining opportunity to see the calculator.</p>
      </div>
    );
  }

  const volumeIndicator = getVolumeIndicator(data.volume_score);
  const VolIcon = volumeIndicator.icon;

  return (
    <div className="bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-lg p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Calculator className="h-5 w-5 text-blue-400" />
          <h3 className="text-lg font-semibold text-gray-100">Set Combining Calculator</h3>
        </div>
        <div className={`px-3 py-1 rounded-full border text-sm font-medium ${getRiskColor(data.ai_risk_level)}`}>
          {data.ai_risk_level.toUpperCase()} RISK
        </div>
      </div>

      {/* Set Information */}
      <div className="bg-gray-700/20 rounded-lg p-4">
        <h4 className="font-semibold text-gray-100 mb-2">{data.set_name}</h4>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-gray-400">Strategy:</span>
            <div className="font-medium text-gray-200">{data.strategy_description}</div>
          </div>
          <div>
            <span className="text-gray-400">Data Freshness:</span>
            <div className="font-medium text-gray-200">{formatTime(data.avg_data_age_hours)}</div>
          </div>
        </div>
        
        {/* AI Insights */}
        {data.ai_timing_recommendation && (
          <div className="mt-3 p-3 bg-blue-400/10 border border-blue-400/20 rounded-lg">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-blue-400 font-medium text-sm">🤖 AI Recommendation:</span>
            </div>
            <div className="text-blue-300 text-sm">{data.ai_timing_recommendation}</div>
            {data.ai_market_sentiment && (
              <div className="text-blue-400 text-xs mt-1">Market: {data.ai_market_sentiment}</div>
            )}
          </div>
        )}
      </div>

      {/* Volume & Confidence */}
      <div className="flex items-center justify-between bg-blue-400/10 border border-blue-400/20 rounded-lg p-4">
        <div className="flex items-center gap-2">
          <VolIcon className={`h-5 w-5 ${volumeIndicator.color}`} />
          <span className="font-medium text-gray-200">{volumeIndicator.label}</span>
          <span className="text-sm text-gray-400">({(data.volume_score * 100).toFixed(0)}%)</span>
        </div>
        <div className="text-right">
          <div className="text-sm text-gray-400">AI Confidence</div>
          <div className="font-semibold text-gray-200">{(data.confidence_score * 100).toFixed(0)}%</div>
          {data.model_consensus_score && (
            <div className="text-xs text-gray-500">
              Consensus: {(data.model_consensus_score * 100).toFixed(0)}%
            </div>
          )}
        </div>
      </div>

      {/* Input Controls */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Number of Sets
          </label>
          <input
            type="number"
            min="1"
            max={maxAffordable}
            value={quantity}
            onChange={(e) => setQuantity(Math.max(1, parseInt(e.target.value) || 1))}
            className="w-full px-3 py-2 bg-gray-700/50 border border-gray-600/50 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50"
          />
          <div className="text-xs text-gray-500 mt-1">
            Max affordable: {maxAffordable.toLocaleString()}
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Your Capital
          </label>
          <input
            type="number"
            min="1000000"
            step="1000000"
            value={userCapital}
            onChange={(e) => setUserCapital(parseInt(e.target.value) || 50000000)}
            className="w-full px-3 py-2 bg-gray-700/50 border border-gray-600/50 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50"
          />
          <div className="text-xs text-gray-500 mt-1">
            {formatGP(userCapital)}
          </div>
        </div>
      </div>

      {/* Calculation Results */}
      <div className="grid grid-cols-2 gap-4">
        {/* Investment Required */}
        <div className="bg-gray-700/30 rounded-lg p-4">
          <div className="text-sm text-gray-400 mb-1">Investment Required</div>
          <div className="text-xl font-bold text-gray-100">{formatGP(totalCapital)}</div>
          <div className="text-xs text-gray-500">
            {formatGP(data.required_capital)} per set
          </div>
        </div>

        {/* Expected Profit */}
        <div className="bg-green-400/10 border border-green-400/30 rounded-lg p-4">
          <div className="text-sm text-gray-400 mb-1 flex items-center gap-1">
            <TrendingUp className="h-4 w-4" />
            Net Profit (after GE tax)
          </div>
          <div className="text-xl font-bold text-green-400">{formatGP(totalProfit)}</div>
          <div className="text-xs text-gray-500">
            {formatGP(data.lazy_tax_profit)} per set
          </div>
        </div>

        {/* Profit Margin */}
        <div className="bg-blue-400/10 border border-blue-400/30 rounded-lg p-4">
          <div className="text-sm text-gray-400 mb-1">Profit Margin</div>
          <div className="text-xl font-bold text-blue-400">
            {data.profit_margin_pct.toFixed(1)}%
          </div>
          <div className="text-xs text-gray-500">ROI per transaction</div>
        </div>

        {/* Hourly Potential */}
        <div className="bg-purple-400/10 border border-purple-400/30 rounded-lg p-4">
          <div className="text-sm text-gray-400 mb-1">Hourly Potential</div>
          <div className="text-xl font-bold text-purple-400">{formatGP(hourlyProfit)}</div>
          <div className="text-xs text-gray-500">
            ~{data.estimated_sets_per_hour} sets/hour
          </div>
        </div>
      </div>

      {/* GE Tax Breakdown */}
      <div className="bg-yellow-400/10 border border-yellow-400/30 rounded-lg p-4">
        <div className="flex items-center gap-2 mb-2">
          <AlertTriangle className="h-4 w-4 text-yellow-400" />
          <span className="font-medium text-yellow-400">Grand Exchange Tax</span>
        </div>
        <div className="text-sm text-gray-300">
          <div className="flex justify-between">
            <span>GE Tax ({quantity} set{quantity > 1 ? 's' : ''}):</span>
            <span className="font-medium">{formatGP(totalGETax)}</span>
          </div>
          <div className="flex justify-between">
            <span>Tax per set:</span>
            <span>{formatGP(data.ge_tax)}</span>
          </div>
        </div>
      </div>

      {/* Piece Breakdown */}
      <div className="border-t border-gray-600/30 pt-4">
        <h5 className="font-medium text-gray-200 mb-3">Individual Pieces</h5>
        <div className="space-y-2">
          {data.pieces_data.map((piece, index) => (
            <div key={piece.item_id} className="flex items-center justify-between py-2 px-3 bg-gray-700/20 rounded">
              <div className="flex-1">
                <div className="font-medium text-sm text-gray-200">{piece.name}</div>
                <div className="text-xs text-gray-500">
                  Vol: {(piece.volume_score * 100).toFixed(0)}% • 
                  Updated: {formatTime(piece.age_hours)}
                </div>
              </div>
              <div className="text-right">
                <div className="text-sm font-medium text-gray-200">
                  {data.strategy === 'combining' ? formatGP(piece.buy_price) : formatGP(piece.sell_price)}
                </div>
                <div className="text-xs text-gray-500">
                  {data.strategy === 'combining' ? 'Buy' : 'Sell'} price
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Warning for Low Volume */}
      {data.volume_score < 0.3 && (
        <div className="bg-red-400/10 border border-red-400/30 rounded-lg p-4">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-red-400" />
            <span className="font-medium text-red-400">Low Volume Warning</span>
          </div>
          <p className="text-sm text-red-300 mt-1">
            This set has low trading volume. Consider starting with smaller quantities to test market liquidity.
          </p>
        </div>
      )}

      {/* OSRS Wiki Attribution */}
      <div className="text-xs text-gray-500 text-center border-t border-gray-600/30 pt-3">
        Real-time pricing from OSRS Wiki API (/mapping, /latest, /timeseries)
      </div>
    </div>
  );
};

export default SetCombiningCalculator;