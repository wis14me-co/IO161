from fastapi import APIRouter, Depends, HTTPException, Query, Header, Body
from typing import Optional, List
from pydantic import BaseModel
from app.deps import get_current_user
from app.storage import storage
from app.validation import create_error_response

class RequestCreate(BaseModel):
    to_handle: str
    amount: int
    note: str = ""


class PayRequest(BaseModel):
    visibility: str = "private"


router = APIRouter(tags=["requests"])


@router.post("", status_code=201)
async def create_request(
    request_data: RequestCreate = Body(...),
    user_id: str = Depends(get_current_user),
    idempotency_key: str = Header(..., alias="Idempotency-Key")
):
    """Create a new payment request."""
    try:
        payer = storage.get_user_by_handle(request_data.to_handle)
        if not payer:
            raise HTTPException(status_code=404, detail=create_error_response("not_found", "User not found"))
        if payer.id == user_id:
            raise HTTPException(status_code=400, detail=create_error_response("validation_failed", "Cannot request from yourself"))
        
        request = storage.create_request(
            requester_id=user_id,
            payer_id=payer.id,
            amount=request_data.amount,
            note=request_data.note
        )
        
        return {
            "request_id": request.id,
            "requester_id": request.requester_id,
            "payer_id": request.payer_id,
            "amount": request.amount,
            "note": request.note,
            "status": request.status,
            "created_at": request.created_at
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=create_error_response("internal_error", str(e)))


@router.get("")
async def list_requests(
    direction: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user_id: str = Depends(get_current_user)
):
    """List payment requests for the current user."""
    try:
        requests = storage.get_requests_for_user(user_id, direction, status, limit, offset)
        result = []
        for r in requests:
            requester = storage.get_user_by_id(r.requester_id)
            payer = storage.get_user_by_id(r.payer_id)
            result.append({
                "request_id": r.id,
                "requester_id": r.requester_id,
                "requester_handle": requester.handle if requester else "",
                "payer_id": r.payer_id,
                "payer_handle": payer.handle if payer else "",
                "amount": r.amount,
                "note": r.note,
                "status": r.status,
                "payment_id": r.payment_id,
                "created_at": r.created_at
            })
        return {"requests": result, "has_more": len(result) == limit}
    except Exception as e:
        raise HTTPException(status_code=500, detail=create_error_response("internal_error", str(e)))


@router.post("/{request_id}/pay")
async def pay_request(
    request_id: str,
    visibility: str = "private",
    user_id: str = Depends(get_current_user),
    idempotency_key: str = Header(..., alias="Idempotency-Key")
):
    """Pay a payment request (payer only)."""
    try:
        request = storage.get_request(request_id)
        if not request:
            raise HTTPException(status_code=404, detail=create_error_response("not_found", "Request not found"))
        if request.payer_id != user_id:
            raise HTTPException(status_code=403, detail=create_error_response("forbidden", "Only payer can pay request"))
        if request.status != "pending":
            raise HTTPException(status_code=400, detail=create_error_response("validation_failed", "Request not pending"))
        
        requester = storage.get_user_by_id(request.requester_id)
        payer = storage.get_user_by_id(request.payer_id)
        
        # Atomic transfer
        storage.atomic_transfer(payer.id, requester.id, request.amount)
        
        # Create payment
        payment = storage.create_payment(
            from_user_id=payer.id,
            to_user_id=requester.id,
            amount=request.amount,
            note=request.note,
            visibility=visibility,
            request_id=request.id
        )
        
        # Update request status
        storage.update_request_status(request_id, "paid", payment.id)
        
        return {
            "payment_id": payment.id,
            "from_user_id": payment.from_user_id,
            "from_handle": payer.handle,
            "to_user_id": payment.to_user_id,
            "to_handle": requester.handle,
            "amount": payment.amount,
            "currency": storage.currency,
            "note": payment.note,
            "visibility": payment.visibility,
            "request_id": payment.request_id,
            "created_at": payment.created_at
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=create_error_response("internal_error", str(e)))


@router.post("/{request_id}/decline")
async def decline_request(
    request_id: str,
    user_id: str = Depends(get_current_user)
):
    """Decline a payment request (payer only)."""
    try:
        request = storage.get_request(request_id)
        if not request:
            raise HTTPException(status_code=404, detail=create_error_response("not_found", "Request not found"))
        if request.payer_id != user_id:
            raise HTTPException(status_code=403, detail=create_error_response("forbidden", "Only payer can decline request"))
        if request.status != "pending":
            raise HTTPException(status_code=400, detail=create_error_response("validation_failed", "Request not pending"))
        
        storage.update_request_status(request_id, "declined")
        return {"status": "declined"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=create_error_response("internal_error", str(e)))


@router.post("/{request_id}/cancel")
async def cancel_request(
    request_id: str,
    user_id: str = Depends(get_current_user)
):
    """Cancel a payment request (requester only)."""
    try:
        request = storage.get_request(request_id)
        if not request:
            raise HTTPException(status_code=404, detail=create_error_response("not_found", "Request not found"))
        if request.requester_id != user_id:
            raise HTTPException(status_code=403, detail=create_error_response("forbidden", "Only requester can cancel request"))
        if request.status != "pending":
            raise HTTPException(status_code=400, detail=create_error_response("validation_failed", "Request not pending"))
        
        storage.update_request_status(request_id, "cancelled")
        return {"status": "cancelled"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=create_error_response("internal_error", str(e)))