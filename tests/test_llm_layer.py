"""LLM isolation layer: client, factory, JSON contract (P2-T03). Offline only."""
import pytest

from app.config import Settings
from app.llm.client import LLMResponse, get_client
from app.llm.fake_client import FakeLLMClient
from app.llm.schema import (
    LLMOutputError,
    LLMTestPayload,
    TestGenerationResult,
    assemble_result,
    parse_payload,
)
from app.models.context_snapshot import ContextSnapshot
from app.models.java_source import JavaClassStructure


def _ctx() -> ContextSnapshot:
    return ContextSnapshot(
        target_class="com.example.Calc",
        target_method="max",
        target_method_source="public int max(int a, int b){return a>b?a:b;}",
        class_structure=JavaClassStructure(class_name="Calc", package="com.example"),
    )


def test_fake_client_offline_valid_payload():
    resp = FakeLLMClient().generate("ignored prompt")
    assert isinstance(resp, LLMResponse)
    assert resp.provider == "fake"
    payload = parse_payload(resp.text)
    assert isinstance(payload, LLMTestPayload)
    assert payload.test_source
    assert "org.junit.jupiter.api.Test" in payload.imports


def test_factory_defaults_to_fake():
    client = get_client(Settings())
    assert isinstance(client, FakeLLMClient)


def test_factory_real_provider_raises():
    with pytest.raises(NotImplementedError):
        get_client(Settings(llm_provider="openai"))


def test_parse_plain_and_fenced_json():
    plain = '{"test_source": "x"}'
    fenced = '```json\n{"test_source": "y", "imports": ["a.B"]}\n```'
    assert parse_payload(plain).test_source == "x"
    p = parse_payload(fenced)
    assert p.test_source == "y" and p.imports == ["a.B"]


def test_parse_invalid_json_raises():
    with pytest.raises(LLMOutputError):
        parse_payload("not json at all")


def test_parse_missing_required_field_raises():
    with pytest.raises(LLMOutputError):
        parse_payload('{"imports": ["a.B"]}')  # no test_source


def test_assemble_result_deterministic_identity():
    payload = parse_payload(FakeLLMClient().generate("x").text)
    result = assemble_result(_ctx(), payload, model="fake-1")
    assert isinstance(result, TestGenerationResult)
    assert result.target_class == "com.example.Calc"
    assert result.target_method == "max"
    assert result.package == "com.example"
    assert result.test_class_name == "CalcAiGeneratedTest"
    assert result.file_name == "CalcAiGeneratedTest.java"
    assert result.trusted is False           # never trusted (docs/07 P2)
    assert result.model == "fake-1"
