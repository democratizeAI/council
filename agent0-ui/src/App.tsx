import React, { useState } from 'react';
import { ChatWindow } from './components/ChatWindow';
import { MetricsSidebar } from './components/MetricsSidebar';
import { TicketTable } from './components/TicketTable';
import { AlertToast } from './components/AlertToast';
import './styles/globals.css';

function App() {
  const [sidebarVisible, setSidebarVisible] = useState(true);
  const [ticketTableVisible, setTicketTableVisible] = useState(true);
  const [alertsEnabled, setAlertsEnabled] = useState(true);

  return (
    <div className="h-screen flex bg-gray-900">
      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Header with controls */}
        <div className="bg-gray-800 p-3 border-b border-gray-700 flex justify-between items-center">
          <h1 className="text-xl font-bold text-white">Agent-0 Desktop</h1>
          <div className="flex space-x-2">
            <button
              onClick={() => setTicketTableVisible(!ticketTableVisible)}
              className="bg-gray-700 hover:bg-gray-600 text-white px-3 py-1 rounded text-sm transition-colors"
            >
              {ticketTableVisible ? 'Hide Tickets' : 'Show Tickets'}
            </button>
            <button
              onClick={() => setSidebarVisible(!sidebarVisible)}
              className="bg-gray-700 hover:bg-gray-600 text-white px-3 py-1 rounded text-sm transition-colors"
            >
              {sidebarVisible ? 'Hide Metrics' : 'Show Metrics'}
            </button>
            <button
              onClick={() => setAlertsEnabled(!alertsEnabled)}
              className={`px-3 py-1 rounded text-sm transition-colors ${
                alertsEnabled 
                  ? 'bg-green-700 hover:bg-green-600 text-white'
                  : 'bg-red-700 hover:bg-red-600 text-white'
              }`}
            >
              Alerts {alertsEnabled ? 'ON' : 'OFF'}
            </button>
          </div>
        </div>
        
        {/* Main content area */}
        <div className="flex-1 flex">
          {/* Chat Window */}
          <div className="flex-1">
            <ChatWindow />
          </div>
          
          {/* Ticket Table */}
          {ticketTableVisible && (
            <div className="w-80 border-l border-gray-700">
              <TicketTable className="h-full" />
            </div>
          )}
        </div>
      </div>

      {/* Metrics Sidebar */}
      {sidebarVisible && <MetricsSidebar />}
      
      {/* Alert Toast System */}
      {alertsEnabled && (
        <AlertToast 
          position="top-right"
          maxAlerts={5}
          autoHideDelay={10000}
        />
      )}
    </div>
  );
}

export default App; 