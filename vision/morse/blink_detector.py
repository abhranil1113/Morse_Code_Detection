import time
from typing import Optional, Tuple, Union
from vision.morse.timing_calibration import TimingCalibrator, MorseTimingProfile


class BlinkDetector:
    """
    Robust state machine that transforms eye state signals into Morse symbols (dot, dash).
    Supports three distinct observation states:
        - OPEN (1 or 'OPEN')
        - CLOSED (0 or 'CLOSED')
        - INVALID / UNKNOWN (-1, 'INVALID', 'UNKNOWN', or None)

    Enforces explicit rules:
    - Only valid OPEN -> CLOSED -> OPEN sequences produce Morse symbols.
    - Missing/invalid landmarks NEVER produce Morse symbols or character/word boundaries.
    - Safe recovery policy handles brief landmark dropouts during closures while aborting prolonged dropouts.
    """

    STATE_CLOSED = 0
    STATE_OPEN = 1
    STATE_INVALID = -1

    def __init__(
        self,
        profile: Optional[MorseTimingProfile] = None,
        max_invalid_during_closure_sec: float = 0.25
    ):
        self.calibrator = TimingCalibrator(profile)
        self.profile = self.calibrator.profile
        self.max_invalid_during_closure_sec = max_invalid_during_closure_sec

        self.is_closed = False
        self.close_start_time: float = 0.0
        self.last_valid_closure_time: float = 0.0
        self.closure_invalid_start_time: Optional[float] = None

        self.open_start_time: float = time.time()
        self.last_open_time: float = time.time()
        self.accumulated_open_duration: float = 0.0
        self.last_closure_duration: float = 0.0

        self.has_notified_char_end = True
        self.has_notified_word_end = True

    @classmethod
    def normalize_observation(cls, raw_state: Union[int, str, None]) -> int:
        """Normalizes heterogeneous input signals to STATE_OPEN, STATE_CLOSED, or STATE_INVALID."""
        if raw_state is None:
            return cls.STATE_INVALID
        if isinstance(raw_state, str):
            s = raw_state.strip().upper()
            if s == "CLOSED":
                return cls.STATE_CLOSED
            elif s == "OPEN":
                return cls.STATE_OPEN
            else:
                return cls.STATE_INVALID
        if isinstance(raw_state, (int, float)):
            if int(raw_state) == 0:
                return cls.STATE_CLOSED
            elif int(raw_state) == 1:
                return cls.STATE_OPEN
            else:
                return cls.STATE_INVALID
        return cls.STATE_INVALID

    def update(
        self,
        eye_state: Union[int, str, None],
        timestamp: Optional[float] = None
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Updates the state machine with an eye observation.
        eye_state: 0/'CLOSED', 1/'OPEN', or -1/'INVALID'/'UNKNOWN'
        Returns:
            (new_symbol, event_type)
            new_symbol: '.' or '-' or None
            event_type: 'DOT', 'DASH', 'CHAR_COMPLETE', 'WORD_COMPLETE',
                        'TRACKING_LOST_ABORTED', 'TRACKING_PAUSED',
                        'MICRO_FLUTTER_REJECTED', 'LONG_CLOSURE_REJECTED', None
        """
        t = timestamp if timestamp is not None else time.time()
        obs = self.normalize_observation(eye_state)

        symbol_event = None
        state_event = None

        # ---------------------------------------------------------------------
        # Case 1: Eye is CLOSED
        # ---------------------------------------------------------------------
        if obs == self.STATE_CLOSED:
            if not self.is_closed:
                # Transition: Open -> Closed
                self.is_closed = True
                self.close_start_time = t
                self.last_valid_closure_time = t
                self.closure_invalid_start_time = None
                self.has_notified_char_end = False
                self.has_notified_word_end = False
                state_event = "CLOSURE_START"
            else:
                # Continuing closure
                self.last_valid_closure_time = t
                self.closure_invalid_start_time = None
                curr_duration = t - self.close_start_time
                if curr_duration > self.profile.dash_max_sec:
                    state_event = "CLOSURE_EXCEEDED"

            # Open timer paused during closures
            self.last_open_time = t

        # ---------------------------------------------------------------------
        # Case 2: Eye is OPEN
        # ---------------------------------------------------------------------
        elif obs == self.STATE_OPEN:
            if self.is_closed:
                # Verified Transition: Closed -> Open (Blink Completed)
                duration = t - self.close_start_time
                self.is_closed = False
                self.last_closure_duration = duration
                self.closure_invalid_start_time = None

                self.open_start_time = t
                self.last_open_time = t
                self.accumulated_open_duration = 0.0

                if duration < self.profile.dot_min_sec:
                    # Involuntary micro-flutter / twitch (< 0.10s)
                    state_event = "MICRO_FLUTTER_REJECTED"
                elif duration <= self.profile.dot_max_sec:
                    # Intentional Short Blink -> DOT
                    symbol_event = "."
                    state_event = "DOT"
                elif duration <= self.profile.dash_max_sec:
                    # Intentional Long Blink -> DASH
                    symbol_event = "-"
                    state_event = "DASH"
                else:
                    # Prolonged closure (> 1.40s) discarded
                    state_event = "LONG_CLOSURE_REJECTED"
            else:
                # Continuing valid OPEN observation: advance inter-blink timer
                dt = t - self.last_open_time if self.last_open_time > 0 and (t - self.last_open_time) < 0.25 else 0.033
                self.accumulated_open_duration += max(0.0, dt)
                self.last_open_time = t

                if not self.has_notified_char_end and self.accumulated_open_duration >= self.profile.char_gap_sec:
                    self.has_notified_char_end = True
                    state_event = "CHAR_COMPLETE"
                elif not self.has_notified_word_end and self.accumulated_open_duration >= self.profile.word_gap_sec:
                    self.has_notified_word_end = True
                    state_event = "WORD_COMPLETE"

        # ---------------------------------------------------------------------
        # Case 3: Eye Observation is INVALID / UNKNOWN
        # ---------------------------------------------------------------------
        else:
            if self.is_closed:
                # Tracking lost during active closure: apply safe recovery policy
                if self.closure_invalid_start_time is None:
                    self.closure_invalid_start_time = t

                invalid_duration = t - self.closure_invalid_start_time
                total_duration = t - self.close_start_time

                if invalid_duration > self.max_invalid_during_closure_sec or total_duration > self.profile.dash_max_sec:
                    # Prolonged tracking loss: abort closure safely without emitting phantom blinks
                    self.is_closed = False
                    self.closure_invalid_start_time = None
                    state_event = "TRACKING_LOST_ABORTED"
                else:
                    # Brief glitch: pause and hold state
                    state_event = "TRACKING_PAUSED"
            else:
                # Open tracking lost: pause open timer so invalid periods do NOT accumulate
                # towards character or word completion
                self.last_open_time = 0.0

        return symbol_event, state_event

    def get_current_closure_duration(self, current_time: Optional[float] = None) -> float:
        """Returns the elapsed duration of the currently active closure in seconds."""
        if not self.is_closed:
            return 0.0
        now = current_time if current_time is not None else time.time()
        return max(0.0, now - self.close_start_time)

    def reset(self):
        """Resets detector state cleanly."""
        self.is_closed = False
        self.close_start_time = 0.0
        self.last_valid_closure_time = 0.0
        self.closure_invalid_start_time = None
        self.open_start_time = time.time()
        self.last_open_time = time.time()
        self.accumulated_open_duration = 0.0
        self.last_closure_duration = 0.0
        self.has_notified_char_end = True
        self.has_notified_word_end = True

