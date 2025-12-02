from dataclasses import dataclass
import json
from typing import Any, Dict
from app.services import CodeurBrowserSession, CodeurProjectCrawler
from app.services.globalVars import ProjectStatus, profile
from app.repositories.project_repository import update_project_status
from app.repositories.project_repository import get_project_by_url
import logging
from app.services import call_llama as call_llama_service

logger = logging.getLogger(__name__)

@dataclass
class OfferMessage:
    offer_message: str

async def apply_for_project(project: dict[str, Any]) -> OfferMessage:
    # try:
    #     project = await get_project_by_url(project_url)
    #     project_id = project.get("project_id")
    #     crawler = CodeurProjectCrawler(project_url)
    #     if not crawler.check_project_availability():
    #         await update_project_status(project_id, ProjectStatus.NOT_AVAILABLE)
    #         return False
    #     # TODO: fill the offer form and submit the offer
    #     # TODO: generate the offer message with AI
    #     await update_project_status(project_id, ProjectStatus.ANSWERED)
    #     return True
    # except Exception as e:
    #     logger.error(f"Failed to apply for project {project_url}: {e}")
    #     return False

    system_prompt = "You are a helper responsible for generating the offer message for the project, and can only output JSON format message."
    prompt = build_prompt(profile, project["description"])
    ai_response = call_llama_service(prompt, system_prompt)
    print("AI response: ", ai_response)
    print("Parse AI response: ", parse_ai_decision(ai_response))
    return parse_ai_decision(ai_response)


def build_prompt(person_profile: str, project_description: str) -> str:
    """Build prompt, combine candidate profile and project description into context and generate the offer message with AI."""
    exemplar = {
        "offer_message": (
            "（please generate the message in the same language as the project description, for example, if the project description is in French, please generate the message in French; if it is in English, use English.）"
            "Bonjour, je suis très enthousiaste à l’idée de participer à votre projet. Mes compétences et expériences variées me permettent d’apporter des solutions efficaces et créatives, parfaitement adaptées à vos besoins. "
            "I have a strong ability to solve complex problems, design robust architectures, and ensure the quality of development. "
            "I put a lot of emphasis on communication, listening, and accompaniment at each stage of the project to ensure the success of our collaboration. "
            "Contact me to discuss more: I am ready to transform your vision into reality!"
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

def parse_ai_decision(result: Dict[str, Any]) -> OfferMessage:
    print("AI response: ", result)
    try:
        offer_message = result["offer_message"]
        return OfferMessage(offer_message=offer_message)
    except (ValueError, TypeError, KeyError) as exc:
        logger.error("Parse AI response failed: %s", result, exc_info=True)
        return OfferMessage(offer_message="")