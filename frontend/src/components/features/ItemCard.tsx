import React from 'react';
import { motion } from 'framer-motion';
import { TrendingUp, TrendingDown, Crown, Users, Database, Clock, Shield, Zap, Star } from 'lucide-react';
import type { Item, PriceSourceMetadata } from '../../types';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';

interface ItemCardProps {
  item: Item;
  onClick?: () => void;
}

export const ItemCard: React.FC<ItemCardProps> = ({ item, onClick }) => {
  const formatGP = (amount: number | null | undefined) => {
    // Handle null, undefined, or invalid numbers
    if (amount == null || isNaN(Number(amount))) {
      return '0';
    }
    
    const num = Number(amount);
    if (num >= 1000000) {
      return `${(num / 1000000).toFixed(1)}M`;
    } else if (num >= 1000) {
      return `${(num / 1000).toFixed(1)}K`;
    }
    return num.toString();
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

  // High Alchemy specific helper functions
  const getAlchViabilityScore = (item: Item) => {
    return item.profit_calc?.high_alch_viability_score ?? 0;
  };

  const getAlchEfficiencyRating = (item: Item) => {
    return item.profit_calc?.alch_efficiency_rating ?? 0;
  };

  const getSustainableAlchPotential = (item: Item) => {
    return item.profit_calc?.sustainable_alch_potential ?? 0;
  };

  const getMagicXpEfficiency = (item: Item) => {
    return item.profit_calc?.magic_xp_efficiency ?? 0;
  };

  const getNetAlchProfit = (item: Item) => {
    const buyPrice = getCurrentBuyPrice(item);
    const natureRuneCost = 180;
    return item.high_alch - natureRuneCost - buyPrice;
  };

  const getAlchViabilityBadge = (score: number) => {
    if (score >= 80) return { variant: 'success' as const, text: 'Excellent Alch', icon: Star };
    if (score >= 60) return { variant: 'info' as const, text: 'Good Alch', icon: Zap };
    if (score >= 40) return { variant: 'warning' as const, text: 'Fair Alch', icon: Zap };
    return { variant: 'neutral' as const, text: 'Poor Alch', icon: Zap };
  };

  const getProfitColor = (profit: number) => {
    if (profit > 0) return 'text-green-400';
    if (profit < 0) return 'text-red-400';
    return 'text-gray-400';
  };

  const getRecommendationBadge = (score: number) => {
    if (score >= 0.8) return { variant: 'success' as const, text: 'Excellent' };
    if (score >= 0.6) return { variant: 'info' as const, text: 'Good' };
    if (score >= 0.4) return { variant: 'warning' as const, text: 'Fair' };
    return { variant: 'neutral' as const, text: 'Low' };
  };

  const getDataSourceInfo = (item: Item) => {
    // Try nested metadata first, then fallback to top-level fields
    const metadata = item.profit_calc?.price_source_metadata;
    const source = metadata?.source || item.data_source;
    const quality = metadata?.quality || item.data_quality;
    const confidence = metadata?.confidence_score ?? item.confidence_score;
    const ageHours = metadata?.age_hours ?? item.data_age_hours;
    
    if (!source || source === 'unknown') return null;

    const sourceNames: { [key: string]: string } = {
      'weird_gloop': 'Weird Gloop',
      'wiki_timeseries_5m': 'Wiki 5m',
      'wiki_timeseries_1h': 'Wiki 1h',
      'wiki_latest': 'Wiki Latest'
    };

    const qualityColors: { [key: string]: string } = {
      'fresh': 'text-green-400',
      'recent': 'text-blue-400',
      'acceptable': 'text-yellow-400',
      'stale': 'text-red-400',
      'unknown': 'text-gray-400'
    };

    const qualityIcons: { [key: string]: any } = {
      'fresh': Shield,
      'recent': Database,
      'acceptable': Clock,
      'stale': Clock,
      'unknown': Database
    };

    const safeQuality = quality || 'unknown';
    const Icon = qualityIcons[safeQuality] || Database;
    
    return {
      sourceName: sourceNames[source] || source,
      quality: safeQuality,
      colorClass: qualityColors[safeQuality] || 'text-gray-400',
      Icon,
      ageHours: ageHours || 0,
      confidence: confidence || 0.5
    };
  };

  const formatTimeAgo = (hours: number) => {
    if (hours < 1) return `${Math.round(hours * 60)}m`;
    if (hours < 24) return `${Math.round(hours)}h`;
    return `${Math.round(hours / 24)}d`;
  };

  const recommendation = getRecommendationBadge(getRecommendationScore(item));
  const alchViability = getAlchViabilityBadge(getAlchViabilityScore(item));
  const sourceInfo = getDataSourceInfo(item);
  
  // Determine if we should show high alchemy specific metrics
  const showAlchMetrics = getAlchViabilityScore(item) > 0 || getCurrentProfit(item) > 0;

  return (
    <Card hover onClick={onClick} className="flex flex-col min-h-[320px] h-full">
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div className="flex-1 min-w-0 pr-3">
          <h3 className="text-lg font-semibold text-white leading-6 mb-3 overflow-hidden"
              style={{ 
                display: '-webkit-box',
                WebkitLineClamp: 2,
                WebkitBoxOrient: 'vertical',
                height: '3rem',
                lineHeight: '1.5rem'
              }}>
            {item.name}
          </h3>
          <p className="text-sm text-gray-400 leading-5 overflow-hidden"
             style={{ 
               display: '-webkit-box',
               WebkitLineClamp: 2,
               WebkitBoxOrient: 'vertical',
               height: '2.5rem',
               lineHeight: '1.25rem'
             }}>
            {item.examine}
          </p>
        </div>
        <div className="flex items-start space-x-2 flex-shrink-0">
          {item.members && (
            <Crown className="w-4 h-4 text-accent-500 mt-0.5" />
          )}
          {showAlchMetrics && getAlchViabilityScore(item) >= 40 ? (
            <div className="flex items-center space-x-1">
              <Badge variant={alchViability.variant} size="sm">
                <alchViability.icon className="w-3 h-3 mr-1" />
                {alchViability.text}
              </Badge>
            </div>
          ) : (
            <Badge variant={recommendation.variant} size="sm">
              {recommendation.text}
            </Badge>
          )}
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 gap-4 mb-5">
        <div className="space-y-2">
          <div className="text-xs text-gray-400 uppercase tracking-wider min-h-[1.25rem] flex items-center overflow-hidden">
            High Alch Value
          </div>
          <div className="text-lg font-semibold text-accent-400 min-h-[2rem] flex items-center overflow-hidden">
            {formatGP(item.high_alch)} GP
          </div>
        </div>
        <div className="space-y-2">
          <div className="text-xs text-gray-400 uppercase tracking-wider min-h-[1.25rem] flex items-center overflow-hidden">
            Buy Price (GE)
          </div>
          <div className="flex flex-col">
            <div className="text-lg font-semibold text-white min-h-[2rem] flex items-center overflow-hidden">
              {formatGP(getCurrentBuyPrice(item))} GP
            </div>
            {/* Enhanced price transparency with multi-source data */}
            <div className="flex flex-col space-y-1">
              <div className="text-xs text-blue-400">
                Instant-buy price
              </div>
              {sourceInfo && (
                <div className="flex items-center space-x-1 text-xs">
                  <sourceInfo.Icon className="w-3 h-3" />
                  <span className={sourceInfo.colorClass}>
                    {sourceInfo.sourceName}
                  </span>
                  <span className="text-gray-500">•</span>
                  <span className="text-gray-400">
                    {formatTimeAgo(sourceInfo.ageHours)} ago
                  </span>
                  {sourceInfo.confidence < 0.5 && (
                    <>
                      <span className="text-gray-500">•</span>
                      <span className="text-yellow-400">Low confidence</span>
                    </>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Profit Information */}
      <div className="bg-black/20 rounded-lg p-4 space-y-3 mb-5 flex-1">
        {showAlchMetrics ? (
          <>
            {/* High Alchemy Focused Display */}
            <div className="flex items-center justify-between min-h-[1.5rem]">
              <span className="text-sm text-gray-300 flex-shrink-0">Net Alch Profit:</span>
              <div className={`font-semibold flex items-center gap-1 ${getProfitColor(getNetAlchProfit(item))}`}>
                <Zap className="w-4 h-4 flex-shrink-0 text-purple-400" />
                <span className="whitespace-nowrap text-right">
                  {getNetAlchProfit(item) > 0 ? '+' : ''}{formatGP(getNetAlchProfit(item))} GP
                </span>
              </div>
            </div>
            <div className="flex items-center justify-between min-h-[1.5rem]">
              <span className="text-sm text-gray-300 flex-shrink-0">Magic XP per Cast:</span>
              <div className="font-semibold text-blue-400 whitespace-nowrap">
                65 XP
              </div>
            </div>
            {getAlchViabilityScore(item) > 0 && (
              <div className="flex items-center justify-between min-h-[1.5rem]">
                <span className="text-sm text-gray-300 flex-shrink-0">Alch Viability:</span>
                <div className={`font-semibold whitespace-nowrap ${
                  getAlchViabilityScore(item) >= 80 ? 'text-green-400' :
                  getAlchViabilityScore(item) >= 60 ? 'text-blue-400' :
                  getAlchViabilityScore(item) >= 40 ? 'text-yellow-400' : 'text-gray-400'
                }`}>
                  {getAlchViabilityScore(item)}/100
                </div>
              </div>
            )}
          </>
        ) : (
          <>
            {/* Standard Trading Display */}
            <div className="flex items-center justify-between min-h-[1.5rem]">
              <span className="text-sm text-gray-300 flex-shrink-0">Profit per Item:</span>
              <div className={`font-semibold flex items-center gap-1 ${getProfitColor(getCurrentProfit(item))}`}>
                {getCurrentProfit(item) > 0 ? (
                  <TrendingUp className="w-4 h-4 flex-shrink-0" />
                ) : (
                  <TrendingDown className="w-4 h-4 flex-shrink-0" />
                )}
                <span className="whitespace-nowrap text-right">
                  {getCurrentProfit(item) > 0 ? '+' : ''}{formatGP(getCurrentProfit(item))} GP
                </span>
              </div>
            </div>
            <div className="flex items-center justify-between min-h-[1.5rem]">
              <span className="text-sm text-gray-300 flex-shrink-0">Profit Margin:</span>
              <div className={`font-semibold whitespace-nowrap ${getProfitColor(getCurrentProfit(item))}`}>
                {getCurrentProfitMargin(item).toFixed(2)}%
              </div>
            </div>
          </>
        )}
        
        {/* Data quality warning for stale data */}
        {sourceInfo && (sourceInfo.quality === 'stale' || sourceInfo.confidence < 0.3) && (
          <div className="flex items-center space-x-1 text-xs text-yellow-400 bg-yellow-400/10 px-2 py-1 rounded border border-yellow-400/20">
            <Clock className="w-3 h-3 flex-shrink-0" />
            <span>
              {sourceInfo.quality === 'stale' ? 'Stale price data' : 'Low confidence data'}
            </span>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between text-xs text-gray-400 mt-auto min-h-[1.5rem] py-1">
        <div className="flex items-center space-x-1 flex-1 min-w-0">
          <Users className="w-3 h-3 flex-shrink-0" />
          <span className="truncate">Limit: {item.limit || 'Unlimited'}</span>
        </div>
        <div className="whitespace-nowrap flex-shrink-0 ml-2">
          ID: {item.item_id}
        </div>
      </div>
    </Card>
  );
};