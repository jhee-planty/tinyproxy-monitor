import React from 'react'
import './LogViewer.css'

const LogViewer = ({ logs, autoScroll = true }) => {
  const containerRef = React.useRef(null)
  
  // 로그 레벨별 클래스명 반환
  const getLevelClass = (level) => {
    const levelLower = level?.toLowerCase() || 'info'
    return `level-${levelLower}`
  }
  
  // 타임스탬프 포맷팅
  const formatTimestamp = (timestamp) => {
    if (!timestamp) return ''
    const date = new Date(timestamp)
    return date.toLocaleTimeString('en-US', { 
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })
  }
  
  // 자동 스크롤
  React.useEffect(() => {
    if (autoScroll && containerRef.current && logs.length > 0) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight
    }
  }, [logs, autoScroll])
  
  if (logs.length === 0) {
    return (
      <div className="log-viewer-empty">
        <p>No logs to display</p>
        <p className="empty-hint">Waiting for logs...</p>
      </div>
    )
  }
  
  return (
    <div className="log-viewer" ref={containerRef}>
      <div className="log-list">
        {logs.map((log) => (
          <div 
            key={log.id || `${log.timestamp}-${Math.random()}`}
            className={`log-entry log-${log.level?.toLowerCase() || 'info'}`}
          >
            <span className="log-time">
              {formatTimestamp(log.timestamp)}
            </span>
            <span className={`log-level ${getLevelClass(log.level)}`}>
              {log.level || 'INFO'}
            </span>
            {log.pid > 0 && (
              <span className="log-pid">[{log.pid}]</span>
            )}
            <span className="log-msg">{log.message}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

export default LogViewer