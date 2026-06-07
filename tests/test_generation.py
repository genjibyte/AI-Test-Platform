"""Prompt builder + offline dry-run (P2-T03/T04). No real model, no writes."""
from pathlib import Path

from app.context.context_collector import build_snapshot
from app.generate.generation import dry_generate
from app.generate.prompt_builder import build_prompt
from app.llm.fake_client import FakeLLMClient

REPO = Path(__file__).resolve().parents[1] / "samples" / "calc"


def _context():
    return build_snapshot(REPO, "com.example.Calc", "max")


def test_prompt_is_deterministic():
    ctx = _context()
    assert build_prompt(ctx) == build_prompt(ctx)


def test_prompt_contains_bounded_context_and_contract():
    prompt = build_prompt(_context())
    assert "com.example.Calc" in prompt
    assert "max" in prompt
    assert "a > b" in prompt                      # target method source
    assert "CalcTest" in prompt                   # neighbor test style ref
    assert "junit-jupiter" in prompt              # maven dependency summary
    assert '"test_source"' in prompt              # output JSON contract advertised
    assert "JUnit5" in prompt


def test_prompt_does_not_dump_whole_repo():
    # Bounded context: the prompt is fixed rules + a small target context, never
    # the whole repo. The bound has headroom for the deterministic v3/v3.1 rule
    # text; a real repository dump would be an order of magnitude larger.
    assert len(build_prompt(_context())) < 6000


def test_dry_generate_offline_contract_loop():
    result = dry_generate(_context(), client=FakeLLMClient())
    assert result.target_class == "com.example.Calc"
    assert result.target_method == "max"
    assert result.file_name == "CalcAiGeneratedTest.java"
    assert result.test_source                      # placeholder, not executed
    assert result.trusted is False
    assert result.model == "fake-1"
