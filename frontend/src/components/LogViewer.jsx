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
// ...existing code...
const formatTimestamp = (timestamp) => {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  // 년-월-일 시:분:초 포맷
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hour = String(date.getHours()).padStart(2, '0')
  const minute = String(date.getMinutes()).padStart(2, '0')
  const second = String(date.getSeconds()).padStart(2, '0')
  return `${year}-${month}-${day} ${hour}:${minute}:${second}`
}
// ...existing code...
  
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