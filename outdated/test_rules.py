
from categorybrain_rules import predict_category


tests = [
    ("Walmart", "Milk 2L"),
    ("McDonalds", "Big Mac combo"),
    ("Starbucks", "Latte grande"),
    ("Canadian Tire", "Motor oil 5W-30"),
    ("Uniway", "USB-C cable"),
]



for merchant, item in tests: 
    cat, bucket, conf = predict_category(merchant, item) 
    print(f"{merchant:13} | {item:20} -> {cat:12} | {bucket:6} | conf={conf:.1f}")