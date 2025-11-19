/**
 * Debugging Utilities
 * Helper functions for development and debugging
 */

import config from '../config';

/**
 * Enhanced console logger with timestamps and colors
 */
export const logger = {
  info: (...args) => {
    if (config.features.enableDebug) {
      console.log(`[${new Date().toISOString()}] ℹ️`, ...args);
    }
  },

  success: (...args) => {
    if (config.features.enableDebug) {
      console.log(`[${new Date().toISOString()}] ✅`, ...args);
    }
  },

  warn: (...args) => {
    if (config.features.enableDebug) {
      console.warn(`[${new Date().toISOString()}] ⚠️`, ...args);
    }
  },

  error: (...args) => {
    if (config.features.enableDebug) {
      console.error(`[${new Date().toISOString()}] ❌`, ...args);
    }
  },

  debug: (...args) => {
    if (config.features.enableDebug) {
      console.debug(`[${new Date().toISOString()}] 🐛`, ...args);
    }
  },
};

/**
 * Performance measurement utility
 */
export const measurePerformance = (label) => {
  const start = performance.now();

  return {
    end: () => {
      const duration = performance.now() - start;
      logger.debug(`⏱️ ${label}: ${duration.toFixed(2)}ms`);
      return duration;
    },
  };
};

/**
 * Format bytes to human-readable size
 */
export const formatBytes = (bytes, decimals = 2) => {
  if (bytes === 0) return '0 Bytes';

  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];

  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
};

/**
 * Format date to readable string
 */
export const formatDate = (dateString) => {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

/**
 * Format number with commas
 */
export const formatNumber = (num) => {
  return num?.toLocaleString('en-US') || '0';
};

/**
 * Debug panel component data
 */
export const getDebugInfo = () => {
  return {
    timestamp: new Date().toISOString(),
    userAgent: navigator.userAgent,
    viewport: {
      width: window.innerWidth,
      height: window.innerHeight,
    },
    config: config,
    performance: {
      memory: performance.memory
        ? {
            used: formatBytes(performance.memory.usedJSHeapSize),
            total: formatBytes(performance.memory.totalJSHeapSize),
            limit: formatBytes(performance.memory.jsHeapSizeLimit),
          }
        : 'Not available',
    },
  };
};

/**
 * Copy text to clipboard
 */
export const copyToClipboard = async (text) => {
  try {
    await navigator.clipboard.writeText(text);
    logger.success('Copied to clipboard');
    return true;
  } catch (err) {
    logger.error('Failed to copy to clipboard:', err);
    return false;
  }
};
