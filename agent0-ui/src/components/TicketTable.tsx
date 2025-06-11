import React, { useState, useEffect } from 'react';
import { agent0Client } from '../api/agent0';

interface Ticket {
  id: string;
  ticket: string;
  owner: string;
  wave: string;
  status: 'open' | 'in_progress' | 'merged' | 'failed';
  pr_url?: string;
  created_at: string;
  updated_at: string;
}

interface TicketTableProps {
  className?: string;
}

export const TicketTable: React.FC<TicketTableProps> = ({ className = '' }) => {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  // Auto-refresh every 30 seconds
  useEffect(() => {
    const fetchTickets = async () => {
      try {
        setError(null);
        const response = await fetch('http://localhost:8000/ledger');
        
        if (!response.ok) {
          throw new Error(`Failed to fetch tickets: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Transform API response to ticket format
        const ticketList: Ticket[] = data.rows ? data.rows.map((row: any) => ({
          id: row.id || `ticket-${Date.now()}`,
          ticket: row.ticket || row.description || 'No description',
          owner: row.owner || 'Unassigned',
          wave: row.wave || 'General',
          status: row.status === '🟢' ? 'merged' : 
                  row.status === '🔴' ? 'failed' : 
                  row.status === '🟡' ? 'in_progress' : 'open',
          pr_url: row.pr_url || (row.pr_id ? `https://github.com/agent0/scaffold/pull/${row.pr_id}` : undefined),
          created_at: row.created_at || new Date().toISOString(),
          updated_at: row.updated_at || new Date().toISOString(),
        })) : [];
        
        setTickets(ticketList);
        setLastUpdate(new Date());
        setLoading(false);
      } catch (err) {
        console.error('Failed to fetch tickets:', err);
        setError(err instanceof Error ? err.message : 'Unknown error');
        setLoading(false);
      }
    };

    // Initial fetch
    fetchTickets();

    // Set up auto-refresh interval
    const interval = setInterval(fetchTickets, 30000); // 30 seconds

    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'merged': return 'text-green-400 bg-green-900/20';
      case 'failed': return 'text-red-400 bg-red-900/20';
      case 'in_progress': return 'text-yellow-400 bg-yellow-900/20';
      default: return 'text-blue-400 bg-blue-900/20';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'merged': return '✓';
      case 'failed': return '✗';
      case 'in_progress': return '⋯';
      default: return '○';
    }
  };

  const openPR = (ticket: Ticket) => {
    if (ticket.pr_url) {
      window.open(ticket.pr_url, '_blank', 'noopener,noreferrer');
    } else {
      // Generate PR URL based on ticket ID if no explicit URL
      const prUrl = `https://github.com/agent0/scaffold/pulls?q=is:pr+${ticket.id}`;
      window.open(prUrl, '_blank', 'noopener,noreferrer');
    }
  };

  const formatTime = (isoString: string) => {
    try {
      const date = new Date(isoString);
      return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return 'Invalid date';
    }
  };

  if (loading) {
    return (
      <div className={`bg-gray-800 rounded-lg p-4 ${className}`}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-white">Live Tickets</h3>
          <div className="animate-pulse w-2 h-2 bg-blue-400 rounded-full"></div>
        </div>
        <div className="space-y-2">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="animate-pulse bg-gray-700 h-12 rounded"></div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`bg-gray-800 rounded-lg p-4 ${className}`}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-white">Live Tickets</h3>
          <div className="w-2 h-2 bg-red-400 rounded-full"></div>
        </div>
        <div className="text-red-400 text-sm">
          Error: {error}
          <button 
            onClick={() => window.location.reload()}
            className="ml-2 underline hover:no-underline"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-gray-800 rounded-lg p-4 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white">Live Tickets</h3>
        <div className="flex items-center space-x-2">
          <div className="w-2 h-2 bg-green-400 rounded-full"></div>
          <span className="text-xs text-gray-400">
            Updated {formatTime(lastUpdate.toISOString())}
          </span>
        </div>
      </div>

      {/* Tickets List */}
      <div className="space-y-2 max-h-96 overflow-y-auto">
        {tickets.length === 0 ? (
          <div className="text-gray-400 text-sm text-center py-8">
            No tickets found
          </div>
        ) : (
          tickets.map((ticket) => (
            <div
              key={ticket.id}
              className="bg-gray-700 rounded-lg p-3 hover:bg-gray-600 transition-colors cursor-pointer"
              onClick={() => openPR(ticket)}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center space-x-2 mb-1">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(ticket.status)}`}>
                      {getStatusIcon(ticket.status)} {ticket.status.replace('_', ' ')}
                    </span>
                    <span className="text-xs text-gray-400">#{ticket.id}</span>
                  </div>
                  
                  <h4 className="text-sm font-medium text-white truncate mb-1">
                    {ticket.ticket}
                  </h4>
                  
                  <div className="flex items-center space-x-4 text-xs text-gray-300">
                    <span>Owner: {ticket.owner}</span>
                    <span>Wave: {ticket.wave}</span>
                    <span>Created: {formatTime(ticket.created_at)}</span>
                  </div>
                </div>
                
                <div className="flex items-center space-x-2 ml-2">
                  {ticket.pr_url && (
                    <div className="text-xs text-blue-400">
                      PR Available
                    </div>
                  )}
                  <div className="text-gray-400">
                    →
                  </div>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Footer Stats */}
      <div className="mt-4 pt-3 border-t border-gray-600">
        <div className="flex justify-between text-xs text-gray-400">
          <span>Total: {tickets.length}</span>
          <span>
            Open: {tickets.filter(t => t.status === 'open').length} | 
            In Progress: {tickets.filter(t => t.status === 'in_progress').length} | 
            Merged: {tickets.filter(t => t.status === 'merged').length}
          </span>
        </div>
      </div>
    </div>
  );
};

export default TicketTable; 