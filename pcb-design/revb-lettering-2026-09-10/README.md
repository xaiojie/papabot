# RevB PCB：Jay / 爬爬丝印版

2026-09-10 已在原嘉立创工程 `DesktopAssistant_RevA / Board1 / PCB1` 内添加并保存两个名字。电路版本仍为 RevB。

- [带名字的 Gerber 制板文件](DesktopAssistant_RevB_Jay_PaPa_Gerber.zip)
- [带名字的嘉立创原生工程](DesktopAssistant_RevB_Jay_PaPa.epro2)
- [实际 Gerber 正面预览](gerber-top-preview.png)（阻焊绿色仅为预览配色）
- [验证记录](verification.json)
- [原版电路、装配与上电说明](../native-rev-b/README.md)

名字在正面左上方，J7 左侧，约 3 mm 高，按普通白色丝印制作。`Jay` 为可编辑文字；`爬爬` 已转换为 6 块锁定的实心矢量丝印区域，确保不依赖另一台电脑的中文字库。两个名字共占约 13.32 × 3.00 mm，距上板边约 1.20 mm，距最近阻焊开窗的保守间距约 1.38 mm。

严格 PCB DRC 返回 0 项错误。新旧原生工程中，除文档时间/版本信息及新增的 7 个顶层丝印对象外，所有既有记录保持一致。实际 Gerber 的上下铜层、上下阻焊层、底层丝印和板框几何逐项一致；原有顶层丝印完整保留，129 个电镀孔（含 25 个过孔）及 4 个非电镀孔不变。新增中文 Gerber 区域面积与源矢量一致，已检查渲染字形。

本目录替代旧版的无名字 Gerber 作为当前文字版交付入口。原 RevB 电气、供电、实物针序和装配验证边界继续适用；本次是丝印更新，不代表新增实机验证。未下单。

修改前工程和 PCB 源文件保存在 `before/`。`chinese-outline.json` 保存可复用的中文字形；`verify_lettering.py` 用于对交付文件重新比对；`audit/` 保存本轮 API 操作记录。
