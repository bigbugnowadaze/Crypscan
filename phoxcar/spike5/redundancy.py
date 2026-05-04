"""R-fold per-byte replication + majority-vote recovery.

Encoder layer (between RS encoding and germ packing):

    payload bytes B  (length N)
        --replicate-->  B repeated R times = B || B || ... || B  (length R*N)

So for each byte at index i in the original B, the R copies live at indices
i, i+N, i+2N, ..., i+(R-1)*N in the replicated stream. After bit-packing
into 5-byte germs, those copies end up in different germs at different
scene positions on the rendered grid (since germs are placed in raster
order). This gives spatial separation of redundant copies — a localized
capture failure (e.g., focus blur over one quadrant) cannot wipe all R
copies of any single byte.

Decoder layer (between germ unpacking and RS decoding):

    R*N candidate bytes  -->  reshape to (R, N)
                          -->  per-column majority vote
                          -->  N voted bytes  --> RS decoder

Tie-breaking rule (when no value has a strict majority among R copies):
fall through to copy 0 (the first replica). With R=3 and 30%-per-germ
failure rate, the tie-break pathway only activates on the (rare) case
where all 3 copies disagree, and even then the first copy is correct
~70% of the time, so tie-break contributes ~6% post-vote byte errors
on top of ~3% from "majority of wrong values agreeing" (which itself
is ~1/256 per occurrence). RS(255, 191)'s 12.5% tolerance comfortably
absorbs this.
"""
from __future__ import annotations
from collections import Counter


def replicate(data: bytes, R: int) -> bytes:
    """Replicate `data` R times, returning data || data || ... || data."""
    if R < 1:
        raise ValueError(f"R must be >= 1 (got {R})")
    return data * R


def majority_vote(replicated: bytes, n_original: int, R: int) -> tuple[bytes, dict]:
    """Vote over R copies of an n_original-byte stream.

    Args:
        replicated: bytes of length R * n_original (the recovered byte
                    stream, pre-vote).
        n_original: length of the original stream pre-replication.
        R: number of copies.

    Returns:
        voted: bytes of length n_original (the voted bytes).
        stats: dict with diagnostics:
            'unanimous_bytes':  count where all R copies agreed
            'majority_bytes':   count where >R/2 copies agreed (incl. unanimous)
            'tied_bytes':       count where no strict majority existed
                                (all copies different, or split evenly)
            'tiebreak_byte_disagrees_with_truth': not measurable here
    """
    if len(replicated) != R * n_original:
        raise ValueError(
            f"replicated length {len(replicated)} != R*n_original "
            f"({R}*{n_original}={R*n_original})"
        )
    out = bytearray(n_original)
    unanimous = 0
    majority = 0
    tied = 0
    threshold = R // 2 + 1   # strict majority
    for i in range(n_original):
        candidates = [replicated[r * n_original + i] for r in range(R)]
        counts = Counter(candidates)
        top_value, top_count = counts.most_common(1)[0]
        if top_count == R:
            unanimous += 1
            out[i] = top_value
        elif top_count >= threshold:
            majority += 1
            out[i] = top_value
        else:
            tied += 1
            out[i] = candidates[0]   # tie-break: first copy
    return bytes(out), {
        'unanimous_bytes': unanimous,
        'majority_bytes': majority,
        'tied_bytes': tied,
        'total_bytes': n_original,
        'R': R,
    }
