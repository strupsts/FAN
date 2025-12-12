# scripts/test_llm_classifier.py

from categorybrain.llm_classifier import LLMClassifier
from schemas_llm import LLMItemRequest


def main() -> None:
    clf = LLMClassifier()

    examples = [
        LLMItemRequest(
            merchant="Walmart",
            item_name_raw="Milk 2L",
            price=3.99,
            lang="en",
        ),
        LLMItemRequest(
            merchant="McDonalds",
            item_name_raw="Big Mac combo",
            price=11.99,
            lang="en",
        ),
        LLMItemRequest(
            merchant="Starbucks",
            item_name_raw="Latte grande",
            price=5.95,
            lang="en",
        ),
        LLMItemRequest(
            merchant="Canadian Tire",
            item_name_raw="Motor oil 5W-30",
            price=34.99,
            lang="en",
        ),
        LLMItemRequest(
            merchant="Пятёрочка",
            item_name_raw="Молоко 2л",
            price=120.0,
            lang="ru",
        ),
    ]

    for req in examples:
        resp = clf.classify_item(req)
        print(
            f"{req.merchant:12} | {req.item_name_raw:25} -> "
            f"{resp.category:12} | {resp.bucket:6} | conf={resp.confidence:.2f}"
        )


if __name__ == "__main__":
    main()
