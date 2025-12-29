from pathlib import Path
from typing import Tuple

import pandas as pd
import joblib

from sklearn.feature_extraction.text import CountVectorizer
from sklearn.preprocessing import LabelEncoder
from sklearn.linear_model import LogisticRegression

from categorybrain.categorybrain_rules import category_to_bucket


class CategoryBrainML:

    def __init__(self) -> None:

        self.vectorizer = CountVectorizer(lowercase=True, ngram_range=(1, 1), min_df=1)

        self.label_enc = LabelEncoder()

        self.clf = LogisticRegression(max_iter=1000, solver="lbfgs")

        # Флаг чтобы не забыть обучить
        self._is_fitted = False

    def _prepare_dataframe(self, csv_path: Path) -> pd.DataFrame:

        df = pd.read_csv(csv_path)

        df["merchant"] = df["merchant"].astype(str)
        df["item_name"] = df["item_name"].astype(str)
        df["category"] = df["category"].astype(str).str.strip().str.upper()

        return df

    def _make_corpus_and_labels(self, df: pd.DataFrame):

        corpus = (df["merchant"] + " " + df["item_name"]).str.lower().values
        y_text = df["category"].values

        return corpus, y_text

    def fit_from_csv(self, csv_path: str | Path) -> float:

        csv_path = Path(csv_path)
        df = self._prepare_dataframe(csv_path)
        corpus, y_text = self._make_corpus_and_labels(df)

        X = self.vectorizer.fit_transform(corpus)

        y = self.label_enc.fit_transform(y_text)

        self.clf.fit(X, y)
        self._is_fitted = True

        train_acc = self.clf.score(X, y)
        print(f"[CategoryBrainML] Train accuracy on all data: {train_acc:.3f}")
        return float(train_acc)

    def save(self, path: str | Path) -> None:

        if not self._is_fitted:
            raise RuntimeError(
                "Нельзя сохранять необученный CategoryBrainML. Сначала fit_from_csv"
            )

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "vectorizer": self.vectorizer,
            "label_enc": self.label_enc,
            "clf": self.clf,
        }

        joblib.dump(payload, path)
        print(f"[CategoryBrainML] Saved model to {path}")

    @classmethod
    def load(cls, path):

        path = Path(path)
        payload = joblib.load(path)

        obj = cls()
        obj.vectorizer = payload["vectorizer"]
        obj.label_enc = payload["label_enc"]
        obj.clf = payload["clf"]
        obj._is_fitted = True

        print(f"[CategoryBrain_ML] Loaded model from {path}")
        return obj

    def predict(self, merchant: str, item_name: str) -> Tuple[str, str, float]:
        """
        Делает предсказание для одной позиции.
        Возвращает (category, bucket, confidence).
        """

        if not self._is_fitted:
            raise RuntimeError(
                "CategoryBrainML не обучен. Сначала вызови fit_from_csv()."
            )

        text = (str(merchant) + " " + str(item_name)).lower()

        X_ex = self.vectorizer.transform([text])

        probs = self.clf.predict_proba(X_ex)[0]
        y_pred = self.clf.predict(X_ex)[0]
        cat = self.label_enc.inverse_transform([y_pred])[0]

        bucket = category_to_bucket(cat)

        # 7) Уверенность = вероятность предсказанного класса
        #    Внимание: y_pred — это индекс класса, он совпадает с позицией в probs,
        #    потому что LabelEncoder дал нам 0..N-1, и clf.classes_ те же числа.
        conf = float(probs[int(y_pred)])

        return cat, bucket, conf
