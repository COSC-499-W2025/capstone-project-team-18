from __future__ import annotations

from typing import Any


JOB_READINESS_SYSTEM_PROMPT = """You are a job readiness evaluator.

Compare the provided job description against the provided user evidence and return a concise, evidence based evaluation.

Rules:
Use only the provided evidence for judging fit.
Do not assume skills or experience that are not supported by the evidence.
Interpret related experience reasonably.
If the job asks for a tool or framework and the evidence shows a closely related one, treat it as related experience instead of an exact match.
Keep the response concise, practical, and readable.
Focus only on overall fit, strongest supported strengths, clearest weaknesses, and the most useful improvement suggestions.
Suggestions must be practical and real world.
Suggestions must be concrete and action oriented.
Do not give vague advice like learn X, improve Y, or explore Z.
Instead, tell the user to build, create, deploy, document, or add a specific artifact or experience that would close the gap.
Each suggestion should tell the user exactly what to do next, and where useful, point them toward a concrete resource type such as an official tutorial, a guided learning path, a certificate program, or a portfolio project idea.
Make the first words of each suggestion action-first, such as Build, Create, Deploy, Add, Complete, Document, Implement, Publish, Describe, or Containerize.
Tie each suggestion to a specific weakness or partial match from the evaluation.
Each suggestion must produce a concrete output the user could finish this week and later reference in a resume, project, or portfolio.
Good outputs include a small project, a deployed demo, a documented feature, a portfolio artifact, or a revised resume bullet.
If a learning resource is mentioned, it must support a concrete build task and cannot be the main recommendation by itself.
Bad examples: "Learn Flask", "Enhance Git skills", "Explore Docker", "Improve debugging".
Good examples: "Build a small Flask CRUD API and publish the repo", "Containerize an existing FastAPI service and add deployment notes to the portfolio", "Document one debugging fix as a resume-ready project bullet".
Do not invent exact URLs.
Prefer official docs and reputable learning platforms when naming resources.
Return valid JSON only that matches the required schema."""


JOB_READINESS_USER_PROMPT_TEMPLATE = """Compare the following job description against the user evidence and return only:
fit_score
summary
strengths
weaknesses
suggestions

Job description:
{{job_description}}

User evidence:
{{user_profile}}

Output rules:
fit_score must be an integer from 0 to 100.
strengths must be ranked from strongest and most role relevant to less strong.
weaknesses must be ranked from biggest role relevant gap to smaller gap.
suggestions must be ranked by which improvement would most increase readiness.
Suggestions must be specific and actionable.
For each suggestion, include:
item
reason
priority
action_type
resource_name
resource_type
resource_hint
resource_hint should be a short explanation of what the user should look for, not a made up link.
For each suggestion, provide a practical next step that the user can complete and later reference in a resume, project, or portfolio.
Prefer specific outputs such as:
a small project
a deployed demo
a documented feature
a portfolio artifact
a resume bullet improvement
a targeted course followed by a project
Start each suggestion item with an action verb.
Do not write generic suggestion items like:
Learn Flask
Enhance Git skills
Familiarize yourself with Docker
Explore cloud platforms
Improve debugging skills
Instead write suggestion items like:
Build a small Flask CRUD API and publish the repository
Containerize an existing service and document the deployment steps
Add a resume bullet that describes a debugging fix with measurable impact
Complete an official tutorial and apply it by shipping a small demo
Keep the analysis evidence based and conservative.
Return JSON only."""


JOB_READINESS_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "fit_score": {
            "type": "integer",
            "minimum": 0,
            "maximum": 100,
        },
        "summary": {
            "type": "string",
        },
        "strengths": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "item": {"type": "string"},
                    "reason": {"type": "string"},
                    "rank": {"type": "integer", "minimum": 1},
                },
                "required": ["item", "reason", "rank"],
            },
        },
        "weaknesses": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "item": {"type": "string"},
                    "reason": {"type": "string"},
                    "rank": {"type": "integer", "minimum": 1},
                },
                "required": ["item", "reason", "rank"],
            },
        },
        "suggestions": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "item": {"type": "string"},
                    "reason": {"type": "string"},
                    "priority": {"type": "integer", "minimum": 1},
                    "action_type": {"type": "string"},
                    "resource_name": {"type": "string"},
                    "resource_type": {"type": "string"},
                    "resource_hint": {"type": "string"},
                },
                "required": [
                    "item",
                    "reason",
                    "priority",
                    "action_type",
                    "resource_name",
                    "resource_type",
                    "resource_hint",
                ],
            },
        },
    },
    "required": ["fit_score", "summary", "strengths", "weaknesses", "suggestions"],
}


DEFAULT_JOB_READINESS_SCHEMA_NAME = "job_readiness_analysis"
