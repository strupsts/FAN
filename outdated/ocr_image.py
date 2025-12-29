from io import BytesIO

from PIL import Image, ImageOps
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"D:\Development\DevSoftware\Tesseract\tesseract.exe"







def ocr_image_to_text(image_bytes: bytes, lang: str = "en") -> str:
    """
    Принимает байты картинки (JPEG/PNG и т.п.) и возвращает сырой текст чека.

    lang:
      - "en"  -> английский (eng)
      - "ru"  -> русский (rus)
      - и т.д., но пока держимся за eng.
    """
    # Transform raw bites to file-like object
    buf = BytesIO(image_bytes)
    # Use pillow to open image
    img = Image.open(buf)

    # For OCR sometimes useful transform img to black&white
    img = img.convert("L") # "L" = grayscale
    img = ImageOps.autocontrast(img)
    # in case if receipt too small -> scale it
    min_width = 1000
    if img.width < min_width:
        scale = min_width / img.width
        new_size = (int(img.width * scale), int(img.height * scale))
        img = img.resize(new_size, Image.LANCZOS)

    # Have to map raw lang to Tesseract language
    lang_map = {
        "en": "eng",
        "ru": "rus",
        "uk": "ukr",
    }
    tess_lang = lang_map.get(lang, "eng")

    # Settings for tesseract:
    config = "--psm 6 --oem 3"
    # Call Tesseract thru pytesseract
    text = pytesseract.image_to_string(img, lang=tess_lang, config=config)

    # Clean some garbage
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    cleaned = "\n".join(lines)

    return cleaned 
    