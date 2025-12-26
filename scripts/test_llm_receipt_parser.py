from LLM.llm_receipt_parser import LLMReceiptParser


def main() -> None:
    print("[TEST] start receipt parse+classify", flush=True)
    parser = LLMReceiptParser()

    lines = [
        "SHOPPERS DRUG MART",
        "FAYAZ RAJA PHARMACY INC",
        "B121-118th Avenue EDMONTON AB",
        "Dec 10, 2025 9:32 PM",
        "SOME MEDICINE 29.52",
        "13.25",
        "SOME Antibiotics",
        "SUBTOTAL 29.52",
        "TOTAL 29.52",
        "VISA 29.52",
        "CUSTOMER COPY",
    ]

    result, meta = parser.parse_and_classify_from_lines(
        lines=lines,
        lang="en",
        debug=True,
        max_tokens=256,
    )

    print("\n=== PARSED + CLASSIFIED RECEIPT ===", flush=True)
    print("merchant:", result.merchant, flush=True)
    print("lang    :", result.lang, flush=True)
    print("raw_total_guess:", result.raw_total_guess, flush=True)
    print("items:", flush=True)

    for it in result.items:
        print(
            f"  - {it.item_name_raw!r} price={it.price} | "
            f"cat={getattr(it, 'category', None)} "
            f"bucket={getattr(it, 'bucket', None)} "
            f"conf={getattr(it, 'confidence', None)} "
            f"norm={getattr(it, 'norm_name', None)!r}",
            flush=True,
        )

    print("\nMETA:", meta, flush=True)


if __name__ == "__main__":
    main()
