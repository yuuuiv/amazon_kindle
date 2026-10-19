from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_URL = "https://read.amazon.co.jp/kindle-library"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tiff", ".avif"}


@dataclass(frozen=True)
class CaptureConfig:
    start_url: str = DEFAULT_URL
    output_dir: Path = ROOT_DIR / "original_images"
    cookie_path: Path = ROOT_DIR / "kindle_cookies.json"
    max_fails: int = 3
    page_turn_wait: float = 5.0
    network_wait: float = 10.0
    driver_path: Path | None = None

    def session_dir(self, timestamp: str) -> Path:
        return self.output_dir / timestamp
