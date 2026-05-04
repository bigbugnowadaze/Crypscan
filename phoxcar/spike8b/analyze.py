"""Spike-8B capture analysis.

Reads phone captures from `captures/raw/`, decodes each with the P3.A
pipeline, writes per-capture results to `results/spike8b_results.json`.

Workflow:
    captures/raw/{phone}_{screen}_{distance}_{angle}_{lighting}_{seq}.jpg
      -> auto-rotate via EXIF
      -> convert to grayscale float [0, 1]
      -> attempt P3.A decode
         (P3.A's ArUco pose recovery handles un-cropped photos natively;
          markers can be detected anywhere in the frame.)
      -> if pose detected but decode failed AND image is large:
         crop to ArUco bounding box + 10% margin, retry
      -> record everything

Re-run safely; `analyze.py` overwrites `spike8b_results.json` on each run.
"""
from __future__ import annotations
import hashlib
import json
import re
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

HERE = Path(__file__).resolve().parent
P3A = HERE.parent / 'p3a_aruco'
sys.path.insert(0, str(P3A))

from encoder import EncodeParams                                  # noqa: E402
from decoder import decode                                         # noqa: E402
from fiducials import canonical_layout                             # noqa: E402
from pose import detect_pose                                       # noqa: E402

import cv2                                                          # noqa: E402

REFERENCE_INFO_PATH = HERE / 'reference_carrier.info.json'
RAW_DIR = HERE / 'captures' / 'raw'
PROCESSED_DIR = HERE / 'captures' / 'processed'
RESULTS_PATH = HERE / 'results' / 'spike8b_results.json'

# Filename pattern: {phone}_{screen}_{distance}_{angle}_{lighting}_{seq}.{ext}
FILENAME_RE = re.compile(
    r'^(?P<phone>[a-z0-9]+)_(?P<screen>[a-z0-9]+)_(?P<distance>[a-z]+)_'
    r'(?P<angle>[a-z0-9]+)_(?P<lighting>[a-z]+)_(?P<seq>\d+)\.(?:jpg|jpeg|png)$',
    re.IGNORECASE,
)


def parse_filename(name: str) -> dict:
    m = FILENAME_RE.match(name)
    if not m:
        return {'phone': None, 'screen': None, 'distance': None,
                'angle': None, 'lighting': None, 'seq': None,
                'parsed': False}
    g = m.groupdict()
    g['parsed'] = True
    g['seq'] = int(g['seq'])
    return g


def load_capture(path: Path) -> tuple[np.ndarray, dict]:
    """Load a phone capture, auto-rotate via EXIF, return (gray_float, meta)."""
    img = Image.open(path)
    meta = {'orig_size': list(img.size), 'orig_mode': img.mode}
    img = ImageOps.exif_transpose(img)
    meta['post_exif_size'] = list(img.size)
    if img.mode != 'L':
        img = img.convert('L')
    arr = np.asarray(img, dtype=np.float32) / 255.0
    return arr, meta


def maybe_crop_to_markers(image: np.ndarray, params: EncodeParams,
                            margin_frac: float = 0.10) -> np.ndarray | None:
    """Try ArUco detection on the full image; if it finds markers, crop to bbox."""
    layout = canonical_layout(1280, 1280)
    pose = detect_pose(image, layout)
    if not pose.success:
        return None
    centers = np.array(list(pose.observed_centers.values()), dtype=np.float64)
    x_min, y_min = centers.min(axis=0)
    x_max, y_max = centers.max(axis=0)
    w = x_max - x_min
    h = y_max - y_min
    side = max(w, h)
    margin = side * margin_frac
    x0 = max(0, int(round(x_min - margin)))
    y0 = max(0, int(round(y_min - margin)))
    x1 = min(image.shape[1], int(round(x_max + margin)))
    y1 = min(image.shape[0], int(round(y_max + margin)))
    if x1 - x0 < 100 or y1 - y0 < 100:
        return None
    return image[y0:y1, x0:x1].copy()


def analyze_one(path: Path, expected_sha_hex: str,
                  params: EncodeParams) -> dict:
    """Analyze a single capture and return a result dict."""
    name = path.name
    file_meta = parse_filename(name)
    t0 = time.perf_counter()
    record = {
        'filename': name,
        'meta': file_meta,
        'load_error': None,
        'image_size': None,
        'pose_ok_full': None,
        'sha256_ok_full': None,
        'decode_error_full': None,
        'pose_ok_cropped': None,
        'sha256_ok_cropped': None,
        'decode_error_cropped': None,
        'transform': None,
        'rs_corrected_frames': None,
        'rs_failed_frames': None,
        'observed_filename': None,
        'wall_time_s': None,
    }

    try:
        captured, meta = load_capture(path)
    except Exception as e:
        record['load_error'] = f"{type(e).__name__}: {e}"
        record['wall_time_s'] = time.perf_counter() - t0
        return record
    record['image_size'] = list(captured.shape[::-1])  # (W, H)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    proc_full = PROCESSED_DIR / (path.stem + '_full.png')
    Image.fromarray((np.clip(captured, 0, 1) * 255 + 0.5).astype(np.uint8),
                     mode='L').save(proc_full)

    res_full = decode(proc_full, params=params)
    record['pose_ok_full'] = bool(res_full.pose_ok)
    record['sha256_ok_full'] = bool(res_full.sha256_ok)
    record['decode_error_full'] = res_full.decode_error
    if res_full.transform:
        record['transform'] = res_full.transform.to_dict()
    record['rs_corrected_frames'] = int(res_full.rs_corrected_frames)
    record['rs_failed_frames'] = list(res_full.rs_failed_frames)
    if res_full.sha256_ok:
        record['observed_filename'] = res_full.filename

    if not res_full.sha256_ok:
        cropped = maybe_crop_to_markers(captured, params)
        if cropped is not None:
            proc_crop = PROCESSED_DIR / (path.stem + '_cropped.png')
            Image.fromarray((np.clip(cropped, 0, 1) * 255 + 0.5).astype(np.uint8),
                             mode='L').save(proc_crop)
            res_crop = decode(proc_crop, params=params)
            record['pose_ok_cropped'] = bool(res_crop.pose_ok)
            record['sha256_ok_cropped'] = bool(res_crop.sha256_ok)
            record['decode_error_cropped'] = res_crop.decode_error
            if res_crop.transform and not record['transform']:
                record['transform'] = res_crop.transform.to_dict()
            if res_crop.sha256_ok:
                record['observed_filename'] = res_crop.filename
                record['rs_corrected_frames'] = int(res_crop.rs_corrected_frames)
                record['rs_failed_frames'] = list(res_crop.rs_failed_frames)

    record['wall_time_s'] = time.perf_counter() - t0
    return record


def main() -> int:
    if not REFERENCE_INFO_PATH.exists():
        print(f"ERROR: {REFERENCE_INFO_PATH.name} not found. "
                "Run `python3 generate_reference.py` first.", file=sys.stderr)
        return 1
    info = json.loads(REFERENCE_INFO_PATH.read_text())
    expected_sha_hex = info['reference_payload_sha256']
    params = EncodeParams(pixel_bit_depth=8)

    if not RAW_DIR.exists():
        print(f"ERROR: {RAW_DIR.relative_to(HERE.parent.parent)} does not exist. "
                "Drop your captures there per CAPTURE_PROTOCOL.md.", file=sys.stderr)
        return 1

    captures = sorted([p for p in RAW_DIR.iterdir()
                        if p.suffix.lower() in ('.jpg', '.jpeg', '.png')])
    if not captures:
        print(f"WARNING: no captures found in {RAW_DIR.relative_to(HERE.parent.parent)}")
        return 0

    print(f"Analyzing {len(captures)} captures from "
            f"{RAW_DIR.relative_to(HERE.parent.parent)}/ ...")
    results = []
    n_pass = n_fail = 0
    for i, path in enumerate(captures, 1):
        try:
            r = analyze_one(path, expected_sha_hex, params)
        except Exception as e:
            r = {
                'filename': path.name,
                'fatal_error': f"{type(e).__name__}: {e}",
                'traceback': traceback.format_exc(),
            }
        results.append(r)
        ok = r.get('sha256_ok_full') or r.get('sha256_ok_cropped')
        if ok:
            n_pass += 1
        else:
            n_fail += 1
        sym = '[PASS]' if ok else '[FAIL]'
        crop_note = ''
        if r.get('sha256_ok_cropped') and not r.get('sha256_ok_full'):
            crop_note = ' (after auto-crop)'
        err = r.get('decode_error_cropped') or r.get('decode_error_full') or ''
        err_note = f"  ({err})" if err and not ok else ''
        wall = r.get('wall_time_s') or 0.0
        print(f"  [{i:>3}/{len(captures)}] {sym} {path.name}{crop_note}  "
                f"{wall:.2f}s{err_note}")

    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    profile = {
        'timestamp': timestamp,
        'spike': 'spike-8B',
        'substrate_under_test': 'P3.A (ArUco fiducials + spike-7 codebook)',
        'reference_payload_sha256': expected_sha_hex,
        'n_captures': len(captures),
        'n_pass': n_pass,
        'n_fail': n_fail,
        'pass_rate': n_pass / max(1, len(captures)),
        'results': results,
    }
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(profile, indent=2))
    print()
    print(f"Pass: {n_pass}/{len(captures)} ({100*n_pass/max(1,len(captures)):.1f}%)")
    print(f"Wrote {RESULTS_PATH.relative_to(HERE.parent.parent)}")
    print(f"Run `python3 report.py` to generate the human-readable report.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
