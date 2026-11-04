# Collaboration Rules

## Purpose
Build a reliable Nifty 50 intraday stock-selection and analysis dashboard. The repository is the shared source of truth for requirements, decisions, code, tests and evidence.

## Roles
- **Owner (Munesh):** Product owner and final decision-maker. Approves scope, strategy changes, merges and releases.
- **ChatGPT:** Quantitative strategy architect, requirements analyst, independent reviewer, test-design and backtest auditor.
- **Claude:** Primary implementation agent for application code, integrations, tests and UI, unless the owner assigns a different task.

These are default responsibilities, not a restriction on either agent contributing ideas or code.

## No-Loop Protocol
1. Every task must have a written objective, scope, acceptance criteria and a named owner before implementation.
2. Each task gets at most **one proposal round, one review round and one revision round**.
3. A reviewer must identify concrete defects, reproducible examples, failed tests or evidence. Preference-only objections must be labelled as such.
4. After one revision, unresolved disagreements are recorded in `docs/DECISION_LOG.md` with options, trade-offs, evidence and a recommended default.
5. The owner decides unresolved product or strategy questions. Agents must not keep reopening a settled decision without new evidence.
6. No agent should claim work is complete without reporting files changed, tests run, results and known limitations.
7. If blocked, report the blocker and the minimum decision/input needed. Do not repeat the same failed approach.

## Change Control
- Work on a feature branch; do not work directly on `main`.
- One active implementation owner per task/branch.
- Do not concurrently edit the same files.
- Keep PRs small and focused. Use draft PRs for incomplete work.
- No force-push, destructive reset, deletion or merge to `main` without owner approval.
- Strategy changes require an update to the relevant specification, rationale and regression tests.
- Do not commit credentials, API keys, access tokens, personal data or broker secrets. Use environment variables and an ignored local env file.

## Definition of Done
A change is complete only when:
- Acceptance criteria are met.
- Relevant automated tests pass.
- Type/lint checks pass where configured.
- No look-ahead bias or use of incomplete candles is introduced into signal logic.
- Data timestamp, timezone, session and missing-data behaviour are explicit.
- The PR describes behaviour, validation evidence, risks and rollback considerations.
- Documentation is updated when behaviour or decisions change.

## Quantitative Research Discipline
- Treat scoring weights and thresholds as hypotheses until tested.
- Separate directional ranking from entry tradability.
- Avoid look-ahead bias, survivorship bias and data leakage.
- Include brokerage, taxes where applicable, slippage and realistic execution assumptions in backtests.
- Use chronological out-of-sample validation; do not tune on the final test period.
- Report sample size, dates, metrics, benchmark and limitations. Never present backtest results as guaranteed future performance.

## Communication Format
For each task, agents report:
1. Objective and assigned role
2. Files/areas changed or reviewed
3. Evidence and tests
4. Open issues (maximum three, prioritised)
5. Next action and who owns it

## Stop Condition
If a task has had one proposal, one review and one revision, stop. Summarise the remaining issue for the owner. Do not continue an agent-to-agent debate loop.
