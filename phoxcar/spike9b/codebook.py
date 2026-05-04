"""256-glyph phoxoidal codebook for spike-6 (codebook modulation).

Built once at module load via deterministic farthest-point sampling in
c_ortho space (the Cholesky-orthonormalized 5-coefficient basis from
spike-3's basis.py).

Design rationale (per ChatGPT's analysis 2026-05-04, Bug-audited):

- Spike-3 / spike-4 / spike-5 encode 40 bits per germ as continuous
  5-coefficient values, recovered to 8-bit precision per coefficient.
  This works at zero noise but fails at low noise because the inverse
  fit operates near the noise floor (per spike-4 sec 3 byte-error cliff).

- Codebook modulation encodes 8 bits per germ as one of 256 distinct
  glyphs in coefficient space. Decode is nearest-neighbor against the
  fixed codebook — categorical, not continuous. Errors only occur when
  the noisy descriptor lands closer to a wrong codeword than the right
  one. With maximum-min-distance codebook design, this is dramatically
  more noise-tolerant than continuous parameter recovery.

- Cost: 5x density penalty (1 byte/germ vs spike-3's 5 bytes/germ).

# Codebook construction

Farthest-point sampling: start with a large random pool of c_ortho
candidates uniform in the basis's codebook box, then greedily pick
points that are maximally distant from already-chosen ones (in
Euclidean metric in c_ortho space, which is the natural noise metric
because the basis is orthonormal).

The result is a 256-codeword codebook with a high minimum pairwise
distance, which directly lower-bounds the symbol error rate against
Gaussian noise on the recovered descriptor.
"""
from __future__ import annotations
import numpy as np

from basis import OrthoBasis


def design_codebook(
    basis: OrthoBasis,
    n_codewords: int = 256,
    n_pool: int = 20000,
    seed: int = 20260504,
) -> np.ndarray:
    """Farthest-point sampling codebook in c_ortho space.

    Returns:
        codebook: (n_codewords, 5) c_ortho coordinates.
    """
    rng = np.random.default_rng(seed)
    bounds = basis.codebook_bounds                              # (5,)
    # Sample uniform in c_ortho box
    pool = rng.uniform(-bounds[None, :], bounds[None, :],
                        size=(n_pool, 5))
    # Initial codeword: centered (average of bounds) origin-ish
    chosen = [0]
    # Distance bookkeeping: min distance from each pool point to ANY chosen point
    min_dist = np.linalg.norm(pool - pool[0][None, :], axis=1)
    min_dist[0] = 0.0
    for _ in range(n_codewords - 1):
        # Pick the pool point with max min_dist (farthest from any chosen)
        next_idx = int(np.argmax(min_dist))
        chosen.append(next_idx)
        # Update min distances against the new chosen point
        new_dists = np.linalg.norm(pool - pool[next_idx][None, :], axis=1)
        min_dist = np.minimum(min_dist, new_dists)
        min_dist[next_idx] = 0.0
    codebook = pool[chosen]
    return codebook


def codebook_min_pairwise_distance(codebook: np.ndarray) -> float:
    """Diagnostic: minimum pairwise Euclidean distance across the codebook."""
    n = codebook.shape[0]
    min_d = np.inf
    for i in range(n - 1):
        d = np.linalg.norm(codebook[i + 1:] - codebook[i][None, :], axis=1)
        m = float(np.min(d))
        if m < min_d:
            min_d = m
    return min_d


def encode_byte_to_c_ortho(b: int, codebook: np.ndarray) -> np.ndarray:
    """Encode a single byte (0..255) to its c_ortho codebook entry."""
    if not (0 <= b < codebook.shape[0]):
        raise ValueError(f"byte {b} out of codebook range [0, {codebook.shape[0]})")
    return codebook[b].copy()


def decode_c_ortho_to_byte(c_ortho_recovered: np.ndarray, codebook: np.ndarray) -> int:
    """Nearest-neighbor decode in Euclidean c_ortho distance."""
    distances = np.linalg.norm(codebook - c_ortho_recovered[None, :], axis=1)
    return int(np.argmin(distances))


def decode_with_confidence(
    c_ortho_recovered: np.ndarray,
    codebook: np.ndarray,
) -> tuple[int, float, float]:
    """Decode + return confidence (margin between best and 2nd-best).

    Returns:
        byte:           recovered byte value (codebook index).
        best_distance:  distance to nearest codeword.
        margin:         distance to 2nd nearest minus best (larger is better).
    """
    distances = np.linalg.norm(codebook - c_ortho_recovered[None, :], axis=1)
    sorted_idx = np.argsort(distances)
    best = int(sorted_idx[0])
    return best, float(distances[best]), float(distances[sorted_idx[1]] - distances[best])
