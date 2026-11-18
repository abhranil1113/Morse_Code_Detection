import React, { useEffect, useRef, useState } from "react";
import { TelemetryPayload } from "../../types";

interface CameraFeedProps {
  onPermissionGranted?: () => void;
  telemetry?: TelemetryPayload;
  onFrameCapture?: (base64Image: string) => void;
}

export function stopAllCameraStreams() {
  // 1. Stop all registered window streams
  if (typeof window !== "undefined" && (window as any).__eyespeak_active_streams) {
    const streams: MediaStream[] = (window as any).__eyespeak_active_streams;
    streams.forEach((stream) => {
      try {
        stream.getTracks().forEach((track) => {
          track.stop();
          track.enabled = false;
        });
      } catch (e) {}
    });
    (window as any).__eyespeak_active_streams = [];
  }

  // 2. Stop all video elements in DOM
  if (typeof document !== "undefined") {
    document.querySelectorAll("video").forEach((videoEl) => {
      if (videoEl.srcObject) {
        try {
          const s = videoEl.srcObject as MediaStream;
          s.getTracks().forEach((track) => {
            track.stop();
            track.enabled = false;
          });
        } catch (e) {}
        videoEl.srcObject = null;
      }
      try {
        videoEl.pause();
      } catch (e) {}
    });
  }
}

export const CameraFeed: React.FC<CameraFeedProps> = ({ onPermissionGranted, telemetry, onFrameCapture }) => {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const isMountedRef = useRef<boolean>(true);
  const [hasPermission, setHasPermission] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string>("");

  // Independent eye-state evaluation (GREEN = OPEN, RED = CLOSED, GREY = UNAVAILABLE)
  const leftEyeState = telemetry?.left_eye_state || (telemetry?.eye_state === "CLOSED" ? "CLOSED" : telemetry?.eye_state === "OPEN" ? "OPEN" : "UNAVAILABLE");
  const rightEyeState = telemetry?.right_eye_state || (telemetry?.eye_state === "CLOSED" ? "CLOSED" : telemetry?.eye_state === "OPEN" ? "OPEN" : "UNAVAILABLE");
  const overallState = telemetry?.overall_eye_state || (telemetry?.eye_state === "CLOSED" ? "CLOSED" : telemetry?.eye_state === "OPEN" ? "OPEN" : "UNAVAILABLE");

  const leftEyeColor = leftEyeState === "OPEN" ? "#10b981" : leftEyeState === "CLOSED" ? "#f43f5e" : "#64748b";
  const rightEyeColor = rightEyeState === "OPEN" ? "#10b981" : rightEyeState === "CLOSED" ? "#f43f5e" : "#64748b";

  let statusText = "EYES NOT DETECTED";
  let statusColor = "#64748b";
  if (telemetry?.face_detected) {
    if (overallState === "CLOSED") {
      statusText = "BLINK DETECTED";
      statusColor = "#f43f5e";
    } else if (overallState === "OPEN") {
      statusText = "EYES OPEN";
      statusColor = "#10b981";
    } else if (overallState === "PARTIAL") {
      statusText = "PARTIAL BLINK";
      statusColor = "#f59e0b";
    } else {
      statusText = "UNCERTAIN";
      statusColor = "#64748b";
    }
  }

  const stopCamera = () => {
    stopAllCameraStreams();
    streamRef.current = null;
    if (videoRef.current) {
      videoRef.current.srcObject = null;
      try {
        videoRef.current.pause();
      } catch (e) {}
    }
    setHasPermission(false);
  };

  const requestCamera = async () => {
    try {
      setErrorMsg("");

      if (!isMountedRef.current) return;

      // Verify browser MediaDevices support (requires secure context or localhost)
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        // Try legacy fallback
        const legacyGetUserMedia =
          (navigator as any).getUserMedia ||
          (navigator as any).webkitGetUserMedia ||
          (navigator as any).mozGetUserMedia;

        if (legacyGetUserMedia) {
          legacyGetUserMedia.call(
            navigator,
            { video: { width: 640, height: 480, facingMode: "user" } },
            (stream: MediaStream) => {
              if (!isMountedRef.current) {
                stream.getTracks().forEach((t) => t.stop());
                return;
              }
              if (typeof window !== "undefined") {
                (window as any).__eyespeak_active_streams = (window as any).__eyespeak_active_streams || [];
                (window as any).__eyespeak_active_streams.push(stream);
              }
              if (typeof window !== "undefined") {
        (window as any).__eyespeak_active_streams = (window as any).__eyespeak_active_streams || [];
        (window as any).__eyespeak_active_streams.push(stream);
      }

      streamRef.current = stream;
              if (videoRef.current) {
                videoRef.current.srcObject = stream;
                videoRef.current.play().catch(() => {});
              }
              setHasPermission(true);
              if (onPermissionGranted) onPermissionGranted();
            },
            (err: any) => {
              setErrorMsg(err.message || "Camera access denied.");
            }
          );
          return;
        }

        setErrorMsg(
          "Camera API is disabled by the browser: Please access this app via http://localhost:5173 or http://127.0.0.1:5173. Browsers block webcam access on network IP addresses (e.g. 192.168.x.x) unless using HTTPS."
        );
        return;
      }

      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480, facingMode: "user" },
      });

      // If component unmounted or user logged out while awaiting camera permission:
      if (!isMountedRef.current) {
        stream.getTracks().forEach((track) => {
          try {
            track.stop();
            track.enabled = false;
          } catch (e) {}
        });
        return;
      }

      if (typeof window !== "undefined") {
        (window as any).__eyespeak_active_streams = (window as any).__eyespeak_active_streams || [];
        (window as any).__eyespeak_active_streams.push(stream);
      }

      streamRef.current = stream;

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.play().catch(() => {});
      }
      setHasPermission(true);
      if (onPermissionGranted) onPermissionGranted();
    } catch (err: any) {
      if (!isMountedRef.current) return;
      console.error("Camera access error:", err);
      if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
        setErrorMsg("Browser permission blocked: Click the lock/tune icon in the browser address bar (left of localhost:5173) and switch Camera to 'Allow', then refresh.");
      } else if (err.name === "NotReadableError" || err.name === "TrackStartError") {
        setErrorMsg("Camera is in use by another app (e.g., Python OpenCV vision agent, Zoom, or Windows Camera). Close the other app or continue using the Python agent.");
      } else if (err.name === "NotFoundError" || err.name === "DevicesNotFoundError") {
        setErrorMsg("No camera detected. Please connect a webcam.");
      } else {
        setErrorMsg(err.message || "Camera permission denied or camera is in use by another app.");
      }
    }
  };

  useEffect(() => {
    isMountedRef.current = true;
    requestCamera();

    const handleForceStop = () => {
      stopCamera();
    };
    window.addEventListener("eyespeak:stop-camera", handleForceStop);

    return () => {
      isMountedRef.current = false;
      window.removeEventListener("eyespeak:stop-camera", handleForceStop);
      stopCamera();
    };
  }, []);

  // Stream browser webcam frames to backend over WebSocket for MediaPipe AI tracking
  useEffect(() => {
    if (!hasPermission || !onFrameCapture) return;

    if (!canvasRef.current) {
      canvasRef.current = document.createElement("canvas");
      canvasRef.current.width = 640;
      canvasRef.current.height = 480;
    }

    const interval = setInterval(() => {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      if (!video || video.readyState < 2 || !canvas) return;

      const ctx = canvas.getContext("2d");
      if (!ctx) return;

      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      const dataUrl = canvas.toDataURL("image/jpeg", 0.82);
      onFrameCapture(dataUrl);
    }, 55); // ~18 FPS stream with high-fidelity resolution for MediaPipe FaceMesh

    return () => clearInterval(interval);
  }, [hasPermission, onFrameCapture]);

  return (
    <div
      style={{
        position: "relative",
        borderRadius: "12px",
        overflow: "hidden",
        backgroundColor: "#020617",
        border: "1px solid #334155",
        aspectRatio: "4/3",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <video
        ref={videoRef}
        playsInline
        muted
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          transform: "scaleX(-1)", // Mirror display
          display: hasPermission ? "block" : "none",
        }}
      />

      {/* AI Eye Focus Target Squares Overlay */}
      {hasPermission && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            pointerEvents: "none",
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between",
            padding: "12px",
          }}
        >
          {/* Top HUD Status */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span
              style={{
                backgroundColor: "rgba(15, 23, 42, 0.85)",
                color: statusColor,
                padding: "4px 10px",
                borderRadius: "4px",
                fontSize: "11px",
                fontWeight: 700,
                letterSpacing: "0.5px",
                border: `1px solid ${statusColor}`,
              }}
            >
              {statusText}
            </span>
            <span
              style={{
                backgroundColor: "rgba(15, 23, 42, 0.75)",
                color: "#94a3b8",
                padding: "3px 8px",
                borderRadius: "4px",
                fontSize: "11px",
              }}
            >
              GAZE: {telemetry?.gaze_direction || "CENTER"}
            </span>
          </div>

          {/* Dynamic Eye Target Squares Locked on Detected Eye Positions */}
          {telemetry?.face_detected ? (
            <>
              {/* Left Eye Target Square */}
              <div
                style={{
                  position: "absolute",
                  left: telemetry.left_box
                    ? `${(1 - telemetry.left_box.x - telemetry.left_box.width) * 100}%`
                    : "36%",
                  top: telemetry.left_box
                    ? `${telemetry.left_box.y * 100}%`
                    : "38%",
                  width: telemetry.left_box
                    ? `${telemetry.left_box.width * 100}%`
                    : "64px",
                  height: telemetry.left_box
                    ? `${telemetry.left_box.height * 100}%`
                    : "52px",
                  minWidth: "48px",
                  minHeight: "36px",
                  border: `2px solid ${leftEyeColor}`,
                  borderRadius: "6px",
                  backgroundColor: leftEyeState === "CLOSED" ? "rgba(244, 63, 94, 0.2)" : leftEyeState === "OPEN" ? "rgba(16, 185, 129, 0.12)" : "rgba(100, 116, 139, 0.12)",
                  boxShadow: `0 0 12px ${leftEyeColor}40`,
                  transition: "left 0.06s ease-out, top 0.06s ease-out, width 0.06s ease-out, height 0.06s ease-out",
                  pointerEvents: "none",
                }}
              >
                <span
                  style={{
                    position: "absolute",
                    top: "-18px",
                    left: "2px",
                    fontSize: "10px",
                    color: leftEyeColor,
                    fontWeight: 700,
                    letterSpacing: "0.5px",
                    textShadow: "0 1px 3px rgba(0,0,0,0.8)",
                  }}
                >
                  L-EYE [{leftEyeState}{telemetry?.left_eye_visibility ? ` | ${telemetry.left_eye_visibility.slice(0, 4)}` : ""}]
                </span>
                {/* Corner crosshairs */}
                <div style={{ position: "absolute", top: -2, left: -2, width: 8, height: 8, borderTop: `2px solid ${leftEyeColor}`, borderLeft: `2px solid ${leftEyeColor}` }} />
                <div style={{ position: "absolute", top: -2, right: -2, width: 8, height: 8, borderTop: `2px solid ${leftEyeColor}`, borderRight: `2px solid ${leftEyeColor}` }} />
                <div style={{ position: "absolute", bottom: -2, left: -2, width: 8, height: 8, borderBottom: `2px solid ${leftEyeColor}`, borderLeft: `2px solid ${leftEyeColor}` }} />
                <div style={{ position: "absolute", bottom: -2, right: -2, width: 8, height: 8, borderBottom: `2px solid ${leftEyeColor}`, borderRight: `2px solid ${leftEyeColor}` }} />
              </div>

              {/* Right Eye Target Square */}
              <div
                style={{
                  position: "absolute",
                  left: telemetry.right_box
                    ? `${(1 - telemetry.right_box.x - telemetry.right_box.width) * 100}%`
                    : "54%",
                  top: telemetry.right_box
                    ? `${telemetry.right_box.y * 100}%`
                    : "38%",
                  width: telemetry.right_box
                    ? `${telemetry.right_box.width * 100}%`
                    : "64px",
                  height: telemetry.right_box
                    ? `${telemetry.right_box.height * 100}%`
                    : "52px",
                  minWidth: "48px",
                  minHeight: "36px",
                  border: `2px solid ${rightEyeColor}`,
                  borderRadius: "6px",
                  backgroundColor: rightEyeState === "CLOSED" ? "rgba(244, 63, 94, 0.2)" : rightEyeState === "OPEN" ? "rgba(16, 185, 129, 0.12)" : "rgba(100, 116, 139, 0.12)",
                  boxShadow: `0 0 12px ${rightEyeColor}40`,
                  transition: "left 0.06s ease-out, top 0.06s ease-out, width 0.06s ease-out, height 0.06s ease-out",
                  pointerEvents: "none",
                }}
              >
                <span
                  style={{
                    position: "absolute",
                    top: "-18px",
                    left: "2px",
                    fontSize: "10px",
                    color: rightEyeColor,
                    fontWeight: 700,
                    letterSpacing: "0.5px",
                    textShadow: "0 1px 3px rgba(0,0,0,0.8)",
                  }}
                >
                  R-EYE [{rightEyeState}{telemetry?.right_eye_visibility ? ` | ${telemetry.right_eye_visibility.slice(0, 4)}` : ""}]
                </span>
                {/* Corner crosshairs */}
                <div style={{ position: "absolute", top: -2, left: -2, width: 8, height: 8, borderTop: `2px solid ${rightEyeColor}`, borderLeft: `2px solid ${rightEyeColor}` }} />
                <div style={{ position: "absolute", top: -2, right: -2, width: 8, height: 8, borderTop: `2px solid ${rightEyeColor}`, borderRight: `2px solid ${rightEyeColor}` }} />
                <div style={{ position: "absolute", bottom: -2, left: -2, width: 8, height: 8, borderBottom: `2px solid ${rightEyeColor}`, borderLeft: `2px solid ${rightEyeColor}` }} />
                <div style={{ position: "absolute", bottom: -2, right: -2, width: 8, height: 8, borderBottom: `2px solid ${rightEyeColor}`, borderRight: `2px solid ${rightEyeColor}` }} />
              </div>
            </>
          ) : (
            <div
              style={{
                position: "absolute",
                top: "42%",
                left: "50%",
                transform: "translate(-50%, -50%)",
                backgroundColor: "rgba(15, 23, 42, 0.90)",
                padding: "10px 18px",
                borderRadius: "8px",
                border: "1px dashed #38bdf8",
                color: "#e2e8f0",
                fontSize: "12px",
                textAlign: "center",
                maxWidth: "300px",
                boxShadow: "0 4px 14px rgba(0,0,0,0.6)",
              }}
            >
              <div style={{ fontWeight: 600, color: "#38bdf8", marginBottom: "4px" }}>
                AI Vision Seeking Face & Eyes
              </div>
              <div style={{ color: "#94a3b8", fontSize: "11px", lineHeight: "1.4" }}>
                Position face towards camera in normal lighting. Ensure backend server is running.
              </div>
            </div>
          )}

          {/* Bottom EAR & Head Orientation HUD */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "6px" }}>
            <span
              style={{
                backgroundColor: "rgba(15, 23, 42, 0.75)",
                color: "#e2e8f0",
                padding: "2px 8px",
                borderRadius: "4px",
                fontSize: "11px",
              }}
            >
              EAR: {telemetry ? telemetry.ear.toFixed(2) : "0.28"}
            </span>

            {telemetry?.head_yaw !== undefined && (
              <span
                style={{
                  backgroundColor: "rgba(15, 23, 42, 0.75)",
                  color: "#38bdf8",
                  padding: "2px 8px",
                  borderRadius: "4px",
                  fontSize: "11px",
                  fontWeight: 600,
                }}
              >
                HEAD: {telemetry.head_yaw > 0 ? "+" : ""}{Math.round(telemetry.head_yaw)}° YAW
              </span>
            )}

            <span
              style={{
                backgroundColor: "rgba(15, 23, 42, 0.75)",
                color: telemetry?.tracking_status === "REACQUIRING" ? "#f59e0b" : "#38bdf8",
                padding: "2px 8px",
                borderRadius: "4px",
                fontSize: "11px",
              }}
            >
              BUFFER: {telemetry?.current_buffer || "—"}
            </span>
          </div>
        </div>
      )}

      {!hasPermission && (
        <div style={{ textAlign: "center", padding: "20px" }}>
          <p style={{ color: "#94a3b8", fontSize: "0.88rem", marginBottom: "12px", lineHeight: 1.5 }}>
            {errorMsg || "Requesting camera access..."}
          </p>
          <button
            onClick={requestCamera}
            style={{
              padding: "8px 16px",
              backgroundColor: "#2563eb",
              color: "white",
              border: "none",
              borderRadius: "6px",
              cursor: "pointer",
              fontWeight: 600,
              fontSize: "0.88rem",
            }}
          >
            Grant Camera Access
          </button>
          <div style={{ marginTop: "14px", fontSize: "0.78rem", color: "#64748b" }}>
            💡 <strong>Note:</strong> If running <code>python vision/agent/main.py</code>, OpenCV is directly reading the webcam and broadcasting live telemetry to the indicators below.
          </div>
        </div>
      )}
    </div>
  );
};
