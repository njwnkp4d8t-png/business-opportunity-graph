/**
 * Application configuration
 * All environment variables are prefixed with VITE_ to be exposed to the client
 */

const config = {
  // API Configuration
  api: {
    baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
    timeout: parseInt(import.meta.env.VITE_API_TIMEOUT || '30000', 10),
  },

  // Feature Flags
  features: {
    enableDebug: import.meta.env.VITE_ENABLE_DEBUG === 'true',
    enableMockData: import.meta.env.VITE_ENABLE_MOCK_DATA === 'true',
  },

  // Application Metadata
  app: {
    name: import.meta.env.VITE_APP_NAME || 'Business Opportunity Knowledge Graph',
    version: import.meta.env.VITE_APP_VERSION || '0.0.1',
  },
};

// Log configuration in development
if (config.features.enableDebug) {
  console.log('🔧 Application Configuration:', config);
}

export default config;
