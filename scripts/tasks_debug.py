# app/redis/tasks_debug.py
from __future__ import annotations

import time
from typing import Any

from .connection import queue_main


def slow_echo(x: Any) -> str:
    print(f"[TASK] start slow_echo({x})")
    time.sleep(3)
    print(f"[TASK] done slow_echo({x})")
    return f"echo: {x}"


def enqueue_debug() -> None:
    job = queue_main.enqueue(slow_echo, "hello-from-FAN")
    print("Enqueued job:", job.id)


if __name__ == "__main__":
    enqueue_debug()
