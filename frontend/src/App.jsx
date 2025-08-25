import React, { useState, useEffect } from 'react'
import Dashboard from './pages/Dashboard'
import Logs from './pages/Logs'
import Login from './pages/Login'
import './App.css'

function App() {
  const [currentPage, setCurrentPage] = useState('dashboard')
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [userInfo, setUserInfo] = useState(null)
  const [checkingAuth, setCheckingAuth] = useState(true)

  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

  // 초기 인증 상태 확인
  useEffect(() => {
    checkAuthStatus()
  }, [])

  const checkAuthStatus = async () => {
    try {
      // 먼저 인증이 활성화되어 있는지 확인
      const authCheckRes = await fetch(`${API_URL}/api/auth/check-auth`)
      const authCheck = await authCheckRes.json()
      
      if (!authCheck.auth_enabled) {
        // 인증이 비활성화된 경우 자동 로그인
        setIsAuthenticated(true)
        setUserInfo({ username: 'demo', is_admin: true })
        setCheckingAuth(false)
        return
      }

      // 저장된 토큰 확인
      const token = localStorage.getItem('access_token')
      const storedUserInfo = localStorage.getItem('user_info')
      
      if (token && storedUserInfo) {
        // 토큰 유효성 검증
        const response = await fetch(`${API_URL}/api/auth/me`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })
        
        if (response.ok) {
          setIsAuthenticated(true)
          setUserInfo(JSON.parse(storedUserInfo))
        } else {
          // 토큰이 만료되었거나 유효하지 않음
          handleLogout()
        }
      }
    } catch (error) {
      console.error('Auth check error:', error)
    } finally {
      setCheckingAuth(false)
    }
  }

  const handleLogin = (userInfo) => {
    setIsAuthenticated(true)
    setUserInfo(userInfo)
  }

  const handleLogout = () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('user_info')
    setIsAuthenticated(false)
    setUserInfo(null)
    setCurrentPage('dashboard')
  }

  // 인증 체크 중
  if (checkingAuth) {
    return (
      <div className="app-loading">
        <div className="loading-spinner">Loading...</div>
      </div>
    )
  }

  // 로그인 페이지
  if (!isAuthenticated) {
    return <Login onLogin={handleLogin} />
  }

  // 메인 앱
  return (
    <div className="app">
      <nav className="navbar">
        <div className="navbar-brand">
          <h1>Tinyproxy Monitor</h1>
        </div>
        <div className="navbar-menu">
          <button
            className={`nav-item ${currentPage === 'dashboard' ? 'active' : ''}`}
            onClick={() => setCurrentPage('dashboard')}
          >
            System Overview
          </button>
          <button
            className={`nav-item ${currentPage === 'logs' ? 'active' : ''}`}
            onClick={() => setCurrentPage('logs')}
          >
            Logs
          </button>
        </div>
        <div className="navbar-user">
          <span className="user-info">
            👤 {userInfo?.username}
            {userInfo?.is_admin && <span className="admin-badge">Admin</span>}
          </span>
          <button className="logout-btn" onClick={handleLogout}>
            Logout
          </button>
        </div>
      </nav>

      <main className="main-content">
        {currentPage === 'dashboard' && <Dashboard />}
        {currentPage === 'logs' && <Logs />}
      </main>
    </div>
  )
}

export default App
