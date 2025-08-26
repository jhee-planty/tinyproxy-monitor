import React from 'react'
import './StatsCard.css'

const StatsCard = ({ title, stats, type, value, unit, compact = false }) => {
  // Compact mode for status row
  if (compact && stats) {
    const cardClass = `stats-card compact ${type}-card`
    
    switch (type) {
      case 'connections':
        return (
          <div className={cardClass}>
            <h3>{title}</h3>
            <div className="stats-main">
              <div className="stats-number">{stats.stats?.opens || 0}</div>
              <div className="stats-label">Active</div>
            </div>
          </div>
        )
      
      case 'requests':
        return (
          <div className={cardClass}>
            <h3>{title}</h3>
            <div className="stats-main">
              <div className="stats-number">{(stats.stats?.requests || 0).toLocaleString()}</div>
              <div className="stats-label">Total</div>
            </div>
          </div>
        )
      
      case 'errors':
        const errorRate = stats.error_rate || 0
        const errorClass = errorRate > 5 ? 'error-high' : errorRate > 1 ? 'error-medium' : 'error-low'
        return (
          <div className={cardClass}>
            <h3>{title}</h3>
            <div className="stats-main">
              <div className={`stats-number ${errorClass}`}>
                {stats.total_errors || 0}
              </div>
              <div className="stats-label">{errorRate.toFixed(1)}%</div>
            </div>
          </div>
        )
      
      default:
        return null
    }
  }
  
  // 새로운 간단한 메트릭 카드 (시스템, 성능 메트릭용)
  if (type === 'system' || type === 'performance') {
    const cardClass = `stats-card ${type}-card ${compact ? 'compact' : ''}`
    return (
      <div className={cardClass}>
        <h3>{title}</h3>
        <div className="stats-main">
          <div className="stats-number">
            {value || '0'}
            {unit && <span className="stats-unit">{unit}</span>}
          </div>
        </div>
      </div>
    )
  }

  // 기존 Tinyproxy 통계 카드
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
              <div className="stats-number">{stats.stats?.opens || 0}</div>
              <div className="stats-label">Active Connections</div>
            </div>
            <div className="stats-secondary">
              <div className="stats-item">
                <span className="item-label">Total:</span>
                <span className="item-value">{stats.total_connections || 0}</span>
              </div>
              <div className="stats-item">
                <span className="item-label">Load:</span>
                <span className="item-value">{stats.current_load_ratio || 0}%</span>
              </div>
            </div>
          </>
        )

      case 'requests':
        return (
          <>
            <div className="stats-main">
              <div className="stats-number">{(stats.stats?.requests || 0).toLocaleString()}</div>
              <div className="stats-label">Total Requests</div>
            </div>
            <div className="stats-secondary">
              <div className="stats-item">
                <span className="item-label">Avg/min:</span>
                <span className="item-value">
                  {stats.stats?.started_at 
                    ? Math.round((stats.stats?.requests || 0) / 60)
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
                {stats.total_errors || 0}
              </div>
              <div className="stats-label">Total Errors</div>
            </div>
            <div className="stats-secondary">
              <div className="stats-item">
                <span className="item-label">Bad:</span>
                <span className="item-value">{stats.stats?.bad_connections || 0}</span>
              </div>
              <div className="stats-item">
                <span className="item-label">Denied:</span>
                <span className="item-value">{stats.stats?.denied || 0}</span>
              </div>
              <div className="stats-item">
                <span className="item-label">Refused:</span>
                <span className="item-value">{stats.stats?.refused || 0}</span>
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