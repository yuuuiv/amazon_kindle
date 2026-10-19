import re
from pathlib import Path

from PIL import Image

from .config import IMAGE_EXTENSIONS, ROOT_DIR


def contains_pages(directory: Path) -> bool:
    return any(re.fullmatch(r"page_\d+", file.stem) and file.suffix.lower() in IMAGE_EXTENSIONS for file in directory.iterdir() if file.is_file())


def default_input_dir(source_dir: Path | None = None) -> Path:
    source_dir = source_dir or ROOT_DIR / "original_images"
    sessions = [d for d in source_dir.iterdir() if d.is_dir() and contains_pages(d)] if source_dir.is_dir() else []
    if sessions:
        return max(sessions, key=lambda path: path.stat().st_mtime)
    if source_dir.is_dir() and contains_pages(source_dir):
        return source_dir
    raise ValueError("没有找到页面图片，请使用 --input-dir 指定目录")


def find_page(directory: Path, number: int) -> Path:
    matches = [file for file in directory.iterdir() if file.is_file() and file.stem == f"page_{number:04d}" and file.suffix.lower() in IMAGE_EXTENSIONS]
    if len(matches) != 1:
        raise ValueError(f"第 {number} 页的图片数量不是 1：{directory}")
    return matches[0]


def merge_pages(directory: Path, left_number: int, right_number: int, output_root: Path | None = None) -> tuple[Path, tuple[int, int]]:
    left_path, right_path = find_page(directory, left_number), find_page(directory, right_number)
    with Image.open(left_path) as left, Image.open(right_path) as right:
        if left.height != right.height:
            raise ValueError(f"两页高度不同：{left.height} 与 {right.height}")
        mode = "RGBA" if any("A" in image.getbands() or "transparency" in image.info for image in (left, right)) else "RGB"
        merged = Image.new(mode, (left.width + right.width, left.height))
        merged.paste(left.convert(mode), (0, 0))
        merged.paste(right.convert(mode), (left.width, 0))
        output_dir = (output_root or ROOT_DIR / "merged") / directory.name
        output_dir.mkdir(parents=True, exist_ok=True)
        output = output_dir / f"pages_{left_number:04d}_{right_number:04d}.png"
        suffix = 2
        while output.exists():
            output = output_dir / f"pages_{left_number:04d}_{right_number:04d}_{suffix}.png"
            suffix += 1
        merged.save(output)
        return output, merged.size
