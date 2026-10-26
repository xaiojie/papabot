# 总装 V1 验证记录

验证日期：2026-09-07。对象：最终渲染流程保存后的 `desktop-assistant-assembly-v1.blend`。运行 Blender 5.2.1 LTS 后台重新打开文件，结果 **25 / 25**。验证器未保存或修改被验证的源文件。

源文件 SHA-256：`3987e973de94fb7fd8b52ad92566a54d572742aade9d99db66da6dc19f00d822`。

## 已完成的检查

| 检查 | 结果 |
| --- | --- |
| saved stage flag | 通过 |
| metric units | 通过 |
| supplier nominal PCB envelope | 通过 |
| display centered on body X axis | 通过 |
| body design width | 通过 |
| four PCB mounting centers are open | 通过 |
| single-mesh topology only | 通过 |
| cover / main hood sampled solids | 通过 |
| optical well / EC11 knob sampled solids | 通过 |
| speaker / main hood sampled solids | 通过 |
| left ear / hood sampled solids | 通过 |
| right ear / hood sampled solids | 通过 |
| PCB / four hip servo envelopes | 通过 |
| seven sampled front removal positions | 通过 |
| four disassembly display states | 通过 |
| framing HERO | 通过 |
| framing FRONT | 通过 |
| framing SIDE | 通过 |
| framing REAR | 通过 |
| framing FRONT_OPEN | 通过 |
| framing BOTTOM_OPEN | 通过 |
| framing EXPLODED | 通过 |
| framing LAYOUT | 通过 |
| fonts embedded | 通过 |
| native graphics dependency | 通过 |

完整数据见 [reopen-verification.json](reopen-verification.json)，文件指纹见 [verified-file.json](verified-file.json)。

150 个受检网格（不计摄影棚地面）在本次检查中没有非流形边或零面积面。31 个 `PRINT_CANDIDATE` 对象仍是候选几何，不等于 31 个可直接打印的生产件。

对以下指定对象做了实体相交体积检查：前盖/主壳、遮光井/旋钮、扬声器/主壳、左右耳/主壳、四个髋舵机占位/显示PCB，检测体积均小于 0.001 mm³。前盖与遮光井相对 PCB、旋钮和 LCD 外框在 0、2、5、10、20、40、85 mm 七个位移样本中的相交体积也均小于该阈值。此结果只针对这些对象与位置，不构成全机或连续路径无干涉证明。

正面、侧面、背面、整体、拆前盖、拆底盖、爆炸与内部布局共八张 1800×1350 PNG 已完成，并检查了可见实体投影边界不越出画面。主要视图又经人工看图复核。修改器顺序警告已消除；构建日志仍有 Blender API 的弃用提示，不影响本次 Blender 5.2.1 构建，未来版本需适配。

所用 Arial Unicode 字体已嵌入，内置 Bfont 无需打包；没有外部位图纹理依赖。实际后台重开和渲染成功；没有把桌面 UI 自动打开尝试记为成功证据。

## 已修正的问题

- 以一致的前端截面重建主壳，改善前盖接缝。
- 前盖定位柱与主壳配对接收结构已建模；通过避免共面布尔运算修复了主壳非流形问题。
- 耳键与耳体、托板支柱与托板合为对应几何；增加耳部配对孔。
- 增加屏幕支架的排针让位，调整扬声器占位远离后壳内壁。
- 四腿左右各外移 13 mm，使四个髋舵机占位避开偏置 PCB。机身仍为 118 mm 宽，当前含脚端包络宽 208 mm。
- P010 舵机连接区从打印候选降为隐藏线框占位；实际承载支架未完成，未将其画成已完成的固定件。
- 扩大爆炸与布局画幅，修正前视图地面条带。

## 本次不包含的验证

没有完成全部对象间碰撞矩阵、连续拆卸扫掠体检查、线束与插拔路径、紧固件与工具路径、最小壁厚、实际打印公差、强度/重心/步态、热/声学/电气验证、切片或实物试配。未选电子件和舵机的尺寸只是占位。主壳与腿的承载连接、底盖锁止、屏幕支架最终固定孔均待进一步设计。

`print_release = false`。结果允许交付本阶段外观、比例、空间占位与分件评审，不能据此向商家宣称已经具备打印生产或整机兼容性保证。

[独立审查历史](independent-review.md) 保留初审、第二轮失败与最终复核；本记录针对末次保存后的文件补齐了重开和哈希追溯。
