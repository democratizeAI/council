import React from 'react';
import { MetricGauge } from './MetricGauge';
import { useMetrics } from '../hooks/useMetrics';

export const MetricsSidebar: React.FC = () => {
  const { metrics, isLoading, error } = useMetrics();

  if (error) {
    return (
      <div className="w-80 bg-gray-800 p-4 border-l border-gray-700">
        <h3 className="text-lg font-semibold text-white mb-4">System Metrics</h3>
        <div className="text-red-400 text-sm">
          Error loading metrics: {error.message}
        </div>
      </div>
    );
  }

  return (
    <div className="w-80 bg-gray-800 p-4 border-l border-gray-700">
      <h3 className="text-lg font-semibold text-white mb-4">System Metrics</h3>
      
      <div className="space-y-4">
        {/* Service Status */}
        <div className="bg-gray-700 rounded-lg p-4">
          <h4 className="text-sm font-medium text-gray-300 mb-2">Service Status</h4>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-sm text-gray-400">Status:</span>
              <span className={`text-sm ${metrics?.status === 'healthy' ? 'text-green-400' : 'text-red-400'}`}>
                {metrics?.status || 'Unknown'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-400">Uptime:</span>
              <span className="text-sm text-white">
                {metrics?.service.uptime_seconds 
                  ? Math.floor(metrics.service.uptime_seconds / 60) + 'm'
                  : '0m'
                }
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-400">Restarts:</span>
              <span className="text-sm text-white">
                {metrics?.service.startups_total || 0}
              </span>
            </div>
          </div>
        </div>

        {/* Performance Metrics */}
        <MetricGauge
          title="GPU Utilization"
          value={metrics?.monitoring.gpu_utilization || 0}
          unit="%"
          max={100}
          color="text-blue-400"
        />

        <MetricGauge
          title="System Health"
          value={(metrics?.monitoring.system_health || 0) * 100}
          unit="%"
          max={100}
          color="text-green-400"
        />

        <MetricGauge
          title="Queue Size"
          value={metrics?.monitoring.scratchpad_queue || 0}
          unit="items"
          max={1000}
          color="text-yellow-400"
        />

        {/* Refresh Indicator */}
        <div className="text-xs text-gray-500 text-center">
          {isLoading ? 'Updating...' : 'Updated just now'}
        </div>
      </div>
    </div>
  );
}; 