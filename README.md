# StretchSense BLE Data Acquisition Client

基于 Python 和 Bleak 的 StretchSense 双通道传感器数据采集上位机。程序提供 BLE 扫描、设备连接、实时曲线显示、数据记录和断开清理功能。

## 功能

- 扫描附近的 BLE 设备并筛选 StretchSense
- 连接指定 BLE 设备
- 校验自定义 GATT Service 和 Notify Characteristic
- 接收并解析双通道传感器数据
- 实时绘制 CH1 和 CH2 曲线
- 将采集数据保存为带时间戳的 CSV 文件
- 正常处理断开连接、重新连接和窗口关闭

## 环境要求

- Windows
- Python 3.8 或更高版本
- 支持 BLE 的蓝牙适配器
- nRF52832 或兼容固件设备

Python 依赖：

- `bleak`
- `matplotlib`

Tkinter 通常随标准 Windows Python 安装包提供。

## 安装

建议在项目根目录创建虚拟环境：

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 配置

BLE 参数统一配置在 [config.py](config.py)：

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `DEVICE_NAME` | `StretchSense` | 广播设备名称关键字 |
| `SERVICE_UUID` | `12345678-1234-5678-1234-56789abcdef0` | 自定义 GATT Service UUID |
| `DATA_CHAR_UUID` | `12345679-1234-5678-1234-56789abcdef0` | 数据 Notify Characteristic UUID |
| `PLOT_POINTS` | `500` | 实时曲线最多显示的采样点数 |
| `NOTIFICATION_INTERVAL_MS` | `100` | 固件通知周期，仅用于说明，不参与解析 |

修改固件参数时，需要确保 [config.py](config.py) 中的 Service UUID、Characteristic UUID 和设备名称与固件一致。

## 使用方法

启动图形界面：

```powershell
python main.py
```

操作流程：

1. 点击 **Scan** 搜索设备。
2. 从设备列表中选择 StretchSense。
3. 点击 **Connect** 建立 BLE 连接并启用数据通知。
4. 点击 **Start Recording** 开始保存数据。
5. 点击 **Stop Recording** 停止保存。
6. 点击 **Disconnect** 或关闭窗口断开设备。

仅测试 BLE 扫描、连接和数据接收：

```powershell
python test_ble.py
```

该测试程序会搜索名为 `StretchSense` 的设备，订阅数据 Characteristic，并在 10 秒后停止接收。

## 数据格式

每个 Notify 数据包固定包含 4 字节：

| 字节 | 内容 |
| --- | --- |
| 0-1 | CH1，16 位无符号整数，小端序 |
| 2-3 | CH2，16 位无符号整数，小端序 |

[data_parser.py](data_parser.py) 使用小端序将原始字节解析为两个通道值。

## CSV 数据

开始录制后，程序会在 `data/` 目录中创建带时间戳的 CSV 文件：

```text
data/StretchSense_YYYYMMDD_HHMMSS.csv
```

CSV 格式：

| 列名 | 说明 |
| --- | --- |
| `Time_s` | 相对数据记录开始时间的秒数 |
| `CH1_raw` | CH1 原始数据值 |
| `CH2_raw` | CH2 原始数据值 |

本地采集数据和 Python 缓存不会提交到 Git，由 [.gitignore](.gitignore) 排除。

## 项目结构

```text
.
├── main.py           # Tkinter 主界面和应用流程
├── ble_client.py     # BLE 扫描、连接、GATT 和通知处理
├── data_parser.py    # 4 字节传感器数据解析
├── data_logger.py    # CSV 数据记录
├── realtime_plot.py  # 实时双通道曲线
├── config.py         # 设备、UUID 和采集参数
├── test_ble.py       # BLE 接收功能测试
├── requirements.txt  # Python 依赖
└── data/             # 本地生成的 CSV 文件
```

## 常见问题

### 找不到 StretchSense

- 确认设备已通电并开始广播。
- 确认 `DEVICE_NAME` 与固件广播名称一致。
- 确认 Windows 蓝牙已开启且未被其他程序占用。
- 尝试重新运行扫描或重启 BLE 适配器。

### 找不到 GATT Service 或 Characteristic

检查固件中的 UUID 是否与 [config.py](config.py) 完全一致，并确认数据 Characteristic 支持 Notify。

### 收到的数据长度不正确

固件必须发送 4 字节通知：前 2 字节为 CH1，后 2 字节为 CH2，且均采用小端序。
