from pathlib import Path
from categorybrain.categorybrain_ml import CategoryBrainML

csv_path = Path("data/category_seed.csv")
model_path = Path("models/categorybrain_ml.joblib")

brain = CategoryBrainML()
brain.fit_from_csv(csv_path)
brain.save(model_path)