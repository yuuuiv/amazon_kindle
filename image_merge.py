import argparse
import re
from pathlib import Path

from PIL import Image


BASE_DIR = Path(__file__).resolve().parent
SOURCE_DIR = BASE_DIR / "original_images"
OUTPUT_DIR = BASE_DIR / "merged"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tiff", ".avif"}


def contains_pages(directory):
    return any(
        re.fullmatch(r"page_\d+", file.stem)
        and file.suffix.lower() in IMAGE_EXTENSIONS
        for file in directory.iterdir() if file.is_file()
    )


def default_input_dir():
    """优先使用最近一次包含图片的抓取目录，兼容旧版平铺输出。"""
    if SOURCE_DIR.is_dir():
        sessions = [d for d in SOURCE_DIR.iterdir() if d.is_dir() and contains_pages(d)]
        if sessions:
            return max(sessions, key=lambda d: d.stat().st_mtime)
        if contains_pages(SOURCE_DIR):
            return SOURCE_DIR
    raise ValueError("original_images 中没有页面图片，请使用 --input-dir 指定图片目录。")


def find_page(directory, number):
    matches = [
        file for file in directory.iterdir()
        if file.is_file() and file.stem == f"page_{number:04d}"
        and file.suffix.lower() in IMAGE_EXTENSIONS
    ]
    if not matches:
        raise ValueError(f"找不到第 {number} 页：{directory / f'page_{number:04d}.*'}")
    if len(matches) > 1:
        raise ValueError(f"第 {number} 页存在多个图片格式，请先保留要使用的版本。")
    return matches[0]


def merge_pages(directory, left_number, right_number):
    if left_number < 1 or right_number < 1:
        raise ValueError("页码必须是正整数。")
    left_path = find_page(directory, left_number)
    right_path = find_page(directory, right_number)
    with Image.open(left_path) as left, Image.open(right_path) as right:
        if left.height != right.height:
            raise ValueError(
                f"两页高度不同（{left.height} 与 {right.height}），无法在不缩放、不补边的情况下横向拼接。"
            )
        mode = "RGBA" if any("A" in img.getbands() or "transparency" in img.info for img in (left, right)) else "RGB"
        merged = Image.new(mode, (left.width + right.width, left.height))
        merged.paste(left.convert(mode), (0, 0))
        merged.paste(right.convert(mode), (left.width, 0))
        output_dir = OUTPUT_DIR / directory.name
        output_dir.mkdir(parents=True, exist_ok=True)
        stem = f"pages_{left_number:04d}_{right_number:04d}"
        output = output_dir / f"{stem}.png"
        suffix = 2
        while output.exists():
            output = output_dir / f"{stem}_{suffix}.png"
            suffix += 1
        # PNG 无损保存，保持原尺寸，不加入间距或边框。
        merged.save(output)
        return output, merged.size


def main():
    parser = argparse.ArgumentParser(description="指定两页横向拼接，第一个页码在左，第二个在右。")
    parser.add_argument("pages", nargs="*", type=int, metavar="页码", help="例如：2 3")
    parser.add_argument("--input-dir", type=Path, help="图片目录；默认最近一次非空的 original_images 子目录")
    args = parser.parse_args()
    try:
        directory = args.input_dir.expanduser().resolve() if args.input_dir else default_input_dir()
        if not directory.is_dir():
            raise ValueError(f"图片目录不存在：{directory}")
        print(f"图片目录：{directory}")
        pages = args.pages
        if not pages:
            value = input("请输入左页和右页的编号，例如 2 3（也支持 2,3）：").strip()
            pages = [int(part) for part in re.split(r"[\s,，和]+", value) if part]
        if len(pages) != 2:
            raise ValueError("请指定两个页码，例如：python image_merge.py 2 3")
        output, size = merge_pages(directory, *pages)
        print(f"已拼接：第 {pages[0]} 页在左，第 {pages[1]} 页在右；尺寸 {size[0]}×{size[1]}")
        print(f"保存于：{output}")
    except (ValueError, OSError, EOFError) as error:
        parser.exit(1, f"无法拼接：{error}\n")


if __name__ == "__main__":
    main()
