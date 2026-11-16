import time
from typing import Optional, Tuple


class GazeController:
    """Interprets pupil gaze ratio and ML predictions into discrete directional commands for hands-free UI control."""

    def __init__(
        self,
        left_threshold: float = 0.65,
        right_threshold: float = 0.35,
        dwell_time_sec: float = 0.60
    ):
        self.left_threshold = left_threshold
        self.right_threshold = right_threshold
        self.dwell_time_sec = dwell_time_sec

        self.current_direction: str = "CENTER"
        self.direction_start_time: float = time.time()
        self.has_triggered_action = False

    def update(
        self,
        avg_gaze_ratio: Optional[float] = None,
        predicted_gaze: Optional[str] = None
    ) -> Tuple[str, Optional[str]]:
        """
        Calculates direction and returns (current_direction, triggered_action).
        Actions: 'SELECT_LEFT', 'SELECT_RIGHT', 'SELECT_UP', 'SELECT_DOWN', None
        """
        now = time.time()

        if predicted_gaze and predicted_gaze in ["LEFT", "RIGHT", "UP", "DOWN", "CENTER"]:
            detected_direction = predicted_gaze
        elif avg_gaze_ratio is not None:
            if avg_gaze_ratio > self.left_threshold:
                detected_direction = "LEFT"
            elif avg_gaze_ratio < self.right_threshold:
                detected_direction = "RIGHT"
            else:
                detected_direction = "CENTER"
        else:
            detected_direction = "CENTER"

        action = None

        if detected_direction != self.current_direction:
            self.current_direction = detected_direction
            self.direction_start_time = now
            self.has_triggered_action = False
        else:
            # Gaze held in the same direction: check dwell time
            dwell = now - self.direction_start_time
            if dwell >= self.dwell_time_sec and not self.has_triggered_action:
                if detected_direction == "LEFT":
                    action = "SELECT_LEFT"
                    self.has_triggered_action = True
                elif detected_direction == "RIGHT":
                    action = "SELECT_RIGHT"
                    self.has_triggered_action = True
                elif detected_direction == "UP":
                    action = "SELECT_UP"
                    self.has_triggered_action = True
                elif detected_direction == "DOWN":
                    action = "SELECT_DOWN"
                    self.has_triggered_action = True

        return self.current_direction, action
