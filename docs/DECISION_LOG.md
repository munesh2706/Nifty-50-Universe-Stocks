# Decision Log

Record material product, architecture, data and trading-strategy decisions here.

## Status values
- Proposed
- Accepted
- Rejected
- Superseded

## Decision template

### DEC-000 — Short title
- **Status:** Proposed
- **Date:** YYYY-MM-DD
- **Owner:** Munesh
- **Context:**
- **Options considered:**
- **Evidence / tests:**
- **Decision:**
- **Consequences / trade-offs:**
- **Revisit only if:**

---

## Initial decisions

### DEC-001 — Nifty 50 as the initial universe
- **Status:** Accepted
- **Date:** 2026-11-04
- **Owner:** Munesh
- **Decision:** The initial scanner universe is restricted to the 50 Nifty 50 constituents. Constituent membership must be maintained as versioned reference data rather than assumed permanently fixed.
- **Consequences:** The system must support constituent updates and historical universe membership for unbiased backtests.

### DEC-002 — Separate directional ranking from tradability
- **Status:** Accepted as a design principle
- **Date:** 2026-11-04
- **Owner:** Munesh
- **Decision:** Bullish/bearish ranking and entry tradability are separate stages. A strong directional stock is not automatically an actionable trade. The system must support a NO TRADE outcome.
- **Consequences:** Selection and execution-readiness scores must be independently calculated, explained and tested.

### DEC-003 — Bounded agent collaboration
- **Status:** Accepted
- **Date:** 2026-11-04
- **Owner:** Munesh
- **Decision:** Use the No-Loop Protocol in `COLLABORATION_RULES.md`. After one proposal, one review and one revision, unresolved issues are escalated to the owner.
- **Consequences:** No unbounded AI debate or silent scope changes.
