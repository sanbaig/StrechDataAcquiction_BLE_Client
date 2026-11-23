# StretchSense BLE Data Acquisition Client

A Python desktop application for acquiring, visualizing, and recording dual-channel sensor data from a StretchSense BLE device.

The client is built with [Bleak](https://github.com/hbldh/bleak), Tkinter, and Matplotlib. It supports BLE device discovery, GATT validation, real-time plotting, CSV recording, and connection lifecycle management.

## Features

- BLE device scanning and StretchSense discovery
- GATT service and characteristic validation
- Bluetooth Notify subscriptions
- Dual-channel real-time data visualization
- Timestamped CSV data recording
- Safe handling of disconnection, reconnection, and application shutdown
- Cross-platform Windows BLE access through Bleak

## Requirements

- Windows 10 or later
- Python 3.8 or later
- A BLE-capable Bluetooth adapter
- A StretchSense-compatible nRF52832 BLE device

Python dependencies:

- `bleak`
- `matplotlib`

Tkinter is included with most standard Python distributions on Windows.

## Installation

From the project root, create and activate a virtual environment:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Configuration

All BLE and application parameters are maintained in [config.py](config.py):

| Parameter | Default | Description |
| --- | --- | --- |
| `DEVICE_NAME` | `StretchSense` | Device name or name fragment used during discovery |
| `SERVICE_UUID` | `12345678-1234-5678-1234-56789abcdef0` | Custom GATT service UUID |
| `DATA_CHAR_UUID` | `12345679-1234-5678-1234-56789abcdef0` | GATT characteristic UUID used for data notifications |
| `PLOT_POINTS` | `500` | Maximum number of samples retained by the plot |
| `NOTIFICATION_INTERVAL_MS` | `100` | Firmware notification interval; informational only |

Update these values if the firmware changes its broadcast name or GATT configuration.

## Usage

Launch the desktop application:

```powershell
python main.py
```

1. Click **Scan** to discover nearby StretchSense devices.
2. Select a device from the device list.
3. Click **Connect** to establish the BLE connection.
4. Wait until the status changes to **Receiving**.
5. Click **Start Recording** to create a CSV file.
6. Click **Stop Recording** to finalize the CSV file.
7. Click **Disconnect** or close the application to release the BLE connection.

To run the lightweight BLE receive test:

```powershell
python test_ble.py
```

The test discovers a device named `StretchSense`, subscribes to its data characteristic, receives notifications for 10 seconds, and then disconnects.

## Data Protocol

Each notification packet contains exactly four bytes:

| Byte range | Field | Format |
| --- | --- | --- |
| 0-1 | CH1 | 16-bit unsigned integer, little-endian |
| 2-3 | CH2 | 16-bit unsigned integer, little-endian |

[data_parser.py](data_parser.py) converts the raw notification payload into the CH1 and CH2 values.

Example packet:

```text
EF 03 DB 07
CH1 = 1007
CH2 = 2011
```

## CSV Output

When recording starts, the application creates a timestamped file in the `data/` directory:

```text
data/StretchSense_YYYYMMDD_HHMMSS.csv
```

CSV structure:

| Column | Description |
| --- | --- |
| `Time_s` | Elapsed time in seconds relative to recording start |
| `CH1_raw` | Raw CH1 value |
| `CH2_raw` | Raw CH2 value |

Generated data files and Python cache directories are excluded through [.gitignore](.gitignore).

## Project Structure

```text
.
├── main.py           # Tkinter application and GUI event loop
├── ble_client.py     # BLE discovery, connection, GATT, and notification handling
├── data_parser.py    # Raw notification payload decoding
├── data_logger.py    # Timestamped CSV recording
├── realtime_plot.py  # Real-time dual-channel visualization
├── config.py         # Device, UUID, and plot configuration
├── test_ble.py       # Standalone BLE receive test
├── requirements.txt  # Python dependencies
└── data/             # Locally generated CSV files
```

## Troubleshooting

### Device Not Found

- Confirm that the device is powered on and advertising.
- Verify that `DEVICE_NAME` matches the firmware broadcast name.
- Confirm that Windows Bluetooth is enabled.
- Restart the BLE scan or reconnect the Bluetooth adapter.
- Close other applications that may have exclusive access to the device.

### GATT Service or Characteristic Not Found

Confirm that the firmware UUID values exactly match `SERVICE_UUID` and `DATA_CHAR_UUID` in [config.py](config.py). The data characteristic must support the Notify property.

### Invalid Packet Length

The firmware must send four-byte notification payloads:

- Bytes 0-1: CH1
- Bytes 2-3: CH2
- Both fields: unsigned 16-bit little-endian integers
