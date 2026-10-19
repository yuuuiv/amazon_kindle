import argparse
import re
from pathlib import Path

from .capture import run
from .config import CaptureConfig
from .merge import default_input_dir, merge_pages


def capture_command() -> None:
    parser = argparse.ArgumentParser(description="抓取 Kindle Cloud Reader 当前书籍页面")
    parser.add_argument("--url", default=CaptureConfig.start_url)
    parser.add_argument("--output-dir", type=Path, default=CaptureConfig.output_dir)
    parser.add_argument("--cookie-file", type=Path, default=CaptureConfig.cookie_path)
    parser.add_argument("--driver", type=Path, default=None, help="可选：ChromeDriver 可执行文件路径")
    args = parser.parse_args()
    run(CaptureConfig(start_url=args.url, output_dir=args.output_dir, cookie_path=args.cookie_file, driver_path=args.driver))


def merge_command() -> None:
    parser = argparse.ArgumentParser(description="横向拼接两张页面图片")
    parser.add_argument("pages", nargs="*", type=int, metavar="PAGE")
    parser.add_argument("--input-dir", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    pages = args.pages
    if not pages:
        value = input("请输入左页和右页的编号，例如 2 3（也支持 2,3）：").strip()
        pages = [int(part) for part in re.split(r"[\s,，和]+", value) if part]
    if len(pages) != 2:
        parser.error("请指定两个页码，例如：kindle-merge 2 3")
    directory = args.input_dir or default_input_dir()
    output, size = merge_pages(directory, *pages, output_root=args.output_dir)
    print(f"已拼接，尺寸 {size[0]}×{size[1]}：{output}")


if __name__ == "__main__":
    capture_command()
