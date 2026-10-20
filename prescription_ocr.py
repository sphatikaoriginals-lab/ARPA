import io
import re
import cv2
import numpy as np
from PIL import Image
from rapidfuzz import process, fuzz
from normalize import get_all_cached_brands

try:
    import easyocr
    reader = easyocr.Reader(['en'], gpu=False)
    OCR_ENGINE = "easyocr"
except Exception:
    reader = None
    OCR_ENGINE = "none"

def enhance_medicine_strip_cv(image_bytes: bytes) -> np.ndarray:
    """Foil reflection remove karke text ko ultra-sharp B/W banata hai."""
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return None

    # Grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Contrast Stretching (CLAHE) - shiny strips ke reflection handle karne ke liye
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)

    # Bilateral Filter to remove noise while keeping text edges sharp
    denoised = cv2.bilateralFilter(enhanced, 9, 75, 75)
    return denoised

def extract_medicines_from_image(image_bytes: bytes) -> dict:
    if not image_bytes or len(image_bytes) < 100:
        return {"source": "Empty Snapshot", "medicines": []}

    detected_medicines = set()

    try:
        processed_cv_img = enhance_medicine_strip_cv(image_bytes)
        if processed_cv_img is None:
            return {"source": "Decode Error", "medicines": []}

        if OCR_ENGINE == "easyocr" and reader is not None:
            # Single High-Res Snap Read
            results = reader.readtext(processed_cv_img, detail=0, paragraph=False)
            raw_lines = [str(r).lower() for r in results]
        else:
            return {"source": "OCR Engine Missing", "medicines": []}

        known_brands = get_all_cached_brands()
        if not known_brands:
            known_brands = ["azikem", "dolo", "combiflam", "pan", "augmentin", "telma", "ecosprin", "glycomet", "calpol"]

        # Text matching
        for line in raw_lines:
            clean = re.sub(r'\b(tab|cap|syp|inj|mg|mcg|ml|g|tablets|capsules|ip|bp|usp)\b', '', line)
            clean = re.sub(r'[^a-zA-Z0-9\s]', ' ', clean).strip()

            if len(clean) < 3:
                continue

            # Substring match
            for brand in known_brands:
                if brand in clean:
                    detected_medicines.add(brand.title())

            # Token level fuzzy match
            for word in clean.split():
                if len(word) >= 4:
                    match_result = process.extractOne(word, known_brands, scorer=fuzz.ratio)
                    if match_result:
                        match, score, _ = match_result
                        if score >= 76:
                            detected_medicines.add(match.title())

        return {
            "source": "High-Res Snap OCR",
            "medicines": sorted(list(detected_medicines))
        }

    except Exception as e:
        print(f"[OCR Error]: {e}")
        return {"source": "Error", "medicines": []}
