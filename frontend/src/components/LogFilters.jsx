import React, { useState } from 'react'
import './LogFilters.css'

const LogFilters = ({ 
  onFilterChange, 
  currentFilters = {},
  isConnected = false 
}) => {
  const [filters, setFilters] = useState({
    level: currentFilters.level || 'INFO',
    search: currentFilters.search || '',
    realtime: currentFilters.realtime !== false
  })
  
  // 로그 레벨 옵션
  const logLevels = [
    { value: 'CRITICAL', label: 'Critical', color: '#dc2626' },
    { value: 'ERROR', label: 'Error', color: '#ef4444' },
    { value: 'WARNING', label: 'Warning', color: '#f59e0b' },
    { value: 'NOTICE', label: 'Notice', color: '#3b82f6' },
    { value: 'CONNECT', label: 'Connect', color: '#10b981' },
    { value: 'INFO', label: 'Info', color: '#6b7280' }
  ]
  
  // 레벨 변경 처리
  const handleLevelChange = (e) => {
    const newFilters = { ...filters, level: e.target.value }
    setFilters(newFilters)
    onFilterChange(newFilters)
  }
  
  // 검색어 변경 처리
  const handleSearchChange = (e) => {
    const newFilters = { ...filters, search: e.target.value }
    setFilters(newFilters)
  }
  
  // 검색 실행 (Enter 키 또는 버튼 클릭)
  const handleSearchSubmit = (e) => {
    e.preventDefault()
    onFilterChange(filters)
  }
  
  // 실시간 모드 토글
  const handleRealtimeToggle = () => {
    const newFilters = { ...filters, realtime: !filters.realtime }
    setFilters(newFilters)
    onFilterChange(newFilters)
  }
  
  // 필터 초기화
  const handleReset = () => {
    const defaultFilters = {
      level: 'INFO',
      search: '',
      realtime: true
    }
    setFilters(defaultFilters)
    onFilterChange(defaultFilters)
  }
  
  return (
    <div className="log-filters">
      <div className="filter-group">
        <label className="filter-label">Log Level</label>
        <select 
          className="filter-select"
          value={filters.level}
          onChange={handleLevelChange}
          disabled={!isConnected}
        >
          {logLevels.map(level => (
            <option key={level.value} value={level.value}>
              {level.label}
            </option>
          ))}
        </select>
      </div>
      
      <div className="filter-group">
        <label className="filter-label">Search</label>
        <form onSubmit={handleSearchSubmit} className="search-form">
          <input
            type="text"
            className="filter-input"
            placeholder="Search in logs..."
            value={filters.search}
            onChange={handleSearchChange}
            disabled={!isConnected}
          />
          <button 
            type="submit" 
            className="search-btn"
            disabled={!isConnected}
          >
            🔍
          </button>
        </form>
      </div>
      
      <div className="filter-group">
        <label className="filter-label">Mode</label>
        <button
          className={`mode-toggle ${filters.realtime ? 'active' : ''}`}
          onClick={handleRealtimeToggle}
          disabled={!isConnected}
        >
          {filters.realtime ? '⚡ Realtime' : '📄 Static'}
        </button>
      </div>
      
      <div className="filter-group">
        <button 
          className="reset-btn"
          onClick={handleReset}
          disabled={!isConnected}
        >
          🔄 Reset Filters
        </button>
      </div>
      
      {/* 현재 필터 상태 표시 */}
      <div className="filter-status">
        <span className="status-item">
          Level: <strong>{filters.level}</strong>
        </span>
        {filters.search && (
          <span className="status-item">
            Search: <strong>"{filters.search}"</strong>
          </span>
        )}
        <span className="status-item">
          Mode: <strong>{filters.realtime ? 'Realtime' : 'Static'}</strong>
        </span>
      </div>
    </div>
  )
}

export default LogFilters