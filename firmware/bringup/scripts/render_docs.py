"""Deterministic, offline SVG/HTML wiring guide. No remote assets or JavaScript libs."""
from html import escape
from pathlib import Path

FONT = "'PingFang SC','Microsoft YaHei',system-ui,sans-serif"
COLORS = {"ground": "#475569", "power": "#d04d38", "spi": "#2c65b7", "input": "#008773"}


def text(x, y, content, size=20, color="#192a3b", weight=400, extra=""):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" font-weight="{weight}" {extra}>{escape(str(content))}</text>'


def rect(x, y, w, h, fill="#fff", stroke="#dce4ea", radius=14):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke}"/>'


def svg_start(height, title):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1240 {height}" role="img" aria-label="{escape(title)}" style="font-family:{FONT}"><title>{escape(title)}</title><rect width="1240" height="{height}" fill="#f5f8fa"/>'


def screen_svg(data):
    s = [svg_start(1110, "屏幕与控件：外部3.3V，12针逐根连接"), text(50, 57, "02  屏幕、旋钮和按键", 30, weight=700),
         text(50, 94, "逐针连接示意 · 左侧按功能排列，不代表开发板实物针序", 18, "#627283"),
         rect(50, 126, 544, 99), text(75, 164, "电脑 USB → 开发板 USB-C", 24, weight=600),
         text(75, 199, "主控由 USB 供电，3V3 / 5V 排针不接外部正极", 17, "#627283"),
         rect(618, 126, 572, 99, "#fff4ee", "#edc5b7"), text(642, 164, "可调电源 → 稳压 3.3 V", 24, "#b0412d", 600),
         text(642, 199, "VCC、BLK 接同一正极；负极与开发板共地", 17, "#884d40"),
         text(65, 279, "接到哪里", 20, weight=700), text(870, 279, "屏幕模块 12 针", 20, weight=700)]
    for index, pin in enumerate(data["screen"]["pins"]):
        y = 321 + index * 46
        color = COLORS[pin["kind"]]
        if pin["gpio"] is not None:
            label = f'开发板 GPIO{pin["gpio"]}   ·   {pin["position"]}'
        elif pin["kind"] == "ground": label = "电源负极 + 开发板 GND（L7）"
        else: label = "外部 3.3 V 正极（同一路）"
        s.extend([f'<g data-wire="{pin["pin"]}" class="wire">', rect(50, y - 24, 480, 40, "#fff", "#e0e6eb", 7),
                  text(67, y + 3, label, 19, color, 500),
                  f'<path d="M530 {y-4} H855" fill="none" stroke="{color}" stroke-width="3"/>',
                  f'<circle cx="530" cy="{y-4}" r="5" fill="{color}"/><circle cx="855" cy="{y-4}" r="5" fill="{color}"/>',
                  rect(855, y - 24, 335, 40, "#fff", "#e0e6eb", 7),
                  text(873, y + 3, f'{pin["pin"]:02d}  {pin["label"]}', 20, color, 600), "</g>"])
    s.extend([rect(50, 890, 1140, 176, "#eaf4f1", "#bfdace"),
              text(75, 926, "按这个顺序上电", 21, "#166253", 700),
              text(75, 959, "接好线 → USB 上电 → 确认 PASSIVE → 开 3.3V → 输入 screen start", 19),
              text(75, 993, "结束：stop → 关外部 3.3V → 拔 USB；改线前全部断电。", 19),
              text(75, 1030, "SCL / SDA 是 SPI 时钟 / MOSI；RES 接 GPIO21；模块自带控件上拉。", 17, "#536775"),
              text(50, 1093, "bench-v1 · 基于 RevB 屏幕接口表 · 仍须按实物丝印核对方向；没有测得最大背光电流。", 15, "#627283"), "</svg>"])
    return "".join(s)


def board_svg(data):
    s = [svg_start(650, "开发板自检：仅连接电脑USB"), text(50, 57, "01  只测试开发板", 30, weight=700),
         text(50, 94, "先确认烧录、串口和主控正常，再接屏幕与舵机。", 19, "#627283"),
         rect(60, 155, 375, 200), text(91, 205, "电脑", 30, weight=700), text(91, 254, "复用现有 USB 数据线", 22),
         text(91, 297, "UART0 / CH340 · 115200", 20, "#627283"),
         '<path d="M435 254 H798" fill="none" stroke="#2c65b7" stroke-width="6"/>', text(535, 233, "USB 数据 + 供电", 19, "#2c65b7"),
         rect(798, 155, 382, 200, "#eaf4f1", "#bfdace"), text(827, 205, "立创 ESP32S3R8N8", 25, "#166253", 600),
         text(827, 252, "USB-C 插口", 23), text(827, 298, "8MB Flash + 8MB OPI PSRAM", 18, "#536775"),
         rect(60, 400, 1120, 187), text(87, 440, "这一步不接外部电源、屏幕或舵机。", 24, weight=600),
         text(87, 481, "烧录后打开串口，依次输入：help → selftest → wifi scan", 21),
         text(87, 520, "观察 LED 闪烁；正常启动后按 BOOT，检查串口计数。", 21),
         text(87, 559, "预期：芯片 / Flash / PSRAM 信息与自检结果；这是到货后的验收项目。", 18, "#627283"),
         text(60, 625, "程序编译验证与实物测试分开记录；现在没有连接或烧录任何开发板。", 17, "#627283"), "</svg>"]
    return "".join(s)


def servo_svg(data):
    s = [svg_start(910, "双舵机：外部5V供电，GPIO18/GPIO15信号，共地"), text(50, 57, "03  双舵机，GPIO18 + GPIO15", 30, weight=700),
         text(50, 94, "先断电并拆下屏幕的全部接线，再将外部电源调到 5.0 V。", 20, "#b0412d", 600),
         rect(50, 131, 540, 109), text(75, 173, "开发板继续用电脑 USB 供电", 24, weight=600),
         text(75, 211, "只引出 GPIO18 / GPIO15 和 GND，不给舵机供电", 18, "#627283"),
         rect(614, 131, 576, 109, "#fff4ee", "#edc5b7"), text(639, 173, "外部电源稳压 5.0 V → 两个舵机", 24, "#b0412d", 600),
         text(639, 211, "两根红线并联取 5V；GND 必须与开发板共地", 18, "#884d40"),
         text(67, 299, "接到哪里", 20, weight=700), text(853, 299, "MG90S 三根线", 20, weight=700)]
    rows = [("GPIO18（R8）· 舵机1 信号", "信号 S · 常见橙 / 黄 / 白", "#2c65b7"),
            ("GPIO15（R5）· 舵机2 信号", "信号 S · 常见橙 / 黄 / 白", "#3b7fd4"),
            ("外部 5.0 V 正极（两舵机并联）", "正极 + · 常见红色", "#d04d38"),
            ("电源负极 + 开发板 GND（R9）", "负极 − · 常见棕 / 黑", "#475569")]
    for n, (left, right, color) in enumerate(rows):
        y = 359 + n * 70
        s.extend([rect(50, y - 29, 480, 58, radius=8), text(68, y + 7, left, 20, color, 500),
                  f'<path d="M530 {y} H817" stroke="{color}" stroke-width="4"/><circle cx="530" cy="{y}" r="6" fill="{color}"/><circle cx="817" cy="{y}" r="6" fill="{color}"/>',
                  rect(817, y - 29, 373, 58, radius=8), text(835, y + 7, right, 20, color, 600)])
    s.extend([rect(50, 668, 1140, 200, "#eaf4f1", "#bfdace"), text(75, 706, "两个舵机都先卸下舵盘和腿，固定舵机本体。", 22, "#166253", 700),
              text(75, 745, "USB → 确认 PASSIVE → 开 5V → servo arm → servo pulse 1100 / 1900（两路一起）", 20),
              text(75, 782, "只动一路：servo pulse 0 1100 ／ servo pulse 1 1900；允许 1000–2000μs。", 20),
              text(75, 819, "10 秒无有效控制命令停止 PWM；stop / ! 可提前停止。停止 PWM 不会切断舵机电源。", 18),
              text(50, 893, "GPIO18/GPIO15 是桌面试验脚；整机八舵机仍走 PCA9685。颜色仅供参考，以实际插头定义为准。", 17, "#627283"), "</svg>"])
    return "".join(s)


def render_docs(root: Path, data, positions):
    svgs = {"board": board_svg(data), "screen": screen_svg(data), "servo": servo_svg(data)}
    diagrams = root / "docs/diagrams"
    diagrams.mkdir(parents=True, exist_ok=True)
    for name, content in svgs.items():
        (diagrams / f"{name}-wiring.svg").write_text(content)
    rows = []
    for p in data["screen"]["pins"]:
        rows.append(f'<tr data-wire="{p["pin"]}"><td>{p["pin"]}</td><td><b>{escape(p["label"])}</b></td><td>{escape(p["target"])}</td><td>{escape(p["position"])}</td></tr>')
    physical_rows = []
    for i in range(20):
        left, right = positions[i], positions[i + 20]
        physical_rows.append(f'<tr><td>{left["本项目位置"]}</td><td>{left["厂家丝印"]}</td><td>{right["本项目位置"]}</td><td>{right["厂家丝印"]}</td></tr>')
    html = '''<!doctype html>
<html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>桌面助手 · 开发测试接线与程序</title>
<style>
:root{--ink:#1c2f42;--muted:#617383;--line:#dbe5e9;--mint:#087764;--paper:#f4f7f8}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font-family:"PingFang SC","Microsoft YaHei",system-ui,sans-serif;line-height:1.65}main{max-width:1240px;margin:auto;padding:40px 28px 70px}header{display:flex;justify-content:space-between;gap:30px;align-items:flex-start}.eyebrow{font-size:13px;letter-spacing:.12em;color:var(--mint);font-weight:700}h1{font-size:34px;line-height:1.35;margin:10px 0 14px}h2{font-size:23px;margin:0 0 12px}h3{font-size:18px;margin:0 0 10px}p{margin:10px 0}.muted{color:var(--muted)}.badge{display:inline-block;padding:6px 12px;border-radius:6px;background:#e1efea;color:#166253;font-size:13px;white-space:nowrap}.status-badge{background:#fff0df;color:#9b5614}a{color:#076d88;text-underline-offset:3px}button{font:inherit;cursor:pointer}.tabs{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:28px 0 20px}.tabs button{border:1px solid var(--line);background:white;border-radius:10px;padding:16px;color:var(--ink);font-weight:600;text-align:left}.tabs button[aria-selected=true]{background:#0b7865;color:white;border-color:#0b7865}.tabs span{opacity:.8;font-size:13px;display:block;margin-top:2px}.panel{display:none}.panel.active{display:block}.card{background:#fff;border:1px solid var(--line);border-radius:13px;padding:24px;margin-top:20px}.diagram{padding:8px;overflow:auto}.diagram svg{width:100%;height:auto;display:block}.wire{transition:opacity .15s}.diagram.hovering .wire{opacity:.2}.diagram.hovering .wire.selected{opacity:1}.diagram .wire{cursor:pointer}.columns{display:grid;grid-template-columns:1fr 1fr;gap:20px}.columns>.card{margin-top:20px}.note{border-left:4px solid #d57e2a;background:#fff6ea;padding:14px 18px;margin:16px 0}.soft{background:#eaf4f1;border-left-color:#0b7865}ol,ul{padding-left:24px;margin:10px 0}li{margin:8px 0}code{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:.92em;background:#eef2f4;padding:2px 5px;border-radius:4px}pre{background:#172a3b;color:#e8f7f3;padding:18px;border-radius:8px;overflow:auto;line-height:1.7}pre code{background:transparent;padding:0;color:inherit}.scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-size:15px}th,td{text-align:left;padding:11px 13px;border-bottom:1px solid var(--line)}th{color:#446172;background:#f0f5f6}tbody tr[data-wire]{cursor:pointer}tbody tr.selected,tbody tr[data-wire]:hover{background:#e9f3ef}details{margin-top:22px}summary{cursor:pointer;font-weight:600}.download{display:flex;gap:14px;flex-wrap:wrap;font-size:14px;margin-top:12px}.toolbar{display:flex;gap:10px}.toolbar button{border:1px solid var(--line);background:white;border-radius:7px;padding:7px 13px;font-size:14px}.foot{font-size:13px;color:var(--muted);margin-top:25px}.kbd{font-size:13px;font-weight:700;border:1px solid #a3b6bf;padding:1px 5px;border-radius:3px}.checklist label{display:block;margin:8px 0}.checklist input{margin-right:8px}.print-all{font-size:13px}
@media(max-width:760px){main{padding:24px 14px}header{display:block}h1{font-size:28px}.tabs{gap:6px}.tabs button{padding:10px;font-size:14px}.columns{grid-template-columns:1fr;gap:0}.card{padding:17px}.diagram{padding:0}.diagram svg{min-width:760px}.toolbar{margin-top:10px}th,td{white-space:nowrap}}
@media print{body{background:white}main{max-width:none;padding:0}header{margin-bottom:20px}.tabs,.toolbar,.download{display:none}.panel,.panel.active{display:block;break-before:page}.card{box-shadow:none;border:1px solid #bbb;break-inside:avoid}.diagram svg{min-width:0}.columns{display:block}details{display:block}summary{display:none}.foot{color:#444}a{color:inherit}}
</style></head><body><main>
<header><div><div class="eyebrow">DESKTOP ASSISTANT · BENCH V1</div><h1>先在桌面上，把三个模块测通。</h1><p class="muted">立创 ESP32S3R8N8 + 2.4 寸 ST7789 / EC11 + 单个 MG90S。<br>不需要定制 PCB，按三个阶段接线、烧录与验收。</p></div><div><p><span class="badge">沿用 RevB 屏幕引脚</span></p><p><span class="badge status-badge">主控已实测通过 · 屏幕与舵机待测</span></p><div class="toolbar"><button onclick="window.print()">打印接线说明</button></div></div></header>
<nav class="tabs" role="tablist" aria-label="测试阶段"><button id="tab-board" role="tab" aria-controls="board" aria-selected="false" tabindex="-1" data-tab="board">01 · 开发板自检<span>只接 USB，先测芯片和存储器</span></button><button id="tab-screen" role="tab" aria-controls="screen" aria-selected="true" data-tab="screen">02 · 屏幕和控件<span>外部 3.3V，逐根接 12 针</span></button><button id="tab-servo" role="tab" aria-controls="servo" aria-selected="false" tabindex="-1" data-tab="servo">03 · 双舵机<span>外部 5V，GPIO18/GPIO15，空载动作</span></button></nav>
<section id="board" class="panel" role="tabpanel" aria-labelledby="tab-board"><div class="card diagram">__BOARD__</div><div class="columns"><article class="card"><h2>到货后先做这一步</h2><ol><li>暂不接屏幕、舵机、外部电源。检查开发板外观。</li><li>用现有 USB 数据线连接电脑与开发板 USB-C。</li><li>按 <a href="../README.md">工程说明</a>烧录。macOS 不带 CH34x 驱动，优先用原生 USB 口 <code>/dev/cu.usbmodem*</code> 配 <code>-e lckfb_s3_usbjtag</code>；串口波特率为 <code>115200</code>。</li><li>看到 <code>READY / PASSIVE</code> 后执行下方命令。如果漏掉开机提示，输入 <code>help</code>。</li></ol><pre><code>help
selftest
wifi scan
status
wifi connect 你的SSID 你的密码
net test</code></pre></article><article class="card"><h2>应该看到什么</h2><ul><li><code>selftest</code> 显示 ESP32-S3、8 MB Flash、8 MB PSRAM，并检查一块 64 KiB PSRAM。</li><li>板载 LED 每秒短闪一次；正常启动后按 BOOT，串口按压计数增加。</li><li>Wi-Fi 命令扫描 2.4 GHz 网络并逐个打印 RSSI / 信道 / 加密方式，不保存账号密码；RSSI 是天线与 RF 通路的实测依据，扫描结果为零需要结合现场环境判断。</li><li><code>wifi connect</code> 做一次性联通测试：口令不回显、只存 RAM、不写 NVS，<code>WiFi.persistent(false)</code> 已显式关闭持久化；复位后即失效。<code>net test</code> 依次验证 DNS、TCP:80 与 HTTP GET（含耗时），比 ICMP 更能说明端到端连通。</li></ul><p class="note soft">这一步能在排针未焊时先做。屏幕与舵机没有接上，便于排除连接问题。</p></article></div></section>
<section id="screen" class="panel active" role="tabpanel" aria-labelledby="tab-screen"><div class="card diagram screen-diagram">__SCREEN__</div><div class="download"><a href="diagrams/screen-wiring.svg">打开高清 SVG</a><a href="屏幕12针接线表.csv" download>下载 12 针接线表</a><a href="开发测试接线与验收.md">完整操作说明</a><a href="通电前自检与故障对照.md">通电前自检与故障对照</a><a href="assistant-ui-prototype.html">⭐ 双程序 UI 原型（表情/时钟/天气/状态）</a><a href="screen-simulator.html">bench-v1 屏幕预览</a></div><div class="columns"><article class="card"><h2>接线和供电</h2><ol><li>断开 USB、关闭外部电源。按模块丝印核对 12 个端子并接线。</li><li>外部电源先空载调到 <b>3.3V</b> 并测量，输出关闭后再接 VCC / BLK / GND。</li><li>接 USB，确认固件待机，再开启外部 3.3V。测模块端 VCC、BLK 电压。</li><li>输入 <code>screen start</code>，测试色条、旋钮和两个按键。</li><li>结束时输入 <code>stop</code>，先关外部 3.3V，再拔 USB。</li></ol><p class="note">开发板 3V3 输出与外部 3.3V 正极不要相连。电源负极、屏幕 GND、开发板 GND 必须共地。</p></article><article class="card"><h2>屏幕测试命令</h2><pre><code>screen start
status
# 倒置时，再选另一横屏方向：
screen rotation 1
# 黑白反相时，切换观察：
screen invert 0
# 每格计数不符时，比较 2 / 4：
encoder divisor 2
stop</code></pre><p class="muted">带 # 的行是说明，不要输入。默认横屏 rotation=3、invert=1、divisor=4。方向、颜色和每格计数仍需实物确认。</p><p>旋钮计数显示为 <code>ENC</code>；按下旋钮看 <code>PUSH</code>；独立按键看 <code>KEY0</code>。<code>stop</code> 后背光可能仍亮，因为 BLK 直接接 3.3V。</p></article></div><article class="card"><h2>逐根核对表</h2><p class="muted">点一行或图中的接线，可突出对应关系。GPIO 数字以丝印为准；不要套用别的 ESP32 开发板针位。</p><div class="scroll"><table><thead><tr><th>模块针号</th><th>丝印</th><th>接到哪里</th><th>开发板位置</th></tr></thead><tbody id="pin-table">__ROWS__</tbody></table></div></article></section>
<section id="servo" class="panel" role="tabpanel" aria-labelledby="tab-servo"><div class="card diagram">__SERVO__</div><div class="download"><a href="diagrams/servo-wiring.svg">打开高清 SVG</a></div><div class="columns"><article class="card"><h2>先把屏幕拆下，再测舵机</h2><ol><li><code>stop</code> → 关外部电源 → 拔 USB。拆下屏幕全部接线。</li><li>把外部电源调到 <b>5.0V</b>，测量后关闭输出，再接两个舵机。</li><li>两个舵机的正负线都直接去电源（<b>红色线 5V 并联</b>）。GPIO18 / GPIO15 只传信号，开发板 GND 接电源负极。</li><li>首次拆下舵盘和腿，固定舵机本体。接 USB 后再开 5V，输入 <code>servo arm</code>。</li></ol><p class="note">启用时两个舵机可能直接回到中位。舵机电流不经过开发板、普通面包板电源条或多段细杜邦线。</p></article><article class="card"><h2>双舵机命令</h2><pre><code>servo arm
servo pulse 1100
servo pulse 1900
servo pulse 0 1100
servo pulse 1 1900
servo stop</code></pre><p><code>servo pulse &lt;us&gt;</code> 动<b>两路</b>；<code>servo pulse &lt;编号&gt; &lt;us&gt;</code> 只动一路（0=GPIO18，1=GPIO15）。每条命令之间观察约一两秒；允许 1000–2000μs。10 秒没有有效脉宽命令会停发 PWM，再次测试须重新 <code>servo arm</code>。</p><p><span class="kbd">!</span> 不用按回车即可停发 PWM。<b>停止信号不等于断电</b>，若持续抖动、发热或堵转，关闭 5V 电源检查。</p><p class="muted">现有电源的 5V 电流能力要核实，两个舵机同时动建议留 2A 以上余量；实际需求以测量为准。</p></article></div></section>
<article class="card"><h2>排针和连接线，准备这些就能开始</h2><div class="columns"><div><h3>焊在哪里</h3><ul><li><b>开发板：</b>若两条长边是空孔，每边焊 1×20P、2.54mm 排针。已焊版本不用重复。</li><li><b>屏幕：</b>在原板左侧短边、两个固定孔之间的 12 孔接口，焊配套 1×12P、2.54mm 排针。先对照 GND / VCC 丝印，确认排针伸出方向。</li><li>短脚穿 PCB 焊接，长脚用来插杜邦母头；最终外壳高度与朝向还需按实物试装。</li></ul></div><div><h3>用哪些线</h3><ul><li>屏幕 ↔ 开发板：母对母杜邦线，优先短线约 10–20cm。</li><li>舵机母插头 ↔ GPIO / 接头：适当公头转接；正负主线用短线和牢靠的电源接头。</li><li>电源 ↔ 模块：匹配电源端子的引线、分线端子；将一组 3.3V 分给屏幕 VCC 和 BLK。</li><li>复用现有 USB 数据线；本次无需电池、充电板或定制 PCB。</li></ul></div></div><p class="muted">先焊一针调正，再焊其余。断电检查焊点、相邻脚连锡与正负极短路。图中的编号是功能顺序，不可据此猜正反面。</p></article>
<details class="card"><summary>展开开发板针位参考 · 元件面朝上，天线在上，USB 在下</summary><p>本项目 L/R 编号按各列从上到下 1–20，属于位置记号，不是厂家的 J1/J2 原理图脚号。实物版本如不一致，先按实际资料核对。</p><div class="scroll"><table><thead><tr><th>左侧位置</th><th>丝印</th><th>右侧位置</th><th>丝印</th></tr></thead><tbody>__PHYSICAL__</tbody></table></div></details>
<article class="card"><h2>验收记录</h2><p>当前状态为待实测。把真实结果填入 <a href="实机验收记录.csv" download>实机验收记录 CSV</a>，后续才能判断是否进入显示界面、联网语音和步态开发。</p><p class="muted">本机编译、行为测试与引脚比对结果另见 <a href="验证记录.md">验证记录</a>。这份程序不包含完整语音助手、中文 UI 或四足步态。</p><p class="muted">上电前先走一遍 <a href="通电前自检与故障对照.md">通电前自检与故障对照</a>：终端运行 <code>python3 scripts/preflight_check.py --rehearse</code> 可先预演全部步骤。</p></article>
<footer class="foot">资料依据：当前 RevB 屏幕接口表、所购模块供应商程序、立创开发板原理图与针位资料。bench-v1 · 2026-09-09。所有电源时序、负载、实际插头方向与动作范围都需要到货后核实。</footer>
</main><script>
const tabs=[...document.querySelectorAll('[data-tab]')];
function selectTab(name){tabs.forEach(b=>{const yes=b.dataset.tab===name;b.setAttribute('aria-selected',String(yes));b.tabIndex=yes?0:-1;});document.querySelectorAll('.panel').forEach(p=>p.classList.toggle('active',p.id===name));}
tabs.forEach((b,i)=>{b.addEventListener('click',()=>selectTab(b.dataset.tab));b.addEventListener('keydown',e=>{if(!['ArrowLeft','ArrowRight','Home','End'].includes(e.key))return;e.preventDefault();let j=e.key==='Home'?0:e.key==='End'?tabs.length-1:(i+(e.key==='ArrowRight'?1:-1)+tabs.length)%tabs.length;selectTab(tabs[j].dataset.tab);tabs[j].focus();});});
const wires=[...document.querySelectorAll('[data-wire]')];let picked=null;
function highlight(id){document.querySelector('.screen-diagram').classList.toggle('hovering',!!id);wires.forEach(w=>w.classList.toggle('selected',w.dataset.wire===id));}
wires.forEach(w=>{w.addEventListener('mouseenter',()=>highlight(w.dataset.wire));w.addEventListener('mouseleave',()=>highlight(picked));w.addEventListener('click',()=>{picked=picked===w.dataset.wire?null:w.dataset.wire;highlight(picked);});});
window.addEventListener('beforeprint',()=>document.querySelectorAll('details').forEach(d=>{d.dataset.wasOpen=d.open?'1':'0';d.open=true;}));
window.addEventListener('afterprint',()=>document.querySelectorAll('details').forEach(d=>d.open=d.dataset.wasOpen==='1'));
</script></body></html>'''
    replacements = {"__BOARD__":svgs["board"], "__SCREEN__":svgs["screen"], "__SERVO__":svgs["servo"],
                    "__ROWS__":"".join(rows), "__PHYSICAL__":"".join(physical_rows)}
    for key, value in replacements.items(): html = html.replace(key, value)
    (root / "docs/index.html").write_text(html)
