"""
This is the entry point for the API.

To run the api in development, run:
> fastapi dev ./src/interface/api/api.py

For a more interactive experience, go to
http:http://127.0.0.1:<port>/docs
"""

from fastapi import FastAPI

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


@app.get("/ping")
def ping_pong():
    return "pong"


# Register routers
app.include_router(projects)
app.include_router(resume)
app.include_router(portfolio)
app.include_router(skills)
app.include_router(privacy)
