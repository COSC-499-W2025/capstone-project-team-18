"""
Routers allows us to organize our endpoints by domain.
Each router groups related endpoints together and can be
mounted onto the actual FastAPI app.

The routers are re-exported here to provide a clean and consistent import
surface for the API entry point.
"""

from src.interface.api.routers.projects import router as projects
from src.interface.api.routers.resume import router as resume
from src.interface.api.routers.portfolio import router as portfolio
from src.interface.api.routers.skills import router as skills
from src.interface.api.routers.privacy import router as privacy

__all__ = [
    "projects",
    "resume",
    "portfolio",
    "skills",
    "privacy",
]
