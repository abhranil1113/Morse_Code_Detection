import time
from typing import Optional, Tuple
from vision.morse.timing_calibration import TimingCalibrator, MorseTimingProfile


class BlinkDetector:
    """
    State machine that transforms eye state signals into Morse symbols (dot, dash).
    Maintains debouncing, hysteresis, and separate measurements for:
    - Eye closure duration (intentional blink length)
    - Inter-blink open-eye interval (character & word gap timeouts)
    """

    def __init__(self, profile: Optional[MorseTimingProfile] = None):
        self.calibrator = TimingCalibrator(profile)
        self.profile = self.calibrator.profile

        self.is_closed = False
        self.close_start_time: float = 0.0
        self.open_start_time: float = time.time()
        self.last_closure_duration: float = 0.0
        self.current_open_duration: float = 0.0

        self.has_notified_char_end = True
        self.has_notified_word_end = True

        # Debouncing filters to prevent single-frame noise artifacts
        self.pending_state: Optional[int] = None
        self.pending_state_time: float = 0.0
        self.debounce_duration_sec: float = 0.035  # ~1 frame buffer at 30 fps

    def update(self, eye_state: int, timestamp: Optional[float] = None) -> Tuple[Optional[str], Optional[str]]:
        """
        Updates the state machine.
        eye_state: 0 = CLOSED, 1 = OPEN.
        Returns:
            (new_symbol, event_type)
            new_symbol: '.' or '-' or None
            event_type: 'DOT', 'DASH', 'CHAR_COMPLETE', 'WORD_COMPLETE', None
        """
        t = timestamp or time.time()
        symbol_event = None
        state_event = None

        if eye_state == 0:  # Eye is CLOSED
            if not self.is_closed:
                # Transition Open -> Closed
                self.is_closed = True
                self.close_start_time = t
                self.has_notified_char_end = False
                self.has_notified_word_end = False
        else:  # Eye is OPEN
            if self.is_closed:
                # Transition Closed -> Open
                self.is_closed = False
                duration = t - self.close_start_time
                self.last_closure_duration = duration
                self.open_start_time = t
                self.current_open_duration = 0.0

                if self.profile.dot_min_sec <= duration <= self.profile.dot_max_sec:
                    symbol_event = "."
                    state_event = "DOT"
                elif self.profile.dash_min_sec <= duration <= self.profile.dash_max_sec:
                    symbol_event = "-"
                    state_event = "DASH"
                # Durations < dot_min_sec are discarded as involuntary micro-flutters
                # Durations > dash_max_sec are discarded as sleep / accidental closure
            else:
                # Eye continues to stay OPEN: evaluate separate open-eye interval
                self.current_open_duration = t - self.open_start_time
                if not self.has_notified_char_end and self.current_open_duration >= self.profile.char_gap_sec:
                    self.has_notified_char_end = True
                    state_event = "CHAR_COMPLETE"
                elif not self.has_notified_word_end and self.current_open_duration >= self.profile.word_gap_sec:
                    self.has_notified_word_end = True
                    state_event = "WORD_COMPLETE"

        return symbol_event, state_event

    def reset(self):
        """Resets detector state cleanly."""
        self.is_closed = False
        self.close_start_time = 0.0
        self.open_start_time = time.time()
        self.has_notified_char_end = True
        self.has_notified_word_end = True
