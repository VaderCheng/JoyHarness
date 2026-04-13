# JoyHarness

将 Nintendo Switch Joy-Con 手柄通过蓝牙连接到 Windows 11，映射为键盘快捷键。支持单个左手柄、单个右手柄、以及双手柄（L+R 组合设备）三种连接模式，自动检测并切换对应键位映射。

![JoyHarness GUI](assets/screenshot.png)


## 功能特性

- **多手柄支持**：自动检测连接模式（右手柄 / 左手柄 / 双手柄），切换对应的键位映射配置档
- **热插拔**：运行中断开重连自动恢复；连接模式变化（如只连右手柄后再连左手柄）自动切换配置档
- **按键映射**：支持 tap（点击）、hold（长按）、auto（自适应）、combination（组合键）、sequence（序列键）、macro（宏）
- **摇杆映射**：4/8 方向映射到键盘按键，可配置死区
- **窗口切换**：R 键快速切换指定应用窗口（类似 Alt+Tab）
- **系统托盘**：最小化到托盘运行
- **GUI 设置界面**：可视化编辑按键映射和切换应用列表，自动适配当前连接模式的按钮
- **校准工具**：交互式按钮/摇杆索引校准

## 安装

### 环境要求

- Windows 11
- Python 3.10+
- Joy-Con 已通过蓝牙配对

### 安装依赖

```bash
pip install -r requirements.txt
```

### 蓝牙配对

1. Windows 设置 → 蓝牙和设备 → 添加设备
2. 按住 Joy-Con 滑轨上的小配对按钮 3 秒，指示灯快速闪烁
3. 在蓝牙列表中选择 "Joy-Con R" 或 "Joy-Con L"

## 使用

### 启动

```bash
# 使用管理员权限运行（键盘模拟需要）
python src/main.py

# 或使用批处理文件自动提权
run.bat
```

启动时自动检测连接模式，标题栏会显示当前模式：`JoyHarness [右手柄]` / `JoyHarness [左手柄]` / `JoyHarness [左右手柄]`。

### 命令行参数

```
python src/main.py --config custom.json  # 使用自定义配置
python src/main.py --discover            # 调试模式：显示按钮/轴原始值
python src/main.py --deadzone 0.2        # 覆盖死区值
python src/main.py --list-controls       # 列出当前映射和可用配置档
python src/main.py --verbose             # 调试日志
python src/main.py --joystick 0          # 指定手柄设备索引
python src/main.py --version             # 显示版本号
python src/main.py --no-admin-warn       # 关闭管理员权限警告
```

### 校准工具

如果按钮索引不正确（不同驱动/手柄可能不同），运行校准工具：

```bash
python calibrate.py
```

按提示逐一按下按钮和推动摇杆，程序会生成 `calibration_result.json` 并输出需要更新的常量。

> **注意**：左手柄和双手柄模式的按钮索引目前为占位值，需要分别在对应连接模式下运行 `--discover` 来校准。

## 配置文件

配置文件为 JSON 格式，位于 `config/user.json`（自动生成）或 `config/default.json`。支持三种连接模式的独立配置档：

```json
{
  "version": "2.0",
  "deadzone": 0.2,
  "poll_interval": 0.01,
  "stick_mode": "4dir",
  "switch_scroll_interval": 400,
  "active_profile": "single_right",
  "profiles": {
    "single_right": {
      "mappings": { "buttons": {...}, "stick_directions": {...} }
    },
    "single_left": {
      "mappings": { "buttons": {...}, "stick_directions": {...} }
    },
    "dual": {
      "mappings": { "buttons": {...}, "stick_directions": {...} }
    }
  },
  "known_apps": { "VS Code": "code.exe" }
}
```

| 字段 | 说明 | 默认值 |
|------|------|--------|
| `deadzone` | 摇杆死区 (0.0 - 0.99) | 0.2 |
| `poll_interval` | 轮询间隔（秒） | 0.01 |
| `stick_mode` | 摇杆方向模式 | "4dir" |
| `switch_scroll_interval` | 窗口切换滚动间隔（毫秒） | 400 |
| `profiles.<mode>.mappings.buttons` | 按键映射 | 见 constants.py |
| `profiles.<mode>.mappings.stick_directions` | 摇杆方向映射 | 见 constants.py |

> 旧版配置格式（顶级 `mappings`）会自动迁移为 `profiles.single_right`，无需手动处理。

### 连接模式说明

| 模式 | 标签 | 说明 |
|------|------|------|
| `single_right` | 右手柄 | 仅连接右手柄，可用按钮：A/B/X/Y/R/ZR/Plus/Home/RStick/SL/SR |
| `single_left` | 左手柄 | 仅连接左手柄，可用按钮：A/B/X/Y/L/ZL/Minus/Capture/LStick/SL/SR |
| `dual` | 左右手柄 | 双手柄组合设备，可用按钮：以上全部 |

### 动作类型

- **tap** — 点击：按下后立即松开
- **hold** — 长按：按下保持，松开时释放（适合修饰键）
- **auto** — 自适应：短按（<250ms）= tap，长按 = hold
- **combination** — 组合键：同时按下多个键（如 Ctrl+S）
- **sequence** — 序列键：按住修饰键 + 依次点击其他键
- **window_switch** — 窗口切换：在指定应用窗口间循环切换
- **macro** — 宏：执行预定义的按键序列

## 项目结构

```
src/
├── __init__.py          # 包初始化
├── __main__.py          # python -m src 入口
├── main.py              # CLI 入口
├── config_loader.py     # JSON 配置加载/验证/保存（支持多配置档）
├── constants.py         # 硬件常量、默认映射、多模式按钮索引
├── joycon_reader.py     # pygame 手柄轮询 (100Hz)、连接模式检测、热插拔重连
├── joystick_handler.py  # 死区算法、方向判定
├── key_mapper.py        # 事件翻译引擎（核心）、配置档热切换
├── keyboard_output.py   # keyboard 库封装
├── gui.py               # 主窗口 GUI（显示当前连接模式）
├── settings_window.py   # 设置界面（自动适配当前模式的按钮列表）
├── window_switcher.py   # Win32 窗口枚举/切换
├── switcher_overlay.py  # 窗口切换覆盖层
├── tray_icon.py         # 系统托盘图标
├── battery_reader.py    # HID 电池电量读取
└── resizable.py         # 无边框窗口缩放
```

## 依赖

- [pygame](https://www.pygame.org/) — 手柄输入
- [keyboard](https://github.com/boppreh/keyboard) — 键盘模拟
- [pystray](https://github.com/moses-palmer/pystray) — 系统托盘
- [ttkbootstrap](https://github.com/israel-dryer/ttkbootstrap) — GUI 主题
- [Pillow](https://python-pillow.org/) — 图像处理（pystray 依赖）
- [hidapi](https://github.com/libusb/hidapi) — HID 电池读取

## 许可证

[MIT](LICENSE)
