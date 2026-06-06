"""Frozen-manifest + commit-pin tests (Phase 2.6, docs/23).

Two concerns, both offline:
  1. benchmarks/manifest.v1.json is well-formed and stays frozen — every case
     pinned to an exact SHA, the 3 baseline cases pinned to the EXACT commits
     used by var/benchmark/v2-pro-quality-final (so that comparison needs no
     re-run).
  2. _ensure_mirror(commit=...) reproduces an exact revision: a downstream clone
     of the pinned mirror checks out that SHA, not the branch tip.
"""
import json
import subprocess
from pathlib import Path

from app.benchmark.models import load_spec
from app.benchmark.runner import _ensure_mirror

MANIFEST = Path(__file__).resolve().parent.parent / "benchmarks" / "manifest.v1.json"

# The exact commits var/benchmark/v2-pro-quality-final ran on. Pinning here keeps
# that pro baseline a valid v2-vs-v3 comparison point with zero model re-run.
FROZEN = {
    "org.apache.commons.cli.Option": "ae44dcdffd28d6a1a32dc4e0801b715adcef162e",
    "org.apache.commons.csv.CSVRecord": "8192d9d196a554d67d7d65b0a131001b9d1eb412",
    "org.apache.commons.text.WordUtils": "e910b53a90308dbd70d54b4f69843805b53fc0fa",
}


def _load_manifest_cases():
    return load_spec(json.loads(MANIFEST.read_text(encoding="utf-8")))


def test_manifest_loads_and_is_in_size_range():
    cases = _load_manifest_cases()
    assert 8 <= len(cases) <= 12  # user spec: freeze 3, expand to 8-12


def test_manifest_every_case_is_sha_pinned():
    # "Frozen" means reproducible: every case carries a full 40-hex commit pin.
    for c in _load_manifest_cases():
        assert c.commit is not None, f"{c.label()} is not pinned"
        assert len(c.commit) == 40 and all(ch in "0123456789abcdef" for ch in c.commit)
        assert c.target_class.startswith("org.apache.commons."), c.target_class


def test_manifest_freezes_the_three_baseline_cases_to_exact_commits():
    by_target = {c.target_class: c for c in _load_manifest_cases()}
    for target, sha in FROZEN.items():
        assert target in by_target, f"missing frozen baseline case {target}"
        assert by_target[target].commit == sha  # exact v2-pro-quality-final commit


def test_manifest_has_four_distinct_repo_revisions():
    # cli / csv / text / lang — one mirror build per (repo, commit) pair.
    cases = _load_manifest_cases()
    pairs = {(c.repo_url, c.commit) for c in cases}
    assert len(pairs) == 4


# --- commit-pin mechanism (offline, against a local two-commit repo) ----------

def _git(*args, cwd):
    subprocess.run(["git", *args], cwd=cwd, check=True,
                   capture_output=True, text=True, timeout=60)


def _make_source_repo(root: Path) -> tuple[str, str, str]:
    """Build a local repo with two commits; return (file_uri, old_sha, tip_sha)."""
    src = root / "src"
    src.mkdir()
    _git("init", "-q", ".", cwd=src)
    _git("config", "user.email", "t@t", cwd=src)
    _git("config", "user.name", "t", cwd=src)
    # mirror GitHub's behaviour so fetch-by-SHA is permitted on a local repo.
    _git("config", "uploadpack.allowAnySHA1InWant", "true", cwd=src)
    (src / "f.txt").write_text("a\n", encoding="utf-8")
    _git("add", ".", cwd=src)
    _git("commit", "-qm", "c1", cwd=src)
    old = subprocess.run(["git", "rev-parse", "HEAD"], cwd=src, capture_output=True,
                         text=True, check=True).stdout.strip()
    (src / "f.txt").write_text("a\nb\n", encoding="utf-8")
    _git("add", ".", cwd=src)
    _git("commit", "-qm", "c2", cwd=src)
    tip = subprocess.run(["git", "rev-parse", "HEAD"], cwd=src, capture_output=True,
                         text=True, check=True).stdout.strip()
    return src.as_uri(), old, tip


def test_ensure_mirror_pins_exact_commit(tmp_path):
    src_uri, old, tip = _make_source_repo(tmp_path)
    assert old != tip

    mirror_uri = _ensure_mirror(src_uri, None, tmp_path / "mirrors", commit=old)

    mirror_dir = Path(mirror_uri.replace("file://", "").lstrip("/"))
    if not mirror_dir.exists():  # Windows file URI -> drive path
        mirror_dir = Path(mirror_uri[len("file:///"):])
    pinned = subprocess.run(["git", "-C", str(mirror_dir), "rev-parse", "pinned"],
                            capture_output=True, text=True, check=True).stdout.strip()
    assert pinned == old  # mirror is at the OLD commit, not the tip

    # the importer clones the mirror's default branch -> must yield the pin
    clone = tmp_path / "clone"
    _git("clone", "-q", "--depth", "1", mirror_uri, str(clone), cwd=tmp_path)
    head = subprocess.run(["git", "-C", str(clone), "rev-parse", "HEAD"],
                          capture_output=True, text=True, check=True).stdout.strip()
    assert head == old


def test_ensure_mirror_distinct_commits_distinct_mirrors(tmp_path):
    src_uri, old, tip = _make_source_repo(tmp_path)
    a = _ensure_mirror(src_uri, None, tmp_path / "m", commit=old)
    b = _ensure_mirror(src_uri, None, tmp_path / "m", commit=tip)
    assert a != b  # commit is part of the cache key
