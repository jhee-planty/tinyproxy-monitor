import React, { useState } from 'react'
import Dashboard from './pages/Dashboard'
import Logs from './pages/Logs'
import './App.css'

function App() {
  const [currentPage, setCurrentPage] = useState('dashboard')

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
      </nav>

      <main className="main-content">
        {currentPage === 'dashboard' && <Dashboard />}
        {currentPage === 'logs' && <Logs />}
      </main>
    </div>
  )
}

export default App