# 电路资料来源

获取日期：2026-09-08。原始PDF和HTML保留在本目录，PDF的SHA-256见上级validation.json。厂家板型与当前实物是否同版仍需核实。

| 资料 | 来源 | 本轮可用范围 |
|---|---|---|
| lckfb-datasheet.pdf | https://atta.szlcsc.com/upload/public/pdf/source/20241206/8BAF30E9665AF2DA28B66306BACEE9A0.pdf | 立创商品C20626143给出的LCKFB原厂PDF；第2页名义尺寸，第4页完整引脚图，另存对应页JPG |
| lckfb-open-source.html / lckfb-source.js | https://wiki.lckfb.com/zh-hans/esp32s3r8n8/open-source/ | 该页面当前只显示开源资料标题，没有实际原理图下载内容；不能当作已取得板内电源拓扑 |
| lckfb-download-center.html | https://wiki.lckfb.com/zh-hans/esp32s3r8n8/download-center.html | 厂家网盘资料入口；已正常预览第02章的原理图 PDF，详情见下两行 |
| lckfb-schematic-cover.jpg / lckfb-schematic-core.jpg | https://pan.baidu.com/s/191qHjphKNeRITbFmC6Ct-g?pwd=hoga | 厂家公开分享240926版资料，第02章开源硬件/SCH_立创ESP32S3R8N8开发板原理图.pdf，图框2024-02-28；正常公开预览导出的2页JPEG，不是原PDF。第2页证明USB VBUS和5V排针直连，并给出厂家J1/J2脚号 |
| selected-display-module-spec.png / selected-display-module-evidence.json | 项目已有的 mechanical-design/assembly-v1/reference/selected-display-module-spec.png | 所选TOUGLESY模块供应商图；3.3–5V供电，BLK默认全亮可不接。Rev A选+5V_LOGIC和3.3V SPI，BLK留NC；不证明5V逻辑容限或BLK内部电路 |
| esp32-s3-datasheet.pdf | https://www.espressif.com/sites/default/files/documentation/esp32-s3_datasheet_en.pdf | 芯片GPIO复用、ADC1_CH0、启动配置脚；不代替开发板针序 |
| pca9685-datasheet.pdf | https://www.nxp.com/docs/en/data-sheet/PCA9685.pdf | 芯片OE、MODE2.OUTNE、I2C和PWM功能；不代替HANLI成品板上拉/下拉和机械图 |
| mic-product.html | https://www.dfrobot.com.cn/goods-2567.html | SKU SEN0327、功能端名、1.8–3.3V、LR声道、HTML直径14mm；与所链PDF机械数据冲突 |
| sen0327.pdf | https://www.dfrobot.com.cn/images/upload/File/20191224164325rhavtz.pdf | 实际标题Sipeed I2S_Mic，MSM261S4030H0是麦克风芯片；15.24×9.14×11.2mm与HTML圆板冲突，不确定所购实际板型 |
| max98357a-datasheet.pdf | https://www.analog.com/media/en/technical-documentation/data-sheets/MAX98357A-MAX98357B.pdf | 芯片I2S/LJ、BTL、SD_MODE/声道及供电时序；不代替淘宝模块电阻配置 |
| dfr0753-product.html | https://www.dfrobot.com.cn/goods-2971.html | 6–14V、5V/0–8A；HTML未给完整尺寸 |
| 好盈厂家网页（已有项目核对记录） | https://www.hobbywing.com/products/ubec-3a-2-6s99 | 86010010、43×17×7mm、11g、5.5–26V、5V/3A或6V/3A；引线/磁环另计 |

PDF文字提取为空的LCKFB页属于图片型PDF，本轮阅读的是提取出的原页图片，不把空文本误判为无资料。
