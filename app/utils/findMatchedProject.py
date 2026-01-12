import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup  # pyright: ignore[reportMissingModuleSource]
import logging

from app.services import CodeurProjectCrawler
from app.services.logging import setup_logging
from app.services.globalVars import profile
from app.services import call_llama as call_llama_service
from app.utils.someCommonFunctions import extract_projectUrl_from_emailcontent

logger = logging.getLogger(__name__)

_MIN_AI_SCORE = float(os.getenv("MATCH_MIN_SCORE", "0.65"))
_RAW_KEYWORDS = os.getenv("MATCH_RULE_KEYWORDS", "")
_RULE_KEYWORDS: List[str] = [word.strip().lower() for word in _RAW_KEYWORDS.split(",") if word.strip()]


@dataclass
class MatchDecision:
    matched: bool
    score: Optional[float] = None
    reasons: Optional[List[str]] = None


def is_matched_project(emailcontent: str) -> bool:
    text_content = extract_text_from_html(emailcontent)
    if not text_content:
        logger.debug("Email content is empty, return False")
        return False

    if not keyword_filter(text_content):
        logger.debug("Keyword filter failed, return False")
        return False

    # first step filter: email content filter
    decision = ai_match_decision(text_content)
    if decision.matched is None or not decision.matched:
        logger.debug(f"AI match decision matched is None or False, return False")
        return decision.matched

    # second step filter: project details filter
    project_url = extract_projectUrl_from_emailcontent(emailcontent)
    if project_url is None:
        logger.debug("Project URL not found, return False")
        return False
    crawler = CodeurProjectCrawler(project_url)
    project_details = crawler.crawl_project_details()  # crawl project details from the codeur website
    decision = ai_match_decision(project_details)   # parse AI decision from the project details
    if decision.score is None:
        logger.debug(f"AI match decision score is None")
        return decision.matched

    return decision.matched and decision.score >= _MIN_AI_SCORE


def keyword_filter(emailcontent: str) -> bool:
    lowered = emailcontent.lower()

    if _RULE_KEYWORDS:
        keyword_hit = any(keyword in lowered for keyword in _RULE_KEYWORDS)
        if not keyword_hit:
            logger.debug(f"Keyword not hit: {_RULE_KEYWORDS}")
            return False

    return True


def ai_match_decision(emailcontent: str) -> MatchDecision:
    prompt = build_prompt(profile, emailcontent)
    system_prompt = "You are a helper responsible for analyzing the match between candidates and projects, and can only output JSON format conclusions."

    try:
        ai_response = call_llama_service(prompt, system_prompt)
    except Exception as exc:
        logger.error(f"AI call failed, fallback to rule result: {exc}", exc_info=True)
        return MatchDecision(matched=False)  # Conservative strategy: rule layer already passed

    return parse_ai_decision(ai_response)


def build_prompt(person_profile: str, project_description: str) -> str:
    """Build prompt, combine candidate profile and project description into context."""
    exemplar = {
        "match": True,
        "score": 0.8,
        "reasons": ["Candidate has many years of AI experience", "Project needs LLM Agent practice"],
    }
    prompt_blocks = [
        "Please evaluate if the candidate matches the project, output JSON.",
        "Response field description:",
        '- match: boolean, true means recommend to follow up.',
        '- score: 0-1 float, confidence score of match.',
        '- reasons: string array, list 1-3 key reasons.',
        f"Example output: {json.dumps(exemplar, ensure_ascii=False)}",
        "",
        "[Candidate profile]",
        person_profile or "No candidate profile.",
        "",
        "[Project email content]",
        project_description,
        "",
        "Please only return JSON, do not include extra text.",
    ]
    return "\n".join(prompt_blocks)


def parse_ai_decision(result: Dict[str, Any]) -> MatchDecision:
    try:
        matched = bool(result["match"])
        score_value = result.get("score")
        score = float(score_value) if score_value is not None else None
        reasons_raw = result.get("reasons") or []
        reasons = [str(reason) for reason in reasons_raw][:3]
        return MatchDecision(matched=matched, score=score, reasons=reasons)
    except (ValueError, TypeError, KeyError) as exc:
        logger.error(f"Parse AI response failed: {result}", exc_info=True)
        return MatchDecision(matched=False)


def extract_text_from_html(html_content: str) -> str:
    soup = BeautifulSoup(html_content, "html.parser")
    body = soup.body
    if body:
        return body.get_text(separator="\n", strip=True)
    return soup.get_text(separator="\n", strip=True)