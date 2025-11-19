/**
 * Debug Panel Component
 * Shows debug information and controls (only in development)
 */

import { useState } from 'react';
import config from '../config';
import { getDebugInfo, copyToClipboard, logger } from '../utils/debug';

const DebugPanel = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [debugInfo] = useState(getDebugInfo());

  if (!config.features.enableDebug) {
    return null;
  }

  const handleCopyDebugInfo = () => {
    const info = JSON.stringify(debugInfo, null, 2);
    copyToClipboard(info);
  };

  const handleClearConsole = () => {
    console.clear();
    logger.info('Console cleared');
  };

  const handleReloadPage = () => {
    window.location.reload();
  };

  return (
    <>
      <button
        className="debug-toggle"
        onClick={() => setIsOpen(!isOpen)}
        title="Toggle debug panel"
      >
        DBG
      </button>

      {isOpen && (
        <div className="debug-panel">
          <div className="debug-header">
            <h3>Debug Panel</h3>
            <button onClick={() => setIsOpen(false)} className="debug-close">
              ×
            </button>
          </div>

          <div className="debug-content">
            <div className="debug-section">
              <h4>Configuration</h4>
              <div className="debug-info">
                <div className="debug-row">
                  <span className="debug-label">API Base URL:</span>
                  <span className="debug-value">{config.api.baseURL}</span>
                </div>
                <div className="debug-row">
                  <span className="debug-label">Mock Data:</span>
                  <span className="debug-value">
                    {config.features.enableMockData ? 'Enabled' : 'Disabled'}
                  </span>
                </div>
                <div className="debug-row">
                  <span className="debug-label">App Version:</span>
                  <span className="debug-value">{config.app.version}</span>
                </div>
              </div>
            </div>

            <div className="debug-section">
              <h4>Performance</h4>
              <div className="debug-info">
                {debugInfo.performance.memory !== 'Not available' ? (
                  <>
                    <div className="debug-row">
                      <span className="debug-label">Memory Used:</span>
                      <span className="debug-value">
                        {debugInfo.performance.memory.used}
                      </span>
                    </div>
                    <div className="debug-row">
                      <span className="debug-label">Memory Total:</span>
                      <span className="debug-value">
                        {debugInfo.performance.memory.total}
                      </span>
                    </div>
                  </>
                ) : (
                  <div className="debug-row">
                    <span className="debug-value">Memory info not available</span>
                  </div>
                )}
              </div>
            </div>

            <div className="debug-section">
              <h4>Viewport</h4>
              <div className="debug-info">
                <div className="debug-row">
                  <span className="debug-label">Width:</span>
                  <span className="debug-value">
                    {debugInfo.viewport.width}
                    px
                  </span>
                </div>
                <div className="debug-row">
                  <span className="debug-label">Height:</span>
                  <span className="debug-value">
                    {debugInfo.viewport.height}
                    px
                  </span>
                </div>
              </div>
            </div>

            <div className="debug-section">
              <h4>Actions</h4>
              <div className="debug-actions">
                <button onClick={handleCopyDebugInfo} className="debug-button">
                  Copy debug info
                </button>
                <button onClick={handleClearConsole} className="debug-button">
                  Clear console
                </button>
                <button onClick={handleReloadPage} className="debug-button">
                  Reload page
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default DebugPanel;

