import json
import logging

import httpx
from langchain.agents import create_agent
from langchain_groq import ChatGroq
from pydantic import ValidationError

from app.agent.prompts import INVESTIGATOR_PROMPT, REPORT_PROMPT
from app.agent.schemas import IncidentReport, fallback_report
from app.agent.tools import build_tools
from app.core.config import settings

logger = logging.getLogger(__name__)

MAX_BRIEF_ISSUES = 15


def build_llm() -> ChatGroq:
    return ChatGroq(
        model=settings.llm_model,
        api_key=settings.groq_api_key,
        temperature=0,
        max_tokens=settings.llm_max_tokens,
        timeout=settings.llm_timeout_seconds,
        max_retries=2,
    )


def build_brief(name: str, url: str, status: str, issues: list[str]) -> str:
    lines = [f"- {issue}" for issue in issues[:MAX_BRIEF_ISSUES]]
    if len(issues) > MAX_BRIEF_ISSUES:
        lines.append(f"- ... and {len(issues) - MAX_BRIEF_ISSUES} more")
    return "\n".join(
        [
            f"Website name: {name}",
            f"Address: {url}",
            f"Status: {status}",
            "Problems found by the monitor:",
            *lines,
            "",
            "Investigate with your tools and explain the most likely cause.",
        ]
    )


def _as_text(content) -> str:
    """Model replies are usually a string, but can be a list of content blocks."""
    if isinstance(content, str):
        return content
    parts = []
    for block in content or []:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
    return "\n".join(parts)


def extract_json(text: str) -> dict | None:
    """Find the JSON object in a reply, even with extra words or ``` fences around it."""
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        data = json.loads(text[start : end + 1])
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def run_investigation(llm, tools: list, brief: str) -> str:
    """Phase 1: the agent calls tools and returns its findings as plain text."""
    agent = create_agent(model=llm, tools=tools, system_prompt=INVESTIGATOR_PROMPT)
    result = agent.invoke(
        {"messages": [{"role": "user", "content": brief}]},
        config={"recursion_limit": settings.agent_max_steps},
    )
    return _as_text(result["messages"][-1].content)


def format_report(llm, brief: str, findings: str) -> IncidentReport | None:
    """Phase 2: turn the findings into a validated report. One retry, then give up."""
    messages = [
        ("system", REPORT_PROMPT),
        ("user", f"Monitor brief:\n{brief}\n\nInvestigator findings:\n{findings}"),
    ]
    for _ in range(2):
        text = _as_text(llm.invoke(messages).content)
        data = extract_json(text)
        if data is not None:
            try:
                return IncidentReport.model_validate({**data, "ai_generated": True})
            except ValidationError as e:
                logger.warning("Agent report failed validation: %s", e)
        messages = [
            *messages,
            ("assistant", text),
            (
                "user",
                "That was not a valid JSON object with all the required keys. "
                "Return ONLY the JSON object.",
            ),
        ]
    return None


def investigate(
    name: str,
    url: str,
    status: str,
    issues: list[str],
    llm=None,
    transport: httpx.BaseTransport | None = None,
) -> IncidentReport:
    """Investigate a problem. Never raises: any failure gives the plain fallback report."""
    if llm is None and not settings.groq_api_key:
        logger.warning("GROQ_API_KEY is not set: using the plain report")
        return fallback_report(status, issues)

    try:
        llm = llm or build_llm()
        brief = build_brief(name, url, status, issues)
        findings = run_investigation(llm, build_tools(url, transport), brief)
        report = format_report(llm, brief, findings)
    except Exception:
        logger.exception("Agent investigation failed: using the plain report")
        return fallback_report(status, issues)

    if report is None:
        logger.warning("Agent did not return a usable report: using the plain report")
        return fallback_report(status, issues)
    return report