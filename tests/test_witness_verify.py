"""Tests for witness_verify.py (C1–C4) and declare.py.

The README says the board catches a rewound entry_count, a deleted middle
declaration, and edits to committed lines. These tests are where that is shown.
Each test builds its own board in a temp dir; the real ledger_heads/ is not touched.
"""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


wv = _load("witness_verify")


@pytest.fixture
def board(tmp_path, monkeypatch):
    heads = tmp_path / "ledger_heads"
    heads.mkdir()
    monkeypatch.setattr(wv, "HERE", tmp_path)
    monkeypatch.setattr(wv, "HEADS", heads)
    return heads


def declare(heads, operator, ledger, entries, *, head="ab" * 8):
    """Append one correctly sealed declaration by running the real declare.py."""
    script = heads.parent / "declare.py"
    if not script.exists():
        script.write_text((ROOT / "declare.py").read_text())
    subprocess.run([sys.executable, str(script), "--operator", operator, "--ledger", ledger,
                    "--head", head, "--entries", str(entries), "--ts", f"2026-01-0{entries}T00:00:00Z"],
                   check=True, capture_output=True)


def verify(heads):
    fails = []
    for path in sorted(heads.glob("*.jsonl")):
        wv.verify_file(path, fails)
    return fails


def lines(path):
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def write(path, recs):
    path.write_text("".join(json.dumps(r) + "\n" for r in recs))


def test_real_board_verifies():
    r = subprocess.run([sys.executable, str(ROOT / "witness_verify.py")],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout
    assert "ALL OK" in r.stdout


def test_declare_then_verify_is_clean(board):
    for n in (2, 3, 5):
        declare(board, "op", "L", n)
    recs = lines(board / "op.jsonl")
    assert [r["entry_count"] for r in recs] == [2, 3, 5]
    assert recs[0]["prev_decl_seal"] == "genesis"
    assert recs[1]["prev_decl_seal"] == recs[0]["decl_seal"]
    assert len(recs[0]["decl_seal"]) == 64
    assert verify(board) == []


def test_c1_missing_field(board):
    declare(board, "op", "L", 2)
    recs = lines(board / "op.jsonl")
    del recs[0]["head_seal"]
    write(board / "op.jsonl", recs)
    fails = verify(board)
    assert len(fails) == 1 and "[C1 schema]" in fails[0]


def test_c2_c3_rewinding_a_past_count(board):
    """README: rewinding a past entry_count trips C2 + C3."""
    for n in (2, 3, 4):
        declare(board, "op", "L", n)
    recs = lines(board / "op.jsonl")
    recs[2]["entry_count"] = 1
    write(board / "op.jsonl", recs)
    fails = verify(board)
    assert any("[C2 decl-chain]" in f and "decl_seal mismatch" in f for f in fails)
    assert any("[C3 monotonic]" in f for f in fails)


def test_c3_alone_when_resealed(board):
    """A declarer who reseals honestly but lowers the count still trips C3."""
    declare(board, "op", "L", 5)
    declare(board, "op", "L", 3)
    fails = verify(board)
    assert len(fails) == 1 and "[C3 monotonic]" in fails[0]


def test_c2_deleting_a_middle_declaration(board):
    """README: deleting a middle declaration trips C2."""
    for n in (2, 3, 4):
        declare(board, "op", "L", n)
    recs = lines(board / "op.jsonl")
    write(board / "op.jsonl", [recs[0], recs[2]])
    fails = verify(board)
    assert any("[C2 decl-chain]" in f and "prev_decl_seal" in f for f in fails)


def test_legacy_16hex_seal_accepted_but_not_other_prefixes(board):
    declare(board, "op", "L", 2)
    recs = lines(board / "op.jsonl")
    full = recs[0]["decl_seal"]
    assert wv.decl_seal_matches(full[:16], full)
    assert not wv.decl_seal_matches(full[:15], full)
    assert not wv.decl_seal_matches(full[:20], full)


# ---- C4 needs a git history --------------------------------------------------

def git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True,
                   env={"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
                        "GIT_COMMITTER_EMAIL": "t@t", "HOME": str(cwd), "PATH": "/usr/bin:/bin"})


@pytest.fixture
def committed_board(board):
    declare(board, "op", "L", 2)
    declare(board, "op", "L", 3)
    declare(board, "other", "M", 1)
    root = board.parent
    git(root, "init", "-q")
    git(root, "add", "ledger_heads")
    git(root, "commit", "-q", "-m", "base")
    return board


def c4(board):
    fails = []
    wv.append_only_vs_base("HEAD", fails)
    return fails


def test_c4_append_is_allowed(committed_board):
    declare(committed_board, "op", "L", 4)
    declare(committed_board, "newcomer", "N", 1)
    assert c4(committed_board) == []


def test_c4_editing_a_committed_line(committed_board):
    p = committed_board / "op.jsonl"
    p.write_text(p.read_text().replace('"entry_count": 2', '"entry_count": 9', 1))
    fails = c4(committed_board)
    assert len(fails) == 1 and "[C4 append-only] ledger_heads/op.jsonl" in fails[0]


def test_c4_truncating_a_file(committed_board):
    p = committed_board / "op.jsonl"
    p.write_text(p.read_text().splitlines(keepends=True)[0])
    assert any("[C4 append-only]" in f for f in c4(committed_board))


def test_c4_deleting_a_whole_operator_file(committed_board):
    """Was a gap: the loop only walked files that still exist, so this passed."""
    (committed_board / "other.jsonl").unlink()
    fails = c4(committed_board)
    assert len(fails) == 1 and "file deleted" in fails[0]
