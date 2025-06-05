/**
 * Progress Indicator for Agent-0 Background Refinement
 * Shows "🔄 refining..." while specialists work in background
 */

class Agent0ProgressIndicator {
    constructor() {
        this.indicators = new Map(); // messageId -> indicator element
        this.refinementTimers = new Map(); // messageId -> timer
    }

    /**
     * Show progress indicator for a message being refined
     * @param {string} messageId - Unique message identifier
     * @param {HTMLElement} messageElement - The message bubble element
     * @param {Object} response - Initial Agent-0 response
     */
    showRefinementProgress(messageId, messageElement, response) {
        // Only show if refinement is available
        if (!response.refinement_available) {
            return;
        }

        // Create progress indicator
        const indicator = document.createElement('div');
        indicator.className = 'agent0-progress-indicator';
        indicator.innerHTML = `
            <div class="refinement-status">
                <span class="spinner">🔄</span>
                <span class="status-text">refining...</span>
                <div class="progress-details">
                    <small>Specialists: ${response.wanted_specialists?.join(', ') || 'working'}</small>
                </div>
            </div>
        `;

        // Style the indicator
        indicator.style.cssText = `
            margin-top: 8px;
            padding: 8px 12px;
            background: #f8f9fa;
            border-left: 3px solid #007bff;
            border-radius: 4px;
            font-size: 0.9em;
            color: #6c757d;
            animation: pulse 1.5s ease-in-out infinite;
        `;

        // Add spinning animation
        const style = document.createElement('style');
        style.textContent = `
            @keyframes pulse {
                0%, 100% { opacity: 0.7; }
                50% { opacity: 1; }
            }
            .spinner {
                display: inline-block;
                animation: spin 1s linear infinite;
            }
            @keyframes spin {
                from { transform: rotate(0deg); }
                to { transform: rotate(360deg); }
            }
        `;
        document.head.appendChild(style);

        // Append to message
        messageElement.appendChild(indicator);
        this.indicators.set(messageId, indicator);

        // Set timeout for automatic cleanup (max 8 seconds)
        const timer = setTimeout(() => {
            this.hideRefinementProgress(messageId);
        }, 8000);
        this.refinementTimers.set(messageId, timer);

        console.log(`🔄 Showing refinement progress for message ${messageId}`);
    }

    /**
     * Update progress indicator with current status
     * @param {string} messageId - Message identifier
     * @param {string} status - Current refinement status
     * @param {Array} specialists - Active specialists
     */
    updateRefinementStatus(messageId, status, specialists = []) {
        const indicator = this.indicators.get(messageId);
        if (!indicator) return;

        const statusText = indicator.querySelector('.status-text');
        const progressDetails = indicator.querySelector('.progress-details small');

        if (statusText) {
            statusText.textContent = status || 'refining...';
        }

        if (progressDetails && specialists.length > 0) {
            progressDetails.textContent = `Specialists: ${specialists.join(', ')}`;
        }
    }

    /**
     * Hide progress indicator and optionally update message
     * @param {string} messageId - Message identifier
     * @param {Object} finalResponse - Final refined response (optional)
     */
    hideRefinementProgress(messageId, finalResponse = null) {
        const indicator = this.indicators.get(messageId);
        const timer = this.refinementTimers.get(messageId);

        if (timer) {
            clearTimeout(timer);
            this.refinementTimers.delete(messageId);
        }

        if (indicator) {
            // Show completion status briefly before removing
            if (finalResponse && finalResponse.text !== indicator.parentElement.querySelector('.message-text')?.textContent) {
                indicator.innerHTML = `
                    <div class="refinement-complete">
                        <span>✨</span> Response improved by specialists
                    </div>
                `;
                indicator.style.borderLeftColor = '#28a745';
                indicator.style.background = '#f8fff8';

                // Update message content
                const messageText = indicator.parentElement.querySelector('.message-text');
                if (messageText && finalResponse.text) {
                    messageText.textContent = finalResponse.text;
                }

                // Remove after showing completion
                setTimeout(() => {
                    indicator.remove();
                    this.indicators.delete(messageId);
                }, 2000);
            } else {
                // No improvement, just remove
                indicator.remove();
                this.indicators.delete(messageId);
            }
        }

        console.log(`✅ Refinement complete for message ${messageId}`);
    }

    /**
     * Clean up all indicators (e.g., on page navigation)
     */
    cleanup() {
        for (const [messageId, timer] of this.refinementTimers) {
            clearTimeout(timer);
        }
        
        for (const [messageId, indicator] of this.indicators) {
            indicator.remove();
        }

        this.indicators.clear();
        this.refinementTimers.clear();
    }
}

// Global instance
const progressIndicator = new Agent0ProgressIndicator();

/**
 * Integration with existing chat UI
 * Call this when receiving Agent-0 response
 */
function handleAgent0Response(messageId, messageElement, response) {
    // Show Agent-0 response immediately
    const messageText = messageElement.querySelector('.message-text');
    if (messageText) {
        messageText.textContent = response.text;
    }

    // Show progress indicator if refinement is happening
    if (response.refinement_available) {
        progressIndicator.showRefinementProgress(messageId, messageElement, response);

        // Poll for refinement updates (if supported)
        if (response.refinement_task || response.session_id) {
            pollForRefinementUpdates(messageId, response.session_id);
        }
    }
}

/**
 * Poll for refinement updates (optional - depends on backend support)
 */
async function pollForRefinementUpdates(messageId, sessionId) {
    const maxPollTime = 8000; // 8 seconds max
    const pollInterval = 1000; // Poll every second
    const startTime = Date.now();

    const poll = async () => {
        if (Date.now() - startTime > maxPollTime) {
            progressIndicator.hideRefinementProgress(messageId);
            return;
        }

        try {
            // This would need backend endpoint to check refinement status
            const response = await fetch(`/api/refinement-status/${sessionId}/${messageId}`);
            if (response.ok) {
                const status = await response.json();
                
                if (status.complete) {
                    progressIndicator.hideRefinementProgress(messageId, status.final_response);
                } else if (status.progress) {
                    progressIndicator.updateRefinementStatus(
                        messageId, 
                        status.status_text, 
                        status.active_specialists
                    );
                    setTimeout(poll, pollInterval);
                }
            } else {
                setTimeout(poll, pollInterval);
            }
        } catch (error) {
            console.warn('Refinement polling failed:', error);
            setTimeout(poll, pollInterval);
        }
    };

    setTimeout(poll, pollInterval);
}

// Example usage:
/*
// When receiving Agent-0 response from WebSocket or API:
const response = {
    text: "I can help with that calculation. [Agent-0 draft]",
    confidence: 0.25,
    refinement_available: true,
    wanted_specialists: ["math"],
    session_id: "session_123"
};

const messageElement = document.getElementById('message-456');
handleAgent0Response('msg-456', messageElement, response);
*/

// Global instance
const progressIndicator = new Agent0ProgressIndicator();

// Export for use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { Agent0ProgressIndicator };
} else if (typeof window !== 'undefined') {
    window.Agent0ProgressIndicator = Agent0ProgressIndicator;
    window.progressIndicator = progressIndicator;
} 