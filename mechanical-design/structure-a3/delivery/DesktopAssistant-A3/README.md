# Desktop Assistant — 整机结构 A3

**当前模型：DesktopAssistant-整机结构-A3.blend；30个独立STL在stl-complete/中，每件打印1个。**

按旧V1恢复：屏幕保持竖直正对使用者，旋钮和按键留在完整原板上，藏在深可拆前盖内。玻璃名义内凹约20.8mm，拆前盖后操作控件。后盖取消旋钮/按键孔和R07/R08压片，保留充电、总开关、喇叭及功放固定。PCB电气设计保持原状。

当前四个场景：`10_A3_COMPLETE_ASSEMBLY`正确坐标总装、`11_A3_EXPLODED_ASSEMBLY`爆炸关系、`12_A3_PRINT_PARTS_OVERVIEW`打印件总览、`13_A3_FRONT_CAP_REMOVED`拆前盖展示。旧场景继续留在文件内供追溯；编辑和打印请从A3场景及清单开始。

- [设计修正说明](设计修正说明.md)
- [30件零件清单](零件清单.md)
- [装配、拆盖与打印说明](装配与打印说明.md)
- [紧固件核对](紧固件与辅料核对.csv)及[安装明细](紧固件安装明细.csv)
- [检查范围与结果](验证说明.md)
- [参数记录](reports/assembly-parameters.json)

机身含盖约124×116.8×76mm，不含腿、耳朵和外伸总开关/螺丝头。R02加深，R01接管底盘前固定点，R04增加排针末端让位，其余结构沿用A2。前盖用4颗M3×30和0.8mm垫片；拆前盖不用拆底盘或主板。

屏幕及旋钮的实物高度仍需核对：商品图的15mm是轴长，不是原板到旋钮顶端的总高。本套是**实物试装版**，尚未实际切片或完成装配、承载、线束、声学、温升与步态验证。

![正面：屏幕竖直正对使用者](renders/A3-front.png)

![斜视：显示内凹关系](renders/A3-perspective.png)

![前盖取下：完整原板、右侧旋钮及按键](renders/A3-front-open.png)

![后盖](renders/A3-rear.png)

![内部](renders/A3-internal.png)

![爆炸关系](renders/A3-exploded.png)

![30个打印件](renders/A3-parts.png)

完整项目中的scripts/可重建；依赖旧A1/R06输入、原V1及PCB参数，独立ZIP无需运行脚本即可编辑Blender和读取STL。STL不保留材质，前盖黑色内井和薄荷线槽通过打印后上色实现。
