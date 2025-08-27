import React, { useState, useEffect } from 'react'
import StatusCard from '../components/StatusCard'
import StatsCard from '../components/StatsCard'
import SystemMetricsChart from '../components/SystemMetricsChart'
import ProxyMetricsChart from '../components/ProxyMetricsChart'
import './Dashboard.css'

const Dashboard = () => {
  const [processStatus, setProcessStatus] = useState(null)
  const [stats, setStats] = useState(null)
  const [systemMetrics, setSystemMetrics] = useState(null)
  const [performanceMetrics, setPerformanceMetrics] = useState(null)
  const [systemHistory, setSystemHistory] = useState([])
  const [last5minStats, setLast5minStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [lastUpdate, setLastUpdate] = useState(null)

  // Vite 프록시를 사용하도록 상대 경로 사용
  // const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
  
  // 인증 헤더 가져오기
  const getAuthHeaders = () => {
    const token = localStorage.getItem('access_token')
    if (token && token !== 'demo-token') {
      return {
        'Authorization': `Bearer ${token}`
      }
    }
    return {}
  }

  // 데이터 가져오기
  const fetchData = async () => {
    try {
      setError(null)
      
      // 병렬로 모든 데이터 가져오기
      const headers = getAuthHeaders()
      const [statusRes, statsRes, systemRes, perfRes, sysHistRes, last5minRes] = await Promise.allSettled([
        fetch(`/api/process/status`, { headers }),
        fetch(`/api/stats/summary`, { headers }),
        fetch(`/api/system/metrics/current`, { headers }),
        fetch(`/api/performance/metrics/current`, { headers }),
        fetch(`/api/system/metrics/history?seconds=300`, { headers }),
        fetch(`/api/performance/metrics/last5min`, { headers })
      ])

      // 프로세스 상태
      if (statusRes.status === 'fulfilled' && statusRes.value.ok) {
        const statusData = await statusRes.value.json()
        setProcessStatus(statusData)
      }

      // 통계 정보
      if (statsRes.status === 'fulfilled' && statsRes.value.ok) {
        const statsData = await statsRes.value.json()
        setStats(statsData)
      }

      // 시스템 메트릭
      if (systemRes.status === 'fulfilled' && systemRes.value.ok) {
        const systemData = await systemRes.value.json()
        setSystemMetrics(systemData)
      }

      // 성능 메트릭
      if (perfRes.status === 'fulfilled' && perfRes.value.ok) {
        const perfData = await perfRes.value.json()
        setPerformanceMetrics(perfData)
      }

      // 시스템 히스토리
      if (sysHistRes.status === 'fulfilled' && sysHistRes.value.ok) {
        const sysHistData = await sysHistRes.value.json()
        setSystemHistory(formatSystemHistory(sysHistData))
      }

      // 최근 5분 통계
      if (last5minRes.status === 'fulfilled' && last5minRes.value.ok) {
        const last5minData = await last5minRes.value.json()
        setLast5minStats(last5minData)
      }

      setLastUpdate(new Date())
      setLoading(false)
    } catch (err) {
      console.error('Error fetching data:', err)
      setError('Failed to fetch data from server')
      setLoading(false)
    }
  }

  // 히스토리 데이터 포맷팅
  const formatSystemHistory = (data) => {
    if (!Array.isArray(data)) return []
    return data.slice(-60).map(item => ({
      time: new Date(item.timestamp).toLocaleTimeString(),
      cpu: item.cpu?.percent || 0,
      memory: item.memory?.percent || 0,
      disk: item.disk?.percent || 0
    }))
  }

  // 초기 로드 및 자동 새로고침
  useEffect(() => {
    fetchData()
    
    // 30초마다 자동 새로고침
    const interval = setInterval(fetchData, 30000)
    
    return () => clearInterval(interval)
  }, [])

  // 수동 새로고침
  const handleRefresh = () => {
    setLoading(true)
    fetchData()
  }

  // 로딩 상태
  if (loading && !processStatus && !stats) {
    return (
      <div className="dashboard">
        <div className="loading">Loading dashboard...</div>
      </div>
    )
  }

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h2>System Overview</h2>
        <div className="header-actions">
          <button 
            onClick={handleRefresh} 
            className="refresh-btn"
            disabled={loading}
          >
            {loading ? (
              <>⟳ Refreshing...</>
            ) : (
              <>↻ Refresh</>
            )}
          </button>
          {lastUpdate && (
            <span className="last-update">
              Last updated: {lastUpdate.toLocaleTimeString()}
            </span>
          )}
        </div>
      </div>

      {error && (
        <div className="error-banner">
          ⚠️ {error}
        </div>
      )}

      <div className="dashboard-content">
        {/* 첫 번째 줄: 프로세스 상태와 주요 통계 */}
        <div className="status-row">
          <div className="status-item process-status">
            <StatusCard status={processStatus} compact={false} />
          </div>
          <div className="status-item">
            <StatsCard 
              title="Connections"
              stats={stats}
              type="connections"
              last5minStats={last5minStats}
              compact={false}
            />
          </div>
          <div className="status-item">
            <StatsCard 
              title="Requests"
              stats={stats}
              type="requests"
              processStatus={processStatus}
              last5minStats={last5minStats}
              compact={false}
            />
          </div>
          <div className="status-item">
            <StatsCard 
              title="Errors"
              stats={stats}
              type="errors"
              last5minStats={last5minStats}
              compact={false}
            />
          </div>
        </div>

        {/* 두 번째 줄: Proxy 메트릭 차트 */}
        <div className="proxy-metrics-row">
          <ProxyMetricsChart title="Proxy Performance Metrics (10 sec sampling, 5 min aggregation)" />
        </div>

        {/* 세 번째 줄: 시스템 메트릭과 차트 */}
        <div className="metrics-row">
          <div className="metrics-left">
            {systemMetrics && (
              <div className="system-stats">
                <div className="stat-box">
                  <span className="stat-label">CPU</span>
                  <span className="stat-value">{systemMetrics.cpu?.percent?.toFixed(1)}%</span>
                </div>
                <div className="stat-box">
                  <span className="stat-label">Memory</span>
                  <span className="stat-value">{systemMetrics.memory?.percent?.toFixed(1)}%</span>
                </div>
                <div className="stat-box">
                  <span className="stat-label">Disk</span>
                  <span className="stat-value">{systemMetrics.disk?.percent?.toFixed(1)}%</span>
                </div>
                {performanceMetrics && (
                  <div className="stat-box">
                    <span className="stat-label">Throughput</span>
                    <span className="stat-value">{performanceMetrics.throughput?.toFixed(1)} req/s</span>
                  </div>
                )}
              </div>
            )}
          </div>
          <div className="metrics-right">
            {systemHistory.length > 0 && (
              <SystemMetricsChart 
                data={systemHistory}
                title="System Resources (Last 5 min)"
                compact={true}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default Dashboard