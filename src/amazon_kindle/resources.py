import base64
import hashlib
import json
import time
from io import BytesIO
from pathlib import Path

from PIL import Image
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


VISIBLE_IMAGES_JS = r"""
const root = document.querySelector('#kr-renderer');
if (!root) return [];
const viewport = root.getBoundingClientRect();
return [...root.querySelectorAll('img')].filter(img => {
  if (!img.complete || !img.naturalWidth) return false;
  for (let node = img; node; node = node.parentElement) {
    const style = getComputedStyle(node);
    if (style.display === 'none' || style.visibility === 'hidden' || Number(style.opacity) === 0) return false;
    if (node === root) break;
  }
  const r = img.getBoundingClientRect();
  return r.width > 0 && r.height > 0 && r.right > Math.max(0, viewport.left) &&
    r.left < Math.min(innerWidth, viewport.right) && r.bottom > Math.max(0, viewport.top) &&
    r.top < Math.min(innerHeight, viewport.bottom);
}).map(img => ({src: img.currentSrc || img.src}));
"""

READ_IMAGE_JS = r"""
const id = arguments[0], done = arguments[arguments.length - 1];
window.__kindleSources.read(id).then(data => done({data})).catch(error => done({error: String(error)}));
"""

DEFAULT_SCRIPT_PATH = Path(__file__).with_name("assets") / "capture_sources.js"


def image_info(data: bytes) -> tuple[str, str, int, int]:
    extensions = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp", "GIF": ".gif", "BMP": ".bmp", "TIFF": ".tiff", "AVIF": ".avif"}
    with Image.open(BytesIO(data)) as image:
        image_format = (image.format or "").upper()
        width, height = image.size
        image.verify()
    if image_format not in extensions:
        raise RuntimeError(f"不支持的资源格式：{image_format or '未知'}")
    return extensions[image_format], image_format, width, height


class OriginalResourceCollector:
    """保存阅读器显示页关联的绘制前资源，不导出 Canvas 截图。"""

    def __init__(self, driver, output_dir: Path, network_wait: float = 10.0):
        self.driver = driver
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=False)
        self.network_wait = network_wait
        self.records = []
        self.saved_ids = set()
        self.saved_hashes = set()
        self.last_state = None
        self.last_wait_reason = ""
        self.driver.set_script_timeout(30)

    def enable(self, script_path: Path | None = None) -> None:
        script_path = script_path or DEFAULT_SCRIPT_PATH
        script = script_path.read_text(encoding="utf-8")
        self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": script})
        self.driver.refresh()
        WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.ID, "kr-renderer")))

    def state(self):
        images = self.driver.execute_script(VISIBLE_IMAGES_JS)
        if not isinstance(images, list) or len(images) != 1:
            self.last_wait_reason = "等待稳定的单页显示"
            return None
        src = images[0].get("src") if isinstance(images[0], dict) else None
        ids = self.driver.execute_script("return window.__kindleSources?.ids(arguments[0]) || [];", src)
        if not src or not isinstance(ids, list) or not ids or any(type(item) is not int for item in ids):
            self.last_wait_reason = "当前图片尚未关联到原始资源"
            return None
        location = self.driver.execute_script("return document.querySelector('ion-range.scrubber-bar')?.getAttribute('aria-label') || ''; ")
        self.last_wait_reason = ""
        return tuple(ids), location

    def wait_for_page(self, previous=None, timeout: float | None = None):
        deadline = time.monotonic() + (timeout if timeout is not None else self.network_wait)
        candidate = None
        stable_since = time.monotonic()
        while time.monotonic() < deadline:
            current = self.state()
            if current != candidate:
                candidate, stable_since = current, time.monotonic()
            if current and current != previous and time.monotonic() - stable_since >= 1.5:
                return current
            time.sleep(0.2)
        return None

    def save(self, state) -> bool:
        pending = []
        for source_id in state[0]:
            if source_id in self.saved_ids:
                continue
            result = self.driver.execute_async_script(READ_IMAGE_JS, source_id)
            if not isinstance(result, dict) or not result.get("data"):
                raise RuntimeError("读取原始图片失败：浏览器返回空数据")
            data = base64.b64decode(result["data"], validate=True)
            pending.append((source_id, data, image_info(data)))
        if self.state() != state:
            return False
        for source_id, data, info in pending:
            digest = hashlib.sha256(data).hexdigest()
            self.saved_ids.add(source_id)
            if digest in self.saved_hashes:
                continue
            extension, image_format, width, height = info
            number = len(self.records) + 1
            output = self.output_dir / f"page_{number:04d}{extension}"
            output.write_bytes(data)
            self.saved_hashes.add(digest)
            self.records.append({"sequence": number, "file": output.name, "location": state[1], "sha256": digest, "width": width, "height": height, "format": image_format, "source": "pre_canvas_image"})
        (self.output_dir / "manifest.json").write_text(json.dumps(self.records, ensure_ascii=False, indent=2), encoding="utf-8")
        self.driver.execute_script("window.__kindleSources.release(arguments[0]);", list(state[0]))
        self.last_state = state
        return True
