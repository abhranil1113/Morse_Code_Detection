import time
from enum import Enum
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field


class VisionEventType(str, Enum):
    BLINK_DOT = "BLINK_DOT"
    BLINK_DASH = "BLINK_DASH"
    CHAR_COMPLETE = "CHAR_COMPLETE"
    WORD_COMPLETE = "WORD_COMPLETE"
    GAZE_DIRECTION = "GAZE_DIRECTION"
    GESTURE_ACTION = "GESTURE_ACTION"
    TELEMETRY_FRAME = "TELEMETRY_FRAME"


@dataclass
class BlinkEvent:
    event_type: VisionEventType
    symbol: Optional[str]  # '.' or '-'
    duration_ms: int
    confidence: float
    timestamp: float = field(default_factory=time.time)


@dataclass
class GazeEvent:
    direction: str  # CENTER, LEFT, RIGHT, UP, DOWN
    action: Optional[str]  # SELECT_LEFT, SELECT_RIGHT, SELECT_UP, SELECT_DOWN
    confidence: float
    timestamp: float = field(default_factory=time.time)


@dataclass
class TelemetryEvent:
    face_detected: bool
    ear: float
    eye_state: str  # OPEN, CLOSED, UNKNOWN
    confidence: float
    current_buffer: str
    decoded_text: str
    gaze_direction: str
    gesture_action: Optional[str]
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "face_detected": self.face_detected,
            "ear": self.ear,
            "eye_state": self.eye_state,
            "confidence": self.confidence,
            "current_buffer": self.current_buffer,
            "decoded_text": self.decoded_text,
            "gaze_direction": self.gaze_direction,
            "gesture_action": self.gesture_action,
            "timestamp": self.timestamp
        }


class VisionEventEmitter:
    """Publish-subscribe bus for local computer vision and Morse signals."""

    def __init__(self):
        self._listeners: Dict[str, List[Callable[[Any], None]]] = {}

    def on(self, event_type: str, callback: Callable[[Any], None]):
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(callback)

    def emit(self, event_type: str, event_data: Any):
        if event_type in self._listeners:
            for cb in self._listeners[event_type]:
                try:
                    cb(event_data)
                except Exception as e:
                    print(f"[VisionEventEmitter] Callback error on '{event_type}': {e}")
