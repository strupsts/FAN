from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile

from app.adapters.inbound.api.routes.receipt_schemas import (
    ConfirmReceiptRequest,
    ReceiptDraftResponse,
    ReceiptResponse,
    SpendingSummaryResponse,
    receipt_draft_to_response,
    receipt_to_response,
    summary_to_response,
)
from app.application import ConfirmReceiptCommand, ProcessReceiptCommand
from app.domain import Money
from app.infrastructure import AppContainer, build_container, get_settings

router = APIRouter(prefix="/api/receipts", tags=["receipts"])

_container = build_container()

# Temporary fake user until auth is added.
_FAKE_USER_ID = get_settings().dev_user_id


def get_container() -> AppContainer:
    return _container


def get_current_user_id() -> UUID:
    return _FAKE_USER_ID


@router.post("/process", response_model=ReceiptDraftResponse)
async def process_receipt(
    file: UploadFile = File(...),
    container: AppContainer = Depends(get_container),
    user_id: UUID = Depends(get_current_user_id),
) -> ReceiptDraftResponse:
    image_bytes = await file.read()

    command = ProcessReceiptCommand(
        user_id=user_id,
        image_bytes=image_bytes,
        original_filename=file.filename,
        content_type=file.content_type,
    )

    draft = container.process_receipt_use_case.execute(command)

    return receipt_draft_to_response(draft)


@router.post("/confirm", response_model=ReceiptResponse)
def confirm_receipt(
    request: ConfirmReceiptRequest,
    container: AppContainer = Depends(get_container),
    user_id: UUID = Depends(get_current_user_id),
) -> ReceiptResponse:
    command = ConfirmReceiptCommand(
        user_id=user_id,
        draft_id=request.draft_id,
        merchant_name=request.merchant_name,
        purchased_at=request.purchased_at,
        image_ref=request.image_ref,
        total=Money(
            amount=request.total_amount,
            currency=request.total_currency,
        ),
        items=[item.to_domain() for item in request.items],
    )

    confirmed_receipt = container.confirm_receipt_use_case.execute(command)

    return receipt_to_response(confirmed_receipt)


@router.get("/history", response_model=list[ReceiptResponse])
def get_receipt_history(
    container: AppContainer = Depends(get_container),
    user_id: UUID = Depends(get_current_user_id),
) -> list[ReceiptResponse]:
    receipts = container.get_receipt_history_use_case.execute(user_id=user_id)
    return [receipt_to_response(receipt) for receipt in receipts]


@router.get("/summary", response_model=SpendingSummaryResponse)
def get_receipt_summary(
    from_date: str,
    to_date: str,
    container: AppContainer = Depends(get_container),
    user_id: UUID = Depends(get_current_user_id),
) -> SpendingSummaryResponse:
    summary = container.get_spending_summary_use_case.execute(
        user_id=user_id,
        from_date=date.fromisoformat(from_date),
        to_date=date.fromisoformat(to_date),
    )

    return summary_to_response(summary)
