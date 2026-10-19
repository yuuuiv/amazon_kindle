import json
import time
from pathlib import Path
from urllib.parse import urlparse

from selenium.common.exceptions import InvalidCookieDomainException, WebDriverException


def domain_matches(hostname: str | None, cookie_domain: str | None) -> bool:
    hostname = (hostname or "").lower().rstrip(".")
    cookie_domain = (cookie_domain or "").lower().lstrip(".").rstrip(".")
    return bool(cookie_domain) and (hostname == cookie_domain or hostname.endswith("." + cookie_domain))


def restore_cookies(driver, cookie_path: Path) -> int:
    if not cookie_path.exists():
        return 0
    try:
        cookies = json.loads(cookie_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"Cookie 文件无法读取，将改为手动登录：{error}")
        return 0

    current_host = urlparse(driver.current_url).hostname
    restored = 0
    for saved_cookie in cookies:
        cookie = dict(saved_cookie)
        if not domain_matches(current_host, cookie.get("domain")):
            continue
        if cookie.get("sameSite") not in (None, "Strict", "Lax", "None"):
            cookie.pop("sameSite", None)
        if "expiry" in cookie:
            cookie["expiry"] = int(cookie["expiry"])
        try:
            driver.add_cookie(cookie)
            restored += 1
        except (InvalidCookieDomainException, WebDriverException):
            continue
    if restored:
        driver.refresh()
        time.sleep(3)
    print(f"已恢复 {restored} 条 Cookie")
    return restored


def save_cookies(driver, cookie_path: Path) -> None:
    cookie_path.parent.mkdir(parents=True, exist_ok=True)
    cookie_path.write_text(json.dumps(driver.get_cookies(), ensure_ascii=False, indent=2), encoding="utf-8")
