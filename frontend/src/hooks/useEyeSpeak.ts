import { useState, useEffect, useRef, useCallback } from "react";
import { TelemetryPayload } from "../types";
import { VisionStreamSocket } from "../services/websocket";

export function useEyeSpeak() {
  const [telemetry, setTelemetry] = useState<TelemetryPayload>({
    face_detected: false,
    ear: 0.0,
    eye_state: "UNKNOWN",
    confidence: 0.0,
    current_buffer: "",
    decoded_text: "",
    gaze_direction: "CENTER",
  });

  const [isConnected, setIsConnected] = useState<boolean>(false);
  const socketRef = useRef<VisionStreamSocket | null>(null);

  useEffect(() => {
    const socket = new VisionStreamSocket();
    socketRef.current = socket;
    socket.connect((data) => {
      setTelemetry(data);
      setIsConnected(true);
    });

    return () => {
      socket.disconnect();
      socketRef.current = null;
    };
  }, []);

  const sendFrame = useCallback((base64Image: string) => {
    socketRef.current?.sendFrame(base64Image);
  }, []);

  return { telemetry, isConnected, sendFrame };
}
