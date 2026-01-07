# core/stats_service.py
from data import repository_firebase as repository
from collections import Counter
from datetime import datetime

def parse_date(value):
    """Convierte diferentes formatos de fecha a datetime."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        # formato ISO (2025-11-10T14:35:00)
        return datetime.fromisoformat(value)
    except Exception:
        try:
            # formato con espacio o sin zona horaria
            return datetime.strptime(str(value).split(".")[0], "%Y-%m-%d %H:%M:%S")
        except Exception:
            return None

def get_statistics(year=None, month=None, status=None):
    incidents = repository.get_all_incidents()
    filtered = []

    for inc in incidents:
        try:
            dt = parse_date(inc.get("created_at"))
            if not dt:
                continue

            if year and dt.year != int(year):
                continue
            if month and dt.month != int(month):
                continue
            if status and inc.get("status") != status:
                continue

            filtered.append(inc)
        except Exception:
            continue

    if not filtered:
        return {
            "daily": {"labels": [], "data": []},
            "categories": {"labels": [], "data": []},
            "status": {"labels": [], "data": []},
            "hourly": [0] * 24,
        }

    # 1️⃣ Por día
    daily_counts = Counter([parse_date(i.get("created_at")).day for i in filtered if parse_date(i.get("created_at"))])
    daily = {
        "labels": [str(d) for d in sorted(daily_counts.keys())],
        "data": [daily_counts[d] for d in sorted(daily_counts.keys())],
    }

    # 2️⃣ Por categoría
    cat_counts = Counter([i.get("category", "Desconocido") for i in filtered])
    categories = {"labels": list(cat_counts.keys()), "data": list(cat_counts.values())}

    # 3️⃣ Por estado
    status_counts = Counter([i.get("status", "open") for i in filtered])
    status_stats = {"labels": list(status_counts.keys()), "data": list(status_counts.values())}

    # 4️⃣ Por hora
    hourly_counts = [0] * 24
    for i in filtered:
        dt = parse_date(i.get("created_at"))
        if dt:
            hourly_counts[dt.hour] += 1

    return {
        "daily": daily,
        "categories": categories,
        "status": status_stats,
        "hourly": hourly_counts,
    }
