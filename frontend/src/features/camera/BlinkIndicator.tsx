import React from "react";
import { TelemetryPayload } from "../../types";

interface BlinkIndicatorProps {
  telemetry: TelemetryPayload;
}

export const BlinkIndicator: React.FC<BlinkIndicatorProps> = ({ telemetry }) => {
  const isClosed = telemetry.eye_state === "CLOSED";
  const earPercentage = Math.min(100, Math.max(0, (telemetry.ear / 0.4) * 100));

  return (
    <div
      style={{
        backgroundColor: "#1e293b",
        border: "1px solid #334155",
        borderRadius: "12px",
        padding: "16px",
        marginTop: "12px",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <span style={{ fontSize: "14px", fontWeight: 600, color: "#94a3b8" }}>OVERALL:</span>
          <span
            style={{
              fontSize: "14px",
              fontWeight: 700,
              color: isClosed ? "#f43f5e" : telemetry.overall_eye_state === "PARTIAL" ? "#f59e0b" : "#10b981",
            }}
          >
            {telemetry.overall_eye_state || telemetry.eye_state} ({Math.round(telemetry.confidence * 100)}%)
          </span>
        </div>
        <span
          style={{
            fontSize: "12px",
            padding: "2px 8px",
            borderRadius: "4px",
            backgroundColor: telemetry.face_detected ? "#10b98120" : "#ef444420",
            color: telemetry.face_detected ? "#6ee7b7" : "#fca5a5",
            fontWeight: 500,
          }}
        >
          {telemetry.face_detected ? "Face Tracked" : "No Face"}
        </span>
      </div>

      {/* Independent Left & Right Eye State Indicators */}
      <div style={{ display: "flex", gap: "8px", marginBottom: "10px" }}>
        <span
          style={{
            flex: 1,
            textAlign: "center",
            padding: "4px 8px",
            borderRadius: "6px",
            fontSize: "11px",
            fontWeight: 600,
            backgroundColor: telemetry.left_eye_state === "OPEN" ? "#10b98120" : telemetry.left_eye_state === "CLOSED" ? "#f43f5e20" : "#334155",
            color: telemetry.left_eye_state === "OPEN" ? "#34d399" : telemetry.left_eye_state === "CLOSED" ? "#f87171" : "#94a3b8",
            border: `1px solid ${telemetry.left_eye_state === "OPEN" ? "#10b981" : telemetry.left_eye_state === "CLOSED" ? "#f43f5e" : "#475569"}`,
          }}
        >
          L-EYE: {telemetry.left_eye_state || "OPEN"} {telemetry.left_eye_confidence ? `(${Math.round(telemetry.left_eye_confidence * 100)}%)` : ""}
        </span>
        <span
          style={{
            flex: 1,
            textAlign: "center",
            padding: "4px 8px",
            borderRadius: "6px",
            fontSize: "11px",
            fontWeight: 600,
            backgroundColor: telemetry.right_eye_state === "OPEN" ? "#10b98120" : telemetry.right_eye_state === "CLOSED" ? "#f43f5e20" : "#334155",
            color: telemetry.right_eye_state === "OPEN" ? "#34d399" : telemetry.right_eye_state === "CLOSED" ? "#f87171" : "#94a3b8",
            border: `1px solid ${telemetry.right_eye_state === "OPEN" ? "#10b981" : telemetry.right_eye_state === "CLOSED" ? "#f43f5e" : "#475569"}`,
          }}
        >
          R-EYE: {telemetry.right_eye_state || "OPEN"} {telemetry.right_eye_confidence ? `(${Math.round(telemetry.right_eye_confidence * 100)}%)` : ""}
        </span>
      </div>

      {/* EAR Progress Bar */}
      <div style={{ height: "8px", backgroundColor: "#0f172a", borderRadius: "9999px", overflow: "hidden", marginBottom: "12px" }}>
        <div
          style={{
            height: "100%",
            width: `${earPercentage}%`,
            backgroundColor: isClosed ? "#f43f5e" : "#38bdf8",
            transition: "width 0.1s ease",
          }}
        />
      </div>

      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", color: "#64748b" }}>
        <span>EAR: {telemetry.ear.toFixed(2)}</span>
        <span>
          GAZE: <strong style={{ color: "#38bdf8" }}>{telemetry.gaze_direction}</strong>
        </span>
        {telemetry.gesture_action && (
          <span style={{ color: "#facc15", fontWeight: "bold" }}>
            ACTION: {telemetry.gesture_action}
          </span>
        )}
      </div>
    </div>
  );
};
