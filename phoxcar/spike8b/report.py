"""Spike-8B human-readable report generator.

Reads `results/spike8b_results.json` (produced by `analyze.py`) and writes
`results/SPIKE8B_REPORT.md` — a Markdown report aggregating pass/fail by
phone × screen × condition, photometric drift summary, common failure modes.

Re-run after each `analyze.py` run.
"""
from __future__ import annotations
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS_PATH = HERE / 'results' / 'spike8b_results.json'
REPORT_PATH = HERE / 'results' / 'SPIKE8B_REPORT.md'


def _passed(r: dict) -> bool:
    return bool(r.get('sha256_ok_full') or r.get('sha256_ok_cropped'))


def _crop_only(r: dict) -> bool:
    """True if cropped decode succeeded but full-frame did not."""
    return bool(r.get('sha256_ok_cropped') and not r.get('sha256_ok_full'))


def _bucket_by(results: list, key: str) -> dict:
    out = defaultdict(list)
    for r in results:
        v = (r.get('meta') or {}).get(key)
        out[v if v else '(unparsed)'].append(r)
    return out


def _pass_rate_table(results: list, axis_key: str) -> str:
    buckets = _bucket_by(results, axis_key)
    if not buckets or set(buckets.keys()) == {'(unparsed)'}:
        return f"  (no `{axis_key}` axis info available — captures named outside the convention)\n"
    lines = [f"| {axis_key} | n | pass | rate | crop-only |",
              f"|---|---|---|---|---|"]
    for k in sorted(buckets.keys()):
        rs = buckets[k]
        n = len(rs)
        n_pass = sum(1 for r in rs if _passed(r))
        n_crop = sum(1 for r in rs if _crop_only(r))
        rate = (100 * n_pass / n) if n else 0.0
        lines.append(f"| {k} | {n} | {n_pass} | {rate:.0f}% | {n_crop} |")
    return '\n'.join(lines) + '\n'


def _cross_table(results: list, row_key: str, col_key: str) -> str:
    rows = sorted({(r.get('meta') or {}).get(row_key) for r in results
                    if (r.get('meta') or {}).get(row_key)})
    cols = sorted({(r.get('meta') or {}).get(col_key) for r in results
                    if (r.get('meta') or {}).get(col_key)})
    if not rows or not cols:
        return f"  (insufficient `{row_key}` × `{col_key}` info)\n"
    lines = [f"| {row_key} \\ {col_key} | " + ' | '.join(cols) + ' |',
              "|---|" + "|".join(['---'] * len(cols)) + '|']
    for rk in rows:
        cells = []
        for ck in cols:
            rs = [r for r in results
                    if (r.get('meta') or {}).get(row_key) == rk
                    and (r.get('meta') or {}).get(col_key) == ck]
            if not rs:
                cells.append('—')
            else:
                p = sum(1 for r in rs if _passed(r))
                cells.append(f"{p}/{len(rs)}")
        lines.append(f"| {rk} | " + ' | '.join(cells) + ' |')
    return '\n'.join(lines) + '\n'


def _photometric_summary(results: list) -> str:
    transforms = [r['transform'] for r in results
                    if r.get('transform') and _passed(r)]
    if not transforms:
        return "  (no successful decodes — no photometric drift fits to summarize)\n"
    a = [t['a'] for t in transforms]
    b = [t['b'] for t in transforms]
    g = [t['gamma'] for t in transforms]
    fr = [t.get('fit_residual', 0.0) for t in transforms]
    lines = [
        "Pilot-fit intensity transform `I_observed = a + b · I_true^γ`:",
        "",
        "| param | min | median | max | n |",
        "|---|---|---|---|---|",
        f"| a (offset)   | {min(a):+.3f} | {statistics.median(a):+.3f} | {max(a):+.3f} | {len(a)} |",
        f"| b (gain)     | {min(b):.3f} | {statistics.median(b):.3f} | {max(b):.3f} | {len(b)} |",
        f"| γ (gamma)    | {min(g):.3f} | {statistics.median(g):.3f} | {max(g):.3f} | {len(g)} |",
        f"| fit residual | {min(fr):.3f} | {statistics.median(fr):.3f} | {max(fr):.3f} | {len(fr)} |",
    ]
    return '\n'.join(lines) + '\n'


def _failure_mode_summary(results: list) -> str:
    failures = [r for r in results if not _passed(r)]
    if not failures:
        return "  No failures.\n"
    by_error = defaultdict(int)
    for r in failures:
        err = (r.get('decode_error_cropped')
                 or r.get('decode_error_full')
                 or r.get('load_error')
                 or r.get('fatal_error') or 'unknown')
        # Normalize: keep prefix up to first colon for grouping
        prefix = err.split(':')[0].strip() if isinstance(err, str) else 'unknown'
        by_error[prefix] += 1
    lines = ["| failure category | count |", "|---|---|"]
    for cat, count in sorted(by_error.items(), key=lambda kv: -kv[1]):
        lines.append(f"| {cat} | {count} |")
    return '\n'.join(lines) + '\n'


def main() -> int:
    if not RESULTS_PATH.exists():
        print(f"ERROR: {RESULTS_PATH.name} not found. "
                "Run `python3 analyze.py` first.", file=sys.stderr)
        return 1
    profile = json.loads(RESULTS_PATH.read_text())
    results = profile['results']
    n = profile['n_captures']
    n_pass = profile['n_pass']
    rate = 100.0 * n_pass / max(1, n)

    md = []
    md.append(f"# Spike-8B real-camera validation report")
    md.append(f"")
    md.append(f"**Timestamp:** {profile['timestamp']}")
    md.append(f"**Substrate under test:** {profile['substrate_under_test']}")
    md.append(f"**Reference payload SHA-256:** `{profile['reference_payload_sha256']}`")
    md.append(f"**Captures:** {n} (pass: {n_pass}, fail: {n - n_pass}, rate: {rate:.1f}%)")
    md.append(f"")
    md.append(f"## Headline")
    md.append(f"")
    if n_pass == n and n > 0:
        md.append(f"**FULL PASS** across all {n} real-camera captures. "
                    f"P3.A's synthetic-tested envelope holds in the wild.")
    elif n_pass == 0:
        md.append(f"**FULL FAIL.** Something fundamental is wrong: capture quality, "
                    f"reference carrier display, or substrate brittleness. Investigate "
                    f"before continuing.")
    else:
        md.append(f"**Partial pass ({rate:.0f}%).** P3.A handles a subset of real-world "
                    f"capture conditions cleanly. Failure axes below identify what "
                    f"P3.C needs to address.")
    md.append(f"")

    md.append(f"## Pass rate by axis")
    md.append(f"")
    md.append(f"### By phone")
    md.append(f"")
    md.append(_pass_rate_table(results, 'phone'))
    md.append(f"### By screen")
    md.append(f"")
    md.append(_pass_rate_table(results, 'screen'))
    md.append(f"### By distance")
    md.append(f"")
    md.append(_pass_rate_table(results, 'distance'))
    md.append(f"### By angle")
    md.append(f"")
    md.append(_pass_rate_table(results, 'angle'))
    md.append(f"### By lighting")
    md.append(f"")
    md.append(_pass_rate_table(results, 'lighting'))

    md.append(f"## Phone × screen cross-table")
    md.append(f"")
    md.append(_cross_table(results, 'phone', 'screen'))

    md.append(f"## Distance × angle cross-table")
    md.append(f"")
    md.append(_cross_table(results, 'distance', 'angle'))

    md.append(f"## Real-world photometric drift")
    md.append(f"")
    md.append(_photometric_summary(results))
    md.append(f"_(How `b` and `γ` distribute tells us how much display gamma + camera "
                f"gamma compounding shows up in practice.)_")
    md.append(f"")

    md.append(f"## Failure modes")
    md.append(f"")
    md.append(_failure_mode_summary(results))

    md.append(f"## Per-capture detail")
    md.append(f"")
    md.append(f"| filename | phone | screen | dist | angle | light | result | RS corr | err |")
    md.append(f"|---|---|---|---|---|---|---|---|---|")
    for r in results:
        m = r.get('meta') or {}
        ok = _passed(r)
        crop = _crop_only(r)
        result_cell = ('PASS (cropped)' if crop
                          else ('PASS' if ok else 'FAIL'))
        err = (r.get('decode_error_cropped')
                 or r.get('decode_error_full')
                 or r.get('load_error') or '')
        if ok:
            err = ''
        rs_corr = r.get('rs_corrected_frames')
        rs_corr_cell = '—' if rs_corr is None else str(rs_corr)
        err_clean = err.replace('|', '\\|')[:80] if isinstance(err, str) else ''
        md.append(f"| `{r.get('filename', '')}` | {m.get('phone', '?')} | "
                    f"{m.get('screen', '?')} | {m.get('distance', '?')} | "
                    f"{m.get('angle', '?')} | {m.get('lighting', '?')} | "
                    f"{result_cell} | {rs_corr_cell} | "
                    f"{err_clean} |")
    md.append(f"")

    md.append(f"## Recommended next step")
    md.append(f"")
    if n == 0:
        md.append(f"  No captures yet. Run the protocol in CAPTURE_PROTOCOL.md.")
    elif n_pass == n:
        md.append(f"  Real-world envelope confirmed. P3.C is a research luxury, "
                    f"not a blocker. V1 ships on P3.A as-is.")
    else:
        md.append(f"  Look at the failing axes above. The most-common failure category "
                    f"+ the worst-performing phone/screen/condition combination tells "
                    f"us what P3.C iteration to scope first.")
        md.append(f"")
        md.append(f"  - If failures concentrate in `dim` lighting → photometric "
                    f"calibration drift exceeds pilot-fit envelope.")
        md.append(f"  - If failures concentrate in `tilt30` angles → P3.C v3 "
                    f"(multi-rotation NCC) or wider quad-detection range.")
        md.append(f"  - If failures concentrate at `far` distances → ArUco markers "
                    f"too small in frame; bump marker pixel size.")
        md.append(f"  - If failures spread evenly → real-world is generally harder "
                    f"than synthetic; need a multi-axis P3.C revision.")

    REPORT_PATH.write_text('\n'.join(md))
    print(f"Wrote {REPORT_PATH.relative_to(HERE.parent.parent)}")
    print(f"Headline: pass {n_pass}/{n} ({rate:.1f}%)")
    return 0


if __name__ == '__main__':
    sys.exit(main())
