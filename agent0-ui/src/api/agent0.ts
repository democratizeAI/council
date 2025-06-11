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

export interface DistillRequest {
  prompt: string;
  session_id: string;
}

export interface DistillResponse {
  intent: string;
  confidence: number;
  structured_data: {
    action: string;
    parameters: Record<string, any>;
    priority: 'low' | 'medium' | 'high';
  };
  preview_text: string;
  estimated_tokens: number;
  session_id: string;
}

export class Agent0Client {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE) {
    this.baseUrl = baseUrl;
  }

  // IDR-01 Intent Distillation endpoint
  async distillIntent(prompt: string, sessionId: string = 'ui_session'): Promise<DistillResponse> {
    const response = await fetch(`${this.baseUrl}/distill`, {
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
      throw new Error(`Distillation request failed: ${response.status}`);
    }

    return response.json();
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

  // Enhanced send message with IDR-01 integration
  async sendMessageWithDistillation(prompt: string, sessionId: string = 'ui_session'): Promise<{
    distillation: DistillResponse;
    response: ChatResponse;
  }> {
    try {
      // Step 1: Distill intent first
      const distillation = await this.distillIntent(prompt, sessionId);
      
      // Step 2: Send to chat with distilled context
      const response = await this.sendMessage(prompt, sessionId);
      
      return { distillation, response };
    } catch (error) {
      // Fallback to direct chat if distillation fails
      console.warn('Distillation failed, falling back to direct chat:', error);
      const response = await this.sendMessage(prompt, sessionId);
      
      // Create mock distillation response
      const distillation: DistillResponse = {
        intent: 'Direct chat (distillation unavailable)',
        confidence: 0.5,
        structured_data: {
          action: 'chat',
          parameters: { prompt },
          priority: 'medium',
        },
        preview_text: response.text.slice(0, 100) + '...',
        estimated_tokens: response.text.length / 4,
        session_id: sessionId,
      };
      
      return { distillation, response };
    }
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