# Rev A 离线布线交付

最终导入文件：`route-candidate.json`。这是供嘉立创EDA原生导入和 DRC 复核的布线候选，不是独立的生产文件。其他 `route-*.json` 是保留的尝试记录，部分使用旧规则或仍有未连通网络，不能作为交付版使用。

## 最终验收

- 21 个元件、98 个铜焊盘，其中 12 个 NC 铜焊盘保留避让。
- **25/25 网络全部连通，未连通组为零。**
- 93 条折线，共 736 个直线段；24 个过孔；TOP/BOTTOM 两层。
- 信号线 12 mil；`+5V_LOGIC`、`+5V_MCU`、`GND` 均 40 mil；`+3V3` 24 mil；低电流电池采样入口 `VBAT_SW` 32 mil。
- 最小异网铜净距 **8.009055 mil**，要求 ≥8 mil。
- 最小铜到板边/开槽边距离 **13.015748 mil**，要求 ≥12 mil。
- 最小铜到 Ø3.2 mm 安装孔孔边 **39.763780 mil（1.01 mm）**，要求 ≥0.9 mm，即避开半径 2.5 mm 的螺钉头区域。
- 最小钻孔孔边间距 **19.685076 mil（约 0.5 mm）**，所有钻孔无重叠。
- 5V、3V3、电池采样电源网络无独立换层过孔，必要换层通过对应镀通孔焊盘完成。GND 有 2 处换层，每处均加了第二个并联过孔，并使用 40 mil 线在两层连接。过孔均为焊盘 Ø0.6 mm、钻孔 Ø0.3 mm。
- 最终 SVG/PNG 按实际焊盘、铜线、过孔、板框和开槽绘制；已查看 PNG。

详细验收在 `route-candidate-validation.json`，逐网实际线宽在 `widths_by_net_mil`。

## 冻结输入

`../pcb-placed-pads.json` 始终未改动，SHA-256：

`79d20db7fc3ca2060349ffe2459e11c9de65ca11875596465acff966b948899f`

另使用原生 `pcb_PrimitivePad.getAll()` 导出的 `../pcb-free-pads.json` 复核真实坐标与钻孔，按 `primitiveId` 匹配全部 98 铜焊盘。其 SHA-256：

`c4f6bcb9f05b3eb39b156b02e0793cbebac90391268e3bf08578ae98ef2b6dda`

该文件共 102 个焊盘（含 4 个 NPTH）。与原输入最大中心位置差为 0.06058 mil，属于读取舍入差。最终净距、连通与钻孔检查使用此高精度数据。原 `getAllPins()` 的孔径存在除以 10 的读取问题，其孔径完全没有用于制造几何，也没有改动任何原生钻孔。

板框 80×32 mm；左侧 U 槽 x=0…24.17 mm、y=9.5…22.5 mm；安装孔中心为 (5,5)、(75,5)、(75,27)、(5,27) mm。所有 JSON 布线坐标和线宽单位均为 mil。

## 复现

在本目录执行，使用包含 numpy 的 Python，并将 Shapely 安装到本地 `_deps` 或解释器环境。当前工作使用 Codex 随附 Python 和本目录 `_deps/shapely`。

```sh
python3 route.py --priority 'ADC_BAT,ENC_B,LCD_RST_N,MIC_BCLK,PCA_OE_N,PCA_SCL,+3V3,+5V_LOGIC,GND' --prefix route-40mil-priority3
python3 finalize.py route-40mil-priority3
python3 route.py --validate-only
```

`route.py` 使用基础 5 mil 网格，加上实际焊盘中心及 100 mil 排针的针间中线。`finalize.py` 在精确几何检查允许时压缩折线，并补齐 GND 并联过孔。最终精确检查将圆焊盘和过孔表示为中心点加半径、走线表示为折线加半线宽、矩形焊盘表示为旋转矩形；净距结果不依赖圆弧多边形近似。只检查已有候选可用 `--validate-only`，两份源文件哈希不符时会拒绝验收。

`repair.py` 提供同网已有走线为目标的铜树接入修复；最终方案通过布线顺序完成全部连通，没有使用该修复结果。

## 原生交接边界

本目录工具从未调用 EDA、修改原生工程或操作 3D。主任务需导入 `route-candidate.json` 后运行嘉立创EDA原生 DRC，并检查导出制造文件。几何检查不代表电流/温升/压降、RF、阻抗、装配、阻焊或工厂工艺验收。并联过孔不构成额定载流证明；八个舵机与功放的供电仍走外部线束。

布线含少量非 45° 角度，是带净距验证的网格压缩结果。导入时应保留给定浮点坐标，不要先量化到整数 mil；最窄通道对坐标精度敏感。
