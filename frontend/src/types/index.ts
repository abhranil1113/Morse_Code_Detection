export interface EyeBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface TelemetryPayload {
  face_detected: boolean;
  ear: number;
  left_ear?: number;
  right_ear?: number;
  left_eye_state?: "OPEN" | "CLOSED" | "UNAVAILABLE";
  right_eye_state?: "OPEN" | "CLOSED" | "UNAVAILABLE";
  overall_eye_state?: "OPEN" | "CLOSED" | "PARTIAL" | "UNAVAILABLE";
  eye_state: "OPEN" | "CLOSED" | "PARTIAL" | "UNAVAILABLE" | "UNKNOWN";
  left_eye_confidence?: number;
  right_eye_confidence?: number;
  eye_detection_confidence?: number;
  confidence: number;
  current_buffer: string;
  decoded_text: string;
  gaze_direction: "CENTER" | "LEFT" | "RIGHT" | "UP" | "DOWN" | "UNKNOWN";
  gesture_action?: "SELECT_LEFT" | "SELECT_RIGHT" | "SELECT_UP" | "SELECT_DOWN" | "SEND_MESSAGE" | string | null;
  blink_event?: "DOT" | "DASH" | "CHAR_COMPLETE" | "WORD_COMPLETE" | null;
  left_box?: EyeBox | null;
  right_box?: EyeBox | null;
  timestamp?: number;
}

export interface User {
  id: string;
  username: string;
  display_name?: string;
  email: string;
  role?: string;
  is_active: boolean;
  created_at: string;
}

export interface Room {
  id: string;
  name: string;
  description: string;
  status?: string;
  created_by?: string | null;
  created_at: string;
}

export interface Participant {
  id: string;
  room_id: string;
  user_id: string;
  role: "SPEAKER" | "ASSISTANT" | "OBSERVER" | string;
  status: "JOINED" | "LEFT" | string;
  joined_at: string;
}

export interface Message {
  id: string;
  room_id: string;
  user_id: string;
  content: string;
  input_method: string;
  morse_raw: string;
  confidence_score: string;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user_id: string;
}

export interface CalibrationProfile {
  device_key: string;
  calibration_data: {
    ear_threshold: number;
    ear_open_mean?: number;
    ear_closed_mean?: number;
    dot_max_sec: number;
    dash_min_sec: number;
  };
  model_version?: string;
  calibrated_at?: string;
}
