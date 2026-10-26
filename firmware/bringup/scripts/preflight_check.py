#!/usr/bin/env python3
"""Guided pre-power-on electrical self-check for the bench bring-up.

Safety gates cannot be skipped: a failing continuity or short-circuit check
stops the walkthrough instead of letting you power up anyway.

Usage:
  python3 scripts/preflight_check.py --rehearse   # walk every step, no hardware
  python3 scripts/preflight_check.py              # interactive, records answers
  python3 scripts/preflight_check.py --list       # list stages
  python3 scripts/preflight_check.py --from 5     # resume at stage 5
  python3 scripts/preflight_check.py --ports      # list candidate serial ports
"""
import argparse
import datetime as dt
import glob
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# kind: info = 只显示; gate = 安全门禁,必须通过; record = 记录数值; cmd = 执行/确认命令
STAGES = [
    {
        "id": "prep",
        "title": "阶段 0 · 准备与断电确认",
        "items": [
            {"kind": "info", "text": "工具：可调限流电源、万用表、烙铁/焊锡、杜邦线、USB 数据线。"},
            {"kind": "gate", "text": "USB 已拔掉，外部电源输出已关闭，手上没有带电的线？",
             "remedy": "先断电再做任何接线或测量。本工程没有硬件掉电隔离，软件不承担保护。"},
            {"kind": "info", "text": "红线：屏幕 VCC/BLK 只接 3.3V（RevB）；屏幕不允许单独带电；改线一律全断电。"},
        ],
    },
    {
        "id": "solder",
        "title": "阶段 1 · 断电电学自检（焊接后、上电前）",
        "items": [
            {"kind": "gate", "text": "A1 目视：排针每针独立，无连锡、锡渣、歪针？",
             "remedy": "补焊或清锡后重看。这一步不通过，后面全部无意义。"},
            {"kind": "gate", "text": "A2 关键：万用表量屏幕模块 VCC↔GND 不导通（不蜂鸣）？",
             "remedy": "VCC/GND 相邻最易搭锡。清锡重查，禁止上电。"},
            {"kind": "record", "text": "A2 记录：VCC↔GND 实测电阻", "hint": "应远大于 1kΩ；记「开路/OL」也可"},
            {"kind": "gate", "text": "A3 每根杜邦线首尾导通，晃动线身不断续？",
             "remedy": "换掉断芯的线。细杜邦线不做大电流供电。"},
            {"kind": "gate", "text": "A4 相邻排针之间不导通（GND 组除外）？",
             "remedy": "查到哪两针相通，对应修正接线或焊接。"},
            {"kind": "gate", "text": "A5 屏幕 GND、开发板 GND、外部电源负极三者互相导通？",
             "remedy": "补共地。不共地会出现随机花屏和通信失败。"},
        ],
    },
    {
        "id": "header",
        "title": "阶段 2 · 12 针实物朝向识别（断电）",
        "items": [
            {"kind": "info", "text": "文档的「针号 1–12」是功能序号，不承诺等于实物物理顺序。以实物丝印为准。"},
            {"kind": "gate", "text": "已找到实物丝印（GND/VCC/SCL/SDA/BLK…）并与 12 针表逐根对上？",
             "remedy": "丝印不清时用万用表通断档找 GND：量到模块大面积覆铜地/屏蔽罩/固定孔导通的那针即 GND。"},
            {"kind": "record", "text": "记录：实物朝向（哪一端是 GND、丝印顺序）", "hint": "拍照存档更稳"},
            {"kind": "gate", "text": "实物朝向与 12 针功能表一致（或已确认以实物为准并需更新 wiring.json）？",
             "remedy": "若冲突，以实物为准，回报修改 wiring.json，不要改接线去迁就文档。"},
        ],
    },
    {
        "id": "supply",
        "title": "阶段 3 · 电源空载复测",
        "items": [
            {"kind": "cmd", "text": "电源空载调到屏幕支路目标 3.3V", "cmd": "空载调整 → 万用表复测 → 关闭输出 → 再接负载"},
            {"kind": "record", "text": "屏幕支路空载实测电压 (V)", "hint": "目标 3.30"},
            {"kind": "cmd", "text": "电源空载调到舵机支路目标 5.0V", "cmd": "空载调整 → 万用表复测 → 关闭输出 → 再接负载"},
            {"kind": "record", "text": "舵机支路空载实测电压 (V)", "hint": "目标 5.00"},
            {"kind": "info", "text": "起始限流建议：屏幕约 0.1A、舵机空载约 0.5A。这是保护值，不是实测耗电。"},
        ],
    },
    {
        "id": "mcu",
        "title": "阶段 4 · 主控单独上电（只接裸开发板 USB）",
        "items": [
            {"kind": "info", "text": "屏幕、舵机、外部电源全部断开，只接 USB。"},
            {"kind": "record", "text": "记录：实际串口路径", "hint": "优先 /dev/cu.wchusbserial* 或 /dev/cu.usbserial*；不要凭列表顺序选"},
            {"kind": "cmd", "text": "烧录固件", "cmd": "bash scripts/pio.sh run --target upload --upload-port 实际串口"},
            {"kind": "cmd", "text": "打开串口监视器", "cmd": "bash scripts/pio.sh device monitor --port 实际串口 --baud 115200"},
            {"kind": "gate", "text": "串口出现 READY / PASSIVE？",
             "remedy": "核对波特率 115200 与发送换行设置；烧录停在连接阶段就 BOOT+RESET 进下载模式重试。"},
            {"kind": "gate", "text": "selftest：Flash=8388608、PSRAM=8388608，64KiB PSRAM 样本 PASS？",
             "remedy": "PSRAM=0 或复位循环：先确认是同款 N8R8 板。配置已在编译期核对，实机仍为 0 则回报。"},
            {"kind": "gate", "text": "LED 短闪；按 BOOT 一次计数加一？",
             "remedy": "LED 在 GPIO48 低有效。无反应先查是否真的选对了串口。"},
            {"kind": "record", "text": "wifi scan 扫描到的 AP 数量", "hint": "0 个不足以单独判故障"},
        ],
    },
    {
        "id": "screen",
        "title": "阶段 5 · 屏幕与控件 3.3V",
        "items": [
            {"kind": "info", "text": "接线以 12 针 CSV 和 screen-wiring.svg 为准。SCL=GPIO12、SDA=GPIO11 是 SPI，不是 I2C。"},
            {"kind": "gate", "text": "全部接线已完成并复查，屏幕 VCC/BLK 都只在外部 3.3V 上（没有一处接 5V）？",
             "remedy": "再次确认。RevA 是 5V，当前是 RevB，接错可能直接损坏屏幕。"},
            {"kind": "gate", "text": "USB 先上电、固件已在 PASSIVE，现在才开外部 3.3V？",
             "remedy": "顺序必须是 USB 先上。反了就是带电插拔，且可能经信号倒灌未供电的主控。"},
            {"kind": "record", "text": "记录：模块端 VCC 对 GND 实测电压 (V)", "hint": "应接近 3.3"},
            {"kind": "record", "text": "记录：模块端 BLK 对 GND 实测电压 (V)", "hint": "固定全亮，应接近 3.3"},
            {"kind": "record", "text": "记录：屏幕全亮/刷新电流 (mA)", "hint": "未知项；测到才填。此值决定 RevB 的 JP3 能否短接"},
            {"kind": "cmd", "text": "启动屏幕", "cmd": "screen start"},
            {"kind": "gate", "text": "完整白边 + 红绿蓝白色条 + 横屏文字，无裁切/镜像？",
             "remedy": "只亮背光不显示：查 CS/DC/RES/SCL/SDA 与共地。没有 MISO，串口 SCREEN active 不证明屏幕正常。"},
            {"kind": "record", "text": "记录：最终 rotation（1 或 3）", "hint": "默认 3"},
            {"kind": "record", "text": "记录：最终 invert（0 或 1）", "hint": "默认 1；颜色次序仍错要记录照片与批次，不要用 invert 掩盖"},
            {"kind": "gate", "text": "编码器正转 10 格、反转 10 格计数对称，无多跳？",
             "remedy": "不匹配就比较 encoder divisor 2 与 4，记录最终值与方向。"},
            {"kind": "record", "text": "记录：最终 encoder divisor（2 或 4）", "hint": "默认 4"},
            {"kind": "gate", "text": "PUSH 与 KEY0 各按 10 次计 10 次，长按不连续增加？",
             "remedy": "PUSH=GPIO38(R13)、KEY0=GPIO40(R11)。模块自带 10k 上拉，固件不另开内部上拉。"},
        ],
    },
    {
        "id": "servo",
        "title": "阶段 6 · 单个 MG90S 5V",
        "items": [
            {"kind": "gate", "text": "已 stop、关外部电源、拔 USB，并拆掉屏幕全部接线？",
             "remedy": "必须先移走屏幕，避免误接到 5V。"},
            {"kind": "gate", "text": "舵盘和腿已卸下，舵机本体固定，轴不碰其他物体？",
             "remedy": "arm 的瞬间会直接回中位，带着腿可能撞到东西。"},
            {"kind": "gate", "text": "舵机 S=GPIO18、正极=外部 5V、负极=电源负极，开发板 GND(R9) 接同一负极？",
             "remedy": "信号常橙/黄/白、正极常红、负极常棕/黑，但必须先核对实际插头定义，不能只靠颜色。"},
            {"kind": "gate", "text": "USB 先上电确认 PASSIVE，然后才开外部 5V？",
             "remedy": "顺序反了就是带电插拔。"},
            {"kind": "cmd", "text": "输出中位 1500us", "cmd": "servo arm"},
            {"kind": "gate", "text": "首次回中位动作可接受，无持续堵转或异常发热？",
             "remedy": "堵转/抖动/发热立即关 5V，先查接线、压降和脉宽范围。"},
            {"kind": "cmd", "text": "小范围测试", "cmd": "servo pulse 1450 / servo pulse 1550 / servo pulse 1500，每次留时间观察"},
            {"kind": "gate", "text": "1400–1600us 范围内动作平稳，无持续堵转/异常发热？",
             "remedy": "不要在这一步做 0–180° 全行程扫描。异常就关 5V。"},
            {"kind": "record", "text": "记录：启动电流 (A)", "hint": "不等同 8 舵机负载"},
            {"kind": "record", "text": "记录：电源压降 (V)", "hint": "空载值减带载值"},
            {"kind": "gate", "text": "10 秒无有效命令后 PWM 停止，stop 也能停发？",
             "remedy": "预期行为。注意停 PWM 不等于断电，有些舵机仍保持位置。"},
        ],
    },
    {
        "id": "wrap",
        "title": "阶段 7 · 收尾",
        "items": [
            {"kind": "gate", "text": "已 stop → 关 5V/3.3V → 拔 USB 的受控顺序断电？",
             "remedy": "永远是先断外部电源再拔 USB，屏幕支路尤其严格。"},
            {"kind": "cmd", "text": "回填实测数据", "cmd": "把上面的记录填进 docs/实机验收记录.csv（22 行）"},
            {"kind": "info", "text": "三项通过只证明这三件模块能通。八舵机电源、整机承重、步态、电池充电电流仍未验证。"},
        ],
    },
]


def c(text, code):
    return f"\033[{code}m{text}\033[0m" if sys.stdout.isatty() else text


def list_serial_ports():
    patterns = ["/dev/cu.usbserial*", "/dev/cu.wchusbserial*", "/dev/cu.SLAB_USBtoUART*", "/dev/ttyUSB*", "/dev/ttyACM*"]
    found = sorted({p for pat in patterns for p in glob.glob(pat)})
    return found


def run_ports():
    found = list_serial_ports()
    print("候选串口：")
    if not found:
        print("  （未发现）板子还没插，或驱动/数据线有问题。")
        print("  该板可能同时出现 CH340 与原生 USB 两个串口，不要凭列表顺序选。")
        return 0
    for p in found:
        print("  " + p)
    print("\n优先选 CH340 对应的 wchusbserial / usbserial；用 bash scripts/pio.sh device list 复核。")
    return 0


def rehearse():
    print(c("═" * 66, "36"))
    print(c("  预演模式：走完全部步骤，不连接任何硬件，不写入记录", "36"))
    print(c("═" * 66, "36"))
    gates = records = 0
    for stage in STAGES:
        print("\n" + c(f"▌{stage['title']}", "1;36"))
        for item in stage["items"]:
            if item["kind"] == "info":
                print(f"  · {item['text']}")
            elif item["kind"] == "cmd":
                print(f"  $ {item['text']}\n      → {item['cmd']}")
            elif item["kind"] == "gate":
                gates += 1
                print(f"  {c('[门禁]', '33')} {item['text']}\n      预演判定：通过")
            elif item["kind"] == "record":
                records += 1
                print(f"  {c('[记录]', '32')} {item['text']}" + (f"  ({item['hint']})" if item.get("hint") else ""))
    print("\n" + c("═" * 66, "36"))
    print(f"预演结束：{len(STAGES)} 个阶段、{gates} 个安全门禁、{records} 项待记录。")
    print("门禁不通过时会停下并给出处置办法，不会让你带着短路继续上电。")
    print("到货后运行：python3 scripts/preflight_check.py")
    return 0


def interactive(start_stage, out_dir):
    stages = [s for s in STAGES if _index_of(s["id"]) >= start_stage]
    answers = []
    print(c("═" * 66, "36"))
    print(c("  通电前自检向导　y=通过／n=不通过（会给出处置）／q=退出", "36"))
    print(c("═" * 66, "36"))
    try:
        for stage in stages:
            print("\n" + c(f"▌{stage['title']}", "1;36"))
            for item in stage["items"]:
                kind = item["kind"]
                if kind == "info":
                    print(f"  · {item['text']}")
                    continue
                if kind == "cmd":
                    print(f"  $ {item['text']}\n      → {item['cmd']}")
                    answers.append((stage["title"], "cmd", item["text"], item["cmd"]))
                    continue
                if kind == "gate":
                    while True:
                        ans = input(f"  {c('[门禁]', '33')} {item['text']} [y/n/q]: ").strip().lower()
                        if ans in ("q", "quit"):
                            raise KeyboardInterrupt
                        if ans in ("y", "yes"):
                            answers.append((stage["title"], "gate", item["text"], "通过"))
                            break
                        if ans in ("n", "no"):
                            answers.append((stage["title"], "gate", item["text"], "不通过"))
                            print(c(f"  ✗ 停下：{item['remedy']}", "31"))
                            print("    修好后重跑：python3 scripts/preflight_check.py --from " + str(_index_of(stage["id"])))
                            _write_log(answers, out_dir, aborted=True)
                            return 1
                        print(f"  无法识别 {ans!r}；请输入 y（通过）/ n（不通过）/ q（退出）")
                elif kind == "record":
                    hint = f"  ({item['hint']})" if item.get("hint") else ""
                    val = input(f"  {c('[记录]', '32')} {item['text']}{hint}: ").strip()
                    answers.append((stage["title"], "record", item["text"], val or "待填"))
    except (KeyboardInterrupt, EOFError):
        print("\n已中断。")
        _write_log(answers, out_dir, aborted=True)
        return 130
    print("\n" + c("═" * 66, "36"))
    print("自检全部通过。可以进行下一步，并回填 docs/实机验收记录.csv。")
    _write_log(answers, out_dir, aborted=False)
    return 0


def _index_of(stage_id):
    for i, s in enumerate(STAGES):
        if s["id"] == stage_id:
            return i
    return 0


def _write_log(answers, out_dir, aborted):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    path = out_dir / f"preflight-log-{stamp}.md"
    lines = [
        "# 通电前自检记录",
        "",
        f"- 时间：{dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 结果：{'中断/未通过' if aborted else '全部通过'}",
        "- 说明：本文件由 scripts/preflight_check.py 生成；数值仍以 docs/实机验收记录.csv 为最终记录。",
        "",
        "| 阶段 | 类型 | 项目 | 结果 |",
        "|---|---|---|---|",
    ]
    for stage, kind, text, value in answers:
        lines.append(f"| {stage} | {kind} | {text} | {value} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n记录已写入：{path.relative_to(ROOT) if path.is_relative_to(ROOT) else path}")


def main():
    ap = argparse.ArgumentParser(description="通电前电学自检向导")
    ap.add_argument("--rehearse", action="store_true", help="预演全部步骤，不接硬件、不记录")
    ap.add_argument("--list", action="store_true", help="列出阶段")
    ap.add_argument("--ports", action="store_true", help="列出候选串口")
    ap.add_argument("--from", dest="start", type=int, default=0, help="从第 N 阶段开始（0 起）")
    ap.add_argument("--out", default=str(ROOT / "docs"), help="记录输出目录")
    args = ap.parse_args()

    if args.list:
        for i, s in enumerate(STAGES):
            print(f"{i}  {s['title']}")
        return 0
    if args.ports:
        return run_ports()
    if args.rehearse:
        return rehearse()
    return interactive(max(0, min(args.start, len(STAGES) - 1)), args.out)


if __name__ == "__main__":
    sys.exit(main())
