from dataclasses import dataclass


@dataclass
class MorseTimingProfile:
    """Configurable timing thresholds for distinguishing Morse blinks."""
    dot_min_sec: float = 0.10
    dot_max_sec: float = 0.40
    dash_min_sec: float = 0.40
    dash_max_sec: float = 1.40
    char_gap_sec: float = 0.80
    word_gap_sec: float = 2.00


class TimingCalibrator:
    """Adapts blink thresholds to an individual user's biological blink rate."""

    def __init__(self, profile: MorseTimingProfile = None):
        self.profile = profile or MorseTimingProfile()
        self.recorded_short_blinks = []
        self.recorded_long_blinks = []

    def record_calibration_blink(self, duration: float, is_dash: bool):
        if is_dash:
            self.recorded_long_blinks.append(duration)
        else:
            self.recorded_short_blinks.append(duration)

    def compute_optimized_profile(self) -> MorseTimingProfile:
        if self.recorded_short_blinks and self.recorded_long_blinks:
            avg_short = sum(self.recorded_short_blinks) / len(self.recorded_short_blinks)
            avg_long = sum(self.recorded_long_blinks) / len(self.recorded_long_blinks)
            split = (avg_short + avg_long) / 2.0

            self.profile.dot_max_sec = split * 0.95
            self.profile.dash_min_sec = split * 1.05
            self.profile.char_gap_sec = avg_long * 1.1
            self.profile.word_gap_sec = avg_long * 2.2
            print(f"[TimingCalibrator] Recalibrated split threshold to {split:.2f}s")
        return self.profile
