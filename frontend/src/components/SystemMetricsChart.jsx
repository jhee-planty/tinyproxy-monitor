import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import './SystemMetrics.css';

function SystemMetricsChart({ data, title }) {
  return (
    <div className="chart-container">
      <h3 className="chart-title">{title}</h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data}>
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
  );
}

export default SystemMetricsChart;