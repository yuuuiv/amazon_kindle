import os
from PIL import Image

# ========== 配置 ==========
input_dir = "images"
output_dir = "merged"
os.makedirs(output_dir, exist_ok=True)

# ========== 按页拼接 ==========
page_numbers = set()

# 识别所有 page_xxxx_1.jpg
for filename in os.listdir(input_dir):
    if filename.endswith("_1.jpg"):
        page_num = filename.replace("_1.jpg", "")
        page_numbers.add(page_num)

for page in sorted(page_numbers):
    upper_path = os.path.join(input_dir, f"{page}_1.jpg")
    lower_path = os.path.join(input_dir, f"{page}_2.jpg")
    output_path = os.path.join(output_dir, f"{page}.jpg")

    if not os.path.exists(upper_path) or not os.path.exists(lower_path):
        print(f"⚠️ 缺失文件：{upper_path} 或 {lower_path}，跳过")
        continue

    # 打开图片并拼接
    upper_img = Image.open(upper_path)
    lower_img = Image.open(lower_path)

    # 创建新图像容器（宽度相同，高度相加）
    total_height = upper_img.height + lower_img.height
    merged_img = Image.new("RGB", (upper_img.width, total_height))

    # 拼接上下图像
    merged_img.paste(upper_img, (0, 0))
    merged_img.paste(lower_img, (0, upper_img.height))

    # 保存新图像
    merged_img.save(output_path)
    print(f"✅ 已合并保存：{output_path}")

print("\n📘 所有图片合并完成，结果保存在：", os.path.abspath(output_dir))
