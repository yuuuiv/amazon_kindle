"""Backward-compatible entry point for Kindle capture."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from amazon_kindle.capture import run, turn_page
from amazon_kindle.config import CaptureConfig
from amazon_kindle.cookies import domain_matches, restore_cookies, save_cookies
from amazon_kindle.resources import OriginalResourceCollector, VISIBLE_IMAGES_JS, READ_IMAGE_JS, image_info

original_image_info = image_info
BASE_DIR = Path(__file__).resolve().parent
SAVE_DIR = CaptureConfig.output_dir
COOKIE_PATH = CaptureConfig.cookie_path
LIBRARY_URL = CaptureConfig.start_url
MAX_FAILS = CaptureConfig.max_fails
PAGE_TURN_WAIT = CaptureConfig.page_turn_wait
NETWORK_WAIT = CaptureConfig.network_wait


def main():
    return run(CaptureConfig())


if __name__ == "__main__":
    main()
