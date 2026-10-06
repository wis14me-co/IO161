from fastapi import APIRouter, HTTPException, Body
from typing import Optional, Dict, Any
from pydantic import BaseModel
from app.storage import storage
from app.models import Fixture

router = APIRouter()


@router.post("/_test/reset")
async def reset_state(fixture: Optional[Fixture] = Body(default=None)):
    """Reset the service state with an optional fixture."""
    try:
        if fixture:
            errors = storage.validate_fixture(fixture)
            if errors:
                raise HTTPException(status_code=422, detail={"code": "validation_failed", "message": "; ".join(errors)})
        storage.reset(fixture)
        return {"status": "ok"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail={"code": "internal_error", "message": str(e)})


@router.get("/_test/export")
async def export_state():
    """Export the current service state."""
    try:
        return {"track": "pocketful", "format_version": 1, "state": storage.export_state()}
    except Exception as e:
        raise HTTPException(status_code=500, detail={"code": "internal_error", "message": str(e)})


@router.post("/_test/import")
async def import_state(state: Dict[str, Any] = Body(...)):
    """Import a previously exported service state."""
    try:
        # Handle both full export format and bare state format
        if "state" in state and "track" in state:
            storage.import_state(state["state"])
        else:
            storage.import_state(state)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail={"code": "internal_error", "message": str(e)})