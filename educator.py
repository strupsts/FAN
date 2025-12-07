from pathlib import Path                      # Работа с путями (без боли на Win/macOS/Linux)
import pandas as pd                           # Табличные данные: CSV, фильтры, группировки

# ---- 1) Читаем CSV ----
CSV_PATH = Path("data/category_seed.csv")     # Файл с примерами
df = pd.read_csv(CSV_PATH)                    



displayGroup = df.groupby("category").agg(rows = ("price", "size"))
print(displayGroup)
