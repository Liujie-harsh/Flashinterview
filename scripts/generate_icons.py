# -*- coding: utf-8 -*-
"""
FlashInterview PWA 图标生成脚本

从 icon.svg 的设计（琥珀圆角方块 + 居中黑色 "F"）用 Pillow 直接绘制
生成 PWA 所需的全部 PNG 图标变体：

  - icon-192.png            192x192   purpose=any
  - icon-512.png            512x512   purpose=any
  - icon-maskable-512.png   512x512   purpose=maskable（rx=0 全填充，安全区内放 F）
  - apple-touch-icon-180.png 180x180 iOS apple-touch-icon

输出目录：app/icons/

设计依据：app/icon.svg
  - 背景 #f59e0b，圆角 rx=96（maskable 变体 rx=0）
  - "F" 居中，Arial Black / Helvetica Neue，字重 900，填充 #0a0a0f

运行：python scripts/generate_icons.py
依赖：Pillow（已安装）

不使用 cairosvg，避免 Windows 下 cairo 原生库依赖问题。
"""

import os
from PIL import Image, ImageDraw, ImageFont

# ---------- 配置 ----------

# 项目根目录（脚本位于 <root>/scripts/，向上回一层）
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, 'app', 'icons')

# 颜色（与 icon.svg 一致）
BG_COLOR = (245, 158, 11, 255)      # #f59e0b
FG_COLOR = (10, 10, 15, 255)       # #0a0a0f

# 字体：优先 Arial Black（Windows 自带），其次 Helvetica Neue，最后退化到默认
FONT_CANDIDATES = [
    r'C:\Windows\Fonts\ariblk.ttf',          # Arial Black
    r'C:\Windows\Fonts\ARBLI___.TTF',
    '/Library/Fonts/Arial Black.ttf',         # macOS
    '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',  # Linux fallback
]


def load_font(size):
    """按候选顺序加载字体，找不到则退化到 PIL 默认字体。"""
    for path in FONT_CANDIDATES:
        if os.path.isfile(path):
            try:
                return ImageFont.truetype(path, size=size)
            except Exception:
                continue
    print('[warn] 未找到 Arial Black，退化到默认字体')
    return ImageFont.load_default()


def draw_icon(size, rounded=True):
    """
    绘制单个图标。

    :param size: 输出像素尺寸（正方形）
    :param rounded: True=圆角 rx=96（按 512 比例缩放）；False=maskable 全方形
    :return: PIL.Image RGBA
    """
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 圆角半径：icon.svg 在 512 画布上是 rx=96，按比例缩放
    if rounded:
        radius = max(2, int(size * 96 / 512))
        draw.rounded_rectangle(
            [(0, 0), (size - 1, size - 1)],
            radius=radius,
            fill=BG_COLOR,
        )
    else:
        # maskable：全方形填充，让平台 mask 自行裁切
        draw.rectangle([(0, 0), (size - 1, size - 1)], fill=BG_COLOR)

    # 字号：icon.svg 在 512 画布上是 font-size=360，按比例缩放
    font_size = max(8, int(size * 360 / 512))
    font = load_font(font_size)

    # 居中绘制 "F"
    # 使用 textbbox 获取实际渲染边界（兼容 Pillow 新旧 API）
    try:
        bbox = draw.textbbox((0, 0), 'F', font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        text_x = (size - text_w) // 2 - bbox[0]
        text_y = (size - text_h) // 2 - bbox[1]
    except AttributeError:
        # Pillow < 8.0 退化方案
        text_w, text_h = draw.textsize('F', font=font)
        text_x = (size - text_w) // 2
        text_y = (size - text_h) // 2

    draw.text((text_x, text_y), 'F', font=font, fill=FG_COLOR)

    return img


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    # 待生成的图标列表：(文件名, 尺寸, rounded)
    targets = [
        ('icon-192.png',              192, True),
        ('icon-512.png',              512, True),
        ('icon-maskable-512.png',     512, False),  # maskable 用方形
        ('apple-touch-icon-180.png',  180, False),  # iOS 不需要圆角，系统自加 mask
    ]

    print('[generate_icons] 输出目录:', OUT_DIR)
    for name, size, rounded in targets:
        img = draw_icon(size, rounded=rounded)
        out_path = os.path.join(OUT_DIR, name)
        img.save(out_path, 'PNG')
        print('  - {} ({}x{})'.format(name, size, size))

    print('[generate_icons] 完成，共 {} 个图标'.format(len(targets)))


if __name__ == '__main__':
    main()
