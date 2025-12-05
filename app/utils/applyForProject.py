from dataclasses import dataclass
import json
from typing import Any, Dict
import logging

from app.services import CodeurProjectCrawler
from app.services.globalVars import ProjectStatus, profile
from app.repositories.project_repository import update_project_record
from app.services import call_llama as call_llama_service
from app.models.OfferPayload import OfferPayload
from app.services.offer_automation import apply_once

logger = logging.getLogger(__name__)

@dataclass
class OfferAmount:
    offer_amount: int

@dataclass
class OfferMessage:
    offer_message: str

@dataclass
class OfferDuration:
    offer_duration: int

async def apply_for_project(project: dict[str, Any]) -> tuple[bool, str]:
    try:
        project_url = project.get("url")
        crawler = CodeurProjectCrawler(project_url)
        if not crawler.check_project_availability():
            new_project = project.copy()
            new_project["status"] = ProjectStatus.NOT_AVAILABLE
            await update_project_record(project_url, new_project)
            logger.info(f"Project {project_url} is not available")
            return False, f"Project {project_url} is not available"
        # Generate the offer message, amount and duration with AI
        system_prompt_offer_duration = "You are a helper responsible for generating the offer duration for the project, and can only output JSON format duration."
        prompt_offer_duration = build_offer_project_duration_prompt(project["description"])
        ai_response_offer_duration = call_llama_service(prompt_offer_duration, system_prompt_offer_duration)
        offer_duration = parse_ai_offer_duration(ai_response_offer_duration).offer_duration
        system_prompt_offer_amount = "You are a helper responsible for generating the offer amount for the project, and can only output JSON format amount."
        prompt_offer_amount = build_offer_amount_prompt(project.get("amount"), offer_duration, project["description"])
        ai_response_offer_amount = call_llama_service(prompt_offer_amount, system_prompt_offer_amount)
        offer_amount = parse_ai_offer_amount(ai_response_offer_amount).offer_amount
        system_prompt_offer_message = "You are a helper responsible for generating the offer message for the project, and can only output JSON format message."
        prompt_offer_message = build_offer_message_prompt(profile, project["description"])
        ai_response_offer_message = call_llama_service(prompt_offer_message, system_prompt_offer_message)
        offer_message = parse_ai_offer_message(ai_response_offer_message).offer_message
        # Fill the offer form and submit the offer
        offer_payload = OfferPayload(
            project_url=project_url,
            amount=offer_amount,
            duration=offer_duration,
            message=offer_message,
            pricing_mode="flat_rate",
            level="standard",
        )
        logger.info("Offer payload: ", offer_payload)
        success, message = await apply_once(offer_payload)
        if success:
            new_project = project.copy()
            new_project["status"] = ProjectStatus.ANSWERED
            await update_project_record(project_url, new_project)
            logger.info(f"Project {project_url} applied successfully: {message}")
            return True, message
        else:
            logger.error(f"Project {project_url} applied failed: {message}")
            return False, message
    except Exception as e:
        logger.error(f"Failed to apply for project {project_url}: {e}")
        return False, f"Internal error: {e}"


def build_offer_project_duration_prompt(project_description: str) -> str:
    """Build prompt, combine project description into context and generate the offer duration with AI."""
    exemplar = {
        "offer_duration": 10 # in days
    }
    prompt_blocks = [
        "Please generate a reasonable offer duration for the project according to the project description, the duration should be less than 180 days (6 months).",
        "Response field description:",
        "- offer_duration: integer. The offer duration for the project, in days.",
        "",
        "Here is an example output:",
        f"{json.dumps(exemplar, ensure_ascii=False)}",
        "",
        "[Project description]", project_description, "", "Please only return JSON, do not include extra text.",
    ]
    return "\n".join(prompt_blocks)

def parse_ai_offer_duration(result: Dict[str, Any]) -> OfferDuration:
    logger.info("AI response: ", result)
    try:
        offer_duration = result["offer_duration"]
        return OfferDuration(offer_duration=offer_duration)
    except (ValueError, TypeError, KeyError) as exc:
        logger.error("Parse AI response failed: %s", result, exc_info=True)
        return OfferDuration(offer_duration=0)

def build_offer_amount_prompt(project_amount_range: list[int],duration: int, project_description: str) -> str:
    """Build prompt, combine project amount range, project duration and project description into context and generate the offer amount with AI."""
    exemplar = {
        "offer_amount": 1000 # in euros
    }
    prompt_blocks = [
        "Please generate a reasonable offer amount for the project according to the project amount range（more or equal than minimum amount and less or equal than maximum amount）, project duration and the project description, the amount should be between the project amount range.",
        "The offer amount should be calculated based on the project amount range, project duration and the project description.",
        "The offer amount should be a reasonable amount that is affordable for the project owner and the candidate.",
        "The offer amount should be a reasonable amount that is affordable for the project owner and the candidate.",
        "Response field description:",
        "- offer_amount: integer. The offer amount for the project, in euros.",
        "Here is an example output:",
        f"{json.dumps(exemplar, ensure_ascii=False)}",
        "",
        "[Project amount range]",
        f"Project amount range: {project_amount_range[0]} euros - {project_amount_range[1]} euros",
        "",
        "[Project duration]",
        f"Project duration: {duration} days",
        "",
        "[Project description]",
        project_description,
        "",
        "Please only return JSON, do not include extra text.",
    ]
    return "\n".join(prompt_blocks)

def parse_ai_offer_amount(result: Dict[str, Any]) -> OfferAmount:
    logger.info("AI response: ", result)
    try:
        offer_amount = result["offer_amount"]
        return OfferAmount(offer_amount=offer_amount)
    except (ValueError, TypeError, KeyError) as exc:
        logger.error("Parse AI response failed: %s", result, exc_info=True)
        return OfferAmount(offer_amount=0)

def build_offer_message_prompt(person_profile: str, project_description: str) -> str:
    """Build prompt, combine candidate profile and project description into context and generate the offer message with AI."""
    exemplar = {
        "offer_message": (
            "（please generate the message in the same language as the project description, for example, if the project description is in French, please generate the message in French; if it is in English, use English.）"
            "Bonjour, je suis très enthousiaste à l’idée de participer à votre projet. Mes compétences et expériences variées me permettent d’apporter des solutions efficaces et créatives, parfaitement adaptées à vos besoins. "
            "I have a strong ability to solve complex problems, design robust architectures, and ensure the quality of development. "
            "I put a lot of emphasis on communication, listening, and accompaniment at each stage of the project to ensure the success of our collaboration. "
            "If you want to share more details about the project, feel free to contact me to discuss more: I am ready to transform your vision into reality!"
        ),
    }
    prompt_blocks = [
        "Please generate a persuasive, eye-catching, genuine, and professional human-like offer message for the project. The message must output JSON only.",
        "Instructions for the message:",
        "- offer_message: string. The offer message for the project.",
        "- Maximize the candidate's advantages, highlight strengths and outstanding skills as much as possible, minimize or downplay any shortcomings.",
        "- Avoid mentioning age or years of work experience if possible.",
        "- Within 1000 characters, create the most compelling, positive, and attention-grabbing message that clearly demonstrates value to the client.",
        "- The message should be friendly, professional, and sincere.",
        "- Please match the language of the offer message with the project's language. For example, if the project description is in French, generate the message in French; if it is in English, use English.",
        "",
        "Here is an example output:",
        f"{json.dumps(exemplar, ensure_ascii=False)}",
        "",
        "[Candidate profile]",
        person_profile or "No candidate profile.",
        "",
        "[Project description]",
        project_description,
        "",
        "Please only return JSON, do not include extra text.",
    ]
    return "\n".join(prompt_blocks)

def parse_ai_offer_message(result: Dict[str, Any]) -> OfferMessage:
    logger.info("AI response: ", result)
    try:
        offer_message = result["offer_message"]
        return OfferMessage(offer_message=offer_message)
    except (ValueError, TypeError, KeyError) as exc:
        logger.error("Parse AI response failed: %s", result, exc_info=True)
        return OfferMessage(offer_message="")