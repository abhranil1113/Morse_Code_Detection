import React, { useState } from "react";
import { TelemetryPayload } from "../../types";

interface MorseComposerProps {
  telemetry: TelemetryPayload;
  onSendMessage: (text: string, rawMorse: string) => void;
  onClear: () => void;
  onBackspace?: () => void;
  onQuickWord?: (word: string) => void;
}

const MORSE_ALPHABET = [
  { char: "A", morse: "• —" },
  { char: "B", morse: "— • • •" },
  { char: "C", morse: "— • — •" },
  { char: "D", morse: "— • •" },
  { char: "E", morse: "•" },
  { char: "F", morse: "• • — •" },
  { char: "G", morse: "— — •" },
  { char: "H", morse: "• • • •" },
  { char: "I", morse: "• •" },
  { char: "J", morse: "• — — —" },
  { char: "K", morse: "— • —" },
  { char: "L", morse: "• — • •" },
  { char: "M", morse: "— —" },
  { char: "N", morse: "— •" },
  { char: "O", morse: "— — —" },
  { char: "P", morse: "• — — •" },
  { char: "Q", morse: "— — • —" },
  { char: "R", morse: "• — •" },
  { char: "S", morse: "• • •" },
  { char: "T", morse: "—" },
  { char: "U", morse: "• • —" },
  { char: "V", morse: "• • • —" },
  { char: "W", morse: "• — —" },
  { char: "X", morse: "— • • —" },
  { char: "Y", morse: "— • — —" },
  { char: "Z", morse: "— — • •" },
];

export const MorseComposer: React.FC<MorseComposerProps> = ({
  telemetry,
  onSendMessage,
  onClear,
  onBackspace,
  onQuickWord,
}) => {
  const [mode, setMode] = useState<"STANDARD" | "PHRASES">("STANDARD");
  const [showCheatSheet, setShowCheatSheet] = useState(false);
  const currentBuffer = telemetry.current_buffer || "";
  const decodedText = telemetry.decoded_text || "";

  const quickMacros = [
    { label: "SOS (...---...)", val: "SOS", morse: "...---..." },
    { label: "HELP (.... . .-.. .--.)", val: "HELP", morse: ".... . .-.. .--." },
    { label: "YES (-.-- . ...)", val: "YES", morse: "-.-- . ..." },
    { label: "NO (-. ---)", val: "NO", morse: "-. ---" },
    { label: "WATER (.-- .- - . .-.)", val: "WATER", morse: ".-- .- - . .-." },
    { label: "COME HERE", val: "COME HERE", morse: "-.-. --- -- . / .... . .-. ." },
  ];

  return (
    <div
      style={{
        backgroundColor: "#1e293b",
        border: "1px solid #334155",
        borderRadius: "12px",
        padding: "20px",
        display: "flex",
        flexDirection: "column",
        gap: "14px",
      }}
    >
      {/* Header & Mode Switcher */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "8px" }}>
        <div>
          <h3 style={{ margin: 0, fontSize: "16px", color: "#f8fafc", fontWeight: 600 }}>
            Live Eye-Spoken Composer
          </h3>
          <span style={{ fontSize: "11px", color: "#94a3b8" }}>
            Short Blink = • (0.1s - 0.35s) | Long Blink = — (0.4s - 1.0s)
          </span>
        </div>
        <div style={{ display: "flex", gap: "4px", backgroundColor: "#0f172a", padding: "3px", borderRadius: "6px" }}>
          <button
            type="button"
            onClick={() => setMode("STANDARD")}
            style={{
              padding: "4px 10px",
              borderRadius: "4px",
              border: "none",
              backgroundColor: mode === "STANDARD" ? "#2563eb" : "transparent",
              color: mode === "STANDARD" ? "#ffffff" : "#94a3b8",
              fontSize: "12px",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            Standard Morse
          </button>
          <button
            type="button"
            onClick={() => setMode("PHRASES")}
            style={{
              padding: "4px 10px",
              borderRadius: "4px",
              border: "none",
              backgroundColor: mode === "PHRASES" ? "#2563eb" : "transparent",
              color: mode === "PHRASES" ? "#ffffff" : "#94a3b8",
              fontSize: "12px",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            Quick Phrases
          </button>
        </div>
      </div>

      {/* Gaze & Timing Gesture Legend */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))",
          gap: "6px",
          backgroundColor: "#0f172a",
          padding: "8px 12px",
          borderRadius: "8px",
          fontSize: "11px",
          color: "#94a3b8",
          border: "1px solid #334155",
        }}
      >
        <div>⬆️ <strong>Gaze UP:</strong> Send Message</div>
        <div>⬇️ <strong>Gaze DOWN:</strong> Backspace</div>
        <div>➡️ <strong>Gaze RIGHT:</strong> Dedicated Space</div>
        <div>⬅️ <strong>Gaze LEFT:</strong> Clear Buffer</div>
        <div>⏱️ <strong>Pause 0.8s:</strong> Next Letter</div>
        <div>⏱️ <strong>Pause 2.0s:</strong> Word Space</div>
      </div>

      {/* Active Dot/Dash Symbol Buffer */}
      <div>
        <label style={{ fontSize: "12px", color: "#94a3b8", display: "block", marginBottom: "4px" }}>
          CURRENT MORSE BUFFER
        </label>
        <div
          style={{
            backgroundColor: "#0f172a",
            padding: "10px 14px",
            borderRadius: "8px",
            minHeight: "28px",
            fontSize: "24px",
            letterSpacing: "4px",
            color: "#38bdf8",
            fontFamily: "monospace",
          }}
        >
          {currentBuffer || <span style={{ color: "#475569" }}>_</span>}
        </div>
      </div>

      {/* Translated Full Text */}
      <div>
        <label style={{ fontSize: "12px", color: "#94a3b8", display: "block", marginBottom: "4px" }}>
          TRANSLATED TEXT PREVIEW
        </label>
        <div
          style={{
            backgroundColor: "#0f172a",
            padding: "14px",
            borderRadius: "8px",
            minHeight: "50px",
            fontSize: "18px",
            color: "#f8fafc",
            fontWeight: 500,
            whiteSpace: "pre-wrap",
          }}
        >
          {decodedText || <span style={{ color: "#475569" }}>Blink to start typing or click below...</span>}
        </div>
      </div>

      {/* Quick Assistive Macros */}
      <div style={{ display: "flex", gap: "6px", flexWrap: "wrap", alignItems: "center" }}>
        <span style={{ fontSize: "0.75rem", color: "#64748b" }}>Quick Commands:</span>
        {quickMacros.map((macro) => (
          <button
            key={macro.val}
            type="button"
            onClick={() => onQuickWord?.(macro.val)}
            style={{
              padding: "4px 8px",
              borderRadius: "4px",
              backgroundColor: macro.val === "SOS" ? "#ef444425" : "#334155",
              border: `1px solid ${macro.val === "SOS" ? "#ef4444" : "#475569"}`,
              color: macro.val === "SOS" ? "#fca5a5" : "#e2e8f0",
              fontSize: "0.75rem",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            {macro.label}
          </button>
        ))}
        <button
          type="button"
          onClick={() => setShowCheatSheet(!showCheatSheet)}
          style={{
            marginLeft: "auto",
            padding: "4px 8px",
            borderRadius: "4px",
            backgroundColor: "#0369a130",
            border: "1px solid #0284c7",
            color: "#38bdf8",
            fontSize: "0.75rem",
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          {showCheatSheet ? "Hide Morse Guide ▲" : "Show Morse Guide ▼"}
        </button>
      </div>

      {/* Expandable Morse Alphabet Guide */}
      {showCheatSheet && (
        <div
          style={{
            backgroundColor: "#0f172a",
            border: "1px solid #334155",
            borderRadius: "8px",
            padding: "10px",
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(75px, 1fr))",
            gap: "6px",
            maxHeight: "140px",
            overflowY: "auto",
          }}
        >
          {MORSE_ALPHABET.map((item) => (
            <div
              key={item.char}
              onClick={() => onQuickWord?.(item.char)}
              title={`Click to insert ${item.char} or blink: ${item.morse}`}
              style={{
                backgroundColor: "#1e293b",
                borderRadius: "4px",
                padding: "4px 6px",
                textAlign: "center",
                border: "1px solid #334155",
                cursor: "pointer",
              }}
            >
              <span style={{ color: "#38bdf8", fontWeight: 700, fontSize: "0.85rem", marginRight: "4px" }}>
                {item.char}
              </span>
              <span style={{ color: "#94a3b8", fontSize: "0.75rem", fontFamily: "monospace" }}>
                {item.morse}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Actions */}
      <div style={{ display: "flex", gap: "8px" }}>
        <button
          onClick={() => onSendMessage(decodedText, currentBuffer)}
          disabled={!decodedText.trim()}
          style={{
            flex: 3,
            padding: "12px",
            backgroundColor: decodedText.trim() ? "#2563eb" : "#334155",
            color: decodedText.trim() ? "white" : "#64748b",
            border: "none",
            borderRadius: "8px",
            fontWeight: 600,
            cursor: decodedText.trim() ? "pointer" : "not-allowed",
          }}
        >
          Send Message 🚀
        </button>

        {onBackspace && (
          <button
            onClick={onBackspace}
            style={{
              flex: 1,
              padding: "12px",
              backgroundColor: "#334155",
              color: "#f8fafc",
              border: "none",
              borderRadius: "8px",
              cursor: "pointer",
              fontWeight: 500,
            }}
          >
            ⌫ Back
          </button>
        )}

        <button
          onClick={onClear}
          style={{
            flex: 1,
            padding: "12px",
            backgroundColor: "#334155",
            color: "#f8fafc",
            border: "none",
            borderRadius: "8px",
            cursor: "pointer",
            fontWeight: 500,
          }}
        >
          Clear
        </button>
      </div>
    </div>
  );
};
