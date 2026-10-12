#!/usr/bin/env python3
"""把手机拍的启动画面裁切放大，好把屏幕上的内核日志读清楚。

macOS 的内核 verbose 日志只打在屏幕上、不落盘，出问题时通常只能拍照。
低分辨率照片直接看是糊的；裁成横条 + 3~4 倍 LANCZOS 放大后基本都能读。

用法:
    python read-screen-photo.py photo.jpg                     # 自动输出底部 3 条切片
    python read-screen-photo.py photo.jpg --scale 4           # 放大 4 倍
    python read-screen-photo.py photo.jpg --crop 0.72 1.0     # 只取纵向 72%~100% 区域
    python read-screen-photo.py photo.jpg --out ./shots

依赖: Pillow
"""
import argparse
import os
import sys

try:
    from PIL import Image
except ImportError:
    sys.exit("需要 Pillow：pip install Pillow")


def save(im, box, scale, out_dir, name):
    c = im.crop(box)
    c = c.resize((int(c.width * scale), int(c.height * scale)), Image.LANCZOS)
    path = os.path.join(out_dir, name)
    c.save(path, quality=95)
    print(f"  {name}  crop={box}  ->  {c.size[0]}x{c.size[1]}")


def main():
    ap = argparse.ArgumentParser(description="裁切放大启动画面照片以便阅读")
    ap.add_argument("photo")
    ap.add_argument("--out", default="shots", help="输出目录（默认 ./shots）")
    ap.add_argument("--scale", type=float, default=3.0, help="放大倍数（默认 3）")
    ap.add_argument("--crop", nargs=2, type=float, metavar=("TOP", "BOTTOM"),
                    help="纵向比例区间，如 --crop 0.72 1.0")
    a = ap.parse_args()

    os.makedirs(a.out, exist_ok=True)
    im = Image.open(a.photo).convert("RGB")
    W, H = im.size
    print(f"原图 {W}x{H} -> {a.out}")

    if a.crop:
        top, bottom = a.crop
        save(im, (0, int(H * top), W, int(H * bottom)), a.scale, a.out, "crop.jpg")
        return

    # 默认：底部三条切片，覆盖不同高度，便于逐步定位"最后一行"
    save(im, (0, int(H * 0.70), W, H), a.scale, a.out, "bottom_full.jpg")
    save(im, (0, int(H * 0.78), W, int(H * 0.90)), a.scale, a.out, "bottom_mid.jpg")
    save(im, (0, int(H * 0.88), W, int(H * 0.99)), a.scale + 1, a.out, "bottom_last.jpg")
    print("\n先看 bottom_last.jpg（最后几行），再按需用 --crop 精确定位。")


if __name__ == "__main__":
    main()
