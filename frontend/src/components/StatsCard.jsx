import React from 'react'
import './StatsCard.css'

const StatsCard = ({ title, stats, type }) => {
  if (!stats) {
    return (
      <div className="stats-card">
        <h3>{title}</h3>
        <div className="stats-loading">Loading...</div>
      </div>
    )
  }

  const renderContent = () => {
    switch (type) {
      case 'connections':
        return (
          <>
            <div className="stats-main">
              <div className="stats-number">{stats.stats.opens}</div>
              <div className="stats-label">Active Connections</div>
            </div>
            <div className="stats-secondary">
              <div className="stats-item">
                <span className="item-label">Total:</span>
                <span className="item-value">{stats.total_connections}</span>
              </div>
              <div className="stats-item">
                <span className="item-label">Load:</span>
                <span className="item-value">{stats.current_load_ratio}%</span>
              </div>
            </div>
          </>
        )

      case 'requests':
        return (
          <>
            <div className="stats-main">
              <div className="stats-number">{stats.stats.requests.toLocaleString()}</div>
              <div className="stats-label">Total Requests</div>
            </div>
            <div className="stats-secondary">
              <div className="stats-item">
                <span className="item-label">Avg/min:</span>
                <span className="item-value">
                  {stats.stats.started_at 
                    ? Math.round(stats.stats.requests / 60)
                    : 'N/A'}
                </span>
              </div>
            </div>
          </>
        )

      case 'errors':
        const errorRate = stats.error_rate || 0
        const errorClass = errorRate > 5 ? 'error-high' : errorRate > 1 ? 'error-medium' : 'error-low'
        
        return (
          <>
            <div className="stats-main">
              <div className={`stats-number ${errorClass}`}>
                {stats.total_errors}
              </div>
              <div className="stats-label">Total Errors</div>
            </div>
            <div className="stats-secondary">
              <div className="stats-item">
                <span className="item-label">Bad:</span>
                <span className="item-value">{stats.stats.bad_connections}</span>
              </div>
              <div className="stats-item">
                <span className="item-label">Denied:</span>
                <span className="item-value">{stats.stats.denied}</span>
              </div>
              <div className="stats-item">
                <span className="item-label">Refused:</span>
                <span className="item-value">{stats.stats.refused}</span>
              </div>
              <div className="stats-item">
                <span className="item-label">Error Rate:</span>
                <span className={`item-value ${errorClass}`}>
                  {errorRate.toFixed(2)}%
                </span>
              </div>
            </div>
          </>
        )

      default:
        return null
    }
  }

  return (
    <div className="stats-card">
      <h3>{title}</h3>
      {renderContent()}
    </div>
  )
}

export default StatsCard