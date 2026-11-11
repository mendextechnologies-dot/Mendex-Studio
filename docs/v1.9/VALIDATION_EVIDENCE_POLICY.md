# MENDEX ENGINEERING STUDIO v1.9 — VALIDATION EVIDENCE POLICY

## 1. Zero Fabrication Policy

- A missing tool, missing input, or unexecuted check is strictly marked `NOT_EVALUATED`.
- Solver exit code $0$ indicates process completion only; engineering pass requires validation against explicit criteria.

---

## 2. Cryptographic Evidence Hashing

- Every staged input, output artifact, waveform, and simulation log is hashed via SHA-256.
- Tampering or manual modification outside the Studio is detected and invalidates the validation record.
