
class ChatWebSocket {
  constructor() {
    this.ws = null;
    this.messageHandlers = new Map();
  }

  connect() {
    this.ws = new WebSocket("ws://localhost:8000/ws");
    
    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      const handler = this.messageHandlers.get(data.type);
      if (handler) handler(data);
    };
    
    this.ws.onopen = () => console.log("WebSocket connected");
    this.ws.onerror = (err) => console.error("WebSocket error:", err);
    this.ws.onclose = () => this.reconnect();
  }

  reconnect() {
    setTimeout(() => this.connect(), 1000);
  }

  sendChat(prompt) {
    if (this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({
        type: "chat",
        prompt: prompt
      }));
    }
  }

  onToken(handler) {
    this.messageHandlers.set("token", handler);
  }

  onComplete(handler) {
    this.messageHandlers.set("complete", handler);
  }
}

// Usage
const chatWS = new ChatWebSocket();
chatWS.connect();

chatWS.onToken((data) => {
  appendTokenToChatBubble(data.token);
});

chatWS.onComplete((data) => {
  finalizeChatResponse(data.meta);
});
