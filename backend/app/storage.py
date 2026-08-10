import os
from pathlib import Path


uploads_directory = Path(
    os.getenv("UPLOADS_DIR", str(Path(__file__).resolve().parents[1] / "uploads"))
)
uploads_directory.mkdir(parents=True, exist_ok=True)
