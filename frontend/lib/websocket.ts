export type AgentEvent = {
  type: "thought" | "tool_call" | "tool_result" | "message_info" | "message_ask" | "message_result" | "agent_error" | "session_end";
  content?: string;
  text?: string;
  tool?: string;
  params?: any;
  output?: string;
  error?: string;
  success?: boolean;
  iteration?: number;
};

export class ArchimedesSocket {
  private socket: WebSocket | null = null;
  private sessionId: string;
  private onMessage: (event: AgentEvent) => void;
  private baseUrl: string;

  constructor(sessionId: string, onMessage: (event: AgentEvent) => void) {
    this.sessionId = sessionId;
    this.onMessage = onMessage;
    // Use the environment variable or default to localhost:8001
    this.baseUrl = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8001/ws";
  }

  connect() {
    try {
      const url = `${this.baseUrl}/${this.sessionId}`;
      console.log(`Connecting to WebSocket: ${url}`);
      this.socket = new WebSocket(url);

      this.socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.onMessage(data as AgentEvent);
        } catch (err) {
          console.error("Failed to parse WebSocket message:", err);
        }
      };

      this.socket.onclose = () => {
        console.log("WebSocket connection closed. Retrying in 3s...");
        setTimeout(() => {
          if (this.socket) this.connect();
        }, 3000);
      };

      this.socket.onerror = (err) => {
        console.error("WebSocket error:", err);
      };
    } catch (error) {
      console.error("Connection failed:", error);
    }
  }

  disconnect() {
    if (this.socket) {
      this.socket.onclose = null; // Prevent auto-reconnect
      this.socket.close();
      this.socket = null;
    }
  }

  getReadyState(): number {
    return this.socket ? this.socket.readyState : WebSocket.CLOSED;
  }

  sendTask(task: string, agentId?: string) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
    this.socket.send(JSON.stringify({ type: 'task', task, agent_id: agentId || 'archimedes-cosmo' }));

    } else {
      console.error("WebSocket is not open. Cannot send task.");
      // Attempt to reconnect and send? For now just log.
    }
  }
}
