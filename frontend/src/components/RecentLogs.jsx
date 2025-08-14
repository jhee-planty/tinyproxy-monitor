import React from 'react'
import './RecentLogs.css'

const RecentLogs = ({ logs }) => {
  // 로그 레벨별 색상
  const getLevelClass = (level) => {
    switch (level) {
      case 'CRITICAL':
        return 'log-critical'
      case 'ERROR':
        return 'log-error'
      case 'WARNING':
        return 'log-warning'
      case 'NOTICE':
        return 'log-notice'
      case 'CONNECT':
        return 'log-connect'
      case 'INFO':
        return 'log-info'
      default:
        return 'log-default'
    }
  }

  // 시간 포맷팅
  const formatTime = (timestamp) => {
    const date = new Date(timestamp)
    return date.toLocaleTimeString()
  }

  return (
    <div className="recent-logs-card">
      <div className="logs-header">
        <h3>Recent Logs</h3>
        <span className="logs-count">{logs.length} entries</span>
      </div>

      <div className="logs-container">
        {logs.length === 0 ? (
          <div className="logs-empty">No recent logs available</div>
        ) : (
          <div className="logs-list">
            {logs.map((log, index) => (
              <div key={index} className="log-entry">
                <div className="log-meta">
                  <span className="log-time">{formatTime(log.timestamp)}</span>
                  <span className={`log-level ${getLevelClass(log.level)}`}>
                    {log.level}
                  </span>
                  {log.pid > 0 && (
                    <span className="log-pid">PID: {log.pid}</span>
                  )}
                </div>
                <div className="log-message">{log.message}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="logs-footer">
        <a href="/logs" className="view-all-link">
          View all logs →
        </a>
      </div>
    </div>
  )
}

export default RecentLogs