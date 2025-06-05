import React, { useState, useEffect, useRef } from 'react';
import { agent0Client, ChatResponse } from '../api/agent0';
import { Agent0WebSocket, StreamMessage } from '../api/websocket';

interface Message {
  id: string;
  text: string;
  isUser: boolean;
  timestamp: Date;
  isStreaming?: boolean;
}

export const ChatWindow: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<Agent0WebSocket | null>(null);

  useEffect(() => {
    // Initialize WebSocket connection
    wsRef.current = new Agent0WebSocket(
      'ws://localhost:8765',
      handleStreamMessage,
      handleWebSocketError,
      () => setIsConnected(true),
      () => setIsConnected(false)
    );

    wsRef.current.connect();

    return () => {
      wsRef.current?.disconnect();
    };
  }, []);

  useEffect(() => {
    // Auto-scroll to bottom
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleStreamMessage = (message: StreamMessage) => {
    if (message.type === 'agent0_token' && message.partial) {
      // Update streaming message
      setMessages(prev => 
        prev.map(msg => 
          msg.isStreaming 
            ? { ...msg, text: message.text }
            : msg
        )
      );
    } else if (message.type === 'agent0_complete') {
      // Finalize streaming message
      setMessages(prev => 
        prev.map(msg => 
          msg.isStreaming 
            ? { ...msg, text: message.text, isStreaming: false }
            : msg
        )
      );
      setIsLoading(false);
    }
  };

  const handleWebSocketError = (error: Event) => {
    console.error('WebSocket error:', error);
    setIsConnected(false);
  };

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      text: input,
      isUser: true,
      timestamp: new Date(),
    };

    const streamingMessage: Message = {
      id: (Date.now() + 1).toString(),
      text: '',
      isUser: false,
      timestamp: new Date(),
      isStreaming: true,
    };

    setMessages(prev => [...prev, userMessage, streamingMessage]);
    setInput('');
    setIsLoading(true);

    try {
      // Use WebSocket for streaming if connected, fallback to REST API
      if (isConnected && wsRef.current) {
        wsRef.current.sendMessage({
          prompt: input,
          session_id: 'ui_session',
        });
      } else {
        // Fallback to REST API
        const response = await agent0Client.sendMessage(input);
        setMessages(prev => 
          prev.map(msg => 
            msg.isStreaming 
              ? { ...msg, text: response.text, isStreaming: false }
              : msg
          )
        );
        setIsLoading(false);
      }
    } catch (error) {
      console.error('Failed to send message:', error);
      setMessages(prev => 
        prev.map(msg => 
          msg.isStreaming 
            ? { ...msg, text: 'Error: Failed to get response', isStreaming: false }
            : msg
        )
      );
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="flex flex-col h-full bg-gray-900 text-white">
      {/* Header */}
      <div className="bg-gray-800 px-4 py-3 border-b border-gray-700">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Agent-0 Chat</h2>
          <div className="flex items-center space-x-2">
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
            <span className="text-sm text-gray-400">
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.isUser ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                message.isUser
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-700 text-gray-200'
              } ${message.isStreaming ? 'opacity-70' : ''}`}
            >
              <p className="text-sm">{message.text}</p>
              {message.isStreaming && (
                <div className="mt-1 text-xs text-gray-400">Typing...</div>
              )}
              <p className="text-xs text-gray-400 mt-1">
                {message.timestamp.toLocaleTimeString()}
              </p>
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="bg-gray-800 p-4 border-t border-gray-700">
        <div className="flex space-x-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Type your message..."
            disabled={isLoading}
            className="flex-1 bg-gray-700 text-white rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
          />
          <button
            onClick={sendMessage}
            disabled={isLoading || !input.trim()}
            className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white px-6 py-2 rounded-lg transition-colors"
          >
            {isLoading ? 'Sending...' : 'Send'}
          </button>
        </div>
      </div>
    </div>
  );
}; 