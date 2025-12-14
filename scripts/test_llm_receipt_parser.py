# scripts/test_llm_receipt_parser.py

from LLM.llm_receipt_parser import LLMReceiptParser


def main() -> None:
    parser = LLMReceiptParser()

    # Тут пока руками вставляем строки.
    # Можно взять те, что tesseract выдавал по Shoppers чекy.
    lines = [
        "SHOPPERS DRUG MART",
        "FAYAZ RAJA PHARMACY INC",
        "B121-118th Avenue EDMONTON AB",
        "Deo 10, 2025 9:32 PM",
        "RX AM 4 9370 1001 379646",
        "SOME MEDICINE 29.52",
        "13.25",
        "SOME Antibiotics",
        "SUBTOTAL 29.52",
        "TOTAL 29.52",
        "VISA 29.52",
        "CUSTOMER COPY",
    ]

    result = parser.parse_from_lines(lines=lines, lang="en")

    print("\n=== PARSED RECEIPT ===")
    print("merchant:", result.merchant)
    print("lang    :", result.lang)
    print("items:")
    for it in result.items:
        print(f"  - {it.item_name_raw!r}  price={it.price}")
    print("raw_total_guess:", result.raw_total_guess)


if __name__ == "__main__":
    main()
