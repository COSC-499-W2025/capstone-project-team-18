from fastapi import APIRouter

router = APIRouter(
    prefix="",
    tags=["privacy"],
)


@router.post("/privacy-consent")
def privacy_consent():
    return {"status": "consent recorded"}
