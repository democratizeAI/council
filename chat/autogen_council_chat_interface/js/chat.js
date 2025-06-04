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
      
      // Send request to backend
      const res = await fetch('/vote', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({prompt: text})
      });
      
      const j = await res.json();
      const t1 = performance.now();
      
      // Add AI response to state
      state.msgs.push({
        isUser: false,
        text: j.answer,
        ms: j.meta.latency_ms || Math.round(t1 - t0),
        $: j.meta.cost_usd || '0.00',
        timestamp: new Date()
      });
    } catch (error) {
      // Handle error
      state.msgs.push({
        isUser: false,
        text: `Sorry, there was an error processing your request: ${error.message}`,
        ms: 0,
        $: '0.00',
        timestamp: new Date()
      });
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
  
  // Add some welcome messages for demonstration
  state.msgs.push({
    isUser: false,
    text: "Welcome to the AutoGen Council Chat! How can I assist you today?",
    ms: 574,
    $: '0.04',
    timestamp: new Date(Date.now() - 60000)
  });
  
  renderMessages();
});
