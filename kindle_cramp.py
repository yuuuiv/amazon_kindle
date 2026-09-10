import base64
import hashlib
import json
import sys
import time
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime

from PIL import Image
from selenium import webdriver
from selenium.common.exceptions import InvalidCookieDomainException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


# ========== 配置 ==========
BASE_DIR = Path(__file__).resolve().parent
SAVE_DIR = BASE_DIR / "original_images"
COOKIE_PATH = BASE_DIR / "kindle_cookies.json"
LIBRARY_URL = "https://read.amazon.co.jp/kindle-library"
MAX_FAILS = 3
PAGE_TURN_WAIT = 5
NETWORK_WAIT = 10



def domain_matches(hostname, cookie_domain):
    hostname = (hostname or "").lower().rstrip(".")
    cookie_domain = (cookie_domain or "").lower().lstrip(".").rstrip(".")
    return bool(cookie_domain) and (
        hostname == cookie_domain or hostname.endswith("." + cookie_domain)
    )


def restore_cookies(driver):
    if not COOKIE_PATH.exists():
        return 0

    print("📘 检测到 cookie，尝试自动登录...")
    try:
        with COOKIE_PATH.open("r", encoding="utf-8") as file:
            cookies = json.load(file)
    except (OSError, json.JSONDecodeError) as error:
        print(f"⚠️ Cookie 文件无法读取，将改为手动登录：{error}")
        return 0

    current_host = urlparse(driver.current_url).hostname
    restored = 0
    skipped = 0
    for saved_cookie in cookies:
        cookie = dict(saved_cookie)
        if not domain_matches(current_host, cookie.get("domain")):
            skipped += 1
            continue
        if cookie.get("sameSite") not in (None, "Strict", "Lax", "None"):
            cookie.pop("sameSite", None)
        if "expiry" in cookie:
            cookie["expiry"] = int(cookie["expiry"])
        try:
            driver.add_cookie(cookie)
            restored += 1
        except (InvalidCookieDomainException, WebDriverException):
            skipped += 1

    print(f"✅ 已恢复 {restored} 条 Cookie，跳过 {skipped} 条不匹配项")
    if restored:
        driver.refresh()
        time.sleep(3)
    return restored


def save_cookies(driver):
    print("💾 保存登录 cookie...")
    with COOKIE_PATH.open("w", encoding="utf-8") as file:
        json.dump(driver.get_cookies(), file, ensure_ascii=False, indent=2)


def original_image_info(image_data):
    """校验图片格式；不转换、不重新编码。"""
    extension_by_format = {
        "JPEG": ".jpg",
        "PNG": ".png",
        "WEBP": ".webp",
        "GIF": ".gif",
        "BMP": ".bmp",
        "TIFF": ".tiff",
        "AVIF": ".avif",
    }
    with Image.open(BytesIO(image_data)) as image:
        image_format = (image.format or "").upper()
        width, height = image.size
        image.verify()

    extension = extension_by_format.get(image_format)
    if not extension:
        raise RuntimeError(f"不支持的资源格式：{image_format or '未知'}")
    return extension, image_format, width, height


# 只读取阅读器正在显示的图片。不要用网络响应顺序或资源名推断页码。
VISIBLE_IMAGES_JS = r"""
const root = document.querySelector('#kr-renderer');
if (!root) return [];
const viewport = root.getBoundingClientRect();
return [...root.querySelectorAll('img')].filter(img => {
    if (!img.complete || !img.naturalWidth) return false;
    for (let node = img; node; node = node.parentElement) {
        const style = getComputedStyle(node);
        if (style.display === 'none' || style.visibility === 'hidden' ||
            Number(style.opacity) === 0) return false;
        if (node === root) break;
    }
    const r = img.getBoundingClientRect();
    return r.width > 0 && r.height > 0 &&
        r.right > Math.max(0, viewport.left) &&
        r.left < Math.min(innerWidth, viewport.right) &&
        r.bottom > Math.max(0, viewport.top) &&
        r.top < Math.min(innerHeight, viewport.bottom);
}).map(img => ({src: img.currentSrc || img.src}));
"""

READ_IMAGE_JS = r"""
const id = arguments[0], done = arguments[arguments.length - 1];
window.__kindleSources.read(id).then(data => done({data}))
    .catch(error => done({error: String(error)}));
"""


class OriginalResourceCollector:
    """按显示页追踪绘制前图片；不导出 Canvas 合成结果。"""

    def __init__(self, driver, output_dir):
        self.driver = driver
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=False)
        self.records = []
        self.saved_ids = set()
        self.saved_hashes = set()
        self.last_state = None
        self.last_wait_reason = ''
        self.driver.set_script_timeout(30)

    def enable(self):
        script = (BASE_DIR / 'capture_sources.js').read_text(encoding='utf-8')
        self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {'source': script})
        self.driver.refresh()
        WebDriverWait(self.driver, 30).until(
            EC.presence_of_element_located((By.ID, 'kr-renderer'))
        )

    def state(self):
        images = self.driver.execute_script(VISIBLE_IMAGES_JS)
        # 页面刷新/导航期间 WebDriver 可能返回 null，不能对其直接 len()。
        if not isinstance(images, list):
            self.last_wait_reason = '浏览器未返回图片列表，页面可能正在导航或刷新'
            return None
        if len(images) != 1:
            self.last_wait_reason = f'当前可见图片数量为 {len(images)}，等待稳定的单页显示'
            return None
        if not isinstance(images[0], dict) or not images[0].get('src'):
            self.last_wait_reason = '当前图片尚未提供有效来源'
            return None
        ids = self.driver.execute_script(
            'return window.__kindleSources?.ids(arguments[0]) || [];', images[0]['src']
        )
        if not isinstance(ids, list) or not ids or any(type(i) is not int for i in ids):
            self.last_wait_reason = '当前图片尚未关联到绘制前来源'
            return None
        location = self.driver.execute_script(
            "return document.querySelector('ion-range.scrubber-bar')"
            "?.getAttribute('aria-label') || '';"
        )
        self.last_wait_reason = ''
        return tuple(ids), location or ''

    def wait_for_page(self, previous=None, timeout=NETWORK_WAIT):
        deadline = time.monotonic() + timeout
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

    def save(self, state):
        pending = []
        for source_id in state[0]:
            if source_id in self.saved_ids:
                continue
            result = self.driver.execute_async_script(READ_IMAGE_JS, source_id)
            if not isinstance(result, dict) or not result.get('data'):
                reason = result.get('error', '浏览器返回空数据') if isinstance(result, dict) else '浏览器返回空数据'
                raise RuntimeError('读取绘制前图片失败：' + reason)
            if result.get('error'):
                raise RuntimeError('读取绘制前图片失败：' + result['error'])
            data = base64.b64decode(result['data'], validate=True)
            info = original_image_info(data)
            pending.append((source_id, data, info))
        if self.state() != state:
            return False
        for source_id, data, info in pending:
            digest = hashlib.sha256(data).hexdigest()
            self.saved_ids.add(source_id)
            if digest in self.saved_hashes:
                continue
            extension, image_format, width, height = info
            number = len(self.records) + 1
            output = self.output_dir / f'page_{number:04d}{extension}'
            output.write_bytes(data)
            self.saved_hashes.add(digest)
            self.records.append({
                'sequence': number, 'file': output.name, 'location': state[1],
                'sha256': digest, 'width': width, 'height': height, 'format': image_format,
                'source': 'pre_canvas_image',
            })
            print(f'✅ 已保存绘制前独立图片：{output.name} '
                  f'[{image_format}, {width}x{height}, {len(data)} bytes, {state[1]}]')
        (self.output_dir / 'manifest.json').write_text(
            json.dumps(self.records, ensure_ascii=False, indent=2), encoding='utf-8'
        )
        self.driver.execute_script('window.__kindleSources.release(arguments[0]);', list(state[0]))
        self.last_state = state
        return True


def turn_page(driver):
    # 使用阅读器的“下一页”语义，兼容左右阅读方向；不点击页面中央。
    buttons = driver.find_elements(By.CSS_SELECTOR, '#kr-chevron-left, #kr-chevron-right')
    for button in buttons:
        label = (button.get_attribute('aria-label') or button.get_attribute('title') or '').lower()
        if any(word in label for word in ('下一页', '下一頁', 'next', '次のページ', '次の頁')):
            if not button.is_displayed() or not button.is_enabled() or button.get_attribute('aria-disabled') == 'true':
                return False
            button.click()
            time.sleep(PAGE_TURN_WAIT)
            return True
    raise RuntimeError('无法识别阅读器的下一页按钮，已停止以避免翻页方向错误。')


def main():
    # Windows 重定向输出可能使用 GBK，避免日志中的 emoji 中断抓取。
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(errors='backslashreplace')
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    driver = webdriver.Chrome(options=chrome_options)

    try:
        driver.get(LIBRARY_URL)
        restore_cookies(driver)
        input("📘 请登录并点击任意书籍进入阅读页面，然后按回车继续...")
        save_cookies(driver)

        handles = driver.window_handles
        if len(handles) > 1:
            driver.switch_to.window(handles[-1])

        if "read.amazon.co.jp" not in driver.current_url:
            print("❌ 当前没有进入 Kindle 阅读页面，请先打开书籍后再按回车")
            return

        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.ID, "kr-renderer"))
        )
        output_dir = SAVE_DIR / datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        collector = OriginalResourceCollector(driver, output_dir)
        collector.enable()
        input("📘 请跳到封面并切换为单页显示，确认后按回车开始（用于确定原图顺序）... ")
        print("✅ 已启用绘制前图片捕获；按当前显示页关联原图，不保存合成画面")

        state = collector.wait_for_page()
        if state is None:
            raise RuntimeError("未追踪到稳定页面的原图来源：" + collector.last_wait_reason)
        while True:
            if not collector.save(state):
                state = collector.wait_for_page()
                if state is None:
                    raise RuntimeError("页面持续变化，无法保存稳定图片。")
                continue
            if not turn_page(driver):
                print("📘 下一页按钮不可用，已停止。")
                break
            # 点击一次后只等待，不重复翻页，以免慢加载时跳过页面。
            next_state = None
            for attempt in range(MAX_FAILS):
                next_state = collector.wait_for_page(previous=collector.last_state)
                if next_state:
                    break
                print(f"⚠️ 等待显示页变化（{attempt + 1}/{MAX_FAILS}）...")
            if next_state is None:
                print("⚠️ 翻页后显示内容未变化：可能已到末页或加载停滞，请核对阅读器位置。")
                break
            state = next_state

        print(f"\n📘 本次保存 {len(collector.records)} 张绘制前独立图片：{output_dir}")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
