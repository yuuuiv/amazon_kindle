import os
import base64
import time
import json
from PIL import Image
from io import BytesIO
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

# ========== 配置 ==========
SAVE_DIR = "images"
COOKIE_PATH = "kindle_cookies.json"
os.makedirs(SAVE_DIR, exist_ok=True)

# ========== 启动浏览器 ==========
chrome_options = Options()
chrome_options.add_argument("--start-maximized")
driver = webdriver.Chrome(options=chrome_options)
actions = ActionChains(driver)

# ========== 登录 ==========
driver.get("https://read.amazon.co.jp/kindle-library")

# 如果存在 cookie 文件，则加载
if os.path.exists(COOKIE_PATH):
    print("📘 检测到 cookie，尝试自动登录...")
    with open(COOKIE_PATH, "r", encoding="utf-8") as f:
        cookies = json.load(f)
        for cookie in cookies:
            driver.add_cookie(cookie)
    driver.refresh()
    time.sleep(3)

# 等待用户手动登录
input("📘 请登录并点击任意书籍进入阅读页面，然后按回车继续...")

# 保存登录后的 cookies
print("💾 保存登录 cookie...")
cookies = driver.get_cookies()
with open(COOKIE_PATH, "w", encoding="utf-8") as f:
    json.dump(cookies, f, ensure_ascii=False, indent=2)

# ========== 切换到新标签页 ==========
original_tabs = driver.window_handles
for _ in range(20):
    if len(driver.window_handles) > 1:
        break
    time.sleep(1)

if len(driver.window_handles) <= 1:
    print("❌ 未检测到新标签页，请确认是否已点击书籍")
    driver.quit()
    exit()

driver.switch_to.window(driver.window_handles[-1])
print("✅ 已切换到新标签页：", driver.current_url)

# ========== 抓图逻辑 ==========
page_counter = 1
last_saved_hashes = set()

def save_base64_images_from_visible_iframe():
    iframes = driver.find_elements(By.CSS_SELECTOR, 'iframe[id^="column_0_frame_"]')
    visible_iframes = [
        iframe for iframe in iframes
        if iframe.is_displayed() and iframe.value_of_css_property("visibility") == "visible"
    ]

    if not visible_iframes:
        print("⚠️ 未找到可见 iframe")
        return False

    iframe = visible_iframes[0]
    driver.switch_to.frame(iframe)

    img_elements = driver.find_elements(By.CSS_SELECTOR, 'img[src^="data:image/jpeg;base64,"]')
    found_new_image = False

    for i, img in enumerate(img_elements):
        src = img.get_attribute("src")
        base64_data = src.split(",", 1)[1]
        img_hash = hash(base64_data)

        if img_hash in last_saved_hashes:
            continue

        try:
            image_data = base64.b64decode(base64_data)
            img_pil = Image.open(BytesIO(image_data))
            save_path = os.path.join(SAVE_DIR, f"page_{page_counter:04d}_{i+1}.jpg")
            img_pil.save(save_path)
            print(f"✅ 已保存：{save_path}")
            last_saved_hashes.add(img_hash)
            found_new_image = True
        except Exception as e:
            print(f"❌ 解码失败：{e}")

    driver.switch_to.default_content()
    return found_new_image

# ========== 主循环：保存+自动翻页 ==========
fail_count = 0
MAX_FAILS = 3

while True:
    success = save_base64_images_from_visible_iframe()
    if not success:
        fail_count += 1
        print("⚠️ 未检测到新图片，可能是最后一页")
        if fail_count >= MAX_FAILS:
            break
    else:
        fail_count = 0
        page_counter += 1

    # 自动翻页（向右方向键）
    driver.switch_to.default_content()
    actions.send_keys(Keys.ARROW_RIGHT).perform()
    time.sleep(5)

# ========== 结束 ==========
print(f"\n📘 全部完成，图片保存于：{os.path.abspath(SAVE_DIR)}")
driver.quit()
