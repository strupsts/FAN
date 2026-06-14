from __future__ import annotations

from app.adapters.outbound.llm.vllm_receipt_parser_adapter import VLLMReceiptParserAdapter
from app.infrastructure.config import get_settings
from app.ports import OCRLine, OCRResult


def main() -> None:
    settings = get_settings()

    parser = VLLMReceiptParserAdapter(
        base_url=settings.vllm_base_url,
        api_key=settings.vllm_api_key,
        model=settings.vllm_model,
        timeout_seconds=settings.vllm_timeout_seconds,
        temperature=settings.vllm_temperature,
        max_tokens=settings.vllm_max_tokens,
    )

    ocr_result = OCRResult(
        full_text="FAKE STORE\nMILK 4.29\nBREAD 3.49\nTOTAL 7.78",
        lines=[
            OCRLine(text="FAKE STORE", confidence=0.99),
            OCRLine(text="MILK 4.29", confidence=0.95),
            OCRLine(text="BREAD 3.49", confidence=0.95),
            OCRLine(text="TOTAL 7.78", confidence=0.98),
        ],
        engine_name="manual_test_ocr",
    )

    draft = parser.parse_receipt(
        ocr_result=ocr_result,
        image_ref="local://manual-test.jpg",
    )

    print("Parser:", draft.parser_name)
    print("Merchant:", draft.merchant_name)
    print("Total:", draft.total)
    print("Items:")

    for item in draft.items:
        print(
            f"- {item.name} | {item.total_price.amount} {item.total_price.currency} | "
            f"{item.category} | {item.bucket} | confidence={item.confidence}"
        )


if __name__ == "__main__":
    main()
