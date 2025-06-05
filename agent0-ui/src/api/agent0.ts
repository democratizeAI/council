// Agent-0 FastAPI client with proper error handling
const API_BASE = 'http://localhost:8000';

export interface ChatMessage {
  text: string;
  session_id: string;
  timestamp?: number;
}

export interface ChatResponse {
  text: string;
  voices: Array<{
    voice: string;
    reply: string;
    tokens: number;
    cost: number;
    confidence: number;
    model: string;
  }>;
  cost_usd: number;
  model_chain: string[];
  session_id: string;
}

export interface MetricsResponse {
  service: {
    startups_total: number;
    uptime_seconds: number;
    service_managed: boolean;
  };
  monitoring: {
    gpu_utilization: number;
    system_health: number;
    scratchpad_queue: number;
  };
  status: string;
}

export class Agent0Client {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE) {
    this.baseUrl = baseUrl;
  }

  async sendMessage(prompt: string, sessionId: string = 'ui_session'): Promise<ChatResponse> {
    const response = await fetch(`${this.baseUrl}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        prompt,
        session_id: sessionId,
      }),
    });

    if (!response.ok) {
      throw new Error(`Chat request failed: ${response.status}`);
    }

    return response.json();
  }

  async getHealth(): Promise<MetricsResponse> {
    const response = await fetch(`${this.baseUrl}/health`);
    
    if (!response.ok) {
      throw new Error(`Health check failed: ${response.status}`);
    }

    return response.json();
  }

  async getMetrics(): Promise<string> {
    const response = await fetch(`${this.baseUrl}/metrics`);
    
    if (!response.ok) {
      throw new Error(`Metrics request failed: ${response.status}`);
    }

    return response.text();
  }

  // Service control commands
  async pauseService(): Promise<void> {
    const response = await fetch(`${this.baseUrl}/admin/pause`, {
      method: 'POST',
    });
    
    if (!response.ok) {
      throw new Error(`Pause request failed: ${response.status}`);
    }
  }

  async resumeService(): Promise<void> {
    const response = await fetch(`${this.baseUrl}/admin/resume`, {
      method: 'POST',
    });
    
    if (!response.ok) {
      throw new Error(`Resume request failed: ${response.status}`);
    }
  }
}

export const agent0Client = new Agent0Client(); 