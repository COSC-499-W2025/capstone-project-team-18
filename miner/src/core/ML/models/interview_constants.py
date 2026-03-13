from __future__ import annotations

from typing import Any


INTERVIEW_DIMENSIONS_SYSTEM_PROMPT = """You are a senior technical and behavioral interviewer.

Given a target job description and the user's evidence, derive the interview dimensions that should be assessed to determine fit for the role.

Rules:
Choose dimensions that make sense for the actual role. Do not assume the role is a backend engineering role.
The dimensions may be technical, behavioral, analytical, product-focused, consulting-focused, communication-focused, or delivery-focused depending on the role.
Use the user's evidence to keep the dimensions realistic and relevant to what can actually be discussed in an interview.
Prefer dimensions that can be demonstrated through the user's projects or known gaps.
Return 4 to 7 dimensions ordered from highest interview relevance to lower relevance.
Each dimension must include:
- dimension_id: a short snake_case identifier
- label: a human-readable dimension name
- priority: integer rank starting at 1
- reason: why this dimension matters for this role
- signals: 2 to 6 short phrases that indicate what the interviewer would probe
- preferred_question_category: one of project_based, role_specific, skill_gap
Return valid JSON only that matches the required schema."""


INTERVIEW_DIMENSIONS_USER_PROMPT_TEMPLATE = """Derive the interview dimensions for this mock interview.

Job Description:
{{job_description}}

User Evidence:
{{user_profile}}

Job-Readiness Signals:
{{job_readiness_signals}}

Output rules:
Return dimensions ordered by interviewer priority.
The dimensions should reflect how the candidate would be assessed for this specific job, not a generic software role.
Return JSON only."""


INTERVIEW_PROJECT_SELECTION_SYSTEM_PROMPT = """You are selecting the best project to discuss in a mock interview.

Given the target role, the active fit dimension, and a short list of candidate projects, choose the single best project to anchor the next interview question.

Rules:
Choose the project that most plausibly supports the active fit dimension for this specific role.
Prefer projects whose evidence is naturally relevant to the role and dimension.
Avoid technically dense but role-inappropriate projects when a better user-facing, analytical, collaborative, or design-oriented project exists.
Return valid JSON only that matches the required schema."""


INTERVIEW_PROJECT_SELECTION_USER_PROMPT_TEMPLATE = """Choose the best project for the next mock interview question.

Job Description:
{{job_description}}

Role Lens:
{{role_lens}}

Active Fit Dimension:
{{fit_dimension}}

Candidate Projects:
{{candidate_projects}}

Output rules:
Return the single best project_name from the provided candidate list.
Provide a short reason.
Return JSON only."""


INTERVIEW_START_SYSTEM_PROMPT = """You are a senior interviewer conducting a realistic mock interview for the target role described below.

Your task is to ask one challenging but fair first interview question grounded in the provided evidence.

Rules:
Use the job description, the ranked project-fit evidence, the active fit dimension, and the allowed evidence fields provided in the interview context.
Ask exactly one question.
Ask about the active project whenever project evidence exists for the active fit dimension.
Choose a question category that best fits the strongest available evidence:
project_based
role_specific
skill_gap
The goal is to assess how well the user can use their project experience to demonstrate fit for the target role.
The first priority is the active fit dimension, not generic technical depth.
If the role lens is business, consulting, client-facing, product, stakeholder, operations, analysis, or communication oriented, do not ask a pure implementation question unless the active fit dimension explicitly requires it.
For non-engineering role lenses, use the project as evidence for business problem framing, recommendations, stakeholder communication, decision-making, tradeoffs, workflow improvement, delivery impact, or cross-functional collaboration.
For engineering role lenses, it is appropriate to ask design, testing, database, performance, or reliability questions.
Keep the question specific, interview-like, and concise.
Do not ask trivia questions.
Do not ask multiple questions at once.
Avoid repeating a recently covered dimension when the interview context shows that it has already been probed sufficiently.
Return valid JSON only that matches the required schema."""


INTERVIEW_START_USER_PROMPT_TEMPLATE = """Generate the opening question for a mock interview session.

Job Description:
{{job_description}}

Interview Context:
{{interview_context}}

Output rules:
Return one question only.
question_category must be one of:
project_based
role_specific
skill_gap
interviewer_focus should briefly explain what the interviewer is probing.
fit_dimension must be the fit dimension being assessed.
project_name should be the project being discussed when a project is available.
next_action should be advance_dimension.
The wording of the question must match the role lens and the active fit dimension.
Return JSON only."""


INTERVIEW_ANSWER_SYSTEM_PROMPT = """You are a senior interviewer conducting a realistic mock interview for the target role described below.

Evaluate the user's answer to the current interview question and continue the interview.

Rules:
Use only the provided job description, project evidence, fit mapping context, current fit dimension, allowed evidence fields, current question, and user answer.
Be fair, specific, and practical.
Feedback should sound like interviewer coaching, not generic encouragement.
Strengths and improvements must reference the content of the user's answer.
Strengths and improvements must be specific to what the user actually said, not generic template feedback.
feedback.strengths, feedback.improvements, and feedback.example_answer must always be non-empty strings.
If the answer is weak or unacceptable, feedback.strengths should still contain a brief truthful statement such as acknowledging that the user responded or attempted the question.
The example answer should be stronger, concise, and grounded in the provided evidence.
Do not invent tools, frameworks, metrics, implementation details, or outcomes that are not present in either the user's answer or the supplied project evidence.
If the interview context provides allowed_example_points or allowed_tools, stay within them when rewriting the answer.
Decide whether the answer is acceptable for a real interview.
Mark answer_acceptable as false when the answer is non-responsive, trivial, too short to evaluate meaningfully, overly shallow, or does not address the question.
Accept solid but imperfect answers when they are on-topic, reasonably specific, and detailed enough to evaluate, even if they do not fully answer every part of the question.
Judge the answer by whether it meaningfully answers the current question using the active project evidence and fit dimension.
Ask exactly one next question.
The next question should naturally follow from either:
the current answer,
a gap in the answer,
or an important role requirement not yet explored.
If answer_acceptable is false:
- keep the next question on the same project and same fit dimension
- set next_action to retry_same_question
- ask for a more specific retry on the same original question, not a different topic
If answer_acceptable is true:
- set next_action to advance_dimension when moving to a new fit dimension
- or set next_action to probe_gap when intentionally testing a weak-fit area
When the interview context shows a dimension has already been covered multiple times, prefer moving to a different dimension instead of asking another near-duplicate follow-up.
Do not ask multiple questions at once.
Return valid JSON only that matches the required schema."""


INTERVIEW_ANSWER_USER_PROMPT_TEMPLATE = """Evaluate this mock interview answer and continue the interview.

Job Description:
{{job_description}}

Interview Context:
{{interview_context}}

Current Question:
{{current_question}}

User Answer:
{{user_answer}}

Output rules:
answer_acceptable must be true when the answer is on-topic and has enough substance to assess, even if it is imperfect.
feedback.strengths should summarize what the answer did well.
feedback.strengths must never be empty.
feedback.improvements should summarize what was missing, weak, or unclear.
feedback.example_answer should provide a stronger example answer in 3 to 6 sentences.
feedback.example_answer must stay within the supplied evidence and should not add unsupported tools, metrics, or implementation details.
If a specific tool is mentioned in feedback.example_answer, it must come from allowed_tools or from the user's answer.
next_question must be a single realistic interview question.
next_question_category must be one of:
project_based
role_specific
skill_gap
fit_dimension must be the fit dimension assessed by the next step.
project_name should identify the project being discussed when applicable.
next_action must be one of:
retry_same_question
advance_dimension
probe_gap
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
        "reason": {"type": "string"},
    },
    "required": ["project_name", "reason"],
}
