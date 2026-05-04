"""Photometric noise injection for the spike-4 tolerance profile.

Each function takes a (H, W) intensity image in [0, 1] and a severity
parameter, returning the noisy image (also clipped to [0, 1]).

Pure numpy + scipy + Pillow. CPU-only. Deterministic given a seed.
"""
from __future__ import annotations
import io

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter


def gaussian_intensity(image: np.ndarray, sigma: float, seed: int = 0) -> np.ndarray:
    """Additive zero-mean Gaussian noise with std `sigma` in intensity units."""
    rng = np.random.default_rng(seed)
    noisy = image + rng.normal(0.0, sigma, size=image.shape).astype(image.dtype)
    return np.clip(noisy, 0.0, 1.0)


def jpeg_roundtrip(image: np.ndarray, quality: int) -> np.ndarray:
    """Save as JPEG at the given quality, reload, return as float in [0, 1]."""
    img8 = (np.clip(image, 0, 1) * 255 + 0.5).astype(np.uint8)
    pil = Image.fromarray(img8, mode='L')
    buf = io.BytesIO()
    pil.save(buf, format='JPEG', quality=int(quality))
    buf.seek(0)
    out = np.asarray(Image.open(buf), dtype=np.float32) / 255.0
    return out


def focus_blur(image: np.ndarray, sigma_px: float) -> np.ndarray:
    """Gaussian convolution simulating focus blur (sigma in pixels)."""
    return np.clip(gaussian_filter(image.astype(np.float64), sigma=sigma_px), 0.0, 1.0)


def gamma_correction(image: np.ndarray, gamma: float) -> np.ndarray:
    """Apply intensity = image^gamma. gamma > 1 darkens, gamma < 1 brightens."""
    return np.clip(np.power(np.clip(image, 0.0, 1.0), gamma), 0.0, 1.0)


def brightness_shift(image: np.ndarray, delta: float) -> np.ndarray:
    """Add `delta` to every pixel (delta > 0 brightens, delta < 0 darkens)."""
    return np.clip(image + delta, 0.0, 1.0)


def contrast_scale(image: np.ndarray, factor: float) -> np.ndarray:
    """Scale intensity around 0.5: out = 0.5 + factor * (in - 0.5)."""
    return np.clip(0.5 + factor * (image - 0.5), 0.0, 1.0)


def salt_and_pepper(image: np.ndarray, rate: float, seed: int = 0) -> np.ndarray:
    """Set fraction `rate` of pixels to either 0 or 1 (50/50 split)."""
    rng = np.random.default_rng(seed)
    out = image.copy()
    mask = rng.random(image.shape) < rate
    coin = rng.random(image.shape) < 0.5
    out[mask & coin] = 0.0
    out[mask & ~coin] = 1.0
    return out


# ---------------------------------------------------------------------------
# Tolerance profile sweep configuration
# ---------------------------------------------------------------------------

NOISE_SWEEP = [
    ("gaussian_intensity", gaussian_intensity, [0.001, 0.005, 0.01, 0.02, 0.05, 0.10]),
    ("jpeg_roundtrip",     jpeg_roundtrip,     [95, 90, 75, 50, 30, 15]),
    ("focus_blur",         focus_blur,         [0.3, 0.6, 1.0, 1.5, 2.0]),
    ("gamma_correction",   gamma_correction,   [0.7, 0.85, 1.0, 1.18, 1.4]),
    ("brightness_shift",   brightness_shift,   [-0.10, -0.05, -0.02, 0.02, 0.05, 0.10]),
    ("contrast_scale",     contrast_scale,     [0.7, 0.85, 1.0, 1.18, 1.4]),
    ("salt_and_pepper",    salt_and_pepper,    [0.001, 0.005, 0.01, 0.02, 0.05]),
]
