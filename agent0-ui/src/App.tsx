import React, { useState } from 'react';
import { ChatWindow } from './components/ChatWindow';
import { MetricsSidebar } from './components/MetricsSidebar';
import './styles/globals.css';

function App() {
  const [sidebarVisible, setSidebarVisible] = useState(true);

  return (
    <div className="h-screen flex bg-gray-900">
      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Header with controls */}
        <div className="bg-gray-800 p-3 border-b border-gray-700 flex justify-between items-center">
          <h1 className="text-xl font-bold text-white">Agent-0 Desktop</h1>
          <div className="flex space-x-2">
            <button
              onClick={() => setSidebarVisible(!sidebarVisible)}
              className="bg-gray-700 hover:bg-gray-600 text-white px-3 py-1 rounded text-sm transition-colors"
            >
              {sidebarVisible ? 'Hide Metrics' : 'Show Metrics'}
            </button>
          </div>
        </div>
        
        <ChatWindow />
      </div>

      {/* Metrics Sidebar */}
      {sidebarVisible && <MetricsSidebar />}
    </div>
  );
}

export default App; 