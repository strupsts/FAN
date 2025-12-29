
from pathlib import Path

import pandas as pd

from sklearn.feature_extraction.text import CountVectorizer
from sklearn.preprocessing import LabelEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split

# Я пишу руками и буду делать комменты тут, если в чем не прав поправляй

csv_path = Path("data/category_seed.csv")
# При помощи pandas преобразуем извлеченные данные из csv в data frame
df = pd.read_csv(csv_path)


# Приводим данные в переменных к строковому типу, а категорию ещё 
# и поднимаем заглавными, удаляя пробелы по концам
df["merchant"] = df["merchant"].astype(str)
df["item_name"] = df["item_name"].astype(str)
df["category"] = df["category"].astype(str).str.strip().str.upper()

# извлекаем значения из столбца category - в список типа ["DAIRY", "MEAT", ....]
y_text = df["category"].values 

# Создаем контекстный список состоящий из склеек магазина и продукта грубо говря
corpus = (df["merchant"] + " " + df["item_name"]).str.lower().values

# опять векторайзер - который создаст матрицу признаков и словарь
vectorizer = CountVectorizer(lowercase=True, ngram_range=(1,1), min_df=1)

# corpus - список склеек, эти склейки разобьются пословесно - это будет словарь
# и создастся разреженная (безнулевая) матрица которая подгонится под 
# тот самый словарь
X = vectorizer.fit_transform(corpus)

print("Форма X:", X.shape)
# y_text[:5] возвращает список только с пятью первыми элементами
print("Примеры y_text", y_text[:5])

# Создаем экзепляр конструктора классов для label encoder
label_enc = LabelEncoder()

# Преобразуем также слова в цифры для того чтобы модель могла понимать
# и учиться находить различия. Только тут у нас не матрица признаков
# а типа массив цифр которые принадлежат определенной категории
# так понимаю в будущем пересечем X и y каким-то образом, пока не знаю как
# p.s Если класс повторяется он его не добавляет, насколько понимаю
y = label_enc.fit_transform(y_text)


print("Коды классов: ", y[:5])

# При помощи zip склеиваем таблицу/массив названия классов и их индексов 
# которые мы узнали благодаряlen()
print("Маппинг классов ", dict(zip(label_enc.classes_, range(len(label_enc.classes_)))))


# Делим данные на 2 части - train и split. 
# text_size = 0.3 это 30 процентов в тест, остальные в обучение
# stratify = y важный параметр регулирует равномерное разбиение пропорций
# классов, иначе из train или test могут не учитываться некоторые категории
# random_state=42 фиксирует чтобы каждый раз разбиение было одинаковым
# при каждом запуске, а 42 это мемное число в ML, лол?
X_train, X_test, y_train, y_test = train_test_split(
    X, y, 
    test_size = 0.3, 
    random_state=42,
    stratify=y
)

print("Train size: ", X_train.shape[0], "Test Size: ", X_test.shape[0])

# настраиваем модель:
# max_iter - кол-во итераций для обучения модели
# multi_class - раньше по дефолту логрега была бинарной (2 класса), но 
# сейчас multinominal идет по умолчанию
# solver - Алгоритм оптимизации модели, как именно логрег будет обучаться,
# подводных связанных с этим не знаю, но хватает пока того что это алгоритм
clf = LogisticRegression (
    max_iter=1000,
    # multi_class="multinomial", - параметр теперь стоит по умолчанию
    solver="lbfgs"
)

# само обучение. Как мне кажется - маржинирование матрицы признаков и классов
clf.fit(X_train, y_train)

# По сути выводим результаты точности тренировки и тестов. Одновременно исполняя тесты, btw
train_acc = clf.score(X_train, y_train)
test_acc = clf.score(X_test, y_test)

print ("\n=== РЕЗУЛЬТАТЫ ===")
print("Train accuracy:", round(train_acc, 3))
print("Test accuracy: ", round(test_acc, 3))

examples = [
    "walmart milk 2l",
    "mcdonalds big mac combo",
    "starbucks latte grande",
    "canadian tire motor oil 5w-30",
    "uniway usb-c cable",
    "mcdonalds lil mac combo",
    "mcdonalds big latte double double",
    "mcdonalds small chicken burger",
    "american gear oil 5w-30",
]

# Уже рабочий код. Создаем матрицу признаков и новоиспеченных данных,
# -> Делаем предсказание помещая матрицу в метод predict тренированной
# модели -> После чего при помощи label_enc который трансформировал для
# нас категории в цифры - сейчас их обратно преобразует в читаемый текст
X_ex = vectorizer.transform(examples)
y_pred = clf.predict(X_ex)
y_pred_text = label_enc.inverse_transform(y_pred)

print("\n=== Примеры предсказаний ===")
for text, cat in zip(examples, y_pred_text):
    print(f"{text:40} -> {cat}")