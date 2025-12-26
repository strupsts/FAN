from __future__ import annotations

import argparse
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from LLM.llm_core import LLMCore, LLMCoreConfig
from LLM.llm_receipt_parser import LLMReceiptParser


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


def one_call(host: str, model: str, max_tokens: int) -> float:
    # Важно: отдельный core+session на поток (requests.Session не гарантированно thread-safe)
    core = LLMCore(LLMCoreConfig(host=host, model=model, timeout_s=120, num_predict_default=max_tokens))
    parser = LLMReceiptParser(core=core)

    t0 = time.perf_counter()
    _result, _meta = parser.parse_and_classify_from_lines(
        lines=LINES,
        lang="en",
        debug=False,
        max_tokens=max_tokens,
    )
    return time.perf_counter() - t0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="http://127.0.0.1:8000")
    ap.add_argument("--model", default="qwen3-8b")
    ap.add_argument("--n", type=int, default=50, help="сколько запросов всего")
    ap.add_argument("--c", type=int, default=10, help="concurrency (параллельность)")
    ap.add_argument("--warmup", type=int, default=3)
    ap.add_argument("--max_tokens", type=int, default=256)
    args = ap.parse_args()

    # warmup (последовательно)
    for _ in range(args.warmup):
        one_call(args.host, args.model, args.max_tokens)

    lat = []
    errors = 0
    t_all = time.perf_counter()

    with ThreadPoolExecutor(max_workers=args.c) as ex:
        futs = [ex.submit(one_call, args.host, args.model, args.max_tokens) for _ in range(args.n)]
        for f in as_completed(futs):
            try:
                lat.append(f.result())
            except Exception as e:
                errors += 1
                print("[ERR]", repr(e))

    wall = time.perf_counter() - t_all

    if not lat:
        print("No successful requests.")
        return

    lat_sorted = sorted(lat)
    p50 = statistics.median(lat_sorted)
    p95 = lat_sorted[int(0.95 * (len(lat_sorted) - 1))]
    p99 = lat_sorted[int(0.99 * (len(lat_sorted) - 1))]
    avg = statistics.mean(lat_sorted)

    rps = len(lat) / wall

    print("\n=== BENCH RESULTS ===")
    print(f"ok={len(lat)} err={errors} total_wall={wall:.3f}s rps={rps:.2f}")
    print(f"avg={avg:.3f}s p50={p50:.3f}s p95={p95:.3f}s p99={p99:.3f}s min={lat_sorted[0]:.3f}s max={lat_sorted[-1]:.3f}s")


if __name__ == "__main__":
    main()
