from fastapi import APIRouter, Depends, HTTPException, Header, Query
from app.payments.schemas import PaymentCreate, PaymentResponse
from app.payments.service import payment_service
from app.deps import get_current_user
from app.validation import create_error_response
from app.storage import storage
from typing import List


router = APIRouter(tags=["payments"])


@router.post("", response_model=PaymentResponse, status_code=201)
async def create_payment(
    payment_data: PaymentCreate,
    user_id: str = Depends(get_current_user),
    idempotency_key: str = Header(..., alias="Idempotency-Key")
):
    """Create a new payment."""
    try:
        # Check idempotency
        body = payment_data.model_dump()
        idempotent_result = storage.check_idempotency(user_id, idempotency_key, "POST", "/api/v1/payments", body)
        if idempotent_result:
            status_code, response_body = idempotent_result
            if status_code == 409:
                raise HTTPException(status_code=409, detail=response_body)
            # Replay: return 200 with original response body
            return PaymentResponse(**response_body)
        
        payment_obj = payment_service.create_payment(
            from_user_id=user_id,
            to_handle=payment_data.to_handle,
            amount=payment_data.amount,
            note=payment_data.note,
            visibility=payment_data.visibility
        )
        
        from_user = storage.get_user_by_id(payment_obj.from_user_id)
        to_user = storage.get_user_by_id(payment_obj.to_user_id)
        
        response = PaymentResponse(
            payment_id=payment_obj.id,
            from_user_id=payment_obj.from_user_id,
            from_handle=from_user.handle if from_user else "",
            to_user_id=payment_obj.to_user_id,
            to_handle=to_user.handle if to_user else "",
            amount=payment_obj.amount,
            currency=storage.currency,
            note=payment_obj.note,
            visibility=payment_obj.visibility,
            request_id=payment_obj.request_id,
            created_at=payment_obj.created_at
        )
        
        # Store idempotency key
        storage.store_idempotency(user_id, idempotency_key, "POST", "/api/v1/payments", body, 201, response.model_dump())
        
        return response
    except HTTPException:
        raise
    except Exception as e:
        if hasattr(e, 'status_code'):
            raise HTTPException(status_code=e.status_code, detail=create_error_response(e.code, e.message))
        raise


@router.get("", response_model=list)
async def list_payments(
    user_id: str = Depends(get_current_user),
    limit: int = 50,
    offset: int = 0
):
    """List payments for the current user."""
    try:
        payments = storage.get_payments_for_user(user_id, limit, offset)
        result = []
        for p in payments:
            from_user = storage.get_user_by_id(p.from_user_id)
            to_user = storage.get_user_by_id(p.to_user_id)
            result.append(PaymentResponse(
                payment_id=p.id,
                from_user_id=p.from_user_id,
                from_handle=from_user.handle if from_user else "",
                to_user_id=p.to_user_id,
                to_handle=to_user.handle if to_user else "",
                amount=p.amount,
                currency=storage.currency,
                note=p.note,
                visibility=p.visibility,
                request_id=p.request_id,
                created_at=p.created_at
            ))
        return result
    except Exception as e:
        if hasattr(e, 'status_code'):
            raise HTTPException(status_code=e.status_code, detail=create_error_response(e.code, e.message))
        raise


@router.get("/activity")
async def get_activity(
    user_id: str = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """Get activity feed - payments visible to the caller."""
    try:
        payments = storage.get_activity_feed(user_id, limit, offset)
        result = []
        for p in payments:
            from_user = storage.get_user_by_id(p.from_user_id)
            to_user = storage.get_user_by_id(p.to_user_id)
            result.append(PaymentResponse(
                payment_id=p.id,
                from_user_id=p.from_user_id,
                from_handle=from_user.handle if from_user else "",
                to_user_id=p.to_user_id,
                to_handle=to_user.handle if to_user else "",
                amount=p.amount,
                currency=storage.currency,
                note=p.note,
                visibility=p.visibility,
                request_id=p.request_id,
                created_at=p.created_at
            ))
        return {"payments": result, "has_more": len(result) == limit}
    except Exception as e:
        if hasattr(e, 'status_code'):
            raise HTTPException(status_code=e.status_code, detail=create_error_response(e.code, e.message))
        raise