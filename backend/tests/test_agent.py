import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from app.agent import agent as agent_module
from app.agent.schemas import IncidentReport, fallback_report
from app.core.config import settings

GOOD_JSON = """{
  "summary": "The website cannot be reached.",
  "probable_cause": "The domain name does not resolve (DNS failure).",
  "severity": "critical",
  "affected": ["every page"],
  "suggestions": ["Check the domain registration", "Check the DNS records"],
  "confidence": "high"
}"""


def fake_llm(*replies):
    return GenericFakeChatModel(messages=iter([AIMessage(content=r) for r in replies]))


def test_extract_json_plain_and_wrapped():
    assert agent_module.extract_json('{"a": 1}') == {"a": 1}
    assert agent_module.extract_json('Here you go:\n```json\n{"a": 1}\n```') == {"a": 1}


def test_extract_json_rejects_garbage():
    assert agent_module.extract_json("no json here") is None
    assert agent_module.extract_json("{broken") is None
    assert agent_module.extract_json("[1, 2]") is None


def test_format_report_valid_json():
    report = agent_module.format_report(fake_llm(GOOD_JSON), "brief", "findings")
    assert report.severity == "critical"
    assert report.ai_generated is True
    assert "DNS" in report.probable_cause


def test_format_report_retries_once():
    report = agent_module.format_report(
        fake_llm("sorry, here is text", GOOD_JSON), "brief", "findings"
    )
    assert report is not None and report.confidence == "high"


def test_format_report_gives_up_after_two_bad_answers():
    assert agent_module.format_report(fake_llm("nope", "still nope"), "b", "f") is None


def test_report_cleans_long_text_and_lists():
    report = IncidentReport(
        summary="x" * 2000,
        probable_cause="  spaced   out  ",
        severity="low",
        suggestions=["a"] * 30 + ["", "  "],
    )
    assert len(report.summary) == 600
    assert report.probable_cause == "spaced out"
    assert len(report.suggestions) == 10


def test_report_rejects_unknown_severity():
    with pytest.raises(ValueError):
        IncidentReport(summary="s", probable_cause="c", severity="apocalyptic")


def test_fallback_report():
    down = fallback_report("down", ["a failed", "b failed"])
    assert down.severity == "critical" and down.ai_generated is False
    assert "1 more" in down.summary
    assert fallback_report("degraded", ["a failed"]).severity == "medium"


def test_investigate_without_key_returns_fallback(monkeypatch):
    monkeypatch.setattr(settings, "groq_api_key", "")
    report = agent_module.investigate("Shop", "https://shop.test", "down", ["boom"])
    assert report.ai_generated is False


def test_investigate_happy_path(monkeypatch):
    monkeypatch.setattr(agent_module, "run_investigation", lambda llm, tools, brief: "findings")
    report = agent_module.investigate(
        "Shop", "https://shop.test", "down", ["boom"], llm=fake_llm(GOOD_JSON)
    )
    assert report.ai_generated is True


def test_investigate_survives_a_crash(monkeypatch):
    def crash(llm, tools, brief):
        raise RuntimeError("network died")

    monkeypatch.setattr(agent_module, "run_investigation", crash)
    report = agent_module.investigate(
        "Shop", "https://shop.test", "down", ["boom"], llm=fake_llm(GOOD_JSON)
    )
    assert report.ai_generated is False


def test_brief_lists_the_problems():
    brief = agent_module.build_brief("Shop", "https://shop.test", "down", ["a", "b"])
    assert "Shop" in brief and "- a" in brief and "- b" in brief