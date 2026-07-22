from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from starlette.concurrency import run_in_threadpool

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
from app.ports import (
    InvalidReceiptImageError,
    ReceiptDraftAlreadyConfirmedError,
    ReceiptDraftNotFoundError,
    ReceiptExtractionError,
    ReceiptExtractorResponseError,
    ReceiptExtractorUnavailableError,
)


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

    if not image_bytes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded receipt image is empty.",
        )

    command = ProcessReceiptCommand(
        user_id=user_id,
        image_bytes=image_bytes,
        original_filename=file.filename,
        content_type=file.content_type,
    )

    try:
        draft = await run_in_threadpool(
            container.process_receipt_use_case.execute,
            command,
        )
    except InvalidReceiptImageError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded file is not a supported receipt image.",
        ) from error
    except ReceiptExtractorUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Receipt extraction service is temporarily unavailable.",
            headers={"Retry-After": "5"},
        ) from error
    except ReceiptExtractorResponseError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Receipt extraction service returned an invalid response.",
        ) from error
    except ReceiptExtractionError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Receipt extraction failed.",
        ) from error

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
        subtotal=(
            Money(
                amount=request.subtotal_amount,
                currency=request.subtotal_currency,
            )
            if request.subtotal_amount is not None
            else None
        ),
        tax=(
            Money(
                amount=request.tax_amount,
                currency=request.tax_currency,
            )
            if request.tax_amount is not None
            else None
        ),
        image_ref=request.image_ref,
        total=Money(
            amount=request.total_amount,
            currency=request.total_currency,
        ),
        items=[item.to_domain() for item in request.items],
    )

    try:
        confirmed_receipt = (
            container.confirm_receipt_use_case.execute(command)
        )
    except ReceiptDraftNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Receipt draft was not found.",
        ) from error
    except ReceiptDraftAlreadyConfirmedError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Receipt draft has already been confirmed.",
        ) from error

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
