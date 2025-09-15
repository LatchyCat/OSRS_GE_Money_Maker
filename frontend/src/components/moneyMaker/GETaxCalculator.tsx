import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Calculator, DollarSign, AlertCircle, CheckCircle, Info } from 'lucide-react';
import { moneyMakerApi } from '../../api/moneyMaker';
import * as MoneyMakerTypes from '../../types/moneyMaker';

export const GETaxCalculator: React.FC = () => {
  const [sellPrice, setSellPrice] = useState<string>('1000000');
  const [itemId, setItemId] = useState<string>('');
  const [calculation, setCalculation] = useState<MoneyMakerTypes.GETaxCalculation | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (sellPrice && !isNaN(Number(sellPrice))) {
      calculateTax();
    }
  }, [sellPrice, itemId]);

  const calculateTax = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const price = Number(sellPrice);
      const itemIdNum = itemId ? Number(itemId) : undefined;
      
      if (isNaN(price) || price < 0) {
        throw new Error('Invalid sell price');
      }
      
      if (itemId && (isNaN(itemIdNum!) || itemIdNum! < 0)) {
        throw new Error('Invalid item ID');
      }
      
      const result = await moneyMakerApi.calculateGETax(price, itemIdNum);
      setCalculation(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Calculation failed');
      setCalculation(null);
    } finally {
      setLoading(false);
    }
  };

  const presetPrices = [
    { label: '100K', value: 100_000 },
    { label: '1M', value: 1_000_000 },
    { label: '10M', value: 10_000_000 },
    { label: '50M', value: 50_000_000 },
    { label: '100M', value: 100_000_000 },
    { label: '500M', value: 500_000_000 },
  ];

  const bondItemId = 13190; // Old School Bond

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-gray-800 rounded-lg p-6 border border-gray-700"
    >
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 bg-blue-600 rounded-lg">
          <Calculator className="h-5 w-5 text-white" />
        </div>
        <div>
          <h3 className="text-xl font-semibold text-white">GE Tax Calculator</h3>
          <p className="text-sm text-gray-400">Calculate Grand Exchange taxes and net profits</p>
        </div>
      </div>

      {/* Input Form */}
      <div className="space-y-4 mb-6">
        {/* Sell Price Input */}
        <div>
          <label htmlFor="sellPrice" className="block text-sm font-medium text-gray-300 mb-2">
            Sell Price (GP)
          </label>
          <div className="relative">
            <DollarSign className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="number"
              id="sellPrice"
              value={sellPrice}
              onChange={(e) => setSellPrice(e.target.value)}
              placeholder="Enter sell price..."
              className="w-full pl-10 pr-4 py-2 bg-gray-700 border border-gray-600 text-white rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </div>

        {/* Quick Preset Buttons */}
        <div>
          <p className="text-sm text-gray-400 mb-2">Quick presets:</p>
          <div className="flex flex-wrap gap-2">
            {presetPrices.map(preset => (
              <button
                key={preset.label}
                onClick={() => setSellPrice(preset.value.toString())}
                className="px-3 py-1 bg-gray-700 hover:bg-gray-600 text-gray-300 text-sm rounded transition-colors"
              >
                {preset.label}
              </button>
            ))}
          </div>
        </div>

        {/* Item ID Input (Optional) */}
        <div>
          <label htmlFor="itemId" className="block text-sm font-medium text-gray-300 mb-2">
            Item ID (Optional)
            <span className="text-gray-500 ml-1">- for tax exemption check</span>
          </label>
          <div className="flex gap-2">
            <input
              type="number"
              id="itemId"
              value={itemId}
              onChange={(e) => setItemId(e.target.value)}
              placeholder="Enter item ID..."
              className="flex-1 px-3 py-2 bg-gray-700 border border-gray-600 text-white rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <button
              onClick={() => setItemId(bondItemId.toString())}
              className="px-3 py-2 bg-green-600 hover:bg-green-700 text-white text-sm rounded-lg transition-colors"
            >
              Bond ID
            </button>
          </div>
          <p className="text-xs text-gray-500 mt-1">
            Bond ID: {bondItemId} (tax exempt)
          </p>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="mb-4 p-3 bg-red-900/20 border border-red-700 rounded-lg">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-4 w-4 text-red-400" />
            <span className="text-red-300 text-sm">{error}</span>
          </div>
        </div>
      )}

      {/* Calculation Results */}
      {calculation && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-4"
        >
          {/* Tax Exemption Alert */}
          {calculation.is_tax_exempt ? (
            <div className="p-4 bg-green-900/20 border border-green-700 rounded-lg">
              <div className="flex items-center gap-2 mb-2">
                <CheckCircle className="h-5 w-5 text-green-400" />
                <span className="font-semibold text-green-300">Tax Exempt Item!</span>
              </div>
              <p className="text-green-400 text-sm">
                This item is exempt from Grand Exchange tax. You keep 100% of the sale price.
              </p>
            </div>
          ) : (
            <div className="p-4 bg-blue-900/20 border border-blue-700 rounded-lg">
              <div className="flex items-center gap-2 mb-2">
                <Info className="h-5 w-5 text-blue-400" />
                <span className="font-semibold text-blue-300">Tax Applied</span>
              </div>
              <p className="text-blue-400 text-sm">
                Standard 2% Grand Exchange tax applies to this transaction.
              </p>
            </div>
          )}

          {/* Calculation Breakdown */}
          <div className="bg-gray-900 rounded-lg p-4 border border-gray-700">
            <h4 className="text-lg font-semibold text-white mb-4">Tax Calculation</h4>
            
            <div className="space-y-3">
              {/* Sell Price */}
              <div className="flex items-center justify-between">
                <span className="text-gray-300">Sell Price:</span>
                <span className="text-white font-semibold">
                  {MoneyMakerTypes.formatGP(calculation.sell_price)}
                </span>
              </div>
              
              {/* GE Tax */}
              <div className="flex items-center justify-between">
                <span className="text-gray-300">GE Tax ({calculation.effective_tax_percentage.toFixed(2)}%):</span>
                <span className={calculation.ge_tax > 0 ? 'text-red-400' : 'text-green-400'}>
                  {calculation.ge_tax > 0 ? '-' : ''}{MoneyMakerTypes.formatGP(calculation.ge_tax)}
                </span>
              </div>
              
              {/* Net Received */}
              <div className="flex items-center justify-between pt-3 border-t border-gray-700">
                <span className="text-green-300 font-semibold">Net Received:</span>
                <span className="text-green-400 font-bold text-xl">
                  {MoneyMakerTypes.formatGP(calculation.net_received)}
                </span>
              </div>
              
              {/* Tax Savings (if applicable) */}
              {calculation.is_tax_exempt && calculation.sell_price > 50 && (
                <div className="flex items-center justify-between pt-2">
                  <span className="text-green-300">Tax Savings:</span>
                  <span className="text-green-400 font-semibold">
                    +{MoneyMakerTypes.formatGP(Math.min(calculation.sell_price * 0.02, 5_000_000))}
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* Tax Rules Reference */}
          <div className="bg-gray-900 rounded-lg p-4 border border-gray-700">
            <h4 className="text-lg font-semibold text-white mb-3">GE Tax Rules</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-gray-300 mb-2"><strong>Base Rate:</strong></p>
                <p className="text-white">{calculation.tax_rules.base_rate}</p>
              </div>
              
              <div>
                <p className="text-gray-300 mb-2"><strong>Exemption Threshold:</strong></p>
                <p className="text-white">{calculation.tax_rules.exemption_threshold}</p>
              </div>
              
              <div>
                <p className="text-gray-300 mb-2"><strong>Maximum Tax:</strong></p>
                <p className="text-white">{calculation.tax_rules.maximum_tax}</p>
              </div>
              
              <div>
                <p className="text-gray-300 mb-2"><strong>Exempt Items:</strong></p>
                <p className="text-green-400">{calculation.tax_rules.exempt_items.join(', ')}</p>
              </div>
            </div>
          </div>

          {/* Profit Scenarios */}
          {!calculation.is_tax_exempt && calculation.sell_price >= 100_000 && (
            <div className="bg-gray-900 rounded-lg p-4 border border-gray-700">
              <h4 className="text-lg font-semibold text-white mb-3">Bond Flipping Comparison</h4>
              <p className="text-gray-400 text-sm mb-3">
                See how much you'd save with tax-exempt Old School Bonds:
              </p>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="text-center p-3 bg-red-900/20 border border-red-700/50 rounded">
                  <p className="text-red-300 text-sm">Regular Items</p>
                  <p className="text-white font-bold">{MoneyMakerTypes.formatGP(calculation.net_received)}</p>
                  <p className="text-red-400 text-xs">-{MoneyMakerTypes.formatGP(calculation.ge_tax)} tax</p>
                </div>
                
                <div className="text-center p-3 bg-green-900/20 border border-green-700/50 rounded">
                  <p className="text-green-300 text-sm">Bonds (Tax Exempt)</p>
                  <p className="text-white font-bold">{MoneyMakerTypes.formatGP(calculation.sell_price)}</p>
                  <p className="text-green-400 text-xs">+{MoneyMakerTypes.formatGP(calculation.ge_tax)} saved</p>
                </div>
              </div>
            </div>
          )}
        </motion.div>
      )}

      {loading && (
        <div className="text-center py-4">
          <div className="inline-block animate-spin rounded-full h-6 w-6 border-b-2 border-blue-400"></div>
          <span className="ml-2 text-gray-400">Calculating...</span>
        </div>
      )}
    </motion.div>
  );
};