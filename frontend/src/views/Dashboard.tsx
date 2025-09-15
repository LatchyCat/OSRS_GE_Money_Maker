import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { RefreshCw, Plus, TrendingUp, Package } from 'lucide-react';
import { itemsApi } from '../api/itemsApi';
import { planningApi } from '../api/planningApi';
import { systemApi } from '../api/systemApi';
import { MarketStats } from '../components/features/MarketStats';
import { ItemCard } from '../components/features/ItemCard';
import { AIRecommendationCard } from '../components/ai/AIRecommendationCard';
import { CSSParticleBackground } from '../components/effects/CSSParticleBackground';
import { HolographicItemCard } from '../components/effects/HolographicItemCard';
import { FuturisticGrid } from '../components/effects/FuturisticGrid';
import { HolographicLoader } from '../components/effects/HolographicLoader';
import { DashboardHeader } from '../components/dashboard/DashboardHeader';
import { AgentPerformanceSection } from '../components/dashboard/AgentPerformanceSection';
import { AIRecommendationsSection } from '../components/dashboard/AIRecommendationsSection';
import { TopProfitableItemsSection } from '../components/dashboard/TopProfitableItemsSection';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import type { Item, MarketAnalysis, GoalPlanStats } from '../types';

export const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const [topItems, setTopItems] = useState<Item[]>([]);
  const [marketAnalysis, setMarketAnalysis] = useState<MarketAnalysis | null>(null);
  const [goalPlanStats, setGoalPlanStats] = useState<GoalPlanStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  
  // Individual loading and error states
  const [itemsLoading, setItemsLoading] = useState(false);
  const [marketLoading, setMarketLoading] = useState(false);
  const [statsLoading, setStatsLoading] = useState(false);
  const [itemsError, setItemsError] = useState<string | null>(null);
  const [marketError, setMarketError] = useState<string | null>(null);
  const [statsError, setStatsError] = useState<string | null>(null);
  
  // Request deduplication
  const [activeRequests, setActiveRequests] = useState(new Set<string>());

  // Calculate particle system parameters based on portfolio performance
  const calculateProfitLevel = (): number => {
    if (topItems.length === 0) return 0.5;
    const avgProfit = topItems.reduce((sum, item) => sum + (item.current_profit || 0), 0) / topItems.length;
    // Normalize to 0-1 scale (assuming 50K GP as high profit)
    return Math.min(Math.max(avgProfit / 50000, 0), 1);
  };

  const calculateParticleIntensity = (): number => {
    let intensity = 0.3; // Base intensity
    if (topItems.length > 0) intensity += topItems.length / 20; // More items = more particles
    if (marketAnalysis) intensity += 0.2; // Market data loaded
    if (goalPlanStats) intensity += 0.1; // Planning data loaded
    return Math.min(intensity, 1);
  };

  const fetchDashboardData = async (showRefreshSpinner = false) => {
    if (showRefreshSpinner) setRefreshing(true);
    
    // Reset error states
    setItemsError(null);
    setMarketError(null);
    setStatsError(null);
    
    console.log('🔄 Fetching fresh dashboard data...');
    
    // Fetch items first (priority data) with deduplication
    if (!activeRequests.has('items')) {
      setActiveRequests(prev => new Set(prev).add('items'));
      setItemsLoading(true);
      try {
        const itemsResult = await itemsApi.getItems({ ordering: '-current_profit', page: 1, page_size: 20 });
        const topItemsData = itemsResult.results.slice(0, 8);
        console.log('📊 Top items fetched:', topItemsData.map(item => 
          `${item.name}: ${item.current_profit}GP [${item.data_source}]`
        ));
        setTopItems(topItemsData);
      } catch (error) {
        console.error('Error fetching items:', error);
        setItemsError('Failed to load items data. Please try refreshing.');
      } finally {
        setItemsLoading(false);
        setActiveRequests(prev => {
          const next = new Set(prev);
          next.delete('items');
          return next;
        });
      }
    }
    
    // Fetch planning data in background (less critical)
    const fetchPlanningData = async () => {
      // Market analysis with deduplication
      if (!activeRequests.has('market')) {
        setActiveRequests(prev => new Set(prev).add('market'));
        setMarketLoading(true);
        try {
          const marketResult = await planningApi.getMarketAnalysis();
          setMarketAnalysis(marketResult);
          console.log('📈 Market analysis loaded');
        } catch (error) {
          console.error('Error fetching market analysis:', error);
          setMarketError('Market analysis temporarily unavailable');
        } finally {
          setMarketLoading(false);
          setActiveRequests(prev => {
            const next = new Set(prev);
            next.delete('market');
            return next;
          });
        }
      }
      
      // Goal plan stats with deduplication
      if (!activeRequests.has('stats')) {
        setActiveRequests(prev => new Set(prev).add('stats'));
        setStatsLoading(true);
        try {
          const statsResult = await planningApi.getGoalPlanStats();
          setGoalPlanStats(statsResult);
          console.log('📋 Goal plan stats loaded');
        } catch (error) {
          console.error('Error fetching goal plan stats:', error);
          setStatsError('Planning statistics temporarily unavailable');
        } finally {
          setStatsLoading(false);
          setActiveRequests(prev => {
            const next = new Set(prev);
            next.delete('stats');
            return next;
          });
        }
      }
    };
    
    // Run planning data fetch in background
    fetchPlanningData();
    
    setLoading(false);
    setRefreshing(false);
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const handleRefresh = async () => {
    console.log('🔄 Force refreshing dashboard with latest data...');
    
    // Clear existing state first
    setTopItems([]);
    setMarketAnalysis(null);
    setGoalPlanStats(null);
    
    // Fetch completely fresh data
    await fetchDashboardData(true);
    
    console.log('✅ Dashboard refresh completed');
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-black via-gray-900 to-black">
        <div className="relative">
          <FuturisticGrid className="absolute inset-0" opacity={0.2} />
          <CSSParticleBackground 
            profitLevel={0.3}
            intensity={0.2}
            className="absolute inset-0 pointer-events-none"
          />
          <div className="relative z-10">
            <HolographicLoader 
              size="lg" 
              text="Initializing Holographic Trading Interface..." 
              variant="system"
            />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="relative">
      {/* Interactive Particle Background */}
      <CSSParticleBackground 
        profitLevel={calculateProfitLevel()}
        intensity={calculateParticleIntensity()}
        className="fixed inset-0 pointer-events-none z-0"
      />
      
      {/* Futuristic Grid Overlay */}
      <FuturisticGrid className="z-5" opacity={0.15} />
      
      {/* Main Dashboard Content */}
      <div className="relative z-10 space-y-8">
      {/* Dashboard Header */}
      <DashboardHeader 
        onRefresh={handleRefresh}
        refreshing={refreshing}
      />



      {/* Multi-Agent Performance Status */}
      <AgentPerformanceSection />

      {/* Money-Making Strategy Hub */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
      >
        <Card className="space-y-6">
          <div className="text-center">
            <h2 className="text-2xl font-bold text-white mb-2">Money-Making Strategies</h2>
            <p className="text-gray-400">Choose your preferred method to maximize OSRS profits</p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <Button
              variant="primary"
              onClick={() => navigate('/high-alchemy')}
              className="h-24 flex-col space-y-2 bg-gradient-to-br from-yellow-500/10 to-yellow-600/20 border-yellow-500/30 hover:from-yellow-500/20 hover:to-yellow-600/30"
            >
              <div className="text-2xl">⚡</div>
              <div>
                <div className="font-semibold">High Alchemy</div>
                <div className="text-xs text-gray-400">Magic XP + GP</div>
              </div>
            </Button>
            
            <Button
              variant="primary"
              onClick={() => navigate('/decanting')}
              className="h-24 flex-col space-y-2 bg-gradient-to-br from-blue-500/10 to-blue-600/20 border-blue-500/30 hover:from-blue-500/20 hover:to-blue-600/30"
            >
              <div className="text-2xl">🧪</div>
              <div>
                <div className="font-semibold">Decanting</div>
                <div className="text-xs text-gray-400">Potion Profits</div>
              </div>
            </Button>
            
            <Button
              variant="primary"
              onClick={() => navigate('/flipping')}
              className="h-24 flex-col space-y-2 bg-gradient-to-br from-purple-500/10 to-purple-600/20 border-purple-500/30 hover:from-purple-500/20 hover:to-purple-600/30"
            >
              <div className="text-2xl">📈</div>
              <div>
                <div className="font-semibold">Item Flipping</div>
                <div className="text-xs text-gray-400">Buy Low, Sell High</div>
              </div>
            </Button>
            
            <Button
              variant="primary"
              onClick={() => navigate('/magic-runes')}
              className="h-24 flex-col space-y-2 bg-gradient-to-br from-indigo-500/10 to-indigo-600/20 border-indigo-500/30 hover:from-indigo-500/20 hover:to-indigo-600/30"
            >
              <div className="text-2xl">🔮</div>
              <div>
                <div className="font-semibold">Magic & Runes</div>
                <div className="text-xs text-gray-400">Spellcasting Profits</div>
              </div>
            </Button>
            
            <Button
              variant="primary"
              onClick={() => navigate('/crafting')}
              className="h-24 flex-col space-y-2 bg-gradient-to-br from-orange-500/10 to-orange-600/20 border-orange-500/30 hover:from-orange-500/20 hover:to-orange-600/30"
            >
              <div className="text-2xl">🔨</div>
              <div>
                <div className="font-semibold">Crafting</div>
                <div className="text-xs text-gray-400">Skill & Profit</div>
              </div>
            </Button>
            
            <Button
              variant="primary"
              onClick={() => navigate('/set-combining')}
              className="h-24 flex-col space-y-2 bg-gradient-to-br from-green-500/10 to-green-600/20 border-green-500/30 hover:from-green-500/20 hover:to-green-600/30"
            >
              <div className="text-2xl">🛡️</div>
              <div>
                <div className="font-semibold">Set Combining</div>
                <div className="text-xs text-gray-400">Equipment Sets</div>
              </div>
            </Button>
          </div>
        </Card>
      </motion.div>

      {/* AI Trading Recommendations */}
      <AIRecommendationsSection />

      {/* Top Profitable Items - Simplified */}
      <TopProfitableItemsSection 
        items={topItems.slice(0, 6)}
        loading={itemsLoading}
        error={itemsError}
        onRetry={handleRefresh}
        itemsPerPage={6}
      />

      {/* Getting Started */}
      <Card className="text-center py-8">
        <div className="space-y-4">
          <div className="w-12 h-12 bg-accent-500/20 rounded-full flex items-center justify-center mx-auto">
            <TrendingUp className="w-6 h-6 text-accent-500" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white">Goal Planning</h3>
            <p className="text-gray-400 mt-2 text-sm">
              Set wealth targets and get personalized strategies
            </p>
          </div>
          <Button 
            variant="primary"
            onClick={() => navigate('/planning/create')}
            icon={<Plus className="w-4 h-4" />}
            size="sm"
          >
            Create Goal Plan
          </Button>
        </div>
      </Card>
    </div>
    </div>
  );
};