"""
Constants used by the contribution summary generator.

Keeping large prompt text and keyword maps here improves readability in
`summary_generator.py`.
"""

SUMMARY_STYLE_EXAMPLE = (
    "Data-driven Computer Science Honours student with hands-on experience analyzing user and system data "
    "to generate insights that improve software delivery processes. Strong in Python, Java, SQL, Excel and "
    "Power BI with proven ability to automate reporting, build dashboards, and clearly communicate findings "
    "to technical and non-technical stakeholders. Curious learner with exposure to Generative AI and LLM evaluation."
)

SUMMARY_EXAMPLE_GUIDANCE = (
    "Example style (do NOT copy wording, only match tone and structure). "
    "Do NOT reuse any phrases from the example; avoid any 5-word sequence overlap.\n"
    "Example: "
)

SUMMARY_BASE_PROMPT = (
    "Write a 2-6 sentence professional summary based ONLY on the facts below. "
    "The summary must be narrative, not a list. Avoid repeating full skill/tool lists; "
    "instead describe experience and impact. Do not invent tools, roles, or skills. "
    "Adapt wording to the user's profile by using their focus, role, cadence, commit_focus, "
    "themes, activities, emerging fields, and experience_stage when available. "
    "Do not repeat the same domain statement more than once (e.g., web, data, mobile). "
    "Merge overlapping ideas instead of repeating them with different wording. "
    "Use stage-specific identity language: student, early-career, or experienced. "
    "Prefer concise, specific phrasing used in modern resume summaries. "
    "Use a professional resume tone. Do NOT mention being an assistant or providing summaries. "
    "Avoid generic filler like 'team player', 'keen eye for detail', 'strong focus on quality', "
    "'committed to delivering high-quality work' or 'strive to meet deadlines'. "
    "Do NOT mention specific project names, company names, or team management."
)

SUMMARY_BANNED_PHRASES = (
    "resume assistant",
    "as an assistant",
    "i can provide",
    "i can help",
    "committed to delivering",
    "strive to meet deadlines",
    "high-quality work",
    "team player",
    "keen eye for detail",
    "strong focus on quality",
    "collaborative environment",
    "team members",
    "company",
    "organization",
    "project names",
)

SUMMARY_DOMAIN_KEYWORDS: dict[str, tuple[str, ...]] = {
    "web": (
        "web", "frontend", "html", "css", "javascript",
        "typescript", "react", "vue", "angular",
    ),
    "data": (
        "data analysis", "data visualization", "analytics", "dashboard",
        "sql", "power bi", "tableau", "pandas",
    ),
    "mobile": (
        "mobile", "android", "android studio", "ios", "kotlin", "swift",
    ),
    "backend": (
        "backend", "api", "service", "server", "microservice",
    ),
    "ml": (
        "machine learning", "generative ai", "llm", "model evaluation",
    ),
}

SUMMARY_PHRASE_NORMALIZATION_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    (r"\bdata analysis and data visualization\b", "data analysis and visualization"),
    (r"\bweb development and web applications\b", "web application development"),
    (r"\bmobile development using\b", "mobile development with"),
)
