# 📚 Kindle 网页端图像抓取与拼接工具

本项目包含两个 Python 脚本：

- `kindle_cramp.py`：抓取 Kindle 阅读器中 iframe 内嵌的 base64 图像
- `image_merge.py`：将图像文件夹中的上下半页图像拼接成完整页面

---

## 📦 环境依赖

请先安装 Python 包依赖：

```bash
pip install selenium pillow
```

并确保：

- 安装了 [Google Chrome 浏览器](https://www.google.com/chrome/)
- 安装了与你的 Chrome 浏览器版本匹配的 [ChromeDriver](https://chromedriver.chromium.org/downloads)
- `chromedriver` 已添加至系统环境变量路径中

------

## 📘 使用说明

### 1️⃣ 抓取图像（`kindle_cramp.py`）

```bash
python kindle_cramp.py
```

程序将执行以下操作：

1. 启动浏览器并提示你登录 Kindle（https://read.amazon.co.jp/kindle-library）
2. 登录后手动点击进入一本书籍，程序将自动切换到新标签页
3. 每页图像通常为上下两半（分别保存为 `_1.jpg` 和 `_2.jpg`）
4. 自动翻页并持续抓取，直到最后一页
5. 图像保存至 `images/` 目录

------

### 2️⃣ 拼接图像（`image_merge.py`）

```bash
python image_merge.py
```

此脚本会：

- 扫描 `images/` 中所有形如 `page_XXXX_1.jpg` 和 `page_XXXX_2.jpg` 的图片对
- 将它们上下拼接为完整页面
- 结果保存至 `merged/` 文件夹中，文件名如：`page_0001.jpg`

------

## 📂 目录结构示例

```
.
├── kindle_cramp.py        # 图像抓取脚本
├── image_merge.py         # 拼接图像脚本
├── images/                # 保存中间图片（原始半页）
│   ├── page_0001_1.jpg
│   ├── page_0001_2.jpg
│   └── ...
├── merged/                # 保存合并后完整图片
│   ├── page_0001.jpg
│   └── ...
```

------

## 🔒 Cookie 登录与自动翻页

目前：

- 登录操作由用户手动完成，确保账户合法
- 已支持自动翻页功能
- 后续可扩展 Cookie 持久化与全自动化下载流程

------

## ⚠️ 注意事项

- **仅限用于个人已购内容的整理与备份，严禁用于传播与商业用途！**
- 若抓图缺失或图像不完整，请切换 Kindle 阅读器为「单页模式」
- 图像为 base64 编码嵌入，抓取后保存为 JPG，便于本地查看与处理

------

## 📧 联系方式

如需反馈问题、提出建议或请求扩展功能，请联系作者或提交 Issue。
