#!/usr/bin/env python3
"""生成中文字模二进制，供 assistant 固件嵌进 flash。

为什么要自己生成：ST7789 只认像素，屏幕模块也没有字库芯片，所以汉字字形必须由
固件提供。Adafruit GFX 自带的是 5x7 ASCII 字模，完全没有汉字。

字符集：GB2312 一级字库（3755 字，区位 16–55）。它覆盖日常中文的绝大部分，
而且**不需要猜"界面会用到哪些字"**——昵称、城市名、天气现象、以后的提醒文案都在里面。

输出格式（小端）：
    0   4B  magic "CJK1"
    4   1B  字号 px
    5   3B  保留
    8   4B  字形数 count
    12  4B  bitsOffset = 16 + count*8
    16  ... count 条记录，每条 8 字节：
            cp      u16   Unicode 码点
            off     u32   相对 bitsOffset 的位图偏移
            w       u8    宽（像素）
            h       u8    高（像素）
    bitsOffset ... 位图区，逐行、每行按字节对齐、1bpp、MSB 在左

字形统一用 px × px 的方框存放（CJK 点阵惯例），这样所有字的基线一致，
不会因为紧致裁剪而高低不齐。

用法：
    python3 scripts/make_cjk_font.py                      # 默认 16 与 24，输出到 data/
    python3 scripts/make_cjk_font.py --sizes 24 --out data
    python3 scripts/make_cjk_font.py --preview            # 顺便输出一张预览图
"""
import argparse
import struct
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# ⚠️ 字体授权：这里默认用 macOS 自带字体，仅供个人开发预览。
#    若项目要发布或商用，请换成思源黑体 / Noto Sans CJK（SIL OFL，可商用）：
#      --font /path/to/SourceHanSansSC-Regular.otf
DEFAULT_FONTS = [
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
    "/System/Library/Fonts/Supplemental/Songti.ttc",
]


def gb2312_level1() -> list[str]:
    """GB2312 一级汉字：区位 16–55，即高字节 0xB0–0xD7、低字节 0xA1–0xFE。"""
    out = []
    for hi in range(0xB0, 0xD8):
        for lo in range(0xA1, 0xFF):
            try:
                out.append(bytes([hi, lo]).decode("gb2312"))
            except UnicodeDecodeError:
                pass
    return out


def gb2312_symbols() -> list[str]:
    """GB2312 符号区（区 1–9）：中文标点、全角符号，以及 ° · — … 等。
    一级汉字只有汉字，'长沙 · 岳麓区' 的间隔号、'20°' 的度号都在这里。"""
    out = []
    for hi in range(0xA1, 0xAA):
        for lo in range(0xA1, 0xFF):
            try:
                out.append(bytes([hi, lo]).decode("gb2312"))
            except UnicodeDecodeError:
                pass
    return out


# 少数常用、但 GB2312 符号区里没有、或 Python 编解码映射对不上的字符，显式补进来。
# U+00B7 间隔号就是典型例子：GB2312 的 A1A4 在 Python 里解码成 U+30FB（片假名中点），
# 而中文文本普遍写 U+00B7，不补就会画成空心方块。
EXTRAS = "嗯·•‧‥—～℃℉°±×÷≈≠≤≥∞　、。！？：；「」『』（）《》〈〉—…“”‘’"


def load_font(path: str, px: int):
    last = None
    for idx in (0, 1, 2, 3):
        try:
            return ImageFont.truetype(path, px, index=idx)
        except Exception as e:      # noqa: BLE001
            last = e
    raise SystemExit(f"字体加载失败 {path}: {last}")


def render_glyph(ch: str, font, px: int) -> bytes:
    """把一个字渲染成 px*px 的 1bpp 位图，逐行、每行按字节对齐。"""
    ascent, descent = font.getmetrics()
    # 把 em 盒在 px 方框里垂直居中：基线落在 (px - (ascent+descent))/2 + ascent
    top = (px - (ascent + descent)) // 2
    img = Image.new("L", (px, px), 0)
    ImageDraw.Draw(img).text((0, top + ascent), ch, font=font, fill=255, anchor="ls")
    # 阈值化：抗锯齿的灰度削成二值，和固件里 1bpp 点阵一致
    bw = img.point(lambda p: 255 if p >= 110 else 0).convert("1")

    row_bytes = (px + 7) // 8
    buf = bytearray(row_bytes * px)
    pix = bw.load()
    for y in range(px):
        for x in range(px):
            if pix[x, y]:
                buf[y * row_bytes + (x >> 3)] |= 0x80 >> (x & 7)
    return bytes(buf)


def build(chars: list[str], font, px: int) -> bytes:
    row_bytes = (px + 7) // 8
    glyph_size = row_bytes * px
    records, bits = [], bytearray()
    for ch in chars:
        cp = ord(ch)
        if cp > 0xFFFF:            # 基本多文种平面之外的不收
            continue
        records.append((cp, len(bits), px, px))
        bits += render_glyph(ch, font, px)
        assert len(bits) - records[-1][1] == glyph_size
    # GB2312 一级是按拼音排的，Unicode 码点不是升序 —— 固件侧要二分查找，这里必须排序
    records.sort(key=lambda r: r[0])
    count = len(records)
    bits_off = 16 + count * 8
    out = bytearray()
    out += b"CJK1" + bytes([px, 0, 0, 0])
    out += struct.pack("<II", count, bits_off)
    for cp, off, w, h in records:
        out += struct.pack("<HIBB", cp, off, w, h)
    out += bits
    return bytes(out)


def preview(font, px, path: Path, sample="爬爬长沙岳麓区阴多云转晴你好呀年月日周四五"):
    """把若干字渲成放大的对照图，用来肉眼确认基线和清晰度。"""
    cols, rows = 16, 4
    sheet = Image.new("L", (cols * px, rows * px), 0)
    ascent, descent = font.getmetrics()
    top = (px - (ascent + descent)) // 2
    d = ImageDraw.Draw(sheet)
    for i, ch in enumerate(sample[: cols * rows]):
        cx, cy = (i % cols) * px, (i // cols) * px
        d.text((cx, cy + top + ascent), ch, font=font, fill=255, anchor="ls")
    sheet.point(lambda p: 255 if p >= 110 else 0).resize(
        (cols * px * 3, rows * px * 3), Image.NEAREST).save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--font", default=None)
    ap.add_argument("--sizes", type=int, nargs="+", default=[16, 24])
    ap.add_argument("--out", default=str(Path(__file__).resolve().parents[1] / "data"))
    ap.add_argument("--preview", action="store_true")
    args = ap.parse_args()

    font_path = args.font
    if not font_path:
        for f in DEFAULT_FONTS:
            if Path(f).exists():
                font_path = f
                break
    if not font_path:
        raise SystemExit("找不到可用中文字体，用 --font 指定一个 TTF/OTF")
    print(f"字体：{font_path}")
    if "System/Library" in font_path:
        print("⚠️  这是 macOS 自带字体，仅供个人开发；发布/商用请换思源黑体或 Noto Sans CJK")

    syms, hanzi = gb2312_symbols(), gb2312_level1()
    chars = list(dict.fromkeys(list(EXTRAS) + syms + hanzi))   # 去重，符号在前
    print(f"字符集：符号 {len(syms)} + 汉字 {len(hanzi)} + 补充 {len(EXTRAS)} "
          f"→ 去重后 {len(chars)} 字形")

    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    for px in args.sizes:
        font = load_font(font_path, px)
        blob = build(chars, font, px)
        path = outdir / f"cjk{px}.bin"
        path.write_bytes(blob)
        print(f"  → {path.name}  {len(blob):,} 字节  ({len(blob)/1024:.0f} KB)")
        if args.preview:
            pv = outdir / f"preview-cjk{px}.png"
            preview(font, px, pv)
            print(f"     预览图 {pv.name}")


if __name__ == "__main__":
    main()
