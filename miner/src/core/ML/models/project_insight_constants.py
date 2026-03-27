from __future__ import annotations

from typing import Any


PROJECT_INSIGHT_REFILL_SYSTEM_PROMPT = """You generate concise, evidence-based resume insight prompts for a technical project.

Rules:
Use only the supplied project context and signals.
Do not assume a project type beyond the evidence provided.
Do not invent tools, results, users, metrics, or responsibilities that are not supported by the context.
Return exactly the requested number of new insight prompts when possible.
Each insight must be distinct from the excluded insights and should not closely paraphrase them.
Match the tone and structure of the style examples when examples are provided.
Each insight should help a user turn project work into a stronger resume bullet or interview-ready accomplishment statement.
Keep each insight concise, practical, and specific.
Prefer reflective prompt/question wording over generic advice.
Do not give vague career advice.
Return valid JSON only that matches the required schema."""


PROJECT_INSIGHT_REFILL_USER_PROMPT_TEMPLATE = """Generate {{count}} new project insight prompt(s).

Project context:
{{project_context}}

Style examples:
{{style_examples}}

Excluded insights:
{{excluded_insights}}

Output rules:
- Return only new insight prompts that are grounded in the project context.
- Avoid duplicates and close paraphrases of excluded insights.
- Make each prompt resume-helpful, concrete, and tied to real project evidence.
- Each prompt should be 1 to 2 sentences max.
- Return JSON only."""


def project_insight_refill_response_schema(count: int) -> dict[str, Any]:
    safe_count = max(1, int(count))
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "insights": {
                "type": "array",
                "minItems": 1,
                "maxItems": safe_count,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "message": {"type": "string"},
                    },
                    "required": ["message"],
                },
            },
        },
        "required": ["insights"],
    }


DEFAULT_PROJECT_INSIGHT_REFILL_SCHEMA_NAME = "project_insight_refill"
