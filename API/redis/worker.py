# app/redis/worker.py
from __future__ import annotations

from rq import Worker
from .connection import redis_conn, queue_main


def main() -> None:
    # воркер, который слушает очередь "fan-main"
    worker = Worker([queue_main], connection=redis_conn)
    worker.work(with_scheduler=True)


if __name__ == "__main__":
    main()
