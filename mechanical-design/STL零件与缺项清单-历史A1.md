# STL文件与整机装配缺项核对

核对日期：2026-09-08。扫描整个“自研桌面助手”工作目录，实际找到12个STL：6个结构草稿、6个试配样件。目前没有完整的整机装配打印包。

以下尺寸直接读取当前STL，顺序为导出时的X×Y×Z，单位mm；已经按打印方向旋转，不能直接当整机前后左右尺寸。这里只核对文件、用途和包络，没有重新执行切片、实物试装或承载试验。

## 已有结构零件草稿

| 件号 | 实际文件 | 用途 | 每台计划数量 | STL包络mm |
|---|---|---|---:|---|
| R01 | [R01__main_housing__DRAFT_mm.stl](print-v2/stl-structure-a1-DRAFT/R01__main_housing__DRAFT_mm.stl) | 主外壳：顶部、左右侧壁、后部框架；前盖、底盖单独安装 | 1 | 124.00×74.07×68.50 |
| R02 | [R02__shallow_front_cover__DRAFT_mm.stl](print-v2/stl-structure-a1-DRAFT/R02__shallow_front_cover__DRAFT_mm.stl) | 浅前盖：屏幕开窗和定位边 | 1 | 124.00×76.00×4.40 |
| R03 | [R03__rear_controls_panel_BLANK__DRAFT_mm.stl](print-v2/stl-structure-a1-DRAFT/R03__rear_controls_panel_BLANK__DRAFT_mm.stl) | 可拆后面板：有喇叭网孔，旋钮/按键/总开关/充电口尚未完善 | 1 | 98.00×58.00×2.40 |
| R04 | [R04__display_support_frame__DRAFT_mm.stl](print-v2/stl-structure-a1-DRAFT/R04__display_support_frame__DRAFT_mm.stl) | 完整91×44mm屏幕板的内部固定支架 | 1 | 106.50×66.00×5.60 |
| R05 | [R05__bottom_cover_integrated_battery_tray__DRAFT_mm.stl](print-v2/stl-structure-a1-DRAFT/R05__bottom_cover_integrated_battery_tray__DRAFT_mm.stl) | 底盖与电池限位托架一体件，电池目标75×40×20mm待商家确认 | 1 | 110.00×62.70×6.80 |
| R06 | [R06__controller_carrier_bridge__DRAFT_mm.stl](print-v2/stl-structure-a1-DRAFT/R06__controller_carrier_bridge__DRAFT_mm.stl) | 自研80×32mm主控PCB支撑桥架，需按最终PCB及叠装高度复核 | 1 | 108.00×42.00×29.40 |

上述6件均为DRAFT结构草稿；文件存在不表示已完成全部接口、安装顺序和整机空间验收。电池托架已集成R05，不重复计作缺少一件。

## 已有试配样件

| 件号 | 实际文件 | 用途 |
|---|---|---|
| T01 | [T01__display_hole_pitch_frame__mm.stl](print-v2/stl/T01__display_hole_pitch_frame__mm.stl) | 检查屏幕板84.5×37.5mm四孔孔距；不装入整机 |
| T02 | [T02__M2_nut_fit_coupon__mm.stl](print-v2/stl/T02__M2_nut_fit_coupon__mm.stl) | 试M2螺母槽的松紧：对边4.1/4.2/4.3mm |
| T03 | [T03__M3_nut_fit_coupon__mm.stl](print-v2/stl/T03__M3_nut_fit_coupon__mm.stl) | 试M3螺母槽的松紧：对边5.6/5.7/5.8mm |
| T04A | [T04A__MG90S_body_opening_gauge__mm.stl](print-v2/stl/T04A__MG90S_body_opening_gauge__mm.stl) | MG90S机壳开口试配：23.4×12.8mm |
| T04B | [T04B__MG90S_body_opening_gauge__mm.stl](print-v2/stl/T04B__MG90S_body_opening_gauge__mm.stl) | MG90S机壳开口试配：23.8×13.2mm |
| T04C | [T04C__MG90S_body_opening_gauge__mm.stl](print-v2/stl/T04C__MG90S_body_opening_gauge__mm.stl) | MG90S机壳开口试配：24.2×13.6mm |

T04A/B/C是三档间隙样件，不是三种正式舵机支架。试配样件不计入整机装配数量。

## 缺少的可装配打印结构

| 部位 | 还缺什么 | 数量/状态 |
|---|---|---|
| 四条腿 | 机身上的髋舵机固定座、上腿连杆、膝舵机固定座、下腿和脚掌，以及舵盘连接/必要限位 | 当前规划前四类各4件；可合并分件，最终数量由关节方案确定。旧Blender中有外观占位，没有对应正式STL |
| 小耳朵 | 左右耳框、内片及可靠固定接口 | 耳框2件、内片2件；也可合并后配色。已有旧模型，尚未整理为装配STL |
| 后部控件 | EC11和独立按键的固定座/压片，以及总开关、充电口的安装结构 | R03目前控件区留白，孔位和支架仍需设计 |
| 电源模块 | DFR0753、好盈UBEC的固定座；充电板固定座；保险座/XT30线束固定 | 降压座2处、充电座1处；其余可集成底盘或内支架 |
| 舵机驱动与功放 | PCA9685板固定座、MAX98357板固定座 | 各1处，可合并为内部安装架 |
| 音频 | 麦克风可换固定座与声孔、喇叭压圈/固定座 | 各1套；后盖已有喇叭网孔，但没有完整喇叭固定件 |
| 整机紧固与走线 | 底盘腿座加强、螺母装入/防脱、线束应力释放、必要通风与插拔空间 | 属于现有零件需补的结构特征，不一定新增STL |

前脸薄荷细边可在前盖上做后处理配色，不必再做薄小独立STL。外购舵机、电路板、电池、硅胶脚垫和金属紧固件不应作为打印件导出。

## 本轮进度边界

`structure-a2/scripts/build_structure_a2.py`仅建立了新版本脚本开头；被中断前尚未生成A2模型或STL，不计为完成件。旧V1、V2及A1文件保留。

后续按整机装配推进：先完成底盘与单腿连接，再补齐内部模块固定和后控件面板，最后统一检查壳体、PCB、紧固件与线束空间并逐件导出。
