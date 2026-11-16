import React, { useState, useEffect } from "react";
import { api } from "../../services/api";

interface CalibrationModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentEar: number;
  onSimulateBlink?: (durationMs: number) => void;
  onSimulateGaze?: (dir: string) => void;
}

export const CalibrationModal: React.FC<CalibrationModalProps> = ({
  isOpen,
  onClose,
  currentEar,
  onSimulateBlink,
  onSimulateGaze,
}) => {
  const [deviceKey, setDeviceKey] = useState("webcam_primary_default");
  const [earThreshold, setEarThreshold] = useState(0.22);
  const [dotMaxSec, setDotMaxSec] = useState(0.35);
  const [dashMinSec, setDashMinSec] = useState(0.40);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (isOpen) {
      api.getCalibration(deviceKey)
        .then((profile) => {
          if (profile?.calibration_data) {
            setEarThreshold(profile.calibration_data.ear_threshold ?? 0.22);
            setDotMaxSec(profile.calibration_data.dot_max_sec ?? 0.35);
            setDashMinSec(profile.calibration_data.dash_min_sec ?? 0.40);
          }
        })
        .catch(() => {});
    }
  }, [isOpen, deviceKey]);

  if (!isOpen) return null;

  const handleSave = async () => {
    setIsSaving(true);
    setStatusMessage(null);
    try {
      await api.saveCalibration({
        device_key: deviceKey,
        calibration_data: {
          ear_threshold: earThreshold,
          dot_max_sec: dotMaxSec,
          dash_min_sec: dashMinSec,
        },
        model_version: "1.0.0-rf",
      });
      setStatusMessage("Calibration profile saved successfully to database!");
    } catch (e: any) {
      setStatusMessage(`Error saving: ${e.message}`);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        backgroundColor: "rgba(0,0,0,0.8)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
        padding: "20px",
      }}
    >
      <div
        style={{
          backgroundColor: "#1e293b",
          padding: "28px",
          borderRadius: "14px",
          width: "520px",
          maxHeight: "90vh",
          overflowY: "auto",
          color: "#f8fafc",
          border: "1px solid #334155",
          boxShadow: "0 20px 30px rgba(0,0,0,0.6)",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
          <div>
            <h2 style={{ margin: 0, fontSize: "1.3rem", color: "#38bdf8" }}>
              Vision Calibration & Accessibility Controls
            </h2>
            <p style={{ margin: "4px 0 0", fontSize: "0.82rem", color: "#94a3b8" }}>
              Tune eye detection thresholds and alternative tactile fallbacks
            </p>
          </div>
          <button
            onClick={onClose}
            aria-label="Close calibration modal"
            style={{
              background: "none",
              border: "none",
              color: "#94a3b8",
              fontSize: "1.4rem",
              cursor: "pointer",
            }}
          >
            ✕
          </button>
        </div>

        {statusMessage && (
          <div
            style={{
              padding: "10px",
              borderRadius: "6px",
              backgroundColor: statusMessage.startsWith("Error") ? "#ef444420" : "#10b98120",
              border: `1px solid ${statusMessage.startsWith("Error") ? "#ef4444" : "#10b981"}`,
              color: statusMessage.startsWith("Error") ? "#fca5a5" : "#6ee7b7",
              fontSize: "0.85rem",
              marginBottom: "16px",
            }}
          >
            {statusMessage}
          </div>
        )}

        <div style={{ display: "flex", flexDirection: "column", gap: "18px" }}>
          {/* Live EAR Feedback Gauge */}
          <div
            style={{
              padding: "12px",
              backgroundColor: "#0f172a",
              borderRadius: "8px",
              border: "1px solid #334155",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px", fontSize: "0.85rem" }}>
              <span style={{ color: "#94a3b8" }}>Live Camera EAR:</span>
              <span style={{ fontWeight: "bold", color: currentEar < earThreshold ? "#ef4444" : "#10b981" }}>
                {currentEar.toFixed(3)} ({currentEar < earThreshold ? "EYE CLOSED" : "EYE OPEN"})
              </span>
            </div>
            <div style={{ height: "8px", backgroundColor: "#334155", borderRadius: "4px", overflow: "hidden" }}>
              <div
                style={{
                  height: "100%",
                  width: `${Math.min(100, Math.max(0, currentEar * 200))}%`,
                  backgroundColor: currentEar < earThreshold ? "#ef4444" : "#10b981",
                  transition: "width 0.1s ease",
                }}
              />
            </div>
          </div>

          {/* Device Identifier */}
          <div>
            <label style={{ display: "block", fontSize: "0.85rem", color: "#94a3b8", marginBottom: "4px" }}>
              Device Key Profile
            </label>
            <input
              type="text"
              value={deviceKey}
              onChange={(e) => setDeviceKey(e.target.value)}
              style={{
                width: "100%",
                padding: "8px 12px",
                borderRadius: "6px",
                border: "1px solid #475569",
                backgroundColor: "#0f172a",
                color: "#f8fafc",
                boxSizing: "border-box",
              }}
            />
          </div>

          {/* EAR Threshold Slider */}
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.85rem", marginBottom: "4px" }}>
              <label htmlFor="ear-thresh" style={{ color: "#cbd5e1" }}>Eye Closure Threshold (EAR)</label>
              <span style={{ color: "#38bdf8", fontWeight: "bold" }}>{earThreshold.toFixed(2)}</span>
            </div>
            <input
              id="ear-thresh"
              type="range"
              min="0.10"
              max="0.35"
              step="0.01"
              value={earThreshold}
              onChange={(e) => setEarThreshold(parseFloat(e.target.value))}
              style={{ width: "100%", accentColor: "#38bdf8" }}
            />
            <span style={{ fontSize: "0.75rem", color: "#64748b" }}>
              EAR below this value is treated as CLOSED. Default: 0.22.
            </span>
          </div>

          {/* Dot Max Duration */}
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.85rem", marginBottom: "4px" }}>
              <label htmlFor="dot-max" style={{ color: "#cbd5e1" }}>Dot Max Blink Duration</label>
              <span style={{ color: "#38bdf8", fontWeight: "bold" }}>{dotMaxSec.toFixed(2)}s</span>
            </div>
            <input
              id="dot-max"
              type="range"
              min="0.15"
              max="0.50"
              step="0.01"
              value={dotMaxSec}
              onChange={(e) => setDotMaxSec(parseFloat(e.target.value))}
              style={{ width: "100%", accentColor: "#38bdf8" }}
            />
            <span style={{ fontSize: "0.75rem", color: "#64748b" }}>
              Blinks under this duration register as dots (.).
            </span>
          </div>

          {/* Dash Min Duration */}
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.85rem", marginBottom: "4px" }}>
              <label htmlFor="dash-min" style={{ color: "#cbd5e1" }}>Dash Min Blink Duration</label>
              <span style={{ color: "#38bdf8", fontWeight: "bold" }}>{dashMinSec.toFixed(2)}s</span>
            </div>
            <input
              id="dash-min"
              type="range"
              min="0.30"
              max="1.20"
              step="0.02"
              value={dashMinSec}
              onChange={(e) => setDashMinSec(parseFloat(e.target.value))}
              style={{ width: "100%", accentColor: "#38bdf8" }}
            />
            <span style={{ fontSize: "0.75rem", color: "#64748b" }}>
              Blinks over this duration register as dashes (-).
            </span>
          </div>

          {/* Alternative Accessibility Inputs */}
          <div
            style={{
              padding: "14px",
              backgroundColor: "#0f172a",
              borderRadius: "8px",
              border: "1px dashed #475569",
            }}
          >
            <div style={{ fontSize: "0.85rem", fontWeight: "bold", color: "#facc15", marginBottom: "8px" }}>
              Alternative Tactile / Keyboard Controls (No Camera Required)
            </div>
            <p style={{ margin: "0 0 10px", fontSize: "0.78rem", color: "#94a3b8" }}>
              Use buttons or keyboard shortcuts if camera is unavailable or for motor accessibility:
            </p>
            <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
              <button
                type="button"
                onClick={() => onSimulateBlink?.(200)}
                style={{
                  padding: "6px 12px",
                  borderRadius: "6px",
                  backgroundColor: "#334155",
                  border: "1px solid #64748b",
                  color: "#f8fafc",
                  fontSize: "0.8rem",
                  cursor: "pointer",
                }}
              >
                Simulate Dot (.)
              </button>
              <button
                type="button"
                onClick={() => onSimulateBlink?.(600)}
                style={{
                  padding: "6px 12px",
                  borderRadius: "6px",
                  backgroundColor: "#334155",
                  border: "1px solid #64748b",
                  color: "#f8fafc",
                  fontSize: "0.8rem",
                  cursor: "pointer",
                }}
              >
                Simulate Dash (-)
              </button>
              <button
                type="button"
                onClick={() => onSimulateGaze?.("UP")}
                style={{
                  padding: "6px 12px",
                  borderRadius: "6px",
                  backgroundColor: "#334155",
                  border: "1px solid #64748b",
                  color: "#f8fafc",
                  fontSize: "0.8rem",
                  cursor: "pointer",
                }}
              >
                Gaze UP (Send)
              </button>
              <button
                type="button"
                onClick={() => onSimulateGaze?.("DOWN")}
                style={{
                  padding: "6px 12px",
                  borderRadius: "6px",
                  backgroundColor: "#334155",
                  border: "1px solid #64748b",
                  color: "#f8fafc",
                  fontSize: "0.8rem",
                  cursor: "pointer",
                }}
              >
                Gaze DOWN (Backspace)
              </button>
            </div>
          </div>

          {/* Action Buttons */}
          <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "10px" }}>
            <button
              type="button"
              onClick={onClose}
              style={{
                padding: "10px 18px",
                borderRadius: "6px",
                backgroundColor: "transparent",
                border: "1px solid #475569",
                color: "#cbd5e1",
                cursor: "pointer",
              }}
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSave}
              disabled={isSaving}
              style={{
                padding: "10px 20px",
                borderRadius: "6px",
                backgroundColor: "#2563eb",
                border: "none",
                color: "#fff",
                fontWeight: 600,
                cursor: isSaving ? "not-allowed" : "pointer",
              }}
            >
              {isSaving ? "Saving..." : "Save Calibration"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
