from categorybrain.db import DbConfig, ReceiptItemInput, save_receipt

def main():
    cfg = DbConfig ()

    items = [
         ReceiptItemInput(
            merchant="Walmart",
            item_name="Milk 2L",
            price=3.99,
            category="DAIRY",
            bucket="NEEDS",
            confidence=0.9,
        ),
        ReceiptItemInput(
            merchant="McDonalds",
            item_name="Big Mac combo",
            price=11.99,
            category="FASTFOOD",
            bucket="WANTS",
            confidence=0.8,
        ),
    ]
    # Function "save_receipt" from Db.py will save receipt all items
    # and return receipt_id after creating
    receipt_id = save_receipt(
        user_id = 1, 
        items = items,
        source = "manual",
        cfg=cfg
    )

    print("Created receipt with id: ", receipt_id)

if __name__ == "__main__":
        main()