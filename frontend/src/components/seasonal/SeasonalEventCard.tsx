import React from 'react';
import { motion } from 'framer-motion';
import { 
  CalendarDaysIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  ClockIcon,
  CheckBadgeIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon
} from '@heroicons/react/24/outline';
import type { SeasonalEvent } from '../../types/seasonal';

interface SeasonalEventCardProps {
  event: SeasonalEvent;
  onClick?: () => void;
  className?: string;
}

export function SeasonalEventCard({ event, onClick, className = '' }: SeasonalEventCardProps) {
  const formatPercentage = (value: number) => {
    return `${value > 0 ? '+' : ''}${value.toFixed(1)}%`;
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric',
      year: date.getFullYear() !== new Date().getFullYear() ? 'numeric' : undefined
    });
  };

  const getEventTypeColor = (type: string) => {
    switch (type) {
      case 'osrs_official': return 'text-blue-400 bg-blue-400/10';
      case 'community': return 'text-green-400 bg-green-400/10';
      case 'detected_anomaly': return 'text-orange-400 bg-orange-400/10';
      case 'holiday': return 'text-purple-400 bg-purple-400/10';
      case 'update': return 'text-red-400 bg-red-400/10';
      case 'seasonal': return 'text-yellow-400 bg-yellow-400/10';
      default: return 'text-gray-400 bg-gray-400/10';
    }
  };

  const getVerificationIcon = (status: string) => {
    switch (status) {
      case 'verified': return <CheckBadgeIcon className="w-5 h-5 text-green-400" />;
      case 'disputed': return <ExclamationTriangleIcon className="w-5 h-5 text-red-400" />;
      default: return <InformationCircleIcon className="w-5 h-5 text-gray-400" />;
    }
  };

  const getImpactColor = (impact: number) => {
    const absImpact = Math.abs(impact);
    if (absImpact >= 20) return impact > 0 ? 'text-green-400' : 'text-red-400';
    if (absImpact >= 10) return impact > 0 ? 'text-green-300' : 'text-red-300';
    if (absImpact >= 5) return impact > 0 ? 'text-green-200' : 'text-red-200';
    return 'text-gray-400';
  };

  const getRecurrenceDisplay = (pattern: string, isRecurring: boolean) => {
    if (!isRecurring) return 'One-time';
    switch (pattern) {
      case 'weekly': return 'Weekly';
      case 'monthly': return 'Monthly';
      case 'quarterly': return 'Quarterly';
      case 'yearly': return 'Yearly';
      default: return 'Recurring';
    }
  };

  const getTimeStatus = () => {
    const now = new Date();
    const startDate = event.start_date ? new Date(event.start_date) : null;
    const endDate = event.end_date ? new Date(event.end_date) : null;

    if (event.is_current) return { text: 'Currently Active', color: 'text-green-400' };
    if (event.is_upcoming) return { text: `${event.days_until_start} days until start`, color: 'text-blue-400' };
    if (endDate && endDate < now) return { text: 'Ended', color: 'text-gray-400' };
    return { text: 'Scheduled', color: 'text-yellow-400' };
  };

  const timeStatus = getTimeStatus();
  const priceImpact = event.average_price_impact_pct;
  const volumeImpact = event.average_volume_impact_pct;

  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      className={`bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6 cursor-pointer transition-all duration-200 hover:border-blue-500/50 hover:shadow-lg hover:shadow-blue-500/10 ${className}`}
      onClick={onClick}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-gray-100 mb-2">
            {event.event_name}
          </h3>
          <div className="flex items-center gap-2 mb-2">
            <div className={`px-3 py-1 rounded-full text-xs font-semibold ${getEventTypeColor(event.event_type)}`}>
              {event.event_type.replace('_', ' ').toUpperCase()}
            </div>
            <div className={`text-xs font-semibold ${timeStatus.color}`}>
              {timeStatus.text}
            </div>
          </div>
        </div>
        <div className="flex flex-col items-end gap-2">
          {getVerificationIcon(event.verification_status)}
          {event.has_significant_impact && (
            <div className="px-2 py-1 rounded-full text-xs font-semibold text-orange-400 bg-orange-400/10">
              HIGH IMPACT
            </div>
          )}
        </div>
      </div>

      {/* Description */}
      <div className="mb-4">
        <p className="text-sm text-gray-300 leading-relaxed">
          {event.description}
        </p>
      </div>

      {/* Event Timing */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <CalendarDaysIcon className="w-4 h-4 text-gray-400" />
            <span className="text-xs text-gray-400">Duration</span>
          </div>
          <div className="text-sm font-semibold text-gray-200">
            {event.duration_days} {event.duration_days === 1 ? 'day' : 'days'}
          </div>
        </div>
        <div>
          <div className="flex items-center gap-2 mb-1">
            <ClockIcon className="w-4 h-4 text-gray-400" />
            <span className="text-xs text-gray-400">Recurrence</span>
          </div>
          <div className="text-sm font-semibold text-gray-200">
            {getRecurrenceDisplay(event.recurrence_pattern, event.is_recurring)}
          </div>
        </div>
      </div>

      {/* Date Range */}
      {(event.start_date || event.end_date) && (
        <div className="mb-4">
          <div className="flex items-center justify-between">
            {event.start_date && (
              <div className="text-center">
                <div className="text-xs text-gray-400 mb-1">Start Date</div>
                <div className="text-sm font-semibold text-green-400">
                  {formatDate(event.start_date)}
                </div>
              </div>
            )}
            {event.end_date && (
              <div className="text-center">
                <div className="text-xs text-gray-400 mb-1">End Date</div>
                <div className="text-sm font-semibold text-red-400">
                  {formatDate(event.end_date)}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Market Impact */}
      <div className="mb-4">
        <div className="text-sm text-gray-400 mb-3">Expected Market Impact</div>
        <div className="grid grid-cols-2 gap-4">
          <div className="text-center">
            <div className="flex items-center justify-center gap-2 mb-1">
              {priceImpact >= 0 ? (
                <ArrowTrendingUpIcon className="w-4 h-4 text-green-400" />
              ) : (
                <ArrowTrendingDownIcon className="w-4 h-4 text-red-400" />
              )}
              <span className="text-xs text-gray-400">Price Impact</span>
            </div>
            <div className={`text-lg font-bold ${getImpactColor(priceImpact)}`}>
              {formatPercentage(priceImpact)}
            </div>
          </div>
          <div className="text-center">
            <div className="flex items-center justify-center gap-2 mb-1">
              {volumeImpact >= 0 ? (
                <ArrowTrendingUpIcon className="w-4 h-4 text-blue-400" />
              ) : (
                <ArrowTrendingDownIcon className="w-4 h-4 text-blue-400" />
              )}
              <span className="text-xs text-gray-400">Volume Impact</span>
            </div>
            <div className={`text-lg font-bold ${getImpactColor(volumeImpact)}`}>
              {formatPercentage(volumeImpact)}
            </div>
          </div>
        </div>
      </div>

      {/* Impact Confidence */}
      <div className="mb-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-gray-400">Impact Confidence</span>
          <span className="text-sm font-semibold text-blue-400">
            {(event.impact_confidence * 100).toFixed(0)}%
          </span>
        </div>
        <div className="flex-1 bg-gray-700 rounded-full h-2">
          <div 
            className="bg-gradient-to-r from-blue-500 to-purple-500 h-full rounded-full transition-all duration-300"
            style={{ width: `${event.impact_confidence * 100}%` }}
          />
        </div>
      </div>

      {/* Affected Categories */}
      {event.affected_categories.length > 0 && (
        <div className="mb-4">
          <div className="text-sm text-gray-400 mb-2">Affected Categories</div>
          <div className="flex flex-wrap gap-2">
            {event.affected_categories.slice(0, 4).map((category, index) => (
              <div key={index} className="px-2 py-1 rounded-full text-xs font-medium text-blue-400 bg-blue-400/10">
                {category}
              </div>
            ))}
            {event.affected_categories.length > 4 && (
              <div className="px-2 py-1 rounded-full text-xs font-medium text-gray-400 bg-gray-400/10">
                +{event.affected_categories.length - 4} more
              </div>
            )}
          </div>
        </div>
      )}

      {/* Historical Data */}
      {event.historical_occurrences.length > 0 && (
        <div className="mb-4">
          <div className="text-sm text-gray-400 mb-2">Historical Pattern</div>
          <div className="text-sm text-gray-300">
            Occurred {event.historical_occurrences.length} time{event.historical_occurrences.length !== 1 ? 's' : ''} previously
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between mt-4 pt-3 border-t border-gray-700/50">
        <div className="text-xs text-gray-500">
          {event.detection_method}
        </div>
        <div className="text-xs text-gray-500">
          ID: {event.id}
        </div>
      </div>

      {/* Status Badge */}
      <div className="flex items-center justify-between mt-2">
        <div className={`text-xs font-semibold ${
          event.verification_status === 'verified' ? 'text-green-400' :
          event.verification_status === 'disputed' ? 'text-red-400' :
          'text-gray-400'
        }`}>
          {event.verification_status.toUpperCase()}
        </div>
        {event.is_active && (
          <div className="px-2 py-1 rounded-full text-xs font-semibold text-green-400 bg-green-400/10">
            ACTIVE
          </div>
        )}
      </div>
    </motion.div>
  );
}

export default SeasonalEventCard;