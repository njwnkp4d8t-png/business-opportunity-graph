/**
 * Mock Data for Development
 * Used when VITE_ENABLE_MOCK_DATA is true
 */

export const mockData = {
  // Database tables
  tables: [
    {
      name: 'block_group',
      source: 'data/block_group.json',
      purpose: 'Census block group geometry and demographics',
      recordCount: 1523,
      lastUpdated: '2024-01-15',
    },
    {
      name: 'business_location',
      source: 'data/business_location.json',
      purpose: 'Geocoded business locations with attributes',
      recordCount: 45289,
      lastUpdated: '2024-01-14',
    },
    {
      name: 'city',
      source: 'data/city.json',
      purpose: 'City boundaries and metadata',
      recordCount: 342,
      lastUpdated: '2024-01-10',
    },
    {
      name: 'zipcode',
      source: 'data/zipcode.json',
      purpose: 'Zipcode polygons for aggregation and filtering',
      recordCount: 1876,
      lastUpdated: '2024-01-12',
    },
    {
      name: 'zone_location',
      source: 'data/zone_location.json',
      purpose: 'Zoning-based scoring locations and candidate sites',
      recordCount: 8934,
      lastUpdated: '2024-01-16',
    },
  ],

  // Export files
  exports: [
    {
      name: 'blockgroups.csv',
      path: 'exports/blockgroups.csv',
      description: 'Scored block groups for candidate regions',
      size: '2.3 MB',
      rows: 15234,
      createdAt: '2024-01-15T10:30:00Z',
    },
    {
      name: 'locations.csv',
      path: 'exports/locations.csv',
      description: 'Store and candidate locations with features',
      size: '8.7 MB',
      rows: 45289,
      createdAt: '2024-01-14T14:20:00Z',
    },
    {
      name: 'businesses.csv',
      path: 'exports/businesses.csv',
      description: 'Business-level attributes for graph ingestion',
      size: '12.1 MB',
      rows: 67123,
      createdAt: '2024-01-16T09:15:00Z',
    },
  ],

  // Notebooks
  notebooks: [
    {
      name: 'city_attributes.ipynb',
      path: 'notebooks/city_attributes.ipynb',
      description: 'City-level attributes and enrichment',
      lastRun: '2024-01-14T16:45:00Z',
      status: 'success',
    },
    {
      name: 'neo4j_analytics.ipynb',
      path: 'notebooks/neo4j_analytics.ipynb',
      description: 'Graph analytics over the Neo4j model',
      lastRun: '2024-01-15T11:20:00Z',
      status: 'success',
    },
    {
      name: 'neo4j_visualization.ipynb',
      path: 'notebooks/neo4j_visualization.ipynb',
      description: 'Visual exploration of the graph',
      lastRun: '2024-01-15T13:30:00Z',
      status: 'success',
    },
    {
      name: 'neo4j_llm.ipynb',
      path: 'notebooks/neo4j_llm.ipynb',
      description: 'LLM-assisted categorization and enrichment',
      lastRun: '2024-01-16T10:00:00Z',
      status: 'running',
    },
  ],

  // Scripts
  scripts: [
    {
      name: 'analysis_block_group_tables.sql',
      path: 'scripts/analysis_block_group_tables.sql',
      description: 'Analysis helpers over block group tables',
      lines: 342,
    },
    {
      name: 'analysis_esri_tables.sql',
      path: 'scripts/analysis_esri_tables.sql',
      description: 'ESRI enrichment and QA queries',
      lines: 278,
    },
    {
      name: 'create_postgres_tables.sql',
      path: 'scripts/create_postgres_tables.sql',
      description: 'Core relational schema for the pipeline',
      lines: 456,
    },
    {
      name: 'etl_entity_tables.sql',
      path: 'scripts/etl_entity_tables.sql',
      description: 'Entity ETL into the warehouse',
      lines: 523,
    },
    {
      name: 'etl_entity_relationships.sql',
      path: 'scripts/etl_entity_relationships.sql',
      description: 'Relationship ETL supporting the knowledge graph',
      lines: 612,
    },
  ],

  // Dashboard stats
  stats: {
    totalBusinesses: 67123,
    totalBlockGroups: 1523,
    totalCities: 342,
    totalZipcodes: 1876,
    graphNodes: 125847,
    graphRelationships: 342156,
    lastUpdated: '2024-01-16T12:00:00Z',
  },
};

/**
 * Simulate API delay for realistic testing
 */
export const delay = (ms = 500) => new Promise((resolve) => setTimeout(resolve, ms));

/**
 * Mock API endpoints
 */
export const mockApi = {
  getTables: async () => {
    await delay();
    return mockData.tables;
  },

  getExports: async () => {
    await delay();
    return mockData.exports;
  },

  getNotebooks: async () => {
    await delay();
    return mockData.notebooks;
  },

  getScripts: async () => {
    await delay();
    return mockData.scripts;
  },

  getStats: async () => {
    await delay();
    return mockData.stats;
  },
};
