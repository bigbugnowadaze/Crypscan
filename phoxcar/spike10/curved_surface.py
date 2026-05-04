"""Synthetic curved-surface display for spike-10.

Simulates displaying the carrier on a curved monitor (e.g., MSI G27C4X
1500R curvature) viewed by a roughly-centered camera. The geometric
distortion is:

  - Each canonical-canvas pixel (x, y) is mapped onto a cylindrical
    surface with horizontal curvature radius R (along x-axis only —
    cylindrical, not spherical).
  - The camera at distance D from the screen vertex projects the
    cylindrical surface onto its image plane via pinhole projection.
  - The result is a smooth horizontal foreshortening that's strongest
    near the canvas vertical centerline and weakest at the canvas
    edges (where the surface is closer to perpendicular to the camera).

Parameters:
  R: curvature radius in canvas-pixel units. R=∞ means flat (no
     distortion). R=2000 px ≈ MSI G27C4X 1500R-equivalent at typical
     desktop viewing distances.
  D: camera-to-screen-vertex distance in canvas-pixel units. D=4000
     ≈ typical 30-50cm desktop viewing.
  curvature_axis: 'x' for left-right curvature (typical curved monitor)
                   or 'y' for top-bottom curvature.

The output is the same canonical 1280×1280 image with each pixel
sampled from a transformed source position.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import cv2


@dataclass
class CurvedDisplayParams:
    """Parameters for synthetic curved-display warp."""
    radius: float = 2000.0          # curvature radius (canvas px units; smaller=more curved)
    camera_distance: float = 4000.0  # camera-to-screen distance (px units)
    axis: str = 'x'                  # 'x' = horizontal curve (typical), 'y' = vertical


def _cylindrical_to_camera(canonical_xy: np.ndarray,
                              R: float,
                              D: float,
                              canvas_w: int,
                              canvas_h: int,
                              axis: str = 'x') -> np.ndarray:
    """Map canonical canvas (x, y) coordinates through cylindrical surface
    to camera image plane.

    Returns the camera-plane (x, y) coordinates that the canonical pixel
    appears at after the curve distortion.

    Mathematical model (axis='x'):
      Treat canonical x as arc length along the cylindrical surface.
      Convert to angle θ around the cylinder axis: θ = (x - cx) / R.
      Surface point: (R sin θ, y, R - R cos θ) = (R sin θ, y, R(1 - cos θ))
      Camera at (cx, cy, D); pinhole projection.
      Image plane y = D in front of camera.
    """
    x, y = canonical_xy[..., 0], canonical_xy[..., 1]
    cx = canvas_w / 2.0
    cy = canvas_h / 2.0
    if axis == 'x':
        u = x - cx
        theta = u / R
        x_surface = R * np.sin(theta)
        y_surface = y - cy
        z_surface = R * (1 - np.cos(theta))
    elif axis == 'y':
        v = y - cy
        theta = v / R
        x_surface = x - cx
        y_surface = R * np.sin(theta)
        z_surface = R * (1 - np.cos(theta))
    else:
        raise ValueError(f"axis must be 'x' or 'y'")

    # Pinhole projection: camera at (0, 0, -D) (in surface coords, looking +z).
    # Image plane at z = 0 in camera coordinates; world z relative to that:
    # camera-frame z = D + z_surface.
    z_cam = D + z_surface
    img_x = (x_surface * D / z_cam) + cx
    img_y = (y_surface * D / z_cam) + cy
    return np.stack([img_x, img_y], axis=-1)


def apply_curved_display(canonical: np.ndarray,
                            params: CurvedDisplayParams) -> np.ndarray:
    """Warp a canonical-canvas image to simulate display on a curved
    monitor + camera capture.

    Args:
        canonical: (H, W) grayscale image.
        params: CurvedDisplayParams.

    Returns: (H, W) image, same shape, with curved-display geometric
        distortion applied.
    """
    h, w = canonical.shape
    R = params.radius
    D = params.camera_distance
    if not np.isfinite(R) or R > 1e9:
        return canonical.copy()

    # Build inverse map: for each output pixel (x_dst, y_dst), find which
    # source-canvas pixel it was — by inverting cylindrical_to_camera.
    # Approach: for each canvas point, compute its image-plane location.
    # This gives forward map. For warpaffine we need INVERSE (output to
    # input). Use cv2.remap with the forward map evaluated densely, then
    # invert.
    # For a small smooth warp, we can approximate the inverse by evaluating
    # the forward map and inverting it via interpolation.
    yy, xx = np.indices((h, w), dtype=np.float32)
    canonical_xy = np.stack([xx, yy], axis=-1)
    camera_xy = _cylindrical_to_camera(canonical_xy, R, D, w, h, axis=params.axis)
    # camera_xy[y, x] = where does canvas pixel (x, y) APPEAR on the camera.
    # We need the inverse: for camera pixel (x_cam, y_cam), what canvas
    # pixel landed there?
    # Approximation: under small smooth warps, the inverse is closely
    # related to the forward. Use a fixed-point iteration:
    # x_canvas ≈ x_cam - (camera_xy[y_cam, x_cam, 0] - x_cam)
    # Iterate twice.
    map_x = xx - (camera_xy[..., 0] - xx)
    map_y = yy - (camera_xy[..., 1] - yy)
    # One more iteration: sample canonical_xy at (map_x, map_y)
    # to refine.
    out = cv2.remap(
        canonical.astype(np.float32),
        map_x.astype(np.float32),
        map_y.astype(np.float32),
        interpolation=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0.5,
    )
    return out


def deformation_field(canonical_w: int, canonical_h: int,
                          params: CurvedDisplayParams) -> np.ndarray:
    """Return the per-pixel (dx, dy) deformation field induced by the
    curved-display warp.

    deformation[y, x] = (camera_x, camera_y) - (canvas_x, canvas_y)
    """
    yy, xx = np.indices((canonical_h, canonical_w), dtype=np.float32)
    canonical_xy = np.stack([xx, yy], axis=-1)
    camera_xy = _cylindrical_to_camera(canonical_xy, params.radius,
                                          params.camera_distance,
                                          canonical_w, canonical_h,
                                          axis=params.axis)
    return camera_xy - canonical_xy
