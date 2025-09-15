import React, { useState } from 'react';
import { Calendar, ChevronDown } from 'lucide-react';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';

export type TimeRange = '1h' | '6h' | '24h' | '7d' | '30d' | '90d' | 'custom';

interface DateRangePickerProps {
  selectedRange: TimeRange;
  onRangeChange: (range: TimeRange) => void;
  customStartDate?: Date;
  customEndDate?: Date;
  onCustomDateChange?: (startDate: Date, endDate: Date) => void;
}

export const DateRangePicker: React.FC<DateRangePickerProps> = ({
  selectedRange,
  onRangeChange,
  customStartDate,
  customEndDate,
  onCustomDateChange
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [showCustomPicker, setShowCustomPicker] = useState(false);

  const timeRangeOptions: { value: TimeRange; label: string; description: string }[] = [
    { value: '1h', label: 'Last Hour', description: 'Past 60 minutes' },
    { value: '6h', label: 'Last 6 Hours', description: 'Past 6 hours' },
    { value: '24h', label: 'Last 24 Hours', description: 'Past day' },
    { value: '7d', label: 'Last 7 Days', description: 'Past week' },
    { value: '30d', label: 'Last 30 Days', description: 'Past month' },
    { value: '90d', label: 'Last 90 Days', description: 'Past quarter' },
    { value: 'custom', label: 'Custom Range', description: 'Select specific dates' }
  ];

  const getSelectedOptionLabel = () => {
    const option = timeRangeOptions.find(opt => opt.value === selectedRange);
    if (selectedRange === 'custom' && customStartDate && customEndDate) {
      return `${customStartDate.toLocaleDateString()} - ${customEndDate.toLocaleDateString()}`;
    }
    return option?.label || 'Select Range';
  };

  const handleRangeSelect = (range: TimeRange) => {
    if (range === 'custom') {
      setShowCustomPicker(true);
    } else {
      setShowCustomPicker(false);
      onRangeChange(range);
      setIsOpen(false);
    }
  };

  const handleCustomDateSubmit = () => {
    if (customStartDate && customEndDate && onCustomDateChange) {
      onCustomDateChange(customStartDate, customEndDate);
      onRangeChange('custom');
      setShowCustomPicker(false);
      setIsOpen(false);
    }
  };

  const formatDateForInput = (date?: Date): string => {
    if (!date) return '';
    return date.toISOString().split('T')[0];
  };

  const parseInputDate = (dateString: string): Date => {
    return new Date(dateString + 'T00:00:00');
  };

  return (
    <div className="relative">
      <Button
        variant="outline"
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 min-w-48"
      >
        <Calendar className="w-4 h-4" />
        <span className="flex-1 text-left truncate">{getSelectedOptionLabel()}</span>
        <ChevronDown className={`w-4 h-4 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </Button>

      {isOpen && (
        <div className="absolute top-full left-0 mt-2 z-20">
          <Card className="p-4 min-w-80 shadow-xl border border-white/20">
            {!showCustomPicker ? (
              <div className="space-y-2">
                <div className="text-sm font-medium text-gray-300 mb-3">Select Time Range</div>
                {timeRangeOptions.map((option) => (
                  <button
                    key={option.value}
                    onClick={() => handleRangeSelect(option.value)}
                    className={`w-full text-left p-3 rounded-lg transition-colors ${
                      selectedRange === option.value
                        ? 'bg-accent-500/20 border border-accent-500/30 text-accent-400'
                        : 'bg-white/5 hover:bg-white/10 text-white border border-transparent'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-medium">{option.label}</div>
                        <div className="text-xs text-gray-400 mt-0.5">{option.description}</div>
                      </div>
                      {selectedRange === option.value && (
                        <div className="w-2 h-2 bg-accent-400 rounded-full" />
                      )}
                    </div>
                  </button>
                ))}
              </div>
            ) : (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="text-sm font-medium text-gray-300">Custom Date Range</div>
                  <button
                    onClick={() => setShowCustomPicker(false)}
                    className="text-gray-400 hover:text-white text-sm"
                  >
                    Back
                  </button>
                </div>

                <div className="space-y-3">
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">Start Date</label>
                    <input
                      type="date"
                      value={formatDateForInput(customStartDate)}
                      onChange={(e) => onCustomDateChange?.(parseInputDate(e.target.value), customEndDate || new Date())}
                      className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white text-sm focus:border-accent-400 focus:outline-none"
                    />
                  </div>

                  <div>
                    <label className="block text-xs text-gray-400 mb-1">End Date</label>
                    <input
                      type="date"
                      value={formatDateForInput(customEndDate)}
                      min={formatDateForInput(customStartDate)}
                      onChange={(e) => onCustomDateChange?.(customStartDate || new Date(), parseInputDate(e.target.value))}
                      className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white text-sm focus:border-accent-400 focus:outline-none"
                    />
                  </div>
                </div>

                <div className="flex gap-2 pt-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setShowCustomPicker(false)}
                    className="flex-1"
                  >
                    Cancel
                  </Button>
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={handleCustomDateSubmit}
                    disabled={!customStartDate || !customEndDate}
                    className="flex-1"
                  >
                    Apply
                  </Button>
                </div>
              </div>
            )}
          </Card>
        </div>
      )}

      {/* Backdrop to close dropdown */}
      {isOpen && (
        <div 
          className="fixed inset-0 z-10" 
          onClick={() => {
            setIsOpen(false);
            setShowCustomPicker(false);
          }}
        />
      )}
    </div>
  );
};