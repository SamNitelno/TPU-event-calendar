import re
from datetime import datetime, date, time as time_obj

DATE_PATTERN = re.compile(r"\b(\d{1,2})\.(\d{1,2})\.(?:\d{2}|\d{4})\b")
TIME_PATTERN = re.compile(r"\b(?:[01]?\d|2[0-3]):[0-5]\d\b")

def parse_date_strict(text: str) -> Optional[date]:
    m = DATE_PATTERN.search(text)
    if not m:
        return None
    d, mth, y = map(int, m.groups())
    y_str = m.group(3)
    year = int(y_str) if len(y_str) == 4 else (2000 + y if y < 50 else 1900 + y)
    try:
        return date(year, mth, d)
    except ValueError:
        return None

def parse_time(text: str) -> Optional[time_obj]:
    m = TIME_PATTERN.search(text)
    if not m:
        return None
    h, m = map(int, m.group().split(":"))
    try:
        return time_obj(h, m)
    except ValueError:
        return None

def extract_place(text: str) -> Optional[str]:
    text_lower = text.lower()
    keywords = ["зал", "аудитория", "корпус", "кабинет", "комната"]
    for kw in keywords:
        pos = text_lower.find(kw)
        if pos != -1:
            rest = text[pos + len(kw):].strip()
            place = rest.split(".")[0].split(",")[0].strip()
            if place:
                return place
    return None
