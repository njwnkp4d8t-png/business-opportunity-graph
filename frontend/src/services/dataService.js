/**
 * Data Service Layer
 * Provides a unified interface for fetching data (real API or mock)
 */

import { api } from './api';
import { mockApi } from './mockData';
import config from '../config';

const useMock = config.features.enableMockData;

/**
 * Data service with automatic fallback to mock data
 */
export const dataService = {
  /**
   * Fetch database tables
   */
  async getTables() {
    if (useMock) {
      console.log('📦 Using mock data for tables');
      return { data: await mockApi.getTables(), error: null };
    }

    const { data, error } = await api.get('/api/tables');

    // Fallback to mock if API fails
    if (error) {
      console.warn('⚠️ API failed, falling back to mock data');
      return { data: await mockApi.getTables(), error: null };
    }

    return { data, error };
  },

  /**
   * Fetch export files
   */
  async getExports() {
    if (useMock) {
      console.log('📦 Using mock data for exports');
      return { data: await mockApi.getExports(), error: null };
    }

    const { data, error } = await api.get('/api/exports');

    if (error) {
      console.warn('⚠️ API failed, falling back to mock data');
      return { data: await mockApi.getExports(), error: null };
    }

    return { data, error };
  },

  /**
   * Fetch notebooks
   */
  async getNotebooks() {
    if (useMock) {
      console.log('📦 Using mock data for notebooks');
      return { data: await mockApi.getNotebooks(), error: null };
    }

    const { data, error } = await api.get('/api/notebooks');

    if (error) {
      console.warn('⚠️ API failed, falling back to mock data');
      return { data: await mockApi.getNotebooks(), error: null };
    }

    return { data, error };
  },

  /**
   * Fetch scripts
   */
  async getScripts() {
    if (useMock) {
      console.log('📦 Using mock data for scripts');
      return { data: await mockApi.getScripts(), error: null };
    }

    const { data, error } = await api.get('/api/scripts');

    if (error) {
      console.warn('⚠️ API failed, falling back to mock data');
      return { data: await mockApi.getScripts(), error: null };
    }

    return { data, error };
  },

  /**
   * Fetch dashboard stats
   */
  async getStats() {
    if (useMock) {
      console.log('📦 Using mock data for stats');
      return { data: await mockApi.getStats(), error: null };
    }

    const { data, error } = await api.get('/api/stats');

    if (error) {
      console.warn('⚠️ API failed, falling back to mock data');
      return { data: await mockApi.getStats(), error: null };
    }

    return { data, error };
  },

  /**
   * Health check endpoint
   */
  async healthCheck() {
    const { data, error } = await api.get('/health');
    return { data, error };
  },
};

export default dataService;
