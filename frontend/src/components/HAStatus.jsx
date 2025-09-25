import React, { useState, useEffect } from 'react'
import axios from 'axios'
import './HAStatus.css'

const HAStatus = ({ apiUrl = '/api', compact = false }) => {
  const [status, setStatus] = useState({
    state: 'UNKNOWN',
    has_vip: false,
    vip: 'N/A',
    hostname: '',
    timestamp: null
  })
  const [loading, setLoading] = useState(true)
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [refreshInterval, setRefreshInterval] = useState(5000)

  // 상태 가져오기
  const fetchStatus = async () => {
    try {
      setLoading(true)
      
      // 간단한 상태 먼저 가져오기
      const response = await axios.get(`${apiUrl}/ha/simple`)
      
      if (response.data) {
        setStatus(response.data)
      }
      
      // 토큰이 있으면 상세 정보 시도
      const token = localStorage.getItem('access_token')
      if (token && !compact) {
        try {
          const detailResponse = await axios.get(`${apiUrl}/ha/status`, {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          })
          
          if (detailResponse.data) {
            setStatus(detailResponse.data)
          }
        } catch (err) {
          // 상세 정보 실패는 무시
          console.log('Could not fetch detailed HA status')
        }
      }
      
    } catch (err) {
      console.error('Failed to fetch HA status:', err)
      setStatus({
        state: 'UNKNOWN',
        has_vip: false,
        vip: 'N/A',
        hostname: '',
        timestamp: new Date().toISOString()
      })
    } finally {
      setLoading(false)
    }
  }

  // 자동 새로고침
  useEffect(() => {
    fetchStatus()

    if (autoRefresh) {
      const interval = setInterval(fetchStatus, refreshInterval)
      return () => clearInterval(interval)
    }
  }, [autoRefresh, refreshInterval])

  const getStateClass = () => {
    switch (status.state) {
      case 'MASTER':
        return 'state-master'
      case 'BACKUP':
        return 'state-backup'
      case 'FAULT':
        return 'state-fault'
      default:
        return 'state-unknown'
    }
  }

  const getStateText = () => {
    switch (status.state) {
      case 'MASTER':
        return 'Master (Active)'
      case 'BACKUP':
        return 'Backup (Standby)'
      case 'FAULT':
        return 'Fault'
      default:
        return 'Unknown'
    }
  }

  // Compact 모드
  if (compact) {
    return (
      <div className="ha-status-compact">
        <span className={`ha-badge ${getStateClass()}`}>
          <span className="ha-dot"></span>
          {status.state}
        </span>
        {status.has_vip && (
          <span className="ha-vip-badge" title={`VIP: ${status.vip}`}>
            VIP
          </span>
        )}
      </div>
    )
  }

  // 전체 모드
  return (
    <div className="ha-status-card">
      <div className="ha-header">
        <h3>HA Status</h3>
        <span className={`ha-badge ${getStateClass()}`}>
          <span className="ha-dot"></span>
          {getStateText()}
        </span>
      </div>

      <div className="ha-details">
        <div className="ha-row">
          <span className="ha-label">State:</span>
          <span className="ha-value">
            {status.state}
            {status.has_vip && ' (VIP Active)'}
          </span>
        </div>

        {status.hostname && (
          <div className="ha-row">
            <span className="ha-label">Hostname:</span>
            <span className="ha-value">{status.hostname}</span>
          </div>
        )}

        <div className="ha-row">
          <span className="ha-label">Virtual IP:</span>
          <span className="ha-value">{status.vip}</span>
        </div>

        {status.config?.priority && (
          <div className="ha-row">
            <span className="ha-label">Priority:</span>
            <span className="ha-value">{status.config.priority}</span>
          </div>
        )}

        {status.config?.configured_state && (
          <div className="ha-row">
            <span className="ha-label">Configured:</span>
            <span className="ha-value">{status.config.configured_state}</span>
          </div>
        )}

        {status.timestamp && (
          <div className="ha-row">
            <span className="ha-label">Last Update:</span>
            <span className="ha-value">
              {new Date(status.timestamp).toLocaleTimeString()}
            </span>
          </div>
        )}
      </div>

      <div className="ha-controls">
        <label className="ha-checkbox">
          <input
            type="checkbox"
            checked={autoRefresh}
            onChange={(e) => setAutoRefresh(e.target.checked)}
          />
          <span>Auto refresh ({refreshInterval / 1000}s)</span>
        </label>
        
        <button 
          className="ha-refresh-btn"
          onClick={fetchStatus}
          disabled={loading}
        >
          {loading ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      {status.service?.recent_changes && status.service.recent_changes.length > 0 && (
        <details className="ha-events">
          <summary>Recent Events ({status.service.recent_changes.length})</summary>
          <div className="ha-event-list">
            {status.service.recent_changes.map((change, idx) => (
              <div key={idx} className="ha-event">
                <span className={`ha-event-state state-${change.state.toLowerCase()}`}>
                  {change.state}
                </span>
                <span className="ha-event-message">
                  {change.message?.substring(0, 100)}...
                </span>
              </div>
            ))}
          </div>
        </details>
      )}
    </div>
  )
}

// Header용 간단 배지
export const HAStatusBadge = ({ apiUrl = '/api' }) => {
  const [state, setState] = useState('')
  const [hasVip, setHasVip] = useState(false)

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const response = await axios.get(`${apiUrl}/ha/simple`)
        if (response.data) {
          setState(response.data.state)
          setHasVip(response.data.has_vip)
        }
      } catch (err) {
        // HA 기능이 없으면 표시하지 않음
        setState('')
      }
    }

    fetchStatus()
    const interval = setInterval(fetchStatus, 10000)
    return () => clearInterval(interval)
  }, [apiUrl])

  // MASTER일 때만 표시
  if (state === 'MASTER') {
    return <span style={{ 
      marginLeft: '8px',
      padding: '2px 6px',
      backgroundColor: '#28a745',
      color: 'white',
      borderRadius: '3px',
      fontSize: '0.75em',
      fontWeight: 'bold'
    }}>[MASTER]</span>
  }
  
  // BACKUP일 때 표시 (선택적)
  if (state === 'BACKUP') {
    return <span style={{ 
      marginLeft: '8px',
      padding: '2px 6px',
      backgroundColor: '#6c757d',
      color: 'white',
      borderRadius: '3px',
      fontSize: '0.75em',
      fontWeight: 'bold'
    }}>[BACKUP]</span>
  }

  // FAULT나 UNKNOWN은 표시하지 않음
  return null
}

export default HAStatus