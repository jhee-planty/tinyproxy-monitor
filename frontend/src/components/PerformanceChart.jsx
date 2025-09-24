import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import './PerformanceChart.css';

function PerformanceChart({ data, title }) {
  return (
    <div className="chart-container">
      <h3 className="chart-title">{title}</h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="time" />
          <YAxis yAxisId="left" />
          <YAxis yAxisId="right" orientation="right" />
          <Tooltip />
          <Legend />
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
            dataKey="errorRate" 
            stroke="#f44336" 
            strokeWidth={2}
            dot={false}
            name="Error Rate (%)"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export default PerformanceChart;