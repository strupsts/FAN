from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, UploadFile

from app.application import ProcessReceiptCommand
from app.infrastructure import AppContainer, build_container

router = APIRouter(prefix="/api/receipts", tags=["receipts"])

_container = build_container()


def get_container() -> AppContainer:
    return _container


@router.post("/process")
async def process_receipt(
    file: UploadFile = File(...),
    container: AppContainer = Depends(get_container),
) -> dict:
    # Temporary fake user until auth is added.
    user_id: UUID = uuid4()

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
