#!/usr/bin/env python3
"""GIF → 固件可播的动画二进制。

设计要点（都是实测踩出来的，别随手改）：

1. **不用抖动（dither=NONE）**
   实测 Floyd-Steinberg 是误差扩散，静态区域里相邻帧的抖动图案会整体漂移，
   把帧间差分压缩彻底毁掉（1035K vs 567K）。有序抖动虽然逐帧稳定，
   但会加上肉眼可见的网格纹理。不抖动画质反而最干净，压缩也最好。

2. **帧间差分**
   这些动画背景基本不动，只存变化像素。
   实测：奶蛙1 压 2.2x，奶蛙2 压 3.6x。

3. **每部动画一张全局 256 色调色板，转成 RGB565 存**
   面板是 RGB565（65536 色），GIF 只有 256 色，所以颜色够用；
   调色板一次性转好，播放时每像素只做一次查表。

输出格式（小端，当前 v2）：
    0   4B  magic "GFX1"
    4   1B  版本 = 2
    5   1B  动画数量
    6   2B  保留
    8   ... 每部动画一条 24B 记录：
              u16 w, u16 h, u16 frames, u16 delayMs, u16 reserved
              u32 paletteOff, u32 frameIndexOff, u32 dataOff
    然后依次是：调色板区、帧索引区、帧数据区

帧数据：
    第 0 帧   : w*h 字节的索引，整帧
    第 n 帧   : 若干条差分记录，直到遇到终止标记
                 u32 start  —— 绝对像素位置；0xFFFFFFFF 表示结束（此条不再有 run）
                 u16 run    —— 接下来写入多少像素
                 u8  data[run]

为什么有 v2（2026-09-16）：
    v1 的差分记录是 `u16 start / u16 run`，且 `start == 0xFFFF` 当结束标记。
    u16 让 start 最大只能到 65534 —— **单帧像素数不能超过 65535**。
    320x240 是 76800 像素，**从来就编不出来**；奶蛙1(268x240=64320) 和
    奶蛙2(240x240=57600) 只是运气好卡在门槛内。
    加第三部 320x230(73600) 时被 encode_delta 的 assert 当场拦住，于是升级：
    start/run 都改成 u32，结束标记 0xFFFFFFFF。
    ⚠️ **v2 必须和固件 src/anim.cpp 一起升** —— 两边格式不一致会解出乱码。

用法：
    python3 scripts/make_gif_anim.py a.gif b.gif -o data/anim.bin
    python3 scripts/make_gif_anim.py a.gif --screen 320x240 --preview
"""
import argparse
import json
import struct
from pathlib import Path

from PIL import Image, ImageSequence

MAGIC = b"GFX1"
VERSION = 2
REC_SIZE = 24
PALETTE_COLORS = 256


def rgb565(r: int, g: int, b: int) -> int:
    return ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)


def load_frames(path: Path, max_w: int, max_h: int, stride: int = 1):
    """读 GIF，等比缩放到能放进 max_w x max_h（偶数尺寸），返回 (w, h, frames, delay_ms)。

    stride > 1 时按步长抽帧，并把帧延时乘回去 —— 面板推一屏要上百毫秒
    （320x230 @10 MHz 约 118 ms，上限 8.5 fps），动画比这快也显示不出来，
    抽掉中间帧观感不变、体积直接除以步长。
    """
    im = Image.open(path)
    src = [f.convert("RGB").copy() for f in ImageSequence.Iterator(im)]
    if not src:
        raise SystemExit(f"{path.name}: 读不出帧")

    # 每个 GIF 的帧延时可能不同，取平均值（面板用固定帧率播）
    delays = []
    im.seek(0)
    try:
        while True:
            delays.append(im.info.get("duration", 0) or 0)
            im.seek(im.tell() + 1)
    except EOFError:
        pass
    delay = int(sum(delays) / len(delays)) if delays else 100
    delay = max(30, min(1000, delay))

    if stride > 1:
        if len(src) // stride < 2:
            print(f"  ! {path.name}: 帧数太少（{len(src)}），忽略步长 {stride}")
        else:
            src = src[::stride]
            delay = max(30, min(1000, delay * stride))

    w, h = im.size
    scale = min(max_w / w, max_h / h)
    nw, nh = max(2, int(w * scale) // 2 * 2), max(2, int(h * scale) // 2 * 2)
    frames = [f.resize((nw, nh), Image.LANCZOS) for f in src]

    # 全局调色板：用中间帧的 median-cut，再让所有帧映射过去
    pal_src = frames[len(frames) // 2].quantize(colors=PALETTE_COLORS, method=Image.MEDIANCUT)
    idx = [f.quantize(palette=pal_src, dither=Image.NONE).tobytes() for f in frames]

    # 调色板转 RGB565
    raw_pal = pal_src.getpalette()[: PALETTE_COLORS * 3]
    pal565 = [rgb565(raw_pal[i * 3], raw_pal[i * 3 + 1], raw_pal[i * 3 + 2])
              for i in range(PALETTE_COLORS)]
    return nw, nh, idx, delay, pal565, frames


def encode_delta(prev: bytes, cur: bytes):
    """一条差分帧的字节流。返回 (bytes, 变化像素数)。

    记录格式（v2）：u32 start（绝对像素位置）+ u16 run + run 字节数据，
    末尾一条 start == 0xFFFFFFFF 作结束标记。
    """
    n = len(cur)
    out = bytearray()
    i = 0
    changed = 0
    while i < n:
        if prev[i] == cur[i]:
            i += 1
            continue
        start = i
        # 向后收集变化段；允许段内夹少量未变像素，避免碎成太多小段
        last_change = i
        while i < n and (i - last_change) <= 8 and (i - start) < 60000:
            if prev[i] != cur[i]:
                last_change = i
            i += 1
        end = min(last_change + 1, n)
        run = end - start
        changed += run
        # run 由上面的 < 60000 保证，u16 足够；start 全靠 u32 才装得下大尺寸帧
        assert run < 0x10000, run
        assert start < 0xFFFFFFFF, start
        out += struct.pack("<IH", start, run)
        out += cur[start:end]
    out += struct.pack("<I", 0xFFFFFFFF)
    return bytes(out), changed


def decode_frames(w: int, h: int, frames_blob):
    """按 v2 格式把 frames_blob 解回帧索引 —— 用来原地校验编码器没写错。

    固件 anim.cpp 的 decode() 是同一套逻辑，这里先跑一遍就不用烧板子才发现问题。
    """
    need = w * h
    if len(frames_blob[0]) != need:
        raise SystemExit(f"第 0 帧长度 {len(frames_blob[0])} != {need}")
    cur = bytearray(frames_blob[0])
    out = [bytearray(cur)]
    for blob in frames_blob[1:]:
        p, n = 0, len(blob)
        while p + 4 <= n:
            start = struct.unpack_from("<I", blob, p)[0]
            p += 4
            if start == 0xFFFFFFFF:
                break
            if p + 2 > n:
                raise SystemExit("差分记录被截断（缺 run）")
            run = struct.unpack_from("<H", blob, p)[0]
            p += 2
            if start + run > need:
                raise SystemExit(f"差分越界 start={start} run={run} need={need}")
            if p + run > n:
                raise SystemExit("差分数据被截断")
            cur[start:start + run] = blob[p:p + run]
            p += run
        else:
            raise SystemExit("差分帧没有结束标记")
        out.append(bytearray(cur))
    return out


def build(specs, max_w, max_h):
    """specs 是 [(Path, stride), ...]，顺序决定固件里的动画序号。"""
    anims = []
    for path, stride in specs:
        w, h, idx, delay, pal565, frames = load_frames(path, max_w, max_h, stride)
        frames_blob = []
        frames_blob.append(idx[0])                       # 第 0 帧整存
        changed_total = 0
        for a, b in zip(idx, idx[1:]):
            d, ch = encode_delta(a, b)
            frames_blob.append(d)
            changed_total += ch
        # 往返校验：解回来必须和原始索引逐帧一致
        got = decode_frames(w, h, frames_blob)
        for k, (want, have) in enumerate(zip(idx, got)):
            if want != have:
                raise SystemExit(f"{path.name}: 第 {k} 帧往返解码不一致")
        anims.append(dict(name=path.stem, w=w, h=h, delay=delay, pal=pal565,
                          frames=frames_blob, nframes=len(idx), stride=stride,
                          src=path, changed=changed_total, preview=frames))

    header_len = 8 + REC_SIZE * len(anims)
    cursor = header_len
    layout = []
    for a in anims:
        pal_off = cursor
        cursor += PALETTE_COLORS * 2
        idx_off = cursor
        cursor += a["nframes"] * 8                      # u32 off + u32 len
        data_off = cursor
        cursor += sum(len(f) for f in a["frames"])
        layout.append((pal_off, idx_off, data_off))

    out = bytearray()
    out += MAGIC + bytes([VERSION, len(anims)]) + b"\x00\x00"
    for a, (pal_off, idx_off, data_off) in zip(anims, layout):
        # 10B 数据 + 2B 对齐 = 12B，再加 12B 偏移 = REC_SIZE(24)
        out += struct.pack("<HHHHHH", a["w"], a["h"], a["nframes"], a["delay"], 0, 0)
        out += struct.pack("<III", pal_off, idx_off, data_off)

    for a, (pal_off, idx_off, data_off) in zip(anims, layout):
        assert len(out) == pal_off, (len(out), pal_off)
        for c in a["pal"]:
            out += struct.pack("<H", c)
        assert len(out) == idx_off
        off = 0                     # 必须相对 dataOff —— 固件是 data + off 定位
        for f in a["frames"]:
            out += struct.pack("<II", off, len(f))
            off += len(f)
        assert len(out) == data_off
        for f in a["frames"]:
            out += f
    return bytes(out), anims


def parse_spec(raw: str):
    """把命令行参数解析成 (Path, stride)。

    允许 `file.gif` 或 `file.gif:2` —— 后者表示这部动画按步长 2 抽帧。
    先看整个字符串是不是真实存在的文件，避免路径里本来就带冒号时被误拆。
    """
    if Path(raw).exists():
        return Path(raw), 1
    head, sep, tail = raw.rpartition(":")
    if sep and tail.isdigit() and Path(head).exists():
        return Path(head), max(1, int(tail))
    return Path(raw), 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("gifs", nargs="+", type=str,
                    help="GIF 路径，可写成 file.gif:2 表示按步长 2 抽帧")
    ap.add_argument("--screen", default="320x240", help="屏幕尺寸，默认 320x240")
    ap.add_argument("-o", "--out", default=None, help="输出 .bin")
    ap.add_argument("--preview", action="store_true", help="生成试看页")
    args = ap.parse_args()

    mw, mh = (int(x) for x in args.screen.lower().split("x"))
    specs = [parse_spec(g) for g in args.gifs]
    missing = [p for p, _ in specs if not p.exists()]
    if missing:
        raise SystemExit("找不到文件: " + ", ".join(str(p) for p in missing))

    blob, anims = build(specs, mw, mh)

    for a in anims:
        full = a["w"] * a["h"] * a["nframes"]
        used = sum(len(f) for f in a["frames"])
        print(f"  {a['name']:14s} {a['w']}x{a['h']}  {a['nframes']} 帧  {a['delay']}ms/帧"
              f"  ({1000/a['delay']:.1f} fps)")
        print(f"  {'':14s} 整存 {full/1024:7.0f} KB  →  差分 {used/1024:7.0f} KB"
              f"   ({full/used:.1f}x，变化像素 {a['changed']/full*100:.0f}%)")
    print(f"\n  合计 {len(blob):,} 字节 ({len(blob)/1024:.0f} KB)")
    print(f"  格式 v{VERSION}  往返解码自检：{len(anims)} 部全部逐帧一致 ✅")

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(blob)
        print(f"  -> {out}")

    if args.preview:
        sheets = []
        for a in anims:
            picks = [a["preview"][i] for i in
                     (0, a["nframes"] // 5, 2 * a["nframes"] // 5,
                      3 * a["nframes"] // 5, 4 * a["nframes"] // 5, a["nframes"] - 1)]
            W = sum(p.width for p in picks) + 5 * (len(picks) - 1)
            H = max(p.height for p in picks)
            row = Image.new("RGB", (W, H), (255, 255, 255))
            x = 0
            for p in picks:
                row.paste(p, (x, 0))
                x += p.width + 5
            sheets.append((a["name"], row))
        if sheets:
            W = max(s.width for _, s in sheets)
            H = sum(s.height for _, s in sheets) + 10 * len(sheets)
            page = Image.new("RGB", (W, H), (255, 255, 255))
            y = 0
            for _, s in sheets:
                page.paste(s, (0, y))
                y += s.height + 10
            pv = Path(args.out).with_suffix(".preview.png") if args.out else Path("anim.preview.png")
            page.save(pv)
            print(f"  -> 试看图 {pv}")


if __name__ == "__main__":
    main()
