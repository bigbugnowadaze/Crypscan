"""Synthetic screen-camera distortion channel for spike-9A.

Goal: reproduce the spike-8B run 4 failure mode (codebook NN returns wrong
bytes after pose succeeds) without needing real hardware. Once the channel
faithfully reproduces real-capture failure, we can iterate substrate
variants against it as a closed-loop test bed.

Channel stack (per ADDENDUM_04 §3 recommendation #5):

    rendered carrier (1280x1280 grayscale, [0,1])
      -> apply screen-subpixel raster (RGB-stripe luminance mask)
      -> 2x bilinear upsample (simulates camera oversampling)
      -> Bayer mosaic (RGGB pattern, random sub-pixel offset)
      -> bilinear demosaic
      -> JPEG round-trip at quality q
      -> downsample back to 1280x1280
      -> mild perspective warp (~5 deg tilt)
      -> additive Gaussian noise (sigma ~0.02)

Each step models one stage of the actual screen->lens->sensor->JPEG pipeline:

  - Screen subpixel raster: real LCD/OLED panels have RGB stripe layouts. A
    grayscale carrier is rendered by displaying the same intensity in all 3
    subpixels, but the subpixel structure itself imprints a high-frequency
    pattern at the sub-pixel pitch.

  - Bayer mosaic + bilinear demosaic: phone cameras sample through an RGGB
    color filter array, then reconstruct full-color via demosaicing. This
    introduces structured low-pass blur and channel-dependent aliasing that
    is the dominant source of the 'high-frequency vertical stripes' we
    observed on real capture.

  - JPEG round-trip: real captures are saved as JPEG. Quantization of 8x8
    DCT blocks at q ~70-85 attenuates exactly the mid-frequency content
    that contains germ structure.

  - Perspective warp + Gaussian noise: residual factors that the previous
    pose layer + photometric calibration handle, but they're in the channel
    for completeness.

The output of `apply_screen_camera_channel` should look QUALITATIVELY like
the rectified frame of a real S21 FE capture of an Asus laptop screen
displaying the carrier (per spike-8B run 4).
"""
from __future__ import annotations
from dataclasses import dataclass, field
import io

import numpy as np
import cv2
from PIL import Image


@dataclass
class ChannelParams:
    """Configurable parameters for the synthetic channel."""
    # Screen subpixel mask: which subpixel layout to simulate.
    # 'rgb_stripe' = standard horizontal RGB stripe (most LCD/OLED panels)
    # 'none' = no subpixel structure
    subpixel_pattern: str = 'rgb_stripe'

    # Per-subpixel attenuation. Each "carrier pixel" gets split into 3 vertical
    # stripes at relative weights (R, G, B). For grayscale carrier, all three
    # display the same value, but the 3-stripe structure creates moiré with
    # camera Bayer sampling. This models display panel characteristics.
    subpixel_weights: tuple = (1.0, 1.0, 1.0)

    # Camera sensor oversampling factor (simulates that camera pixels are
    # smaller than screen pixels at typical capture distance). 2.0x is
    # roughly accurate for a phone camera at 30-50cm from a 1080p screen.
    camera_oversample: float = 2.0

    # Bayer pattern offset (sub-pixel; controls phase of moiré beat).
    bayer_offset_x: float = 0.0
    bayer_offset_y: float = 0.0

    # JPEG quality used for round-trip
    jpeg_quality: int = 80

    # Perspective tilt in degrees (small; pose layer handles this, included
    # for completeness)
    perspective_tilt_deg: float = 5.0

    # Additive Gaussian noise sigma in [0,1] image-value space
    gaussian_sigma: float = 0.02

    # Random seed for stochastic components (Bayer offset, noise)
    seed: int = 42


def _rgb_stripe_mask(h: int, w: int, weights=(1.0, 1.0, 1.0)) -> np.ndarray:
    """Build an (H, W, 3) per-subpixel mask. Each column belongs to one
    of R/G/B channels; the mask shows the subpixel weight for each color
    at that column.

    For a horizontal RGB stripe layout, columns 0,3,6,... are R; 1,4,7,... G;
    2,5,8,... B.
    """
    mask = np.zeros((h, w, 3), dtype=np.float32)
    for c in range(3):
        mask[:, c::3, c] = weights[c]
    return mask


def _apply_subpixel_raster(image: np.ndarray, params: ChannelParams) -> np.ndarray:
    """Convert a grayscale carrier (H, W) in [0,1] into an (H, W, 3) RGB image
    where each column carries information for one subpixel only. This models
    the panel's RGB stripe layout.

    A real screen displaying a grayscale value v sets all 3 subpixels to v.
    The subpixel rasterization SUBPIXEL_GRID model splits the carrier across
    3-column sub-cells where each sub-cell is dominated by one color.

    For our purposes this is approximate -- the key behavior we need is the
    high-frequency horizontal-stripe structure, since that's what beats with
    the Bayer sensor sampling to produce moiré.
    """
    h, w = image.shape
    if params.subpixel_pattern == 'none':
        return np.stack([image, image, image], axis=-1).astype(np.float32)
    mask = _rgb_stripe_mask(h, w, params.subpixel_weights)
    rgb = mask * image[..., None].astype(np.float32)
    # Sum back per-pixel-cell so the 3 subpixel weights add up to "the original"
    # for solid uniform regions but vary at the per-column level.
    # The 3-stripe layout means: rgb[:, 0::3, 0]=v, rgb[:, 1::3, 1]=v, rgb[:, 2::3, 2]=v
    # For a grayscale display, each subpixel emits the carrier value; the camera
    # then sums per its own pattern.
    return rgb


def _bayer_sample(rgb: np.ndarray, offset_x: float = 0.0,
                    offset_y: float = 0.0) -> np.ndarray:
    """Sample an (H, W, 3) RGB image through an RGGB Bayer filter to produce
    an (H, W) raw mosaic. Optional sub-pixel offset to shift the Bayer
    pattern phase.

    Pattern (top-left 2x2 cell):
        R G
        G B
    """
    h, w, _ = rgb.shape
    if offset_x or offset_y:
        # Apply a tiny translation via warp (sub-pixel)
        M = np.array([[1, 0, offset_x], [0, 1, offset_y]], dtype=np.float32)
        rgb_shifted = cv2.warpAffine(rgb, M, (w, h),
                                      flags=cv2.INTER_LINEAR,
                                      borderMode=cv2.BORDER_REFLECT)
    else:
        rgb_shifted = rgb
    raw = np.zeros((h, w), dtype=np.float32)
    raw[0::2, 0::2] = rgb_shifted[0::2, 0::2, 0]   # R
    raw[0::2, 1::2] = rgb_shifted[0::2, 1::2, 1]   # G
    raw[1::2, 0::2] = rgb_shifted[1::2, 0::2, 1]   # G
    raw[1::2, 1::2] = rgb_shifted[1::2, 1::2, 2]   # B
    return raw


def _bilinear_demosaic(raw: np.ndarray) -> np.ndarray:
    """Bilinear demosaic of an RGGB raw image to RGB. Returns (H, W, 3).

    For every missing color value, average the 4 nearest neighbors of that
    color. Real demosaicers (AHD, VNG, RCD) do better, but bilinear is the
    simplest and produces the characteristic 'zipper' moiré that real cameras
    also exhibit on high-frequency regions.
    """
    raw_u8 = (np.clip(raw, 0, 1) * 255 + 0.5).astype(np.uint8)
    rgb = cv2.cvtColor(raw_u8, cv2.COLOR_BAYER_RG2RGB)
    return rgb.astype(np.float32) / 255.0


def _rgb_to_gray(rgb: np.ndarray) -> np.ndarray:
    """Grayscale conversion using ITU-R BT.601 weights (matches PIL/Pillow)."""
    return (0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2])


def _jpeg_roundtrip(image: np.ndarray, quality: int) -> np.ndarray:
    """JPEG-encode and decode an image at the given quality."""
    img8 = (np.clip(image, 0, 1) * 255 + 0.5).astype(np.uint8)
    if img8.ndim == 2:
        pil = Image.fromarray(img8, mode='L')
    else:
        pil = Image.fromarray(img8, mode='RGB')
    buf = io.BytesIO()
    pil.save(buf, format='JPEG', quality=int(quality))
    buf.seek(0)
    pil2 = Image.open(buf)
    return np.asarray(pil2, dtype=np.float32) / 255.0


def _perspective_tilt(image: np.ndarray, tilt_deg: float, axis: str = 'x',
                        rng: np.random.Generator | None = None) -> np.ndarray:
    """Apply a small perspective tilt around an axis."""
    h, w = image.shape[:2]
    cx, cy = w / 2.0, h / 2.0
    angle_rad = np.deg2rad(tilt_deg)
    src = np.array([(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)], dtype=np.float32)
    if axis == 'x':
        scale_top = 1.0 - 0.3 * np.sin(abs(angle_rad)) * np.sign(angle_rad)
        scale_bot = 1.0 + 0.3 * np.sin(abs(angle_rad)) * np.sign(angle_rad)
        dst = np.array([
            (cx + (0 - cx) * scale_top, 0),
            (cx + (w - 1 - cx) * scale_top, 0),
            (cx + (0 - cx) * scale_bot, h - 1),
            (cx + (w - 1 - cx) * scale_bot, h - 1),
        ], dtype=np.float32)
    else:
        scale_l = 1.0 - 0.3 * np.sin(abs(angle_rad)) * np.sign(angle_rad)
        scale_r = 1.0 + 0.3 * np.sin(abs(angle_rad)) * np.sign(angle_rad)
        dst = np.array([
            (0, cy + (0 - cy) * scale_l),
            (w - 1, cy + (0 - cy) * scale_r),
            (0, cy + (h - 1 - cy) * scale_l),
            (w - 1, cy + (h - 1 - cy) * scale_r),
        ], dtype=np.float32)
    H, _ = cv2.findHomography(src, dst)
    return cv2.warpPerspective(image, H, (w, h),
                                  flags=cv2.INTER_LINEAR,
                                  borderMode=cv2.BORDER_CONSTANT,
                                  borderValue=0.5)


def apply_screen_camera_channel(carrier: np.ndarray,
                                   params: ChannelParams | None = None) -> np.ndarray:
    """Apply the synthetic screen-camera channel to a grayscale carrier.

    Args:
        carrier: (H, W) grayscale image in [0, 1].
        params: ChannelParams instance.

    Returns:
        (H, W) grayscale image in [0, 1] -- what a phone camera capturing
        this carrier on a screen and saving as JPEG would produce, after
        rectification back to canonical (canvas) coordinates.
    """
    if params is None:
        params = ChannelParams()
    rng = np.random.default_rng(params.seed)
    h, w = carrier.shape

    # 1. Apply screen subpixel raster
    rgb = _apply_subpixel_raster(carrier, params)

    # 2. Camera oversampling: upsample, then we'll downsample after demosaic
    if params.camera_oversample != 1.0:
        new_h = int(round(h * params.camera_oversample))
        new_w = int(round(w * params.camera_oversample))
        rgb = cv2.resize(rgb, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
    else:
        new_h, new_w = h, w

    # 3. Bayer mosaic + 4. bilinear demosaic
    raw = _bayer_sample(rgb, offset_x=params.bayer_offset_x,
                          offset_y=params.bayer_offset_y)
    rgb_demosaic = _bilinear_demosaic(raw)

    # 5. Convert to grayscale (camera does its own Y conversion)
    gray = _rgb_to_gray(rgb_demosaic)

    # 6. Downsample back to canonical resolution
    if params.camera_oversample != 1.0:
        gray = cv2.resize(gray, (w, h), interpolation=cv2.INTER_AREA)

    # 7. JPEG round-trip
    if params.jpeg_quality < 100:
        gray = _jpeg_roundtrip(gray, params.jpeg_quality)

    # 8. Mild perspective tilt
    if params.perspective_tilt_deg != 0.0:
        gray = _perspective_tilt(gray, params.perspective_tilt_deg, axis='x')

    # 9. Additive Gaussian noise
    if params.gaussian_sigma > 0:
        gray = gray + rng.normal(0, params.gaussian_sigma, gray.shape).astype(np.float32)
        gray = np.clip(gray, 0, 1)

    return gray.astype(np.float32)
