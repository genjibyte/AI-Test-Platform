"""Mock / external-dependency smell tests (docs/51, #4 S1). Offline; static; ADVISORY -- a smell
is a review hint and changes NO verdict; the quality gate is not touched.
"""
from app.quality.mock_smells import detect_mock_smells


def test_mock_of_target_via_mock_call():
    r = detect_mock_smells("Calc c = mock(Calc.class);", target_class="com.example.Calc")
    assert r["counts"]["mock_of_target"] == 1
    assert r["smells"][0]["category"] == "mock_of_target"


def test_mock_of_target_via_annotation():
    r = detect_mock_smells("@Mock private Calc calc;", target_class="com.example.Calc")
    assert r["counts"]["mock_of_target"] == 1


def test_mocking_a_collaborator_is_fine():
    r = detect_mock_smells("Repo r = mock(Repo.class);", target_class="com.example.Calc")
    assert r["counts"]["mock_of_target"] == 0


def test_stub_returns_null():
    assert detect_mock_smells("when(r.get()).thenReturn(null);")["counts"]["stub_returns_null"] == 1


def test_loose_matchers():
    assert detect_mock_smells("when(r.get(anyString())).thenReturn(x);")["counts"]["loose_matchers"] == 1
    assert detect_mock_smells("verify(r).save(any());")["counts"]["loose_matchers"] == 1


def test_real_dependency_the_gate_misses():
    assert detect_mock_smells("RestTemplate t = new RestTemplate();")["counts"]["real_dependency"] == 1
    assert detect_mock_smells("@Autowired Service s;")["counts"]["real_dependency"] == 1
    assert detect_mock_smells("c = DriverManager.getConnection(u);")["counts"]["real_dependency"] == 1


def test_clean_mockito_test_has_no_smells():
    src = ("Repo r = mock(Repo.class); when(r.get(5)).thenReturn(9); "
           "assertEquals(9, new Calc(r).run(5));")
    r = detect_mock_smells(src, target_class="com.example.Calc")
    assert r["total"] == 0 and r["smells"] == []


def test_comments_and_strings_are_stripped():
    assert detect_mock_smells("// thenReturn(null)")["total"] == 0
    assert detect_mock_smells('String s = "thenReturn(null)";')["total"] == 0


def test_advisory_shape_and_empty():
    r = detect_mock_smells("", target_class="com.example.Calc")
    assert r["advisory"] is True and r["total"] == 0 and "note" in r


def test_generation_report_surfaces_smells_without_changing_verdict():
    from app.report.generation_report import CONCLUSION, assemble_generation_report

    src = ("package com.example; class T { void t(){ Calc c = mock(Calc.class); "
           "when(x).thenReturn(null); } }")
    bundle = {
        "target": {"target_class": "com.example.Calc", "target_method": "max"},
        "result": {"test_source": src, "model": "fake-1", "trusted": False},
        "write": {"created": True, "production_code_touched": False, "content": src},
        "execution": {"gen_outcome": "PASS", "build_outcome": "SUCCESS",
                      "gen_total": 1, "gen_passed": 1, "gen_failed": 0,
                      "gen_errors": 0, "gen_skipped": 0},
        "error": None,
    }
    r = assemble_generation_report(bundle)
    ms = r["review_summary"]["mock_smells"]
    assert ms["counts"]["mock_of_target"] == 1 and ms["counts"]["stub_returns_null"] == 1
    assert ms["advisory"] is True
    assert r["conclusion"] == CONCLUSION                 # verdict NEVER changes
