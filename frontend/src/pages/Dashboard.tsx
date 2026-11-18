import React, { useState, useEffect } from "react";
import { Navbar } from "../components/Navbar";
import { CameraFeed, stopAllCameraStreams } from "../features/camera/CameraFeed";
import { BlinkIndicator } from "../features/camera/BlinkIndicator";
import { MorseComposer } from "../features/composer/MorseComposer";
import { MessageList } from "../features/messages/MessageList";
import { RoomSelector } from "../features/rooms/RoomSelector";
import { ParticipantList } from "../features/participants/ParticipantList";
import { AuthModal } from "../features/auth/AuthModal";
import { AuthPage } from "./AuthPage";
import { CalibrationModal } from "../features/calibration/CalibrationModal";
import { useEyeSpeak } from "../hooks/useEyeSpeak";
import { api } from "../services/api";
import { Room, Message, User, Participant, TelemetryPayload } from "../types";

export const Dashboard: React.FC = () => {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const { telemetry: streamTelemetry, isConnected, sendFrame } = useEyeSpeak(!!currentUser);
  const [localTelemetry, setLocalTelemetry] = useState<TelemetryPayload | null>(null);
  const telemetry: TelemetryPayload = localTelemetry || streamTelemetry;
  const [isAuthChecking, setIsAuthChecking] = useState<boolean>(true);
  const [rooms, setRooms] = useState<Room[]>([]);
  const [selectedRoomId, setSelectedRoomId] = useState<string>("");
  const [participants, setParticipants] = useState<Participant[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);

  const [isAuthOpen, setIsAuthOpen] = useState(false);
  const [isCalibOpen, setIsCalibOpen] = useState(false);
  const [notification, setNotification] = useState<string | null>(null);

  // 1. Initial auth check
  useEffect(() => {
    api.getCurrentUser()
      .then((user) => setCurrentUser(user))
      .catch(() => setCurrentUser(null))
      .finally(() => setIsAuthChecking(false));
  }, []);

  // 2. Load rooms
  const refreshRooms = () => {
    api.getRooms()
      .then((data) => {
        setRooms(data);
        if (data.length > 0 && !selectedRoomId) {
          setSelectedRoomId(data[0].id);
        }
      })
      .catch(() => {
        const defaultRoom: Room = {
          id: "general-assist",
          name: "General Assistive Room",
          description: "Default EyeSpeak communication space",
          created_at: new Date().toISOString(),
        };
        setRooms([defaultRoom]);
        if (!selectedRoomId) setSelectedRoomId(defaultRoom.id);
      });
  };

  useEffect(() => {
    if (currentUser) {
      refreshRooms();
    }
  }, [currentUser]);

  // 3. Load messages & participants on room selection
  useEffect(() => {
    if (!selectedRoomId) return;

    // Fetch messages
    api.getMessages(selectedRoomId)
      .then((msgs) => setMessages(msgs))
      .catch(() => setMessages([]));

    // Fetch participants
    api.getRoomMembers(selectedRoomId)
      .then((parts) => setParticipants(parts))
      .catch(() => setParticipants([]));

    // Automatically join room as SPEAKER
    api.joinRoom(selectedRoomId, "SPEAKER")
      .then(() => {
        api.getRoomMembers(selectedRoomId).then((parts) => setParticipants(parts));
      })
      .catch(() => {});
  }, [selectedRoomId]);

  // Handle message sending
  const handleSendMessage = async (text: string, rawMorse: string) => {
    if (!text.trim() || !selectedRoomId) return;

    try {
      const newMsg = await api.sendMessage({
        room_id: selectedRoomId,
        content: text.trim(),
        input_method: "EYE_BLINK",
        morse_raw: rawMorse,
        confidence_score: telemetry.confidence || 0.98,
      });
      setMessages((prev) => [...prev, newMsg]);
      setNotification(`Message broadcast: "${text.trim()}"`);
      setTimeout(() => setNotification(null), 3000);
      handleClear();
    } catch {
      // Local optimistic fallback
      const optimisticMsg: Message = {
        id: Math.random().toString(),
        room_id: selectedRoomId,
        user_id: currentUser ? currentUser.id : "local-user",
        content: text.trim(),
        input_method: "EYE_BLINK",
        morse_raw: rawMorse,
        confidence_score: "1.00",
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, optimisticMsg]);
      handleClear();
    }
  };

  const handleCreateRoom = async (name: string) => {
    try {
      const room = await api.createRoom(name, "User-created assistive session");
      setRooms((prev) => [room, ...prev]);
      setSelectedRoomId(room.id);
      setNotification(`Created room #${room.name}`);
      setTimeout(() => setNotification(null), 3000);
    } catch (e: any) {
      setNotification(`Failed to create room: ${e.message}`);
      setTimeout(() => setNotification(null), 3000);
    }
  };

  const handleLeaveRoom = async () => {
    if (!selectedRoomId) return;
    try {
      await api.leaveRoom(selectedRoomId);
      setNotification("Left session.");
      setTimeout(() => setNotification(null), 3000);
      api.getRoomMembers(selectedRoomId).then((parts) => setParticipants(parts));
    } catch {}
  };

  const handleClear = () => {
    setLocalTelemetry({
      ...telemetry,
      current_buffer: "",
      decoded_text: "",
    });
  };

  const handleBackspace = () => {
    const curBuf = telemetry.current_buffer;
    const curTxt = telemetry.decoded_text;
    if (curBuf) {
      setLocalTelemetry({ ...telemetry, current_buffer: curBuf.slice(0, -1) });
    } else if (curTxt) {
      setLocalTelemetry({ ...telemetry, decoded_text: curTxt.slice(0, -1) });
    }
  };

  const handleQuickWord = (word: string) => {
    const newText = (telemetry.decoded_text + " " + word).trim();
    setLocalTelemetry({ ...telemetry, decoded_text: newText, current_buffer: "" });
  };

  const handleSimulateBlink = (durationMs: number) => {
    const sym = durationMs < 350 ? "." : "-";
    const nextBuf = (telemetry.current_buffer || "") + sym;
    setLocalTelemetry({
      ...telemetry,
      current_buffer: nextBuf,
      eye_state: "CLOSED",
      ear: 0.14,
    });
    setTimeout(() => {
      setLocalTelemetry((prev) => (prev ? { ...prev, eye_state: "OPEN", ear: 0.28 } : null));
    }, 250);
  };

  const handleSimulateGaze = (dir: string) => {
    if (dir === "UP") {
      if (telemetry.decoded_text) {
        handleSendMessage(telemetry.decoded_text, telemetry.current_buffer);
      }
    } else if (dir === "DOWN") {
      handleBackspace();
    } else if (dir === "RIGHT") {
      const newText = telemetry.decoded_text ? `${telemetry.decoded_text} ` : " ";
      setLocalTelemetry({ ...telemetry, decoded_text: newText, current_buffer: "" });
    } else if (dir === "LEFT") {
      setLocalTelemetry({ ...telemetry, current_buffer: "" });
    } else {
      setLocalTelemetry({ ...telemetry, gaze_direction: dir as any });
    }
  };

  // Automated Gaze Trigger from live vision stream
  useEffect(() => {
    if (streamTelemetry.gesture_action === "SEND_MESSAGE" && streamTelemetry.decoded_text) {
      handleSendMessage(streamTelemetry.decoded_text, streamTelemetry.current_buffer);
    }
  }, [streamTelemetry.gesture_action]);

  if (isAuthChecking) {
    return (
      <div
        style={{
          minHeight: "100vh",
          backgroundColor: "#090d16",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          color: "#94a3b8",
          gap: "14px",
          fontFamily: "system-ui, -apple-system, sans-serif",
        }}
      >
        <span style={{ fontSize: "40px" }}>👁️</span>
        <span style={{ fontSize: "14px", fontWeight: 600, color: "#38bdf8", letterSpacing: "0.5px" }}>
          Loading EyeSpeak AI...
        </span>
      </div>
    );
  }

  if (!currentUser) {
    return (
      <AuthPage
        onAuthSuccess={(user) => {
          setCurrentUser(user);
          setNotification(`Welcome, ${user.display_name || user.username}!`);
          setTimeout(() => setNotification(null), 3000);
        }}
      />
    );
  }

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", backgroundColor: "#0f172a" }}>
      <Navbar
        isAgentConnected={isConnected}
        currentUser={currentUser}
        onOpenAuth={() => setIsAuthOpen(true)}
        onLogout={async () => {
          // 1. Force stop all active camera hardware streams and media tracks immediately
          stopAllCameraStreams();
          try {
            window.dispatchEvent(new CustomEvent("eyespeak:stop-camera"));
          } catch {}

          // 2. Synchronously wipe state so UI transitions immediately to AuthPage
          setCurrentUser(null);
          setLocalTelemetry(null);
          setMessages([]);
          setParticipants([]);
          setSelectedRoomId("");

          // 3. Purge storage and notify backend with fire-and-forget timeout
          try {
            await api.logout();
          } catch (e) {
            console.error("Logout error:", e);
          }
        }}
        onOpenCalibration={() => setIsCalibOpen(true)}
      />

      {notification && (
        <div
          role="status"
          style={{
            backgroundColor: "#2563eb",
            color: "#ffffff",
            padding: "8px 20px",
            textAlign: "center",
            fontSize: "0.88rem",
            fontWeight: 500,
          }}
        >
          {notification}
        </div>
      )}

      <main
        style={{
          flex: 1,
          padding: "24px",
          maxWidth: "1440px",
          width: "100%",
          margin: "0 auto",
          boxSizing: "border-box",
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: "24px",
        }}
      >
        {/* Left Column: Live Camera & Vision Telemetry */}
        <section style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <CameraFeed telemetry={telemetry} onFrameCapture={sendFrame} />
          <BlinkIndicator telemetry={telemetry} />
          <RoomSelector
            rooms={rooms}
            selectedRoomId={selectedRoomId}
            onSelectRoom={setSelectedRoomId}
            onCreateRoom={handleCreateRoom}
          />
          <ParticipantList
            participants={participants}
            currentUserId={currentUser?.id}
            onLeaveRoom={handleLeaveRoom}
          />
        </section>

        {/* Right Column: Live Morse Composer & Room Chat */}
        <section style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          <MorseComposer
            telemetry={telemetry}
            onSendMessage={handleSendMessage}
            onClear={handleClear}
            onBackspace={handleBackspace}
            onQuickWord={handleQuickWord}
          />
          <MessageList messages={messages} />
        </section>
      </main>

      <AuthModal
        isOpen={isAuthOpen}
        onClose={() => setIsAuthOpen(false)}
        onAuthSuccess={(user) => {
          setCurrentUser(user);
          refreshRooms();
        }}
      />

      <CalibrationModal
        isOpen={isCalibOpen}
        onClose={() => setIsCalibOpen(false)}
        currentEar={telemetry.ear}
        onSimulateBlink={handleSimulateBlink}
        onSimulateGaze={handleSimulateGaze}
      />
    </div>
  );
};
