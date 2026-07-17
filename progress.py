"""Lightweight progress-bar helper using ANSI escape codes.

Avoids the fragile trailing-space trick and uses `\\033[K` to clear each line.
"""
import sys
import time

from utils import format_time


class ProgressBar:
    """Print a single-line, self-clearing progress bar to stderr."""

    def __init__(self, label: str, total: int) -> None:
        self.label = label
        self.total = max(1, total)
        self.start_time = time.time()

    def update(self, current: int) -> None:
        elapsed = time.time() - self.start_time
        progress = current / self.total
        eta = (elapsed / progress - elapsed) if progress > 0 else 0
        line = (
            f"{self.label}: {current}/{self.total} ({progress*100:.1f}%) "
            f"- Time: {format_time(elapsed)} / ETA: {format_time(eta)}"
        )
        sys.stderr.write(f"\r{line}\033[K")
        sys.stderr.flush()

    def finish(self) -> None:
        self.update(self.total)
        sys.stderr.write("\n")
        sys.stderr.flush()