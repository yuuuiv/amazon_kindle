# Kindle Cloud Reader — 图像抓取与拼接工具

> 通过 Selenium 自动化抓取 Kindle Cloud Reader 中的书籍页面图像，并将上下半页拼接为完整页面，方便个人已购内容的本地备份与离线阅读。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)

---

## 功能特性

- **自动抓取** — 自动识别 Kindle Cloud Reader iframe 中内嵌的 base64 图像并保存为 JPG
- **上下拼接** — 将 Kindle 分半页显示的上下两部分合并为一页完整图像
- **去重机制** — 基于图像哈希的去重，避免重复保存相同页面
- **自动翻页** — 模拟键盘方向键自动翻页，逐页抓取直至末尾
- **Cookie 持久化** — 首次手动登录后自动保存 Cookie，后续运行可免登录
- **结构化输出** — 图像按页码编号保存，目录结构清晰

---

## 环境要求

| 依赖 | 说明 |
|------|------|
| Python 3.8+ | 脚本运行环境 |
| Google Chrome | 浏览器 |
| ChromeDriver | 与 Chrome 版本匹配的 WebDriver |

### 安装 Python 依赖

```bash
pip install selenium pillow
```

### 安装 ChromeDriver

1. 检查 Chrome 版本：在地址栏输入 `chrome://version/`
2. 从 [ChromeDriver 下载页](https://chromedriver.chromium.org/downloads) 下载匹配版本
3. 将 `chromedriver` 可执行文件所在目录添加至系统 `PATH`

---

## 快速开始

### 第一步：抓取图像

```bash
python kindle_cramp.py
```

运行流程：

1. 自动打开 Chrome 并跳转至 [Kindle Cloud Reader](https://read.amazon.co.jp/kindle-library)
2. 在浏览器中手动登录你的 Amazon 账户
3. 点击任意一本书籍进入阅读界面，然后在终端按 `Enter` 继续
4. 脚本将自动抓取当前可见页面的图像，并模拟「→」方向键翻页
5. 图像保存至 `images/` 目录，格式为 `page_0001_1.jpg`、`page_0001_2.jpg` …

> 首次登录后，Cookie 将自动保存至 `kindle_cookies.json`，下次运行可跳过登录。

### 第二步：拼接图像

```bash
python image_merge.py
```

脚本会扫描 `images/` 中的所有半页图像对，将其上下拼接为完整页面，输出至 `merged/` 目录，如 `page_0001.jpg`。

---

## 项目结构

```
amazon_kindle/
├── kindle_cramp.py          # 图像抓取脚本
├── image_merge.py           # 图像拼接脚本
├── kindle_cookies.json      # 登录 Cookie（自动生成）
├── images/                  # 原始半页图像（自动生成）
│   ├── page_0001_1.jpg
│   ├── page_0001_2.jpg
│   └── …
├── merged/                  # 拼接后的完整页面（自动生成）
│   ├── page_0001.jpg
│   └── …
├── LICENSE
└── README.md
```

---

## 配置说明

如需修改默认配置，可在 `kindle_cramp.py` 顶部调整以下变量：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `SAVE_DIR` | `"images"` | 抓取图像的保存目录 |
| `COOKIE_PATH` | `"kindle_cookies.json"` | Cookie 持久化文件路径 |
| `MAX_FAILS` | `3` | 连续未检测到新图像的最大次数，超过即视为已到末页 |

---

## 免责声明

- **本工具仅供个人已购内容的合理备份与离线阅读使用。**
- **严禁将抓取的任何内容用于传播、分发或商业用途。**
- 使用者应遵守 Amazon Kindle 服务条款及相关法律法规，自行承担使用本工具的全部责任。
- 若抓取的图像不完整或有缺失，请在 Kindle Cloud Reader 中切换为「单页模式」后重试。

---

## 许可证

本项目基于 [MIT License](LICENSE) 开源。

---

## 贡献与反馈

欢迎提交 [Issue](https://github.com/yuuuiv/amazon_kindle/issues) 报告问题或提出功能建议。Pull Request 同样欢迎。
