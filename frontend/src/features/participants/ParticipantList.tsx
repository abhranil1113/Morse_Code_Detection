import React from "react";
import { Participant } from "../../types";

interface ParticipantListProps {
  participants: Participant[];
  currentUserId?: string;
  onLeaveRoom?: () => void;
}

export const ParticipantList: React.FC<ParticipantListProps> = ({
  participants,
  currentUserId,
  onLeaveRoom,
}) => {
  return (
    <div
      style={{
        backgroundColor: "#1e293b",
        borderRadius: "10px",
        padding: "16px",
        border: "1px solid #334155",
        display: "flex",
        flexDirection: "column",
        gap: "12px",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h3 style={{ margin: 0, fontSize: "0.95rem", color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.05em" }}>
          Connected Participants ({participants.length})
        </h3>
        {onLeaveRoom && (
          <button
            onClick={onLeaveRoom}
            style={{
              padding: "4px 8px",
              fontSize: "0.75rem",
              borderRadius: "4px",
              backgroundColor: "transparent",
              border: "1px solid #ef4444",
              color: "#fca5a5",
              cursor: "pointer",
            }}
          >
            Leave Session
          </button>
        )}
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "8px", maxHeight: "180px", overflowY: "auto" }}>
        {participants.length === 0 ? (
          <div style={{ color: "#64748b", fontSize: "0.85rem", fontStyle: "italic" }}>
            No active participants in this session
          </div>
        ) : (
          participants.map((p) => {
            const isMe = p.user_id === currentUserId;
            return (
              <div
                key={p.id || p.user_id}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  padding: "8px 10px",
                  borderRadius: "6px",
                  backgroundColor: "#0f172a",
                  border: isMe ? "1px solid #2563eb" : "1px solid #334155",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <div
                    style={{
                      width: "8px",
                      height: "8px",
                      borderRadius: "50%",
                      backgroundColor: p.status === "JOINED" ? "#10b981" : "#64748b",
                    }}
                  />
                  <span style={{ fontSize: "0.85rem", color: "#f8fafc", fontWeight: isMe ? 600 : 400 }}>
                    {isMe ? "You" : `User ${p.user_id.slice(0, 6)}...`}
                  </span>
                </div>
                <span
                  style={{
                    fontSize: "0.75rem",
                    padding: "2px 6px",
                    borderRadius: "4px",
                    backgroundColor: p.role === "SPEAKER" ? "#2563eb20" : "#64748b20",
                    color: p.role === "SPEAKER" ? "#38bdf8" : "#94a3b8",
                    fontWeight: 500,
                  }}
                >
                  {p.role}
                </span>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
