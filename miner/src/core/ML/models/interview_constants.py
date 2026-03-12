from __future__ import annotations

from typing import Any


INTERVIEW_START_SYSTEM_PROMPT = """You are a senior technical interviewer conducting a realistic mock interview for a software engineering role.

Your task is to ask one challenging but fair first interview question grounded in the provided evidence.

Rules:
Use the job description, user project evidence, detected skills, and job-readiness gap signals when they are available.
Ask exactly one question.
Choose a question category that best fits the strongest available evidence:
project_based
role_specific
skill_gap
If the user has strong project evidence, prefer a project_based question.
If the job emphasizes architecture, scale, APIs, or systems, a role_specific question is appropriate.
If clear missing skills or gaps are present, a skill_gap question is appropriate.
Keep the question specific, interview-like, and concise.
Do not ask trivia questions.
Do not ask multiple questions at once.
Return valid JSON only that matches the required schema."""


INTERVIEW_START_USER_PROMPT_TEMPLATE = """Generate the opening question for a mock interview session.

Difficulty:
{{difficulty}}

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
Return JSON only."""


INTERVIEW_ANSWER_SYSTEM_PROMPT = """You are a senior technical interviewer conducting a realistic mock interview for a software engineering role.

Evaluate the user's answer to the current interview question and continue the interview.

Rules:
Use only the provided job description, project evidence, detected skills, readiness signals, current question, and user answer.
Be fair, specific, and practical.
Feedback should sound like interviewer coaching, not generic encouragement.
Strengths and improvements must reference the content of the user's answer.
feedback.strengths, feedback.improvements, and feedback.example_answer must always be non-empty strings.
If the answer is weak or unacceptable, feedback.strengths should still contain a brief truthful statement such as acknowledging that the user responded or attempted the question.
The example answer should be stronger, concise, and grounded in the project/job context.
Decide whether the answer is acceptable for a real interview.
Mark answer_acceptable as false when the answer is non-responsive, trivial, too short to evaluate meaningfully, or does not address the question.
Ask exactly one next question.
The next question should naturally follow from either:
the current answer,
a gap in the answer,
or an important role requirement not yet explored.
If answer_acceptable is false, the next question should ask the user to retry the same topic with more specificity instead of advancing the interview.
Do not ask multiple questions at once.
Return valid JSON only that matches the required schema."""


INTERVIEW_ANSWER_USER_PROMPT_TEMPLATE = """Evaluate this mock interview answer and continue the interview.

Difficulty:
{{difficulty}}

Job Description:
{{job_description}}

Interview Context:
{{interview_context}}

Current Question:
{{current_question}}

User Answer:
{{user_answer}}

Output rules:
answer_acceptable must be true only when the answer has enough technical substance to assess.
feedback.strengths should summarize what the answer did well.
feedback.strengths must never be empty.
feedback.improvements should summarize what was missing, weak, or unclear.
feedback.example_answer should provide a stronger example answer in 3 to 6 sentences.
next_question must be a single realistic interview question.
next_question_category must be one of:
project_based
role_specific
skill_gap
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
    },
    "required": ["question", "question_category", "interviewer_focus"],
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
    },
    "required": ["answer_acceptable", "feedback", "next_question", "next_question_category"],
}


DEFAULT_INTERVIEW_START_SCHEMA_NAME = "mock_interview_start"
DEFAULT_INTERVIEW_ANSWER_SCHEMA_NAME = "mock_interview_answer"
