from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, UploadFile

from app.adapters.inbound.api.routes.receipt_schemas import (
    ConfirmReceiptRequest,
    MoneyResponse,
    receipt_to_response,
)
from app.application import ConfirmReceiptCommand, ProcessReceiptCommand
from app.domain import Money
from app.infrastructure import AppContainer, build_container

router = APIRouter(prefix="/api/receipts", tags=["receipts"])

_container = build_container()

# Temporary fake user until auth is added.
_FAKE_USER_ID = uuid4()


def get_container() -> AppContainer:
    return _container


def get_current_user_id() -> UUID:
    return _FAKE_USER_ID


@router.post("/process")
async def process_receipt(
    file: UploadFile = File(...),
    container: AppContainer = Depends(get_container),
    user_id: UUID = Depends(get_current_user_id),
) -> dict:
    image_bytes = await file.read()

    command = ProcessReceiptCommand(
        user_id=user_id,
        image_bytes=image_bytes,
        original_filename=file.filename,
        content_type=file.content_type,
    )

    draft = container.process_receipt_use_case.execute(command)

    return {
        "id": str(draft.id),
        "merchant_name": draft.merchant_name,
        "total": {
            "amount": str(draft.total.amount) if draft.total else None,
            "currency": draft.total.currency if draft.total else None,
        },
        "items": [
            {
                "name": item.name,
                "total_price": {
                    "amount": str(item.total_price.amount),
                    "currency": item.total_price.currency,
                },
                "category": item.category.value,
                "bucket": item.bucket.value,
                "confidence": item.confidence,
            }
            for item in draft.items
        ],
        "image_ref": draft.image_ref,
        "parser_name": draft.parser_name,
    }


@router.post("/confirm")
def confirm_receipt(
    request: ConfirmReceiptRequest,
    container: AppContainer = Depends(get_container),
    user_id: UUID = Depends(get_current_user_id),
) -> dict:
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

    return receipt_to_response(confirmed_receipt).model_dump()


@router.get("/history")
def get_receipt_history(
    container: AppContainer = Depends(get_container),
    user_id: UUID = Depends(get_current_user_id),
) -> list[dict]:
    receipts = container.get_receipt_history_use_case.execute(user_id=user_id)
    return [receipt_to_response(receipt).model_dump() for receipt in receipts]


@router.get("/summary")
def get_receipt_summary(
    from_date: str,
    to_date: str,
    container: AppContainer = Depends(get_container),
    user_id: UUID = Depends(get_current_user_id),
) -> dict:
    from datetime import date

    summary = container.get_spending_summary_use_case.execute(
        user_id=user_id,
        from_date=date.fromisoformat(from_date),
        to_date=date.fromisoformat(to_date),
    )

    return {
        "from_date": summary.from_date.isoformat(),
        "to_date": summary.to_date.isoformat(),
        "total_spent": MoneyResponse(
            amount=str(summary.total_spent.amount),
            currency=summary.total_spent.currency,
        ).model_dump(),
        "by_category": [
            {
                "category": item.category.value,
                "total": {
                    "amount": str(item.total.amount),
                    "currency": item.total.currency,
                },
                "transaction_count": item.transaction_count,
            }
            for item in summary.by_category
        ],
        "by_merchant": [
            {
                "merchant_name": item.merchant_name,
                "total": {
                    "amount": str(item.total.amount),
                    "currency": item.total.currency,
                },
                "transaction_count": item.transaction_count,
            }
            for item in summary.by_merchant
        ],
    }
