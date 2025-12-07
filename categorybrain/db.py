from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable
from typing import List, Dict, Any
from datetime import datetime

import psycopg2
from psycopg2.extras import RealDictCursor


# Connection config

@dataclass
class DbConfig: 
    host: str = "localhost"
    port: int = 5432
    dbname: str = "categorybrain"
    user: str = "postgres"  
    password: str = "ninufi12"

def get_connection(cfg: DbConfig | None = None):
    """
    Opens connection with the Postgres and return object "connection"
    """
    if cfg is None: 
        cfg = DbConfig()

    conn = psycopg2.connect(
        host = cfg.host,
        port = cfg.port,
        dbname = cfg.dbname,
        user = cfg.user,
        password = cfg.password
    )
    return conn
    


# --- Model of entry data for saving a receipt ---

@dataclass
class ReceiptItemInput: 
    merchant: str
    item_name: str
    price: float
    category: str
    bucket: str
    confidence: float 

def save_receipt(
        user_id: int,
        items: Iterable[ReceiptItemInput],
        source: str = "manual",
        cfg: DbConfig | None = None
) -> int: 
    """
    Creates record in receipts and bounded records in receipt_items.
    returns id of created receipt in DB.
    """
    if cfg is None:
        cfg = DbConfig()

    items = list(items)
    if not items:
        raise ValueError("Impossible to save empty receipt (items is empty)")

    total_amount = sum(float(it.price) for it in items)

    # merchant чека — берём из первого айтема
    receipt_merchant = items[0].merchant

    # проверим, что во всех позициях одного чека merchant один и тот же
    for it in items:
        if it.merchant != receipt_merchant:
            raise ValueError(
                f"Все позиции чека должны быть с одним merchant. "
                f"Нашёл '{it.merchant}', ожидалось '{receipt_merchant}'."
            )

    conn = get_connection(cfg)
    try: 
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 1) Create a receipt 
                cur.execute (
                    """
                    INSERT INTO receipts (user_id, total_amount, source, merchant)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id;
                    """,
                    (user_id, total_amount, source, receipt_merchant)
                )       
                row = cur.fetchone()
                receipt_id = int(row["id"])

                # 2) Insert a rows of receipts
                for it in items: 
                    cur.execute(
                       """
                        INSERT INTO receipt_items
                            (receipt_id, merchant, item_name, price, category, bucket, confidence)
                        VALUES
                            (%s, %s, %s, %s, %s, %s, %s);
                        """,
                        (
                            receipt_id,
                            it.merchant, 
                            it.item_name,
                            float(it.price),
                            it.category,
                            it.bucket,
                            float(it.confidence)
                        )
                    )
                      
        # if everything is smooth, transaction commits automatically (because of `with conn: `)
        return receipt_id
    finally: 
        conn.close()


def list_receipts(
        user_id: int,
        limit: int = 50,
        cfg: DbConfig | None = None
) -> List[Dict[str, Any]]:
    """
    Returning last receipts of user (id, created_at, total amount, source)
    """
    if cfg is None: 
        cfg = DbConfig()

    conn = get_connection(cfg)    
    try: 
        with conn: 
            with conn.cursor(cursor_factory=RealDictCursor) as cur: 
                cur.execute(
                    """
                    SELECT id, created_at, total_amount, source, merchant
                    FROM receipts
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (user_id, limit)
                )
                rows = cur.fetchall()
                return list(rows)
    finally: 
        conn.close()

def get_receipt_with_items(
        user_id: int,
        receipt_id: int, 
        cfg: DbConfig | None = None
) -> dict | None:
    """
    Returns one receipt with his items for certain user
    Structure:
     {
      "id": ...,
      "created_at": ...,
      "total_amount": ...,
      "source": "...",
      "items": [
         { "id": ..., "merchant": ..., "item_name": ..., "price": ..., "category": ..., "bucket": ..., "confidence": ... },
         ...
      ]
    }
    """
    if cfg is None:
        cfg = DbConfig()

    conn = get_connection(cfg)
    try: 
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur: 
                # Receipt itself
                cur.execute(
                    """
                    SELECT id, created_at, total_amount, source, merchant
                    FROM receipts
                    WHERE id = %s AND user_id = %s;
                    """,
                    (receipt_id, user_id)
                )      
                receipt_row = cur.fetchone()
                if receipt_row is None:
                    return None   

                cur.execute(
                    """
                    SELECT id, merchant, item_name, price, category, bucket, confidence
                    FROM receipt_items
                    WHERE receipt_id = %s
                    ORDER BY id;
                    """,
                    (receipt_id,)
                )
                item_rows = cur.fetchall()

                return {
                    "id": receipt_row["id"],
                    "created_at": receipt_row["created_at"],
                    "total_amount": receipt_row["total_amount"],
                    "source": receipt_row["source"],
                    "merchant": receipt_row["merchant"],
                    "items": list(item_rows)
                }
    finally: 
        conn.close()

def get_spending_summary(
        user_id: int, 
        since: datetime,
        until: datetime | None = None,
        cfg: DbConfig | None = None, 
)    -> Dict[str, Any]:
    """
    Counts expenses of user that starts from date "since" to "until": 
    - total 
    - by_bucket
    - by_category
    """

    if cfg is None: 
        cfg = DbConfig()

    if until is None: 
        until = datetime.utcnow()

    conn = get_connection(cfg)
    try: 
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur: 
                #1) General total
                cur.execute(
                    """
                    SELECT COALESCE(SUM(ri.price), 0) AS total
                    FROM receipts r
                    JOIN receipt_items ri ON ri.receipt_id = r.id
                    WHERE r.user_id = %s
                        AND r.created_at >= %s
                        AND r.created_at < %s
                    """,
                    (user_id, since, until),
                )
                row = cur.fetchone()
                total = float(row["total"] or 0.0)

                # Buskets total  
                cur.execute(
                    """
                    SELECT ri.bucket, SUM(ri.price) AS total
                    FROM receipts r
                    JOIN receipt_items ri ON ri.receipt_id = r.id
                    WHERE r.user_id = %s
                        AND r.created_at >= %s
                        AND r.created_at <= %s
                    GROUP BY ri.bucket
                    ORDER BY total DESC;
                    """,
                    (user_id, since, until),
                )
                by_bucket_rows = cur.fetchall()
                by_bucket = {
                    r["bucket"]: float(r["total"] or 0.0)
                    for r in by_bucket_rows
                }

                # Categories total
                cur.execute(
                    """
                    SELECT ri.category, SUM(ri.price) AS total
                    FROM receipts r
                    JOIN receipt_items ri ON ri.receipt_id = r.id
                    WHERE r.user_id = %s
                        AND r.created_at >= %s
                        AND r.created_at <= %s
                    GROUP BY ri.category
                    ORDER BY total DESC;
                    """,
                    (user_id, since, until),
                )
                by_cat_rows = cur.fetchall()
                by_category = {
                     r["category"]: float(r["total"] or 0.0)
                     for r in by_cat_rows
                    }
                
                return {
                    "total": total,
                    "by_bucket": by_bucket,
                    "by_category": by_category
                }
    finally:
        conn.close()
