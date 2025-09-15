import { fastApiClient } from './client';
import type { Item, ItemSearchResult, ItemFilters } from '../types';

export const itemsApi = {
  // Get all items with pagination and filters
  getItems: async (filters: ItemFilters = {}): Promise<ItemSearchResult> => {
    const params = new URLSearchParams();
    
    if (filters.search) params.append('search', filters.search);
    if (filters.members !== undefined) params.append('members', filters.members.toString());
    if (filters.min_profit) params.append('min_profit', filters.min_profit.toString());
    if (filters.max_profit) params.append('max_profit', filters.max_profit.toString());
    if (filters.min_margin) params.append('min_margin', filters.min_margin.toString());
    if (filters.max_margin) params.append('max_margin', filters.max_margin.toString());
    if (filters.ordering) params.append('ordering', filters.ordering);
    if (filters.page) params.append('page', filters.page.toString());
    if (filters.page_size) params.append('page_size', filters.page_size.toString());
    
    // Add cache-busting parameter to ensure fresh data
    params.append('_cache_bust', Date.now().toString());

    // Backend doesn't support these parameters based on testing, but keeping for future reference
    // params.append('include_calculations', 'true');
    // params.append('include_prices', 'true'); 
    // params.append('with_profit_calc', 'true');
    // params.append('expand', 'profit_calc,latest_price');

    // Add logging to debug the actual request
    console.log('Items API Debug - Request URL:', `/items/?${params}`);
    console.log('Items API Debug - Filters:', filters);

    const response = await fastApiClient.get<ItemSearchResult>(`/items/?${params}`);
    console.log('Items API Debug - Response sample:', {
      count: response.data.count,
      resultsLength: response.data.results.length,
      firstItem: response.data.results[0],
      hasProfileCalc: !!response.data.results[0]?.profit_calc,
      hasLatestPrice: !!response.data.results[0]?.latest_price
    });
    
    return response.data;
  },

  // Get a specific item by ID
  getItem: async (itemId: number): Promise<Item> => {
    const response = await fastApiClient.get<Item>(`/items/${itemId}/`);
    return response.data;
  },

  // Search items with text query
  searchItems: async (query: string): Promise<Item[]> => {
    const response = await fastApiClient.get<Item[]>(`/items/search/`, {
      params: { q: query }
    });
    return response.data;
  },

  // Get similar items
  getSimilarItems: async (itemId: number): Promise<Item[]> => {
    const response = await fastApiClient.get<Item[]>(`/items/${itemId}/similar/`);
    return response.data;
  },

  // Get profit recommendations
  getProfitRecommendations: async (): Promise<Item[]> => {
    const response = await fastApiClient.get<Item[]>('/items/recommendations/');
    return response.data;
  },

  // Analyze a specific item
  analyzeItem: async (itemId: number): Promise<any> => {
    const response = await fastApiClient.get(`/items/${itemId}/analyze/`);
    return response.data;
  },

  // Health check
  healthCheck: async (): Promise<{ status: string }> => {
    const response = await fastApiClient.get('/items/health/');
    return response.data;
  }
};