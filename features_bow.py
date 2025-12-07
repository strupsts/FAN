# features_bow.py

from pathlib import Path  # удобная работа с путями
import pandas as pd  # табличные данные
from sklearn.feature_extraction.text import CountVectorizer  # мешок слов

# 1) читаем CSV в таблицу
csv_path = Path("data/category_seed.csv")
df = pd.read_csv(csv_path)

# 2) нормализуем нужные колонки (строки/верхний регистр категорий)
df["merchant"] = df["merchant"].astype(str)
df["item_name"] = df["item_name"].astype(str)
df["category"] = df["category"].astype(str).str.strip().str.upper()

# 3) целевая переменная (то, что хотим предсказывать)
y = df["category"].values  # например: ["DAIRY","MEAT",...]

# 4) текстовая «фича»: склеиваем merchant + item_name
#    Зачем склейка: иногда merchant даёт сильный контекст (Starbucks → COFFEE),
#    а item_name уточняет (latte → COFFEE). Вместе лучше, чем по отдельности.
corpus = (df["merchant"] + " " + df["item_name"]).str.lower().values
# пример одного элемента: "walmart milk 2l"

# 5) создаём векторизатор: берём только униграммы (отдельные слова), min_df=1 (не фильтруем редкие)
vectorizer = CountVectorizer(lowercase=True, ngram_range=(1, 1), min_df=1)

# 6) учим словарь на нашем корпусе и превращаем весь корпус в матрицу признаков
X = vectorizer.fit_transform(corpus)
# на выходе X — разреженная матрица формата CSR: shape = (N_строк, N_слов)

# 7) смотрим размеры
print("X shape:", X.shape)  # например: (15, 50) — 15 примеров, 50 разных слов
print("y shape:", y.shape)  # (15,)

# 8) покажем первые 3 «вектора слов» в читаемом виде:
feature_names = vectorizer.get_feature_names_out()  # словарь: индекс -> слово

# Подсчитываем общее кол-во значений матрицы для каждого столбца(слова), .sum метод  .A1 метод превращающий разреж. результат в одномерный массив
# axis=0 суммирует значения столбцов (сверху вниз - по строкам)
word_totals = X.sum(axis=0).A1


def show_row(i: int):
    """
    Функция перебирает строку разряженного массива для того,
    чтобы узнать какие слова и сколько раз были использованы в этой строке и кол-во повторений этих слов

    Разряженный массив - матрица/таблица чисел без нулей. B нашем случае столбцы соответствуют словам из словаря,
    строки записям, a значения - кол-ву упоминаний слов.

    """
    row = X[i]  # i-я строка матрицы (разреженная)
    nz = row.nonzero()[
        1
    ]  # индексы слов с ненулевым счётом. Возвращается 2 массива с одинаковой длиной (длина = кол-во строк не равных нулю), 1 массив - координаты матрицы по x (строки) второй массив по y (столбцы), мы разбираем построчно, поэтому обращаемся ко второму массиву содержащих координаты по y (столбцы) [1]
    pairs = []
    for (
        j
    ) in (
        nz
    ):  # nz = [0,2,3] row =  [1, 0, 1, 1, 0] назв табл (coffee latte milk starbucks walmart)
        localAmount = int(row[0, j])
        totalAmount = int(word_totals[j])
        pairs.append((feature_names[j], totalAmount, localAmount))
    pairs.sort(
        key=lambda t: (-t[1], -t[2], t[0])
    )  # сортируем по частоте убыв., затем по слову

    print(f"\n--- Пример #{i} ---")
    print("Текст:", corpus[i])
    print("Слова и счёты:", [(n, loc) for n, tot, loc in pairs])
    print(
        "Сколько раз встретилось слово в матрице ", [(n, tot) for n, tot, loc in pairs]
    )
    print("Целевая категория:", y[i])


for i in range(X.shape[0]):  # покажем до 3 строк
    show_row(i)
