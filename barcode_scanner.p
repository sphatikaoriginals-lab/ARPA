import io
import re
import cv2
import numpy as np
from datetime import datetime
from PIL import Image

try:
    from pyzbar import pyzbar
    PYZBAR_AVAILABLE = True
except Exception:
    PYZBAR_AVAILABLE = False

try:
    from pylibdmtx import pylibdmtx
    PYLIBDMTX_AVAILABLE = True
except Exception:
    PYLIBDMTX_AVAILABLE = False

def check_expiry_status(expiry_raw: str) -> dict:
    """
    Evaluates YYMMDD format against current system date.
    Returns status: 'VALID', 'EXPIRING_SOON' (within 60 days), or 'EXPIRED'.
    """
    if not expiry_raw or len(expiry_raw) != 6:
        return {"status": "UNKNOWN", "is_expired": False, "days_left": None, "formatted": "N/A"}

    try:
        year = int("20" + expiry_raw[0:2])
        month = int(expiry_raw[2:4])
        day = int(expiry_raw[4:6])

        # If day is '00', default to last day of that month
        if day == 0:
            if month in [1, 3, 5, 7, 8, 10, 12]:
                day = 31
            elif month in [4, 6, 9, 11]:
                day = 30
            elif month == 2:
                day = 29 if (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)) else 28
            else:
                day = 28

        exp_date = datetime(year, month, day)
        today = datetime.now()
        days_left = (exp_date - today).days

        formatted = exp_date.strftime("%d/%m/%Y")

        if days_left < 0:
            return {"status": "EXPIRED", "is_expired": True, "days_left": days_left, "formatted": formatted}
        elif days_left <= 60:
            return {"status": "EXPIRING_SOON", "is_expired": False, "days_left": days_left, "formatted": formatted}
        else:
            return {"status": "VALID", "is_expired": False, "days_left": days_left, "formatted": formatted}

    except Exception:
        return {"status": "UNKNOWN", "is_expired": False, "days_left": None, "formatted": expiry_raw}

def parse_gs1_string(raw_code: str) -> dict:
    parsed = {
        "raw_code": raw_code,
        "gtin": None,
        "expiry_raw": None,
        "expiry_info": {},
        "batch_number": None,
        "serial_number": None
    }
    
    # 1. Extract GTIN (01)
    gtin_match = re.search(r'(?:01|\(01\))(\d{14})', raw_code)
    if gtin_match:
        parsed["gtin"] = gtin_match.group(1)
        
    # 2. Extract Expiry (17)
    exp_match = re.search(r'(?:17|\(17\))(\d{6})', raw_code)
    if exp_match:
        parsed["expiry_raw"] = exp_match.group(1)
        parsed["expiry_info"] = check_expiry_status(exp_match.group(1))

    # 3. Extract Batch / Lot (10)
    batch_match = re.search(r'(?:10|\(10\))([A-Za-z0-9\-]+?)(?:17|21|01|\x1d|$)', raw_code)
    if batch_match:
        parsed["batch_number"] = batch_match.group(1).strip()

    # 4. Extract Serial (21)
    serial_match = re.search(r'(?:21|\(21\))([A-Za-z0-9\-]+)', raw_code)
    if serial_match:
        parsed["serial_number"] = serial_match.group(1).strip()

    return parsed

def scan_gs1_barcode(image_bytes: bytes) -> dict:
    nparr = np.frombuffer(image_bytes, np.uint8)
    cv_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if cv_img is None:
        return {"found": False, "message": "Invalid image format"}

    gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)

    decoded_items = []

    if PYLIBDMTX_AVAILABLE:
        try:
            dmtx_results = pylibdmtx.decode(enhanced, timeout=300)
            for d in dmtx_results:
                raw_data = d.data.decode("utf-8", errors="ignore")
                gs1_info = parse_gs1_string(raw_data)
                gs1_info["barcode_type"] = "GS1 DataMatrix (2D)"
                decoded_items.append(gs1_info)
        except Exception:
            pass

    if PYZBAR_AVAILABLE and not decoded_items:
        try:
            zbar_results = pyzbar.decode(enhanced)
            for z in zbar_results:
                raw_data = z.data.decode("utf-8", errors="ignore")
                gs1_info = parse_gs1_string(raw_data)
                gs1_info["barcode_type"] = f"{z.type} (1D)"
                if not gs1_info["gtin"] and len(raw_data) in [12, 13, 14]:
                    gs1_info["gtin"] = raw_data
                decoded_items.append(gs1_info)
        except Exception:
            pass

    if decoded_items:
        return {"found": True, "data": decoded_items[0]}
    
    return {"found": False, "message": "No standard 1D/2D GS1 barcode found in frame"}