"""ArUco-based fiducial layer for P3.A.

Replaces spike-8A's homemade phoxoidal corner finders with mature CV
markers (OpenCV ArUco DICT_4X4_50). This is the "outer pose layer" of
the split-identity substrate:

    outer pose layer:    ArUco markers (this module)
    inner payload layer: phoxoidal codebook glyph field (frozen,
                          spike-3..7 substrate)

# Configuration (frozen for P3.A)

  - Dictionary: DICT_4X4_50 (50 unique 4x4-bit markers; we use IDs 0-3)
  - Marker IDs:  NW=0, NE=1, SW=2, SE=3
  - Marker size: 96 pixels at canvas resolution (large enough for
                  reliable detection; small enough to leave most of
                  the canvas for payload)
  - Marker margin from edge: 24 pixels
  - White quiet zone padding: 32 pixels on each side of each marker
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import cv2
from cv2 import aruco


# --- Frozen P3.A ArUco config -----------------------------------------------
ARUCO_DICT = aruco.DICT_4X4_50
MARKER_SIZE_PX = 96
MARKER_MARGIN_PX = 60       # marker top-left x,y from canvas edge
QUIET_ZONE_PX = 56           # large white border so ArUco's adaptive threshold
                             # doesn't mistake the quiet-zone boundary on
                             # mid-gray (0.5) canvas baseline for a marker
                             # outer quad. Empirically tuned: 32 fails, 56
                             # passes at baseline=0.5.

NW_ID = 0
NE_ID = 1
SW_ID = 2
SE_ID = 3


def get_dictionary():
    return aruco.getPredefinedDictionary(ARUCO_DICT)


def render_marker(marker_id: int, size_px: int = MARKER_SIZE_PX) -> np.ndarray:
    """Render an ArUco marker as a (size_px, size_px) grayscale image in [0, 1].

    The marker has black bits and a white border (quiet zone is added
    separately by render_markers_into_canvas).
    """
    d = get_dictionary()
    img = aruco.generateImageMarker(d, int(marker_id), size_px)
    return img.astype(np.float32) / 255.0


@dataclass
class MarkerLayout:
    """Canonical positions of the 4 fiducial markers on the carrier canvas.

    Each entry is the (x, y) of the marker's TOP-LEFT pixel (not center).
    The marker spans (x..x+size_px-1, y..y+size_px-1).
    """
    nw_xy: tuple[int, int]
    ne_xy: tuple[int, int]
    sw_xy: tuple[int, int]
    se_xy: tuple[int, int]
    size_px: int

    def corner_centers(self) -> dict[str, tuple[float, float]]:
        s = self.size_px
        return {
            'NW': (self.nw_xy[0] + s / 2, self.nw_xy[1] + s / 2),
            'NE': (self.ne_xy[0] + s / 2, self.ne_xy[1] + s / 2),
            'SW': (self.sw_xy[0] + s / 2, self.sw_xy[1] + s / 2),
            'SE': (self.se_xy[0] + s / 2, self.se_xy[1] + s / 2),
        }


def canonical_layout(canvas_w: int, canvas_h: int,
                       size_px: int = MARKER_SIZE_PX,
                       margin_px: int = MARKER_MARGIN_PX) -> MarkerLayout:
    return MarkerLayout(
        nw_xy=(margin_px, margin_px),
        ne_xy=(canvas_w - margin_px - size_px, margin_px),
        sw_xy=(margin_px, canvas_h - margin_px - size_px),
        se_xy=(canvas_w - margin_px - size_px, canvas_h - margin_px - size_px),
        size_px=size_px,
    )


def render_markers_into_canvas(canvas: np.ndarray,
                                  layout: MarkerLayout,
                                  quiet_zone: int = QUIET_ZONE_PX) -> np.ndarray:
    """Render the 4 ArUco markers onto the canvas (in place AND return).

    Each marker is surrounded by a white quiet zone of `quiet_zone` pixels
    (required by ArUco for reliable detection).
    """
    h, w = canvas.shape
    s = layout.size_px
    placements = [
        (NW_ID, layout.nw_xy),
        (NE_ID, layout.ne_xy),
        (SW_ID, layout.sw_xy),
        (SE_ID, layout.se_xy),
    ]
    for marker_id, (x, y) in placements:
        marker_img = render_marker(marker_id, s)
        # Quiet zone (white) around the marker
        qx0 = x - quiet_zone
        qx1 = x + s + quiet_zone
        qy0 = y - quiet_zone
        qy1 = y + s + quiet_zone
        if qx0 < 0 or qy0 < 0 or qx1 > w or qy1 > h:
            raise ValueError(
                f"marker {marker_id} at ({x},{y}) with quiet_zone={quiet_zone} "
                f"overflows canvas ({w}x{h})"
            )
        canvas[qy0:qy1, qx0:qx1] = 1.0
        # Marker itself
        canvas[y:y + s, x:x + s] = marker_img
    return canvas
