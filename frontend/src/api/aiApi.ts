import axios from 'axios';
import type { 
  AIQueryRequest, 
  AIRecommendation, 
  MarketSignal, 
  AgentMetadata, 
  AIQueryResponse, 
  MultiAgentPerformanceData 
} from '../types/aiTypes';

// Re-export types for convenience
export type { 
  AIQueryRequest, 
  AIRecommendation, 
  MarketSignal, 
  AgentMetadata, 
  AIQueryResponse, 
  MultiAgentPerformanceData 
};

// Create AI-specific axios instance
export const aiApiClient = axios.create({
  baseURL: '/api', // AI endpoints are at /api/ 
  timeout: 60000, // 60s timeout for AI processing
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
});

// Request interceptor
aiApiClient.interceptors.request.use(
  (config) => {
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for AI-specific error handling
aiApiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    // Handle AI-specific errors
    if (error.response?.status === 503) {
      console.warn('AI service temporarily unavailable');
    } else if (error.response?.status === 504) {
      console.warn('AI processing timeout');
    } else if (!error.response) {
      console.error('Network error connecting to AI service:', error.message);
    }
    return Promise.reject(error);
  }
);

// Interface definitions moved to ../types/aiTypes.ts

// AI API methods
export const aiApi = {
  // Send a query to the AI trading assistant
  async queryTrading(request: AIQueryRequest): Promise<AIQueryResponse> {
    try {
      const response = await aiApiClient.post('/trading-query/', request);
      if (!response.data.success) {
        throw new Error(response.data.error || 'AI query failed');
      }
      return response.data;
    } catch (error: any) {
      console.error('AI Trading Query Error:', error);
      
      // Return a fallback response structure for graceful degradation
      return {
        success: false,
        response: error.response?.data?.fallback_response || 'I\'m having trouble with the AI analysis right now, but here\'s some basic market data. Please try refreshing or changing your capital amount.',
        precision_opportunities: error.response?.data?.precision_opportunities || [],
        market_signals: error.response?.data?.market_signals || [],
        agent_metadata: error.response?.data?.agent_metadata || {
          query_complexity: 'error',
          agent_used: 'api_error',
          processing_time_ms: 0,
          task_routing_reason: 'Request failed',
          data_quality_score: 0.0,
          confidence_level: 0.0
        },
        error: error.message,
        fallback_response: 'AI analysis temporarily unavailable - please try again',
        fallback_mode: true
      };
    }
  },

  // Get multi-agent performance metrics
  async getPerformanceMetrics(): Promise<MultiAgentPerformanceData> {
    try {
      const response = await aiApiClient.get('/performance/');
      return response.data;
    } catch (error: any) {
      console.error('Performance Metrics Error:', error);
      
      // Return fallback performance data
      return {
        success: false,
        timestamp: new Date().toISOString(),
        system_status: {
          system_healthy: false,
          agents_available: {
            gemma3_fast: false,
            deepseek_smart: false, 
            qwen3_coordinator: false
          },
          current_load: {}
        },
        performance_metrics: {},
        agent_capabilities: {
          gemma3_fast: {
            name: 'Gemma Fast Lane',
            description: 'Currently unavailable',
            speed_multiplier: 0,
            specialties: [],
            complexity_rating: 0,
            color: '#6B7280'
          },
          deepseek_smart: {
            name: 'DeepSeek Analysis', 
            description: 'Currently unavailable',
            speed_multiplier: 0,
            specialties: [],
            complexity_rating: 0,
            color: '#6B7280'
          },
          qwen3_coordinator: {
            name: 'Qwen Coordinator',
            description: 'Currently unavailable', 
            speed_multiplier: 0,
            specialties: [],
            complexity_rating: 0,
            color: '#6B7280'
          }
        },
        routing_logic: {}
      };
    }
  },

  // Debug endpoint for testing AI functionality
  async debugTest(query?: string): Promise<any> {
    try {
      const response = await aiApiClient.post('/debug-test/', { 
        query: query || 'Test query for debug' 
      });
      return response.data;
    } catch (error: any) {
      console.error('AI Debug Test Error:', error);
      return {
        success: false,
        error: error.message,
        debug_results: {
          errors: ['Debug test failed due to network or server error'],
          steps: {},
          final_result: null
        }
      };
    }
  },
};

export default aiApi;