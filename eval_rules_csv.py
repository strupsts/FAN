from pathlib import Path                      # Работа с путями (без боли на Win/macOS/Linux)
import pandas as pd                           # Табличные данные: CSV, фильтры, группировки

# Импортируем нашу «мозговую» функцию и маппинг ведер
from categorybrain_rules import predict_category, category_to_bucket, BUCKET_MAP

# ---- 0) Небольшое демо zip (для понимания) ----
# Можешь запускать как есть, просто чтобы увидеть поведение:
_demo = list(zip(["Walmart","McDonalds"], ["Milk 2L", "Big Mac combo"]))

# Ожидаемый пример: [('Walmart', 'Milk 2L'), ('McDonalds', 'Big Mac combo')]
# print("_demo zip:", _demo)  # включи при желании

# ---- 1) Читаем CSV ----
CSV_PATH = Path("data/category_seed.csv")     # Файл с примерами
df = pd.read_csv(CSV_PATH)                    # Загружаем в DataFrame (таблица в памяти)

# Проверим обязательные колонки (если чего-то нет — сразу явная ошибка)
required_cols = {"merchant", "item_name", "price", "category"}
missing = required_cols - set(df.columns)
if missing:
    raise ValueError(f"В CSV отсутствуют колонки: {missing}")
# На выходе здесь мы хотим продолжать только если merchant/item_name/price/category на месте.

# Приведём типы — это уменьшит сюрпризы дальше
df["merchant"]  = df["merchant"].astype(str)                      # строка
df["item_name"] = df["item_name"].astype(str)                     # строка
df["price"]     = pd.to_numeric(df["price"], errors="coerce")     # число (непарсящиеся → NaN)
df["category"]  = df["category"].astype(str).str.strip().str.upper()

# ---- 2) Прогоняем предсказания по всем строкам ----
# zip(df["merchant"], df["item_name"]) → пары (m, n) построчно
# predict_category(m, n) → кортеж (pred_cat, pred_bucket, pred_conf)
preds = [predict_category(m, n) for m, n in zip(df["merchant"], df["item_name"])]
# Пример ожидаемого элемента: ('DAIRY','NEEDS',0.6)

# Распакуем список кортежей в три отдельных списка (если preds пуст — защитимся)
pred_cat, pred_bucket, pred_conf = zip(*preds) if preds else ([], [], [])

# Приклеим колонки с предсказаниями к исходным данным → получим «обогащённую» таблицу
df_eval = df.assign(pred_cat=pred_cat, pred_bucket=pred_bucket, confidence=pred_conf)
# На выходе df_eval будет иметь колонки: merchant, item_name, price, category, pred_cat, pred_bucket, confidence

# Истинное «ведро» из твоей метки (сопоставим category → bucket)
df_eval["true_bucket"] = df_eval["category"].map(lambda c: BUCKET_MAP.get(c, "WANTS"))
# На выходе появится колонка true_bucket: например, для DAIRY это NEEDS

# ---- 3) Метрики качества ----
# Строгая точность по категориям: доля, где предсказанная категория == разметке CSV
cat_accuracy = (df_eval["pred_cat"] == df_eval["category"]).mean()
# Выход: число от 0 до 1, например 0.73

# Мягкая точность по «ведрам»: правильно ли мы угадали NEEDS/WANTS/...
bucket_accuracy = (df_eval["pred_bucket"] == df_eval["true_bucket"]).mean()
# Выход: тоже 0..1, обычно выше, чем по категориям

# Пер-категорная статистика: сколько строк в классе и какая точность внутри класса
per_cat = (
    df_eval.assign(is_correct=(df_eval["pred_cat"] == df_eval["category"]))  # добавим булево: угадали/нет
          .groupby("category")                                               # сгруппируем по истинной категории
          .agg(rows=("category", "size"), correct=("is_correct", "sum"))     # посчитаем количество и число угаданных
          .assign(acc=lambda t: (t["correct"] / t["rows"]).round(3))         # аккуратная доля (0.000..1.000)
          .sort_values(["acc", "rows"], ascending=[True, False])             # вывалим слабые классы первыми
)
# Выход: маленькая таблица со строками вида:
# category | rows | correct | acc

# ---- 4) Примеры ошибок для ручного анализа ----
mistakes = df_eval.loc[
    df_eval["pred_cat"] != df_eval["category"],
    ["merchant", "item_name", "category", "pred_cat", "pred_bucket", "confidence"]
].head(10)
# Выход: первые 10 промахов, чтобы глазами понять, чего не хватает в правилах

# ---- 5) Вывод в консоль ----
print("="*60)
print("Общая точность по категориям (strict):", round(cat_accuracy, 3))
print("Точность по ведрам (NEEDS/WANTS/...):  ", round(bucket_accuracy, 3))
print("="*60)
print("Пер-категорная статистика (минимум данных слева):")
print(per_cat.to_string())
print("="*60)
if len(mistakes) > 0:
    print("Примеры ошибок:")
    print(mistakes.to_string(index=False))
else:
    print("Ошибок на текущем сете не найдено.")

# ---- 6) Сохраним полный результат (удобно открыть в Excel) ----
out_dir = Path("out")
out_dir.mkdir(exist_ok=True)
outfile = out_dir / "eval_results.csv"
df_eval.to_csv(outfile, index=False, encoding="utf-8")
print(f"\nСохранил детальный результат в: {outfile}")