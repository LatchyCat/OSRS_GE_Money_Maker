import { apiClient } from './client';

export interface DataRefreshRequest {
  force?: boolean;
  hot_items_only?: boolean;
}

export interface DataRefreshResponse {
  success: boolean;
  message?: string;
  error?: string;
  items_processed: number;
  items_updated: number;
  price_snapshots_created: number;
  profit_calculations_updated: number;
  refresh_time: string;
  operation_id: number;
}

export interface DataFreshnessStatus {
  data_age_hours: number | null;
  data_status: 'fresh' | 'recent' | 'stale' | 'very_stale' | 'unknown';
  quality_score: number;
  hot_items_needing_refresh: number;
  total_items_tracked: number;
  total_calculations: number;
  recommendations: string[];
  last_refresh: string | null;
  sync_in_progress: boolean;
  last_sync_success: string | null;
}

export const systemApi = {
  /**
   * Trigger manual data refresh from OSRS API
   */
  refreshData: async (options: DataRefreshRequest = {}): Promise<DataRefreshResponse> => {
    const response = await apiClient.post<DataRefreshResponse>('/system/refresh-data/', options);
    return response.data;
  },

  /**
   * Get current data freshness status and recommendations
   */
  getDataStatus: async (): Promise<DataFreshnessStatus> => {
    const response = await apiClient.get<DataFreshnessStatus>('/system/data-status/');
    return response.data;
  },

  /**
   * Quick refresh for hot items only (faster)
   */
  refreshHotItems: async (): Promise<DataRefreshResponse> => {
    return systemApi.refreshData({ hot_items_only: true });
  },

  /**
   * Force refresh all data regardless of age
   */
  forceRefreshAll: async (): Promise<DataRefreshResponse> => {
    return systemApi.refreshData({ force: true });
  }
};