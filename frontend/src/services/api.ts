import { Room, Message, User, Participant, AuthResponse, CalibrationProfile } from "../types";

const API_BASE = "http://127.0.0.1:8000/api/v1";

function getAuthHeaders(): HeadersInit {
  const token = localStorage.getItem("eyespeak_access_token");
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

function parseErrorMessage(err: any, fallback: string): string {
  if (!err) return fallback;
  if (typeof err.detail === "string") return err.detail;
  if (Array.isArray(err.detail)) {
    return err.detail
      .map((item: any) => {
        const field = Array.isArray(item.loc) ? item.loc[item.loc.length - 1] : "field";
        return `${field}: ${item.msg}`;
      })
      .join(" | ");
  }
  return fallback;
}

export const api = {
  // --- Auth Endpoints ---
  async login(emailOrUsername: string, password: string): Promise<AuthResponse> {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: emailOrUsername, password }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Login failed" }));
      throw new Error(parseErrorMessage(err, "Login failed"));
    }
    const data: AuthResponse = await res.json();
    localStorage.setItem("eyespeak_access_token", data.access_token);
    localStorage.setItem("eyespeak_refresh_token", data.refresh_token);
    return data;
  },

  async register(email: string, username: string, password: string): Promise<User> {
    const res = await fetch(`${API_BASE}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, username, password }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Registration failed" }));
      throw new Error(parseErrorMessage(err, "Registration failed"));
    }
    return res.json();
  },

  async getCurrentUser(): Promise<User> {
    const res = await fetch(`${API_BASE}/auth/me`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch user");
    return res.json();
  },

  async logout(): Promise<void> {
    const refreshToken = localStorage.getItem("eyespeak_refresh_token");
    if (refreshToken) {
      try {
        await fetch(`${API_BASE}/auth/logout`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
      } catch {}
    }
    localStorage.removeItem("eyespeak_access_token");
    localStorage.removeItem("eyespeak_refresh_token");
  },

  // --- Rooms & Sessions ---
  async getRooms(): Promise<Room[]> {
    const res = await fetch(`${API_BASE}/rooms`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch rooms");
    return res.json();
  },

  async createRoom(name: string, description: string): Promise<Room> {
    const res = await fetch(`${API_BASE}/rooms`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({ name, description }),
    });
    if (!res.ok) throw new Error("Failed to create room");
    return res.json();
  },

  async joinRoom(roomId: string, role: string = "SPEAKER"): Promise<Participant> {
    const res = await fetch(`${API_BASE}/rooms/${roomId}/join`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({ role }),
    });
    if (!res.ok) throw new Error("Failed to join room");
    return res.json();
  },

  async leaveRoom(roomId: string): Promise<void> {
    await fetch(`${API_BASE}/rooms/${roomId}/leave`, {
      method: "POST",
      headers: getAuthHeaders(),
    });
  },

  async getRoomMembers(roomId: string): Promise<Participant[]> {
    const res = await fetch(`${API_BASE}/rooms/${roomId}/members`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) return [];
    return res.json();
  },

  // --- Messages ---
  async getMessages(roomId: string): Promise<Message[]> {
    const res = await fetch(`${API_BASE}/messages/room/${roomId}`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch messages");
    return res.json();
  },

  async sendMessage(message: {
    room_id: string;
    content: string;
    input_method?: string;
    morse_raw?: string;
    confidence_score?: number;
  }): Promise<Message> {
    const res = await fetch(`${API_BASE}/messages`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify(message),
    });
    if (!res.ok) throw new Error("Failed to send message");
    return res.json();
  },

  // --- Calibrations ---
  async saveCalibration(profile: {
    device_key: string;
    calibration_data: Record<string, any>;
    model_version?: string;
  }): Promise<CalibrationProfile> {
    const res = await fetch(`${API_BASE}/calibrations`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify(profile),
    });
    if (!res.ok) throw new Error("Failed to save calibration");
    return res.json();
  },

  async getCalibration(deviceKey: string): Promise<CalibrationProfile> {
    const res = await fetch(`${API_BASE}/calibrations?device_key=${encodeURIComponent(deviceKey)}`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error("Calibration not found");
    return res.json();
  },
};
