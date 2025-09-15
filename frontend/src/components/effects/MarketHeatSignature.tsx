import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Activity, TrendingUp, TrendingDown, Zap } from 'lucide-react';
import type { MarketAnalysis, Item } from '../../types';

interface MarketHeatSignatureProps {
  marketData: MarketAnalysis;
  className?: string;
}

interface MarketSector {
  id: string;
  name: string;
  x: number;
  y: number;
  width: number;
  height: number;
  profitability: number;
  trend: 'rising' | 'stable' | 'declining';
  itemCount: number;
  averageProfit: number;
  topItems: string[];
  riskLevel: 'low' | 'medium' | 'high';
  liquidity: 'high' | 'medium' | 'low';
}

interface HeatZone {
  id: number;
  x: number;
  y: number;
  intensity: number;
  type: 'hot' | 'warm' | 'cold' | 'volatile';
  value: number;
  sector?: MarketSector;
  itemName?: string;
  profit?: number;
  volume?: number;
}

export const MarketHeatSignature: React.FC<MarketHeatSignatureProps> = ({
  marketData,
  className = ''
}) => {
  const [heatZones, setHeatZones] = useState<HeatZone[]>([]);
  const [marketSectors, setMarketSectors] = useState<MarketSector[]>([]);
  const [scanLine, setScanLine] = useState(0);
  const [realMarketData, setRealMarketData] = useState<{
    weapons: Item[];
    armor: Item[];
    runes: Item[];
    potions: Item[];
    resources: Item[];
  }>({ weapons: [], armor: [], runes: [], potions: [], resources: [] });
  const [dataLoading, setDataLoading] = useState(true);
  const [dataError, setDataError] = useState<string | null>(null);

  // Fetch real market data from API
  useEffect(() => {
    const fetchMarketData = async () => {
      setDataLoading(true);
      try {
        // Fetch different categories of items with real profit data
        const [weaponsRes, armorRes, runesRes, potionsRes, resourcesRes] = await Promise.all([
          fetch('/api/v1/items/?search=sword&ordering=-current_profit&page_size=10'),
          fetch('/api/v1/items/?search=platebody&ordering=-current_profit&page_size=10'),
          fetch('/api/v1/items/?search=rune&ordering=-current_profit&page_size=10'),
          fetch('/api/v1/items/?search=potion&ordering=-current_profit&page_size=10'),
          fetch('/api/v1/items/?search=ore&ordering=-current_profit&page_size=10')
        ]);

        const [weaponsData, armorData, runesData, potionsData, resourcesData] = await Promise.all([
          weaponsRes.json(),
          armorRes.json(),
          runesRes.json(),
          potionsRes.json(),
          resourcesRes.json()
        ]);

        setRealMarketData({
          weapons: weaponsData.results || [],
          armor: armorData.results || [],
          runes: runesData.results || [],
          potions: potionsData.results || [],
          resources: resourcesData.results || []
        });

        // Debug logging
        console.log('🗡️ Market Heat - Weapons loaded:', weaponsData.results?.length || 0, 
          weaponsData.results?.slice(0, 2).map(item => `${item.name}: ${item.current_profit}GP`));
        console.log('🛡️ Market Heat - Armor loaded:', armorData.results?.length || 0,
          armorData.results?.slice(0, 2).map(item => `${item.name}: ${item.current_profit}GP`));
        console.log('🔮 Market Heat - Runes loaded:', runesData.results?.length || 0,
          runesData.results?.slice(0, 2).map(item => `${item.name}: ${item.current_profit}GP`));
        console.log('⚗️ Market Heat - Potions loaded:', potionsData.results?.length || 0,
          potionsData.results?.slice(0, 2).map(item => `${item.name}: ${item.current_profit}GP`));
        console.log('⛏️ Market Heat - Resources loaded:', resourcesData.results?.length || 0,
          resourcesData.results?.slice(0, 2).map(item => `${item.name}: ${item.current_profit}GP`));
      } catch (error) {
        console.error('Failed to fetch market data:', error);
        setDataError('Failed to load live market data. Using cached data.');
      } finally {
        setDataLoading(false);
      }
    };

    fetchMarketData();
  }, []);

  // Generate market sectors and heat zones from real API data
  useEffect(() => {
    if (dataLoading) return;

    // Calculate real sector statistics
    const weaponStats = realMarketData.weapons.length > 0 ? {
      count: realMarketData.weapons.length,
      avgProfit: realMarketData.weapons.reduce((sum, item) => sum + (item.current_profit || 0), 0) / realMarketData.weapons.length,
      topItems: realMarketData.weapons.slice(0, 3).map(item => item.name)
    } : { count: 0, avgProfit: 0, topItems: [] };

    const armorStats = realMarketData.armor.length > 0 ? {
      count: realMarketData.armor.length,
      avgProfit: realMarketData.armor.reduce((sum, item) => sum + (item.current_profit || 0), 0) / realMarketData.armor.length,
      topItems: realMarketData.armor.slice(0, 3).map(item => item.name)
    } : { count: 0, avgProfit: 0, topItems: [] };

    const runeStats = realMarketData.runes.length > 0 ? {
      count: realMarketData.runes.length,
      avgProfit: realMarketData.runes.reduce((sum, item) => sum + (item.current_profit || 0), 0) / realMarketData.runes.length,
      topItems: realMarketData.runes.slice(0, 3).map(item => item.name)
    } : { count: 0, avgProfit: 0, topItems: [] };

    const potionStats = realMarketData.potions.length > 0 ? {
      count: realMarketData.potions.length,
      avgProfit: realMarketData.potions.reduce((sum, item) => sum + (item.current_profit || 0), 0) / realMarketData.potions.length,
      topItems: realMarketData.potions.slice(0, 3).map(item => item.name)
    } : { count: 0, avgProfit: 0, topItems: [] };

    const resourceStats = realMarketData.resources.length > 0 ? {
      count: realMarketData.resources.length,
      avgProfit: realMarketData.resources.reduce((sum, item) => sum + (item.current_profit || 0), 0) / realMarketData.resources.length,
      topItems: realMarketData.resources.slice(0, 3).map(item => item.name)
    } : { count: 0, avgProfit: 0, topItems: [] };

    // Define real market sectors with dynamic data and better positioning
    const sectors: MarketSector[] = [
      {
        id: 'weapons',
        name: 'Weapons',
        x: 15, y: 20, width: 25, height: 25, // Better positioning
        profitability: weaponStats.avgProfit > 500 ? 0.8 : weaponStats.avgProfit > 100 ? 0.5 : 0.2,
        trend: weaponStats.avgProfit > 300 ? 'rising' : weaponStats.avgProfit > 0 ? 'stable' : 'declining',
        itemCount: weaponStats.count,
        averageProfit: Math.round(weaponStats.avgProfit),
        topItems: weaponStats.topItems,
        riskLevel: 'medium',
        liquidity: 'medium'
      },
      {
        id: 'armor',
        name: 'Armor',
        x: 50, y: 15, width: 30, height: 25,
        profitability: armorStats.avgProfit > 1000 ? 0.9 : armorStats.avgProfit > 500 ? 0.6 : 0.3,
        trend: armorStats.avgProfit > 500 ? 'rising' : armorStats.avgProfit > 0 ? 'stable' : 'declining',
        itemCount: armorStats.count,
        averageProfit: Math.round(armorStats.avgProfit),
        topItems: armorStats.topItems,
        riskLevel: 'low',
        liquidity: 'high'
      },
      {
        id: 'resources',
        name: 'Resources',
        x: 20, y: 45, width: 35, height: 25, // Moved up for visibility
        profitability: resourceStats.avgProfit > 100 ? 0.4 : resourceStats.avgProfit > 0 ? 0.2 : 0.1,
        trend: resourceStats.avgProfit > 50 ? 'rising' : resourceStats.avgProfit > 0 ? 'stable' : 'declining',
        itemCount: resourceStats.count,
        averageProfit: Math.round(resourceStats.avgProfit),
        topItems: resourceStats.topItems,
        riskLevel: 'low',
        liquidity: 'high'
      },
      {
        id: 'consumables',
        name: 'Potions & Food',
        x: 60, y: 45, width: 25, height: 25, // Better positioning
        profitability: potionStats.avgProfit > 50 ? 0.3 : potionStats.avgProfit > 0 ? 0.2 : 0.1,
        trend: potionStats.avgProfit > 25 ? 'rising' : potionStats.avgProfit > 0 ? 'stable' : 'declining',
        itemCount: potionStats.count,
        averageProfit: Math.round(potionStats.avgProfit),
        topItems: potionStats.topItems,
        riskLevel: 'medium',
        liquidity: 'medium'
      },
      {
        id: 'runes',
        name: 'Runes & Magic',
        x: 10, y: 70, width: 30, height: 20, // Moved up and widened for visibility
        profitability: runeStats.avgProfit > 200 ? 0.4 : runeStats.avgProfit > 0 ? 0.2 : 0.1,
        trend: runeStats.avgProfit > 100 ? 'rising' : runeStats.avgProfit > 0 ? 'stable' : 'declining',
        itemCount: runeStats.count,
        averageProfit: Math.round(runeStats.avgProfit),
        topItems: runeStats.topItems,
        riskLevel: 'medium',
        liquidity: 'medium'
      }
    ];
    
    setMarketSectors(sectors);
    
    // Generate heat zones from real API data
    const zones: HeatZone[] = [];
    let zoneId = 0;
    
    // Hot zones - Top profitable items from all categories
    const allProfitableItems = [
      ...realMarketData.weapons.filter(item => (item.current_profit || 0) > 300),
      ...realMarketData.armor.filter(item => (item.current_profit || 0) > 300),
      ...realMarketData.runes.filter(item => (item.current_profit || 0) > 100),
      ...realMarketData.resources.filter(item => (item.current_profit || 0) > 50)
    ].sort((a, b) => (b.current_profit || 0) - (a.current_profit || 0)).slice(0, 6); // Reduce to 6 to avoid crowding
    
    // Position hot zones with better spacing to avoid overlap
    const hotPositions = [
      { x: 15, y: 15 }, { x: 45, y: 10 }, { x: 75, y: 15 }, { x: 85, y: 35 },
      { x: 75, y: 55 }, { x: 45, y: 60 }, { x: 15, y: 55 }, { x: 5, y: 35 }
    ];
    
    allProfitableItems.forEach((item, i) => {
      const position = hotPositions[i] || { x: 50, y: 50 };
      const profit = item.current_profit || 0;
      
      zones.push({
        id: zoneId++,
        x: position.x,
        y: position.y,
        intensity: Math.min(profit / 1000, 1),
        type: profit > 500 ? 'hot' : 'warm',
        value: profit,
        itemName: item.name,
        profit: profit,
        volume: item.daily_volume || 100
      });
    });
    
    // Add medium profit items from potions category - limited to 2 for cleaner display
    const mediumProfitPotions = realMarketData.potions
      .filter(item => (item.current_profit || 0) > 30 && (item.current_profit || 0) <= 300)
      .slice(0, 2);
    
    const warmPositions = [{ x: 25, y: 75 }, { x: 50, y: 80 }, { x: 75, y: 75 }];
    
    mediumProfitPotions.forEach((item, i) => {
      const position = warmPositions[i] || { x: 50, y: 70 };
      const profit = item.current_profit || 0;
      
      zones.push({
        id: zoneId++,
        x: position.x,
        y: position.y,
        intensity: Math.min(profit / 300, 0.7),
        type: 'warm',
        value: profit,
        itemName: item.name,
        profit: profit,
        volume: item.daily_volume || 50
      });
    });
    
    // Cold zones - Items with negative or very low profits - limited to 1 for cleaner display
    const lowProfitItems = [
      ...realMarketData.potions.filter(item => (item.current_profit || 0) <= 0),
      ...realMarketData.resources.filter(item => (item.current_profit || 0) <= 0)
    ].slice(0, 1);
    
    const coldPositions = [{ x: 10, y: 85 }, { x: 85, y: 85 }];
    
    lowProfitItems.forEach((item, i) => {
      const position = coldPositions[i] || { x: 75, y: 80 };
      const profit = item.current_profit || 0;
      
      zones.push({
        id: zoneId++,
        x: position.x,
        y: position.y,
        intensity: 0.4,
        type: 'cold',
        value: Math.abs(profit),
        itemName: item.name,
        profit: profit,
        volume: item.daily_volume || 10
      });
    });
    
    setHeatZones(zones);
  }, [marketData, realMarketData, dataLoading]);

  // Scanning animation - Much slower and less distracting
  useEffect(() => {
    const interval = setInterval(() => {
      setScanLine(prev => (prev >= 100 ? 0 : prev + 0.5)); // Slower increment
    }, 400); // Much slower update frequency
    
    return () => clearInterval(interval);
  }, []);

  const getZoneColor = (zone: HeatZone) => {
    switch (zone.type) {
      case 'hot':
        return `rgba(239, 68, 68, ${zone.intensity})`;  // Red for high profit
      case 'warm':
        return `rgba(251, 146, 60, ${zone.intensity})`;  // Orange for medium profit
      case 'volatile':
        return `rgba(245, 158, 11, ${zone.intensity})`;  // Yellow for volatile
      case 'cold':
        return `rgba(59, 130, 246, ${zone.intensity * 0.5})`; // Blue for low/negative profit
      default:
        return `rgba(156, 163, 175, ${zone.intensity})`;
    }
  };

  const getZoneIcon = (zone: HeatZone) => {
    switch (zone.type) {
      case 'hot':
        return <TrendingUp className="w-3 h-3 text-red-400" />;
      case 'warm':
        return <TrendingUp className="w-3 h-3 text-orange-400" />;
      case 'volatile':
        return <Zap className="w-3 h-3 text-yellow-400" />;
      case 'cold':
        return <TrendingDown className="w-3 h-3 text-blue-400" />;
      default:
        return <Activity className="w-3 h-3 text-gray-400" />;
    }
  };

  const formatValue = (value: number): string => {
    if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`;
    if (value >= 1000) return `${(value / 1000).toFixed(1)}K`;
    return Math.round(value).toString();
  };

  return (
    <div className={`relative bg-black/40 backdrop-blur-xl rounded-xl border border-cyan-400/30 overflow-hidden shadow-2xl shadow-cyan-400/20 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-cyan-400/20 bg-gradient-to-r from-black/80 to-black/60">
        <div className="flex items-center space-x-3">
          <motion.div
            animate={{ rotate: 360, scale: [1, 1.1, 1] }}
            transition={{ duration: 4, repeat: Infinity, ease: "linear" }}
            className="p-2 bg-cyan-500/20 rounded-lg border border-cyan-400/30"
          >
            <Activity className="w-5 h-5 text-cyan-400 drop-shadow-lg" />
          </motion.div>
          <div>
            <h3 className="text-lg font-semibold bg-gradient-to-r from-white via-cyan-200 to-blue-200 bg-clip-text text-transparent">
              Market Heat Signature
            </h3>
            <p className="text-xs text-cyan-300/80">Real-time profit zone analysis</p>
          </div>
        </div>
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-1">
            <div className="w-2 h-2 bg-cyan-400 rounded-full shadow-lg shadow-cyan-400/75" />
            <span className="text-xs text-cyan-300 font-medium">Live Scan</span>
          </div>
          <div className="text-xs text-gray-400 font-mono">
            {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </div>
        </div>
      </div>

      {/* Enhanced Heat Map Container - 3D Holographic Terrain */}
      <div className="relative h-full min-h-[800px] bg-gradient-to-b from-black/90 via-gray-900/70 to-black/95 overflow-hidden rounded-lg border border-cyan-400/20">
        {/* Advanced 3D Grid System */}
        <svg className="absolute inset-0 w-full h-full opacity-20" viewBox="0 0 100 100" style={{ filter: 'drop-shadow(0 0 2px rgba(6,182,212,0.4))' }}>
          <defs>
            {/* Hexagonal Grid Pattern - Enhanced */}
            <pattern id="hexGrid" width="6" height="6" patternUnits="userSpaceOnUse">
              <path d="M 3 0 L 6 1.5 L 6 4.5 L 3 6 L 0 4.5 L 0 1.5 Z" fill="none" stroke="#06b6d4" strokeWidth="0.4" opacity="0.8" />
              <circle cx="3" cy="3" r="0.3" fill="#06b6d4" opacity="0.6" />
            </pattern>
            {/* Major Grid Lines - 3D perspective */}
            <pattern id="majorGrid" width="20" height="20" patternUnits="userSpaceOnUse">
              <path d="M 20 0 L 0 0 0 20" fill="none" stroke="#06b6d4" strokeWidth="0.8" opacity="0.9" />
              <path d="M 0 0 L 20 20" fill="none" stroke="#0891b2" strokeWidth="0.4" opacity="0.5" />
            </pattern>
            {/* Energy Field Gradient */}
            <radialGradient id="energyField" cx="50%" cy="50%" r="70%">
              <stop offset="0%" stopColor="rgba(6,182,212,0.4)" />
              <stop offset="30%" stopColor="rgba(14,165,233,0.3)" />
              <stop offset="60%" stopColor="rgba(6,182,212,0.2)" />
              <stop offset="100%" stopColor="rgba(6,182,212,0)" />
            </radialGradient>
            {/* Holographic Data Stream */}
            <linearGradient id="dataStream" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="rgba(16,185,129,0.6)" />
              <stop offset="50%" stopColor="rgba(6,182,212,0.4)" />
              <stop offset="100%" stopColor="rgba(139,92,246,0.3)" />
            </linearGradient>
          </defs>
          <rect width="100%" height="100%" fill="url(#energyField)" />
          <rect width="100%" height="100%" fill="url(#hexGrid)" />
          <rect width="100%" height="100%" fill="url(#majorGrid)" />
          
          {/* Holographic Data Streams */}
          <path d="M 0 20 Q 25 10 50 25 T 100 15" fill="none" stroke="url(#dataStream)" strokeWidth="0.5" opacity="0.6" />
          <path d="M 0 70 Q 30 60 60 75 T 100 65" fill="none" stroke="url(#dataStream)" strokeWidth="0.5" opacity="0.4" />
        </svg>

        {/* Advanced 3D Holographic Terrain */}
        <div className="absolute inset-0">
          {/* Multi-layered Background Terrain */}
          <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/8 via-cyan-500/6 to-purple-500/8" />
          <div className="absolute inset-0 bg-gradient-radial from-cyan-400/10 via-transparent to-transparent" style={{ 
            background: 'radial-gradient(ellipse 60% 40% at 30% 70%, rgba(6,182,212,0.15) 0%, transparent 50%), radial-gradient(ellipse 50% 30% at 70% 30%, rgba(16,185,129,0.12) 0%, transparent 50%)'
          }} />
          
          {/* Holographic Depth Grid - Perspective Lines */}
          {[...Array(12)].map((_, i) => (
            <motion.div
              key={`depth-${i}`}
              className="absolute w-full h-px"
              style={{ 
                top: `${8 * (i + 1)}%`,
                background: `linear-gradient(90deg, transparent 0%, rgba(6,182,212,${0.15 + (i * 0.02)}) 20%, rgba(6,182,212,${0.3 + (i * 0.02)}) 50%, rgba(6,182,212,${0.15 + (i * 0.02)}) 80%, transparent 100%)`,
                transform: `perspective(400px) rotateX(${45 - i * 2}deg)`,
                transformOrigin: 'center bottom'
              }}
              animate={{
                opacity: [0.3, 0.7, 0.3],
                scaleX: [0.9, 1.1, 0.9]
              }}
              transition={{
                duration: 4 + (i * 0.2),
                delay: i * 0.1,
                repeat: Infinity,
                ease: "easeInOut"
              }}
            />
          ))}
          
          {/* Vertical Energy Beams */}
          {[25, 50, 75].map((pos, i) => (
            <motion.div
              key={`beam-${i}`}
              className="absolute w-px h-full"
              style={{
                left: `${pos}%`,
                background: 'linear-gradient(0deg, transparent 0%, rgba(6,182,212,0.4) 30%, rgba(16,185,129,0.6) 50%, rgba(6,182,212,0.4) 70%, transparent 100%)',
                filter: 'blur(0.5px)'
              }}
              animate={{
                opacity: [0.4, 0.8, 0.4],
                scaleY: [0.8, 1.2, 0.8]
              }}
              transition={{
                duration: 3,
                delay: i * 0.5,
                repeat: Infinity,
                ease: "easeInOut"
              }}
            />
          ))}
        </div>

        {/* Market Sector Background Zones */}
        {marketSectors.map((sector, index) => (
          <motion.div
            key={sector.id}
            className="absolute border-2 border-dashed rounded-lg"
            style={{
              left: `${sector.x}%`,
              top: `${sector.y}%`,
              width: `${sector.width}%`,
              height: `${sector.height}%`,
              borderColor: sector.trend === 'rising' ? 'rgba(16,185,129,0.4)' : 
                          sector.trend === 'stable' ? 'rgba(6,182,212,0.3)' : 
                          'rgba(239,68,68,0.3)',
              backgroundColor: sector.trend === 'rising' ? 'rgba(16,185,129,0.1)' : 
                              sector.trend === 'stable' ? 'rgba(6,182,212,0.05)' : 
                              'rgba(239,68,68,0.05)'
            }}
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: index * 0.3, duration: 1 }}
          >
            {/* Sector Label */}
            <div className="absolute -top-6 left-0 text-xs font-medium text-cyan-300 bg-black/60 px-2 py-1 rounded border border-cyan-400/30">
              {sector.name}
            </div>
            
            {/* Sector Stats */}
            <div className="absolute bottom-1 left-1 text-xs text-gray-300 bg-black/80 px-1 py-0.5 rounded">
              <div>{sector.itemCount} items</div>
              <div className={`${
                sector.averageProfit > 500 ? 'text-green-400' : 
                sector.averageProfit > 0 ? 'text-yellow-400' : 
                'text-red-400'
              }`}>
                {sector.averageProfit > 0 ? '+' : ''}{sector.averageProfit} GP avg
              </div>
            </div>
            
            {/* Trend Indicator */}
            <div className="absolute top-1 right-1">
              {sector.trend === 'rising' && <TrendingUp className="w-4 h-4 text-green-400" />}
              {sector.trend === 'stable' && <Activity className="w-4 h-4 text-cyan-400" />}
              {sector.trend === 'declining' && <TrendingDown className="w-4 h-4 text-red-400" />}
            </div>
          </motion.div>
        ))}

        {/* Advanced Holographic Heat Zones */}
        {heatZones.map((zone, index) => (
          <motion.div
            key={zone.id}
            className="absolute transform -translate-x-1/2 -translate-y-1/2"
            style={{
              left: `${zone.x}%`,
              top: `${zone.y}%`,
            }}
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ 
              opacity: 1,
              scale: 1
            }}
            transition={{
              duration: 1.5,
              delay: index * 0.3,
              ease: "easeOut"
            }}
            whileHover={{
              scale: 1.1,
              transition: { duration: 0.2 }
            }}
          >
            {/* Multi-layered Heat Signature */}
            <div className="relative">
              {/* Outer Energy Ring - Smaller and less overlapping */}
              <div
                className="absolute inset-0 w-16 h-16 rounded-full"
                style={{
                  background: `radial-gradient(circle, ${getZoneColor(zone)} 0%, transparent 60%)`,
                  filter: 'blur(1px)',
                  transform: 'scale(1.1)'
                }}
              />
              
              {/* Main Heat Core - Smaller for better spacing */}
              <div
                className="w-14 h-14 rounded-full relative overflow-hidden border-2 border-white/30"
                style={{
                  backgroundColor: getZoneColor(zone).replace(')', ', 0.8)').replace('rgba', 'rgba'),
                  boxShadow: `0 0 25px ${getZoneColor(zone)}, inset 0 0 15px rgba(255,255,255,0.1)`,
                  backdropFilter: 'blur(2px)'
                }}
              >
                {/* Inner Holographic Effect */}
                <div className="absolute inset-0 bg-gradient-to-br from-white/20 via-transparent to-transparent rounded-full" />
                
                {/* Zone Type Indicator */}
                <div className="absolute inset-0 flex items-center justify-center">
                  <motion.div
                    animate={{ rotate: 360 }}
                    transition={{ duration: 4, repeat: Infinity, ease: "linear" }}
                  >
                    {getZoneIcon(zone)}
                  </motion.div>
                </div>
                
                {/* Data Stream Particles */}
                {zone.type === 'hot' && [...Array(3)].map((_, i) => (
                  <motion.div
                    key={i}
                    className="absolute w-1 h-1 bg-emerald-400 rounded-full"
                    style={{
                      left: '50%',
                      top: '50%',
                    }}
                    animate={{
                      x: [0, Math.cos(i * 2) * 20, 0],
                      y: [0, Math.sin(i * 2) * 20, 0],
                      opacity: [0, 1, 0]
                    }}
                    transition={{
                      duration: 2,
                      delay: i * 0.3,
                      repeat: Infinity,
                      ease: "easeInOut"
                    }}
                  />
                ))}
              </div>
              
              {/* Enhanced Value Display - Positioned to avoid overlap */}
              <motion.div
                className="absolute -top-20 left-1/2 transform -translate-x-1/2"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 + index * 0.1 }}
                style={{
                  zIndex: 10 + index // Ensure tooltips don't overlap
                }}
              >
                <div className="bg-black/95 backdrop-blur-md border border-cyan-400/60 rounded-lg px-4 py-3 text-sm shadow-2xl min-w-[180px]">
                  {/* Item Name - Larger Font */}
                  {zone.itemName && (
                    <div className="text-white font-semibold mb-2 text-base text-center">
                      {zone.itemName}
                    </div>
                  )}
                  
                  {/* Profit Information - Larger and Clearer */}
                  <div className="flex items-center justify-center space-x-2 mb-2">
                    <div className={`w-2 h-2 rounded-full ${
                      zone.type === 'hot' ? 'bg-red-400' :
                      zone.type === 'warm' ? 'bg-orange-400' :
                      zone.type === 'volatile' ? 'bg-yellow-400' :
                      'bg-blue-400'
                    }`} />
                    <span className={`font-mono font-bold text-base ${
                      zone.profit && zone.profit > 500 ? 'text-green-400' :
                      zone.profit && zone.profit > 0 ? 'text-yellow-400' :
                      'text-red-400'
                    }`}>
                      {zone.profit !== undefined ? 
                        (zone.profit > 0 ? `+${zone.profit.toLocaleString()} GP` : `${zone.profit.toLocaleString()} GP`) :
                        `${formatValue(zone.value)} GP`
                      }
                    </span>
                  </div>
                  
                  {/* Volume Information - More Readable */}
                  {zone.volume && (
                    <div className="text-cyan-300 text-sm text-center font-medium">
                      Volume: {zone.volume}/hour
                    </div>
                  )}
                </div>
              </motion.div>
              
              {/* Connection Lines to nearby zones */}
              {zone.type === 'hot' && heatZones.some(otherZone => 
                otherZone.id !== zone.id && 
                otherZone.type === 'hot' &&
                Math.abs(otherZone.x - zone.x) < 30 &&
                Math.abs(otherZone.y - zone.y) < 30
              ) && (
                <svg className="absolute inset-0 w-24 h-24 pointer-events-none" style={{ transform: 'translate(-50%, -50%)' }}>
                  <motion.path
                    d="M 12 12 Q 18 6 24 12"
                    stroke="rgba(16,185,129,0.4)"
                    strokeWidth="1"
                    fill="none"
                    strokeDasharray="2,2"
                    animate={{ strokeDashoffset: [0, 4] }}
                    transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                  />
                </svg>
              )}
            </div>
          </motion.div>
        ))}

        {/* Advanced Scanning System */}
        <motion.div
          className="absolute w-full h-1 opacity-90 pointer-events-none"
          style={{
            top: `${scanLine}%`,
            background: 'linear-gradient(90deg, transparent 0%, rgba(6,182,212,0.4) 20%, rgba(16,185,129,0.8) 50%, rgba(6,182,212,0.4) 80%, transparent 100%)',
            filter: 'blur(1px)',
            boxShadow: '0 0 15px rgba(6, 182, 212, 0.8), 0 0 30px rgba(16, 185, 129, 0.4)'
          }}
        />
        
        {/* Scanning Particles */}
        <motion.div
          className="absolute w-2 h-2 bg-cyan-400 rounded-full pointer-events-none"
          style={{
            top: `${scanLine}%`,
            left: '10%',
            filter: 'blur(0.5px)',
            boxShadow: '0 0 8px rgba(6, 182, 212, 0.8)'
          }}
          animate={{
            x: ['0%', '800%', '0%'],
            opacity: [0, 1, 0]
          }}
          transition={{
            duration: 2,
            repeat: Infinity,
            ease: "easeInOut"
          }}
        />

        {/* Enhanced Scanning Overlay with Data Trails */}
        <div
          className="absolute inset-0 pointer-events-none"
          style={{
            height: `${scanLine}%`,
            background: 'linear-gradient(180deg, rgba(6,182,212,0.08) 0%, rgba(16,185,129,0.04) 50%, rgba(6,182,212,0.02) 100%)',
            transition: 'height 0.1s ease-out',
            backdropFilter: 'brightness(1.1) saturate(1.2)'
          }}
        />
        
        {/* Holographic Interference Pattern */}
        <div className="absolute inset-0 pointer-events-none opacity-30">
          {[...Array(6)].map((_, i) => (
            <motion.div
              key={`interference-${i}`}
              className="absolute w-full h-px"
              style={{
                top: `${(scanLine + i * 15) % 100}%`,
                background: 'linear-gradient(90deg, transparent 0%, rgba(6,182,212,0.2) 50%, transparent 100%)'
              }}
              animate={{
                opacity: [0.1, 0.4, 0.1],
                scaleX: [0.8, 1.2, 0.8]
              }}
              transition={{
                duration: 1.5,
                delay: i * 0.1,
                repeat: Infinity,
                ease: "easeInOut"
              }}
            />
          ))}
        </div>
      </div>

      {/* Static Information Panel */}
      <div className="bg-black/80 border-t border-cyan-400/20 p-4">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Top Opportunities Panel - Shows all profitable items, not just heat zones */}
          <div className="space-y-3">
            <h4 className="text-sm font-semibold text-cyan-300 mb-2">Top Profit Opportunities</h4>
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {[
                ...realMarketData.weapons,
                ...realMarketData.armor,
                ...realMarketData.runes,
                ...realMarketData.potions,
                ...realMarketData.resources
              ]
                .filter(item => (item.current_profit || 0) > 100)
                .sort((a, b) => (b.current_profit || 0) - (a.current_profit || 0))
                .slice(0, 8)
                .map((item, index) => (
                  <div key={item.item_id} className="flex items-center justify-between bg-black/40 rounded-lg px-3 py-2 border border-red-400/20">
                    <div className="flex items-center space-x-2">
                      <div className={`w-2 h-2 rounded-full ${
                        (item.current_profit || 0) > 500 ? 'bg-red-400' :
                        (item.current_profit || 0) > 200 ? 'bg-orange-400' :
                        'bg-yellow-400'
                      }`} />
                      <span className="text-white text-sm font-medium truncate max-w-[140px]" title={item.name}>
                        {item.name}
                      </span>
                    </div>
                    <div className="text-green-400 text-sm font-bold">
                      +{(item.current_profit || 0).toLocaleString()} GP
                    </div>
                  </div>
                ))
              }
              {[
                ...realMarketData.weapons,
                ...realMarketData.armor,
                ...realMarketData.runes,
                ...realMarketData.potions,
                ...realMarketData.resources
              ].filter(item => (item.current_profit || 0) > 100).length === 0 && (
                <div className="text-gray-400 text-sm text-center py-4">
                  Loading profitable items...
                </div>
              )}
            </div>
          </div>
          
          {/* Market Sectors Overview */}
          <div className="space-y-3">
            <h4 className="text-sm font-semibold text-cyan-300 mb-2">Market Sectors Status</h4>
            <div className="space-y-2">
              {marketSectors
                .sort((a, b) => b.averageProfit - a.averageProfit)
                .slice(0, 3)
                .map((sector, index) => (
                  <div key={sector.id} className="flex items-center justify-between bg-black/40 rounded-lg px-3 py-2 border border-cyan-400/20">
                    <div className="flex items-center space-x-2">
                      {sector.trend === 'rising' && <TrendingUp className="w-3 h-3 text-green-400" />}
                      {sector.trend === 'stable' && <Activity className="w-3 h-3 text-cyan-400" />}
                      {sector.trend === 'declining' && <TrendingDown className="w-3 h-3 text-red-400" />}
                      <span className="text-white text-sm font-medium">
                        {sector.name}
                      </span>
                    </div>
                    <div className="text-right">
                      <div className={`text-sm font-bold ${
                        sector.averageProfit > 500 ? 'text-green-400' :
                        sector.averageProfit > 0 ? 'text-yellow-400' :
                        'text-red-400'
                      }`}>
                        {sector.averageProfit > 0 ? '+' : ''}{sector.averageProfit} GP
                      </div>
                      <div className="text-xs text-gray-400">
                        {sector.itemCount} items
                      </div>
                    </div>
                  </div>
                ))
              }
            </div>
          </div>
        </div>
        
        {/* Summary Statistics */}
        <div className="flex items-center justify-between mt-4 pt-3 border-t border-cyan-400/10 text-xs">
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-1">
              <div className="w-2 h-2 bg-red-400 rounded-full" />
              <span className="text-red-300">High Profit ({heatZones.filter(z => z.type === 'hot').length})</span>
            </div>
            <div className="flex items-center space-x-1">
              <div className="w-2 h-2 bg-orange-400 rounded-full" />
              <span className="text-orange-300">Med Profit ({heatZones.filter(z => z.type === 'warm').length})</span>
            </div>
            <div className="flex items-center space-x-1">
              <div className="w-2 h-2 bg-blue-400 rounded-full" />
              <span className="text-blue-300">Low Profit ({heatZones.filter(z => z.type === 'cold').length})</span>
            </div>
            <div className="flex items-center space-x-1">
              <div className="w-2 h-2 bg-green-400 rounded-full" />
              <span className="text-green-300">{marketSectors.filter(s => s.trend === 'rising').length} Rising Sectors</span>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <div className="text-cyan-300 font-mono">
              {heatZones.length} opportunities • {marketSectors.length} sectors
            </div>
            {!dataLoading && !dataError && (
              <div className="flex items-center space-x-1">
                <div className="w-1.5 h-1.5 bg-green-400 rounded-full animate-pulse" />
                <span className="text-xs text-green-300">Live Data</span>
              </div>
            )}
            {dataError && (
              <div className="flex items-center space-x-1" title={dataError}>
                <div className="w-1.5 h-1.5 bg-orange-400 rounded-full animate-pulse" />
                <span className="text-xs text-orange-300">Cached Data</span>
              </div>
            )}
            {dataLoading && (
              <div className="flex items-center space-x-1">
                <div className="w-1.5 h-1.5 bg-yellow-400 rounded-full animate-pulse" />
                <span className="text-xs text-yellow-300">Loading...</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};