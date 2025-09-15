# OSRS Trading Views Architecture Documentation
## Comprehensive Breadcrumb Guide for High Alchemy & Decanting Views

*Last Updated: 2025-01-12*

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [View Architecture Patterns](#view-architecture-patterns)
3. [Core Feature Implementations](#core-feature-implementations)
4. [Component Integration Patterns](#component-integration-patterns)
5. [State Management Strategies](#state-management-strategies)
6. [API Integration Patterns](#api-integration-patterns)
7. [Real-time Intelligence System](#real-time-intelligence-system)
8. [AI Assistant Integration](#ai-assistant-integration)
9. [Advanced Filtering & Search](#advanced-filtering--search)
10. [Professional Trading Components](#professional-trading-components)
11. [Performance Optimizations](#performance-optimizations)
12. [Implementation Templates](#implementation-templates)

---

## Overview

This document provides a comprehensive analysis of the sophisticated High Alchemy and Decanting trading views, serving as a blueprint for implementing similar advanced trading features across other routes (flipping, crafting, set combining, etc.).

**Key Views Analyzed:**
- `HighAlchemyView.tsx` - 762 lines of advanced trading functionality
- `DecantingView.tsx` - 1208 lines of comprehensive trading features

---

## View Architecture Patterns

### 1. **Core View Structure**

```typescript
export function TradingView() {
  // 1. Core Data State
  const [items, setItems] = useState<Item[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // 2. UI State Management
  const [searchTerm, setSearchTerm] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [selectedItemForChart, setSelectedItemForChart] = useState<number | null>(null);
  
  // 3. Modal State Management
  const [selectedOpportunityForCalculator, setSelectedOpportunityForCalculator] = useState<Item | null>(null);
  const [selectedOpportunityForQuickTrade, setSelectedOpportunityForQuickTrade] = useState<Item | null>(null);
  const [showAIAssistant, setShowAIAssistant] = useState(false);

  // 4. Professional Trading State
  const [currentCapital, setCurrentCapital] = useState(1000000); // Default 1M GP
  const [favorites, setFavorites] = useState<Set<number>>(new Set());
  const [natureRunePrice, setNatureRunePrice] = useState(180); // For high alchemy
  
  // 5. Real-time Intelligence
  const { state: socketState, actions: socketActions } = useReactiveTradingContext();
  
  // 6. Statistics State
  const [stats, setStats] = useState({
    totalOpportunities: 0,
    avgProfit: 0,
    topValue: 0,
    totalEfficiency: 0
  });

  // ... rest of component
}
```

### 2. **Filter State Architecture**

```typescript
// Complex filter state for professional trading
const [filters, setFilters] = useState<TradingFilters>({
  search: '',
  minProfit: 0,
  sortBy: 'profit' | 'efficiency' | 'margin' | 'volume',
  riskLevel: 'all' | 'low' | 'medium' | 'high',
  minMargin: '',
  maxMargin: '',
  minGpPerHour: '',
  maxGpPerHour: '',
  volumeFilter: 'all' | 'high' | 'medium' | 'low',
  profitabilityOnly: true,
  highValueOnly: false,
  minCapital: '',
  maxCapital: '',
  ordering: 'profit_desc',
  onlyProfitable: true, // Tax-aware filtering
  hideTaxNegative: true
});
```

---

## Core Feature Implementations

### 1. **Data Fetching Strategy**

```typescript
const fetchTradingData = async (showRefreshSpinner = false) => {
  if (showRefreshSpinner) setRefreshing(true);
  setLoading(true);

  try {
    // Build dynamic filter parameters
    const filterParams: any = {
      ordering: '-profit_calc__viability_score',
      page_size: 50,
      min_profit: filters.minProfit,
      search: filters.search || undefined,
      is_active: true
    };

    // Fetch from appropriate API endpoint
    const response = await apiClient.getOpportunities(filterParams);
    
    // Apply client-side business logic filtering
    const filteredItems = response.results.filter(item => {
      // Business-specific filtering logic
      return applyBusinessLogic(item);
    });

    // Sort based on selected criteria
    const sortedItems = applySorting(filteredItems, filters.sortBy);
    
    setItems(sortedItems);
    calculateStats(sortedItems);
    
  } catch (error) {
    console.error('Error fetching trading data:', error);
    setItems([]);
  } finally {
    setLoading(false);
    setRefreshing(false);
  }
};
```

### 2. **Real-time Data Integration**

```typescript
// WebSocket integration for live market data
useEffect(() => {
  if (socketState?.isConnected) {
    // Subscribe to route-specific updates
    socketActions.subscribeToRoute('high-alchemy');
    socketActions.getCurrentRecommendations('high-alchemy');
    socketActions.getMarketAlerts();
  }
}, [socketState?.isConnected]);

// Handle real-time price updates
useEffect(() => {
  const priceUpdates = Object.values(socketState?.priceUpdates || {});
  if (priceUpdates.length > 0) {
    setItems(prevItems => {
      const updatedItems = [...prevItems];
      
      priceUpdates.forEach((priceUpdate: any) => {
        const itemIndex = updatedItems.findIndex(item => item.item_id === priceUpdate.item_id);
        if (itemIndex !== -1) {
          const currentPrice = (priceUpdate.high_price + priceUpdate.low_price) / 2;
          const oldPrice = updatedItems[itemIndex].current_buy_price || 0;
          const priceChangePercent = Math.abs((currentPrice - oldPrice) / oldPrice * 100);
          
          // Update price if significant change (>1%)
          if (priceChangePercent > 1 || oldPrice === 0) {
            updatedItems[itemIndex] = {
              ...updatedItems[itemIndex],
              current_buy_price: priceUpdate.low_price,
              last_updated: priceUpdate.timestamp
            };
          }
        }
      });
      
      return updatedItems;
    });
  }
}, [socketState?.priceUpdates]);
```

---

## Component Integration Patterns

### 1. **Opportunity Card Integration**

```typescript
// Pattern for integrating specialized trading cards
{items.map((item) => {
  // Real-time data enhancement
  const realtimeItemData = socketState?.marketData?.find(
    (data: any) => data.item_id === item.item_id
  );
  
  // AI insights integration
  const aiInsights = socketState?.aiAnalysis?.find(
    (analysis: any) => analysis.item_id === item.item_id
  );

  return (
    <TradingOpportunityCard
      key={item.item_id}
      item={{
        ...item,
        // Calculated fields
        profit_per_action: calculateProfit(item),
        is_favorite: favorites.has(item.item_id || 0),
        real_time_data: realtimeItemData,
        ai_insights: aiInsights
      }}
      onClick={() => handleItemClick(item)}
      onToggleFavorite={() => toggleFavorite(item.item_id)}
      onQuickTrade={() => setSelectedOpportunityForQuickTrade(item)}
      onOpenCalculator={() => setSelectedItemForCalculator(item)}
      onOpenChart={() => setSelectedItemForChart(item)}
    />
  );
})}
```

### 2. **Modal System Architecture**

```typescript
// Coordinated modal system
{/* Profit Calculator Modal */}
{selectedItemForCalculator && (
  <ProfitCalculator
    item={enhanceItemData(selectedItemForCalculator)}
    onClose={() => setSelectedItemForCalculator(null)}
    onStartTrading={(item, capital) => {
      setSelectedOpportunityForQuickTrade(item);
      setCurrentCapital(capital);
      setSelectedItemForCalculator(null);
    }}
    onSaveStrategy={(item, calculations) => {
      console.log('Strategy saved:', item.name, calculations);
    }}
    currentCapital={currentCapital}
  />
)}

{/* Quick Trade Modal */}
{selectedOpportunityForQuickTrade && (
  <QuickTradeModal
    isOpen={!!selectedOpportunityForQuickTrade}
    onClose={() => setSelectedOpportunityForQuickTrade(null)}
    opportunity={transformToTradingOpportunity(selectedOpportunityForQuickTrade)}
    currentCapital={currentCapital}
    onTradeComplete={(tradeResult) => {
      setCurrentCapital(prev => Math.max(0, prev + tradeResult.profit));
    }}
  />
)}

{/* AI Assistant Modal */}
{showAIAssistant && (
  <AITradingAssistant
    isOpen={showAIAssistant}
    onClose={() => setShowAIAssistant(false)}
    items={items}
    currentCapital={currentCapital}
  />
)}
```

---

## State Management Strategies

### 1. **Filter State Management**

```typescript
// Centralized filter handling
const handleFilterChange = (key: string, value: any) => {
  setFilters(prev => ({ ...prev, [key]: value }));
};

const clearFilters = () => {
  setFilters({
    // Reset to default state
    search: '',
    minProfit: 0,
    sortBy: 'profit',
    // ... other defaults
  });
};

// Apply filters with business logic
const getFilteredAndSortedItems = () => {
  let filtered = [...items];
  
  // Apply tax-aware filtering (for decanting)
  if (filters.onlyProfitable) {
    filtered = filtered.filter(item => {
      const taxResult = calculateTaxAdjustedProfit(item);
      return taxResult.isProfit;
    });
  }
  
  // Apply sorting with business logic
  return filtered.sort((a, b) => {
    switch (filters.sortBy) {
      case 'profit':
        return calculateProfit(b) - calculateProfit(a);
      case 'efficiency':
        return calculateEfficiency(b) - calculateEfficiency(a);
      default:
        return 0;
    }
  });
};
```

### 2. **Statistics Calculation**

```typescript
// Real-time statistics calculation
useEffect(() => {
  const visibleItems = getFilteredAndSortedItems();
  if (visibleItems.length > 0) {
    setStats({
      totalOpportunities: visibleItems.length,
      avgProfit: visibleItems.reduce((sum, item) => sum + calculateProfit(item), 0) / visibleItems.length,
      topValue: Math.max(...visibleItems.map(item => getItemValue(item))),
      totalEfficiency: calculateTotalEfficiency(visibleItems)
    });
  } else {
    setStats({ totalOpportunities: 0, avgProfit: 0, topValue: 0, totalEfficiency: 0 });
  }
}, [items, filters]);
```

---

## API Integration Patterns

### 1. **API Client Structure**

```typescript
// Pattern for API integration
import { itemsApi } from '../api/itemsApi';
import { tradingStrategiesApiClient } from '../api/tradingStrategiesApi';

// High Alchemy API calls
const response = await itemsApi.getItems({
  ordering: '-profit_calc__high_alch_viability_score',
  page_size: 50,
  min_profit: filters.minProfit,
  search: filters.search || undefined
});

// Decanting API calls
const response = await tradingStrategiesApiClient.decanting.getAIOpportunities({
  is_active: true,
  min_profit: filters.minProfit || 10,
  ordering: filters.ordering,
  // ... other filter params
});
```

### 2. **Error Handling Pattern**

```typescript
try {
  const response = await fetchTradingData();
  setItems(response.results);
} catch (error) {
  console.error('Error fetching data:', error);
  
  // Set error state for user feedback
  setWebsocketError(error instanceof Error ? error.message : 'Failed to fetch data');
  
  // Set safe empty state
  setItems([]);
  setStats({ totalOpportunities: 0, avgProfit: 0, topValue: 0, totalEfficiency: 0 });
} finally {
  setLoading(false);
}
```

---

## Real-time Intelligence System

### 1. **WebSocket Context Integration**

```typescript
// Context provider for centralized WebSocket management
export const ReactiveTradingProvider: React.FC = ({ children }) => {
  const tradingSocket = useReactiveTradingSocket();
  return (
    <ReactiveTradingContext.Provider value={tradingSocket}>
      {children}
    </ReactiveTradingContext.Provider>
  );
};

// Usage in views
const { state: socketState, actions: socketActions } = useReactiveTradingContext();
```

### 2. **Subscription Management**

```typescript
// Efficient item subscription management
useEffect(() => {
  if (socketState?.isConnected && items.length > 0) {
    const itemIds = items.map(item => item.item_id.toString());
    const uniqueItemIds = [...new Set(itemIds)];
    
    console.log(`Batch subscribing to ${uniqueItemIds.length} unique items`);
    
    // Subscribe to all visible items
    const timeoutId = setTimeout(() => {
      uniqueItemIds.forEach(itemId => {
        if (itemId) socketActions.subscribeToItem(itemId);
      });
    }, 200);
    
    // Cleanup subscriptions when items change
    return () => {
      clearTimeout(timeoutId);
      uniqueItemIds.forEach(itemId => {
        if (itemId) socketActions.unsubscribeFromItem(itemId);
      });
    };
  }
}, [socketState?.isConnected, JSON.stringify(items.map(i => i.item_id))]);
```

### 3. **Connection Status Handling**

```typescript
// WebSocket connection status display
{websocketError && (
  <motion.div className="bg-red-900/20 border border-red-500/30 rounded-xl p-4">
    <div className="flex items-center gap-3">
      <div className="w-3 h-3 rounded-full bg-red-500" />
      <div>
        <div className="text-red-400 font-medium">WebSocket Connection Issue</div>
        <div className="text-red-300 text-sm">{websocketError}</div>
        <div className="text-red-300/70 text-xs mt-1">
          Real-time updates may be unavailable. Data will refresh automatically when connection is restored.
        </div>
      </div>
    </div>
  </div>
)}

{socketState?.isConnected && !websocketError && (
  <motion.div className="bg-green-900/20 border border-green-500/30 rounded-xl p-4">
    <div className="flex items-center gap-3">
      <div className="w-3 h-3 rounded-full bg-green-500 animate-pulse" />
      <div>
        <div className="text-green-400 font-medium">Real-Time Intelligence Active</div>
        <div className="text-green-300 text-sm">
          Connected to live market data • Last connected: {lastConnectionAttempt?.toLocaleTimeString()}
        </div>
      </div>
    </div>
  </div>
)}
```

---

## AI Assistant Integration

### 1. **AI Chat Component Integration**

```typescript
// High Alchemy AI Assistant
{showAIAssistant && (
  <AIHighAlchemyAssistant
    isOpen={showAIAssistant}
    onClose={() => setShowAIAssistant(false)}
    items={items}
    currentCapital={currentCapital}
    natureRunePrice={natureRunePrice}
  />
)}

// Floating AI Assistant Button
<motion.button
  initial={{ scale: 0 }}
  animate={{ scale: 1 }}
  whileHover={{ scale: 1.1 }}
  whileTap={{ scale: 0.9 }}
  onClick={() => setShowAIAssistant(true)}
  className="fixed bottom-6 right-6 bg-gradient-to-r from-yellow-600 to-orange-600 hover:from-yellow-700 hover:to-orange-700 text-white p-4 rounded-full shadow-2xl border border-yellow-500/30 transition-all duration-200 z-40"
>
  <ChatBubbleLeftRightIcon className="w-6 h-6" />
  <div className="absolute -top-1 -right-1 w-3 h-3 bg-green-400 rounded-full animate-pulse" />
</motion.button>
```

### 2. **AI Assistant API Integration**

```typescript
// AI API call pattern from AIHighAlchemyAssistant.tsx
const callTradingAI = async (userMessage: string): Promise<Message> => {
  try {
    const response = await fetch('/api/high-alchemy-chat/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query: userMessage,
        natureRunePrice,
        items: items.map(item => ({
          id: item.item_id || 0,
          name: item.name || 'Unknown',
          current_buy_price: item.current_buy_price || 0,
          high_alch: item.high_alch || 0,
          limit: item.limit || 0,
          members: item.members || false,
          recommendation_score: item.recommendation_score || 0,
          daily_volume: item.daily_volume || 0
        }))
      })
    });

    const data = await response.json();
    
    if (data.success) {
      return {
        id: Date.now().toString(),
        role: 'assistant',
        content: data.response,
        timestamp: new Date(),
        type: 'analysis',
        metadata: data.metadata
      };
    } else {
      throw new Error(data.error || 'AI response failed');
    }
  } catch (error) {
    console.error('Trading AI Error:', error);
    // Return fallback response
    return createFallbackResponse();
  }
};
```

---

## Advanced Filtering & Search

### 1. **Multi-dimensional Filter UI**

```typescript
// Advanced filter panel with categorized options
{showFilters && (
  <motion.div
    initial={{ opacity: 0, height: 0 }}
    animate={{ opacity: 1, height: 'auto' }}
    exit={{ opacity: 0, height: 0 }}
    className="border-t border-gray-700/50 pt-4 space-y-4"
  >
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      
      {/* Category Filters */}
      <div className="space-y-2">
        <label className="text-sm font-medium text-blue-400">🧪 Category</label>
        <select
          value={filters.category}
          onChange={(e) => handleFilterChange('category', e.target.value)}
          className="w-full px-3 py-2 bg-gray-700/50 border border-gray-600/50 rounded-lg text-white text-sm focus:outline-none focus:ring-1 focus:ring-blue-500/50"
        >
          <option value="">All Categories</option>
          <option value="prayer">🙏 Prayer & Restore</option>
          <option value="combat">⚔️ Combat Potions</option>
          {/* ... more options */}
        </select>
      </div>

      {/* Profit Range Filter */}
      <div className="space-y-2">
        <label className="text-sm font-medium text-gray-300">Profit Range (GP)</label>
        <div className="flex gap-2">
          <input
            type="number"
            placeholder="Min"
            value={filters.minProfit}
            onChange={(e) => handleFilterChange('minProfit', e.target.value)}
            className="flex-1 px-3 py-2 bg-gray-700/50 border border-gray-600/50 rounded-lg text-white text-sm placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-blue-500/50"
          />
          <input
            type="number"
            placeholder="Max"
            value={filters.maxProfit}
            onChange={(e) => handleFilterChange('maxProfit', e.target.value)}
            className="flex-1 px-3 py-2 bg-gray-700/50 border border-gray-600/50 rounded-lg text-white text-sm placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-blue-500/50"
          />
        </div>
      </div>

      {/* Quick Filter Toggles */}
      <div className="space-y-2">
        <label className="text-sm font-medium text-green-400">🎯 Quick Filters</label>
        <div className="space-y-2">
          <label className="flex items-center space-x-2">
            <input
              type="checkbox"
              checked={filters.highValueOnly}
              onChange={(e) => handleFilterChange('highValueOnly', e.target.checked)}
              className="w-4 h-4 text-green-600 bg-gray-700 border-gray-600 rounded focus:ring-green-500 focus:ring-2"
            />
            <span className="text-sm text-green-400">💎 High Value (500+ GP)</span>
          </label>
          <label className="flex items-center space-x-2">
            <input
              type="checkbox"
              checked={filters.onlyProfitable}
              onChange={(e) => handleFilterChange('onlyProfitable', e.target.checked)}
              className="w-4 h-4 text-blue-600 bg-gray-700 border-gray-600 rounded focus:ring-blue-500 focus:ring-2"
            />
            <span className="text-sm text-blue-400">📈 Only Profitable</span>
          </label>
        </div>
      </div>
      
    </div>
  </motion.div>
)}
```

### 2. **Search Integration**

```typescript
// Real-time search with debouncing
const [searchInput, setSearchInput] = useState('');
const [searchTerm, setSearchTerm] = useState('');

// Debounced search application
useEffect(() => {
  const timeoutId = setTimeout(() => {
    setSearchTerm(searchInput);
  }, 300);
  
  return () => clearTimeout(timeoutId);
}, [searchInput]);

// Search UI component
<div className="relative flex-1 max-w-md">
  <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
  <input
    type="text"
    placeholder="Search items..."
    value={searchInput}
    onChange={(e) => setSearchInput(e.target.value)}
    className="w-full pl-10 pr-4 py-2 bg-gray-700/50 border border-gray-600/50 rounded-lg focus:outline-none focus:ring-2 focus:ring-yellow-500/50 focus:border-yellow-500/50 text-white placeholder-gray-400"
  />
</div>
```

---

## Professional Trading Components

### 1. **Stats Overview Cards**

```typescript
// Professional statistics display
<motion.div
  initial={{ opacity: 0, y: 20 }}
  animate={{ opacity: 1, y: 0 }}
  transition={{ delay: 0.1 }}
  className="grid grid-cols-2 md:grid-cols-4 gap-4"
>
  <div className="bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6 text-center">
    <div className="text-2xl font-bold text-yellow-400 mb-1">{stats.totalOpportunities}</div>
    <div className="text-sm text-gray-400">Active Opportunities</div>
  </div>
  <div className="bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6 text-center">
    <div className="text-2xl font-bold text-green-400 mb-1">{formatGP(stats.avgProfit)}</div>
    <div className="text-sm text-gray-400">Avg Profit</div>
  </div>
  <div className="bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6 text-center">
    <div className="text-2xl font-bold text-blue-400 mb-1">{formatGP(stats.topValue)}</div>
    <div className="text-sm text-gray-400">Top Value</div>
  </div>
  <div className="bg-gray-800/50 backdrop-blur-sm border border-gray-700/50 rounded-xl p-6 text-center">
    <div className="text-2xl font-bold text-purple-400 mb-1">{formatGP(stats.totalEfficiency)}</div>
    <div className="text-sm text-gray-400">Efficiency</div>
  </div>
</motion.div>
```

### 2. **Live Profit Dashboard Integration**

```typescript
// Professional profit tracking
<LiveProfitDashboard 
  opportunities={getFilteredAndSortedItems()}
  currentCapital={currentCapital}
  onCapitalChange={setCurrentCapital}
/>
```

### 3. **Market Intelligence Display**

```typescript
// Real-time market intelligence dashboard
{showReactiveFeatures && socketState?.isConnected && (
  <motion.div className="bg-gradient-to-r from-blue-900/20 via-purple-900/20 to-blue-900/20 backdrop-blur-sm border border-blue-500/30 rounded-xl p-6">
    <div className="flex items-center justify-between mb-4">
      <div className="flex items-center gap-3">
        <div className="p-2 bg-blue-500/20 rounded-lg">
          <SparklesIcon className="w-6 h-6 text-blue-400" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-blue-400">🚀 AI Market Intelligence</h3>
          <p className="text-sm text-gray-400">Real-time market analysis and pattern detection</p>
        </div>
      </div>
    </div>

    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
      {/* Market Events */}
      <div className="bg-gray-800/30 rounded-lg p-4">
        <div className="flex items-center gap-2 mb-2">
          <ChartBarIcon className="w-4 h-4 text-green-400" />
          <span className="text-sm font-medium text-green-400">Market Events</span>
          <span className="text-xs bg-green-500/20 text-green-400 px-2 py-0.5 rounded-full">
            {socketState?.marketEvents?.length || 0}
          </span>
        </div>
        {/* Event listings */}
      </div>

      {/* Pattern Detections */}
      <div className="bg-gray-800/30 rounded-lg p-4">
        <div className="flex items-center gap-2 mb-2">
          <BoltIcon className="w-4 h-4 text-yellow-400" />
          <span className="text-sm font-medium text-yellow-400">Pattern Detections</span>
          <span className="text-xs bg-yellow-500/20 text-yellow-400 px-2 py-0.5 rounded-full">
            {socketState?.patternDetections?.length || 0}
          </span>
        </div>
        {/* Pattern listings */}
      </div>

      {/* Market Alerts */}
      <div className="bg-gray-800/30 rounded-lg p-4">
        <div className="flex items-center gap-2 mb-2">
          <SparklesIcon className="w-4 h-4 text-red-400" />
          <span className="text-sm font-medium text-red-400">Active Alerts</span>
          <span className="text-xs bg-red-500/20 text-red-400 px-2 py-0.5 rounded-full">
            {(socketState?.marketAlerts || []).filter(alert => alert.is_active).length}
          </span>
        </div>
        {/* Alert listings */}
      </div>
    </div>
  </motion.div>
)}
```

---

## Performance Optimizations

### 1. **Efficient Re-rendering Prevention**

```typescript
// Optimized item dependency tracking
useEffect(() => {
  // Only re-run when actual item IDs change, not objects
}, [JSON.stringify(items.map(i => i.item_id))]);

// Batch WebSocket subscriptions
useEffect(() => {
  if (socketState?.isConnected && items.length > 0) {
    const uniqueItemIds = [...new Set(items.map(item => item.item_id.toString()))];
    
    // Add delay to prevent overwhelming WebSocket
    const timeoutId = setTimeout(() => {
      uniqueItemIds.forEach(itemId => {
        if (itemId) socketActions.subscribeToItem(itemId);
      });
    }, 200);
    
    return () => {
      clearTimeout(timeoutId);
      uniqueItemIds.forEach(itemId => {
        if (itemId) socketActions.unsubscribeFromItem(itemId);
      });
    };
  }
}, [socketState?.isConnected, JSON.stringify(items.map(i => i.item_id))]);
```

### 2. **Optimized Data Updates**

```typescript
// Smart price update logic - only update on significant changes
const updatePrices = (priceUpdates: any[]) => {
  setItems(prevItems => {
    const updatedItems = [...prevItems];
    
    priceUpdates.forEach((priceUpdate: any) => {
      const itemIndex = updatedItems.findIndex(item => item.item_id === priceUpdate.item_id);
      if (itemIndex !== -1) {
        const currentPrice = (priceUpdate.high_price + priceUpdate.low_price) / 2;
        const oldPrice = updatedItems[itemIndex].current_buy_price || 0;
        const priceChangePercent = Math.abs((currentPrice - oldPrice) / oldPrice * 100);
        
        // Only update if significant change (>1%)
        if (priceChangePercent > 1 || oldPrice === 0) {
          updatedItems[itemIndex] = {
            ...updatedItems[itemIndex],
            current_buy_price: priceUpdate.low_price,
            last_updated: priceUpdate.timestamp
          };
        }
      }
    });
    
    return updatedItems;
  });
};
```

### 3. **Memory Management**

```typescript
// Proper cleanup on component unmount
useEffect(() => {
  return () => {
    console.log('Cleaning up all subscriptions...');
    // Cleanup is handled by individual useEffect cleanup functions
  };
}, []);

// Limit data size for performance
const response = await apiClient.getData({
  page_size: 50, // Reasonable limit
  // ... other params
});

// Process only top items for context size in AI
const processedItems = allItems.slice(0, 20); // Limit to top 20 for AI context
```

---

## Implementation Templates

### 1. **New Trading View Template**

```typescript
// Template for creating new trading views
export function NewTradingView() {
  // 1. Core State
  const [opportunities, setOpportunities] = useState<TradingOpportunity[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  
  // 2. UI State
  const [searchTerm, setSearchTerm] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [selectedItemForChart, setSelectedItemForChart] = useState<number | null>(null);
  
  // 3. Modal State
  const [selectedOpportunityForCalculator, setSelectedOpportunityForCalculator] = useState<TradingOpportunity | null>(null);
  const [selectedOpportunityForQuickTrade, setSelectedOpportunityForQuickTrade] = useState<TradingOpportunity | null>(null);
  const [showAIAssistant, setShowAIAssistant] = useState(false);
  
  // 4. Professional Trading State
  const [currentCapital, setCurrentCapital] = useState(1000000);
  const [favorites, setFavorites] = useState<Set<number>>(new Set());
  
  // 5. Real-time Intelligence
  const { state: socketState, actions: socketActions } = useReactiveTradingContext();
  
  // 6. Filter State
  const [filters, setFilters] = useState<TradingFilters>({
    // ... filter configuration
  });
  
  // 7. Statistics
  const [stats, setStats] = useState({
    totalOpportunities: 0,
    avgProfit: 0,
    // ... other stats
  });

  // Core Functions
  const fetchTradingData = async () => {
    // ... data fetching logic
  };
  
  const handleFilterChange = (key: string, value: any) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };
  
  // Effects
  useEffect(() => {
    fetchTradingData();
  }, [filters, searchTerm]);
  
  // WebSocket integration
  useEffect(() => {
    if (socketState?.isConnected) {
      socketActions.subscribeToRoute('new-trading-route');
    }
  }, [socketState?.isConnected]);
  
  // Real-time updates
  useEffect(() => {
    // Handle real-time data updates
  }, [socketState?.recommendations, socketState?.priceUpdates]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 p-6">
      <div className="max-w-7xl mx-auto space-y-8">
        
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }}>
          <div className="flex items-center justify-center gap-3 mb-4">
            <div className="p-3 bg-brand-color/10 rounded-xl">
              <BrandIcon className="w-8 h-8 text-brand-color" />
            </div>
            <h1 className="text-4xl font-bold text-gradient">Trading View Title</h1>
          </div>
          <p className="text-xl text-gray-400 max-w-2xl mx-auto">
            Professional trading description
          </p>
        </motion.div>

        {/* Connection Status */}
        {/* ... connection status components */}

        {/* Stats Overview */}
        {/* ... statistics cards */}

        {/* Live Profit Dashboard */}
        <LiveProfitDashboard 
          opportunities={getFilteredAndSortedOpportunities()}
          currentCapital={currentCapital}
          onCapitalChange={setCurrentCapital}
        />

        {/* Controls */}
        {/* ... search and filter controls */}

        {/* Opportunities Grid */}
        <motion.div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {getFilteredAndSortedOpportunities().map((opportunity) => (
            <TradingOpportunityCard
              key={opportunity.id}
              opportunity={opportunity}
              realtimeData={getRealtimeData(opportunity)}
              aiInsights={getAIInsights(opportunity)}
              onClick={() => handleOpportunityClick(opportunity)}
              onCalculateProfit={() => setSelectedOpportunityForCalculator(opportunity)}
              onQuickTrade={() => setSelectedOpportunityForQuickTrade(opportunity)}
            />
          ))}
        </motion.div>

        {/* Modals */}
        {/* ... modal components */}

        {/* AI Assistant Button */}
        {/* ... floating AI assistant button */}
      </div>
    </div>
  );
}
```

### 2. **Filter Implementation Template**

```typescript
// Standard filter implementation pattern
interface TradingFilters {
  search: string;
  minProfit: string;
  maxProfit: string;
  minGpPerHour: string;
  maxGpPerHour: string;
  riskLevel: string;
  minMargin: string;
  maxMargin: string;
  categoryFilter: string;
  volumeFilter: string;
  highValueOnly: boolean;
  onlyProfitable: boolean;
  minCapital: string;
  maxCapital: string;
  ordering: string;
}

const defaultFilters: TradingFilters = {
  search: '',
  minProfit: '',
  maxProfit: '',
  minGpPerHour: '',
  maxGpPerHour: '',
  riskLevel: '',
  minMargin: '',
  maxMargin: '',
  categoryFilter: '',
  volumeFilter: 'all',
  highValueOnly: false,
  onlyProfitable: true,
  minCapital: '',
  maxCapital: '',
  ordering: 'profit_desc'
};

// Filter application function
const getFilteredAndSortedOpportunities = () => {
  let filtered = [...opportunities];
  
  // Apply each filter
  if (filters.search) {
    filtered = filtered.filter(opp => 
      opp.item_name.toLowerCase().includes(filters.search.toLowerCase())
    );
  }
  
  if (filters.minProfit) {
    const minProfit = parseInt(filters.minProfit);
    filtered = filtered.filter(opp => calculateProfit(opp) >= minProfit);
  }
  
  if (filters.onlyProfitable) {
    filtered = filtered.filter(opp => calculateProfit(opp) > 0);
  }
  
  // Apply sorting
  return filtered.sort((a, b) => {
    switch (filters.ordering) {
      case 'profit_desc':
        return calculateProfit(b) - calculateProfit(a);
      case 'gp_per_hour_desc':
        return calculateGpPerHour(b) - calculateGpPerHour(a);
      default:
        return 0;
    }
  });
};
```

---

## Business Logic Patterns

### 1. **Tax-Aware Profit Calculations (Decanting)**

```typescript
// Comprehensive tax calculation for Grand Exchange trading
const calculateTaxAdjustedProfit = (opportunity: DecantingOpportunity) => {
  const buyPrice = opportunity.from_dose_price;
  const sellPrice = opportunity.to_dose_price;
  const dosesPerConversion = opportunity.from_dose;
  
  // Calculate costs with GE tax (2% buy tax)
  const totalBuyCost = buyPrice;
  const buyTax = totalBuyCost * 0.02;
  const totalBuyCostWithTax = totalBuyCost + buyTax;
  
  // Calculate revenue with GE tax (2% sell tax)
  const totalSellRevenue = sellPrice * dosesPerConversion;
  const sellTax = totalSellRevenue * 0.02;
  const totalSellRevenueAfterTax = totalSellRevenue - sellTax;
  
  // Net profit after all taxes
  const netProfit = totalSellRevenueAfterTax - totalBuyCostWithTax;
  
  return {
    netProfit: Math.floor(netProfit),
    isProfit: netProfit > 0,
    taxPaid: buyTax + sellTax,
    marginPercent: buyPrice > 0 ? (netProfit / buyPrice) * 100 : 0
  };
};
```

### 2. **High Alchemy Profit Calculations**

```typescript
// High alchemy specific calculations
const calculateHighAlchemyProfit = (item: Item, natureRunePrice: number = 180) => {
  const buyPrice = item.current_buy_price || item.profit_calc?.current_buy_price || 0;
  const highAlchValue = item.high_alch || 0;
  
  // Basic profit calculation: high_alch_value - buy_price - nature_rune_cost
  const profitPerCast = highAlchValue - buyPrice - natureRunePrice;
  
  // XP and efficiency calculations
  const xpPerCast = 65; // High alchemy XP
  const castsPerHour = 1200; // Efficient casting rate
  const xpPerHour = xpPerCast * castsPerHour; // 78,000 XP/hour
  const profitPerHour = profitPerCast * castsPerHour;
  
  // Efficiency metrics
  const marginPercent = buyPrice > 0 ? (profitPerCast / buyPrice) * 100 : 0;
  const gpPerXp = profitPerCast / xpPerCast;
  
  return {
    profitPerCast,
    profitPerHour,
    xpPerHour,
    marginPercent,
    gpPerXp,
    castsPerHour,
    isProfit: profitPerCast > 0
  };
};
```

---

## Styling & Animation Patterns

### 1. **Consistent Color Schemes**

```typescript
// High Alchemy Theme
const highAlchemyColors = {
  primary: 'yellow-400',
  primaryDark: 'yellow-600',
  accent: 'orange-600',
  gradient: 'from-yellow-600 to-orange-600',
  background: 'from-yellow-900/20 to-orange-900/20'
};

// Decanting Theme
const decantingColors = {
  primary: 'blue-400',
  primaryDark: 'blue-600',
  accent: 'purple-600',
  gradient: 'from-blue-600 to-purple-600',
  background: 'from-blue-900/20 via-purple-900/20 to-blue-900/20'
};

// Usage in components
className={`bg-gradient-to-r ${themeColors.gradient} text-white p-4 rounded-full`}
```

### 2. **Animation Patterns**

```typescript
// Framer Motion animation patterns
import { motion, AnimatePresence } from 'framer-motion';

// Staggered list animations
<motion.div
  initial={{ opacity: 0, y: 20 }}
  animate={{ opacity: 1, y: 0 }}
  transition={{ delay: index * 0.1 }}
  className="grid-item"
>

// Modal animations
<AnimatePresence>
  <motion.div
    initial={{ opacity: 0 }}
    animate={{ opacity: 1 }}
    exit={{ opacity: 0 }}
    className="modal-overlay"
  >
    <motion.div
      initial={{ scale: 0.9, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      exit={{ scale: 0.9, opacity: 0 }}
      className="modal-content"
    >

// Floating button animations
<motion.button
  initial={{ scale: 0 }}
  animate={{ scale: 1 }}
  whileHover={{ scale: 1.1 }}
  whileTap={{ scale: 0.9 }}
  className="floating-button"
>
```

---

## Testing & Debugging Patterns

### 1. **Console Logging Strategy**

```typescript
// Structured logging for debugging
console.log('🔌 WebSocket connected, subscribing to updates...');
console.log('✅ Successfully subscribed to route');
console.log('🔄 Received real-time recommendations:', recommendations);
console.log('💰 Received real-time price updates:', priceUpdates);
console.log('📡 Batch subscribing to items:', uniqueItemIds.length);
console.log('🧹 Cleaning up subscriptions...');

// Debug information with context
console.log('High Alchemy Debug - Filtering results:', {
  totalItems: response.results.length,
  itemsWithHighAlch: response.results.filter(item => item.high_alch).length,
  itemsAboveMinValue: response.results.filter(item => item.high_alch && item.high_alch >= filters.minAlchValue).length,
  finalAlchemyItems: alchemyItems.length,
  sampleItem: alchemyItems[0] ? {
    name: alchemyItems[0].name,
    high_alch: alchemyItems[0].high_alch,
    buy_price: alchemyItems[0].current_buy_price,
    profitPerCast: calculateProfit(alchemyItems[0])
  } : null
});
```

### 2. **Error Handling Patterns**

```typescript
// Comprehensive error handling
try {
  const response = await fetchTradingData();
  setItems(response.results);
} catch (error) {
  console.error('Error fetching trading data:', error);
  
  // Set user-friendly error state
  setWebsocketError(error instanceof Error ? error.message : 'Failed to fetch data');
  
  // Reset to safe state
  setItems([]);
  setStats(getDefaultStats());
} finally {
  setLoading(false);
  setRefreshing(false);
}

// Graceful degradation for WebSocket failures
if (!socketState?.isConnected) {
  // Provide alternative functionality
  return renderStaticView();
}
```

---

## Conclusion

This documentation provides a comprehensive blueprint for implementing sophisticated OSRS trading views. The patterns demonstrated in the High Alchemy and Decanting views can be adapted and extended to create professional trading interfaces for:

- **Flipping View**: Item arbitrage opportunities
- **Crafting View**: Skill-based profit calculations
- **Set Combining View**: Equipment set assembly profits
- **Magic Runes View**: Runecrafting and rune trading
- **Seasonal Trading**: Event-based opportunities

### Key Takeaways

1. **Modular Architecture**: Components are designed for reusability across different trading contexts
2. **Real-time Integration**: WebSocket management provides live market intelligence
3. **Professional UI/UX**: Clean, responsive interfaces with meaningful data visualization
4. **Performance Optimized**: Efficient state management and update strategies
5. **AI-Enhanced**: Intelligent assistants provide contextual trading advice
6. **Comprehensive Filtering**: Multi-dimensional filters enable precise opportunity discovery

### Next Steps

When implementing new trading views:

1. Start with the **New Trading View Template**
2. Adapt the **filter configuration** for your specific trading type
3. Implement **business logic calculations** for your trading mechanics
4. Integrate **real-time WebSocket** subscriptions
5. Add **AI assistant** with domain-specific context
6. Apply **consistent theming** and animations
7. Test with **comprehensive error handling**

This architecture ensures consistent, professional, and feature-rich trading experiences across all routes in the OSRS trading application.

---

*Document generated from analysis of HighAlchemyView.tsx (762 lines) and DecantingView.tsx (1208 lines)*