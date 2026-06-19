import json
import os


SCHEMA_VERSION = "1.0"


def _clean_value(value):
    if value is None:
        return None
    if hasattr(value, "tolist"):
        return _clean_value(value.tolist())
    if isinstance(value, dict):
        return {key: _clean_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean_value(item) for item in value]
    if isinstance(value, (str, int, float, bool)):
        return value
    try:
        return float(value)
    except (TypeError, ValueError):
        return str(value)


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(_clean_value(payload), file, ensure_ascii=False, indent=2)
        file.write("\n")


class JsonlDetectionWriter:
    def __init__(self, path):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self._file = open(path, "w", encoding="utf-8")

    def write(self, record):
        self._file.write(json.dumps(_clean_value(record), ensure_ascii=False, separators=(",", ":")))
        self._file.write("\n")

    def close(self):
        if not self._file.closed:
            self._file.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
