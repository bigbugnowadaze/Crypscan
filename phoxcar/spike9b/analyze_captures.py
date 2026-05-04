"""Spike-9C analyze script — decode real phone captures of the
reference_carrier_v9b.png with the spike-9B substrate.

Workflow:
  1. Bug displays reference_carrier_v9b.png on the Asus laptop
     (or whichever screen) in Chrome F11 fullscreen at native 1:1
  2. Bug captures with S21 FE per the spike-8B solo CAPTURE_PROTOCOL
  3. Bug drops captures into phoxcar/spike9b/captures/raw/
  4. Run this script: python3 analyze_captures.py
  5. Per-capture results print to stdout; summary written to results/
"""
from __future__ import annotations
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import decoder
from encoder import EncodeParams
from fiducials import canonical_layout
from pose import detect_pose
from encoder import CANVAS_WIDTH, CANVAS_HEIGHT


REFERENCE_INFO_PATH = HERE / 'reference_carrier_v9b.info.json'
RAW_DIR = HERE / 'captures' / 'raw'
PROCESSED_DIR = HERE / 'captures' / 'processed'
RESULTS_PATH = HERE / 'results' / 'spike9c_results.json'

FILENAME_RE = re.compile(
    r'^(?P<phone>[a-z0-9]+)_(?P<screen>[a-z0-9]+)_(?P<distance>[a-z]+)_'
    r'(?P<angle>[a-z0-9]+)_(?P<lighting>[a-z]+)_(?P<seq>\d+)\.(?:jpg|jpeg|png)$',
    re.IGNORECASE,
)


def parse_filename(name: str) -> dict:
    m = FILENAME_RE.match(name)
    if not m:
        return {'parsed': False}
    g = m.groupdict()
    g['parsed'] = True
    g['seq'] = int(g['seq'])
    return g


def load_capture(path: Path) -> np.ndarray:
    img = ImageOps.exif_transpose(Image.open(path)).convert('L')
    return np.asarray(img, dtype=np.float32) / 255.0


def maybe_crop_to_markers(image: np.ndarray, margin_frac: float = 0.10):
    """Try ArUco detection on full image; if it finds markers, crop to bbox."""
    layout = canonical_layout(CANVAS_WIDTH, CANVAS_HEIGHT)
    pose = detect_pose(image, layout)
    if not pose.success:
        return None
    centers = np.array(list(pose.observed_centers.values()), dtype=np.float64)
    x_min, y_min = centers.min(axis=0)
    x_max, y_max = centers.max(axis=0)
    w = x_max - x_min; h = y_max - y_min
    side = max(w, h)
    margin = side * margin_frac
    x0 = max(0, int(round(x_min - margin)))
    y0 = max(0, int(round(y_min - margin)))
    x1 = min(image.shape[1], int(round(x_max + margin)))
    y1 = min(image.shape[0], int(round(y_max + margin)))
    if x1 - x0 < 100 or y1 - y0 < 100:
        return None
    return image[y0:y1, x0:x1].copy()


def analyze_one(path: Path, expected_sha: str, params: EncodeParams) -> dict:
    name = path.name
    meta = parse_filename(name)
    t0 = time.perf_counter()
    record = {
        'filename': name, 'meta': meta,
        'load_error': None, 'image_size': None,
        'pose_ok_full': None, 'sha_ok_full': None, 'err_full': None,
        'pose_ok_cropped': None, 'sha_ok_cropped': None, 'err_cropped': None,
        'median_manifest_ncc': None, 'median_payload_ncc': None,
        'pilot_calibration': None, 'n_pilots_per_quadrant': None,
        'rs_corrected_frames': None, 'rs_failed_frames': None,
        'observed_filename': None, 'wall_time_s': None,
    }
    try:
        captured = load_capture(path)
    except Exception as e:
        record['load_error'] = f"{type(e).__name__}: {e}"
        record['wall_time_s'] = time.perf_counter() - t0
        return record
    record['image_size'] = list(captured.shape[::-1])

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    proc_full = PROCESSED_DIR / (path.stem + '_full.png')
    Image.fromarray((np.clip(captured, 0, 1) * 255 + 0.5).astype(np.uint8),
                       mode='L').save(proc_full)

    res = decoder.decode(proc_full, params=params,
                            use_per_quadrant_calibration=True)
    record['pose_ok_full'] = bool(res.pose_ok)
    record['sha_ok_full'] = bool(res.sha256_ok)
    record['err_full'] = res.decode_error
    record['median_manifest_ncc'] = res.median_manifest_ncc
    record['median_payload_ncc'] = res.median_payload_ncc
    record['pilot_calibration'] = res.pilot_calibration
    record['n_pilots_per_quadrant'] = res.n_pilots_per_quadrant
    record['rs_corrected_frames'] = res.rs_corrected_frames
    record['rs_failed_frames'] = res.rs_failed_frames
    if res.sha256_ok:
        record['observed_filename'] = res.filename

    if not res.sha256_ok:
        cropped = maybe_crop_to_markers(captured)
        if cropped is not None:
            proc_crop = PROCESSED_DIR / (path.stem + '_cropped.png')
            Image.fromarray((np.clip(cropped, 0, 1) * 255 + 0.5).astype(np.uint8),
                               mode='L').save(proc_crop)
            res2 = decoder.decode(proc_crop, params=params,
                                     use_per_quadrant_calibration=True)
            record['pose_ok_cropped'] = bool(res2.pose_ok)
            record['sha_ok_cropped'] = bool(res2.sha256_ok)
            record['err_cropped'] = res2.decode_error
            if res2.sha256_ok:
                record['observed_filename'] = res2.filename
                record['median_manifest_ncc'] = res2.median_manifest_ncc
                record['median_payload_ncc'] = res2.median_payload_ncc
                record['rs_corrected_frames'] = res2.rs_corrected_frames
                record['rs_failed_frames'] = res2.rs_failed_frames

    record['wall_time_s'] = time.perf_counter() - t0
    return record


def main():
    if not REFERENCE_INFO_PATH.exists():
        print(f"ERROR: {REFERENCE_INFO_PATH.name} not found. "
                f"Run `python3 generate_reference.py` first.", file=sys.stderr)
        return 1
    info = json.loads(REFERENCE_INFO_PATH.read_text())
    expected_sha = info['reference_payload_sha256']
    params = EncodeParams()

    if not RAW_DIR.exists():
        print(f"ERROR: {RAW_DIR} does not exist. Drop captures there first.",
                file=sys.stderr)
        return 1

    captures = sorted([p for p in RAW_DIR.iterdir()
                        if p.suffix.lower() in ('.jpg', '.jpeg', '.png')])
    if not captures:
        print(f"WARNING: no captures in {RAW_DIR}")
        return 0

    print(f"Analyzing {len(captures)} captures with spike-9B substrate ...")
    results = []
    n_pass = n_fail = 0
    for i, path in enumerate(captures, 1):
        try:
            r = analyze_one(path, expected_sha, params)
        except Exception as e:
            import traceback
            r = {'filename': path.name, 'fatal_error': str(e),
                 'traceback': traceback.format_exc()}
        results.append(r)
        passed = r.get('sha_ok_full') or r.get('sha_ok_cropped')
        if passed:
            n_pass += 1
        else:
            n_fail += 1
        sym = '[PASS]' if passed else '[FAIL]'
        crop_note = (' (after auto-crop)'
                       if r.get('sha_ok_cropped') and not r.get('sha_ok_full')
                       else '')
        err = r.get('err_cropped') or r.get('err_full') or ''
        wall = r.get('wall_time_s') or 0.0
        ncc = r.get('median_payload_ncc') or 0.0
        print(f"  [{i:>3}/{len(captures)}] {sym} {path.name}{crop_note}  "
                f"NCC={ncc:.3f}  {wall:.2f}s  "
                f"{('('+err+')') if err and not passed else ''}")

    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    profile = {
        'timestamp': timestamp,
        'spike': 'spike-9C (real-camera validation of spike-9B substrate)',
        'substrate': 'channel-matched catastrophe-germ (sigma=8 + image-NCC + multi-pilot)',
        'reference_payload_sha256': expected_sha,
        'n_captures': len(captures),
        'n_pass': n_pass,
        'n_fail': n_fail,
        'pass_rate': n_pass / max(1, len(captures)),
        'results': results,
    }
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(profile, indent=2))
    print()
    rate = 100 * n_pass / max(1, len(captures))
    print(f"Pass rate: {n_pass}/{len(captures)} ({rate:.1f}%)")
    print(f"Wrote {RESULTS_PATH.relative_to(HERE.parent.parent)}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
