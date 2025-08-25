import React, { useState, useEffect, useRef, useCallback } from 'react'
import LogViewer from '../components/LogViewer'
import LogFilters from '../components/LogFilters'
import './Logs.css'

const Logs = () => {
  // 로그 데이터 상태
  const [logs, setLogs] = useState([])
  const [filteredLogs, setFilteredLogs] = useState([])
  
  // 연결 상태
  const [isConnected, setIsConnected] = useState(false)
  const [isReconnecting, setIsReconnecting] = useState(false)
  const [connectionAttempts, setConnectionAttempts] = useState(0)
  
  // UI 상태
  const [isPaused, setIsPaused] = useState(false)
  const [autoScroll, setAutoScroll] = useState(true)
  const [error, setError] = useState(null)
  
  // 필터 상태
  const [filters, setFilters] = useState({
    level: 'INFO',
    search: '',
    realtime: true
  })
  
  // WebSocket 및 타이머 refs
  const wsRef = useRef(null)
  const reconnectTimeoutRef = useRef(null)
  const heartbeatIntervalRef = useRef(null)
  
  // 설정
  // Vite 프록시를 위해 상대 경로 사용
  const WS_URL = window.location.origin.replace('http://', 'ws://').replace('https://', 'wss://')
  const MAX_LOGS = 1000
  const MAX_RECONNECT_ATTEMPTS = 5
  const RECONNECT_DELAYS = [1000, 2000, 4000, 8000, 16000]
  
  // 로그 레벨 우선순위 (낮을수록 중요)
  const LOG_LEVEL_PRIORITY = {
    'CRITICAL': 0,
    'ERROR': 1,
    'WARNING': 2,
    'NOTICE': 3,
    'CONNECT': 4,
    'INFO': 5
  }
  
  // 로그 필터링 함수
  const filterLogs = useCallback((logsToFilter, currentFilters) => {
    let filtered = [...logsToFilter]
    
    // 레벨 필터링
    if (currentFilters.level) {
      const minPriority = LOG_LEVEL_PRIORITY[currentFilters.level] || 5
      filtered = filtered.filter(log => {
        const logPriority = LOG_LEVEL_PRIORITY[log.level] || 5
        return logPriority <= minPriority
      })
    }
    
    // 검색어 필터링
    if (currentFilters.search) {
      const searchLower = currentFilters.search.toLowerCase()
      filtered = filtered.filter(log => 
        log.message?.toLowerCase().includes(searchLower)
      )
    }
    
    return filtered
  }, [])
  
  // 초기 로그 로드
  const fetchInitialLogs = async () => {
    try {
      const response = await fetch(`/api/logs/tail?lines=100`)
      if (response.ok) {
        const data = await response.json()
        const logsWithIds = (data.logs || []).map((log, index) => ({
          ...log,
          id: `initial-${index}-${Date.now()}`
        }))
        setLogs(logsWithIds)
        setFilteredLogs(filterLogs(logsWithIds, filters))
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
      
      switch(message.type) {
        case 'realtime':
          if (!isPaused && filters.realtime) {
            const newLogs = (message.logs || []).map((log, index) => ({
              ...log,
              id: `rt-${Date.now()}-${index}`
            }))
            
            setLogs(prevLogs => {
              const combined = [...prevLogs, ...newLogs]
              const trimmed = combined.slice(-MAX_LOGS)
              
              // 필터링된 로그도 업데이트
              setFilteredLogs(filterLogs(trimmed, filters))
              
              return trimmed
            })
          }
          break
          
        case 'data':
          // 페이징 데이터 처리
          if (message.logs) {
            const dataLogs = message.logs.map((log, index) => ({
              ...log,
              id: `data-${Date.now()}-${index}`
            }))
            setLogs(dataLogs)
            setFilteredLogs(filterLogs(dataLogs, filters))
          }
          break
          
        case 'info':
          console.log('WebSocket info:', message.message)
          break
          
        case 'error':
          console.error('WebSocket error:', message.message || message.error)
          setError(message.message || message.error)
          break
          
        case 'ping':
          if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ action: 'ping' }))
          }
          break
          
        default:
          console.log('Unknown message type:', message.type)
      }
    } catch (err) {
      console.error('Error parsing WebSocket message:', err)
    }
  }, [isPaused, filters, filterLogs])
  
  // WebSocket 연결
  const connectWebSocket = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return
    }
    
    setIsReconnecting(true)
    
    try {
      if (wsRef.current) {
        wsRef.current.close()
      }
      
      const ws = new WebSocket(`${WS_URL}/api/ws/logs`)
      wsRef.current = ws
      
      ws.onopen = () => {
        console.log('WebSocket connected')
        setIsConnected(true)
        setIsReconnecting(false)
        setError(null)
        setConnectionAttempts(0)
        
        // 구독 시작 및 필터 설정
        ws.send(JSON.stringify({
          action: 'subscribe',
          level: filters.level,
          search: filters.search
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
  }, [WS_URL, filters, handleWebSocketMessage, connectionAttempts])
  
  // WebSocket 연결 해제
  const disconnectWebSocket = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }
    
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current)
      heartbeatIntervalRef.current = null
    }
    
    if (wsRef.current) {
      wsRef.current.close(1000, 'User disconnect')
      wsRef.current = null
    }
    
    setIsConnected(false)
    setIsReconnecting(false)
  }, [])
  
  // 필터 변경 처리
  const handleFilterChange = useCallback((newFilters) => {
    setFilters(newFilters)
    
    // 로컬 필터링 적용
    setFilteredLogs(filterLogs(logs, newFilters))
    
    // WebSocket에 필터 업데이트 전송
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        action: 'update_filter',
        level: newFilters.level,
        search: newFilters.search
      }))
      
      // 실시간 모드 변경 처리
      if (newFilters.realtime !== filters.realtime) {
        if (newFilters.realtime) {
          wsRef.current.send(JSON.stringify({ action: 'subscribe' }))
        } else {
          wsRef.current.send(JSON.stringify({ action: 'unsubscribe' }))
        }
      }
    }
  }, [logs, filters, filterLogs])
  
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
    setFilteredLogs([])
  }
  
  // 자동 스크롤 토글
  const toggleAutoScroll = () => {
    setAutoScroll(prev => !prev)
  }
  
  // 컴포넌트 마운트 시
  useEffect(() => {
    fetchInitialLogs()
    connectWebSocket()
    
    // Heartbeat 설정
    heartbeatIntervalRef.current = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ action: 'ping' }))
      }
    }, 30000)
    
    // cleanup 함수 - 컴포넌트 언마운트 시 호출
    return () => {
      console.log('Logs component unmounting, cleaning up...')
      disconnectWebSocket()
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps
  
  // 필터 변경 시 로그 재필터링
  useEffect(() => {
    setFilteredLogs(filterLogs(logs, filters))
  }, [logs, filters, filterLogs])
  
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
    <div className="logs-page">
      {/* 헤더 */}
      <div className="logs-header">
        <h2>Log Viewer</h2>
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
            
            <button 
              onClick={toggleAutoScroll}
              className={`btn ${autoScroll ? 'btn-info' : 'btn-secondary'}`}
            >
              {autoScroll ? '📍 Auto-scroll ON' : '📌 Auto-scroll OFF'}
            </button>
            
            <button onClick={clearLogs} className="btn btn-secondary">
              🗑️ Clear
            </button>
          </div>
          
          {/* 로그 카운터 */}
          <div className="log-counter">
            {filteredLogs.length} / {logs.length} logs
            {logs.length >= MAX_LOGS && ` (max ${MAX_LOGS})`}
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
      
      {/* 필터 컨트롤 */}
      <LogFilters 
        onFilterChange={handleFilterChange}
        currentFilters={filters}
        isConnected={isConnected}
      />
      
      {/* 로그 뷰어 */}
      <LogViewer 
        logs={filteredLogs}
        autoScroll={autoScroll}
      />
    </div>
  )
}

export default Logs