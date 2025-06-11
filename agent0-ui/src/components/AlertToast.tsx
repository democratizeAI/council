import React, { useState, useEffect } from 'react';

interface Alert {
  id: string;
  message: string;
  severity: 'info' | 'warning' | 'error' | 'success';
  timestamp: Date;
  source: string;
  dismissed?: boolean;
}

interface AlertToastProps {
  position?: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left';
  maxAlerts?: number;
  autoHideDelay?: number; // ms
}

export const AlertToast: React.FC<AlertToastProps> = ({
  position = 'top-right',
  maxAlerts = 5,
  autoHideDelay = 10000, // 10 seconds
}) => {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [wsConnection, setWsConnection] = useState<WebSocket | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected'>('disconnected');

  // Initialize WebSocket connection to Slack relay service
  useEffect(() => {
    const connectToSlackRelay = () => {
      try {
        setConnectionStatus('connecting');
        
        // Connect to Slack relay WebSocket service
        const ws = new WebSocket('ws://localhost:9001/alerts/stream');
        
        ws.onopen = () => {
          console.log('Connected to Slack alert relay');
          setConnectionStatus('connected');
          setWsConnection(ws);
        };

        ws.onmessage = (event) => {
          try {
            const alertData = JSON.parse(event.data);
            
            // Create alert object
            const newAlert: Alert = {
              id: `alert-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
              message: alertData.text || alertData.message || 'Unknown alert',
              severity: mapSeverity(alertData.severity || alertData.level || 'info'),
              timestamp: new Date(),
              source: alertData.channel || '#ops-alerts',
            };

            console.log('Received alert:', newAlert);
            
            // Add alert to list
            setAlerts(prev => {
              const updated = [newAlert, ...prev].slice(0, maxAlerts);
              return updated;
            });

            // Auto-dismiss after delay
            setTimeout(() => {
              setAlerts(prev => prev.map(alert => 
                alert.id === newAlert.id ? { ...alert, dismissed: true } : alert
              ));
            }, autoHideDelay);

            // Remove dismissed alerts after animation
            setTimeout(() => {
              setAlerts(prev => prev.filter(alert => alert.id !== newAlert.id));
            }, autoHideDelay + 500);

          } catch (error) {
            console.error('Failed to parse alert message:', error);
          }
        };

        ws.onclose = () => {
          console.log('Disconnected from Slack alert relay');
          setConnectionStatus('disconnected');
          setWsConnection(null);
          
          // Attempt reconnection after 5 seconds
          setTimeout(connectToSlackRelay, 5000);
        };

        ws.onerror = (error) => {
          console.error('Slack alert relay error:', error);
          setConnectionStatus('disconnected');
        };

      } catch (error) {
        console.error('Failed to connect to Slack alert relay:', error);
        setConnectionStatus('disconnected');
        
        // Retry connection after 10 seconds
        setTimeout(connectToSlackRelay, 10000);
      }
    };

    // Start connection
    connectToSlackRelay();

    // Cleanup on unmount
    return () => {
      if (wsConnection) {
        wsConnection.close();
      }
    };
  }, [maxAlerts, autoHideDelay]);

  // Map alert severity to our severity levels
  const mapSeverity = (severity: string): Alert['severity'] => {
    const s = severity.toLowerCase();
    if (s.includes('error') || s.includes('critical') || s.includes('fatal')) return 'error';
    if (s.includes('warn') || s.includes('alert')) return 'warning';
    if (s.includes('success') || s.includes('ok') || s.includes('resolved')) return 'success';
    return 'info';
  };

  // Get alert styling based on severity
  const getAlertStyles = (severity: Alert['severity']) => {
    switch (severity) {
      case 'error':
        return 'bg-red-800 border-red-600 text-red-100';
      case 'warning':
        return 'bg-yellow-800 border-yellow-600 text-yellow-100';
      case 'success':
        return 'bg-green-800 border-green-600 text-green-100';
      default:
        return 'bg-blue-800 border-blue-600 text-blue-100';
    }
  };

  // Get alert icon
  const getAlertIcon = (severity: Alert['severity']) => {
    switch (severity) {
      case 'error': return '🚨';
      case 'warning': return '⚠️';
      case 'success': return '✅';
      default: return 'ℹ️';
    }
  };

  // Position classes
  const getPositionClasses = () => {
    switch (position) {
      case 'top-left': return 'top-4 left-4';
      case 'bottom-right': return 'bottom-4 right-4';
      case 'bottom-left': return 'bottom-4 left-4';
      default: return 'top-4 right-4';
    }
  };

  // Manually dismiss alert
  const dismissAlert = (alertId: string) => {
    setAlerts(prev => prev.map(alert => 
      alert.id === alertId ? { ...alert, dismissed: true } : alert
    ));
    
    setTimeout(() => {
      setAlerts(prev => prev.filter(alert => alert.id !== alertId));
    }, 500);
  };

  // Format timestamp
  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  // Don't render if no alerts
  if (alerts.length === 0) {
    return (
      <div className={`fixed ${getPositionClasses()} z-50`}>
        {/* Connection status indicator */}
        <div className="mb-2 text-right">
          <div className={`inline-flex items-center px-2 py-1 rounded text-xs ${
            connectionStatus === 'connected' ? 'bg-green-800 text-green-100' :
            connectionStatus === 'connecting' ? 'bg-yellow-800 text-yellow-100' :
            'bg-red-800 text-red-100'
          }`}>
            <div className={`w-1.5 h-1.5 rounded-full mr-1 ${
              connectionStatus === 'connected' ? 'bg-green-400' :
              connectionStatus === 'connecting' ? 'bg-yellow-400 animate-pulse' :
              'bg-red-400'
            }`}></div>
            {connectionStatus === 'connected' ? 'Live Alerts' :
             connectionStatus === 'connecting' ? 'Connecting...' :
             'Disconnected'}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`fixed ${getPositionClasses()} z-50 space-y-2`}>
      {/* Connection status indicator */}
      <div className="text-right mb-2">
        <div className={`inline-flex items-center px-2 py-1 rounded text-xs ${
          connectionStatus === 'connected' ? 'bg-green-800 text-green-100' :
          connectionStatus === 'connecting' ? 'bg-yellow-800 text-yellow-100' :
          'bg-red-800 text-red-100'
        }`}>
          <div className={`w-1.5 h-1.5 rounded-full mr-1 ${
            connectionStatus === 'connected' ? 'bg-green-400' :
            connectionStatus === 'connecting' ? 'bg-yellow-400 animate-pulse' :
            'bg-red-400'
          }`}></div>
          Alerts: {connectionStatus}
        </div>
      </div>

      {/* Alert toasts */}
      {alerts.map((alert) => (
        <div
          key={alert.id}
          className={`
            transform transition-all duration-500 ease-in-out
            ${alert.dismissed ? 'translate-x-full opacity-0' : 'translate-x-0 opacity-100'}
            max-w-sm w-full shadow-lg rounded-lg border-l-4 p-4
            ${getAlertStyles(alert.severity)}
          `}
        >
          <div className="flex items-start">
            <div className="flex-shrink-0 mr-3">
              <span className="text-lg">
                {getAlertIcon(alert.severity)}
              </span>
            </div>
            
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between mb-1">
                <p className="text-sm font-medium">
                  {alert.source}
                </p>
                <button
                  onClick={() => dismissAlert(alert.id)}
                  className="text-sm opacity-70 hover:opacity-100 transition-opacity"
                >
                  ✕
                </button>
              </div>
              
              <p className="text-sm break-words">
                {alert.message}
              </p>
              
              <p className="text-xs opacity-75 mt-1">
                {formatTime(alert.timestamp)}
              </p>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};

export default AlertToast; 