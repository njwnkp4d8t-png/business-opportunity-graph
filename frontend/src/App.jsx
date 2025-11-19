import { useEffect, useState } from 'react';
import './App.css';
import ErrorBoundary from './components/ErrorBoundary';
import LoadingSpinner from './components/LoadingSpinner';
import ErrorMessage from './components/ErrorMessage';
import DebugPanel from './components/DebugPanel';
import dataService from './services/dataService';
import useApi from './hooks/useApi';
import { formatDate, formatNumber, formatBytes, logger } from './utils/debug';
import config from './config';

const NAV_SECTIONS = [
  { id: 'dashboard', label: 'Dashboard', icon: 'OV' },
  { id: 'territories', label: 'Territories', icon: 'TZ' },
  { id: 'database', label: 'Data Model', icon: 'DB' },
  { id: 'docs', label: 'Docs', icon: 'DOC' },
  { id: 'exports', label: 'Exports', icon: 'EX' },
  { id: 'notebooks', label: 'Notebooks', icon: 'NB' },
  { id: 'scripts', label: 'Scripts', icon: 'ETL' },
  { id: 'aiFranchise', label: 'AI Franchise', icon: 'AI' },
  { id: 'neo4j', label: 'Neo4j & API', icon: 'G' },
  { id: 'gettingStarted', label: 'Getting Started', icon: '?' },
];

function Dashboard() {
  const {
    data: stats,
    loading: statsLoading,
    error: statsError,
    refetch: refetchStats,
  } = useApi(() => dataService.getStats());

  const {
    data: territoryData,
    loading: territoryLoading,
    error: territoryError,
    refetch: refetchTerritories,
  } = useApi(() => dataService.getTerritoryMetrics(), []);

  if (statsLoading) {
    return <LoadingSpinner message="Loading dashboard statistics..." />;
  }

  if (statsError) {
    return <ErrorMessage error={statsError} onRetry={refetchStats} />;
  }

  const territories = territoryData?.territories ?? [];
  const topTerritories = territories.slice(0, 10);

  const formatPercent = (value) => {
    if (typeof value !== 'number') return '—';
    return `${(value * 100).toFixed(1)}%`;
  };

  return (
    <div className="content-section fade-in">
      <h2>Project Dashboard</h2>
      <p className="lede">
        Business Opportunity Knowledge Graph – UCSD DSE 203 project to help franchise planners
        identify promising regions for new locations using spatial, tabular, and graph analytics.
      </p>

      {stats && (
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-icon">OV</div>
            <div className="stat-value">{formatNumber(stats.totalBusinesses)}</div>
            <div className="stat-label">Total Businesses</div>
          </div>
          <div className="stat-card">
            <div className="stat-icon">BG</div>
            <div className="stat-value">{formatNumber(stats.totalBlockGroups)}</div>
            <div className="stat-label">Block Groups</div>
          </div>
          <div className="stat-card">
            <div className="stat-icon">CT</div>
            <div className="stat-value">{formatNumber(stats.totalCities)}</div>
            <div className="stat-label">Cities</div>
          </div>
          <div className="stat-card">
            <div className="stat-icon">ZIP</div>
            <div className="stat-value">{formatNumber(stats.totalZipcodes)}</div>
            <div className="stat-label">ZIP Codes</div>
          </div>
          <div className="stat-card">
            <div className="stat-icon">GN</div>
            <div className="stat-value">
              {stats.graphNodes != null ? formatNumber(stats.graphNodes) : '—'}
            </div>
            <div className="stat-label">Graph Nodes</div>
          </div>
          <div className="stat-card">
            <div className="stat-icon">GR</div>
            <div className="stat-value">
              {stats.graphRelationships != null ? formatNumber(stats.graphRelationships) : '—'}
            </div>
            <div className="stat-label">Relationships</div>
          </div>
        </div>
      )}

      <div className="two-column">
        <div>
          <h3>Overview</h3>
          <ul className="bullet-list">
            <li>Combines geographic data, demographics, and business attributes.</li>
            <li>Builds a Neo4j knowledge graph for rich traversal and scoring.</li>
            <li>Supports LLM-based enrichment for smarter categorization.</li>
            <li>Computes territory-level metrics to support franchise planning.</li>
          </ul>
        </div>
        <div>
          <h3>Team</h3>
          <ul className="bullet-list">
            <li>
              <strong>Spencer</strong> – Data engineering &amp; pipelines
            </li>
            <li>
              <strong>Faizan</strong> – Spatial analytics
            </li>
            <li>
              <strong>Isa</strong> – Neo4j graph modeling &amp; queries
            </li>
            <li>
              <strong>Frank</strong> – Frontend &amp; visualization
            </li>
          </ul>
        </div>
      </div>

      {territoryLoading && (
        <p className="lede">Loading territory metrics for a quick ZIP summary…</p>
      )}

      {!territoryLoading && territoryError && (
        <p className="lede">
          Territory metrics are not available yet. Run
          {' '}
          <code>scripts/aggregate_territory_metrics.py</code>
          {' '}
          to generate
          {' '}
          <code>data/ca_businesses_standardized_by_zip_code.json</code>
          .
        </p>
      )}

      {!territoryLoading && !territoryError && topTerritories.length > 0 && (
        <div style={{ marginTop: '1.5rem' }}>
          <h3>Top Territories by Business Count</h3>
          <table className="info-table">
            <thead>
              <tr>
                <th>Territory (ZIP)</th>
                <th>Businesses</th>
                <th>Franchise %</th>
                <th>Avg Rating</th>
                <th>Top Sector</th>
                <th>Top Subsector</th>
              </tr>
            </thead>
            <tbody>
              {topTerritories.map((t) => (
                <tr key={t.territory_id} className="table-row">
                  <td>
                    <code>{t.territory_id}</code>
                  </td>
                  <td>{formatNumber(t.business_count ?? 0)}</td>
                  <td>{formatPercent(t.pct_franchise)}</td>
                  <td>
                    {typeof t.avg_rating_mean === 'number' ? t.avg_rating_mean.toFixed(2) : '—'}
                  </td>
                  <td>{t.top_sectors?.[0]?.name || '—'}</td>
                  <td>{t.top_subsectors?.[0]?.name || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {stats?.lastUpdated && (
        <div className="info-footer">Last updated: {formatDate(stats.lastUpdated)}</div>
      )}
    </div>
  );
}

function TerritoryMetricsSection() {
  const {
    data: territoryData,
    loading,
    error,
    refetch,
  } = useApi(() => dataService.getTerritoryMetrics(), []);

  if (loading) {
    return <LoadingSpinner message="Loading territory metrics..." />;
  }

  if (error) {
    return <ErrorMessage error={error} onRetry={refetch} />;
  }

  if (!territoryData || !territoryData.territories || territoryData.territories.length === 0) {
    return (
      <div className="content-section fade-in">
        <h2>Territory Metrics</h2>
        <p className="lede">
          No aggregated territory metrics were found.
          {' '}
          Make sure you have run
          {' '}
          <code>scripts/aggregate_territory_metrics.py</code>
          {' '}
          so that
          {' '}
          <code>data/ca_businesses_standardized_by_zip_code.json</code>
          {' '}
          exists in the
          {' '}
          <code>data/</code>
          {' '}
          folder.
        </p>
      </div>
    );
  }

  const { summary, territories } = territoryData;

  const formatPercent = (value) => {
    if (typeof value !== 'number') return '—';
    return `${(value * 100).toFixed(1)}%`;
  };

  return (
    <div className="content-section fade-in">
      <h2>Territory Metrics</h2>
      <p className="lede">
        Aggregated franchise and category metrics by
        {' '}
        {summary?.group_by || territoryData.groupBy}
        {' '}
        to support territory planning and prioritization.
      </p>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon">TZ</div>
          <div className="stat-value">
            {formatNumber(summary?.territory_count ?? territories.length)}
          </div>
          <div className="stat-label">Territories</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">BUS</div>
          <div className="stat-value">
            {formatNumber(
              summary?.total_businesses
                ?? territories.reduce((acc, t) => acc + (t.business_count || 0), 0),
            )}
          </div>
          <div className="stat-label">Businesses in Scope</div>
        </div>
      </div>

      <table className="info-table" style={{ marginTop: '1.5rem' }}>
        <thead>
          <tr>
            <th>Territory (ZIP)</th>
            <th>Businesses</th>
            <th>Franchise</th>
            <th>Independent</th>
            <th>Franchise %</th>
            <th>Avg Rating</th>
            <th>Top Sector</th>
            <th>Top Subsector</th>
          </tr>
        </thead>
        <tbody>
          {territories.map((t) => (
            <tr key={t.territory_id} className="table-row">
              <td>
                <code>{t.territory_id}</code>
              </td>
              <td>{formatNumber(t.business_count ?? 0)}</td>
              <td>{formatNumber(t.franchise_count ?? 0)}</td>
              <td>{formatNumber(t.independent_count ?? 0)}</td>
              <td>{formatPercent(t.pct_franchise)}</td>
              <td>
                {typeof t.avg_rating_mean === 'number' ? t.avg_rating_mean.toFixed(2) : '—'}
              </td>
              <td>{t.top_sectors?.[0]?.name || '—'}</td>
              <td>{t.top_subsectors?.[0]?.name || '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="info-footer">
        Source:
        {' '}
        <code>data/ca_businesses_standardized_by_zip_code.json</code>
        {' '}
        (mounted into the container via
        {' '}
        <code>docker/run_docker.ps1</code>
        ).
      </div>
    </div>
  );
}

function DatabaseSection() {
  const {
    data: tables,
    loading,
    error,
    refetch,
  } = useApi(() => dataService.getTables());

  if (loading) {
    return <LoadingSpinner message="Loading database tables..." />;
  }

  if (error) {
    return <ErrorMessage error={error} onRetry={refetch} />;
  }

  return (
    <div className="content-section fade-in">
      <h2>Data Model &amp; Tables</h2>
      <p className="lede">
        High-level description of the core tables and JSON files used to construct the knowledge
        graph and territory planner.
      </p>
      <table className="info-table">
        <thead>
          <tr>
            <th>Table</th>
            <th>Source</th>
            <th>Purpose</th>
            {tables?.[0]?.recordCount && <th>Records</th>}
            {tables?.[0]?.lastUpdated && <th>Last Updated</th>}
          </tr>
        </thead>
        <tbody>
          {tables?.map((table) => (
            <tr key={table.name} className="table-row">
              <td>
                <code>{table.name}</code>
              </td>
              <td>
                <code>{table.source}</code>
              </td>
              <td>{table.purpose}</td>
              {table.recordCount && <td>{formatNumber(table.recordCount)}</td>}
              {table.lastUpdated && <td>{formatDate(table.lastUpdated)}</td>}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function DocsSection() {
  return (
    <div className="content-section fade-in">
      <h2>Documentation &amp; Diagram</h2>
      <p className="lede">
        Project documentation, diagrams, and reference materials describing the system architecture,
        data model, and operational procedures.
      </p>
      <ul className="bullet-list">
        <li>
          <a href="/graph_model.drawio" target="_blank" rel="noreferrer">
            graph_model.drawio
          </a>
          {' '}
          – Entity and relationship diagram (open in draw.io or download)
        </li>
        <li>
          <code>README.md</code>
          {' '}
          – Project summary and goals
        </li>
        <li>
          <code>docker/README.md</code>
          {' '}
          – Docker setup and deployment guide
        </li>
      </ul>
    </div>
  );
}

function ExportsSection() {
  const {
    data: exports,
    loading,
    error,
    refetch,
  } = useApi(() => dataService.getExports());

  if (loading) {
    return <LoadingSpinner message="Loading export files..." />;
  }

  if (error) {
    return <ErrorMessage error={error} onRetry={refetch} />;
  }

  return (
    <div className="content-section fade-in">
      <h2>Data Exports</h2>
      <p className="lede">
        CSV and JSON exports used for downstream analytics and Neo4j loading. These files contain
        processed data ready for import into various systems.
      </p>
      <div className="exports-grid">
        {exports?.map((file) => (
          <div key={file.name} className="export-card">
            <div className="export-header">
              <span className="export-icon">EX</span>
              <code className="export-name">{file.name}</code>
            </div>
            <p className="export-description">{file.description}</p>
            <div className="export-meta">
              {file.size && <span>Size: {file.size}</span>}
              {file.rows && <span>{formatNumber(file.rows)} rows</span>}
            </div>
            {file.createdAt && (
              <div className="export-date">Created: {formatDate(file.createdAt)}</div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function NotebooksSection() {
  const {
    data: notebooks,
    loading,
    error,
    refetch,
  } = useApi(() => dataService.getNotebooks());

  if (loading) {
    return <LoadingSpinner message="Loading notebooks..." />;
  }

  if (error) {
    return <ErrorMessage error={error} onRetry={refetch} />;
  }

  return (
    <div className="content-section fade-in">
      <h2>Jupyter Notebooks</h2>
      <p className="lede">
        Analysis notebooks for data exploration, graph analytics, and visualization. Run these in
        the Docker container or connect with a remote kernel.
      </p>
      <div className="notebooks-grid">
        {notebooks?.map((notebook) => (
          <div key={notebook.name} className="notebook-card">
            <div className="notebook-header">
              <code className="notebook-name">{notebook.name}</code>
              {notebook.status && (
                <span className={`notebook-status status-${notebook.status}`}>
                  {notebook.status}
                </span>
              )}
            </div>
            <p className="notebook-description">{notebook.description}</p>
            <div className="notebook-meta">
              {notebook.size && <span>{formatBytes(notebook.size)}</span>}
              {notebook.lastRun && <span>Last run: {formatDate(notebook.lastRun)}</span>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ScriptsSection() {
  const {
    data: scripts,
    loading,
    error,
    refetch,
  } = useApi(() => dataService.getScripts());

  if (loading) {
    return <LoadingSpinner message="Loading scripts..." />;
  }

  if (error) {
    return <ErrorMessage error={error} onRetry={refetch} />;
  }

  return (
    <div className="content-section fade-in">
      <h2>ETL &amp; Analytics Scripts</h2>
      <p className="lede">
        SQL and Python scripts for the data pipeline, ETL operations, and analytics. These scripts
        define the core data transformations and schema.
      </p>
      <table className="info-table">
        <thead>
          <tr>
            <th>Script</th>
            <th>Description</th>
            {scripts?.[0]?.lines && <th>Lines</th>}
          </tr>
        </thead>
        <tbody>
          {scripts?.map((script) => (
            <tr key={script.name} className="table-row">
              <td>
                <code>{script.name}</code>
              </td>
              <td>{script.description}</td>
              {script.lines && <td>{formatNumber(script.lines)}</td>}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function AIFranchiseSection() {
  return (
    <div className="content-section fade-in">
      <h2>AI Franchise Classification</h2>
      <p className="lede">
        The AI franchise pipeline cleans and standardizes business data, classifies categories, and
        infers franchise vs independent status for each location.
      </p>
      <h3>Pipeline summary</h3>
      <ul className="bullet-list">
        <li>
          Input:
          {' '}
          <code>data/ca_businesses_with_ai_franchise.json</code>
          {' '}
          (and working copy file).
        </li>
        <li>
          Output:
          {' '}
          <code>data/ca_businesses_standardized.json</code>
          {' '}
          (slim, planner-friendly view).
        </li>
        <li>Normalization: names, ZIPs, block groups, coordinates, phone numbers, ratings.</li>
        <li>
          Classification: rule-based mappings plus batched, rate-limited OpenAI calls for ambiguous
          categories, with safe defaults when uncertain.
        </li>
      </ul>
      <h3>Key fields</h3>
      <ul className="bullet-list">
        <li>
          Identity:
          {' '}
          <code>business_id</code>
          ,
          {' '}
          <code>business_name</code>
          ,
          {' '}
          <code>address</code>
          ,
          {' '}
          <code>city</code>
          ,
          {' '}
          <code>zip_code</code>
          ,
          {' '}
          <code>blockgroup</code>
        </li>
        <li>
          Franchise:
          {' '}
          <code>franchise</code>
          ,
          {' '}
          <code>franchise_type</code>
          ,
          {' '}
          <code>is_franchise</code>
          ,
          {' '}
          <code>confidence</code>
          ,
          {' '}
          <code>reasoning</code>
        </li>
        <li>
          Categories:
          {' '}
          <code>category_sector</code>
          ,
          {' '}
          <code>category_subsector</code>
          ,
          {' '}
          <code>category_confidence</code>
          ,
          {' '}
          <code>category_method</code>
        </li>
      </ul>
      <p className="lede">
        Territory-level metrics are computed by
        {' '}
        <code>scripts/aggregate_territory_metrics.py</code>
        {' '}
        and written to
        {' '}
        <code>data/ca_businesses_standardized_by_zip_code.json</code>
        , which can be used directly for scoring and visualization.
      </p>
    </div>
  );
}

function Neo4jSection() {
  return (
    <div className="content-section fade-in">
      <h2>Neo4j &amp; API Overview</h2>
      <p className="lede">
        The Business Opportunity Knowledge Graph is designed to be loaded into Neo4j for graph
        analytics and territory planning.
      </p>
      <h3>Configuration via .env</h3>
      <p className="lede">
        Set these variables in
        {' '}
        <code>.env</code>
        {' '}
        to enable Neo4j connectivity:
      </p>
      <ul className="bullet-list">
        <li>
          <code>NEO4J_URI</code>
          {' '}
          (e.g.
          {' '}
          <code>bolt://localhost:7687</code>
          )
        </li>
        <li>
          <code>NEO4J_USER</code>
          {' '}
          (e.g.
          {' '}
          <code>neo4j</code>
          )
        </li>
        <li>
          <code>NEO4J_PASSWORD</code>
          {' '}
          (your password)
        </li>
        <li>
          <code>NEO4J_DATABASE</code>
          {' '}
          (e.g.
          {' '}
          <code>neo4j</code>
          )
        </li>
      </ul>
      <p className="lede">
        These values are consumed by
        {' '}
        <code>scripts/config.py</code>
        {' '}
        and the Neo4j notebooks under
        {' '}
        <code>notebooks/</code>
        . The current Docker image focuses on analytics and does not expose a public Neo4j HTTP
        endpoint.
      </p>
      <h3>Example Cypher</h3>
      <pre className="code-block">
{`// Businesses by sector
MATCH (b:Business)
RETURN b.category_sector AS sector, count(*) AS businesses
ORDER BY businesses DESC;

// Franchise candidates in a ZIP
MATCH (b:Business {zip_code: '92101'})
WHERE b.is_franchise = true
RETURN b.business_name, b.category_sector, b.avg_rating
LIMIT 25;`}
      </pre>
    </div>
  );
}

function GettingStartedSection() {
  return (
    <div className="content-section fade-in">
      <h2>Getting Started</h2>
      <p className="lede">
        You can explore this project using Docker without configuring any credentials. If you want
        to connect to external services, you can opt in via a
        {' '}
        <code>.env</code>
        {' '}
        file.
      </p>
      <h3>1. Prerequisites</h3>
      <ul className="bullet-list">
        <li>Docker Desktop (Linux containers enabled)</li>
        <li>PowerShell on Windows</li>
      </ul>
      <h3>2. Optional: Configure secrets</h3>
      <p className="lede">
        To use OpenAI or connect to Neo4j/PostgreSQL, copy the example env file and edit it:
      </p>
      <pre className="code-block">
{`cp .env.example .env
# Edit .env with NEO4J_URI, OPENAI_API_KEY, etc.`}
      </pre>
      <p className="lede">
        If you just want to see the dashboard and sample data, you can skip this and run with no
        {' '}
        <code>.env</code>
        .
      </p>
      <h3>3. Build &amp; run via Docker</h3>
      <pre className="code-block">
{`# From the repository root
powershell -ExecutionPolicy Bypass -File .\\docker\\run_docker.ps1`}
      </pre>
      <p className="lede">
        The script builds the image, mounts
        {' '}
        <code>data/</code>
        ,
        {' '}
        <code>exports/</code>
        ,
        {' '}
        <code>logs/</code>
        , and starts the front end behind Nginx on port 8888.
      </p>
      <h3>4. Open the UI</h3>
      <p className="lede">
        Open
        {' '}
        <code>http://localhost:8888</code>
        {' '}
        in your browser. The dashboard statistics are
        computed from
        {' '}
        <code>data/ca_businesses_standardized.json</code>
        , so they stay up to date whenever you rerun
        the pipeline.
      </p>
      <h3>5. What&rsquo;s in the image</h3>
      <ul className="bullet-list">
        <li>Python 3.11 plus a virtualenv with all project dependencies.</li>
        <li>
          Geo/ML stack:
          {' '}
          <code>numpy</code>
          ,
          {' '}
          <code>pandas</code>
          ,
          {' '}
          <code>geopandas</code>
          ,
          {' '}
          <code>osmnx</code>
          ,
          {' '}
          <code>cenpy</code>
          ,
          {' '}
          <code>rasterio</code>
          ,
          {' '}
          <code>contextily</code>
          ,
          {' '}
          <code>scikit-learn</code>
          ,
          {' '}
          <code>shapely</code>
          ,
          {' '}
          <code>pyproj</code>
        </li>
        <li>
          Graph/LLM stack:
          {' '}
          <code>neo4j</code>
          ,
          {' '}
          <code>psycopg2-binary</code>
          ,
          {' '}
          <code>openai</code>
          ,
          {' '}
          <code>langchain</code>
          {' '}
          components,
          {' '}
          <code>langgraph</code>
        </li>
        <li>
          Nginx serving the React app and the latest
          {' '}
          <code>data/</code>
          {' '}
          files.
        </li>
      </ul>
    </div>
  );
}

function App() {
  const [active, setActive] = useState('dashboard');
  const [navOpen, setNavOpen] = useState(true);
  const [isTransitioning, setIsTransitioning] = useState(false);

  useEffect(() => {
    logger.info('Navigation changed to:', active);
  }, [active]);

  const handleNavigation = (sectionId) => {
    if (sectionId === active) return;
    setIsTransitioning(true);
    setTimeout(() => {
      setActive(sectionId);
      setIsTransitioning(false);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }, 150);
  };

  const renderSection = () => {
    switch (active) {
      case 'dashboard':
        return <Dashboard />;
      case 'territories':
        return <TerritoryMetricsSection />;
      case 'database':
        return <DatabaseSection />;
      case 'docs':
        return <DocsSection />;
      case 'exports':
        return <ExportsSection />;
      case 'notebooks':
        return <NotebooksSection />;
      case 'scripts':
        return <ScriptsSection />;
      case 'aiFranchise':
        return <AIFranchiseSection />;
      case 'neo4j':
        return <Neo4jSection />;
      case 'gettingStarted':
        return <GettingStartedSection />;
      default:
        return <Dashboard />;
    }
  };

  return (
    <ErrorBoundary>
      <div className="app-root">
        <header className="top-bar">
          <div className="top-bar-title">
            {config.app.name}
            <span className="top-bar-version">
              v
              {config.app.version}
            </span>
          </div>
          <div className="top-bar-accent" />
        </header>

        <div className="layout">
          <aside className={`sidebar ${navOpen ? 'sidebar-open' : 'sidebar-collapsed'}`}>
            <button
              type="button"
              className="sidebar-toggle"
              aria-label="Toggle navigation"
              onClick={() => setNavOpen((open) => !open)}
              title={navOpen ? 'Collapse sidebar' : 'Expand sidebar'}
            >
              {navOpen ? '<' : '>'}
            </button>
            <nav className="nav">
              {NAV_SECTIONS.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  className={`nav-item ${active === item.id ? 'nav-item-active' : ''}`}
                  onClick={() => handleNavigation(item.id)}
                  title={item.label}
                >
                  <span className="nav-icon">{item.icon}</span>
                  <span className="nav-label">{item.label}</span>
                </button>
              ))}
            </nav>
          </aside>

          <main className="content-area">
            <div className={`content-inner ${isTransitioning ? 'transitioning' : ''}`}>
              {renderSection()}
            </div>
          </main>
        </div>

        <DebugPanel />
      </div>
    </ErrorBoundary>
  );
}

export default App;

