import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import './TinyproxyMetricsChart.css';

function TinyproxyMetricsChart({ title = "Proxy Metrics" }) {
  const [data, setData] = useState([]);
  const [timeRange, setTimeRange] = useState(1); // 기본 1시간
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // 인증 헤더 가져오기
  const getAuthHeaders = () => {
    const token = localStorage.getItem('access_token');
    if (token && token !== 'demo-token') {
      return {
        'Authorization': `Bearer ${token}`
      };
    }
    return {};
  };

  // 데이터 가져오기
  const fetchMetrics = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const headers = getAuthHeaders();
      const response = await fetch(
        `/api/performance/metrics/aggregated?hours=${timeRange}&interval_minutes=5`,
        { headers }
      );
      
      if (!response.ok) {
        throw new Error('Failed to fetch metrics');
      }
      
      const result = await response.json();
      
      // 데이터 형식 변환 (차트용)
      const chartData = result.data.map(item => {
        const time = new Date(item.timestamp);
        return {
          time: `${time.getHours().toString().padStart(2, '0')}:${time.getMinutes().toString().padStart(2, '0')}`,
          fullTime: time.toLocaleString(),
          connections: item.connections?.avg || 0,
          throughput: item.throughput?.avg || 0,
          errorRate: item.error_rate?.avg || 0,
          requests: item.requests_delta || 0,
          errors: item.errors_delta || 0,
          sampleCount: item.sample_count || 0
        };
      });
      
      setData(chartData);
    } catch (err) {
      console.error('Error fetching metrics:', err);
      setError('Failed to load metrics data');
    } finally {
      setLoading(false);
    }
  };

  // 초기 로드 및 자동 새로고침
  useEffect(() => {
    fetchMetrics();
    
    // 1분마다 자동 새로고침
    const interval = setInterval(fetchMetrics, 60000);
    
    return () => clearInterval(interval);
  }, [timeRange]);

  // 사용자 정의 툴팁
  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      const dataPoint = payload[0]?.payload;
      return (
        <div className="custom-tooltip">
          <p className="tooltip-label">{label}</p>
          {dataPoint?.fullTime && (
            <p className="tooltip-time">{dataPoint.fullTime}</p>
          )}
          {payload.map((entry, index) => (
            <p key={index} style={{ color: entry.color }}>
              {entry.name}: {typeof entry.value === 'number' ? entry.value.toFixed(2) : entry.value}
            </p>
          ))}
          {dataPoint?.sampleCount > 0 && (
            <p className="tooltip-samples">Samples: {dataPoint.sampleCount}</p>
          )}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="proxy-chart-container">
      <div className="chart-header">
        <h3 className="chart-title">{title}</h3>
        <div className="chart-controls">
          <div className="time-range-selector">
            <button 
              className={timeRange === 1 ? 'active' : ''}
              onClick={() => setTimeRange(1)}
            >
              1H
            </button>
            <button 
              className={timeRange === 6 ? 'active' : ''}
              onClick={() => setTimeRange(6)}
            >
              6H
            </button>
            <button 
              className={timeRange === 24 ? 'active' : ''}
              onClick={() => setTimeRange(24)}
            >
              24H
            </button>
          </div>
          {loading && <span className="loading-indicator">Updating...</span>}
        </div>
      </div>
      
      {error ? (
        <div className="chart-error">{error}</div>
      ) : (
        <div className="charts-grid">
          {/* 연결 수 차트 */}
          <div className="chart-item">
            <h4>Active Connections (Current)</h4>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={data}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="time" 
                  interval="preserveStartEnd"
                  tick={{ fontSize: 12 }}
                />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip content={<CustomTooltip />} />
                <Line 
                  type="monotone" 
                  dataKey="connections" 
                  stroke="#10b981" 
                  strokeWidth={2}
                  dot={false}
                  name="Active Connections"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* 처리량 차트 */}
          <div className="chart-item">
            <h4>Throughput (Requests/sec)</h4>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={data}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="time" 
                  interval="preserveStartEnd"
                  tick={{ fontSize: 12 }}
                />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip content={<CustomTooltip />} />
                <Line 
                  type="monotone" 
                  dataKey="throughput" 
                  stroke="#3b82f6" 
                  strokeWidth={2}
                  dot={false}
                  name="Requests/sec"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* 에러율 차트 */}
          <div className="chart-item">
            <h4>Error Rate (% per period)</h4>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={data}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="time" 
                  interval="preserveStartEnd"
                  tick={{ fontSize: 12 }}
                />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip content={<CustomTooltip />} />
                <Line 
                  type="monotone" 
                  dataKey="errorRate" 
                  stroke="#ef4444" 
                  strokeWidth={2}
                  dot={false}
                  name="Error %"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
}

export default TinyproxyMetricsChart;
