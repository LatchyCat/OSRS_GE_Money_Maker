import axios from 'axios';

// Create axios instance with base configuration
export const apiClient = axios.create({
  baseURL: '/api/v1', // Use proxy path instead of full URL
  timeout: 60000, // Default timeout for heavy processing
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // Important for session-based auth
});

// Create specialized client for quick data endpoints
export const fastApiClient = axios.create({
  baseURL: '/api/v1',
  timeout: 15000, // 15s timeout for quick data fetches
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
});

// Create specialized client for AI-powered analysis endpoints
export const aiApiClient = axios.create({
  baseURL: '/api/v1',
  timeout: 600000, // 10 minute timeout for small local models with extensive data processing
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
});

// Circuit breaker to prevent infinite retry loops during server overload
let circuitBreakerState: { [key: string]: { failures: number, lastFailure: number, isOpen: boolean } } = {};

const CIRCUIT_BREAKER_CONFIG = {
  failureThreshold: 3,      // Open circuit after 3 failures (reduced)
  resetTimeout: 60000,      // Try again after 60 seconds (increased)
  halfOpenRetries: 1        // Only allow 1 retry when half-open (reduced)
};

// Separate config for AI endpoints that are expected to be slower
const AI_CIRCUIT_BREAKER_CONFIG = {
  failureThreshold: 5,      // More tolerant of AI endpoint failures
  resetTimeout: 120000,     // Wait longer before retrying AI endpoints  
  halfOpenRetries: 1        // Conservative retry approach for AI
};

// Retry logic with exponential backoff and circuit breaker
const createRetryInterceptor = (client: typeof axios, isAiClient: boolean = false) => {
  const config = isAiClient ? AI_CIRCUIT_BREAKER_CONFIG : CIRCUIT_BREAKER_CONFIG;
  client.interceptors.response.use(
    (response) => {
      // Reset circuit breaker on success
      const baseUrl = response.config.baseURL || '';
      if (circuitBreakerState[baseUrl]) {
        circuitBreakerState[baseUrl].failures = 0;
        circuitBreakerState[baseUrl].isOpen = false;
      }
      return response;
    },
    async (error) => {
      const config = error.config;
      const baseUrl = config?.baseURL || '';
      
      // Initialize circuit breaker state
      if (!circuitBreakerState[baseUrl]) {
        circuitBreakerState[baseUrl] = { failures: 0, lastFailure: 0, isOpen: false };
      }
      
      const circuitState = circuitBreakerState[baseUrl];
      const now = Date.now();
      
      // Check if circuit breaker is open
      if (circuitState.isOpen) {
        if (now - circuitState.lastFailure < config.resetTimeout) {
          console.warn(`🚫 Circuit breaker OPEN for ${baseUrl} - blocking request`);
          return Promise.reject(new Error('Circuit breaker is open - server may be overloaded'));
        } else {
          // Half-open state - allow limited retries
          circuitState.isOpen = false;
          console.info(`🔄 Circuit breaker HALF-OPEN for ${baseUrl} - allowing limited retries`);
        }
      }
      
      // Update failure count
      circuitState.failures++;
      circuitState.lastFailure = now;
      
      // Open circuit if too many failures
      if (circuitState.failures >= config.failureThreshold) {
        circuitState.isOpen = true;
        console.error(`💥 Circuit breaker OPENED for ${baseUrl} after ${circuitState.failures} failures`);
        return Promise.reject(error);
      }
      
      // Don't retry if we've already retried max times or if it's not a retriable error
      const maxRetries = circuitState.isOpen ? config.halfOpenRetries : 3;
      if (!config || config._retry >= maxRetries || error.response?.status < 500) {
        return Promise.reject(error);
      }
      
      config._retry = (config._retry || 0) + 1;
      
      // Exponential backoff: 1s, 2s, 4s
      const delay = Math.pow(2, config._retry - 1) * 1000;
      
      console.log(`Retrying request (attempt ${config._retry}/${maxRetries}) after ${delay}ms:`, config.url);
      
      await new Promise(resolve => setTimeout(resolve, delay));
      return client(config);
    }
  );
};

// Apply retry logic to all clients
createRetryInterceptor(apiClient);
createRetryInterceptor(fastApiClient);
createRetryInterceptor(aiApiClient, true); // AI client with special handling

// Request interceptor for adding auth headers or other common headers
apiClient.interceptors.request.use(
  (config) => {
    // Add any common headers here
    // For example, if you implement JWT later:
    // const token = localStorage.getItem('token');
    // if (token) {
    //   config.headers.Authorization = `Bearer ${token}`;
    // }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for handling common errors
apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    // Handle common errors
    if (error.response?.status === 401) {
      // Handle unauthorized access
      console.warn('Unauthorized access - session may have expired');
    } else if (error.response?.status >= 500) {
      // Handle server errors
      console.error('Server error:', error.response.data);
    } else if (!error.response) {
      // Handle network errors
      console.error('Network error:', error.message);
    }
    return Promise.reject(error);
  }
);

export default apiClient;