/**
 * 🚀 Frontend Agent-0 Front-Speaker Streaming Client
 * Demonstrates how to handle the new instant Agent-0 + background refinement flow
 */

class Agent0StreamingClient {
    constructor(apiBaseUrl = 'http://localhost:8000') {
        this.apiBaseUrl = apiBaseUrl;
        this.currentEventSource = null;
    }

    /**
     * Start a streaming chat session with Agent-0 front-speaker
     * @param {string} prompt - User's question
     * @param {string} sessionId - Session identifier
     * @param {Object} callbacks - Event callbacks
     */
    async streamChat(prompt, sessionId = 'default', callbacks = {}) {
        const {
            onAgent0Token = () => {},      // Called for each Agent-0 word
            onAgent0Complete = () => {},   // Called when Agent-0 draft is complete  
            onRefinementStart = () => {},  // Called when specialists start refining
            onRefinementComplete = () => {}, // Called when refinement is done
            onError = () => {}             // Called on errors
        } = callbacks;

        // Close any existing stream
        this.closeStream();

        try {
            // Start Server-Sent Events stream
            const response = await fetch(`${this.apiBaseUrl}/chat/stream`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    prompt: prompt,
                    session_id: sessionId
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            // Set up EventSource-like processing
            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            let buffer = '';
            let agent0Text = '';
            let refinementPending = false;

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                
                // Process complete lines
                const lines = buffer.split('\n');
                buffer = lines.pop(); // Keep incomplete line in buffer

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = JSON.parse(line.slice(6));
                        await this.handleStreamEvent(data, {
                            onAgent0Token,
                            onAgent0Complete,
                            onRefinementStart,
                            onRefinementComplete,
                            onError
                        });

                        // Track Agent-0 state
                        if (data.type === 'agent0_token') {
                            agent0Text = data.text;
                        } else if (data.type === 'agent0_complete') {
                            refinementPending = data.meta?.refinement_pending || false;
                        }
                    }
                }
            }

        } catch (error) {
            console.error('Streaming error:', error);
            onError(error);
        }
    }

    /**
     * Handle individual stream events
     */
    async handleStreamEvent(data, callbacks) {
        const {
            onAgent0Token,
            onAgent0Complete,
            onRefinementStart,
            onRefinementComplete,
            onError
        } = callbacks;

        switch (data.type) {
            case 'start':
                console.log('🚀 Stream started');
                break;

            case 'agent0_token':
                // Agent-0 is streaming word by word
                onAgent0Token({
                    text: data.text,
                    partial: true,
                    progress: data.progress,
                    confidence: data.confidence
                });
                break;

            case 'agent0_complete':
                // Agent-0 draft is complete
                console.log('✅ Agent-0 draft complete');
                onAgent0Complete({
                    text: data.text,
                    confidence: data.meta.confidence,
                    latency_ms: data.meta.latency_ms,
                    refinementPending: data.meta.refinement_pending
                });
                break;

            case 'refinement_status':
                // Specialists are working in background
                console.log('⚙️ Background refinement starting');
                onRefinementStart({
                    status: data.status,
                    message: data.text
                });
                break;

            case 'refinement_complete':
                // Background refinement finished
                console.log('✨ Refinement complete');
                onRefinementComplete({
                    text: data.text,
                    originalText: data.original_text,
                    improved: data.meta?.improvement || false,
                    refinementType: data.meta?.refinement_type,
                    specialistsUsed: data.meta?.specialists_used || []
                });
                break;

            case 'refinement_timeout':
            case 'refinement_error':
                // Refinement failed - stick with Agent-0
                console.log('⚠️ Refinement failed, using Agent-0 answer');
                onRefinementComplete({
                    text: data.text,
                    improved: false,
                    error: data.meta?.message
                });
                break;

            case 'stream_complete':
                // Entire stream finished
                console.log('🏁 Stream complete');
                break;

            case 'error':
                // Stream error
                console.error('❌ Stream error:', data.error);
                onError(new Error(data.error));
                break;

            default:
                console.log('📨 Unknown event:', data.type, data);
        }
    }

    /**
     * Close the current stream
     */
    closeStream() {
        if (this.currentEventSource) {
            this.currentEventSource.close();
            this.currentEventSource = null;
        }
    }
}

/**
 * 🎨 Example UI Integration
 * Shows how to integrate with a chat interface
 */
class ChatInterface {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.client = new Agent0StreamingClient();
        this.setupUI();
    }

    setupUI() {
        this.container.innerHTML = `
            <div class="chat-messages" id="messages"></div>
            <div class="chat-input">
                <input type="text" id="prompt" placeholder="Ask Agent-0 anything...">
                <button onclick="this.sendMessage()">Send</button>
            </div>
            <style>
                .chat-messages { 
                    height: 400px; 
                    overflow-y: auto; 
                    border: 1px solid #ccc; 
                    padding: 10px; 
                    margin-bottom: 10px;
                }
                .message { 
                    margin: 10px 0; 
                    padding: 8px; 
                    border-radius: 8px; 
                }
                .user { 
                    background: #e3f2fd; 
                    text-align: right; 
                }
                .agent0 { 
                    background: #f3e5f5; 
                    border-left: 4px solid #9c27b0; 
                }
                .refinement-badge { 
                    display: inline-block; 
                    background: #ff9800; 
                    color: white; 
                    padding: 2px 6px; 
                    border-radius: 10px; 
                    font-size: 0.8em; 
                    margin-left: 8px; 
                }
                .confidence { 
                    color: #666; 
                    font-size: 0.9em; 
                }
            </style>
        `;
    }

    async sendMessage() {
        const input = document.getElementById('prompt');
        const prompt = input.value.trim();
        if (!prompt) return;

        const messagesDiv = document.getElementById('messages');
        
        // Add user message
        this.addMessage('user', prompt);
        input.value = '';

        // Create Agent-0 message placeholder
        const agent0MessageId = 'msg_' + Date.now();
        messagesDiv.innerHTML += `
            <div class="message agent0" id="${agent0MessageId}">
                <strong>Agent-0:</strong> 
                <span class="text"></span>
                <span class="confidence"></span>
                <span class="refinement-badge" style="display: none;">⚙️ refining...</span>
            </div>
        `;

        const agent0Msg = document.getElementById(agent0MessageId);
        const textSpan = agent0Msg.querySelector('.text');
        const confidenceSpan = agent0Msg.querySelector('.confidence');
        const refinementBadge = agent0Msg.querySelector('.refinement-badge');

        // Start streaming
        await this.client.streamChat(prompt, 'demo_session', {
            onAgent0Token: (data) => {
                // Update text progressively
                textSpan.textContent = data.text;
                confidenceSpan.textContent = `(${(data.confidence * 100).toFixed(0)}% confidence)`;
                
                // Show refinement badge if pending
                if (data.confidence < 0.60) {
                    refinementBadge.style.display = 'inline-block';
                }
            },

            onAgent0Complete: (data) => {
                textSpan.textContent = data.text;
                confidenceSpan.textContent = `(${(data.confidence * 100).toFixed(0)}% confidence, ${data.latency_ms.toFixed(0)}ms)`;
            },

            onRefinementStart: (data) => {
                refinementBadge.textContent = '⚙️ specialists working...';
                refinementBadge.style.display = 'inline-block';
            },

            onRefinementComplete: (data) => {
                if (data.improved) {
                    // Update with improved text
                    textSpan.textContent = data.text;
                    refinementBadge.textContent = `✨ refined by ${data.specialistsUsed.join(', ')}`;
                    refinementBadge.style.background = '#4caf50';
                } else {
                    // No improvement
                    refinementBadge.style.display = 'none';
                }
            },

            onError: (error) => {
                textSpan.textContent = `Error: ${error.message}`;
                refinementBadge.style.display = 'none';
            }
        });

        // Scroll to bottom
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }

    addMessage(type, text) {
        const messagesDiv = document.getElementById('messages');
        messagesDiv.innerHTML += `
            <div class="message ${type}">
                ${type === 'user' ? '<strong>You:</strong>' : '<strong>Agent-0:</strong>'} ${text}
            </div>
        `;
    }
}

// Example usage:
// const chat = new ChatInterface('chat-container');

/**
 * 📝 Example Expected Flow:
 * 
 * User types: "What is 25 * 17?"
 * 
 * 1. Agent-0 streams: "I can help you calculate that. Let me work through this step by step..."
 *    - Shows immediately (0.3s)
 *    - Confidence: 0.45 (< 0.60 threshold)
 *    - Badge shows "⚙️ refining..."
 * 
 * 2. Math specialist runs in background (1.2s later):
 *    - Replaces text with: "25 × 17 = 425. Here's how: 25 × 17 = 25 × (10 + 7) = 250 + 175 = 425"
 *    - Badge shows "✨ refined by math"
 * 
 * Result: User sees instant response, gets accurate answer 1.5s total
 */ 