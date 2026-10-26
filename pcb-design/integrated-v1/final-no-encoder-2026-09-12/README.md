# DesktopAssistant Integrated V1.2 · 无旋钮修订

2026-09-12。新版屏幕确定为 HS24S010B / C5329587，本目录替代 `final-2026-09-12` 中带 EC11 的旧交付。原理图、PCB 和制造文件均已取消旋钮电路。

## 修改内容

- 移除 EC1（EC1106S）及 R11 / R12 / R26 三个 10kΩ 上拉电阻。
- 删除 ENC_A、ENC_B、ENC_SW_N 三个网络；J1.13、J2.2、J2.8 改为有意不连接的 NC。
- 移除旋钮相关 77 段走线、4 个信号过孔和两个定位孔；清理专用的 3.3V、GND 分支。
- 补齐原旋钮区域上下层 GND 铜皮；其余器件位置、110×75 mm 板框、四个安装孔和接口位置沿用当前集成版。
- 保留 J3 屏幕线束接口，明确 BLK 为背光控制、FSO/FCS 为未使用的可选扩展。屏幕定义和资料矛盾详见接线说明。
- 原理图修订标记、PCB 丝印均为 V1.2；保留 Jay 丝印及电源、接口方向标记。

## 文件入口

| 文件 | 用途 |
|---|---|
| [DesktopAssistant_Integrated_final.epro2](DesktopAssistant_Integrated_final.epro2) | 五页原理图、PCB 与工程库，可继续编辑 |
| [Integrated_schematic_final.pdf](Integrated_schematic_final.pdf) | 当前五页原理图，逐页渲染复核 |
| [DesktopAssistant_Integrated_Gerber_review.zip](DesktopAssistant_Integrated_Gerber_review.zip) | Gerber、钻孔、槽孔和飞针数据 |
| [PCB_Gerber_Top.png](PCB_Gerber_Top.png) / [PCB_Gerber_Bottom.png](PCB_Gerber_Bottom.png) | 从实际制造文件绘制的正反面图，颜色仅供展示 |
| [板载BOM_79器件.csv](板载BOM_79器件.csv) / [采购BOM_合并同料.csv](采购BOM_合并同料.csv) | 79 个器件、36 种物料，价格库存未刷新 |
| [引脚网络表_310引脚.csv](引脚网络表_310引脚.csv) / [接口引脚表.csv](接口引脚表.csv) | 当前逐针连接资料 |
| [装配与接线说明.md](装配与接线说明.md) | HS24S010B 接线、电源隔离和板外物料 |
| [器件坐标_结构参考.csv](器件坐标_结构参考.csv) | 毫米坐标；原点左上，X 向右、Y 向下 |

## 核验结果

| 项目 | 结果 |
|---|---|
| 原理图 / PCB 原生 DRC | 错误结果为空，严格检查均返回 true |
| 器件 / 引脚 / 有连接网络 | 79 / 310 / 59 |
| NC / 单引脚孤立网络 | 48 / 0 |
| 原理图与 PCB 连接 | 310 个引脚逐一一致；其余连接与前版一致 |
| 电气独立核对 | 保护、充电、供电隔离、舵机等 15 项通过 |
| 走线 / 过孔 / 接地 Fill | 787 段（顶 608、底 179）/ 84 个 / 10 块 |
| 钻孔 | 203 个金属化圆孔，含 84 个过孔；4 个 USB-C 槽孔；7 个非金属化孔，含四个安装孔 |
| 制造孔径 | J1.13、J2.2、J2.8 已恢复为 1.2 mm；逐孔与封装核对通过 |
| 位置数值精度 | 原生封装与钻孔文件最大坐标差约 0.001161 mm，核验容差 0.003 mm |
| 贴片焊盘 | 187 个，均有锡膏与阻焊开口 |
| 飞针数据 | 连接网络一致，48 个 NC 引脚彼此独立 |
| 保存包与制造包 | CRC、原生几何、钻孔/槽孔、铜线及铜皮覆盖核验通过 |

数据见 `Schematic_verification.json`、`PCB_DRC_final.json`、`Native_archive_verification.json`、`Gerber_verification.json`。

`Delivery_text_verification.json` 独立确认交付工程只删除八条已记录的旧文字，所有电气与 PCB 记录保持一致，PDF 内容流与对应修订操作相符。`SHA256SUMS.txt` 包含本目录交付文件的 SHA-256，可用于解压后校验。

## 编辑与导出说明

接地铜皮沿用原生静态 Fill 多边形，不能随布线自动更新。移动器件或修改走线后需重新生成/修整铜皮，再做 DRC 和制造文件检查。不要重跑历史脚本覆盖当前设计。

EDA 3.2 的导出缓存保留了八个已在画布中替换的旧文字记录。交付 epro2 与 PDF 已仅清除这些废弃文字，所有电气记录、PCB 数据和其他 PDF 绘图操作保留；处理记录见 `Export_text_normalization.json`。重新从当前应用导出时，应再次检查是否出现旧标题重叠；后续编辑以本目录的修订工程为准。

原生归档可能将角度 -90° 写成 270°、保留 35 段不足 0.002 mm 的旧端点线并规范化默认铜皮规则；检查器确认这些短线位于同网络已有铜的 0.002 mm 范围内，其余几何与规则相符，明细在归档核验报告中。

本板仍为 2 层 FR-4、1.6 mm、2oz，110×75 mm。尚未打样、焊接或进行实物电源、温升、屏幕点亮和整机装配测试。HS24S010B 的实际丝印针序和外壳开窗尺寸仍需实物确认，不能由 DRC 代替。
