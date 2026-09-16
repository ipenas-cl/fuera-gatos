#!/usr/bin/env python3
"""Genera sonidos disuasorios sintéticos (bufido y chorro de aire) en sounds/.

Son ráfagas de ruido de 1.5-2 s. No hace falta nada más que numpy.
"""
from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

RATE = 22050
OUT = Path(__file__).resolve().parent.parent / "sounds"


def write_wav(path: Path, samples: np.ndarray) -> None:
    pcm = np.clip(samples * 32767, -32768, 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(pcm.tobytes())


def envelope(n: int, attack: float, release: float) -> np.ndarray:
    env = np.ones(n)
    a, r = int(attack * RATE), int(release * RATE)
    env[:a] = np.linspace(0, 1, a)
    env[-r:] = np.linspace(1, 0, r)
    return env


def hiss(seconds: float = 1.6, seed: int = 1) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = int(seconds * RATE)
    noise = rng.standard_normal(n)
    # Filtro paso alto simple para un siseo agudo tipo bufido.
    hp = noise - np.concatenate([[0], noise[:-1]]) * 0.95
    # Dos bufidos seguidos.
    env = envelope(n, 0.02, 0.3)
    mid = n // 2
    env[mid - int(0.08 * RATE): mid] = 0
    return 0.9 * hp / np.max(np.abs(hp)) * env


def air(seconds: float = 2.0, seed: int = 2) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = int(seconds * RATE)
    noise = rng.standard_normal(n)
    lp = np.convolve(noise, np.ones(6) / 6, mode="same")  # menos agudo, tipo aire comprimido
    return 0.9 * lp / np.max(np.abs(lp)) * envelope(n, 0.01, 0.6)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    write_wav(OUT / "hiss.wav", hiss())
    write_wav(OUT / "air.wav", air())
    print(f"Sonidos generados en {OUT}")


if __name__ == "__main__":
    main()
