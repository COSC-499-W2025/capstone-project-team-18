from __future__ import annotations

from typing import Any


INTERVIEW_DIMENSIONS_SYSTEM_PROMPT = """You are a senior interviewer. Derive 4 to 7 interview dimensions for the target role from the job description and user evidence.

Rules:
Choose dimensions that fit the actual role, not a generic backend role.
Dimensions may be technical, behavioral, analytical, product, consulting, communication, or delivery focused.
Keep them realistic based on the user's projects or known gaps.
Each dimension must include: dimension_id, label, priority, reason, signals, and preferred_question_category.
Return valid JSON only."""


INTERVIEW_DIMENSIONS_USER_PROMPT_TEMPLATE = """Derive interview dimensions for this mock interview.

Job Description:
{{job_description}}

User Evidence:
{{user_profile}}

Job-Readiness Signals:
{{job_readiness_signals}}

Return dimensions in interviewer priority order as JSON only."""


INTERVIEW_PROJECT_SELECTION_SYSTEM_PROMPT = """Choose the single best project to anchor the next interview question.

Rules:
Pick the candidate that best supports the active fit dimension for this role.
Prefer naturally relevant evidence.
Avoid technically dense but role-inappropriate projects when a better user-facing, analytical, collaborative, or design-oriented option exists.
Return valid JSON only."""


INTERVIEW_PROJECT_SELECTION_USER_PROMPT_TEMPLATE = """Choose the best project for the next mock interview question.

Job Description:
{{job_description}}

Role Lens:
{{role_lens}}

Active Fit Dimension:
{{fit_dimension}}

Candidate Projects:
{{candidate_projects}}

Return the single best project_name from the candidate list. Return JSON only."""


INTERVIEW_START_SYSTEM_PROMPT = """You are a senior interviewer starting a realistic mock interview.

Rules:
Use the job description, active fit dimension, active project, and allowed evidence in the interview context.
Ask exactly one concise interview question.
Prioritize the active fit dimension over generic technical depth.
Use project_based, role_specific, or skill_gap as appropriate.
For non-engineering role lenses, avoid pure implementation questions unless the dimension requires them.
Do not ask trivia or multiple questions at once.
Avoid repeating a dimension that has already been covered enough.
Return valid JSON only."""


INTERVIEW_START_USER_PROMPT_TEMPLATE = """Generate the opening question for a mock interview session.

Job Description:
{{job_description}}

Interview Context:
{{interview_context}}

Return one question only. `question_category` must be `project_based`, `role_specific`, or `skill_gap`. `interviewer_focus` should briefly state the intent. `fit_dimension` and `project_name` must match the chosen focus. `next_action` should be `advance_dimension`. Return JSON only."""


INTERVIEW_ANSWER_SYSTEM_PROMPT = """You are a senior interviewer continuing a realistic mock interview.

Rules:
Use only the provided job description, current question, user answer, fit dimension, and allowed evidence.
Be fair, specific, and practical.
Feedback must reference what the user actually said and avoid generic template language.
`feedback.strengths`, `feedback.improvements`, and `feedback.example_answer` must always be non-empty.
Keep `feedback.example_answer` grounded in the supplied evidence. Do not invent unsupported tools, metrics, implementation details, or outcomes.
Accept solid but imperfect answers if they are on-topic, reasonably specific, and detailed enough to assess.
Reject only answers that are non-responsive, trivial, too short, overly shallow, or off-topic.
Ask exactly one next question.
If the answer is unacceptable, retry the same project and dimension with a more specific version of the same question.
If the answer is acceptable, advance_dimension or probe_gap as appropriate.
Avoid near-duplicate follow-ups when a dimension has already been covered enough.
Return valid JSON only."""


INTERVIEW_ANSWER_USER_PROMPT_TEMPLATE = """Evaluate this mock interview answer and continue the interview.

Job Description:
{{job_description}}

Interview Context:
{{interview_context}}

Current Question:
{{current_question}}

User Answer:
{{user_answer}}

Rules:
Set `answer_acceptable` to true when the answer is on-topic and substantive enough to assess, even if imperfect.
`feedback.strengths` and `feedback.improvements` should summarize what worked and what was missing.
`feedback.example_answer` must be 3 to 6 sentences and stay within the supplied evidence.
Any tool named in `feedback.example_answer` must come from `allowed_tools` or the user's answer.
`next_question` must be a single realistic interview question.
`next_question_category` must be `project_based`, `role_specific`, or `skill_gap`.
`next_action` must be `retry_same_question`, `advance_dimension`, or `probe_gap`.
Return JSON only."""


INTERVIEW_START_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "question": {"type": "string"},
        "question_category": {
            "type": "string",
            "enum": ["project_based", "role_specific", "skill_gap"],
        },
        "interviewer_focus": {"type": "string"},
        "fit_dimension": {"type": "string"},
        "project_name": {"type": ["string", "null"]},
        "next_action": {
            "type": "string",
            "enum": ["retry_same_question", "advance_dimension", "probe_gap"],
        },
    },
    "required": [
        "question",
        "question_category",
        "interviewer_focus",
        "fit_dimension",
        "project_name",
        "next_action",
    ],
}


INTERVIEW_ANSWER_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "answer_acceptable": {"type": "boolean"},
        "feedback": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "strengths": {"type": "string"},
                "improvements": {"type": "string"},
                "example_answer": {"type": "string"},
            },
            "required": ["strengths", "improvements", "example_answer"],
        },
        "next_question": {"type": "string"},
        "next_question_category": {
            "type": "string",
            "enum": ["project_based", "role_specific", "skill_gap"],
        },
        "fit_dimension": {"type": "string"},
        "project_name": {"type": ["string", "null"]},
        "next_action": {
            "type": "string",
            "enum": ["retry_same_question", "advance_dimension", "probe_gap"],
        },
    },
    "required": [
        "answer_acceptable",
        "feedback",
        "next_question",
        "next_question_category",
        "fit_dimension",
        "project_name",
        "next_action",
    ],
}


DEFAULT_INTERVIEW_START_SCHEMA_NAME = "mock_interview_start"
DEFAULT_INTERVIEW_ANSWER_SCHEMA_NAME = "mock_interview_answer"
DEFAULT_INTERVIEW_DIMENSIONS_SCHEMA_NAME = "mock_interview_dimensions"
DEFAULT_INTERVIEW_PROJECT_SCHEMA_NAME = "mock_interview_project_selection"


INTERVIEW_DIMENSIONS_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "dimensions": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "dimension_id": {"type": "string"},
                    "label": {"type": "string"},
                    "priority": {"type": "integer", "minimum": 1},
                    "reason": {"type": "string"},
                    "signals": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "preferred_question_category": {
                        "type": "string",
                        "enum": ["project_based", "role_specific", "skill_gap"],
                    },
                },
                "required": [
                    "dimension_id",
                    "label",
                    "priority",
                    "reason",
                    "signals",
                    "preferred_question_category",
                ],
            },
        },
    },
    "required": ["dimensions"],
}


INTERVIEW_PROJECT_SELECTION_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "project_name": {"type": "string"},
    },
    "required": ["project_name"],
}
