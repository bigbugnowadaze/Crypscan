# refs/

Pointers to source materials this Phase 0 package was authored against. Nothing here is redistributed source — these are *path indexes* for the reviewer.

## Layout

| Subdirectory | What it points to |
|---|---|
| `crypsoid/` | The CRYPSOID public repo (`https://github.com/bigbugnowadaze/CRYPSOID`) |
| `aurexis/` | The Aurexis Core public repo (`https://github.com/KungFury87/Aurexis`) |
| `donald_decode_v2/` | The standalone AXP6 decoder bundle whose contents are present in this repo's root (`aurexis_decode.py`, `DECODE_GUIDE.md`) |

Each subdirectory contains a small `INDEX.md` listing the file paths the proposal cites and a one-line description of each. To reproduce the citations:

```bash
git clone https://github.com/bigbugnowadaze/CRYPSOID.git
git clone https://github.com/KungFury87/Aurexis.git
```

Then read each cited file at the path noted in the relevant `INDEX.md`.

## Why pointers, not copies?

1. The handoff (`cowork_handoff_v4_phoxoidal_carrier_redesign.md` §"Source materials") explicitly directs the agent to "verify against the source," not to redistribute it.
2. CRYPSOID and Aurexis Core are each owned by their respective authors. The Phase 0 package's role is to compose a proposal, not to fork either project.
3. Path indexes are stable enough — the proposal cites file paths and line numbers; reproducing the citations requires the reader to clone the repos at any commit later than the cited line numbers' introduction.
