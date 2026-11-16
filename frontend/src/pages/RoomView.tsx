import React from "react";
import { MessageList } from "../features/messages/MessageList";
import { Message } from "../types";

interface RoomViewProps {
  roomName: string;
  messages: Message[];
}

export const RoomView: React.FC<RoomViewProps> = ({ roomName, messages }) => {
  return (
    <div style={{ padding: "20px" }}>
      <h2 style={{ color: "#38bdf8" }}>Channel: #{roomName}</h2>
      <MessageList messages={messages} />
    </div>
  );
};
