# app/redis/connection.py
from __future__ import annotations

from redis import Redis
from rq import Queue

REDIS_URL = "redis://127.0.0.1:6379/0"

redis_conn = Redis.from_url(REDIS_URL)

# основная очередь для FAN
queue_main = Queue("fan-main", connection=redis_conn)
