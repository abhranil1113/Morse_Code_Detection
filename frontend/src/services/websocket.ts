import { TelemetryPayload } from "../types";

export class VisionStreamSocket {
  private ws: WebSocket | null = null;
  private url: string;
  private onDataCallback: ((data: TelemetryPayload) => void) | null = null;

  constructor(url: string = "ws://127.0.0.1:8000/api/v1/ws/stream") {
    this.url = url;
  }

  connect(onData: (data: TelemetryPayload) => void) {
    this.onDataCallback = onData;
    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => {
      console.log("[WebSocket] Connected to EyeSpeak stream");
    };

    this.ws.onmessage = (event) => {
      try {
        const payload: TelemetryPayload = JSON.parse(event.data);
        if (this.onDataCallback) {
          this.onDataCallback(payload);
        }
      } catch (err) {
        console.error("[WebSocket] Parse error:", err);
      }
    };

    this.ws.onclose = () => {
      console.log("[WebSocket] Disconnected. Reconnecting in 2s...");
      setTimeout(() => this.connect(onData), 2000);
    };
  }

  sendFrame(base64Image: string) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: "frame", image: base64Image }));
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}
