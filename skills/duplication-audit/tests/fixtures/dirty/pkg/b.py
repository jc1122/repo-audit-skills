def normalize_rows(records):
    cleaned = []
    for record in records:
        if record is None:
            continue
        name = record.get("name", "").strip().lower()
        value = record.get("value", 0)
        if value < 0:
            value = 0
        cleaned.append({"name": name, "value": value, "ok": True})
    return cleaned
