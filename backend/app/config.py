import os
import json
from pathlib import Path
from pydantic import BaseModel
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
CONFIG_FILE = DATA_DIR / "credentials.json"

class Settings(BaseModel):
    api_key: str = ""
    api_secret: str = ""
    redirect_uri: str = "http://localhost:8000/api/auth/callback"
    access_token: Optional[str] = None
    user_name: Optional[str] = None
    user_id: Optional[str] = None
    feed_token: Optional[str] = None
    token_expiry: Optional[str] = None

def load_settings() -> Settings:
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                return Settings(**data)
        except Exception:
            pass
    # fallback to environment variables
    return Settings(
        api_key=os.getenv("UPSTOX_API_KEY", ""),
        api_secret=os.getenv("UPSTOX_API_SECRET", ""),
        redirect_uri=os.getenv("UPSTOX_REDIRECT_URI", "http://localhost:8000/api/auth/callback"),
        access_token=os.getenv("UPSTOX_ACCESS_TOKEN", None),
    )

def save_settings(settings: Settings) -> None:
    with open(CONFIG_FILE, "w") as f:
        json.dump(settings.model_dump(), f, indent=2)

current_settings = load_settings()
