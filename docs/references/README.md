# 第三方资料索引

本项目使用的规格书、厂商参考图、供应商说明、例程摘录和选型截图随 Git 仓库保存，可以从下表查阅或下载。资料沿用所在模块的路径，避免重复复制大文件；完整文件清单及 SHA-256 见 [资料清单](资料清单.json)。

整理日期：2026-10-26。原始资料版本与适用对象按下文区分，历史屏幕或候选芯片资料不代表当前整机选型。

## 当前屏幕 HS24S010B

| 资料 | 仓库文件 | 来源与说明 |
|---|---|---|
| HS24S010B 完整规格书 | [原始 PDF](../../pcb-design/integrated-v1/datasheets/HS24S010B.pdf) | 用户提供的立创商品 C5329587 资料，原文件名 `C5329587_LCD显示屏_HS24S010B_规格书_WJ1068154.PDF`；文件内容原样保留 |
| 外形与封装 | [尺寸图](../../pcb-design/integrated-v1/datasheets/屏幕_HS24S010B_封装图.png) | 项目保留的供应商规格图 |
| 引脚定义 | [引脚图](../../pcb-design/integrated-v1/datasheets/屏幕_HS24S010B_引脚图.png) | 项目保留的供应商规格图 |
| 规格书逐页图与文字 | [提取目录](../../pcb-design/integrated-v1/no-encoder-2026-09-12) · [文字](../../pcb-design/integrated-v1/no-encoder-2026-09-12/LCD_datasheet_text.txt) | 16 页图及文字提取，便于查找；以原 PDF 为准 |
| 当前接线解释 | [装配与接线说明](../../pcb-design/integrated-v1/final-no-encoder-2026-09-12/装配与接线说明.md) | 本项目对资料矛盾和实际接线的解释，不是厂商原文 |

## 主控、PWM 与音频

| 对象 | 仓库文件 | 原始来源 |
|---|---|---|
| ESP32-S3 芯片 | [规格书](../../pcb-design/rev-a/sources/esp32-s3-datasheet.pdf) | [Espressif](https://www.espressif.com/sites/default/files/documentation/esp32-s3_datasheet_en.pdf) |
| LCKFB ESP32S3R8N8 开发板 | [规格书](../../pcb-design/rev-a/sources/lckfb-datasheet.pdf) · [原理图核心页](../../pcb-design/rev-a/sources/lckfb-schematic-core.jpg) · [封面页](../../pcb-design/rev-a/sources/lckfb-schematic-cover.jpg) | [立创商品资料](https://atta.szlcsc.com/upload/public/pdf/source/20241206/8BAF30E9665AF2DA28B66306BACEE9A0.pdf)；原理图图像来自厂家公开资料预览，完整出处见 [原资料记录](../../pcb-design/rev-a/sources/README.md) |
| PCA9685 PWM 芯片 | [规格书](../../pcb-design/rev-a/sources/pca9685-datasheet.pdf) | [NXP](https://www.nxp.com/docs/en/data-sheet/PCA9685.pdf) |
| MAX98357A/B 功放 | [规格书](../../pcb-design/rev-a/sources/max98357a-datasheet.pdf) | [Analog Devices](https://www.analog.com/media/en/technical-documentation/data-sheets/MAX98357A-MAX98357B.pdf) |
| 早期麦克风参考 | [SEN0327 所链 PDF](../../pcb-design/rev-a/sources/sen0327.pdf) · [商品页面快照](../../pcb-design/rev-a/sources/mic-product.html) | [DFRobot](https://www.dfrobot.com.cn/images/upload/File/20191224164325rhavtz.pdf)；PDF 实际为 Sipeed I2S_Mic，板型与商品页面有差异，不能当作 INMP441 所购模块的最终规格 |

## 电源、保护与充电

| 对象 | 仓库文件 | 来源与适用范围 |
|---|---|---|
| IP2326 升压充电 | [规格书](../../pcb-design/integrated-v1/repair-2026-09-12/IP2326.pdf) | 项目保存的芯片规格书，相关器件资料见 [立创条目](https://item.szlcsc.com/datasheet/IP2326/2988389.html) |
| HY2120 保护 | [规格书](../../pcb-design/integrated-v1/repair-2026-09-12/HY2120.pdf) | 项目保存的芯片规格书，相关器件资料见 [立创条目](https://item.szlcsc.com/datasheet/HY2120-CB/117763.html) |
| HY2213 均衡 | [规格书](../../pcb-design/integrated-v1/repair-2026-09-12/HY2213.pdf) | 项目保存的芯片规格书，相关器件资料见 [立创条目](https://item.szlcsc.com/datasheet/HY2213-BB3A/114867.html) |
| IP2325 / CN3302 | [IP2325](../../pcb-design/integrated-v1/repair-2026-09-12/IP2325.pdf) · [CN3302](../../pcb-design/integrated-v1/repair-2026-09-12/CN3302.pdf) | 历史充电方案对比资料；未补造未知的原始下载地址 |
| PW7120 / PW4584A | [规格书页图](../../pcb-design/integrated-v1/datasheets) | 历史保护/充电方案参考，目前保留的是选定页图 |
| 平芯微参考设计 | [原理图](../../pcb-design/integrated-v1/电源官方参考原理图.png) · [PCB](../../pcb-design/integrated-v1/电源官方参考PCB.png) · [PW4584A 原理图](../../pcb-design/integrated-v1/电源官方参考原理图_PW4584A版.png) · [PW4584A PCB](../../pcb-design/integrated-v1/电源官方参考PCB_PW4584A版.png) | 项目记录的 [厂商技术文章](https://www.pwchip.com/tw/product/632.html)，用于设计演进追溯 |
| DFR0753 降压模块 | [商品页快照](../../pcb-design/rev-a/sources/dfr0753-product.html) | [DFRobot 商品页](https://www.dfrobot.com.cn/goods-2971.html)，页面没有提供完整机械尺寸 |
| 电池与外置保护板 | [选型证据目录](../../hardware-selection/battery-stock-2026-09-09/evidence) · [YourCee 保护板 PDF](../../hardware-selection/battery-stock-2026-09-09/evidence/YourCee-67325-2S-protection.pdf) | 原采购参考图片和资料，不能视为当前库存或实测电流 |

## 旧屏幕、编码器与供应商例程

以下资料适用于旧 TOUGLESY ST7789 + EC11 模块。集成板 V1.2 已取消 EC11，保留这些资料用于旧台架调试和设计追溯。

| 资料 | 仓库入口 |
|---|---|
| 供应商原始资料摘录 | [资料目录](../../pcb-design/native-rev-a/supplier-review-2026-09-09/sources) · [原来源及校验记录](../../pcb-design/native-rev-a/supplier-review-2026-09-09/source-manifest.json) |
| 屏幕原理图与针序 | [原理图](../../pcb-design/native-rev-b/supplier-evidence/屏幕整板原理图.png) · [引脚说明](../../pcb-design/native-rev-b/supplier-evidence/引脚说明.docx) |
| EC11 编码器 | [EC1103 PDF](../../pcb-design/native-rev-a/supplier-review-2026-09-09/sources/EC11资料/EC1103-D5-K15F7.pdf) · [模块资料目录](<../../pcb-design/native-rev-a/supplier-review-2026-09-09/sources/EC11资料/360度 旋转编码器模块>) |
| 编码器使用与测试说明 | [使用说明](<../../pcb-design/native-rev-a/supplier-review-2026-09-09/sources/EC11资料/360度 旋转编码器模块/使用说明 .doc>) · [STC12 参考例程](<../../pcb-design/native-rev-a/supplier-review-2026-09-09/sources/EC11资料/360度 旋转编码器模块/STC12参考例程.docx>) · [STM8S 测试原文](<../../pcb-design/native-rev-a/supplier-review-2026-09-09/sources/EC11资料/360度 旋转编码器模块/STM8S-IAR/测试方法.txt>) · [UTF-8 阅读版](legacy-encoder-test-method.md) |
| Arduino IDE 库安装说明 | [供应商文档](<../../pcb-design/native-rev-a/supplier-review-2026-09-09/sources/程序/ST7789/ESP8266/Arduino IDE如何添加库.docx>) |
| ESP8266 / STM32 示例摘录 | [程序目录](../../pcb-design/native-rev-a/supplier-review-2026-09-09/sources/程序)；GPIO 只适用于其示例硬件，不直接套用到 ESP32-S3 |

## 商品规格与选型图片

- [屏幕、舵机、电池、充电模块等商品截图](../../hardware-selection/reference)。
- [旧屏整板尺寸图](../../mechanical-design/assembly-v1/reference/selected-display-module-spec.png)。
- [开发板针序及接口资料来源](../../firmware/bringup/docs/reference/资料来源.md)。

这些快照用于保存当时的选型依据，商品价格和库存按记录时间理解。

## 资料保存约定

原厂 PDF、供应商文档和截图作为参考资料入库，保留原文；新的资料放入对应模块的 `sources/`、`datasheets/` 或 `reference/`，并更新本页及清单。清单记录来源、文件大小和 SHA-256，便于核对原件。

第三方资料的版权与许可仍由原作者或厂商规定；本项目 MIT 许可不替代其原许可。此处“随仓库保存”与 README 的许可范围说明同时成立。
