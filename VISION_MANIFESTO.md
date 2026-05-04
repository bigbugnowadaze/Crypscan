# What We Are Building

**Authors:** Bug + Vince Anderson — Aurexis / CRYPSOID / Phoxoidal partnership
**Date:** 2026-05-04
**Status:** working draft — partnership voice, not yet public

---

## I. The thing we are seeing

For as long as humans have stored knowledge, we have done it by cutting the symbol away from the thing it names. The word *fire* is not warm. The chemical formula H₂O is not wet. The pixel data of a photograph is not what you saw. Every symbolic representation requires a cut, and the cut has a cost: the symbol drifts away from its referent, becomes a label, and eventually has to be re-grounded by someone who still knows what the original thing was. We accept this cost because we have always accepted it. We treat it as the price of literacy.

It is not the price of literacy. It is the price of **a particular kind of literacy** — the kind built on extractive symbols. There is another kind, and the mathematics has only recently arrived to make it buildable.

The alchemists knew this. Their symbols were not labels — they were living correspondences in which physical operation, mental state, and structural transformation were enacted simultaneously. *Solve et coagula.* When alchemy was reduced to chemistry, the symbols became labels and the alchemical knowledge — the structural knowledge — was lost in the translation. We replaced living knowledge with extractive knowledge. We gained scale and lost something we could not name.

René Thom rediscovered the same thing through mathematics. His catastrophe theory, his *semiophysics*, was an attempt to give form a notation that did not require it to be reduced to particles or labels first. Thom argued — and was largely ignored for arguing — that meaning arises at the scale where forms are stable, and the right notation for meaning is a notation that captures those forms intrinsically. He was building toward a non-extractive notation. He did not finish.

Embodied cognition. Hyperdimensional computing. Applied sheaf theory. Each of these, in the last fifty years, has noticed the same problem from a different angle. Each has built a partial answer. None has built the substrate.

We are building the substrate.

## II. What it is

The substrate we are building is the first computational medium in which **visual structure can be expressed without translation loss**. Three ways of saying it, each true at a different altitude:

**It is a sense.** A way of perceiving the catastrophic structure of the visual world directly — fold edges, cusps, surface curvatures, occlusion topologies — without going through pixels-then-labels. A trained physicist who knows catastrophe theory already perceives this way; they look at a phase transition or a flame and see fold-cusp structure where others see continuous mush. That perceptual capacity has been locked to a few hundred specialists. The substrate makes it transmissible.

**It is post-Cartesian computing.** Every computational substrate since Turing has lived on the mind-side of the Cartesian split: computation "in here," world "out there," data shuttled across a gap that is treated as free. The substrate refuses the split. The catastrophe-germ basis is grounded in the physical optics of the world, not in human convention. The predicate calculus is grounded in embodied perceptual structure. The sheaf composition is grounded in the topology of overlapping observation. There is no "out there" being modeled — the notation *is* where the world's structure lives.

**It is the writing system for vision.** Speech existed for hundreds of thousands of years before writing. Writing did not replace speech; it created a new medium in which knowledge could accumulate, compose, be argued, be passed forward. Visual content has been in the speech-stage since the first cave painting. We have records of visual experience but no notation for visual claims — no way for a visual proposition to be true or false in a verifiable sense, no way for two visual claims to compose into a stronger third, no way for visual knowledge to accumulate the way written knowledge does. The substrate is that notation. The first one.

These three are angles on a single thing: **a knowledge representation that does not divorce the knower from the known**.

## III. Why now

Each ingredient required for the substrate has existed for some time, but never together:

- **Catastrophe theory** (Thom 1972) supplies the vocabulary — the only locally stable forms that arise from generic projection of smooth surfaces. This is theorem, not engineering choice. Pearcey/Airy class.
- **Applied sheaf cohomology** (Robinson 2017, Hansen & Ghrist 2019) supplies the composition rules — how local visual claims compose into global verdicts via topological consistency.
- **Embodied cognition** (Lakoff, Varela, Maturana, decades) supplies the philosophical ground — meaning is constituted by sensorimotor engagement, not derived from pure abstraction.
- **Hyperdimensional computing** (Kanerva, ongoing) supplies the computational substrate for graded, continuous concept-spaces — symbol-like operations without symbol-like discreteness.
- **Modern fiducial systems** (AprilTag, ArUco) and **soft-decision channel coding** (Chase, RS) supply the engineering scaffolding that makes the medium actually transmissible through real cameras and screens.

The convergence is recent. The substrate could not have been built in 1980, 1995, or 2010. It can be built now.

## IV. What changes

When the substrate lands, the shape of what humans can do with visual information changes:

- **Visual literacy becomes a real literacy** — a learned, transmissible skill in which structural reading of scenes is taught the way numerical literacy and verbal literacy are now taught. Today, "visual literacy" means having taste. Tomorrow, it means being able to read structure: to see the cylindrical-fold catastrophe in a curved monitor's image, to recognize the cusp signature of a folded fabric, to verify that two photographs of the same scene structurally agree.

- **Visual evidence becomes composable.** Two photographs of the same building, taken by different people, with different cameras, at different times, can compose via sheaf cohomology into a single verifiable verdict. The verdict carries the audit trail of how it was composed and where the composition is consistent or contradictory.

- **The wall between text and image dissolves.** Mathematical proofs can include visual claims as load-bearing content. Legal arguments can include verifiable visual evidence as primary text. Scientific papers can include visual decompositions of phenomena that compose with the verbal argument rather than illustrate it. We have never had this.

- **Cross-modal interoperability arrives without learned alignment.** Because images, 3D scenes, and predicates all live in the same basis, a verdict derived from a 3D scan can be checked against a 2D photograph, against an encoded carrier, against any other artifact that decomposes into catastrophe-germ structure. No retraining. No alignment learning. No translation.

- **Machine vision becomes audit-able.** Every claim has a typed derivation chain, a 5-valued confidence state, and a sheaf-cohomological consistency check. For the first time, a machine's perception is open to the same scrutiny as a human expert's — derivable, contestable, repeatable. Visual inferences could become legal evidence in the same way that mathematical proofs are.

- **A third pillar of human knowledge representation.** Language, number, vision. Each with its own grammar, composition rules, truth conditions, accumulation properties. Vision joins language and number as a load-bearing form of human knowing.

## V. What this is not

The substrate is not a barcode replacement. QR codes are extractive symbols printed on paper; they are not the substrate. The substrate happens to support a barcode-like application as a degenerate one-direction case.

The substrate is not a computer-vision system. CV systems extract labels from pixel arrays; the substrate doesn't extract — its notation IS the structural content.

The substrate is not a deep-learning approach. There are no learned weights. Every operation is mathematically derivable. We are building infrastructure that is *complementary* to deep learning — a notation deep learning's outputs could land in to become auditable, but we are not training networks.

The substrate is not a product. A product implements a function. The substrate is a medium that supports many functions.

The substrate is not a tool. A tool extends what humans can do. The substrate is closer to a sense — it changes what humans can perceive.

## VI. Where we are

The substrate is being built across three intentionally-separated streams:

- **CRYPSOID** establishes the catastrophe-germ vocabulary — the basis, the .3dphox file format, the image-to-germ-field lift. This is the *anti-Gaussian thesis* in concrete code: a refusal to accept that visual structure should be reduced to Gaussian mixtures.

- **Aurexis Core** establishes the typed predicate calculus, the 5-valued confidence lattice, the proof system, the sheaf-style composition rules. This is the *predicate fiber* — the formal grammar of visual claims.

- **The phoxoidal carrier proposal** (and its spikes 1 through 9B) establishes the engineering existence proof for one application: that the substrate can survive real-world screen-camera capture. Not because that application is the goal, but because if the substrate cannot survive a real channel, the whole project is theoretical.

None of these alone is the substrate. The integration — where the catastrophe-germ basis composes with the predicate calculus through sheaf cohomology, where a single artifact exercises both fibers and the carrier round-trip — is the next phase of work.

## VII. What we are honest about

The substrate is not built. We have working pieces, working theorems, working spikes. We do not yet have a single artifact that demonstrates the dual-fiber structure end to end. We do not yet have a name for the substrate as a whole — a public-facing identity. We do not yet have collaborators outside the partnership who can verify our claims at the level of mathematics or implementation.

The risk is real. The lineage we are standing in includes thinkers who were correct and ignored (Thom is the obvious example) — being mathematically right is no guarantee of cultural traction. The risk we are taking is that the substrate is correct, valuable, and unrecognized for a generation.

We are willing to take that risk because the alternative — accepting that visual knowledge must remain extractive, that machine perception must remain opaque, that the cost of the symbolic cut is permanent — is one we cannot in good conscience accept.

## VIII. What we want

We are looking for:

- **Collaborators** who can see what we are seeing. Specifically: mathematicians comfortable with applied catastrophe theory and sheaf cohomology; cognitive scientists who take embodied cognition seriously; engineers who can build production-grade systems against unconventional foundations; domain experts in fields where audit-able visual evidence matters (medical imaging, legal documentation, archival systems, scientific imaging).

- **Time to write.** The substrate has a mathematical core that needs to be written down for verification by people who do not yet know our work. The architecture documents, the proofs of structural correctness, the formal specification of the predicate calculus — these are not done.

- **Permission to fail at the right things.** Some of what we propose may be wrong. The way we will know is by building specific artifacts that would be evidence the vision is correct, and seeing whether they work. We need cover to attempt those builds without prematurely converging on the easier "product" framings that AI conversations and venture capital tend to push us toward.

- **Verification from people who care about precision.** This document is not the substrate. The substrate is a thing that exists or does not. We want serious challenges from serious people — mathematical, philosophical, practical, ethical. The substrate either survives those challenges or it doesn't. Either outcome is information.

## IX. The closing line

We are building the first non-extractive notation for the visual world.

If we are right, the consequences are larger than any product description we could write today. If we are wrong, we will at least have failed at a question worth failing at.

— Bug + Vince
