from fastapi import APIRouter, Depends, HTTPException, Header, Body
from typing import List

from app.settlement.schemas import SettlementCreate, SettlementResponse
from app.settlement.service import settlement_service
from app.auth import get_current_user
from app.validation import create_error_response


router = APIRouter(tags=["settlements"])


@router.post("", response_model=SettlementResponse, status_code=201)
async def create_settlement(
    settlement: SettlementCreate,
    user_id: str = Depends(get_current_user),
    idempotency_key: str = Header(..., alias="Idempotency-Key")
):
    """Create an atomic net settlement."""
    try:
        settlement_id, committed_at, created_payments = settlement_service.execute_settlement(
            user_id,
            [t.model_dump() for t in settlement.transfers]
        )
        return settlement_service.build_response(settlement_id, committed_at, created_payments)
    except Exception as e:
        if hasattr(e, 'status_code'):
            raise HTTPException(status_code=e.status_code, detail=create_error_response(e.code, e.message))
        raise


@router.get("/operators")
async def list_operators():
    """List settlement operator IDs (for testing)."""
    from app.storage import storage
    return {"operators": storage.settlement_operator_ids}