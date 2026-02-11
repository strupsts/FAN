from __future__ import annotations

from typing import Any, Dict, List, Optional

from rq.job import Job
from rq.exceptions import NoSuchJobError

from .connection import redis_conn, queue_main
from . import tasks


def enqueue_llm_receipt_job(
    *,
    lines: List[str],
    lang: str = "en",
    max_tokens: int = 256,
) -> str:
    """
    Поставить задачу парсинга чека в очередь fan-main.
    Возвращает job_id.
    """
    job: Job = queue_main.enqueue(
        tasks.parse_receipt_llm,
        lines,
        lang,
        max_tokens,
        job_timeout=120,
        result_ttl=3600,
    )
    return job.id


def get_job(job_id: str) -> Optional[Job]:
    """
    Попробовать вытащить job по id. Если нет — вернуть None.
    """
    try:
        return Job.fetch(job_id, connection=redis_conn)
    except NoSuchJobError:
        return None
