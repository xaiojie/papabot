# 旧 EC11 模块 STM8S 示例测试方法

供应商[原始文件](<../../pcb-design/native-rev-a/supplier-review-2026-09-09/sources/EC11资料/360度 旋转编码器模块/STM8S-IAR/测试方法.txt>)为 GBK 编码、CRLF 换行，原件按字节保留。本页仅转换编码和换行，方便在 GitHub 阅读，内容适用于供应商旧编码器示例。

```text
给LCTS-LCD烧程序
\STM8S-IAR\Project\Debug\Exe\ENCODE.hex
烧完屏幕上会显示500。
接线，从烧写端口给LCTS-LCD供电。 7P白色座子靠近缺口这边1脚是VCC接EC11的VCC，4脚接A,5脚接GND，6脚接B.
旋动EC11，顺时针数字变大，逆时针变小。
```
