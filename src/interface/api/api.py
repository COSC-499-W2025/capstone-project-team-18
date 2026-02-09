"""
This is the entry point for the API.

To run the api in development, run:
> fastapi dev ./src/interface/api/api.py

For a more interactive experience, go to
http:http://127.0.0.1:<port>/docs
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from sqlmodel import SQLModel
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
