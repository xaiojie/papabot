# 🚀 EDA 自动化能力（重大发现）

2026-09-11。**这改变了「③ 出原理图与 PCB」的交付方式** —— 从"写文档"升级为"直接建进嘉立创EDA"。

---

## 一、发现过程

排查仓库时发现三个线索：

| 线索 | 位置 |
|---|---|
| `eda_client.py` | `pcb-design/native-rev-b/` —— 指向 `http://127.0.0.1:49620/execute` |
| `audit/*.js` —— **153 个脚本** | 记录了对 EDA 的每一次操作，**含真实可跑的代码** |
| `bridge-server.log` | 显示 EDA 窗口曾通过 WebSocket 连接 |

顺着 `easyeda-api` 找到完整技能包：

```
/Users/jay/.codex/skills/easyeda-api/
├── SKILL.md                     31 KB —— 完整使用指南
├── scripts/bridge-server.mjs    WebSocket 桥服务端
├── references/                  120 个类 + 62 枚举 + 70 接口的 API 文档
└── guide/                       扩展开发、错误处理等
```

---

## 二、架构

```
┌───────────┐   HTTP/WS     ┌─────────────────┐   WebSocket   ┌───────────┐
│ AI Agent  │ ◄───────────► │  Bridge Server  │ ◄───────────► │ EasyEDA   │
│  （我）    │  49620-49629  │  (Node.js)      │  49620-49629  │  （你）    │
└───────────┘               └─────────────────┘               └───────────┘
```

| 项 | 值 |
|---|---|
| 桥端口 | **49620**（当前已启动运行 ✅）|
| 项目 ID | `e5e438419c1c4681946d5009bb8d6daf`（DesktopAssistant）|
| 原理图文档 UUID | `834bc1f5a1044766` |
| PCB 文档 UUID | `641e84beea5fc9c6` |
| **EDA 客户端所需扩展** | **`run-api-gateway.eext`** |
| 扩展下载 | https://jlc-ext.com/item/oshub/run-api-gateway |

---

## 三、可用 API（从 153 个审计脚本里提取的真实调用）

### 工程 / 文档
```
dmt_Project.getCurrentProjectInfo()
dmt_SelectControl.getCurrentDocumentInfo()
dmt_EditorControl.openDocument() / closeDocument()
dmt_EditorControl.zoomToAllPrimitives()
dmt_EditorControl.getCurrentRenderedAreaImage()   ← 可以截图看效果
sys_FileManager.getDocumentSource() / setDocumentSource() / getProjectFile()
```

### 原理图
```
sch_PrimitiveComponent.getAll() / create() / modify() / createNetPort()
sch_PrimitiveWire.create() / getAll()
sch_Drc.check()          ← 跑 DRC
sch_Document.save()      ← 保存
sch_ManufactureData.getNetlistFile()   ← 导出网表
```

### PCB
```
pcb_PrimitiveComponent.getAll()
pcb_PrimitivePad.getAll()
pcb_PrimitiveLine.create() / getAll()      ← 布线
pcb_PrimitivePolyline.getAll()             ← 铺铜
pcb_PrimitiveVia.create() / getAll()       ← 过孔
pcb_Drc.check()                            ← 跑 DRC
pcb_Document.save() / importChanges()      ← 保存 / 从原理图导入
pcb_ManufactureData.getNetlistFile() / getGerberFile()   ← 导出 Gerber
```

---

## 四、关键 API 签名

```js
// 建元件
SCH_PrimitiveComponent.create(component, x, y, subPartName, rotation, mirror,
                              addIntoBom, addIntoPcb)

// 画导线
SCH_PrimitiveWire.create(line, net, color, lineWidth, lineType)

// 建网络标志 / 端口
SCH_PrimitiveComponent.createNetFlag(identification, net, x, y, rotation, mirror)
SCH_PrimitiveComponent.createNetPort(direction, net, x, y, rotation, mirror)

// PCB 走线
pcb_PrimitiveLine.create(net, layer, startX, startY, endX, endY, lineWidth, false)
//   layer: 1=顶层, 2=底层
```

> ⚠️ 部分 API 标 **BETA**，但仓库里**已经真实跑通过**（153 个脚本 + Gerber 导出成功），证明可用。

---

## 五、真实代码范例（仓库里跑过的）

### 原理图建元件 + 网络
```js
const taskProject = await eda.dmt_Project.getCurrentProjectInfo();
if (!taskProject || taskProject.uuid !== "e5e438419c1c4681946d5009bb8d6daf")
  throw new Error("DesktopAssistant project guard mismatch");

const d = await eda.dmt_SelectControl.getCurrentDocumentInfo();
if (d.uuid !== "834bc1f5a1044766") throw new Error("SCH mismatch");

const existing = await eda.sch_PrimitiveComponent.getAll();
const result = [];
for (const s of [
  { ref: "JP3", dev: "eab4a8150b6d4918927e38d645cd50f2",
    name: "LCD_3V3_LINK_OPEN", x: 800, y: 595, rot: 0,
    nets: { "1": "+3V3", "2": "LCD_3V3" }, note: "..." },
  ...
]) {
  // ... 建元件 + 连线
}
```

### PCB 走线
```js
const EPCB_LayerId = { TOP: 1, BOTTOM: 2 };
const ids = [];
for (const t of [
  { net: "GND", layer: 1, startX: 2830, startY: 885,
    endX: 2790, endY: 885, lineWidth: 40 },
  ...
]) {
  const v = await eda.pcb_PrimitiveLine.create(
      t.net, t.layer, t.startX, t.startY, t.endX, t.endY, t.lineWidth, false);
  if (!v) throw new Error("Route creation failed");
  ids.push(v.getState_PrimitiveId());
}
return ids;
```

---

## 六、当前状态与下一步

### ✅ 已完成
- 桥服务端**已启动**，端口 **49620**，`status: ok`

### ✅ 已连通（2026-09-11 验证）

```json
{ "edaConnected": true, "edaWindowCount": 1,
  "activeWindowId": "8c463d84-9088-4034-be57-d761ded21547" }
```

**工程结构（读到的）：**
```
Project: DesktopAssistant_RevA   e5e438419c1c4681946d5009bb8d6daf
└── Board1
    ├── Schematic1  a6220564039ee089
    │   └── P1      834bc1f5a1044766   ← 原理图页，121 个元件
    └── PCB1        641e84beea5fc9c6
```

**已实测可用的操作：**

| 操作 | API | 结果 |
|---|---|---|
| 打开工程 | `dmt_Project.openProject(uuid)` | ✅ 返回 true |
| 读工程树 | `dmt_Project.getCurrentProjectInfo()` | ✅ 拿到 Board/Schematic/PCB 结构 |
| 打开文档 | `dmt_EditorControl.openDocument(uuid)` | ✅ 返回 tabId |
| 读元件 | `sch_PrimitiveComponent.getAll()` | ✅ 121 个 |
| 缩放全图 | `dmt_EditorControl.zoomToAllPrimitives()` | ✅ |
| **截图** | `dmt_EditorControl.getCurrentRenderedAreaImage()` | ✅ **返回 PNG Blob（589 KB）** |
| 跑任意 JS | 桥的 `/execute` | ✅ `{ok:true,n:42}` 验证通过 |

**截图已存档：`eda-截图/RevB载板原理图_20260911.png`**

**元件对象结构**（属性直接挂载，也有 getState_* 方法）：
```js
c.designator   // 位号
c.name         // 器件名
c.x, c.y       // 坐标
c.net          // 网络
c.component, c.symbol, c.footprint
c.getAllPins() // 引脚
c.getState_Designator() / setState_Designator()
```

### ⚠️ 重要：现有工程是**旧的 RevB 载板**

```
J1/J2  主控 2×20 插座      J3   屏幕 LCD_3V3_SPI
J4     PCA9685_LOGIC_ONLY  J5   MIC_3V3_I2S
J6     AMP_I2S_SIGNALS     J7   LCD_STOCK_CONTROLS
J8     LOGIC_5V_IN         J9   SWITCHED_BAT_SENSE
J10    LCD_EXT_3V3_IN      JP1/2/3  三个跳线
R1–R7  100k/33k/10k×5      C1–C5    100nF×4 + 470µF
```

**这不是我们的单板全集成。** 集成板需要**新建原理图页或新建工程**，
**绝不能改坏现有的 RevB**。

### 需要你做的

1. **打开嘉立创EDA专业版**（桌面客户端）
2. **确认已装扩展 `run-api-gateway.eext`**
   - 下载：https://jlc-ext.com/item/oshub/run-api-gateway
   - 装好后扩展会**自动建立 WebSocket 连接**
3. 打开 **DesktopAssistant** 项目

然后我就能：
- 读当前原理图/PCB 状态
- **程序化建元件、连线、铺铜、打孔**
- **跑 DRC** 并读报告
- **导出 Gerber**

> 仓库里已经有 `/Users/jay/Downloads/easyeda-copilot_v1.1.5.eext`，但**名字不同** ——
> 需要的是 **`run-api-gateway.eext`**，确认一下装的是哪个。

---

## 七、这个能力对项目的意义

| 原计划 | 新计划 |
|---|---|
| 我出设计文档 → 你手工画 | **我出设计文档 → 我程序化建进 EDA → 你审核** |
| 容易抄错（如 PCA9685 的 OE 引脚）| 代码执行，**不会抄错** |
| DRC 手工跑 | **脚本跑，自动读报告** |
| Gerber 手工导 | **脚本导，自动校验** |

**风险**：BETA API + 直接改你的工程。**必须**：
- 每次操作前**备份**（仓库里已有 `backup-before-edit.js` 的先例）
- 用**项目 ID 守卫**防止改错工程
- 分小步执行，**每步验证**
