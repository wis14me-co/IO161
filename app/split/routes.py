from fastapi import APIRouter, Depends, HTTPException, Header, Body
from typing import List
from pydantic import BaseModel
from app.deps import get_current_user
from app.storage import storage
from app.validation import create_error_response


class SplitCreate(BaseModel):
    amount: int
    participant_handles: List[str]
    note: str = ""


router = APIRouter(tags=["split"])


@router.post("", status_code=201)
async def create_split(
    split_data: SplitCreate = Body(...),
    user_id: str = Depends(get_current_user),
    idempotency_key: str = Header(..., alias="Idempotency-Key")
):
    """Create a split bill among participants."""
    try:
        amount = split_data.amount
        handles = split_data.participant_handles
        note = split_data.note
        
        # Verify all handles exist
        participant_users = []
        for handle in handles:
            user = storage.get_user_by_handle(handle)
            if not user:
                raise HTTPException(status_code=404, detail=create_error_response("not_found", f"User with handle '{handle}' not found"))
            participant_users.append(user)
        
        # Calculate shares per spec §9 - equal split with remainder to first participants
        n = len(participant_users)
        base = amount // n
        remainder = amount % n
        shares = [base + (1 if i < remainder else 0) for i in range(n)]
        
        # Create requests from each participant to the caller
        from app.models import SplitShare
        split_shares = [SplitShare(handle=user.handle, amount=shares[i]) for i, user in enumerate(participant_users)]
        
        requests = []
        for i, user in enumerate(participant_users):
            if user.id != user_id:  # Don't create request from caller to themselves
                req = storage.create_request(
                    requester_id=user_id,
                    payer_id=user.id,
                    amount=shares[i],
                    note=note
                )
                requests.append(req)
        
        split_id = storage.create_split(user_id, amount, handles, note, split_shares, requests)
        
        return {
            "split_id": split_id,
            "amount": amount,
            "currency": storage.currency,
            "note": note,
            "shares": [{"handle": s.handle, "amount": s.amount} for s in split_shares],
            "requests": [
                {
                    "request_id": r.id,
                    "requester_id": r.requester_id,
                    "requester_handle": storage.get_user_by_id(r.requester_id).handle if storage.get_user_by_id(r.requester_id) else "",
                    "payer_id": r.payer_id,
                    "payer_handle": storage.get_user_by_id(r.payer_id).handle if storage.get_user_by_id(r.payer_id) else "",
                    "amount": r.amount,
                    "note": r.note,
                    "status": r.status,
                    "created_at": r.created_at
                } for r in requests
            ],
            "created_at": storage._now_iso()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=create_error_response("internal_error", str(e)))