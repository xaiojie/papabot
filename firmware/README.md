# 固件与网页控制台

| 模块 | 入口 | 用途 |
|---|---|---|
| 产品固件 | [assistant/README.md](assistant/README.md) | 表情、信息页面、动画、联网与网页控制 |
| 硬件自检 | [bringup/README.md](bringup/README.md) | 屏幕、麦克风、舵机和串口命令台架 |
| 接线定义 | [bringup/wiring.json](bringup/wiring.json) | bringup 的引脚定义；生成 `board_config.h` 的来源 |
| 网页中转服务 | [服务配置](web-console/server/package.json) | Node.js WebSocket/HTTP 服务 |
| 网页界面 | [控制台](web-console/www/index.html) | 设备远程控制界面 |
| 部署记录 | [部署记录](web-console/部署记录.md) | 已有部署和阶段联调记录 |

运行与烧录方法见 [项目 README](../README.md)，当前实机状态见 [项目进度总览](../项目进度总览.md)。旧屏台架和 HS24S010B 集成板属于不同硬件配置，不能直接混用引脚与交互说明。

主机测试，从仓库根目录执行：

```sh
python3 firmware/bringup/scripts/test_host.py
python3 firmware/assistant/scripts/test_host.py
```

`.pio`、`.venv`、`test/.build`、编译索引、运行凭据和日志保留本地，不提交 Git。
