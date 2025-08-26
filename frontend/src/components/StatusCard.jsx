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
    
    // systemd 시간 형식 파싱: "Tue 2025-08-26 14:14:45 KST"
    // 월 이름을 숫자로 변환
    const monthMap = {
      'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04',
      'May': '05', 'Jun': '06', 'Jul': '07', 'Aug': '08',
      'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12'
    }
    
    // 시간 문자열 파싱
    const parts = status.started_at.split(' ')
    if (parts.length >= 3) {
      // "Tue 2025-08-26 14:14:45 KST" 형식 처리
      const datePart = parts[1] // "2025-08-26"
      const timePart = parts[2] // "14:14:45"
      
      // ISO 형식으로 변환
      const isoString = `${datePart}T${timePart}`
      const start = new Date(isoString)
      
      if (isNaN(start.getTime())) {
        console.warn('Failed to parse start time:', status.started_at)
        return null
      }
      
      const now = new Date()
      const diff = now - start
      
      if (diff < 0) {
        return 'Just started'
      }
      
      const days = Math.floor(diff / (1000 * 60 * 60 * 24))
      const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60))
      const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60))
      
      if (days > 0) {
        return `${days}d ${hours}h ${minutes}m`
      } else if (hours > 0) {
        return `${hours}h ${minutes}m`
      } else {
        return `${minutes}m`
      }
    }
    
    return null
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