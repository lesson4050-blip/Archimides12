export type AgentEvent = {
  type: "thought" | "tool_call" | "tool" | "tool_result" | "message_info" | "message_ask" | "message_result" | "agent_error" | "session_end" | "artifact" | "novnc_ready" | "plan_update" | "session_ready" | "session_queued" | "confidence" | "suggestions" | "token" | "file_artifact" | "browser_navigate" | "desktop_frame" | "canvas_presentation" | "verification_report" | "tool_verification" | "economy_report" | "audit_trail" | "proactive_result";
  content?: string;
  text?: string;
  tool?: string;
  params?: any;
  output?: string;
  error?: string;
  success?: boolean;
  iteration?: number;
  // Artifact fields
  name?: string;
  path?: string;
  language?: string;
  // File Artifact fields
  filename?: string;
  mime_type?: string;
  data?: any;
  size_kb?: number;
  preview_url?: string;
  label?: string;
  // Browser fields
  title?: string;
  url?: string;
  // Canvas Presentation fields
  topic?: string;
  artifact_path?: string;
  slide_count?: number;
  // Plan updates
  phases?: any[];
  // Message result attachments
  message?: string;
  attachments?: string[];
};

export class ArchimedesSocket {
  private socket: WebSocket | null = null;
  private sessionId: string;
  private onMessage: (event: AgentEvent) => void;
  private baseUrl: string;
  private shouldReconnect: boolean = true;

  constructor(sessionId: string, onMessage: (event: AgentEvent) => void) {
    this.sessionId = sessionId;
    this.onMessage = onMessage;
    // Use the environment variable or default to localhost:8000
    this.baseUrl = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws";
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
        console.log("WebSocket connection closed.");
        if (this.shouldReconnect) {
          console.log("Retrying in 3s...");
          setTimeout(() => {
            this.connect();
          }, 3000);
        }
      };

      this.socket.onerror = (err) => {
        console.error("WebSocket error:", err);
      };
    } catch (error) {
      console.error("Connection failed:", error);
    }
  }

  disconnect() {
    this.shouldReconnect = false;
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
  }

  getReadyState(): number {
    return this.socket ? this.socket.readyState : WebSocket.CLOSED;
  }

  sendTask(task: string, agentId?: string, mode?: string, webSearchEnabled?: boolean, globeEnabled?: boolean, taskHint?: string) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify({ 
        type: 'task', 
        task, 
        agent_id: agentId || 'archimedes-cosmo',
        mode: mode || 'planning',
        use_web_search: webSearchEnabled,
        use_globe: globeEnabled,
        task_hint: taskHint
      }));
    } else {
      console.error("WebSocket is not open. Cannot send task.");
      // Attempt to reconnect and send? For now just log.
    }
  }
}
