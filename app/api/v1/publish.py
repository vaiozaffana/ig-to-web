from fastapi import APIRouter

router = APIRouter(prefix="/publish", tags=["publish"])


@router.get("/status")
def publish_status() -> dict[str, str]:
    return {"status": "mock-adapter-ready"}
