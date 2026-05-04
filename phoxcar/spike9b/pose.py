"""ArUco-based pose recovery for P3.A.

Pipeline:
    captured image (8-bit grayscale)
      -> cv2.aruco.ArucoDetector.detectMarkers
      -> identify 4 expected IDs (NW=0, NE=1, SW=2, SE=3)
      -> use marker centers as 4-point homography correspondences
      -> rectify image to canonical canvas via cv2.warpPerspective

This is dramatically more robust than spike-8A's homemade corner finders
because cv2.aruco handles:
  - perspective tilt (markers detected as quads, not blobs)
  - rotation 0-360°
  - scale variation
  - photometric drift (adaptive thresholding internal to detector)
  - sub-pixel marker corner refinement
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import cv2
from cv2 import aruco

from fiducials import (
    get_dictionary, MarkerLayout, canonical_layout,
    NW_ID, NE_ID, SW_ID, SE_ID,
)


@dataclass
class PoseResult:
    success: bool
    homography: np.ndarray | None        # (3, 3) — observed -> canonical
    observed_centers: dict | None        # {'NW': (x, y), ...}
    error: str | None


def _detect_markers(image_8bit: np.ndarray) -> tuple[list, list]:
    """Run ArUco detection on an 8-bit image. Returns (corners, ids).

    Adaptive threshold window expanded from default [3, 23] to [3, 53]
    to handle our 96-pixel markers without aliasing. Sub-pixel corner
    refinement for higher-precision homography correspondences.
    """
    d = get_dictionary()
    params = aruco.DetectorParameters()
    params.adaptiveThreshWinSizeMin = 3
    params.adaptiveThreshWinSizeMax = 53
    params.adaptiveThreshWinSizeStep = 10
    params.cornerRefinementMethod = aruco.CORNER_REFINE_SUBPIX
    detector = aruco.ArucoDetector(d, params)
    corners, ids, _ = detector.detectMarkers(image_8bit)
    return corners, ids


def detect_pose(captured: np.ndarray, layout: MarkerLayout) -> PoseResult:
    """Detect ArUco markers in a captured image and recover homography.

    Args:
        captured: (H, W) grayscale image in [0, 1] (will be converted to 8-bit).
        layout: canonical marker layout (the 4 marker positions in the
                 encoder's canonical canvas).

    Returns:
        PoseResult with homography (observed -> canonical) on success.
    """
    if captured.dtype != np.uint8:
        img8 = (np.clip(captured, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)
    else:
        img8 = captured

    corners, ids = _detect_markers(img8)
    if ids is None or len(ids) < 4:
        return PoseResult(False, None, None,
                            f"detected {0 if ids is None else len(ids)} markers, need 4")

    # Find the 4 expected IDs and gather their CENTERS (not corner-of-marker
    # coordinates — the centers correspond to the canonical layout's marker
    # centers).
    id_to_center = {}
    flat_ids = ids.flatten().tolist()
    for marker_corners, marker_id in zip(corners, flat_ids):
        if int(marker_id) in (NW_ID, NE_ID, SW_ID, SE_ID):
            # marker_corners shape is (1, 4, 2) — 4 corners with (x, y) coords.
            # Center is the mean of the 4 corners.
            cs = marker_corners.reshape(-1, 2)
            cx = float(np.mean(cs[:, 0]))
            cy = float(np.mean(cs[:, 1]))
            id_to_center[int(marker_id)] = (cx, cy)

    missing = [name for name, mid in
                [('NW', NW_ID), ('NE', NE_ID), ('SW', SW_ID), ('SE', SE_ID)]
                if mid not in id_to_center]
    if missing:
        return PoseResult(False, None, None,
                            f"missing markers: {missing}")

    canonical = layout.corner_centers()
    observed_centers = {
        'NW': id_to_center[NW_ID],
        'NE': id_to_center[NE_ID],
        'SW': id_to_center[SW_ID],
        'SE': id_to_center[SE_ID],
    }

    src = np.array([observed_centers[k] for k in ('NW', 'NE', 'SW', 'SE')], dtype=np.float32)
    dst = np.array([canonical[k] for k in ('NW', 'NE', 'SW', 'SE')], dtype=np.float32)

    H, _ = cv2.findHomography(src, dst, method=0)
    if H is None:
        return PoseResult(False, None, observed_centers, "findHomography failed")

    return PoseResult(True, H, observed_centers, None)


def rectify(captured: np.ndarray,
              homography: np.ndarray,
              canvas_w: int,
              canvas_h: int,
              fill: float = 0.5) -> np.ndarray:
    """Warp the captured image to canonical (canvas_h, canvas_w) coords."""
    if captured.dtype != np.float32:
        src = captured.astype(np.float32)
    else:
        src = captured
    rectified = cv2.warpPerspective(
        src, homography, (canvas_w, canvas_h),
        flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT,
        borderValue=fill,
    )
    return rectified
