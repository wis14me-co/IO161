from fastapi import APIRouter, Depends, HTTPException, Header, Query, Body
from typing import Optional, List
from datetime import datetime, timezone

from app.authorization.schemas import (
    AuthorizationCreate, AuthorizationResponse, AuthorizationListResponse,
    AuthorizationCapture
)
from app.authorization.service import authorization_service
from app.deps import get_current_user
from app.storage import storage
from app.models import PaymentResponse
from app.validation import create_error_response


def auth_to_response(auth) -> AuthorizationResponse:
    """Convert storage Authorization to AuthorizationResponse."""
    # Check if expired
    is_expired = False
    if auth.expires_at and auth.status == "open":
        try:
            expires = datetime.fromisoformat(auth.expires_at.replace("Z", "+00:00"))
            if expires <= datetime.now(timezone.utc):
                is_expired = True
        except ValueError:
            pass
    
    return AuthorizationResponse(
        id=auth.id,
        from_user_id=auth.from_user_id,
        to_user_id=auth.to_user_id,
        amount=auth.amount,
        captured_amount=auth.captured_amount,
        note=auth.note,
        visibility=auth.visibility,
        status=auth.status if not is_expired else "expired",
        expires_at=auth.expires_at or "",
        created_at=auth.created_at,
        remaining_amount=auth.amount - auth.captured_amount,
        payment_id=auth.payment_id,
        payment_ids=auth.payment_ids or []
    )


router = APIRouter(tags=["authorizations"])


@router.post("", response_model=AuthorizationResponse, status_code=201)
async def create_authorization(
    auth_data: AuthorizationCreate,
    user_id: str = Depends(get_current_user),
    idempotency_key: str = Header(..., alias="Idempotency-Key")
):
    """Create a new authorization."""
    try:
        auth = authorization_service.create_authorization(
            from_user_id=user_id,
            to_handle=auth_data.to_handle,
            amount=auth_data.amount,
            note=auth_data.note,
            visibility=auth_data.visibility,
            expires_at=auth_data.expires_at
        )
        return auth_to_response(auth)
    except Exception as e:
        if hasattr(e, 'status_code'):
            raise HTTPException(status_code=e.status_code, detail=create_error_response(e.code, e.message))
        raise


@router.post("/{auth_id}/void", response_model=AuthorizationResponse, status_code=200)
async def void_authorization(
    auth_id: str,
    user_id: str = Depends(get_current_user)
):
    """Void an authorization (payer only)."""
    try:
        auth = authorization_service.void_authorization(auth_id, user_id)
        return auth_to_response(auth)
    except Exception as e:
        if hasattr(e, 'status_code'):
            raise HTTPException(status_code=e.status_code, detail=create_error_response(e.code, e.message))
        raise


@router.post("/{auth_id}/capture", response_model=PaymentResponse, status_code=201)
async def capture_authorization(
    auth_id: str,
    capture_data: AuthorizationCapture = Body(default=AuthorizationCapture()),
    user_id: str = Depends(get_current_user),
    idempotency_key: str = Header(..., alias="Idempotency-Key")
):
    """Capture an authorization (receiver only)."""
    try:
        payment_obj, auth = authorization_service.capture_authorization(
            auth_id=auth_id,
            to_user_id=user_id,
            capture_data=capture_data
        )
        
        # Return the payment response as per spec
        from_user = storage.get_user_by_id(payment_obj.from_user_id)
        to_user = storage.get_user_by_id(payment_obj.to_user_id)
        
        return PaymentResponse(
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
    except Exception as e:
        if hasattr(e, 'status_code'):
            raise HTTPException(status_code=e.status_code, detail=create_error_response(e.code, e.message))
        raise


@router.get("", response_model=AuthorizationListResponse)
async def list_authorizations(
    user_id: str = Depends(get_current_user),
    direction: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """List authorizations for the current user."""
    try:
        return authorization_service.list_authorizations(user_id, direction, status, limit, offset)
    except Exception as e:
        if hasattr(e, 'status_code'):
            raise HTTPException(status_code=e.status_code, detail=create_error_response(e.code, e.message))
        raise