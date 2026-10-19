# Amazon Kindle Reader

用于在获得授权的前提下，从 Kindle Cloud Reader 保存当前书籍显示的页面资源，并按需横向拼接两张页面图。

项目使用 Selenium 控制 Chrome，使用 Pillow 校验和拼接图片。抓取器读取阅读器显示页关联的原始图片资源，不导出浏览器截图，也不重新编码图片。

## 功能

- 手动登录 Amazon 后保存 Cookie，后续运行可尝试恢复登录状态
- 等待阅读器页面稳定后保存图片，并记录页码、尺寸、格式和 SHA-256
- 按阅读器的“下一页”按钮自动翻页，直到按钮不可用或页面不再变化
- 通过图像哈希去重，同时保留 `manifest.json` 中的阅读器位置
- 将任意两张页面图片无损横向拼接为 PNG
- 支持命令行安装，也保留根目录 Python 兼容入口

## 前置条件

- Python `>= 3.10`
- Google Chrome
- 与 Chrome 主版本匹配的 ChromeDriver；也可以通过 `--driver` 显式指定路径
- 你对目标内容拥有复制权或已获得相应授权

## 安装

在仓库根目录执行：

```bash
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
# macOS/Linux
# source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -e .
```

依赖由 `pyproject.toml` 管理，包含 `selenium` 和 `Pillow`。

## 快速开始

### 抓取页面

```bash
kindle-capture --driver C:\tools\chromedriver.exe
```

程序会打开 Kindle Cloud Reader。完成登录并进入书籍阅读页后，在终端按回车；接着切换到单页模式、跳到希望的起始页，再按回车开始抓取。

默认输出到由 `--output-dir` 指定的会话目录。每次会话包含 `page_0001.jpg` 这类图片和 `manifest.json`。Cookie 默认保存到一个名为 `kindle_cookies.json` 的文件，该文件已被 `.gitignore` 忽略。

也可以指定阅读器 URL、输出目录和 Cookie 文件：

```bash
kindle-capture --url "https://read.amazon.co.jp/kindle-library" --output-dir artifacts/original_images --cookie-file artifacts/kindle_cookies.json --driver C:\tools\chromedriver.exe
```

### 拼接页面

指定左页和右页的编号：

```bash
kindle-merge 2 3
```

默认选择 `original_images` 中最近一次包含页面图片的会话，输出到 `merged` 下的会话目录。需要固定输入目录时：

```bash
kindle-merge 2 3 --input-dir original_images/20260101_120000 --output-dir artifacts/merged
```

## 命令和参数

### `kindle-capture`

| 参数 | 默认值 | 作用 |
| --- | --- | --- |
| `--url` | `https://read.amazon.co.jp/kindle-library` | 启动时打开的 Kindle 页面 |
| `--output-dir` | `original_images` | 会话目录的父目录 |
| `--cookie-file` | `kindle_cookies.json` | Cookie 保存位置 |
| `--driver` | 自动发现 | ChromeDriver 可执行文件路径 |

### `kindle-merge`

| 参数 | 作用 |
| --- | --- |
| `PAGE PAGE` | 两个正整数页码，第一个放左侧 |
| `--input-dir` | 页面图片目录；省略时选择最近会话 |
| `--output-dir` | 输出根目录；省略时使用 `merged` |

## 项目结构

```text
amazon_kindle/
├── src/amazon_kindle/
│   ├── assets/capture_sources.js  # 阅读器资源来源追踪脚本
│   ├── capture.py                 # Chrome 会话和自动翻页
│   ├── cli.py                     # kindle-capture / kindle-merge 入口
│   ├── config.py                  # 默认路径和抓取配置
│   ├── cookies.py                 # Cookie 读写和域名过滤
│   ├── merge.py                   # 页面查找和横向拼接
│   └── resources.py               # 原始图片资源读取、校验和 manifest
├── kindle_cramp.py                # 兼容旧命令的抓取入口
├── image_merge.py                 # 兼容旧命令的拼接入口
├── pyproject.toml                 # 包元数据、依赖和 console scripts
├── LICENSE
└── README.md
```

运行时生成的 `original_images/`、`merged/`、Cookie 和 ChromeDriver 不应提交到仓库。

## 兼容旧入口

如果暂时不安装包，仍可从根目录运行：

```bash
python kindle_cramp.py
python image_merge.py 2 3
```

兼容入口会从 `src/` 加载同一套实现，避免维护两份逻辑。

## 测试

编译检查所有 Python 模块：

```bash
python -m compileall src kindle_cramp.py image_merge.py
```

检查命令行帮助：

```bash
python -m amazon_kindle.cli --help
```

当前仓库没有单独的测试套件或代码格式化配置。新增功能时应优先为 `src/amazon_kindle/` 中的纯函数补充测试。

## 数据和安全

- `kindle_cookies.json` 包含登录会话信息，只应保存在本机，不要提交或分享。
- 抓取输出可能包含受版权保护的内容，请遵守 Amazon 服务条款和适用法律。
- 本项目只读取阅读器已经加载的页面资源，不提供购买限制、登录验证或访问控制绕过功能。

## 许可证

项目使用 [MIT License](LICENSE)。

## 维护 README

当命令入口、配置参数、输出目录、资源注入脚本位置或 Python/Chrome 依赖发生变化时，请同步更新本 README。
