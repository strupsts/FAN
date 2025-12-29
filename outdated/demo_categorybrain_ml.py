from pathlib import Path 
from categorybrain.categorybrain_ml import CategoryBrainML

csv_path = Path("data/category_seed.csv")

brain = CategoryBrainML()
brain.fit_from_csv(csv_path)
                   
examples = [
    ("Walmart", "Milk 2L"),
    ("McDonalds", "Big Mac combo"),
    ("Starbucks", "Latte grande"),
    ("Canadian Tire", "Motor oil 5W-30"),
    ("Uniway", "USB-C cable"),
    ("Chipotle", "Double steak burrito"),
    ("Pizza Hut", "Pepperoni pizza")
]

for merchant, item in examples: 
    cat, bucket, conf = brain.predict(merchant, item)
    print(f"{merchant:13} | {item:30} -> {cat:12} | {bucket:6} | conf={conf:.2f}")