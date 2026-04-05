"""
This is the entry point for the API.

To run the api in development, run:
> fastapi dev ./src/interface/api/api.py

For a more interactive experience, go to
http:http://127.0.0.1:<port>/docs
"""

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from src.utils.errors import (
    KeyNotFoundError,
    ProjectNotFoundError,
    ResumeNotFoundError,
    UserConfigNotFoundError,
    AIServiceUnavailableError,
    DatabaseOperationError,
    BadOAuthStateError,
    ExpiredOAuthState
)
from src.app import init_system, _init_db
from src.interface.api.routers.projects import router as projects_router
from src.interface.api.routers.resume import router as resume_router
from src.interface.api.routers.portfolio import router as portfolio_router
from src.interface.api.routers.skills import router as skills_router
from src.interface.api.routers.user_config import router as user_config_router
from src.interface.api.routers.job_readiness import router as job_readiness_router
from src.interface.api.routers.insights import router as insights_router
from src.interface.api.routers.interview import router as interview_router
from src.interface.api.routers.github import router as github_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Commands to run on startup
    _init_db()  # Create database tables first
    init_system()

    yield

    # Anything to be cleaned up after the app

app = FastAPI(
    title="Capstone Project API",
    version="1.0.0",
    description=(
        "Backend API for the developer portfolio and resume builder application. "
        "Provides endpoints for ingesting and analyzing project archives, generating "
        "resumes and portfolios, running AI-powered job-readiness assessments, "
        "conducting mock interviews, and managing GitHub OAuth. "
        "\n\n"
        "**Base URL (development):** `http://127.0.0.1:8000`  \n"
        "**Interactive docs:** `http://127.0.0.1:8000/docs`  \n"
        "\n\n"
        "### Error Response Format\n"
        "Most errors return a JSON body with `error_code` and `message` fields:\n"
        "```json\n"
        '{ "error_code": "PROJECT_NOT_FOUND", "message": "..." }\n'
        "```\n"
        "Generic 500 errors return `{ \"message\": \"...\", \"details\": \"...\" }` instead.\n"
        "\n\n"
        "### Authentication/ Security\n"
        "The backend and frontend of the system are meant to run locally in parallel on"
        "the user's computer. This means, there is no authentication required to the API"
        "as the only requests that can arrive to the API come from the user themselves."
        "\n\n"
        "### ML Consent\n"
        "Endpoints that call Azure OpenAI (job-readiness, interview, ML-based insights) "
        "require `ml_consent=true` in the user configuration. Calls without consent "
        "return `503 AI_SERVICE_UNAVAILABLE`."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/ping")
def ping_pong():
    return "pong"


# Register routers
app.include_router(projects_router)
app.include_router(resume_router)
app.include_router(portfolio_router)
app.include_router(skills_router)
app.include_router(user_config_router)
app.include_router(job_readiness_router)
app.include_router(insights_router)
app.include_router(interview_router)
app.include_router(github_router)

# Error handlers. If these errors are ever raised in our code, return the following JSON


@app.exception_handler(KeyNotFoundError)
async def key_not_found_exception_handler(request: Request, exc: KeyNotFoundError):
    return JSONResponse(
        status_code=404,
        content={"error_code": exc.error_code, "message": str(exc)},
    )


@app.exception_handler(ProjectNotFoundError)
async def project_not_found_exception_handler(request: Request, exc: ProjectNotFoundError):
    return JSONResponse(
        status_code=404,
        content={"error_code": exc.error_code, "message": str(exc)},
    )


@app.exception_handler(ResumeNotFoundError)
async def resume_not_found_exception_handler(request: Request, exc: ResumeNotFoundError):
    return JSONResponse(
        status_code=404,
        content={"error_code": exc.error_code, "message": str(exc)},
    )


@app.exception_handler(UserConfigNotFoundError)
async def user_config_not_found_exception_handler(request: Request, exc: UserConfigNotFoundError):
    return JSONResponse(
        status_code=404,
        content={"error_code": exc.error_code, "message": str(exc)},
    )


@app.exception_handler(AIServiceUnavailableError)
async def ai_service_unavailable_exception_handler(request: Request, exc: AIServiceUnavailableError):
    return JSONResponse(
        status_code=503,
        content={"error_code": exc.error_code, "message": str(exc)},
    )


@app.exception_handler(DatabaseOperationError)
async def database_operation_error_handler(request: Request, exc: DatabaseOperationError):
    return JSONResponse(
        status_code=500,
        content={"error_code": exc.error_code, "message": str(exc)},
    )


@app.exception_handler(BadOAuthStateError)
async def bad_oauth_state_error_handler(request: Request, exc: BadOAuthStateError):
    return JSONResponse(
        status_code=404,
        content={"error_code": exc.error_code, "message": str(exc)}
    )


@app.exception_handler(ExpiredOAuthState)
async def expired_oauth_state_error_handler(request: Request, exc: BadOAuthStateError):
    return JSONResponse(
        status_code=410,
        content={"error_code": exc.error_code, "message": str(exc)}
    )


@app.exception_handler(Exception)
async def universal_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"message": "An internal error occurred", "details": str(exc)},
    )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
