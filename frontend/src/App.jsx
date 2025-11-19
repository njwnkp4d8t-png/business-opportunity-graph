import { useState, useEffect } from 'react';
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
  { id: 'dashboard', label: 'Dashboard', icon: '📊' },
  { id: 'database', label: 'Database', icon: '🗄️' },
  { id: 'docs', label: 'Docs', icon: '📚' },
  { id: 'exports', label: 'Exports', icon: '📤' },
  { id: 'notebooks', label: 'Notebooks', icon: '📓' },
  { id: 'scripts', label: 'Scripts', icon: '⚙️' },
];

function Dashboard() {
  const { data: stats, loading, error, refetch } = useApi(() => dataService.getStats());

  if (loading) return <LoadingSpinner message="Loading dashboard statistics..." />;
  if (error) return <ErrorMessage error={error} onRetry={refetch} />;

  return (
    <div className="content-section fade-in">
      <h2>📊 Project Dashboard</h2>
      <p className="lede">
        Business Opportunity Knowledge Graph — UCSD DSE 203 project to help franchise planners
        identify promising regions for new locations using spatial and graph analytics.
      </p>

      {stats && (
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-icon">🏢</div>
            <div className="stat-value">{formatNumber(stats.totalBusinesses)}</div>
            <div className="stat-label">Total Businesses</div>
          </div>
          <div className="stat-card">
            <div className="stat-icon">📍</div>
            <div className="stat-value">{formatNumber(stats.totalBlockGroups)}</div>
            <div className="stat-label">Block Groups</div>
          </div>
          <div className="stat-card">
            <div className="stat-icon">🏙️</div>
            <div className="stat-value">{formatNumber(stats.totalCities)}</div>
            <div className="stat-label">Cities</div>
          </div>
          <div className="stat-card">
            <div className="stat-icon">📮</div>
            <div className="stat-value">{formatNumber(stats.totalZipcodes)}</div>
            <div className="stat-label">ZIP Codes</div>
          </div>
          <div className="stat-card">
            <div className="stat-icon">🔵</div>
            <div className="stat-value">{formatNumber(stats.graphNodes)}</div>
            <div className="stat-label">Graph Nodes</div>
          </div>
          <div className="stat-card">
            <div className="stat-icon">🔗</div>
            <div className="stat-value">{formatNumber(stats.graphRelationships)}</div>
            <div className="stat-label">Relationships</div>
          </div>
        </div>
      )}

      <div className="two-column">
        <div>
          <h3>🎯 Overview</h3>
          <ul>
            <li>Combines geographic data, demographics, and business attributes</li>
            <li>Builds a Neo4j knowledge graph for rich traversal and scoring</li>
            <li>Supports LLM-based enrichment for smarter categorization</li>
            <li>Spatial analytics using PostGIS and geospatial queries</li>
          </ul>
        </div>
        <div>
          <h3>👥 Team</h3>
          <ul>
            <li><strong>Spencer</strong> — Data engineering, pipelines</li>
            <li><strong>Faizan</strong> — Spatial analytics and PostGIS</li>
            <li><strong>Isa</strong> — Neo4j graph modeling and queries</li>
            <li><strong>Frank</strong> — Frontend and visualization</li>
          </ul>
        </div>
      </div>

      {stats?.lastUpdated && (
        <div className="info-footer">
          Last updated: {formatDate(stats.lastUpdated)}
        </div>
      )}
    </div>
  );
}

function DatabaseSection() {
  const { data: tables, loading, error, refetch } = useApi(() => dataService.getTables());

  if (loading) return <LoadingSpinner message="Loading database tables..." />;
  if (error) return <ErrorMessage error={error} onRetry={refetch} />;

  return (
    <div className="content-section fade-in">
      <h2>🗄️ Database &amp; Tables</h2>
      <p className="lede">
        High-level description of the tables used to construct the knowledge graph. This mirrors
        the JSON files and relational tables in the project.
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
              <td><code>{table.name}</code></td>
              <td><code>{table.source}</code></td>
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
      <h2>📚 Documentation</h2>
      <p className="lede">
        Project documentation, diagrams, and reference materials. These files describe the system
        architecture, data models, and operational procedures.
      </p>
      <ul className="bullet-list">
        <li>
          <code>docs/graph_model.drawio</code> — Entity and relationship diagram
        </li>
        <li>
          <code>README.md</code> — Project summary and goals
        </li>
        <li>
          <code>docker/README.md</code> — Docker setup and deployment guide
        </li>
      </ul>
    </div>
  );
}

function ExportsSection() {
  const { data: exports, loading, error, refetch } = useApi(() => dataService.getExports());

  if (loading) return <LoadingSpinner message="Loading export files..." />;
  if (error) return <ErrorMessage error={error} onRetry={refetch} />;

  return (
    <div className="content-section fade-in">
      <h2>📤 Data Exports</h2>
      <p className="lede">
        CSV exports used for downstream analytics and Neo4j loading. These files contain processed
        data ready for import into various systems.
      </p>
      <div className="exports-grid">
        {exports?.map((file) => (
          <div key={file.name} className="export-card">
            <div className="export-header">
              <span className="export-icon">📄</span>
              <code className="export-name">{file.name}</code>
            </div>
            <p className="export-description">{file.description}</p>
            <div className="export-meta">
              {file.size && <span>📦 {file.size}</span>}
              {file.rows && <span>📊 {formatNumber(file.rows)} rows</span>}
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
  const { data: notebooks, loading, error, refetch } = useApi(() => dataService.getNotebooks());

  if (loading) return <LoadingSpinner message="Loading notebooks..." />;
  if (error) return <ErrorMessage error={error} onRetry={refetch} />;

  return (
    <div className="content-section fade-in">
      <h2>📓 Jupyter Notebooks</h2>
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
                  {notebook.status === 'success' && '✅'}
                  {notebook.status === 'running' && '🔄'}
                  {notebook.status === 'error' && '❌'}
                  {' '}{notebook.status}
                </span>
              )}
            </div>
            <p className="notebook-description">{notebook.description}</p>
            {notebook.lastRun && (
              <div className="notebook-meta">
                Last run: {formatDate(notebook.lastRun)}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function ScriptsSection() {
  const { data: scripts, loading, error, refetch } = useApi(() => dataService.getScripts());

  if (loading) return <LoadingSpinner message="Loading scripts..." />;
  if (error) return <ErrorMessage error={error} onRetry={refetch} />;

  return (
    <div className="content-section fade-in">
      <h2>⚙️ ETL Scripts</h2>
      <p className="lede">
        SQL scripts for data pipeline, ETL operations, and analytics. These scripts define the core
        data transformations and schema.
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
              <td><code>{script.name}</code></td>
              <td>{script.description}</td>
              {script.lines && <td>{formatNumber(script.lines)}</td>}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function App() {
  const [active, setActive] = useState('dashboard');
  const [navOpen, setNavOpen] = useState(true);
  const [isTransitioning, setIsTransitioning] = useState(false);

  // Log navigation changes
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
    const sections = {
      dashboard: <Dashboard />,
      database: <DatabaseSection />,
      docs: <DocsSection />,
      exports: <ExportsSection />,
      notebooks: <NotebooksSection />,
      scripts: <ScriptsSection />,
    };

    return sections[active] || null;
  };

  return (
    <ErrorBoundary>
      <div className="app-root">
        <header className="top-bar">
          <div className="top-bar-title">
            {config.app.name}
            <span className="top-bar-version">v{config.app.version}</span>
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
              {navOpen ? '«' : '»'}
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
