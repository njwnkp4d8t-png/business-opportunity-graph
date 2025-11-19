/**
 * API Service Layer
 * Centralized HTTP client with error handling and debugging
 */

import axios from 'axios';
import config from '../config';

// Create axios instance with default configuration
const apiClient = axios.create({
  baseURL: config.api.baseURL,
  timeout: config.api.timeout,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for debugging
apiClient.interceptors.request.use(
  (requestConfig) => {
    if (config.features.enableDebug) {
      console.log('🚀 API Request:', {
        method: requestConfig.method?.toUpperCase(),
        url: requestConfig.url,
        params: requestConfig.params,
        data: requestConfig.data,
      });
    }
    return requestConfig;
  },
  (error) => {
    if (config.features.enableDebug) {
      console.error('❌ Request Error:', error);
    }
    return Promise.reject(error);
  }
);

// Response interceptor for debugging and error handling
apiClient.interceptors.response.use(
  (response) => {
    if (config.features.enableDebug) {
      console.log('✅ API Response:', {
        status: response.status,
        url: response.config.url,
        data: response.data,
      });
    }
    return response;
  },
  (error) => {
    if (config.features.enableDebug) {
      console.error('❌ API Error:', {
        message: error.message,
        status: error.response?.status,
        url: error.config?.url,
        data: error.response?.data,
      });
    }

    // Enhanced error object
    const enhancedError = {
      message: error.message,
      status: error.response?.status,
      statusText: error.response?.statusText,
      data: error.response?.data,
      isNetworkError: !error.response,
      isTimeout: error.code === 'ECONNABORTED',
      url: error.config?.url,
    };

    return Promise.reject(enhancedError);
  }
);

/**
 * Generic API request wrapper with error handling
 */
export const apiRequest = async (method, url, data = null, options = {}) => {
  try {
    const response = await apiClient({
      method,
      url,
      data,
      ...options,
    });
    return { data: response.data, error: null };
  } catch (error) {
    return { data: null, error };
  }
};

/**
 * Convenience methods
 */
export const api = {
  get: (url, options) => apiRequest('GET', url, null, options),
  post: (url, data, options) => apiRequest('POST', url, data, options),
  put: (url, data, options) => apiRequest('PUT', url, data, options),
  patch: (url, data, options) => apiRequest('PATCH', url, data, options),
  delete: (url, options) => apiRequest('DELETE', url, null, options),
};

export default apiClient;
