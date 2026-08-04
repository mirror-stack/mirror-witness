#!/usr/bin/env python3
"""👁 Witness Hub verifier — runs in CI on every PR.

The hub is a public GitHub repo used as a shared witness board. Operators append *declarations*
of their ledger heads (not the ledgers themselves) to ledger_heads/<operator>.jsonl. GitHub
gives timestamping + immutable history for free; this script gives the consistency check that
GitHub alone cannot.

What a declaration proves: "operator O declared, at commit time T, that ledger L's head was
HEAD with N entries." Because the file is append-only (enforced here + by git history), O cannot
later rewind its own clock — a thing no one can do alone (you can always rewind your own
machine; you cannot rewind what someone else already witnessed).

Checks:
  C1 schema      : each declaration has required fields, valid types
  C2 decl-chain  : declarations within a file chain (prev_decl_seal → decl_seal), so the board
                   itself is tamper-evident, not just the ledgers it points to
  C3 monotonic   : per (operator, ledger), entry_count never decreases across declarations
  C4 append-only : (CI-only, via --base) no previously-committed declaration line was changed
                   or deleted in this PR — only appends allowed

Honesty: this proves *time-order of declarations*, not that a hidden ledger is internally valid.
That requires the operator to also publish the ledger, or a peer to cross-check it. The hub's
value is the witness *network*, which is empty until independent operators join.
"""

__version__ = "0.1.0"   # see VERSION / CHANGELOG.md
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
HEADS = HERE / "ledger_heads"
REQUIRED = {"operator", "ts", "ledger", "entry_count", "head_seal", "prev_decl_seal", "decl_seal"}
OK, FAIL = "✅", "❌"


_LEGACY_SEAL_LEN = 16   # pre-v0.2 truncated decl seals — see decl_seal_matches


def decl_seal(rec):
    """Seal of a declaration = full SHA-256 over its content + prev_decl_seal.

    v0.2 widened from 16-hex (64-bit) truncation: a dishonest declarer could
    birthday-search (~2^32) two declarations sharing one seal and swap them.
    Legacy 16-hex decl seals stay verifiable via decl_seal_matches (prefix)."""
    body = {k: rec[k] for k in sorted(rec) if k != "decl_seal"}
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()


def decl_seal_matches(stored, full_hex):
    """Full match, or legacy exactly-16-hex prefix match (v0.1 boards)."""
    stored = str(stored)
    if stored == full_hex:
        return True
    return len(stored) == _LEGACY_SEAL_LEN and stored == full_hex[:_LEGACY_SEAL_LEN]


def load(path):
    return [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]


def verify_file(path, fails):
    name = path.name
    recs = load(path)
    prev = "genesis"
    last_count = {}
    for i, r in enumerate(recs):
        miss = REQUIRED - r.keys()
        if miss:
            fails.append(f"{FAIL} [C1 schema] {name}#{i}: missing {miss}")
            continue
        if str(r["prev_decl_seal"]) != prev:                                    # C2
            fails.append(f"{FAIL} [C2 decl-chain] {name}#{i}: prev_decl_seal "
                         f"{r['prev_decl_seal']} != {prev}")
        if not decl_seal_matches(r["decl_seal"], decl_seal(r)):                 # C2
            fails.append(f"{FAIL} [C2 decl-chain] {name}#{i}: decl_seal mismatch "
                         f"(recomputed {decl_seal(r)})")
        key = (r["operator"], r["ledger"])
        if key in last_count and r["entry_count"] < last_count[key]:            # C3
            fails.append(f"{FAIL} [C3 monotonic] {name}#{i}: {r['ledger']} entry_count "
                         f"{r['entry_count']} < previous {last_count[key]}")
        last_count[key] = r["entry_count"]
        prev = r["decl_seal"]
    return len(recs)


def append_only_vs_base(base, fails):
    """C4: every committed line of each heads file must survive unchanged in this revision."""
    for path in sorted(HEADS.glob("*.jsonl")):
        rel = path.relative_to(HERE)
        old = subprocess.run(["git", "show", f"{base}:{rel}"],
                             capture_output=True, text=True, cwd=HERE)
        if old.returncode != 0:
            continue  # new file in this PR — fine
        old_lines = [l for l in old.stdout.splitlines() if l.strip()]
        new_lines = [l for l in path.read_text().splitlines() if l.strip()]
        if new_lines[:len(old_lines)] != old_lines:
            fails.append(f"{FAIL} [C4 append-only] {rel}: existing declarations were "
                         "modified or deleted (only appends allowed)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=None, help="git ref to diff against for C4 (e.g. origin/main)")
    args = ap.parse_args()
    fails, total = [], 0
    files = sorted(HEADS.glob("*.jsonl"))
    print(f"=== Witness Hub verify — {len(files)} operator file(s) ===")
    for path in files:
        n = verify_file(path, fails)
        total += n
        print(f"  {path.name}: {n} declarations")
    if args.base:
        append_only_vs_base(args.base, fails)
    for f in fails:
        print(f)
    verdict = "ALL OK" if not fails else f"{len(fails)} FAILURE(S)"
    print(f"=== {OK if not fails else FAIL} {verdict} — {total} declarations across "
          f"{len(files)} operators ===")
    sys.exit(0 if not fails else 1)


if __name__ == "__main__":
    main()
