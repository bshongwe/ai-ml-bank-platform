ADR-002 — Lakehouse (Bronze / Silver / Gold)

Decision: Immutable raw data + deterministic transforms

Reason:

- Replayability
- Audit readiness
- ML reproducibility

Consequence:

- No “quick fixes” in downstream layers (this is good)
