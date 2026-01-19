from fastapi import APIRouter

router = APIRouter(
    prefix="/portfolio",
    tags=["portfolio"],
)


@router.get("/{portfolio_id}")
def get_portfolio(portfolio_id: str):
    return {"portfolio_id": portfolio_id}


@router.post("/generate")
def generate_portfolio():
    return {"status": "portfolio generated"}


@router.post("/{portfolio_id}/edit")
def edit_portfolio(portfolio_id: str):
    return {"portfolio_id": portfolio_id, "status": "edited"}
