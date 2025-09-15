import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { XMarkIcon, CalculatorIcon } from '@heroicons/react/24/outline';
import { Shield } from 'lucide-react';
import type { SetCombiningOpportunity } from '../../types/tradingStrategies';
import SetCombiningCalculator from './SetCombiningCalculator';

interface SetCombiningCalculatorModalProps {
  isOpen: boolean;
  onClose: () => void;
  opportunity: SetCombiningOpportunity;
}

export const SetCombiningCalculatorModal: React.FC<SetCombiningCalculatorModalProps> = ({
  isOpen,
  onClose,
  opportunity
}) => {
  if (!isOpen || !opportunity) return null;

  const handleClose = () => {
    console.log('🧮 Calculator modal closing');
    onClose();
  };

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
        onClick={handleClose}
      >
        <motion.div
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.9, opacity: 0 }}
          className="bg-gray-900 border border-gray-700 rounded-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="p-6 border-b border-gray-700 bg-gradient-to-r from-blue-900/20 to-indigo-900/20">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-500/20 rounded-lg">
                  <CalculatorIcon className="w-6 h-6 text-blue-400" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-white">Set Combining Calculator</h2>
                  <p className="text-gray-400 flex items-center gap-2">
                    <Shield className="w-4 h-4" />
                    {opportunity.set_name}
                  </p>
                </div>
              </div>
              <button
                onClick={handleClose}
                className="p-2 hover:bg-gray-700 rounded-lg transition-colors"
              >
                <XMarkIcon className="w-6 h-6 text-gray-400" />
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="p-6">
            <SetCombiningCalculator
              initialData={{
                set_name: opportunity.set_name || 'Unknown Set',
                set_item_id: opportunity.set_item_id || 0,
                strategy: (opportunity as any).strategy_description?.includes('Buy individual pieces') ? 'combining' : 'decombining',
                strategy_description: (opportunity as any).strategy_description || 'Buy complete set → Sell individual pieces for lazy tax profit',
                piece_ids: opportunity.piece_ids || [],
                piece_names: opportunity.piece_names || [],
                individual_pieces_total_cost: opportunity.individual_pieces_total_cost || 0,
                complete_set_price: opportunity.complete_set_price || 0,
                lazy_tax_profit: opportunity.lazy_tax_profit || 0,
                profit_margin_pct: opportunity.profit_margin_pct || 0,
                required_capital: (opportunity as any).required_capital || opportunity.complete_set_price || opportunity.individual_pieces_total_cost || 0,
                volume_score: (opportunity as any).volume_score || 0.5,
                confidence_score: (opportunity as any).confidence_score || 0.5,
                ai_risk_level: (opportunity as any).ai_risk_level || opportunity.risk_level || opportunity.strategy?.risk_level || 'medium' as 'low' | 'medium' | 'high',
                estimated_sets_per_hour: (opportunity as any).estimated_sets_per_hour || Math.min(12, opportunity.set_volume || 6),
                pieces_data: (opportunity as any).pieces_data || opportunity.piece_names.map((name: string, i: number) => {
                  // Get piece price safely
                  let piecePrice = 0;
                  if (opportunity.piece_prices && Array.isArray(opportunity.piece_prices) && i < opportunity.piece_prices.length) {
                    piecePrice = opportunity.piece_prices[i] || 0;
                  } else if (opportunity.individual_pieces_total_cost && opportunity.piece_names.length > 0) {
                    piecePrice = Math.round(opportunity.individual_pieces_total_cost / opportunity.piece_names.length);
                  }
                  
                  // Get piece volume safely
                  let pieceVolume = 0;
                  if (opportunity.piece_volumes) {
                    if (Array.isArray(opportunity.piece_volumes) && i < opportunity.piece_volumes.length) {
                      pieceVolume = opportunity.piece_volumes[i] || 0;
                    } else if (typeof opportunity.piece_volumes === 'object' && opportunity.piece_ids && i < opportunity.piece_ids.length) {
                      const itemId = opportunity.piece_ids[i];
                      pieceVolume = opportunity.piece_volumes[itemId.toString()] || 0;
                    }
                  }
                  
                  return {
                    item_id: opportunity.piece_ids?.[i] || 0,
                    name: name || `Piece ${i + 1}`,
                    buy_price: piecePrice,
                    sell_price: piecePrice,
                    volume_score: pieceVolume > 0 ? Math.min(1, pieceVolume / 10000) : 0.1, // Normalize volume to 0-1
                    age_hours: (opportunity as any).avg_data_age_hours || 2
                  };
                }),
                ge_tax: (opportunity as any).ge_tax || Math.round(opportunity.complete_set_price * 0.01) || 0, // 1% GE tax estimate
                avg_data_age_hours: (opportunity as any).avg_data_age_hours || 2
              }}
            />
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};

export default SetCombiningCalculatorModal;