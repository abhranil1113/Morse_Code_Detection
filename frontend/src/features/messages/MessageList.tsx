import React from "react";
import { Message } from "../../types";

interface MessageListProps {
  messages: Message[];
}

export const MessageList: React.FC<MessageListProps> = ({ messages }) => {
  return (
    <div
      style={{
        backgroundColor: "#1e293b",
        border: "1px solid #334155",
        borderRadius: "12px",
        padding: "20px",
        height: "360px",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <h3 style={{ margin: "0 0 16px 0", fontSize: "16px", color: "#f8fafc", fontWeight: 600 }}>
        Room Message Feed
      </h3>

      <div
        style={{
          flex: 1,
          overflowY: "auto",
          display: "flex",
          flexDirection: "column",
          gap: "12px",
        }}
      >
        {messages.length === 0 ? (
          <div style={{ color: "#64748b", margin: "auto", textAlign: "center" }}>
            No messages in this room yet. Blink to compose the first one!
          </div>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.id}
              style={{
                backgroundColor: "#0f172a",
                padding: "12px 16px",
                borderRadius: "8px",
                borderLeft: "4px solid #38bdf8",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                <span style={{ fontSize: "12px", fontWeight: 700, color: "#38bdf8" }}>
                  {msg.input_method === "morse_eye_blink" ? "👁️ EyeSpeak" : "👤 User"}
                </span>
                <span style={{ fontSize: "11px", color: "#64748b" }}>
                  {new Date(msg.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                </span>
              </div>
              <div style={{ fontSize: "15px", color: "#f8fafc" }}>{msg.content}</div>
              {msg.morse_raw && (
                <div style={{ fontSize: "11px", color: "#64748b", marginTop: "4px", fontFamily: "monospace" }}>
                  Raw Morse: {msg.morse_raw}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
};
