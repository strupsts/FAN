# --- API ---

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from schemas import (
    OcrPreviewRequest,
    OcrPreviewResponse,
    PredictRequest,
    PredictResponse,
    PredictManyRequest,
    PredictManyResponse,
    ReceiptItemResponse,
    ReceiptSummary,
    ReceiptRequest,
    ReceiptResponse,
    ReceiptShort,
    ReceiptItemDetail,
    ReceiptDetail,
    SpendingSummary,
    OcrPredictResponse,
    OcrConfirmedItem,
    OcrConfirmResponse,
    OcrConfirmRequest,
)

from schemas_llm import LLMItemRequest, LLMItemResponse

from categorybrain.categorybrain_ml import CategoryBrainML
from categorybrain.llm_classifier import LLMClassifier
from categorybrain.db import (
    DbConfig,
    ReceiptItemInput,
    TrainingSampleInput,
    save_receipt,
    list_receipts,
    get_receipt_with_items,
    get_spending_summary,
    save_training_samples,
)
from categorybrain.ocr_text import parse_receipt_text, predict_on_preview

from datetime import datetime, timedelta, timezone

# --- Инициализация приложения и загрузка модели ---

app = FastAPI(title="CategoryBrain API", version="0.1.0")

MODEL_PATH = Path("models/categorybrain_ml.joblib")
brain = CategoryBrainML.load(MODEL_PATH)
llm_classifier = LLMClassifier()

DB_CFG = DbConfig()


def normalize_item_name(item_name: str) -> str:
    """
    Простейшая нормализация для обучения:
    - убираем пробелы по краям
    - приводим к нижнему регистру
    """
    return (item_name or "").strip().lower()


# --- Статика: простая веб-морда
app.mount("/web", StaticFiles(directory="web", html=True), name="web")


# --- Эндпоинты ---


@app.get("/health")
def health():
    """
    Простой health-check.
    Можно дернуть GET /health и проверить, что сервис жив.
    """
    return {"status": "ok"}


@app.post("/predict/category", response_model=PredictResponse)
def predict_category(req: PredictRequest):
    """
    Принимает merchant + item_name и возвращает категорию, ведро и уверенность.
    """
    cat, bucket, conf = brain.predict(req.merchant, req.item_name)

    return PredictResponse(
        merchant=req.merchant,
        item_name=req.item_name,
        category=cat,
        bucket=bucket,
        confidence=conf,
    )


@app.post("/predict/category_batch", response_model=PredictManyResponse)
def predict_category_batch(req: PredictManyRequest):
    results: list[PredictResponse] = []

    for item in req.item:
        cat, bucket, conf = brain.predict(item.merchant, item.item_name)
        results.append(
            PredictResponse(
                merchant=item.merchant,
                item_name=item.item_name,
                category=cat,
                bucket=bucket,
                confidence=conf,
            )
        )
    return PredictManyResponse(item=results)


@app.post("/predict/receipt", response_model=ReceiptResponse)
def predict_receipt(req: ReceiptRequest):
    """
    Принимает целый чек (набор позиций) и:
    - классифицирует каждую строку,
    - считает суммы по ведрам и категориям.
    """
    items_out: list[ReceiptItemResponse] = []

    total = 0.0
    sum_by_bucket: dict[str, float] = {}
    sum_by_category: dict[str, float] = {}

    for item in req.items:
        LRcat, LRbucket, LRconf = brain.predict(item.merchant, item.item_name)

        llm_req = LLMItemRequest(
            merchant=item.merchant,
            item_name_raw=item.item_name,
            price=item.price,
            lang=req.lang if hasattr(req, "lang") else "en",  # или "en" пока
        )
        llm_resp = llm_classifier.classify_item(llm_req)

        items_out.append(
            ReceiptItemResponse(
                merchant=item.merchant,
                item_name=item.item_name,
                price=item.price,
                # логрега
                category=LRcat,
                bucket=LRbucket,
                confidence=LRconf,
                # LLM
                llm_category=llm_resp.category,
                llm_bucket=llm_resp.bucket,
                llm_confidence=llm_resp.confidence,
                llm_norm_name=llm_resp.norm_name,
            )
        )

        # считаем суммы
        total += item.price
        sum_by_bucket[LRbucket] = sum_by_bucket.get(LRbucket, 0.0) + item.price
        sum_by_category[LRcat] = sum_by_category.get(LRcat, 0.0) + item.price

    summary = ReceiptSummary(
        total=total,
        by_bucket=sum_by_bucket,
        by_category=sum_by_category,
    )

    # -- Save check to DB --

    items_for_db = [
        ReceiptItemInput(
            merchant=i.merchant,
            item_name=i.item_name,
            price=float(i.price),
            category=i.category,
            bucket=i.bucket,
            confidence=float(i.confidence),
        )
        for i in items_out
    ]

    # Hardcode user_id = 1, we've got only 1 user atm
    receipt_id = save_receipt(
        user_id=1, items=items_for_db, source="manual", cfg=DB_CFG
    )
    print(f"Receipt #{receipt_id} is saved.")
    return ReceiptResponse(
        receipt_id=receipt_id,
        items=items_out,
        summary=summary,
    )


@app.get("/api/receipts", response_model=list[ReceiptShort])
def api_list_request(limit: int = 50):
    """
    Returns last receipts of certain user (only 1 user atm)
    """
    rows = list_receipts(1, limit, cfg=DB_CFG)

    # Mapping of DB dictionary to the Pydantic model
    return [
        ReceiptShort(
            id=row["id"],
            merchant=row["merchant"],
            created_at=row["created_at"].isoformat(),
            total_amount=float(row["total_amount"]),
            source=row["source"],
        )
        for row in rows
    ]


@app.get("/api/receipts/{receipt_id}", response_model=ReceiptDetail)
def api_get_receipt(receipt_id: int):
    """
    Returns 1 receipt with his items for current user (atm we've got only 1 user_id = 1)
    """

    data = get_receipt_with_items(user_id=1, receipt_id=receipt_id, cfg=DB_CFG)

    if data is None:
        raise HTTPException(status_code=404, detail="Receipt not found")

    return ReceiptDetail(
        id=data["id"],
        merchant=data["merchant"],
        created_at=data["created_at"].isoformat(),
        total_amount=float(data["total_amount"]),
        source=data["source"],
        items=[
            ReceiptItemDetail(
                id=row["id"],
                merchant=row["merchant"],
                item_name=row["item_name"],
                price=float(row["price"]),
                category=row["category"],
                bucket=row["bucket"],
                confidence=float(row["confidence"]),
            )
            for row in data["items"]
        ],
    )


@app.get("/api/stats/summary", response_model=SpendingSummary)
def api_spending_summary(mode: str = "days", days: int = 30, which: str = "current"):
    """
    Returns summary of spendings for last "days"
    for certain user (at the moment only 1 user)

     mode="days":
        - returns last N days (by time)

    mode="month":
        - which="current": current calendar month
        - which="previous": previous calendar month
    """
    now = datetime.utcnow().replace(tzinfo=timezone.utc)

    if mode == "days":
        if days <= 0:
            raise HTTPException(status_code=400, detail="days must be > 0")
        since = now - timedelta(days=days)
        until = now

    elif mode == "month":
        # calculating borders of months
        # starts of current month
        this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        if which == "current":
            since = this_month_start
            # starts of the next month
            if this_month_start.month == 12:
                next_month_start = this_month_start = this_month_start.replace(
                    year=this_month_start.year + 1, month=1
                )
            else:
                next_month_start = this_month_start = this_month_start.replace(
                    year=this_month_start.month + 1
                )
            until = next_month_start

        elif which == "previous":
            # end of the last month = start of this month - 1 day
            prev_month_end = this_month_start - timedelta(days=1)
            prev_month_start = prev_month_end.replace(
                day=1, hour=0, minute=0, second=0, microsecond=0
            )
            since = prev_month_start
            # until = start of this month
            until = this_month_start

        else:
            raise HTTPException(
                status_code=400, detail='which must be "current" or "previous"'
            )
    else:
        raise HTTPException(status_code=400, detail='mode must be "days" or "month"')

    data = get_spending_summary(user_id=1, since=since, until=until, cfg=DB_CFG)

    return SpendingSummary(
        total=data["total"],
        by_bucket=data["by_bucket"],
        by_category=data["by_category"],
    )


@app.post("/api/ocr/preview", response_model=OcrPreviewResponse)
def api_ocr_preview(payload: OcrPreviewRequest):
    """
    Getting raw receipt text and reutrn parsed merchant + items
    """
    try:
        preview = parse_receipt_text(raw_text=payload.raw_text, lang=payload.lang)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return preview


@app.post("/api/ocr/preview-and-predict", response_model=OcrPredictResponse)
def api_ocr_preview_and_predict(payload: OcrPreviewRequest):
    """
    Берём сырой текст чека -> парсим -> прогоняем через CategoryBrainML.
    Ничего не сохраняем в БД, это чисто предпросмотр.
    """
    try:
        preview = parse_receipt_text(
            raw_text=payload.raw_text,
            lang=payload.lang,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    result = predict_on_preview(preview, brain)
    return result


@app.post("/api/ocr/confirm", response_model=OcrConfirmResponse)
def api_ocr_confirm(payload: OcrConfirmRequest):
    if not payload.items:
        raise HTTPException(status_code=400, detail="items must not be empty")

    receipt_items: list[ReceiptItemInput] = []

    for item in payload.items:
        receipt_items.append(
            ReceiptItemInput(
                merchant=payload.merchant,
                item_name=item.item_name_raw,  # в чеках храним как видел юзер
                price=float(item.price),
                category=item.final_category,  # уже исправленный класс
                bucket=item.final_bucket,
                confidence=float(item.model_conf),
            )
        )

    receipt_id = save_receipt(
        user_id=1, items=receipt_items, source="ocr", cfg=DB_CFG  # only one user atm
    )

    # Save to future re-train

    training_rows: list[TrainingSampleInput] = []

    for item in payload.items:
        training_rows.append(
            TrainingSampleInput(
                user_id=1,
                merchant=payload.merchant,
                item_name_raw=item.item_name_raw,
                item_name_norm=normalize_item_name(item.item_name_raw),
                lang=payload.lang,
                price=float(item.price),
                true_category=item.final_category,  # что правильно
                model_category=item.model_category,  # что думала модель
                model_conf=float(item.model_conf),
            )
        )

    save_training_samples(training_rows, cfg=DB_CFG)

    return OcrConfirmResponse(
        receipt_id=receipt_id,
        items_saved=len(payload.items),
    )
