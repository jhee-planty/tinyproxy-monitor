import React, { useState, useEffect } from 'react'
import StatusCard from '../components/StatusCard'
import StatsCard from '../components/StatsCard'
import RecentLogs from '../components/RecentLogs'
import './Dashboard.css'

const Dashboard = () => {
  const [processStatus, setProcessStatus] = useState(null)
  const [stats, setStats] = useState(null)
  const [recentLogs, setRecentLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [lastUpdate, setLastUpdate] = useState(null)

  // API Base URL
  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

  // 데이터 가져오기
  const fetchData = async () => {
    try {
      setError(null)
      
      // 병렬로 모든 데이터 가져오기
      const [statusRes, statsRes, logsRes] = await Promise.allSettled([
        fetch(`${API_URL}/api/process/status`),
        fetch(`${API_URL}/api/stats/summary`),
        fetch(`${API_URL}/api/logs/tail?lines=10`)
      ])

      // 프로세스 상태
      if (statusRes.status === 'fulfilled' && statusRes.value.ok) {
        const statusData = await statusRes.value.json()
        setProcessStatus(statusData)
      } else {
        console.error('Failed to fetch process status')
      }

      // 통계 정보
      if (statsRes.status === 'fulfilled' && statsRes.value.ok) {
        const statsData = await statsRes.value.json()
        setStats(statsData)
      } else {
        console.error('Failed to fetch stats')
      }

      // 최근 로그
      if (logsRes.status === 'fulfilled' && logsRes.value.ok) {
        const logsData = await logsRes.value.json()
        setRecentLogs(logsData.logs || [])
      } else {
        console.error('Failed to fetch logs')
      }

      setLastUpdate(new Date())
      setLoading(false)
    } catch (err) {
      console.error('Error fetching data:', err)
      setError('Failed to fetch data from server')
      setLoading(false)
    }
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
          <button onClick={handleRefresh} className="refresh-btn">
            🔄 Refresh
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

        {/* 최근 로그 */}
        <div className="grid-item grid-span-2">
          <RecentLogs logs={recentLogs} />
        </div>
      </div>
    </div>
  )
}

export default Dashboard