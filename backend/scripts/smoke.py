from uuid import uuid4

from app.application import ProcessReceiptCommand
from app.infrastructure import build_container


def main() -> None:
    container = build_container()

    command = ProcessReceiptCommand(
        user_id=uuid4(),
        image_bytes=b"fake image bytes",
        original_filename="receipt.jpg",
        content_type="image/jpeg",
    )

    draft = container.process_receipt_use_case.execute(command)

    print(draft.merchant_name)
    print(draft.total)
    print([item.name for item in draft.items])
    print([event.name for event in container.analytics.events])
    print(len(container.prediction_repository.predictions))


if __name__ == "__main__":
    main()
