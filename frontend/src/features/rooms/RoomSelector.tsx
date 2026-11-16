import React from "react";
import { Room } from "../../types";

interface RoomSelectorProps {
  rooms: Room[];
  selectedRoomId: string;
  onSelectRoom: (roomId: string) => void;
  onCreateRoom: (name: string) => void;
}

export const RoomSelector: React.FC<RoomSelectorProps> = ({
  rooms,
  selectedRoomId,
  onSelectRoom,
  onCreateRoom,
}) => {
  const [newRoomName, setNewRoomName] = React.useState("");

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    if (newRoomName.trim()) {
      onCreateRoom(newRoomName.trim());
      setNewRoomName("");
    }
  };

  return (
    <div
      style={{
        backgroundColor: "#1e293b",
        border: "1px solid #334155",
        borderRadius: "12px",
        padding: "16px",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
        <h4 style={{ margin: 0, fontSize: "14px", color: "#f8fafc" }}>ACTIVE ROOMS</h4>
      </div>

      <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", marginBottom: "16px" }}>
        {rooms.map((r) => (
          <button
            key={r.id}
            onClick={() => onSelectRoom(r.id)}
            style={{
              padding: "6px 12px",
              borderRadius: "6px",
              border: "none",
              fontSize: "13px",
              cursor: "pointer",
              fontWeight: 500,
              backgroundColor: selectedRoomId === r.id ? "#2563eb" : "#334155",
              color: "white",
            }}
          >
            # {r.name}
          </button>
        ))}
      </div>

      <form onSubmit={handleCreate} style={{ display: "flex", gap: "8px" }}>
        <input
          type="text"
          placeholder="New room name..."
          value={newRoomName}
          onChange={(e) => setNewRoomName(e.target.value)}
          style={{
            flex: 1,
            padding: "8px 12px",
            borderRadius: "6px",
            border: "1px solid #334155",
            backgroundColor: "#0f172a",
            color: "white",
            fontSize: "13px",
          }}
        />
        <button
          type="submit"
          style={{
            padding: "8px 12px",
            backgroundColor: "#0ea5e9",
            color: "white",
            border: "none",
            borderRadius: "6px",
            cursor: "pointer",
            fontSize: "13px",
            fontWeight: 600,
          }}
        >
          Add
        </button>
      </form>
    </div>
  );
};
