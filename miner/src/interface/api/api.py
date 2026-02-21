"""
This is the entry point for the API.

To run the api in development, run:
> fastapi dev ./src/interface/api/api.py

For a more interactive experience, go to
http:http://127.0.0.1:<port>/docs
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from sqlmodel import SQLModel

from src.utils.errors import KeyNotFoundError
from src.database.core.base import get_engine
from src.interface.api.routers import (
    projects,
    resume,
    portfolio,
    skills,
    user_config,
)

app = FastAPI(
    title="Capstone Project API",
    version="1.0.0",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Commands to run on startup
    SQLModel.metadata.create_all(get_engine())

    yield

    # Anything to be cleaned up after the app

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
app.include_router(projects)
app.include_router(resume)
app.include_router(portfolio)
app.include_router(skills)
app.include_router(user_config)


# Error handlers. If these errors are ever raised in our code, return the following JSON
@app.exception_handler(KeyNotFoundError)
async def key_not_found_exception_handler(request: Request, exc: KeyNotFoundError):
    return JSONResponse(
        status_code=404,
        content={"error_code": exc.error_code, "message": str(exc)},
    )


@app.exception_handler(Exception)
async def universal_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"message": "An internal error occurred", "details": str(exc)},
    )
