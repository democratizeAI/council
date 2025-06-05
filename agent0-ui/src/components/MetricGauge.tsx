import React from 'react';

interface MetricGaugeProps {
  title: string;
  value: number;
  unit: string;
  max: number;
  color?: string;
}

export const MetricGauge: React.FC<MetricGaugeProps> = ({
  title,
  value,
  unit,
  max,
  color = 'text-blue-400'
}) => {
  const percentage = Math.min((value / max) * 100, 100);

  return (
    <div className="bg-gray-700 rounded-lg p-4">
      <div className="flex justify-between items-center mb-2">
        <h4 className="text-sm font-medium text-gray-300">{title}</h4>
        <span className={`text-lg font-bold ${color}`}>
          {value.toFixed(1)} {unit}
        </span>
      </div>
      
      {/* Progress bar */}
      <div className="w-full bg-gray-600 rounded-full h-2">
        <div
          className={`h-2 rounded-full transition-all duration-300 ${
            color.includes('blue') ? 'bg-blue-500' :
            color.includes('green') ? 'bg-green-500' :
            color.includes('yellow') ? 'bg-yellow-500' :
            'bg-gray-500'
          }`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      
      <div className="mt-1 text-xs text-gray-500">
        {percentage.toFixed(1)}% of {max} {unit}
      </div>
    </div>
  );
}; 