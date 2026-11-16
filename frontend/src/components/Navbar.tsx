import React from "react";
import { StatusBadge } from "./StatusBadge";
import { User } from "../types";

interface NavbarProps {
  isAgentConnected: boolean;
  currentUser: User | null;
  onOpenAuth: () => void;
  onLogout: () => void;
  onOpenCalibration: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  isAgentConnected,
  currentUser,
  onOpenAuth,
  onLogout,
  onOpenCalibration,
}) => {
  return (
    <header
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "14px 24px",
        backgroundColor: "#1e293b",
        borderBottom: "1px solid #334155",
        flexWrap: "wrap",
        gap: "10px",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
        <span style={{ fontSize: "24px" }}>👁️</span>
        <h1 style={{ margin: 0, fontSize: "20px", fontWeight: 700, color: "#38bdf8" }}>
          EyeSpeak AI
        </h1>
        <span
          style={{
            fontSize: "11px",
            color: "#94a3b8",
            backgroundColor: "#0f172a",
            padding: "2px 6px",
            borderRadius: "4px",
          }}
        >
          Assistive Gaze & Morse System
        </span>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
        <StatusBadge
          label={isAgentConnected ? "Vision Stream Online" : "Vision Stream Disconnected"}
          status={isAgentConnected ? "active" : "inactive"}
        />

        <button
          onClick={onOpenCalibration}
          title="Open vision calibration & accessibility settings"
          style={{
            padding: "6px 12px",
            borderRadius: "6px",
            backgroundColor: "#334155",
            border: "1px solid #475569",
            color: "#f8fafc",
            fontSize: "0.85rem",
            cursor: "pointer",
            fontWeight: 500,
          }}
        >
          ⚙️ Calibrate
        </button>

        {currentUser ? (
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span style={{ fontSize: "0.85rem", color: "#38bdf8", fontWeight: 600 }}>
              👤 {currentUser.display_name || currentUser.username}
            </span>
            <button
              onClick={onLogout}
              style={{
                padding: "6px 10px",
                borderRadius: "6px",
                backgroundColor: "transparent",
                border: "1px solid #64748b",
                color: "#cbd5e1",
                fontSize: "0.8rem",
                cursor: "pointer",
              }}
            >
              Sign Out
            </button>
          </div>
        ) : (
          <button
            onClick={onOpenAuth}
            style={{
              padding: "6px 14px",
              borderRadius: "6px",
              backgroundColor: "#2563eb",
              border: "none",
              color: "#fff",
              fontSize: "0.85rem",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            Sign In / Register
          </button>
        )}
      </div>
    </header>
  );
};
