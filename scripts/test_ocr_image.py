from pathlib import Path

from categorybrain.ocr_image import ocr_image_to_text


def main():
    # Положи какой-нибудь чек в data/test_receipt.png
    img_path = Path("data/test_receipt.jpg")

    if not img_path.exists():
        print("Нет файла data/test_receipt.png — положи туда фотку чека.")
        return

    image_bytes = img_path.read_bytes()
    text = ocr_image_to_text(image_bytes, lang="en")

    print("=== OCR TEXT START ===")
    print(text)
    print("=== OCR TEXT END ===")


if __name__ == "__main__":
    main()
