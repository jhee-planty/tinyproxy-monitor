import React, { useState, useEffect, useRef } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

function App() {
  const [systemMetrics, setSystemMetrics] = useState(null);
  const [tinyproxyMetrics, setTinyproxyMetrics] = useState(null);
  const [systemHistory, setSystemHistory] = useState([]);
  const [performanceHistory, setPerformanceHistory] = useState([]);
  const [processStatus, setProcessStatus] = useState(null);
  const ws = useRef(null);
  const maxDataPoints = 60; // 최근 60초 데이터

  useEffect(() => {
    // WebSocket 연결
    connectWebSocket();
    
    // 초기 데이터 로드
    fetchProcessStatus();
    fetchHistoryData();
    
    // 5초마다 히스토리 데이터 갱신
    const interval = setInterval(fetchHistoryData, 5000);
    
    return () => {
      if (ws.current) {
        ws.current.close();
      }
      clearInterval(interval);
    };
  }, []);

  const connectWebSocket = () => {
    ws.current = new WebSocket('ws://localhost:8000/ws/metrics');
    
    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      // 시스템 메트릭 업데이트
      if (data.system) {
        setSystemMetrics(data.system);
        updateSystemHistory(data.system);
      }
      
      // Tinyproxy 메트릭 업데이트
      if (data.tinyproxy) {
        setTinyproxyMetrics(data.tinyproxy);
        updatePerformanceHistory(data.tinyproxy);
      }
    };
    
    ws.current.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
    
    ws.current.onclose = () => {
      // 재연결 시도
      setTimeout(connectWebSocket, 3000);
    };
  };

  const fetchProcessStatus = async () => {
    try {
      const response = await fetch('/api/process/status');
      const data = await response.json();
      setProcessStatus(data);
    } catch (error) {
      console.error('Error fetching process status:', error);
    }
  };

  const fetchHistoryData = async () => {
    try {
      // 시스템 히스토리
      const sysResponse = await fetch('/api/metrics/system/history?seconds=60');
      const sysData = await sysResponse.json();
      
      // 성능 히스토리
      const perfResponse = await fetch('/api/metrics/tinyproxy/history?seconds=60');
      const perfData = await perfResponse.json();
      
      // 차트용 데이터 포맷
      setSystemHistory(formatSystemHistory(sysData));
      setPerformanceHistory(formatPerformanceHistory(perfData));
    } catch (error) {
      console.error('Error fetching history:', error);
    }
  };

  const updateSystemHistory = (metrics) => {
    setSystemHistory(prev => {
      const newPoint = {
        time: new Date(metrics.timestamp).toLocaleTimeString(),
        cpu: metrics.cpu?.percent || 0,
        memory: metrics.memory?.percent || 0,
        disk: metrics.disk?.percent || 0
      };
      const updated = [...prev, newPoint];
      return updated.slice(-maxDataPoints);
    });
  };

  const updatePerformanceHistory = (metrics) => {
    setPerformanceHistory(prev => {
      const newPoint = {
        time: new Date(metrics.timestamp).toLocaleTimeString(),
        throughput: metrics.throughput || 0,
        errorRate: metrics.error_rate || 0,
        p95: metrics.latency?.p95 || 0,
        connections: metrics.active_connections || 0
      };
      const updated = [...prev, newPoint];
      return updated.slice(-maxDataPoints);
    });
  };

  const formatSystemHistory = (data) => {
    return data.map(item => ({
      time: new Date(item.timestamp).toLocaleTimeString(),
      cpu: item.cpu?.percent || 0,
      memory: item.memory?.percent || 0,
      disk: item.disk?.percent || 0
    }));
  };

  const formatPerformanceHistory = (data) => {
    return data.map(item => ({
      time: new Date(item.timestamp).toLocaleTimeString(),
      throughput: item.throughput || 0,
      errorRate: item.error_rate || 0,
      p95: item.latency?.p95 || 0,
      connections: item.active_connections || 0
    }));
  };

  return (
    <div className="container">
      <div className="header">
        <h1>Tinyproxy Monitor</h1>
        <p>
          Status: 
          <span className={`status-indicator ${processStatus?.running ? 'status-running' : 'status-stopped'}`}></span>
          {processStatus?.running ? 'Running' : 'Stopped'}
          {processStatus?.pid && ` (PID: ${processStatus.pid})`}
        </p>
      </div>

      {/* 시스템 메트릭 카드 */}
      <div className="metrics-grid">
        <div className="metric-card">
          <h3>CPU Usage</h3>
          <div className="metric-value">
            {systemMetrics?.cpu?.percent?.toFixed(1) || '0'}
            <span className="metric-unit">%</span>
          </div>
        </div>
        
        <div className="metric-card">
          <h3>Memory Usage</h3>
          <div className="metric-value">
            {systemMetrics?.memory?.percent?.toFixed(1) || '0'}
            <span className="metric-unit">%</span>
          </div>
        </div>
        
        <div className="metric-card">
          <h3>Disk Usage</h3>
          <div className="metric-value">
            {systemMetrics?.disk?.percent?.toFixed(1) || '0'}
            <span className="metric-unit">%</span>
          </div>
        </div>
        
        <div className="metric-card">
          <h3>Network (Send)</h3>
          <div className="metric-value">
            {systemMetrics?.network?.sent_mb_s?.toFixed(2) || '0'}
            <span className="metric-unit">MB/s</span>
          </div>
        </div>
      </div>

      {/* Tinyproxy 성능 메트릭 카드 */}
      <div className="metrics-grid">
        <div className="metric-card">
          <h3>Throughput</h3>
          <div className="metric-value">
            {tinyproxyMetrics?.throughput?.toFixed(1) || '0'}
            <span className="metric-unit">req/s</span>
          </div>
        </div>
        
        <div className="metric-card">
          <h3>Error Rate</h3>
          <div className="metric-value">
            {tinyproxyMetrics?.error_rate?.toFixed(2) || '0'}
            <span className="metric-unit">%</span>
          </div>
        </div>
        
        <div className="metric-card">
          <h3>P95 Latency</h3>
          <div className="metric-value">
            {tinyproxyMetrics?.latency?.p95?.toFixed(0) || '0'}
            <span className="metric-unit">ms</span>
          </div>
        </div>
        
        <div className="metric-card">
          <h3>Active Connections</h3>
          <div className="metric-value">
            {tinyproxyMetrics?.active_connections || '0'}
          </div>
        </div>
      </div>

      {/* 차트 */}
      <div className="performance-grid">
        {/* 시스템 리소스 차트 */}
        <div className="chart-container">
          <h2 className="chart-title">System Resources</h2>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={systemHistory}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" />
              <YAxis domain={[0, 100]} />
              <Tooltip />
              <Legend />
              <Line 
                type="monotone" 
                dataKey="cpu" 
                stroke="#8884d8" 
                strokeWidth={2}
                dot={false}
                name="CPU %"
              />
              <Line 
                type="monotone" 
                dataKey="memory" 
                stroke="#82ca9d" 
                strokeWidth={2}
                dot={false}
                name="Memory %"
              />
              <Line 
                type="monotone" 
                dataKey="disk" 
                stroke="#ffc658" 
                strokeWidth={2}
                dot={false}
                name="Disk %"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* 성능 메트릭 차트 */}
        <div className="chart-container">
          <h2 className="chart-title">Performance Metrics</h2>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={performanceHistory}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" />
              <YAxis yAxisId="left" />
              <YAxis yAxisId="right" orientation="right" />
              <Tooltip />
              <Legend />
              <Line 
                yAxisId="left"
                type="monotone" 
                dataKey="throughput" 
                stroke="#8884d8" 
                strokeWidth={2}
                dot={false}
                name="Throughput (req/s)"
              />
              <Line 
                yAxisId="right"
                type="monotone" 
                dataKey="p95" 
                stroke="#82ca9d" 
                strokeWidth={2}
                dot={false}
                name="P95 Latency (ms)"
              />
              <Line 
                yAxisId="left"
                type="monotone" 
                dataKey="connections" 
                stroke="#ff7300" 
                strokeWidth={2}
                dot={false}
                name="Connections"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 레이턴시 상세 정보 */}
      {tinyproxyMetrics?.latency && (
        <div className="chart-container">
          <h2 className="chart-title">Latency Distribution</h2>
          <div className="metrics-grid">
            <div className="metric-card">
              <h3>P50 (Median)</h3>
              <div className="metric-value">
                {tinyproxyMetrics.latency.p50?.toFixed(0) || '0'}
                <span className="metric-unit">ms</span>
              </div>
            </div>
            <div className="metric-card">
              <h3>P95</h3>
              <div className="metric-value">
                {tinyproxyMetrics.latency.p95?.toFixed(0) || '0'}
                <span className="metric-unit">ms</span>
              </div>
            </div>
            <div className="metric-card">
              <h3>P99</h3>
              <div className="metric-value">
                {tinyproxyMetrics.latency.p99?.toFixed(0) || '0'}
                <span className="metric-unit">ms</span>
              </div>
            </div>
            <div className="metric-card">
              <h3>Max</h3>
              <div className="metric-value">
                {tinyproxyMetrics.latency.max?.toFixed(0) || '0'}
                <span className="metric-unit">ms</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;