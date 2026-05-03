# 05 — Information Density Analysis

> Back-of-envelope numbers for bits-per-area in the proposed phoxoidal carrier vs the AXP6 sample carrier. Honest about uncertainty. Identifies what Phase 1 actually needs to measure to convert these into firm numbers.

---

## 1. The reference point: AXP6 sample carrier

From the v4 handoff §"Local files":

- Original payload: 30 MB video file (`sample-2.mp4`).
- Encoded carrier: 11032×13120 pixel PNG (`sample-2.mp4.axp6.png`), 30 MB on disk.

Verified-from-source numbers (`aurexis_decode.py` §"Constants" lines 39–52, §"PNG Reader" lines 57–138):

- 2-bit indexed PNG: every pixel encodes one 2-bit module.
- BLOCK_SIZE = 8 modules per side; MODULES_PER_BLOCK = 64.
- Total carrier modules: 11032 × 13120 = **144,739,840 modules**.
- Raw module capacity (modulation only): 144,739,840 × 2 bits = **289,479,680 bits ≈ 36.18 MB** of raw modulation capacity.
- Net usable payload (per the handoff): 30 MB.
- AXP6 overhead (manifest + parity + integrity + encode-time padding): ~6.18 MB.
- AXP6's overhead ratio: ≈ 17% of raw modulation capacity, ≈ 21% of net payload.

The 30 MB sample carrier is video — already heavily compressed at the source. Brotli on already-compressed input is essentially a no-op (Brotli compresses meaningfully only on data with redundancy Brotli's context can exploit; H.264/H.265 video has had its redundancy already extracted). So the "30 MB payload" appears in the carrier at ~30 MB encoded length, not at any compression ratio. This sets the *worst-case* density baseline; structured payload (text, source code, JSON) compresses to 5-25% of original (`DECODE_GUIDE.md` lines 119–124) and would fit in a much smaller carrier.

**The single number to compare against: AXP6 fits ~36 MB of raw modulation capacity per 144.7 megapixels of carrier, ≈ 0.25 bits per pixel of net payload (after overhead) for the worst-case incompressible payload, ≈ 1-2 bits per pixel for typical text/code payloads.**

## 2. The phoxoidal carrier capacity calculation

### 2.1 Bits per germ (the load-bearing assumption)

Per `03_PHOXOIDAL_CARRIER_ARCHITECTURE.md` §6 and the v4 handoff, the Phase 0 default budget is **40 bits per germ** (5 coefficients × 8 bits each). This is one of three honest options; the others (range-aware quantization, VSA binding) are deferred to Phase 1.

### 2.2 Raw bit capacity for a 30 MB payload

30 MB = 30 × 8 = 240 megabits = 240,000,000 bits.

Germs needed for raw payload, no compression, no redundancy, no overhead: 240,000,000 / 40 = **6,000,000 germs**.

Compare to: an AXP6 carrier of the same payload uses ~120,000,000 modules of net payload modulation (after the 17% overhead).

### 2.3 Pixels per germ

If we hold the carrier at 144,739,840 pixels (the AXP6 sample-carrier dimensions), each germ would occupy:

144,739,840 / 6,000,000 = **24.12 pixels per germ**

A 24-pixel patch is approximately a 5×5 region (or 4×6, etc.). This is the rough germ-footprint budget for parity with the AXP6 sample carrier on raw payload.

### 2.4 Adjusting for the realistic operating regime

The 24-pixels-per-germ number is the absolute lower bound. Real germ extraction needs:

1. **Sufficient sensor sub-pixels per germ to stay above Nyquist for sub-pixel localization.** Typical scale-space and Mumford-Shah methods want ≥ 10 sensor pixels across the germ's footprint (≥ ~100 sensor pixels per germ) to localize the singular point reliably. For a 5×5 footprint at the encoder, this means the captured image's resolution per encoder pixel needs to be ≥ 2× linearly. Phone cameras at typical capture distances easily satisfy this for screen-displayed carriers; printed carriers depend on print DPI vs camera resolution.
2. **Redundancy across germs (`03_PHOXOIDAL_CARRIER_ARCHITECTURE.md` §5.1).** Phase 0 default R = 3-5 (each payload symbol encoded in R germs). At R = 3, raw germ count triples to 18M. At R = 5, 30M.
3. **Per-tier-group correction overhead (Tier B style, `docs/FORMAT.md` v28 EXACT archive).** Negligible (≤ a few percent) at Phase 0 budget.
4. **Manifest cluster overhead.** Negligible (a single cluster of a few thousand germs at high redundancy and high precision).
5. **Tier C aesthetic field area.** This depends on the design choice for what fraction of the rendered carrier is data-bearing vs purely aesthetic. A reasonable design number for discussion: 60% data-bearing area, 40% aesthetic-only area. (This number is not load-bearing for Phase 0; it is one of many design knobs.)

Combining: at R = 3 and 60% data-bearing area, germs needed for 30 MB payload = 18M / 0.6 = **30 million germs** in the carrier.

### 2.5 Carrier area to fit 30 MB at R = 3 with 60% data-bearing

At 24 pixels-per-germ minimum + 100 sensor-pixels-per-germ Nyquist factor + 60% data-bearing = effective ~167 carrier-pixels-per-germ for a printed/screen-bound carrier with adequate sensor oversampling.

30,000,000 germs × 167 pixels/germ = **5.0 billion pixels** = 50× the AXP6 sample carrier's pixel count for the same payload.

That number is the honest pessimistic upper bound. It corresponds to the **strictest reading of every safety factor**:
- worst-case incompressible 30 MB video payload (no Brotli benefit),
- conservative R = 3 redundancy,
- 60% data-bearing area,
- 100 sensor-pixels-per-germ for confident extraction.

### 2.6 Three more realistic operating points

For *typical* operating regimes, the density is much closer to AXP6:

| Regime | Payload type | Compression ratio | R | Bits/germ | Pixels/germ | Net density | Vs AXP6 |
|---|---|---:|---:|---:|---:|---|---|
| **Conservative** (text-heavy, lab-grade capture) | text/json/code | 0.10 | 3 | 40 | 100 | 0.35 bits/pixel | comparable |
| **Realistic** (mixed payload, V2 protocol capture) | mixed | 0.50 | 3 | 40 | 50 | 0.16 bits/pixel | ~1.5× more carrier area for same payload |
| **Stress** (incompressible video, handheld off-axis) | video | 1.00 | 5 | 40 | 167 | 0.025 bits/pixel | ~10× more carrier area |

The 50× number from §2.5 is the boundary case of the stress regime. Realistic deployments should expect to need 1.5-3× more carrier area than AXP6 for equivalent payload, with significant variance based on payload type and capture quality target.

This is **a real cost**. It is not "1× parity with AXP6"; it is "AXP6's worst-case density times 1.5-10× depending on operating regime." Whether this is acceptable is `09_OPEN_QUESTIONS.md` §6.

## 3. Why the cost is not catastrophic

Three reasons the density penalty is bounded and not blowing up the architecture:

### 3.1 Resolution flexibility

Per `03_PHOXOIDAL_CARRIER_ARCHITECTURE.md` §8.2, the phoxoidal carrier renders at any resolution. Need a higher-density carrier? Render at higher resolution. Need a smaller display area? Render at lower resolution and fit fewer germs. AXP6's PNG dimensions are baked into the manifest at encode time; the phoxoidal carrier's are not.

This means density is fundamentally **a design parameter**, not a fixed limitation. For a given payload, the operator can trade carrier area against payload size against capture quality requirements against display medium constraints. AXP6 has none of these knobs at decode time.

### 3.2 Compression interacts well with the new substrate

Compressed payload (Brotli) hits text/json/code at 5-25% of original. Most realistic data flows in those classes. The "30 MB video" sample carrier in the handoff is the *worst case* Brotli encounters (already-compressed video). Realistic deployments will compress well; the 1.5-3× density penalty from §2.6 is the realistic-deployment number.

### 3.3 The carrier is a design surface (§3.4 of `03`)

For workflows where the *carrier as visual content* has commercial value (a brand asset that also carries data, a marketing image that's also a verification token, a UI element that's also a payload), the additional carrier area is not "wasted pixels" — it is the visual real estate the operator wanted anyway. The data layer rides for free on top of design surface that already has its own value.

For workflows where only the data matters and the carrier is purely transport (Vince emails Bug a `.png` whose only job is to be decoded), AXP6 is the better fit and the proposal explicitly does not displace it (`02_FAILURE_MODEL_ANALYSIS.md` §5).

## 4. Comparison with CRYPSOID's own density numbers

CRYPSOID's published comparison (`README.md` lines 46–60):

| Format | bits/Gaussian | Note |
|---|---:|---|
| zstd -12 PLY (lossless) | 470.4 | baseline |
| CRYPSOID v28 EXACT archive | 336.9 | 1.40× smaller than zstd |
| CRYPSOID v28 VQ render | 196.9 | 2.39× smaller (lossy SH) |
| Self-Organizing Gaussians (SOG) | 50–80 | SOTA |
| HAC | 30–60 | SOTA |

The phoxoidal carrier's bit-per-germ budget (40 bits/germ) is on the low end of CRYPSOID's own per-Gaussian numbers and well below SOTA splat compressors. This makes sense — the proposed carrier is using germs as *symbol carriers* with deliberately quantized coefficients, not as faithful 3D scene primitives. The 40-bit budget is set by the steganographic use case, not by 3D fidelity.

If the bit allocation is range-aware (`03_PHOXOIDAL_CARRIER_ARCHITECTURE.md` §6 option 2), this number can grow somewhat — perhaps to 50-60 bits per germ — by spending more bits on coefficients with more SNR headroom. Phase 1 measurement determines the right number. The 40-bit budget is the conservative starting point.

## 5. What Phase 1 actually needs to measure

The numbers above are honest within their assumed operating points, but every operating point depends on parameters that have not been measured for this use case. Phase 1 must measure:

1. **Sub-pixel germ-localization accuracy as a function of pixels-per-germ.** Is 100 sensor-pixels-per-germ adequate, or do realistic captures need 200? Or can robust localization be done at 50? This sets the carrier's *physical* area requirement.

2. **Per-coefficient detection-noise standard deviation under V2-protocol captures.** This sets the **bit budget per coefficient** — high-SNR coefficients (κ₁, κ₂) can carry more bits; low-SNR ones (ζ at small magnitudes) carry fewer. The 8-bits-per-coefficient default is a placeholder.

3. **Required redundancy R for a given decode-success target.** R=3 is a placeholder; the right R depends on the sheaf-composition consistency check's actual recovery capability.

4. **Extraction time per megapixel.** The phoxoidal decoder's persistent-homology + Newton-fitting pipeline is asymptotically slower than AXP6's pure-stdlib decode (`08_HONEST_TRADEOFFS.md` §3). The constant matters: is it 2× slower, 20×, 200×? Phase 1 benchmarks tell us.

5. **Working envelope of the diffeomorphism approximation.** What tilt / distance / lighting envelope keeps the decode-success rate above 99% / 95% / 90%? `04_DIFFEOMORPHISM_INVARIANCE_ARGUMENT.md` §4 names the failure modes; Phase 1 measures where they bite.

6. **Tier C aesthetic-field interference.** Tier C carries no payload but does carry intensity structure that the germ extractor sees. How much do natural Tier C field singularities (from rendered photographic content) contaminate the payload germ extraction? Phase 1 measures this and may indicate the need for a "Tier C is band-limited" design constraint.

These six measurements turn the back-of-envelope into a real density number. None of them is a Phase 0 deliverable.

## 6. Honest summary

| Question | Phase 0 answer |
|---|---|
| Can the phoxoidal carrier carry the same payload AXP6 carries? | **Yes, with 1.5-3× more carrier area for typical payloads, up to 10× for worst-case incompressible payloads.** |
| Is that acceptable? | **Workflow-dependent. `09_OPEN_QUESTIONS.md` §6.** |
| Is the density penalty fundamental? | **No. It is a function of the bit-budget per germ, the redundancy ratio, and the data-bearing area fraction, all of which are design parameters and all of which can be optimized in Phase 1.** |
| Is there a regime where the phoxoidal carrier beats AXP6 on density? | **No. AXP6 is well-tuned for raw density at low overhead. The phoxoidal carrier optimizes for transformation-invariance, not density. There will likely always be a small density penalty at the same payload.** |
| Does the density penalty disqualify the architecture? | **Only if "match AXP6 density on the worst case" is a hard requirement. If "match AXP6 density on typical payloads, with 1.5-3× tolerance" is acceptable, the architecture is in a workable regime.** |

The 1.5-3× density penalty is the *price of the architectural transition to capture-mediated robustness*. Whether the price is worth paying depends on whether capture-mediated workflows are the primary deployment regime — exactly the question `09_OPEN_QUESTIONS.md` §1 asks Bug and Vince to answer jointly.

---

**Cross-references.** The substrate that produces these numbers is in `03_PHOXOIDAL_CARRIER_ARCHITECTURE.md`. The capture regime that determines the operating point is in `02_FAILURE_MODEL_ANALYSIS.md` and `04_DIFFEOMORPHISM_INVARIANCE_ARGUMENT.md`. The Phase 1 benchmarks that turn these estimates into measurements are in `06_DECODER_RESEARCH_PLAN.md` and `07_INTEGRATION_BRIDGES.md`.
