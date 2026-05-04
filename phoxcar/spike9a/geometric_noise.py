"""Geometric noise injection for spike-8A.

Each function takes an (H, W) grayscale image in [0, 1] and returns a
warped image (also in [0, 1]). Geometry happens BEFORE photometric
noise (per spike-4 sweep order).

Implementations use skimage.transform.* warps with bilinear
interpolation. Output is the same shape as input, padded with the carrier
background (0.5) where the warped region exits the original frame.

# Why same-shape output?

A real captured image typically has the same resolution as the source
(or different, but that's a calibration issue, not a substrate issue).
Spike-8A's job is to test whether the decoder can recover pose and
sample from a transformed-but-same-resolution image. Cropping to a
different resolution is a Phase 1 P4 concern.
"""
from __future__ import annotations
import numpy as np
from skimage.transform import (
    AffineTransform, ProjectiveTransform, SimilarityTransform, warp,
)

DEFAULT_FILL = 0.5


def _apply(image: np.ndarray, tf, fill: float = DEFAULT_FILL) -> np.ndarray:
    """skimage.warp helper that preserves shape and float range."""
    out = warp(
        image.astype(np.float64), tf.inverse,
        output_shape=image.shape,
        order=1, mode='constant', cval=fill, preserve_range=True,
    )
    return np.clip(out, 0.0, 1.0).astype(np.float32)


def translate(image: np.ndarray, dx: float, dy: float = None) -> np.ndarray:
    """Translate by (dx, dy) pixels. If dy not given, uses dy=dx."""
    if dy is None:
        dy = dx
    tf = AffineTransform(translation=(dx, dy))
    return _apply(image, tf)


def rotate(image: np.ndarray, angle_deg: float) -> np.ndarray:
    """Rotate around the image center by angle_deg (CCW)."""
    h, w = image.shape
    cx, cy = w / 2.0, h / 2.0
    angle_rad = np.deg2rad(angle_deg)
    pre = AffineTransform(translation=(-cx, -cy))
    rot = AffineTransform(rotation=angle_rad)
    post = AffineTransform(translation=(cx, cy))
    tf = pre + rot + post
    return _apply(image, tf)


def scale(image: np.ndarray, factor: float) -> np.ndarray:
    """Uniform scale around the image center. factor < 1 shrinks, > 1 grows."""
    h, w = image.shape
    cx, cy = w / 2.0, h / 2.0
    pre = AffineTransform(translation=(-cx, -cy))
    sc = AffineTransform(scale=(factor, factor))
    post = AffineTransform(translation=(cx, cy))
    tf = pre + sc + post
    return _apply(image, tf)


def shear(image: np.ndarray, shear_deg: float) -> np.ndarray:
    """Apply horizontal shear around the image center."""
    h, w = image.shape
    cx, cy = w / 2.0, h / 2.0
    pre = AffineTransform(translation=(-cx, -cy))
    sh = AffineTransform(shear=np.deg2rad(shear_deg))
    post = AffineTransform(translation=(cx, cy))
    tf = pre + sh + post
    return _apply(image, tf)


def perspective_tilt(image: np.ndarray, tilt_deg: float, axis: str = 'x') -> np.ndarray:
    """Apply a perspective tilt (simulated 3D rotation) around an axis.

    axis='x' tilts top-to-bottom (like looking down at a screen).
    axis='y' tilts left-to-right (like looking from the side).
    """
    h, w = image.shape
    cx, cy = w / 2.0, h / 2.0
    angle_rad = np.deg2rad(tilt_deg)
    f = max(w, h)  # focal-length-like scale
    # Build a homography mapping the canonical 4 corners to perspective-tilted ones
    src = np.array([(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)], dtype=np.float64)
    if axis == 'x':
        # Tilt top toward viewer
        scale_top = 1.0 - 0.5 * np.sin(abs(angle_rad)) * np.sign(angle_rad)
        scale_bot = 1.0 + 0.5 * np.sin(abs(angle_rad)) * np.sign(angle_rad)
        dst = np.array([
            (cx + (0 - cx) * scale_top, 0),
            (cx + (w - 1 - cx) * scale_top, 0),
            (cx + (0 - cx) * scale_bot, h - 1),
            (cx + (w - 1 - cx) * scale_bot, h - 1),
        ], dtype=np.float64)
    elif axis == 'y':
        scale_left = 1.0 - 0.5 * np.sin(abs(angle_rad)) * np.sign(angle_rad)
        scale_right = 1.0 + 0.5 * np.sin(abs(angle_rad)) * np.sign(angle_rad)
        dst = np.array([
            (0, cy + (0 - cy) * scale_left),
            (w - 1, cy + (0 - cy) * scale_right),
            (0, cy + (h - 1 - cy) * scale_left),
            (w - 1, cy + (h - 1 - cy) * scale_right),
        ], dtype=np.float64)
    else:
        raise ValueError(f"axis must be 'x' or 'y', got {axis!r}")
    tf = ProjectiveTransform()
    if not tf.estimate(src, dst):
        return image
    return _apply(image, tf)


def rolling_shutter(image: np.ndarray, px_per_row: float) -> np.ndarray:
    """Simulate rolling shutter: each row is shifted by row_index * px_per_row.

    px_per_row is the cumulative horizontal offset per row of capture (mimics
    hand tremor over a rolling-shutter readout). Total shift bottom-to-top is
    H * px_per_row pixels.
    """
    h, w = image.shape
    out = np.full_like(image, DEFAULT_FILL)
    for row in range(h):
        shift = int(round(row * px_per_row))
        if shift >= w or shift <= -w:
            continue                                       # entire row scrolled off
        if shift == 0:
            out[row] = image[row]
        elif shift > 0:
            out[row, shift:] = image[row, :w - shift]
        else:
            out[row, :w + shift] = image[row, -shift:]
    return out


GEOMETRIC_SWEEP = [
    ("translation_x", lambda img, sev: translate(img, dx=sev, dy=0),
     [0, 5, 20, 50, 100]),
    ("rotation",      lambda img, sev: rotate(img, sev),
     [0, 5, 15, 45, 90, 180]),
    ("scale",         lambda img, sev: scale(img, sev),
     [0.7, 0.85, 1.0, 1.18, 1.4]),
    ("shear",         lambda img, sev: shear(img, sev),
     [0, 2, 5, 10]),
    ("tilt_x",        lambda img, sev: perspective_tilt(img, sev, axis='x'),
     [0, 5, 10, 20, 30]),
    ("tilt_y",        lambda img, sev: perspective_tilt(img, sev, axis='y'),
     [0, 5, 10, 20, 30]),
    ("rolling_shutter", lambda img, sev: rolling_shutter(img, sev),
     [0, 0.1, 0.5, 1.0, 2.0]),
]
