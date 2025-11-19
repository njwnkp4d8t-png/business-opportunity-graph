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
      console.log('Using mock data for tables');
      return { data: await mockApi.getTables(), error: null };
    }

    const { data, error } = await api.get('/api/tables');

    // Fallback to mock if API fails
    if (error) {
      console.warn('API failed, falling back to mock data for tables');
      return { data: await mockApi.getTables(), error: null };
    }

    return { data, error };
  },

  /**
   * Fetch export files
   */
  async getExports() {
    if (useMock) {
      console.log('Using mock data for exports');
      return { data: await mockApi.getExports(), error: null };
    }

    const { data, error } = await api.get('/api/exports');

    if (error) {
      console.warn('API failed, falling back to mock data for exports');
      return { data: await mockApi.getExports(), error: null };
    }

    return { data, error };
  },

  /**
   * Fetch notebooks
   */
  async getNotebooks() {
    if (useMock) {
      console.log('Using mock data for notebooks');
      return { data: await mockApi.getNotebooks(), error: null };
    }

    const { data, error } = await api.get('/api/notebooks');

    if (error) {
      console.warn('API failed, falling back to mock data for notebooks');
      return { data: await mockApi.getNotebooks(), error: null };
    }

    return { data, error };
  },

  /**
   * Fetch scripts
   */
  async getScripts() {
    if (useMock) {
      console.log('Using mock data for scripts');
      return { data: await mockApi.getScripts(), error: null };
    }

    const { data, error } = await api.get('/api/scripts');

    if (error) {
      console.warn('API failed, falling back to mock data for scripts');
      return { data: await mockApi.getScripts(), error: null };
    }

    return { data, error };
  },

  /**
   * Fetch dashboard stats
   */
  async getStats() {
    // Prefer dynamic stats from standardized JSON when available.
    // This keeps the dashboard in sync with the latest pipeline run.
    try {
      const response = await fetch('/data/ca_businesses_standardized.json');
      if (!response.ok) {
        throw new Error(`Failed to load standardized data: ${response.status}`);
      }

      const records = await response.json();

      let totalBusinesses = 0;
      const zips = new Set();
      const blockgroups = new Set();
      const cities = new Set();

      for (const rec of records) {
        totalBusinesses += 1;
        if (rec.zip_code) zips.add(rec.zip_code);
        if (rec.blockgroup) blockgroups.add(rec.blockgroup);
        if (rec.city) cities.add(rec.city);
      }

      const stats = {
        totalBusinesses,
        totalBlockGroups: blockgroups.size,
        totalCities: cities.size,
        totalZipcodes: zips.size,
        // Graph metrics can be wired to a real API later.
        graphNodes: null,
        graphRelationships: null,
        lastUpdated: new Date().toISOString(),
      };

      return { data: stats, error: null };
    } catch (error) {
      console.warn('Failed to compute stats from /data, falling back to mock data:', error);
      return { data: await mockApi.getStats(), error: null };
    }
  },

  /**
   * Fetch aggregated territory metrics (e.g., by ZIP code)
   * Reads the JSON produced by scripts/aggregate_territory_metrics.py
   */
  async getTerritoryMetrics() {
    try {
      const response = await fetch('/data/ca_businesses_standardized_by_zip_code.json');
      if (!response.ok) {
        throw new Error(`Failed to load territory metrics: ${response.status}`);
      }

      const payload = await response.json();

      const territories = Array.isArray(payload.territories) ? [...payload.territories] : [];
      territories.sort((a, b) => (b.business_count || 0) - (a.business_count || 0));

      const data = {
        groupBy: payload.group_by || 'zip_code',
        summary: payload.summary || null,
        territories,
      };

      return { data, error: null };
    } catch (error) {
      console.warn('Failed to load territory metrics from /data:', error);
      return { data: null, error };
    }
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
