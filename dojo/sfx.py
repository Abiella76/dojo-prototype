"""Synthesised sound effects.

Generated rather than shipped as audio files: a few hundred bytes of maths
beats committing binaries to the repo, and the notes stay tweakable. Pure
stdlib, so nothing new to install.
"""

from __future__ import annotations

import io
import math
import struct
import wave
from functools import lru_cache

RATE = 22050


def _tone(freq: float, ms: int, *, amp: float = 0.32, shape: str = "blip") -> list[float]:
    """One note with a fast attack and exponential decay.

    A little third harmonic gives it the hollow, chiptune-ish edge that reads as
    "arcade" rather than "notification".
    """
    n = int(RATE * ms / 1000)
    out = []
    for i in range(n):
        t = i / RATE
        pos = i / n
        # 4ms attack, exponential decay — no click at either end.
        attack = min(1.0, pos / 0.06) if pos < 0.06 else 1.0
        decay = math.exp(-3.4 * pos) if shape == "blip" else math.exp(-1.6 * pos)
        wave_ = math.sin(2 * math.pi * freq * t) + 0.22 * math.sin(2 * math.pi * freq * 3 * t)
        out.append(amp * attack * decay * wave_ / 1.22)
    return out


def _render(samples: list[float]) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"".join(
            struct.pack("<h", int(max(-1.0, min(1.0, s)) * 32767)) for s in samples
        ))
    return buf.getvalue()


@lru_cache(maxsize=4)
def clear_sound() -> bytes:
    """Short ascending arpeggio — the reward for clearing a quest."""
    notes = [(1047, 55), (1319, 55), (1568, 130)]  # C6 E6 G6
    return _render([s for f, ms in notes for s in _tone(f, ms)])


@lru_cache(maxsize=4)
def rank_up_sound() -> bytes:
    """Longer fanfare, held on the octave — reserved for a promotion."""
    notes = [(1047, 90), (1319, 90), (1568, 90), (2093, 420)]  # C6 E6 G6 C7
    samples = []
    for i, (f, ms) in enumerate(notes):
        samples += _tone(f, ms, amp=0.34, shape="blip" if i < 3 else "hold")
    return _render(samples)


@lru_cache(maxsize=4)
def badge_sound() -> bytes:
    """Achievement fanfare — longer and higher than a rank-up, so unlocking a
    badge is audibly a bigger moment than climbing a belt."""
    notes = [(784, 80), (1047, 80), (1319, 80), (1568, 110), (2093, 520)]  # G5 C6 E6 G6 C7
    samples: list[float] = []
    for freq, ms in notes:
        samples += _tone(freq, ms, amp=0.34)
    return _render(samples)
