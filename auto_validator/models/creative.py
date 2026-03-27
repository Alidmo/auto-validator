from enum import Enum
from typing import Optional
from pydantic import BaseModel


class QuestionType(str, Enum):
    QUALIFICATION = "qualification"
    PAIN_SCALE = "pain_scale"
    OPEN_ENDED = "open_ended"


class AdHook(BaseModel):
    variation_number: int
    hook_text: str
    angle_type: str
    visual_prompt: str = ""
    generated_image_url: Optional[str] = None


class LandingPageCopy(BaseModel):
    above_fold_headline: str
    above_fold_subheadline: str
    problem_section: str
    desired_outcome_section: str
    social_proof_placeholder: str
    cta_text: str
    cta_subtext: str


class QuizQuestion(BaseModel):
    question_id: str
    question_text: str
    question_type: QuestionType
    options: list[str] = []
    required: bool = True


class CreativeOutput(BaseModel):
    ad_hooks: list[AdHook]
    landing_page: LandingPageCopy
    quiz_questions: list[QuizQuestion]
    generated_image_urls: list[str] = []
    google_doc_url: Optional[str] = None
    tally_quiz_id: Optional[str] = None
    tally_quiz_json: Optional[dict] = None
