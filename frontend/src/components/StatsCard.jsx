import React from 'react'
import './StatsCard.css'

const StatsCard = ({ title, stats, type, value, unit, processStatus, last5minStats, compact = false }) => {
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

  // 기존 proxy 통계 카드
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
                <span className="item-label">Last 5min avg:</span>
                <span className="item-value">
                  {last5minStats?.connections || 'N/A'}
                </span>
              </div>
              <div className="stats-item">
                <span className="item-label">Load:</span>
                <span className="item-value">{stats.current_load_ratio || 0}%</span>
              </div>
            </div>
          </>
        )

      case 'requests':
        // 평균 요청 수 계산
        const calculateAvgPerMinute = () => {
          if (!processStatus?.started_at || !processStatus.running) {
            return 'N/A'
          }
          
          // systemd 시간 형식 파싱: "Tue 2025-08-26 14:14:45 KST"
          const parts = processStatus.started_at.split(' ')
          if (parts.length >= 3) {
            const datePart = parts[1] // "2025-08-26"
            const timePart = parts[2] // "14:14:45"
            
            // ISO 형식으로 변환
            const isoString = `${datePart}T${timePart}`
            const start = new Date(isoString)
            
            if (isNaN(start.getTime())) {
              return 'N/A'
            }
            
            const now = new Date()
            const diffMs = now - start
            
            if (diffMs <= 0) {
              return 'N/A'
            }
            
            // 분 단위로 변환
            const diffMinutes = diffMs / (1000 * 60)
            
            if (diffMinutes < 1) {
              // 1분 미만이면 초당 요청 수로 표시
              const diffSeconds = diffMs / 1000
              const avgPerSecond = (stats.stats?.requests || 0) / diffSeconds
              return `${avgPerSecond.toFixed(1)}/s`
            }
            
            // 평균 요청 수/분 계산
            const avgPerMinute = (stats.stats?.requests || 0) / diffMinutes
            return avgPerMinute.toFixed(1)
          }
          
          return 'N/A'
        }
        
        return (
          <>
            <div className="stats-main">
              <div className="stats-number">{(stats.stats?.requests || 0).toLocaleString()}</div>
              <div className="stats-label">Total Requests</div>
            </div>
            <div className="stats-secondary">
              <div className="stats-item">
                <span className="item-label">Last 5min:</span>
                <span className="item-value">
                  {last5minStats?.requests || 'N/A'}
                </span>
              </div>
              <div className="stats-item">
                <span className="item-label">Avg/sec:</span>
                <span className="item-value">
                  {last5minStats?.avg_throughput || 'N/A'}
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
                <span className="item-label">Last 5min:</span>
                <span className="item-value">{last5minStats?.errors || 'N/A'}</span>
              </div>
              <div className="stats-item">
                <span className="item-label">Bad:</span>
                <span className="item-value">{stats.stats?.bad_connections || 0}</span>
              </div>
              <div className="stats-item">
                <span className="item-label">Denied:</span>
                <span className="item-value">{stats.stats?.denied || 0}</span>
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