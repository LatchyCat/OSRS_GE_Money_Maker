import { useState, useEffect, useCallback, useRef } from 'react';
import { useSeasonalDataContext } from '../contexts/SeasonalDataContext';

interface RealtimeSyncConfig {
  enabled?: boolean;
  syncIntervalMs?: number;
  itemIds?: number[];
  autoSync?: {
    marketOverview?: boolean;
    recommendations?: boolean;
    patterns?: boolean;
    events?: boolean;
    forecasts?: boolean;
  };
}

interface RealtimeSyncState {
  isConnected: boolean;
  lastSyncTime: number | null;
  syncCount: number;
  errors: string[];
  connectionStatus: 'connecting' | 'connected' | 'disconnected' | 'error';
}

export function useRealtimeSync(config: RealtimeSyncConfig = {}) {
  const {
    enabled = true,
    syncIntervalMs = 30000, // 30 seconds
    itemIds = [],
    autoSync = {
      marketOverview: true,
      recommendations: true,
      patterns: false,
      events: true,
      forecasts: false,
    },
  } = config;

  const { actions, utils } = useSeasonalDataContext();
  const [state, setState] = useState<RealtimeSyncState>({
    isConnected: false,
    lastSyncTime: null,
    syncCount: 0,
    errors: [],
    connectionStatus: 'disconnected',
  });

  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const isActiveRef = useRef(true);

  const addError = useCallback((error: string) => {
    setState(prev => ({
      ...prev,
      errors: [...prev.errors.slice(-4), `${new Date().toISOString()}: ${error}`],
    }));
  }, []);

  const clearErrors = useCallback(() => {
    setState(prev => ({ ...prev, errors: [] }));
  }, []);

  const performSync = useCallback(async () => {
    if (!enabled || !isActiveRef.current) return;

    try {
      setState(prev => ({ ...prev, connectionStatus: 'connecting' }));

      const syncPromises: Promise<void>[] = [];

      // Sync market overview if enabled and stale
      if (autoSync.marketOverview && utils.isDataStale('overview', syncIntervalMs)) {
        syncPromises.push(actions.fetchMarketOverview());
      }

      // Sync recommendations if enabled and stale
      if (autoSync.recommendations && utils.isDataStale('recommendations', syncIntervalMs)) {
        syncPromises.push(actions.fetchActiveRecommendations());
      }

      // Sync patterns if enabled and stale
      if (autoSync.patterns && utils.isDataStale('patterns', syncIntervalMs * 2)) {
        syncPromises.push(actions.fetchStrongPatterns());
      }

      // Sync events if enabled and stale
      if (autoSync.events && utils.isDataStale('events', syncIntervalMs * 3)) {
        syncPromises.push(actions.fetchUpcomingEvents());
      }

      // Sync forecasts if enabled and stale
      if (autoSync.forecasts && utils.isDataStale('forecasts', syncIntervalMs * 2)) {
        syncPromises.push(actions.fetchUpcomingForecasts());
      }

      // Sync specific item data
      for (const itemId of itemIds) {
        const itemData = utils.getItemData(itemId);
        if (!itemData || (Date.now() - itemData.lastUpdated) > syncIntervalMs * 2) {
          syncPromises.push(actions.fetchItemData(itemId));
        }
      }

      if (syncPromises.length > 0) {
        await Promise.allSettled(syncPromises);
        
        setState(prev => ({
          ...prev,
          isConnected: true,
          lastSyncTime: Date.now(),
          syncCount: prev.syncCount + 1,
          connectionStatus: 'connected',
        }));
      } else {
        setState(prev => ({ ...prev, connectionStatus: 'connected' }));
      }

    } catch (error: any) {
      addError(`Sync failed: ${error.message}`);
      setState(prev => ({ ...prev, connectionStatus: 'error' }));
    }
  }, [
    enabled,
    autoSync,
    syncIntervalMs,
    itemIds,
    actions,
    utils,
    addError,
  ]);

  const startSync = useCallback(() => {
    if (!enabled || intervalRef.current) return;

    isActiveRef.current = true;
    
    // Immediate sync
    performSync();

    // Set up interval
    intervalRef.current = setInterval(performSync, syncIntervalMs);
    
    setState(prev => ({ 
      ...prev, 
      isConnected: true,
      connectionStatus: 'connecting',
    }));
  }, [enabled, performSync, syncIntervalMs]);

  const stopSync = useCallback(() => {
    isActiveRef.current = false;
    
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    
    setState(prev => ({ 
      ...prev, 
      isConnected: false,
      connectionStatus: 'disconnected',
    }));
  }, []);

  const forceSync = useCallback(async () => {
    await performSync();
  }, [performSync]);

  // Auto-start/stop based on enabled state
  useEffect(() => {
    if (enabled) {
      startSync();
    } else {
      stopSync();
    }

    return () => {
      stopSync();
    };
  }, [enabled, startSync, stopSync]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      isActiveRef.current = false;
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);

  // Handle page visibility changes
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.hidden) {
        // Page is hidden, pause sync
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
      } else {
        // Page is visible, resume sync
        if (enabled && !intervalRef.current) {
          performSync(); // Immediate sync when page becomes visible
          intervalRef.current = setInterval(performSync, syncIntervalMs);
        }
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [enabled, performSync, syncIntervalMs]);

  // Handle network connectivity changes
  useEffect(() => {
    const handleOnline = () => {
      if (enabled && navigator.onLine) {
        addError('Connection restored, resuming sync');
        forceSync();
      }
    };

    const handleOffline = () => {
      addError('Connection lost, sync paused');
      setState(prev => ({ ...prev, connectionStatus: 'error' }));
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [enabled, forceSync, addError]);

  return {
    state,
    actions: {
      start: startSync,
      stop: stopSync,
      forceSync,
      clearErrors,
    },
    config: {
      enabled,
      syncIntervalMs,
      itemIds,
      autoSync,
    },
  };
}

// Specialized hook for item-specific real-time updates
export function useItemRealtimeSync(itemId: number, options: { enabled?: boolean; syncIntervalMs?: number } = {}) {
  return useRealtimeSync({
    enabled: options.enabled,
    syncIntervalMs: options.syncIntervalMs || 60000, // 1 minute for item data
    itemIds: [itemId],
    autoSync: {
      marketOverview: false,
      recommendations: false,
      patterns: false,
      events: false,
      forecasts: false,
    },
  });
}

// Hook for dashboard real-time updates
export function useDashboardRealtimeSync(enabled = true) {
  return useRealtimeSync({
    enabled,
    syncIntervalMs: 30000, // 30 seconds
    itemIds: [],
    autoSync: {
      marketOverview: true,
      recommendations: true,
      patterns: true,
      events: true,
      forecasts: true,
    },
  });
}

export default useRealtimeSync;