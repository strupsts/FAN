from pathlib import Path
from categorybrain.categorybrain_ml import CategoryBrainML

model_path = Path("models/categorybrain_ml.joblib")

brain = CategoryBrainML.load(model_path)

examples = [
    ("Walmart", "Milk 2L"),
    ("McDonalds", "Big Mac combo"),
    ("Starbucks", "Latte grande"),
]

for merchant, item in examples: 
    cat, bucket, conf = brain.predict(merchant, item)
    print(f"{merchant:13} | {item:30} -> {cat:12} | {bucket:6} | conf={conf:.2f}")
