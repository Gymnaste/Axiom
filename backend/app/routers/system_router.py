from fastapi import APIRouter, Depends
from app.config import APP_NAME, APP_VERSION
from app.core.auth_deps import get_current_user_id

router = APIRouter(prefix="/system", tags=["System"])

@router.get("/health")
def health():
    return {"status": "healthy", "app": APP_NAME, "version": APP_VERSION}
