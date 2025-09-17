" Class to keep all file for tests"
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = APP_DIR / "Data"
TEMPLATES_DIR = APP_DIR / "Templates"

DATA_DIR.mkdir(parents=True, exist_ok=True)

def get_app_dir() -> Path:
    return APP_DIR

def get_data_dir() -> Path:
    # funkcja (zamiast stałej) ułatwia monkeypatch w testach, ale bez ENV
    return DATA_DIR