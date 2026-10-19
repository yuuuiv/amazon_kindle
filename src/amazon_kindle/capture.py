import time
from datetime import datetime
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.expected_conditions import presence_of_element_located
from selenium.webdriver.support.ui import WebDriverWait

from .config import CaptureConfig
from .cookies import restore_cookies, save_cookies
from .resources import OriginalResourceCollector


ASSET_PATH = Path(__file__).with_name("assets") / "capture_sources.js"


def create_driver(config: CaptureConfig):
    options = Options()
    options.add_argument("--start-maximized")
    service = None
    if config.driver_path:
        from selenium.webdriver.chrome.service import Service
        service = Service(str(config.driver_path))
    return webdriver.Chrome(service=service, options=options)


def turn_page(driver, wait_seconds: float = 5.0) -> bool:
    buttons = driver.find_elements(By.CSS_SELECTOR, "#kr-chevron-left, #kr-chevron-right")
    for button in buttons:
        label = (button.get_attribute("aria-label") or button.get_attribute("title") or "").lower()
        if any(word in label for word in ("下一页", "下一頁", "next", "次のページ", "次の頁")):
            if not button.is_displayed() or not button.is_enabled() or button.get_attribute("aria-disabled") == "true":
                return False
            button.click()
            time.sleep(wait_seconds)
            return True
    return False


def run(config: CaptureConfig, driver=None) -> Path:
    owns_driver = driver is None
    driver = driver or create_driver(config)
    try:
        driver.get(config.start_url)
        restore_cookies(driver, config.cookie_path)
        input("登录并进入阅读页后按回车继续：")
        save_cookies(driver, config.cookie_path)
        WebDriverWait(driver, 30).until(presence_of_element_located((By.ID, "kr-renderer")))
        output_dir = config.session_dir(datetime.now().strftime("%Y%m%d_%H%M%S_%f"))
        collector = OriginalResourceCollector(driver, output_dir, config.network_wait)
        collector.enable(ASSET_PATH)
        input("请切换单页并跳到封面后按回车开始：")
        state = collector.wait_for_page()
        if state is None:
            raise RuntimeError(f"未追踪到稳定页面：{collector.last_wait_reason}")
        while True:
            if not collector.save(state):
                state = collector.wait_for_page(previous=collector.last_state)
                if state is None:
                    raise RuntimeError("页面持续变化，无法保存稳定图片")
                continue
            if not turn_page(driver, config.page_turn_wait):
                break
            next_state = None
            for _ in range(config.max_fails):
                next_state = collector.wait_for_page(previous=collector.last_state)
                if next_state:
                    break
            if next_state is None:
                break
            state = next_state
        print(f"本次保存 {len(collector.records)} 张图片：{output_dir}")
        return output_dir
    finally:
        if owns_driver:
            driver.quit()
