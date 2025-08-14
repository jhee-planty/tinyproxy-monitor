import React, { useState, useEffect, useRef, useCallback } from 'react'
import './Logs.css'

const Logs = () => {
  // 상태 관리
  const [logs, setLogs] = useState([])
  const [isConnected, setIsConnected] = useState(false)
  const [isReconnecting, setIsReconnecting] = useState(false)
  const [isPaused, setIsPaused] = useState(false)
  const [error, setError] = useState(null)
  const [connectionAttempts, setConnectionAttempts] = useState(0)
  
  // WebSocket 및 타이머 refs
  const wsRef = useRef(null)
  const reconnectTimeoutRef = useRef(null)
  const reconnectIntervalRef = useRef(null)
  const logsContainerRef = useRef(null)
  const autoScrollRef = useRef(true)
  
  // 설정
  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
  const WS_URL = API_URL.replace('http://', 'ws://').replace('https://', 'wss://')
  const MAX_LOGS = 1000 // 메모리 효율을 위한 최대 로그 수
  const MAX_RECONNECT_ATTEMPTS = 5
  const RECONNECT_DELAYS = [1000, 2000, 4000, 8000, 16000] // 지수 백오프

  // 초기 로그 로드
  const fetchInitialLogs = async () => {
    try {
      const response = await fetch(`${API_URL}/api/logs/tail?lines=100`)
      if (response.ok) {
        const data = await response.json()
        setLogs(data.logs || [])
        setError(null)
      } else {
        throw new Error('Failed to fetch initial logs')
      }
    } catch (err) {
      console.error('Error fetching initial logs:', err)
      setError('Failed to load initial logs')
    }
  }

  // WebSocket 메시지 처리
  const handleWebSocketMessage = useCallback((event) => {
    try {
      const message = JSON.parse(event.data)
      
      if (message.type === 'log' && !isPaused) {
        const newLog = {
          ...message.data,
          id: `${Date.now()}-${Math.random()}` // 고유 ID 생성
        }
        
        setLogs(prevLogs => {
          // 최대 로그 수 제한
          const updatedLogs = [...prevLogs, newLog]
          if (updatedLogs.length > MAX_LOGS) {
            return updatedLogs.slice(-MAX_LOGS)
          }
          return updatedLogs
        })
        
        // 자동 스크롤
        if (autoScrollRef.current && logsContainerRef.current) {
          setTimeout(() => {
            logsContainerRef.current?.scrollTo({
              top: logsContainerRef.current.scrollHeight,
              behavior: 'smooth'
            })
          }, 100)
        }
      } else if (message.type === 'error') {
        console.error('WebSocket error message:', message.error)
        setError(message.error)
      } else if (message.type === 'ping') {
        // 서버 ping에 pong 응답
        if (wsRef.current?.readyState === WebSocket.OPEN) {
          wsRef.current.send(JSON.stringify({ type: 'pong' }))
        }
      }
    } catch (err) {
      console.error('Error parsing WebSocket message:', err)
    }
  }, [isPaused])

  // WebSocket 연결
  const connectWebSocket = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return // 이미 연결됨
    }

    setIsReconnecting(true)
    
    try {
      // 기존 연결 정리
      if (wsRef.current) {
        wsRef.current.close()
      }

      // 새 WebSocket 연결
      const ws = new WebSocket(`${WS_URL}/ws/logs`)
      wsRef.current = ws

      ws.onopen = () => {
        console.log('WebSocket connected')
        setIsConnected(true)
        setIsReconnecting(false)
        setError(null)
        setConnectionAttempts(0)
        
        // 초기 설정 전송
        ws.send(JSON.stringify({
          type: 'subscribe',
          filters: {
            level: null,
            search: null
          }
        }))
      }

      ws.onmessage = handleWebSocketMessage

      ws.onerror = (event) => {
        console.error('WebSocket error:', event)
        setError('WebSocket connection error')
      }

      ws.onclose = (event) => {
        console.log('WebSocket disconnected:', event.code, event.reason)
        setIsConnected(false)
        wsRef.current = null
        
        // 정상 종료가 아닌 경우 재연결 시도
        if (!event.wasClean && connectionAttempts < MAX_RECONNECT_ATTEMPTS) {
          const delay = RECONNECT_DELAYS[Math.min(connectionAttempts, RECONNECT_DELAYS.length - 1)]
          setConnectionAttempts(prev => prev + 1)
          
          console.log(`Reconnecting in ${delay}ms... (attempt ${connectionAttempts + 1}/${MAX_RECONNECT_ATTEMPTS})`)
          
          reconnectTimeoutRef.current = setTimeout(() => {
            connectWebSocket()
          }, delay)
        } else if (connectionAttempts >= MAX_RECONNECT_ATTEMPTS) {
          setError('Failed to reconnect after multiple attempts')
          setIsReconnecting(false)
        }
      }
    } catch (err) {
      console.error('Error creating WebSocket:', err)
      setError('Failed to establish WebSocket connection')
      setIsReconnecting(false)
    }
  }, [WS_URL, handleWebSocketMessage, connectionAttempts])

  // WebSocket 연결 해제
  const disconnectWebSocket = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }
    
    if (reconnectIntervalRef.current) {
      clearInterval(reconnectIntervalRef.current)
      reconnectIntervalRef.current = null
    }
    
    if (wsRef.current) {
      wsRef.current.close(1000, 'User disconnect')
      wsRef.current = null
    }
    
    setIsConnected(false)
    setIsReconnecting(false)
  }, [])

  // 수동 재연결
  const handleReconnect = () => {
    setConnectionAttempts(0)
    connectWebSocket()
  }

  // 일시정지/재개 토글
  const togglePause = () => {
    setIsPaused(prev => !prev)
  }

  // 로그 지우기
  const clearLogs = () => {
    setLogs([])
  }

  // 자동 스크롤 감지
  const handleScroll = () => {
    if (!logsContainerRef.current) return
    
    const { scrollTop, scrollHeight, clientHeight } = logsContainerRef.current
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 50
    autoScrollRef.current = isAtBottom
  }

  // 컴포넌트 마운트 시
  useEffect(() => {
    fetchInitialLogs()
    connectWebSocket()
    
    // Heartbeat 설정 (30초마다)
    reconnectIntervalRef.current = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'ping' }))
      }
    }, 30000)
    
    // cleanup
    return () => {
      disconnectWebSocket()
    }
  }, []) // 의도적으로 빈 의존성 배열 사용

  // 연결 상태 표시
  const getConnectionStatus = () => {
    if (isConnected) {
      return { text: 'Connected', className: 'status-connected' }
    } else if (isReconnecting) {
      return { text: `Reconnecting... (${connectionAttempts}/${MAX_RECONNECT_ATTEMPTS})`, className: 'status-reconnecting' }
    } else {
      return { text: 'Disconnected', className: 'status-disconnected' }
    }
  }

  const connectionStatus = getConnectionStatus()

  return (
    <div className="logs">
      {/* 헤더 */}
      <div className="logs-header">
        <h2>Real-time Logs</h2>
        <div className="header-controls">
          {/* 연결 상태 */}
          <div className={`connection-status ${connectionStatus.className}`}>
            <span className="status-dot"></span>
            {connectionStatus.text}
          </div>

          {/* 컨트롤 버튼들 */}
          <div className="control-buttons">
            {!isConnected && !isReconnecting && (
              <button onClick={handleReconnect} className="btn btn-primary">
                🔄 Reconnect
              </button>
            )}
            
            <button 
              onClick={togglePause} 
              className={`btn ${isPaused ? 'btn-success' : 'btn-warning'}`}
              disabled={!isConnected}
            >
              {isPaused ? '▶️ Resume' : '⏸️ Pause'}
            </button>
            
            <button onClick={clearLogs} className="btn btn-secondary">
              🗑️ Clear
            </button>
          </div>

          {/* 로그 카운터 */}
          <div className="log-counter">
            {logs.length} logs {logs.length >= MAX_LOGS && `(max ${MAX_LOGS})`}
          </div>
        </div>
      </div>

      {/* 에러 메시지 */}
      {error && (
        <div className="error-banner">
          ⚠️ {error}
        </div>
      )}

      {/* 일시정지 알림 */}
      {isPaused && (
        <div className="pause-banner">
          ⏸️ Log streaming is paused. Click Resume to continue receiving logs.
        </div>
      )}

      {/* 로그 컨테이너 */}
      <div 
        className="logs-container" 
        ref={logsContainerRef}
        onScroll={handleScroll}
      >
        {logs.length === 0 ? (
          <div className="no-logs">
            <p>No logs to display</p>
            <p className="no-logs-hint">
              {isConnected ? 'Waiting for new logs...' : 'Connect to start receiving logs'}
            </p>
          </div>
        ) : (
          <div className="logs-list">
            {logs.map((log) => (
              <div 
                key={log.id || `${log.timestamp}-${Math.random()}`}
                className={`log-entry log-${log.level?.toLowerCase() || 'info'}`}
              >
                <span className="log-timestamp">{log.timestamp}</span>
                <span className={`log-level level-${log.level?.toLowerCase() || 'info'}`}>
                  {log.level || 'INFO'}
                </span>
                <span className="log-message">{log.message}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 하단 정보 */}
      <div className="logs-footer">
        <div className="footer-info">
          {autoScrollRef.current ? (
            <span className="auto-scroll-indicator">📍 Auto-scrolling enabled</span>
          ) : (
            <span className="auto-scroll-indicator inactive">📌 Auto-scrolling disabled (scroll to bottom to enable)</span>
          )}
        </div>
      </div>
    </div>
  )
}

export default Logs