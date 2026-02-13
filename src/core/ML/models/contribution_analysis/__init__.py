
"""

ML-based contribution analysis models.

"""



from .commit_classifier import CommitClassifier
from .pattern_detector import PatternDetector, WorkPattern
from .role_analyzer import RoleAnalyzer, CollaborationRole
from .summary_generator import (
    generate_signature,
    build_signature_facts,
    resolve_experience_stage_with_ml,
)
from .project_summary_generator import (
    generate_project_summary,
    build_project_summary_facts,
    configure_project_summary_run,
)



__all__ = [

    "CommitClassifier",

    "PatternDetector",

    "WorkPattern",

    "RoleAnalyzer",
    "CollaborationRole",
    "generate_signature",
    "build_signature_facts",
    "resolve_experience_stage_with_ml",
    "generate_project_summary",
    "build_project_summary_facts",
    "configure_project_summary_run",
]
