from pathlib import Path

import pandas as pd 

from sklearn.feature_extraction.text import CountVectorizer
from sklearn.preprocessing import LabelEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split

import numpy as np

csv_path = Path("data/category_seed.csv")
df = pd.read_csv(csv_path)

df["merchant"] = df["merchant"].astype(str)
df["item_name"] = df["item_name"].astype(str)
df["category"] = df["category"].astype(str).str.strip().str.upper()

y_text = df["category"].values

corpus = (df["merchant"] + df["item_name"]).str.lower().values

vectorizer = CountVectorizer(lowercase=True, ngram_range=(1,1), min_df=1)
X = vectorizer.fit_transform(corpus)

label_enc = LabelEncoder()
y = label_enc.fit_transform(y_text)

X_train,  X_test, y_train, y_test = train_test_split(
    X,y,
    test_size=0.3,
    random_state=42,
    stratify=y
) 


clf = LogisticRegression (
    max_iter = 1000,
    solver = "lbfgs"
)

clf.fit(X_train, y_train)

y_pred = clf.predict(X_test) #Предсказанные классы
print("MATRIZAAA:", X_test[0])
print("MATRIZAAA2:", X_test[1])
probs = clf.predict_proba(X_test) # матрица  вероятностей: shape = (N_test, N_classes)

# y_test правильные коды; сравниваем покомпонентно
is_correct = (y_pred == y_test)




error_idx = np.where(~is_correct)[0]

print(f"Всего тестовых примеров: {len(y_test)}")
print (f"Ошибок: {len(error_idx)}")


# Собираем таблицу с ошибками
# Важно: X_test и y_test это подмножество исходных данных,
# но в перемешанном порядке. Нам нужно вытащить обратно mechant/item_name
# Для этого удобно хранить "соответствие" через DataFrame-обёртку
test_rows = df.iloc[X_test.indices * 0] #  костыльно, так лучше не делать

# Правильный способ: при split делить ещё и индексы. 
indices = pd.RangeIndex(start = 0, stop=len(df))
idx_train, idx_test = train_test_split (
    indices, 
    test_size = 0.3, 
    random_state = 42, 
    stratify=y
)

# idx_test - это индексы строк df, которые пошли в X_test / y_test
# берем только ошибочные
wrong_global_idx = idx_test[error_idx]


rows = df.iloc[wrong_global_idx].copy()
rows["true_cat"] = label_enc.inverse_transform(y_test[error_idx])
rows["pred_cat"] = label_enc.inverse_transform(y_pred[error_idx])

topk = 2
class_names = label_enc.classes_

def top_probs_row(probs_row):
    #probs_row: одномерный массив вероятностей длинной N_classses
    idx_sorted = probs_row.argsort()[::-1][:topk] # Индексы top-k по убыванию
    return ", ".join(
        f"{class_names[i]}={probs_row[i]:.2f}" for i in idx_sorted
     )

rows["top_probs"] = [top_probs_row(p) for p in probs[error_idx]]

# выведем первые 10 ошибок
print("\nПервые ошибки:")
cols = ["merchant", "item_name", "true_cat", "pred_cat", "top_probs"]
print(rows[cols].head(10).to_string(index=False))