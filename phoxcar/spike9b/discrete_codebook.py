"""Discrete N-symbol codebook for spike-9A's substrate variant.

ADDENDUM_04 §3 #1 recommendation: replace continuous-coefficient codebook
NN with a discrete classifier in IMAGE space. Pick N codewords whose
RENDERED patches are maximally distinct under NCC, then classify a
captured patch by direct NCC against the N templates.

Key change vs P3.A:
  - P3.A: 256 codewords. Decode = fit 5 catastrophe coefficients via LSQ,
           NN in 5-D c_ortho space. LSQ is biased by structured spatial
           noise (moiré stripes).
  - P3.B/9A: N codewords. Decode = compute NCC of captured patch against
           N pre-rendered template patches. Image-space classification.
           Tolerates biased features as long as bias doesn't cross a
           decision boundary.

Codeword selection strategy: greedy farthest-point sampling in IMAGE-NCC
distance (NOT in c_ortho coefficient distance). This is the right
distance metric for the actual decision the decoder will make.

Note on "what gets rendered":
  Each codeword is still a 5-vector in c_ortho space (so that the encoder
  can use the existing rendering pipeline). The DIFFERENCE is that we
  pick the c_ortho vectors so their RENDERED patches are far apart, and
  the decoder skips the LSQ fit and directly NCCs the patches.
"""
from __future__ import annotations
import numpy as np

from basis import OrthoBasis
from codebook import design_codebook
from density import render_germ_patch_sigmoid


def _ncc(a: np.ndarray, b: np.ndarray) -> float:
    """Normalized cross-correlation of two patches."""
    a = a.astype(np.float64) - a.mean()
    b = b.astype(np.float64) - b.mean()
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float((a * b).sum() / (na * nb))


def render_codebook_patches(codebook_c_ortho: np.ndarray,
                              basis: OrthoBasis,
                              amp: float,
                              baseline: float = 0.0) -> np.ndarray:
    """Render each codeword's patch. Returns (N, side, side) array."""
    n = codebook_c_ortho.shape[0]
    side = 2 * basis.half_size + 1
    out = np.zeros((n, side, side), dtype=np.float64)
    for i in range(n):
        theta_raw = basis.M_to_raw @ codebook_c_ortho[i]
        out[i] = render_germ_patch_sigmoid(theta_raw, basis,
                                              amp=amp, baseline=baseline)
    return out


def select_discrete_subset(full_codebook: np.ndarray,
                              basis: OrthoBasis,
                              n_keep: int,
                              amp: float,
                              baseline: float = 0.0,
                              seed: int = 20260504) -> tuple[np.ndarray, np.ndarray]:
    """Pick `n_keep` codewords from `full_codebook` by greedy farthest-point
    sampling in image-space NCC-distance.

    NCC distance := 1 - NCC(template_i, template_j). This is in [0, 2];
    high distance = visually distinct templates.

    Returns:
        subset_c_ortho: (n_keep, 5) selected codewords in c_ortho space
        subset_indices: (n_keep,) indices into the original full_codebook
    """
    patches = render_codebook_patches(full_codebook, basis, amp, baseline)
    n_total = patches.shape[0]

    # Compute pairwise NCC distance matrix (lazy: only when needed)
    # For 256 codewords with 25x25 patches that's ~256x256 = 65k pairs,
    # each ~1k-element NCC: ~65 million ops. Fine.
    flat = patches.reshape(n_total, -1).astype(np.float64)
    norms = np.linalg.norm(flat - flat.mean(axis=1, keepdims=True), axis=1)
    centered = flat - flat.mean(axis=1, keepdims=True)
    # NCC matrix
    ncc = (centered @ centered.T) / np.outer(norms, norms + 1e-12)
    distance = 1.0 - ncc                # NCC distance, [0, 2]
    np.fill_diagonal(distance, 0.0)

    # Greedy farthest-point sampling
    rng = np.random.default_rng(seed)
    chosen = [0]
    min_dist_to_chosen = distance[0].copy()
    min_dist_to_chosen[0] = 0.0
    for _ in range(n_keep - 1):
        next_idx = int(np.argmax(min_dist_to_chosen))
        chosen.append(next_idx)
        new_d = distance[next_idx]
        min_dist_to_chosen = np.minimum(min_dist_to_chosen, new_d)
        min_dist_to_chosen[next_idx] = 0.0

    subset_indices = np.array(chosen, dtype=np.int64)
    subset = full_codebook[subset_indices]
    return subset, subset_indices


def report_subset_stats(subset_c_ortho: np.ndarray,
                          basis: OrthoBasis,
                          amp: float,
                          baseline: float = 0.0) -> dict:
    """Diagnostic: report min/median pairwise NCC and image-space distance
    of the selected subset."""
    patches = render_codebook_patches(subset_c_ortho, basis, amp, baseline)
    n = patches.shape[0]
    nccs = []
    for i in range(n):
        for j in range(i + 1, n):
            nccs.append(_ncc(patches[i], patches[j]))
    nccs = np.array(nccs)
    return {
        'n_codewords': n,
        'min_ncc': float(nccs.min()),
        'median_ncc': float(np.median(nccs)),
        'max_ncc': float(nccs.max()),
        'min_distance': float(1.0 - nccs.max()),
        'median_distance': float(1.0 - np.median(nccs)),
        'max_distance': float(1.0 - nccs.min()),
    }


def classify_patch(captured_patch: np.ndarray,
                     templates: np.ndarray) -> tuple[int, float, float]:
    """Image-space NCC classifier. Returns (best_idx, best_ncc, margin).

    Args:
        captured_patch: (side, side) extracted from rectified image.
        templates: (N, side, side) rendered codeword templates.

    Returns:
        best_idx: index of the matched codeword.
        best_ncc: NCC value of the match (higher is better).
        margin: best_ncc minus second-best ncc (larger is more confident).
    """
    p = captured_patch.astype(np.float64)
    p = p - p.mean()
    pn = np.linalg.norm(p)
    if pn == 0:
        return 0, -1.0, 0.0
    p = p / pn

    n = templates.shape[0]
    nccs = np.zeros(n, dtype=np.float64)
    for i in range(n):
        t = templates[i].astype(np.float64)
        t = t - t.mean()
        tn = np.linalg.norm(t)
        if tn == 0:
            nccs[i] = -1.0
            continue
        nccs[i] = float((p * (t / tn)).sum())

    sort_idx = np.argsort(nccs)[::-1]
    best = int(sort_idx[0])
    return best, float(nccs[best]), float(nccs[best] - nccs[sort_idx[1]])
