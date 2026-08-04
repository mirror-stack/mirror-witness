# Changelog

All notable changes to Mirror Witness Hub are documented here.  
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

> **Why there is no `pyproject.toml`.** The other three Mirror Stack repos are
> installable libraries; this one is not. It is a public repo used as a shared
> witness board — two scripts (`declare.py`, `witness_verify.py`) plus the CI
> that runs them. Adding packaging metadata would make it *look* installable
> and imply an import surface that does not exist. The version lives in
> [`VERSION`](VERSION) and in each script's `__version__`, which is what a git
> tag needs and nothing more.

---

## [0.1.0] — 2026-08-05

First declared version. The hub has been in use before this point; this entry
records what it already is, so the repo can carry a tag whose meaning is
stated rather than assumed.

### Present
- **Append-only witness board.** Operators append a declaration of their
  ledger's current head to `ledger_heads/<operator>.jsonl` — the head, not the
  ledger. What a declaration proves: *"operator O declared, at commit time T,
  that ledger L's head was HEAD with N entries."*
- **`witness_verify.py`** — the consistency check GitHub alone cannot give.
  Runs in CI on every PR: verifies declarations are append-only and that no
  operator rewinds a previously witnessed head.
- **`declare.py`** — writes a declaration for the calling operator.
- **Sealed-Record Reading Room** (`docs/ledger/`) — a human-readable viewer over
  real sealed ledgers, showing kill-conditions sealed *before* each run and the
  verdict after, including the failures and retractions. Tampering with a value
  in the browser breaks the displayed hash.
- Apache-2.0 (added 2026-07-23, PR #1).

### Honest limitation
The board makes a rewind **detectable by others**; it does not make one
impossible, and it cannot make operators independent. Independence is a social
property — a single person can register many operators (Sybil). The stack's
`stack/PILLARS.md` says this in full: the honest path is visibility, not
prevention.
