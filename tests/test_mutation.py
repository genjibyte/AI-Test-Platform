"""Mutation core tests (docs/46 S3). Offline: PIT is NEVER invoked -- we only parse a
stubbed PIT XML report and build the command string. Mutation evidence is advisory and
never changes a verdict.
"""
import subprocess

from app.mutation import (
    PIT_VERSION,
    build_pit_command,
    build_pit_pom,
    is_junit5_pom,
    parse_line_spec,
    parse_pit_report,
    run_pit,
    scoped_mutation_score,
)

_REPORT = """<?xml version="1.0" encoding="UTF-8"?>
<mutations>
  <mutation detected='true' status='KILLED'><mutatedClass>com.x.Calc</mutatedClass></mutation>
  <mutation detected='true' status='KILLED'><mutatedClass>com.x.Calc</mutatedClass></mutation>
  <mutation detected='true' status='TIMED_OUT'><mutatedClass>com.x.Calc</mutatedClass></mutation>
  <mutation detected='false' status='SURVIVED'><mutatedClass>com.x.Calc</mutatedClass></mutation>
  <mutation detected='false' status='NO_COVERAGE'><mutatedClass>com.x.Calc</mutatedClass></mutation>
</mutations>
"""


def test_parse_pit_report_counts_and_score():
    r = parse_pit_report(_REPORT)
    assert r.available is True
    assert r.total == 5 and r.detected == 3
    assert r.killed == 2 and r.timed_out == 1 and r.survived == 1 and r.no_coverage == 1
    assert r.mutation_score == 0.6           # 3 detected / 5 total
    assert r.status_counts["KILLED"] == 2


def test_parse_pit_report_unavailable_on_empty_or_malformed():
    assert parse_pit_report(None).available is False
    assert parse_pit_report("").available is False
    assert parse_pit_report("<mutations></mutations>").available is False   # zero mutations
    assert parse_pit_report("<not valid xml").available is False            # malformed
    assert parse_pit_report(None).mutation_score is None


def test_build_pit_command_is_commandline_no_pom_edit():
    cmd = build_pit_command("com.x.Calc", "com.x.CalcTest")
    assert cmd[0] == "mvn"
    assert f"org.pitest:pitest-maven:{PIT_VERSION}:mutationCoverage" in cmd
    assert "-DtargetClasses=com.x.Calc" in cmd
    assert "-DtargetTests=com.x.CalcTest" in cmd
    assert "-DoutputFormats=XML" in cmd
    # configuration is via -D only -- the command never edits a pom
    assert not any("pom" in part.lower() for part in cmd)


# --- run_pit: gated execution layer, exercised offline with an injected runner ----

def test_run_pit_parses_report_via_injected_runner(tmp_path):
    def fake_runner(cmd, **kw):
        rpt = tmp_path / "target" / "pit-reports"
        rpt.mkdir(parents=True, exist_ok=True)
        (rpt / "mutations.xml").write_text(_REPORT, encoding="utf-8")

        class _P:
            returncode = 0

        return _P()

    res = run_pit(tmp_path, "com.x.Calc", "com.x.CalcTest", runner=fake_runner)
    assert res.available is True and res.mutation_score == 0.6


def test_run_pit_unavailable_when_no_report(tmp_path):
    def fake_runner(cmd, **kw):
        class _P:
            returncode = 1

        return _P()

    res = run_pit(tmp_path, "com.x.Calc", "com.x.CalcTest", runner=fake_runner)
    assert res.available is False and res.mutation_score is None


def test_run_pit_unavailable_on_timeout(tmp_path):
    def fake_runner(cmd, **kw):
        raise subprocess.TimeoutExpired(cmd, 1)

    assert run_pit(tmp_path, "com.x.Calc", "com.x.CalcTest", runner=fake_runner).available is False


def test_run_pit_writes_junit5_sidecar_and_uses_dash_f(tmp_path):
    # JUnit5 pom present -> run_pit writes a sidecar pom-pit.xml (with the junit5 plugin)
    # and runs it via `mvn -f`, WITHOUT editing the original pom (docs/46 §14).
    (tmp_path / "pom.xml").write_text(
        "<project><dependencies><dependency><artifactId>junit-jupiter</artifactId>"
        "</dependency></dependencies><build><plugins></plugins></build></project>",
        encoding="utf-8")
    seen = {}

    def fake_runner(cmd, **kw):
        seen["cmd"] = cmd
        rpt = tmp_path / "target" / "pit-reports"
        rpt.mkdir(parents=True, exist_ok=True)
        (rpt / "mutations.xml").write_text(_REPORT, encoding="utf-8")

        class _P:
            returncode = 0

        return _P()

    res = run_pit(tmp_path, "com.x.Calc", "com.x.CalcTest", runner=fake_runner)
    assert res.available is True and res.mutation_score == 0.6
    assert "-f" in seen["cmd"]                       # ran the sidecar via -f
    sidecar = tmp_path / "pom-pit.xml"
    assert sidecar.exists()                          # a separate file; original pom untouched
    assert "pitest-junit5-plugin" in sidecar.read_text(encoding="utf-8")


def test_run_pit_resolves_mvn_launcher(tmp_path, monkeypatch):
    # Windows fix (docs/46 §14): bare "mvn" is mvn.cmd; subprocess (no shell) can't launch it,
    # so run_pit resolves it via shutil.which before invoking -- the DEFAULT path must work.
    import app.mutation.run as runmod
    monkeypatch.setattr(runmod.shutil, "which", lambda name: r"C:\maven\bin\mvn.CMD")
    (tmp_path / "pom.xml").write_text(
        "<project><build><plugins></plugins></build></project>", encoding="utf-8")
    seen = {}

    def fake_runner(cmd, **kw):
        seen["cmd"] = cmd
        rpt = tmp_path / "target" / "pit-reports"
        rpt.mkdir(parents=True, exist_ok=True)
        (rpt / "mutations.xml").write_text(_REPORT, encoding="utf-8")

        class _P:
            returncode = 0

        return _P()

    run_pit(tmp_path, "com.x.Calc", "com.x.CalcTest", runner=fake_runner)  # default mvn="mvn"
    assert seen["cmd"][0] == r"C:\maven\bin\mvn.CMD"     # resolved launcher, not bare "mvn"


def test_run_pit_falls_back_when_mvn_unresolved(tmp_path, monkeypatch):
    # Maven not on PATH -> which returns None -> keep the original string so the launch fails
    # and degrades to available=False (the safe behaviour is preserved, never a fake pass).
    import app.mutation.run as runmod
    monkeypatch.setattr(runmod.shutil, "which", lambda name: None)
    (tmp_path / "pom.xml").write_text(
        "<project><build><plugins></plugins></build></project>", encoding="utf-8")
    seen = {}

    def fake_runner(cmd, **kw):
        seen["cmd"] = cmd

        class _P:
            returncode = 0

        return _P()

    run_pit(tmp_path, "com.x.Calc", "com.x.CalcTest", runner=fake_runner)
    assert seen["cmd"][0] == "mvn"                       # unchanged fallback


# --- gated benchmark wire-in (docs/46 S3 #1) -------------------------------------

def test_maybe_mutation_score_gated_off_then_enabled(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from app.benchmark import runner as R
    from app.mutation.pit import MutationResult

    job = SimpleNamespace(id="j1", generation={"execution": {"generated_class": "com.x.CalcTest"}})
    case = SimpleNamespace(target_class="com.x.Calc")

    def _boom(*a, **k):
        raise AssertionError("run_pit must not be called when mutation is disabled")

    # default OFF -> None, and run_pit is never reached
    monkeypatch.setattr(R, "get_settings", lambda: SimpleNamespace(mutation_enabled=False))
    monkeypatch.setattr(R, "run_pit", _boom)
    assert R._maybe_mutation_score(job, case) is None

    # enabled -> runs run_pit (stubbed) in the existing workspace repo_dir -> score
    monkeypatch.setattr(R, "get_settings", lambda: SimpleNamespace(mutation_enabled=True))
    monkeypatch.setattr(R, "Workspace", lambda job_id: SimpleNamespace(repo_dir=tmp_path))
    monkeypatch.setattr(R, "run_pit", lambda *a, **k: MutationResult(available=True, mutation_score=0.6))
    assert R._maybe_mutation_score(job, case) == 0.6


def test_mutation_score_carries_to_ledger():
    from app.benchmark.models import BenchCaseResult
    from app.ledger.ingest import record_from_bench_case
    from app.ledger.models import Provenance

    prov = Provenance(author_type="platform_generator", author_id="m")
    res = BenchCaseResult(name="c", repo_url="u", target_class="C",
                          conclusion="NEED_HUMAN_REVIEW", mutation_score=0.6)
    assert record_from_bench_case(res, prov).mutation_score == 0.6
    bare = BenchCaseResult(name="c", repo_url="u", target_class="C",
                           conclusion="NEED_HUMAN_REVIEW")
    assert record_from_bench_case(bare, prov).mutation_score is None


# --- JUnit5-aware sidecar pom (docs/46 section 14) -------------------------------

def test_is_junit5_pom_detection():
    assert is_junit5_pom("<artifactId>junit-jupiter</artifactId>")
    assert is_junit5_pom("<groupId>org.junit.jupiter</groupId>")
    assert not is_junit5_pom("<artifactId>junit</artifactId><version>4.13.2</version>")
    assert not is_junit5_pom(None)


def test_build_pit_pom_injects_into_existing_plugins_and_adds_junit5():
    pom = ("<project>\n  <build>\n    <plugins>\n      <plugin>existing</plugin>\n"
           "    </plugins>\n  </build>\n</project>\n")
    out = build_pit_pom(pom, target_classes="com.x.C", target_tests="com.x.CT", junit5=True)
    assert "pitest-maven" in out and "pitest-junit5-plugin" in out
    assert "<param>com.x.C</param>" in out and "<param>com.x.CT</param>" in out
    assert "<plugin>existing</plugin>" in out          # original preserved
    assert out.count("</plugins>") == 1                # not duplicated


def test_build_pit_pom_junit4_omits_junit5_plugin():
    pom = "<project><build><plugins></plugins></build></project>"
    out = build_pit_pom(pom, target_classes="com.x.C", target_tests="com.x.CT", junit5=False)
    assert "pitest-maven" in out and "pitest-junit5-plugin" not in out


def test_build_pit_pom_synthesizes_build_when_absent_and_autodetects_junit5():
    pom = ("<project>\n  <dependencies><dependency>"
           "<artifactId>junit-jupiter</artifactId></dependency></dependencies>\n</project>\n")
    out = build_pit_pom(pom, target_classes="com.x.C", target_tests="com.x.CT")  # autodetect
    assert "<build>" in out and "<plugins>" in out
    assert "pitest-maven" in out and "pitest-junit5-plugin" in out  # autodetected JUnit5


# --- docs/48 S3: per-mutation rows + line-scoped score ---------------------------

_REPORT_FULL = """<?xml version="1.0" encoding="UTF-8"?>
<mutations>
  <mutation detected='true' status='KILLED'><mutatedClass>com.x.Calc</mutatedClass><mutatedMethod>add</mutatedMethod><lineNumber>4</lineNumber><mutator>org.pitest.mutationtest.engine.gregor.mutators.MathMutator</mutator></mutation>
  <mutation detected='false' status='SURVIVED'><mutatedClass>com.x.Calc</mutatedClass><mutatedMethod>max</mutatedMethod><lineNumber>5</lineNumber><mutator>org.pitest.mutationtest.engine.gregor.mutators.ConditionalsBoundaryMutator</mutator></mutation>
</mutations>
"""


def test_parse_pit_report_include_mutations_rows():
    r = parse_pit_report(_REPORT_FULL, include_mutations=True)
    assert len(r.mutations) == 2 and r.total == 2
    row = r.mutations[0]
    assert row["line"] == 4 and row["method"] == "add" and row["status"] == "KILLED"
    assert row["mutator"] == "MathMutator" and row["detected"] is True   # short mutator name


def test_parse_pit_report_default_omits_mutations_backcompat():
    r = parse_pit_report(_REPORT_FULL)                  # default: no per-mutation rows
    assert r.mutations == [] and r.total == 2 and r.mutation_score == 0.5


def test_parse_line_spec_forms():
    assert parse_line_spec("125") == {125}
    assert parse_line_spec("130-132") == {130, 131, 132}
    assert parse_line_spec("120,125,130-131") == {120, 125, 130, 131}
    assert parse_line_spec(None) == set() and parse_line_spec("junk") == set()


def test_scoped_mutation_score_by_line_and_method():
    rows = parse_pit_report(_REPORT_FULL, include_mutations=True).mutations
    assert scoped_mutation_score(rows, lines={4}) == 1.0        # add KILLED
    assert scoped_mutation_score(rows, lines={5}) == 0.0        # max SURVIVED
    assert scoped_mutation_score(rows, method="max") == 0.0
    assert scoped_mutation_score(rows, lines={4, 5}) == 0.5     # 1 of 2 killed
    assert scoped_mutation_score(rows) is None                  # no scope -> cannot score
    assert scoped_mutation_score(rows, lines={999}) is None     # no match
    assert scoped_mutation_score([], lines={4}) is None         # no mutations


def test_run_pit_include_mutations_threads_rows(tmp_path):
    (tmp_path / "pom.xml").write_text(
        "<project><build><plugins></plugins></build></project>", encoding="utf-8")

    def fake_runner(cmd, **kw):
        rpt = tmp_path / "target" / "pit-reports"
        rpt.mkdir(parents=True, exist_ok=True)
        (rpt / "mutations.xml").write_text(_REPORT_FULL, encoding="utf-8")

        class _P:
            returncode = 0

        return _P()

    res = run_pit(tmp_path, "com.x.Calc", "com.x.CalcTest",
                  runner=fake_runner, include_mutations=True)
    assert res.available is True and len(res.mutations) == 2
    assert res.mutations[0]["method"] == "add"
    # default (no include_mutations) stays back-compat: rows omitted
    res2 = run_pit(tmp_path, "com.x.Calc", "com.x.CalcTest", runner=fake_runner)
    assert res2.available is True and res2.mutations == []

