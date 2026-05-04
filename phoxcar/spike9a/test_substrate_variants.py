"""Compare substrate variants on the calibrated synthetic channel.

Tests:
  V0 (control): P3.A as-is. Existing 256-codeword codebook, decoder uses
                LSQ-fit catastrophe-germ coefficients then NN in c_ortho
                space. Should reproduce the spike-8B run 4 failure on
                the synthetic channel.

  V1 (image-space NCC, N=256): same encoder. Decoder swaps coefficient-
                space NN for image-space NCC against 256 pre-rendered
                templates. Tests whether the failure is the LSQ fit
                or the codebook density.

  V2 (image-space NCC, N=16, discrete encoder): both encoder and decoder
                use a 16-codeword subset chosen by max pairwise image-
                space NCC distance. Tests the full ADDENDUM_04 §3 #1
                recommendation.

  V3 (V2 + amp=0.6): same as V2 but with germ amplitude 0.6 instead of
                0.3. Tests whether higher contrast moves germ signal
                further over the channel noise floor.

For each variant: encode a payload, push through the calibrated synthetic
channel, decode. Pass = SHA-256 round-trip ok.

Reports per-variant:
  - PASS / FAIL on default channel
  - manifest-byte success rate (how many of 8 manifest bytes correctly
    decoded — a graded signal even when the magic check fails)
  - median NCC (or coefficient-distance) of the per-germ classifier
  - what this tells us about the substrate
"""
from __future__ import annotations
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import encoder           # P3.A encoder
import decoder            # P3.A decoder (coefficient-space)
from channel import apply_screen_camera_channel, ChannelParams
from discrete_decoder import decode_discrete
from discrete_codebook import (
    select_discrete_subset, render_codebook_patches, classify_patch,
)
from basis import OrthoBasis
from codebook import design_codebook
from manifest import MANIFEST_GERM_COUNT
from encoder import (
    EncodeParams, MANIFEST_INDICES, PILOT_INDICES, PAYLOAD_START_INDEX,
    grid_index_to_pixel, N_PILOTS, CANVAS_WIDTH, CANVAS_HEIGHT,
)
from fiducials import canonical_layout
from pose import detect_pose, rectify
from pilots import (
    fit_intensity_transform, gather_anchor_pixels, select_anchor_codewords,
)


# Recoverable text payload, big enough to exercise RS + Brotli
PAYLOAD = (
    b"SPIKE-9A substrate variant comparison. "
    b"Per ADDENDUM_04 we test whether image-space NCC against a "
    b"discrete 16-symbol subset clears the synthetic screen-camera "
    b"channel where 256-codeword continuous LSQ fails. If yes, we "
    b"have validated the central hypothesis (channel-mismatch, not "
    b"insufficient ECC) and earned the right to spike-9B on real "
    b"hardware. If no, neural codec is forced. " * 2
)


def manifest_byte_success_count(decoded_bytes: bytes,
                                  expected_magic_bytes: bytes = b'PHX1') -> int:
    """How many of the first 4 manifest bytes match expected magic."""
    if len(decoded_bytes) < 4:
        return 0
    return sum(1 for i in range(4) if decoded_bytes[i] == expected_magic_bytes[i])


def get_decoded_manifest_bytes_v0(rectified_corrected, basis, codebook, params):
    """Run V0 (P3.A control) manifest sampling and return the decoded bytes."""
    from solver import fit_carrier_sigmoid
    from codebook import decode_with_confidence
    manifest_pos = np.array([grid_index_to_pixel(i) for i in MANIFEST_INDICES])
    thetas, _ = fit_carrier_sigmoid(rectified_corrected, manifest_pos, basis,
                                       amp=params.amp, baseline=params.baseline)
    out = bytearray(MANIFEST_GERM_COUNT)
    for g in range(MANIFEST_GERM_COUNT):
        c_ortho = basis.M_to_ortho @ thetas[g]
        b, _, _ = decode_with_confidence(c_ortho, codebook)
        out[g] = b
    return bytes(out)


def get_decoded_manifest_bytes_v1(rectified_corrected, basis, codebook, params):
    """V1: image-space NCC against full 256 templates."""
    templates = render_codebook_patches(codebook, basis, params.amp, params.baseline)
    half = basis.half_size
    out = bytearray(MANIFEST_GERM_COUNT)
    for g, idx in enumerate(MANIFEST_INDICES):
        cx, cy = grid_index_to_pixel(idx)
        x0 = cx - half; x1 = cx + half + 1
        y0 = cy - half; y1 = cy + half + 1
        patch = rectified_corrected[y0:y1, x0:x1].astype(np.float32)
        best_idx, _, _ = classify_patch(patch, templates)
        out[g] = best_idx
    return bytes(out)


def encode_with_subset(payload, filename, out_path, subset_indices,
                         params, sidecar=False):
    """Encode using only codebook indices from `subset_indices`. Each input
    byte b is mapped to subset_indices[b mod len(subset)]. Decoder must
    use the same subset to recover."""
    n_keep = len(subset_indices)

    # Monkey-patch: encode by mapping byte -> subset_indices[byte mod n_keep]
    # We do this by writing a custom version of encoder.encode that maps
    # before calling the codebook.
    import brotli
    from header import pack_header
    from ecc import rs_encode
    from manifest import encode_manifest_bytes
    from density import render_germ_patch_sigmoid
    from fiducials import canonical_layout, render_markers_into_canvas

    compressed = brotli.compress(payload, quality=11)
    framed = pack_header(payload, compressed, filename)
    rs_encoded = rs_encode(framed)
    n_payload_germs = len(rs_encoded)
    n_used_germs = PAYLOAD_START_INDEX + n_payload_germs
    if n_used_germs > encoder.GRID_SLOTS:
        raise ValueError(f"payload too large for canvas")

    basis = OrthoBasis.build(params.half_size, params.sigma)
    full_codebook = design_codebook(
        basis, n_codewords=params.n_codewords, seed=params.codebook_seed,
    )
    anchor_codeword_indices, _ = select_anchor_codewords(
        full_codebook, basis, params.amp, params.baseline, n_anchors=N_PILOTS,
    )

    manifest_bytes = encode_manifest_bytes(payload_byte_count=n_payload_germs)

    # Map each byte -> subset codebook index
    def map_byte(b):
        return int(subset_indices[int(b) % n_keep])

    cw_per_index = {}
    for i, b in enumerate(manifest_bytes):
        cw_per_index[MANIFEST_INDICES[i]] = map_byte(int(b))
    for i, ci in enumerate(anchor_codeword_indices):
        cw_per_index[PILOT_INDICES[i]] = int(ci)  # pilots use full codebook
    for i, b in enumerate(rs_encoded):
        cw_per_index[PAYLOAD_START_INDEX + i] = map_byte(int(b))

    canvas = np.full((CANVAS_HEIGHT, CANVAS_WIDTH), params.background, dtype=np.float64)
    half = basis.half_size
    for grid_idx in sorted(cw_per_index.keys()):
        cx, cy = grid_index_to_pixel(grid_idx)
        x0 = cx - half; x1 = cx + half + 1
        y0 = cy - half; y1 = cy + half + 1
        cw_idx = cw_per_index[grid_idx]
        theta_raw = basis.M_to_raw @ full_codebook[cw_idx]
        patch = render_germ_patch_sigmoid(theta_raw, basis, params.amp, params.baseline)
        canvas[y0:y1, x0:x1] = patch

    layout = canonical_layout(CANVAS_WIDTH, CANVAS_HEIGHT)
    canvas = render_markers_into_canvas(canvas, layout)
    canvas = np.clip(canvas, 0.0, 1.0)
    img = (canvas * 255.0 + 0.5).astype(np.uint8)
    Image.fromarray(img, mode='L').save(out_path, format='PNG')
    return n_payload_germs


def decode_with_subset(png_path, subset_indices, params):
    """Decode using image-space NCC against the subset templates.
    Maps decoded subset-index back through subset_indices to original byte."""
    n_keep = len(subset_indices)
    img = Image.open(png_path)
    arr = np.asarray(img, dtype=np.float32) / 255.0

    basis = OrthoBasis.build(params.half_size, params.sigma)
    full_codebook = design_codebook(
        basis, n_codewords=params.n_codewords, seed=params.codebook_seed,
    )
    subset = full_codebook[subset_indices]
    templates = render_codebook_patches(subset, basis, params.amp, params.baseline)

    layout = canonical_layout(CANVAS_WIDTH, CANVAS_HEIGHT)
    pose = detect_pose(arr, layout)
    if not pose.success:
        return {'pose_ok': False, 'error': pose.error}

    rectified = rectify(arr, pose.homography, CANVAS_WIDTH, CANVAS_HEIGHT)

    pilot_positions = np.array(
        [grid_index_to_pixel(i) for i in PILOT_INDICES], dtype=np.int64,
    )
    anchor_idx, anchor_patches = select_anchor_codewords(
        full_codebook, basis, params.amp, params.baseline, n_anchors=N_PILOTS,
    )
    anchor_pix = [(int(p[0]), int(p[1])) for p in pilot_positions]
    try:
        I_true, I_obs = gather_anchor_pixels(rectified, anchor_pix, anchor_patches, params.half_size)
        tx = fit_intensity_transform(I_true, I_obs)
    except Exception as e:
        return {'pose_ok': True, 'error': f'pilot fit: {e}'}
    rectified_corrected = tx.invert(rectified).astype(np.float32)

    # Decode all germs using image-space NCC against subset templates
    half = basis.half_size
    grid_to_byte = {}
    nccs = []
    # Decode manifest+payload germs (we don't know n_payload_germs yet)
    # First decode just the manifest cluster
    for g, idx in enumerate(MANIFEST_INDICES):
        cx, cy = grid_index_to_pixel(idx)
        x0 = cx - half; x1 = cx + half + 1
        y0 = cy - half; y1 = cy + half + 1
        patch = rectified_corrected[y0:y1, x0:x1].astype(np.float32)
        best_idx, ncc, _ = classify_patch(patch, templates)
        # Map back: decoded byte = inverse of (byte mod n_keep) — we can only recover
        # the modular residue. For 4-bit subset, decoded byte ∈ [0, n_keep).
        # The encoder stored byte b as subset_indices[b mod n_keep], decoded subset
        # index gives us back (b mod n_keep). For magic check, we want byte values
        # in 0..255 — accepting that we cannot disambiguate full bytes with n_keep<256.
        grid_to_byte[idx] = int(best_idx)  # subset index = byte mod n_keep
        nccs.append(ncc)

    return {
        'pose_ok': True,
        'manifest_bytes': bytes(grid_to_byte[i] for i in MANIFEST_INDICES),
        'median_ncc': float(np.median(nccs)),
        'transform': tx,
    }


def run_variant(name: str, encode_fn, decode_fn, channel_params: ChannelParams):
    print(f"\n{'=' * 70}")
    print(f"  Variant: {name}")
    print(f"{'=' * 70}")
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        clean_png = td / 'clean.png'
        encode_fn(PAYLOAD, 'spike9a.txt', clean_png)
        clean_arr = np.asarray(Image.open(clean_png).convert('L'),
                                  dtype=np.float32) / 255.0
        # Apply synthetic channel
        distorted = apply_screen_camera_channel(clean_arr, channel_params)
        distorted_png = td / 'distorted.png'
        Image.fromarray((distorted * 255 + 0.5).astype(np.uint8), mode='L').save(distorted_png)
        # Decode
        result = decode_fn(distorted_png)
        return result


def main():
    params = EncodeParams()
    basis = OrthoBasis.build(params.half_size, params.sigma)
    full_codebook = design_codebook(
        basis, n_codewords=params.n_codewords, seed=params.codebook_seed,
    )

    # Pre-compute discrete subsets for V2/V3
    print("Building discrete codebook subsets...")
    subset_16, subset_16_indices = select_discrete_subset(
        full_codebook, basis, n_keep=16, amp=params.amp,
        baseline=params.baseline,
    )
    print(f"  N=16 subset selected, indices: {subset_16_indices.tolist()}")

    channel = ChannelParams()  # default

    # ---- V0: P3.A control (coefficient-space LSQ + NN, N=256) ----
    print("\n" + "=" * 70)
    print("  V0: P3.A control (256 cw, coefficient-space LSQ + NN)")
    print("=" * 70)
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        clean = td / 'clean.png'
        encoder.encode(PAYLOAD, 'spike9a.txt', clean, params=params)
        arr = np.asarray(Image.open(clean).convert('L'), dtype=np.float32) / 255.0
        distorted = apply_screen_camera_channel(arr, channel)
        d_png = td / 'd.png'
        Image.fromarray((distorted * 255 + 0.5).astype(np.uint8), mode='L').save(d_png)
        res = decoder.decode(d_png, params=params)
        print(f"  pose_ok:       {res.pose_ok}")
        print(f"  sha_ok:        {res.sha256_ok}")
        print(f"  decode_error:  {res.decode_error}")

    # ---- V1: image-space NCC, N=256 (no encoder change) ----
    print("\n" + "=" * 70)
    print("  V1: 256 cw image-space NCC (no encoder change)")
    print("=" * 70)
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        clean = td / 'clean.png'
        encoder.encode(PAYLOAD, 'spike9a.txt', clean, params=params)
        arr = np.asarray(Image.open(clean).convert('L'), dtype=np.float32) / 255.0
        distorted = apply_screen_camera_channel(arr, channel)
        d_png = td / 'd.png'
        Image.fromarray((distorted * 255 + 0.5).astype(np.uint8), mode='L').save(d_png)
        res = decode_discrete(d_png, n_codewords=256, params=params)
        print(f"  pose_ok:           {res.pose_ok}")
        print(f"  sha_ok:            {res.sha256_ok}")
        print(f"  decode_error:      {res.decode_error}")
        print(f"  median manifest NCC:{res.median_manifest_ncc:.3f}")

    # ---- V2: 16-cw discrete (encoder + decoder use subset) ----
    print("\n" + "=" * 70)
    print("  V2: 16 cw discrete (encoder + decoder match subset)")
    print("=" * 70)
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        clean = td / 'clean.png'
        n_payload = encode_with_subset(PAYLOAD, 'spike9a.txt', clean,
                                          subset_16_indices, params)
        arr = np.asarray(Image.open(clean).convert('L'), dtype=np.float32) / 255.0
        distorted = apply_screen_camera_channel(arr, channel)
        d_png = td / 'd.png'
        Image.fromarray((distorted * 255 + 0.5).astype(np.uint8), mode='L').save(d_png)
        res = decode_with_subset(d_png, subset_16_indices, params)
        if res.get('error'):
            print(f"  ERROR: {res['error']}")
        else:
            decoded_manifest = res['manifest_bytes']
            # For V2 we encoded byte b as subset[b mod 16]. So decoded subset_idx
            # tells us what (b mod 16) was. Compare to expected manifest's first 4
            # bytes mod 16.
            expected_full = b'PHX1'
            expected_residue = bytes([b % 16 for b in expected_full])
            magic_residues_match = sum(1 for i in range(4)
                                          if decoded_manifest[i] == expected_residue[i])
            print(f"  pose_ok:               {res['pose_ok']}")
            print(f"  decoded manifest bytes: {decoded_manifest.hex()}")
            print(f"  expected (b%16):        {expected_residue.hex()}")
            print(f"  magic-residue matches:  {magic_residues_match}/4")
            print(f"  median manifest NCC:    {res['median_ncc']:.3f}")
            tx = res.get('transform')
            if tx:
                print(f"  pilot fit:              a={tx.a:+.3f} b={tx.b:+.3f} γ={tx.gamma:.3f}")

    # ---- V3: 16-cw discrete + amp=0.6 ----
    print("\n" + "=" * 70)
    print("  V3: 16 cw discrete, amp=0.6 (was 0.30)")
    print("=" * 70)
    params_v3 = EncodeParams(amp=0.6)
    basis_v3 = OrthoBasis.build(params_v3.half_size, params_v3.sigma)
    full_v3 = design_codebook(basis_v3, n_codewords=params_v3.n_codewords,
                               seed=params_v3.codebook_seed)
    subset_v3, subset_v3_idx = select_discrete_subset(
        full_v3, basis_v3, n_keep=16, amp=params_v3.amp,
        baseline=params_v3.baseline,
    )
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        clean = td / 'clean.png'
        encode_with_subset(PAYLOAD, 'spike9a.txt', clean, subset_v3_idx, params_v3)
        arr = np.asarray(Image.open(clean).convert('L'), dtype=np.float32) / 255.0
        distorted = apply_screen_camera_channel(arr, channel)
        d_png = td / 'd.png'
        Image.fromarray((distorted * 255 + 0.5).astype(np.uint8), mode='L').save(d_png)
        res = decode_with_subset(d_png, subset_v3_idx, params_v3)
        if res.get('error'):
            print(f"  ERROR: {res['error']}")
        else:
            decoded_manifest = res['manifest_bytes']
            expected_full = b'PHX1'
            expected_residue = bytes([b % 16 for b in expected_full])
            magic_residues_match = sum(1 for i in range(4)
                                          if decoded_manifest[i] == expected_residue[i])
            print(f"  pose_ok:               {res['pose_ok']}")
            print(f"  decoded manifest bytes: {decoded_manifest.hex()}")
            print(f"  expected (b%16):        {expected_residue.hex()}")
            print(f"  magic-residue matches:  {magic_residues_match}/4")
            print(f"  median manifest NCC:    {res['median_ncc']:.3f}")
            tx = res.get('transform')
            if tx:
                print(f"  pilot fit:              a={tx.a:+.3f} b={tx.b:+.3f} γ={tx.gamma:.3f}")


if __name__ == '__main__':
    main()
