"""Mock / external-dependency smell detection (docs/51, #4 S1) -- ADVISORY, judge-side.

Static, regex-based mock-quality smells the quality gate does NOT cover (the gate already BLOCKS
Thread.sleep, randomness, time, and File/URL/Socket/HttpClient). This is a SEPARATE advisory
signal: it NEVER touches the quality gate, never feeds the recommendation/conclusion, and changes
no verdict (`conclusion` stays `NEED_HUMAN_REVIEW`). A smell is a review hint, not a rejection;
static heuristics mean false positives are possible by design.
"""
from __future__ import annotations

import re
from typing import List, Optional

_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_LINE_COMMENT = re.compile(r"//[^\n]*")
_STRING = re.compile(r'"(?:\\.|[^"\\])*"')

_THEN_RETURN_NULL = re.compile(r"thenReturn\s*\(\s*null\s*\)")
_MATCHERS = re.compile(
    r"\bany(?:Int|Long|Short|Byte|Char|Double|Float|Boolean|String|Object|List|Set|Map|"
    r"Collection|Iterable)?\s*\(\s*\)"
)
# Framework-level real dependencies the gate's IO/network regex does NOT catch.
_REAL_DEP = re.compile(
    r"\b(?:DriverManager|getConnection|RestTemplate|WebClient|JdbcTemplate|MongoClient|"
    r"KafkaTemplate|RedisTemplate)\b|@Autowired"
)


def _strip(source: str) -> str:
    """Light comment/string strip to cut false positives (not a full Java parser)."""
    s = _BLOCK_COMMENT.sub(" ", source or "")
    s = _LINE_COMMENT.sub(" ", s)
    return _STRING.sub('""', s)


def _simple(name: Optional[str]) -> Optional[str]:
    return name.rsplit(".", 1)[-1] if name else None


def _mock_of_target(code: str, target_simple: Optional[str]) -> Optional[str]:
    """Does the test mock/spy the class under test? (Testing the mock, not the code.)"""
    if not target_simple:
        return None
    t = re.escape(target_simple)
    if re.search(rf"\b(?:mock|spy)\s*\(\s*{t}\s*\.\s*class", code):
        return f"mock({target_simple}.class)"
    if re.search(rf"@(?:Mock|Spy)\b[^;{{}}]*\b{t}\b", code):
        return f"@Mock {target_simple}"
    return None


def detect_mock_smells(source: str, *, target_class: Optional[str] = None) -> dict:
    """Detect advisory mock / external-dependency smells (docs/51). Pure; never raises; changes no
    verdict. Empty/clean source -> zero smells."""
    code = _strip(source or "")
    smells: List[dict] = []

    mot = _mock_of_target(code, _simple(target_class))
    if mot:
        smells.append({
            "category": "mock_of_target", "evidence": mot,
            "hint": "the test mocks the class under test -- it tests the mock, not the code",
        })
    if _THEN_RETURN_NULL.search(code):
        smells.append({
            "category": "stub_returns_null", "evidence": "thenReturn(null)",
            "hint": "stubbing null can mask NPE / null-handling behaviour -- review",
        })
    m = _MATCHERS.search(code)
    if m:
        smells.append({
            "category": "loose_matchers", "evidence": m.group(0),
            "hint": "loose argument matchers may not pin the real call -- review",
        })
    rd = _REAL_DEP.search(code)
    if rd:
        smells.append({
            "category": "real_dependency", "evidence": rd.group(0),
            "hint": "uses a real framework dependency in a unit test -- mock it -- review",
        })

    counts = {"mock_of_target": 0, "stub_returns_null": 0,
              "loose_matchers": 0, "real_dependency": 0}
    for s in smells:
        counts[s["category"]] = counts.get(s["category"], 0) + 1
    return {
        "smells": smells,
        "counts": counts,
        "total": len(smells),
        "advisory": True,
        "note": "static heuristic; advisory only -- a smell is a review hint, not a verdict",
    }
