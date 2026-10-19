"""Backward-compatible entry point for page merging."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from amazon_kindle.merge import contains_pages, default_input_dir, find_page, merge_pages


def main():
    import argparse
    import re
    parser = argparse.ArgumentParser(description="指定两页横向拼接，第一个页码在左，第二个在右。")
    parser.add_argument("pages", nargs="*", type=int, metavar="PAGE")
    parser.add_argument("--input-dir", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    pages = args.pages
    if not pages:
        value = input("请输入左页和右页的编号，例如 2 3（也支持 2,3）：").strip()
        pages = [int(part) for part in re.split(r"[\s,，和]+", value) if part]
    if len(pages) != 2:
        parser.error("请指定两个页码，例如：python image_merge.py 2 3")
    directory = args.input_dir or default_input_dir()
    output, size = merge_pages(directory, *pages, output_root=args.output_dir)
    print(f"已拼接，尺寸 {size[0]}×{size[1]}：{output}")


if __name__ == "__main__":
    main()
