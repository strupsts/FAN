from __future__ import annotations

import time

from rq.job import Job

from API.redis.connection import queue_main
from API.redis import tasks as llm_tasks
from LLM.schemas_llm import LLMReceiptParseResult

LINES = [
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


def main() -> None:
    print("[TEST] enqueue LLM receipt job", flush=True)

    job: Job = queue_main.enqueue(
        llm_tasks.parse_receipt_llm,
        LINES,
        "en",
        256,
    )
    print("Job enqueued:", job.id)
    print("Polling status...\n", flush=True)

    while True:
        job.refresh()
        status = job.get_status()
        print("status:", status, flush=True)
        if status in ("finished", "failed", "canceled"):
            break
        time.sleep(0.5)

    print("\n=== FINAL JOB DATA ===")
    if job.is_failed:
        print("Job FAILED:")
        print(job.exc_info)
        return

    data = job.result
    print(data)

    result_dict = data.get("result") if isinstance(data, dict) else None
    if not result_dict:
        return

    receipt = LLMReceiptParseResult.model_validate(result_dict)

    print("\n--- Parsed items ---")
    for it in receipt.items:
        print(
            f"- {it.item_name_raw!r}, price={it.price}, "
            f"cat={it.category}, bucket={it.bucket}, "
            f"conf={it.confidence}, norm={it.norm_name!r}"
        )


if __name__ == "__main__":
    main()
