import React from 'react'
import './StatusCard.css'

const StatusCard = ({ status, compact = false }) => {
  if (!status) {
    return (
      <div className="status-card">
        <h3>Process Status</h3>
        <div className="status-loading">Loading...</div>
      </div>
    )
  }

  const isRunning = status.running
  const statusClass = isRunning ? 'status-running' : 'status-stopped'
  const statusText = isRunning ? 'Running' : 'Stopped'

  // Uptime 계산 (시작 시간이 있을 경우)
  const calculateUptime = () => {
    if (!status.started_at || !isRunning) return null
    
    const start = new Date(status.started_at)
    const now = new Date()
    const diff = now - start
    
    const hours = Math.floor(diff / (1000 * 60 * 60))
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60))
    
    if (hours > 24) {
      const days = Math.floor(hours / 24)
      return `${days}d ${hours % 24}h`
    }
    return `${hours}h ${minutes}m`
  }

  const uptime = calculateUptime()

  if (compact) {
    return (
      <div className="status-card compact">
        <div className="status-header">
          <h3>Process Status</h3>
          <span className={`status-badge ${statusClass}`}>
            <span className="status-dot"></span>
            {statusText}
          </span>
        </div>
        <div className="status-details">
          <div className="status-row">
            <span className="status-label">PID:</span>
            <span className="status-value">{status.pid > 0 ? status.pid : '-'}</span>
          </div>
          {uptime && (
            <div className="status-row">
              <span className="status-label">Uptime:</span>
              <span className="status-value">{uptime}</span>
            </div>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="status-card">
      <div className="status-header">
        <h3>Process Status</h3>
        <span className={`status-badge ${statusClass}`}>
          <span className="status-dot"></span>
          {statusText}
        </span>
      </div>

      <div className="status-details">
        <div className="status-row">
          <span className="status-label">Service:</span>
          <span className="status-value">{status.service}</span>
        </div>

        <div className="status-row">
          <span className="status-label">State:</span>
          <span className="status-value">
            {status.active_state} / {status.sub_state}
          </span>
        </div>

        {status.pid > 0 && (
          <div className="status-row">
            <span className="status-label">PID:</span>
            <span className="status-value">{status.pid}</span>
          </div>
        )}

        {status.memory_mb && (
          <div className="status-row">
            <span className="status-label">Memory:</span>
            <span className="status-value">{status.memory_mb} MB</span>
          </div>
        )}

        {uptime && (
          <div className="status-row">
            <span className="status-label">Uptime:</span>
            <span className="status-value">{uptime}</span>
          </div>
        )}

        {status.restart_count !== undefined && (
          <div className="status-row">
            <span className="status-label">Restarts:</span>
            <span className="status-value">{status.restart_count}</span>
          </div>
        )}
      </div>

      {status.status_output && (
        <details className="status-output">
          <summary>System Status</summary>
          <pre>{status.status_output}</pre>
        </details>
      )}
    </div>
  )
}

export default StatusCard