import React, { useState } from 'react'
import './Login.css'

const Login = ({ onLogin }) => {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  
  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      // OAuth2 형식으로 전송
      const formData = new URLSearchParams()
      formData.append('username', username)
      formData.append('password', password)

      const response = await fetch(`${API_URL}/api/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: formData
      })

      const data = await response.json()

      if (response.ok) {
        // 토큰 저장
        localStorage.setItem('access_token', data.access_token)
        localStorage.setItem('user_info', JSON.stringify(data.user_info))
        
        // 부모 컴포넌트에 로그인 성공 알림
        onLogin(data.user_info)
      } else {
        setError(data.detail || 'Login failed')
        
        // root 계정 차단 메시지 처리
        if (data.detail?.includes('not allowed')) {
          setError('This account is not allowed to login for security reasons.')
        }
      }
    } catch (err) {
      console.error('Login error:', err)
      setError('Failed to connect to server')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-container">
      <div className="login-box">
        <div className="login-header">
          <h1>Tinyproxy Monitor</h1>
          <p>Linux System Authentication</p>
        </div>
        
        <form onSubmit={handleSubmit} className="login-form">
          {error && (
            <div className="error-message">
              ⚠️ {error}
            </div>
          )}
          
          <div className="form-group">
            <label htmlFor="username">Username</label>
            <input
              type="text"
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Enter Linux username"
              required
              disabled={loading}
              autoComplete="username"
            />
          </div>
          
          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter password"
              required
              disabled={loading}
              autoComplete="current-password"
            />
          </div>
          
          <button 
            type="submit" 
            className="login-button"
            disabled={loading}
          >
            {loading ? 'Logging in...' : 'Login'}
          </button>
        </form>
        
        <div className="login-footer">
          <p className="security-note">
            🔒 Use your Linux system account credentials<br/>
            <small>Root account is disabled for security</small>
          </p>
        </div>
      </div>
    </div>
  )
}

export default Login
