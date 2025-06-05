/**
 * Enhanced chat interface for AutoGen Council
 * Styled to match the AutoGen Council Evolution Journey frontend
 */

document.addEventListener('DOMContentLoaded', () => {
  const app = document.getElementById('app');
  const state = { 
    msgs: [],
    isTyping: false
  };

  // Initialize the chat interface
  function initChat() {
    app.innerHTML = `
      <div class="chat-container">
        <div class="messages-container" id="messages"></div>
        <div class="input-container">
          <input id="inp" class="input-field" placeholder="Ask anything…" />
          <button id="send" class="send-button">Send</button>
        </div>
      </div>
    `;

    // Set up event listeners
    const sendButton = document.getElementById('send');
    const inputField = document.getElementById('inp');

    sendButton.addEventListener('click', sendMessage);
    inputField.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') {
        sendMessage();
      }
    });

    // Focus the input field
    inputField.focus();
  }

  // Render all messages
  function renderMessages() {
    const messagesContainer = document.getElementById('messages');
    messagesContainer.innerHTML = '';

    // Render each message
    state.msgs.forEach(msg => {
      const messageEl = document.createElement('div');
      messageEl.className = `message ${msg.isUser ? 'message-user' : 'message-ai'}`;
      
      // Format the message content
      let content = msg.isUser ? msg.text : formatAIResponse(msg.text);
      
      messageEl.innerHTML = `
        <div>${content}</div>
        <div class="message-meta">
          ${msg.isUser ? '' : `<span>${msg.ms} ms • $${msg.$}</span>`}
          <span>${formatTimestamp(msg.timestamp)}</span>
        </div>
      `;
      
      // Add consensus information if available
      if (!msg.isUser && msg.metadata && msg.metadata.consensus_fusion && msg.metadata.candidates && msg.metadata.candidates.length > 1) {
        const consensusInfo = document.createElement('div');
        consensusInfo.className = 'consensus-info';
        consensusInfo.innerHTML = `
          <div class="consensus-badge">
            🤝 <strong>Council Consensus</strong> (${msg.metadata.candidates.length} specialists)
          </div>
          <details class="head-votes">
            <summary>📊 View individual specialist votes</summary>
            <div class="specialist-votes">
              ${msg.metadata.candidates.map(candidate => `
                <div class="vote-item">
                  <span class="specialist-name">${candidate.specialist}</span>
                  <span class="confidence">${(candidate.confidence * 100).toFixed(0)}%</span>
                  <div class="vote-text">${candidate.text}</div>
                </div>
              `).join('')}
            </div>
          </details>
        `;
        messageEl.appendChild(consensusInfo);
      }
      
      messagesContainer.appendChild(messageEl);
    });

    // Add typing indicator if needed
    if (state.isTyping) {
      const typingIndicator = document.createElement('div');
      typingIndicator.className = 'typing-indicator';
      typingIndicator.innerHTML = `
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
      `;
      messagesContainer.appendChild(typingIndicator);
    }

    // Scroll to bottom
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    // Apply syntax highlighting to code blocks
    if (window.hljs) {
      document.querySelectorAll('pre code').forEach((el) => {
        hljs.highlightElement(el);
      });
    }

    // Show performance info
    if (state.msgs.length > 0 && state.msgs[state.msgs.length - 1].metadata && state.msgs[state.msgs.length - 1].metadata.routing_info && state.msgs[state.msgs.length - 1].metadata.routing_info.total_latency_ms) {
      let perfInfo = `⚡ ${state.msgs[state.msgs.length - 1].metadata.routing_info.total_latency_ms}ms`;
      if (state.msgs[state.msgs.length - 1].metadata.routing_info.consensus_fusion) {
        perfInfo += ` (${state.msgs[state.msgs.length - 1].metadata.routing_info.candidates.length} heads fused)`;
      }
      addMessage('system', perfInfo);
    }
  }

  // Format AI responses with code highlighting and other enhancements
  function formatAIResponse(text) {
    // Add code block formatting
    let formatted = text.replace(/```(\w+)?\n([\s\S]*?)```/g, (match, language, code) => {
      const lang = language || 'plaintext';
      return `
        <div class="code-container">
          <div class="code-header">${lang}</div>
          <button class="copy-button" data-code="${escapeHtml(code.trim())}">Copy</button>
          <pre><code class="language-${lang}">${escapeHtml(code)}</code></pre>
        </div>
      `;
    });

    // Add status indicators
    formatted = formatted.replace(/🟢 ([^<]+)/g, '<span class="status"><span class="status-dot status-success"></span>$1</span>');
    formatted = formatted.replace(/🟠 ([^<]+)/g, '<span class="status"><span class="status-dot status-warning"></span>$1</span>');
    formatted = formatted.replace(/🔴 ([^<]+)/g, '<span class="status"><span class="status-dot status-error"></span>$1</span>');

    return formatted;
  }

  // Send a message
  async function sendMessage() {
    const inputField = document.getElementById('inp');
    const text = inputField.value.trim();
    
    if (!text) return;
    
    // Clear input field
    inputField.value = '';
    
    // Add user message to state
    state.msgs.push({
      isUser: true,
      text: escapeHtml(text),
      timestamp: new Date()
    });
    
    // Show typing indicator
    state.isTyping = true;
    renderMessages();
    
    // Disable send button while processing
    document.getElementById('send').disabled = true;
    
    try {
      const t0 = performance.now();
      
      // Use the new enhanced voting endpoint with specialist priority
      const res = await fetch('/vote', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          prompt: text,
          candidates: ["math_specialist", "code_specialist", "logic_specialist", "knowledge_specialist", "mistral_general"], // Fixed specialist names
          top_k: 1
        })
      });
      
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      }
      
      const j = await res.json();
      const t1 = performance.now();
      
      // Extract response from new API format
      const responseText = j.text || j.answer || "No response received";
      const modelUsed = j.model_used || j.model || "unknown";
      const latencyMs = j.latency_ms || Math.round(t1 - t0);
      const confidence = j.confidence || 0.5;
      const totalCost = j.total_cost_cents || 0;
      
      // 🏁 USE FIRST-TOKEN LATENCY for honest "Fast response" metrics
      const firstTokenLatency = j.first_token_latency_ms || latencyMs;
      const perceivedSpeed = j.perceived_speed || (firstTokenLatency < 500 ? "fast" : "normal");
      const totalLatency = j.total_latency_ms || latencyMs;
      
      // Format specialist routing info
      let specialistInfo = "";
      if (j.candidates && j.candidates.length > 0) {
        specialistInfo = ` • ${j.candidates[0]} specialist`;
      }
      
      // 🚫 HIDE MATH SPECIALIST SPAM: Don't show specialist tag if math head won with low confidence
      const isMathSpam = (modelUsed.includes("math") || specialistInfo.includes("math")) && confidence < 0.8;
      if (isMathSpam) {
        specialistInfo = ""; // Hide the spam
      }
      
      // Add confidence indicator
      let confidenceIcon = "🟢";
      let confidenceClass = "high";
      if (confidence < 0.5) {
        confidenceIcon = "🔴";
        confidenceClass = "low";
      } else if (confidence < 0.7) {
        confidenceIcon = "🟠";
        confidenceClass = "medium";
      }
      
      // Add specialist type emoji
      let specialistEmoji = "🤖";
      if (modelUsed.includes("math")) specialistEmoji = "🧮";
      else if (modelUsed.includes("code")) specialistEmoji = "🔧";
      else if (modelUsed.includes("logic")) specialistEmoji = "🧠";
      else if (modelUsed.includes("knowledge") || modelUsed.includes("rag")) specialistEmoji = "📚";
      else if (modelUsed.includes("mistral") || modelUsed.includes("openai")) specialistEmoji = "☁️";
      
      // 🎯 ENHANCED BANNER: Hide math spam, use honest latency
      let specialistHeader = "";
      if (!isMathSpam) {
        specialistHeader = `${confidenceIcon} **${specialistEmoji} ${modelUsed}** (${(confidence * 100).toFixed(0)}% confidence${specialistInfo})`;
      }
      
      // 🏁 HONEST PERFORMANCE METRICS: Use first-token latency for perceived speed
      const performanceInfo = firstTokenLatency < 200 
        ? `⚡ Lightning fast: ${firstTokenLatency.toFixed(0)}ms` 
        : firstTokenLatency < 500 
        ? `🚀 Fast response: ${firstTokenLatency.toFixed(0)}ms`
        : `🕐 Response: ${firstTokenLatency.toFixed(0)}ms`;
      
      // Show total latency in ops details (for debugging)
      const opsDetails = totalLatency > firstTokenLatency + 100 
        ? ` (total: ${totalLatency.toFixed(0)}ms)`
        : "";
        
      // Add AI response to state with enhanced metadata
      const responseHeader = specialistHeader ? `${specialistHeader}\n\n` : "";
      state.msgs.push({
        isUser: false,
        text: `${responseHeader}${responseText}\n\n---\n💨 ${performanceInfo}${opsDetails} • 💰 $${(totalCost / 100).toFixed(3)}`,
        ms: firstTokenLatency, // Use first-token latency for perceived speed
        $: (totalCost / 100).toFixed(3), // Convert cents to dollars
        timestamp: new Date(),
        metadata: {
          model: modelUsed,
          confidence: confidence,
          confidenceClass: confidenceClass,
          specialists: j.candidates || [],
          routing_info: j.voting_stats || {},
          consensus_fusion: j.consensus_fusion || false,
          candidates: j.candidates || [],
          first_token_latency_ms: firstTokenLatency,
          total_latency_ms: totalLatency,
          perceived_speed: perceivedSpeed,
          math_spam_hidden: isMathSpam
        }
      });

      // Display the response
      renderMessages();
    } catch (error) {
      console.error('Chat request failed:', error);
      
      // Handle error with specialist fallback info
      let errorMessage = `Sorry, there was an error processing your request: ${error.message}`;
      
      // Try the direct hybrid endpoint as fallback
      try {
        const fallbackRes = await fetch('/hybrid', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({prompt: text})
        });
        
        if (fallbackRes.ok) {
          const fallbackData = await fallbackRes.json();
          const t1 = performance.now();
          
          state.msgs.push({
            isUser: false,
            text: `🟠 **Fallback Response** (${fallbackData.skill_type} specialist)\n\n${fallbackData.text}`,
            ms: fallbackData.latency_ms || Math.round(t1 - t0),
            $: '0.00',
            timestamp: new Date(),
            metadata: {
              model: fallbackData.model,
              skill_type: fallbackData.skill_type,
              confidence: fallbackData.confidence,
              fallback: true
            }
          });
        } else {
          throw new Error('Fallback also failed');
        }
      } catch (fallbackError) {
        // Final error handling
        state.msgs.push({
          isUser: false,
          text: `🔴 **System Error**\n\n${errorMessage}\n\nPlease check that the AutoGen Council server is running and try again.`,
          ms: 0,
          $: '0.00',
          timestamp: new Date(),
          metadata: {
            error: true,
            original_error: error.message,
            fallback_error: fallbackError.message
          }
        });
      }
    } finally {
      // Hide typing indicator and re-enable send button
      state.isTyping = false;
      document.getElementById('send').disabled = false;
      renderMessages();
      
      // Set up copy buttons
      setupCopyButtons();
    }
  }

  // Set up copy buttons for code blocks
  function setupCopyButtons() {
    document.querySelectorAll('.copy-button').forEach(button => {
      button.addEventListener('click', () => {
        const code = button.getAttribute('data-code');
        navigator.clipboard.writeText(code).then(() => {
          const originalText = button.textContent;
          button.textContent = 'Copied!';
          button.style.backgroundColor = 'rgba(16, 185, 129, 0.2)';
          
          setTimeout(() => {
            button.textContent = originalText;
            button.style.backgroundColor = '';
          }, 2000);
        });
      });
    });
  }

  // Format timestamp
  function formatTimestamp(date) {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  // Escape HTML to prevent XSS
  function escapeHtml(unsafe) {
    return unsafe
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // Initialize the chat
  initChat();
  
  // Add enhanced welcome messages for the new consensus system
  state.msgs.push({
    isUser: false,
    text: `🗳️ **AutoGen Council v3.0.0 - Consensus Democracy System**

🟢 **System Status: OPERATIONAL** 
🤝 **New Feature: Council Consensus Fusion**
⚡ **Performance: ~150ms consensus latency**

Welcome to your enhanced Council system! Now featuring **true consensus democracy**:

**🤝 Consensus Fusion** - All 5 specialists contribute to every answer  
**🧮 Math Specialist** - Lightning-fast SymPy calculations  
**🔧 Code Specialist** - DeepSeek Coder with sandbox execution  
**🧠 Logic Specialist** - SWI-Prolog reasoning engine  
**📚 Knowledge Specialist** - FAISS vector search  
**☁️ Cloud Fallback** - Mistral/OpenAI for complex queries  

🎨 **Try these examples to see consensus in action:**
• \`What is 5*7 and why?\` - **Math + explanation fusion**
• \`write python code with comments\` - **Code + knowledge fusion**  
• \`explain quantum computing\` - **Multi-specialist consensus**

🗳️ **Look for the "Council Consensus" badge and click "View individual specialist votes" to see how each head contributed!**`,
    ms: 0,
    $: '0.00',
    timestamp: new Date(Date.now() - 60000),
    metadata: {
      model: "system",
      welcome: true,
      version: "3.0.0-consensus"
    }
  });
  
  renderMessages();
});