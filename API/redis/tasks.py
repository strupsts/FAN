from __future__ import annotations

from typing import Any, Dict, List, Tuple

from LLM.llm_receipt_parser import LLMReceiptParser

# Один экземпляр парсера на воркер
_parser = LLMReceiptParser()


def parse_receipt_llm(
    lines: List[str],
    lang: str = "en",
    max_tokens: int = 256,
) -> Dict[str, Any]:
    """
    RQ-таск: дергает LLMReceiptParser и возвращает dict с result + meta.
    """

    result, meta = _parser.parse_and_classify_from_lines(
        lines=lines,
        lang=lang,
        max_tokens=max_tokens,
        debug=False,
    )

    # result — это Pydantic-модель LLMReceiptParseResult
    return {
        "result": result.model_dump(),
        "meta": meta,
    }
