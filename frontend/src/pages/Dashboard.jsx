import React, { useState, useEffect } from 'react'
import StatusCard from '../components/StatusCard'
import StatsCard from '../components/StatsCard'
import RecentLogs from '../components/RecentLogs'
import SystemMetricsChart from '../components/SystemMetricsChart'
import PerformanceChart from '../components/PerformanceChart'
import './Dashboard.css'

const Dashboard = () => {
  const [processStatus, setProcessStatus] = useState(null)
  const [stats, setStats] = useState(null)
  const [recentLogs, setRecentLogs] = useState([])
  const [systemMetrics, setSystemMetrics] = useState(null)
  const [performanceMetrics, setPerformanceMetrics] = useState(null)
  const [systemHistory, setSystemHistory] = useState([])
  const [performanceHistory, setPerformanceHistory] = useState([])
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
      const [statusRes, statsRes, logsRes, systemRes, perfRes, sysHistRes, perfHistRes] = await Promise.allSettled([
        fetch(`/api/process/status`, { headers }),
        fetch(`/api/stats/summary`, { headers }),
        fetch(`/api/logs/tail?lines=10`, { headers }),
        fetch(`/api/system/metrics/current`, { headers }),
        fetch(`/api/performance/metrics/current`, { headers }),
        fetch(`/api/system/metrics/history?seconds=300`, { headers }),
        fetch(`/api/performance/metrics/history?seconds=300`, { headers })
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

      // 최근 로그
      if (logsRes.status === 'fulfilled' && logsRes.value.ok) {
        const logsData = await logsRes.value.json()
        setRecentLogs(logsData.logs || [])
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

      // 성능 히스토리
      if (perfHistRes.status === 'fulfilled' && perfHistRes.value.ok) {
        const perfHistData = await perfHistRes.value.json()
        setPerformanceHistory(formatPerformanceHistory(perfHistData))
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

  const formatPerformanceHistory = (data) => {
    if (!Array.isArray(data)) return []
    return data.slice(-60).map(item => ({
      time: new Date(item.timestamp).toLocaleTimeString(),
      throughput: item.throughput || 0,
      errorRate: item.error_rate || 0,
      p95: item.latency?.p95 || 0
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

      <div className="dashboard-grid">
        {/* 프로세스 상태 카드 */}
        <div className="grid-item">
          <StatusCard status={processStatus} />
        </div>

        {/* 통계 카드들 */}
        <div className="grid-item">
          <StatsCard 
            title="Connections"
            stats={stats}
            type="connections"
          />
        </div>

        <div className="grid-item">
          <StatsCard 
            title="Requests"
            stats={stats}
            type="requests"
          />
        </div>

        <div className="grid-item">
          <StatsCard 
            title="Errors"
            stats={stats}
            type="errors"
          />
        </div>

        {/* 시스템 메트릭 카드 - 새로 추가 */}
        {systemMetrics && (
          <>
            <div className="grid-item">
              <StatsCard 
                title="CPU Usage"
                value={systemMetrics.cpu?.percent?.toFixed(1)}
                unit="%"
                type="system"
              />
            </div>
            <div className="grid-item">
              <StatsCard 
                title="Memory Usage"
                value={systemMetrics.memory?.percent?.toFixed(1)}
                unit="%"
                type="system"
              />
            </div>
            <div className="grid-item">
              <StatsCard 
                title="Disk Usage"
                value={systemMetrics.disk?.percent?.toFixed(1)}
                unit="%"
                type="system"
              />
            </div>
          </>
        )}

        {/* 성능 메트릭 카드 - 새로 추가 */}
        {performanceMetrics && (
          <>
            <div className="grid-item">
              <StatsCard 
                title="Throughput"
                value={performanceMetrics.throughput?.toFixed(1)}
                unit="req/s"
                type="performance"
              />
            </div>
            <div className="grid-item">
              <StatsCard 
                title="P95 Latency"
                value={performanceMetrics.latency?.p95?.toFixed(0)}
                unit="ms"
                type="performance"
              />
            </div>
          </>
        )}

        {/* 차트 섹션 - 새로 추가 */}
        {systemHistory.length > 0 && (
          <div className="grid-item grid-span-2">
            <SystemMetricsChart 
              data={systemHistory}
              title="System Resources (Last 5 min)"
            />
          </div>
        )}

        {performanceHistory.length > 0 && (
          <div className="grid-item grid-span-2">
            <PerformanceChart 
              data={performanceHistory}
              title="Performance Metrics (Last 5 min)"
            />
          </div>
        )}

        {/* 최근 로그 */}
        <div className="grid-item grid-span-2">
          <RecentLogs logs={recentLogs} />
        </div>
      </div>
    </div>
  )
}

export default Dashboard