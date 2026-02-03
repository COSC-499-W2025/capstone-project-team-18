"""
This is the entry point for the API.

To run the api in development, run:
> fastapi dev ./src/interface/api/api.py

For a more interactive experience, go to
http:http://127.0.0.1:<port>/docs
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.interface.api.routers import (
    projects,
    resume,
    portfolio,
    skills,
    privacy,
)

app = FastAPI(
    title="Capstone Project API",
    version="1.0.0",
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
app.include_router(projects)
app.include_router(resume)
app.include_router(portfolio)
app.include_router(skills)
app.include_router(privacy)
