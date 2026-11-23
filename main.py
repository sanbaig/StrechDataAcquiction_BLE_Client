
import asyncio
import threading
import queue
import time
from collections import deque

import tkinter as tk
from tkinter import ttk, messagebox

from ble_client import BLEClient
from data_logger import DataLogger
from realtime_plot import RealtimePlot
from config import PLOT_POINTS


class StretchSenseApp:
    """StretchSense 双通道 BLE 数据采集上位机"""

    def __init__(self, root):

        self.root = root
        self.root.title("StretchSense BLE Data Acquisition System")
        self.root.geometry("1100x750")
        self.root.minsize(900, 650)

        # ---------------- 状态变量 ----------------

        self.message_queue = queue.Queue()
        self.device_map = {}

        self.is_connected = False
        self.is_connecting = False
        self.is_scanning = False
        self.is_disconnecting = False

        self.is_closing = False
        self.is_closed = False

        # 用于防止重复处理断开事件
        self.disconnect_handled = True

        # ---------------- BLE 异步事件循环 ----------------

        self.loop = asyncio.new_event_loop()

        self.ble_thread = threading.Thread(
            target=self._run_ble_loop,
            daemon=True
        )
        self.ble_thread.start()

        # ---------------- 数据缓存 ----------------

        self.times = deque(maxlen=PLOT_POINTS)
        self.ch1_values = deque(maxlen=PLOT_POINTS)
        self.ch2_values = deque(maxlen=PLOT_POINTS)

        self.first_data_time = None
        self.recording_start_time = None

        # ---------------- 数据记录器 ----------------

        self.data_logger = DataLogger(folder="data")

        # ---------------- BLE 客户端 ----------------

        self.ble_client = BLEClient(
            data_callback=self._on_ble_data,
            status_callback=self._on_ble_status
        )

        # ---------------- 创建界面 ----------------

        self._create_widgets()

        self.root.after(50, self._process_queue)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # =====================================================
    # 1. 异步事件循环
    # =====================================================

    def _run_ble_loop(self):

        asyncio.set_event_loop(self.loop)

        try:
            self.loop.run_forever()

        finally:

            pending = asyncio.all_tasks(self.loop)

            for task in pending:
                task.cancel()

            if pending:
                self.loop.run_until_complete(
                    asyncio.gather(
                        *pending,
                        return_exceptions=True
                    )
                )

            self.loop.close()

    def _submit_coroutine(self, coroutine):

        if not self.loop.is_running():
            coroutine.close()
            raise RuntimeError("BLE event loop is not running.")

        return asyncio.run_coroutine_threadsafe(
            coroutine,
            self.loop
        )

    # =====================================================
    # 2. GUI 界面
    # =====================================================

    def _create_widgets(self):

        # ---------------- BLE 连接区域 ----------------

        connection_frame = ttk.LabelFrame(
            self.root,
            text="Bluetooth Connection",
            padding=10
        )
        connection_frame.pack(
            fill="x",
            padx=10,
            pady=10
        )

        ttk.Label(
            connection_frame,
            text="BLE Device:"
        ).pack(side="left", padx=5)

        self.device_combobox = ttk.Combobox(
            connection_frame,
            width=35,
            state="readonly"
        )
        self.device_combobox.pack(
            side="left",
            padx=5
        )

        self.scan_button = ttk.Button(
            connection_frame,
            text="Scan",
            command=self.scan_devices
        )
        self.scan_button.pack(side="left", padx=5)

        self.connect_button = ttk.Button(
            connection_frame,
            text="Connect",
            command=self.connect_device
        )
        self.connect_button.pack(side="left", padx=5)

        self.disconnect_button = ttk.Button(
            connection_frame,
            text="Disconnect",
            command=self.disconnect_device,
            state="disabled"
        )
        self.disconnect_button.pack(side="left", padx=5)

        self.status_label = ttk.Label(
            connection_frame,
            text="Status: Disconnected",
            foreground="red"
        )
        self.status_label.pack(side="right", padx=10)

        # ---------------- 实时数据区域 ----------------

        data_frame = ttk.LabelFrame(
            self.root,
            text="Real-time Sensor Data",
            padding=10
        )
        data_frame.pack(
            fill="x",
            padx=10,
            pady=5
        )

        self.ch1_label = ttk.Label(
            data_frame,
            text="CH1: ---",
            font=("Arial", 18, "bold")
        )
        self.ch1_label.pack(side="left", padx=40)

        self.ch2_label = ttk.Label(
            data_frame,
            text="CH2: ---",
            font=("Arial", 18, "bold")
        )
        self.ch2_label.pack(side="left", padx=40)

        # ---------------- 实时曲线区域 ----------------

        plot_frame = ttk.LabelFrame(
            self.root,
            text="Real-time Plot",
            padding=5
        )
        plot_frame.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=5
        )

        self.plot = RealtimePlot(plot_frame)
        self.plot.pack(fill="both", expand=True)

        # ---------------- 数据记录区域 ----------------

        recording_frame = ttk.LabelFrame(
            self.root,
            text="Data Recording",
            padding=10
        )
        recording_frame.pack(
            fill="x",
            padx=10,
            pady=10
        )

        self.start_record_button = ttk.Button(
            recording_frame,
            text="Start Recording",
            command=self.start_recording,
            state="disabled"
        )
        self.start_record_button.pack(side="left", padx=5)

        self.stop_record_button = ttk.Button(
            recording_frame,
            text="Stop Recording",
            command=self.stop_recording,
            state="disabled"
        )
        self.stop_record_button.pack(side="left", padx=5)

        self.recording_label = ttk.Label(
            recording_frame,
            text="Recording: Not started"
        )
        self.recording_label.pack(side="left", padx=15)

    # =====================================================
    # 3. BLE 扫描
    # =====================================================

    def scan_devices(self):

        if (
            self.is_closing
            or self.is_scanning
            or self.is_connected
            or self.is_connecting
            or self.is_disconnecting
        ):
            return

        self.is_scanning = True

        self.scan_button.config(state="disabled")

        self.status_label.config(
            text="Status: Scanning...",
            foreground="blue"
        )

        future = self._submit_coroutine(
            self.ble_client.scan_devices()
        )

        future.add_done_callback(
            self._scan_finished
        )

    def _scan_finished(self, future):

        try:
            devices = future.result()

            self.message_queue.put(
                ("scan_complete", devices)
            )

        except Exception as error:

            self.message_queue.put(
                ("scan_failed", str(error))
            )

    def _show_scan_results(self, devices):

        self.device_map.clear()

        device_names = []

        for device in devices:

            name = device.name or "Unknown Device"

            display_name = f"{name} ({device.address})"

            self.device_map[display_name] = device.address
            device_names.append(display_name)

        self.device_combobox["values"] = device_names

        if device_names:

            self.device_combobox.current(0)

            self.status_label.config(
                text=f"Status: Found {len(device_names)} device(s)",
                foreground="green"
            )

        else:

            self.status_label.config(
                text="Status: No device found",
                foreground="red"
            )

        self.scan_button.config(state="normal")
        self.is_scanning = False

    # =====================================================
    # 4. BLE 连接
    # =====================================================

    def connect_device(self):

        if (
            self.is_closing
            or self.is_connected
            or self.is_connecting
            or self.is_disconnecting
        ):
            return

        selected_device = self.device_combobox.get()

        if not selected_device:

            messagebox.showwarning(
                "Warning",
                "Please scan and select a BLE device first."
            )
            return

        address = self.device_map.get(selected_device)

        if not address:

            messagebox.showwarning(
                "Warning",
                "Invalid BLE device selection."
            )
            return

        self.is_connecting = True
        self.disconnect_handled = False

        self.connect_button.config(state="disabled")
        self.scan_button.config(state="disabled")

        self.status_label.config(
            text="Status: Connecting...",
            foreground="blue"
        )

        future = self._submit_coroutine(
            self._connect_task(address)
        )

        future.add_done_callback(
            self._connect_finished
        )

    async def _connect_task(self, address):

        await self.ble_client.connect(address)

        await self.ble_client.start_notifications()

        return True

    def _connect_finished(self, future):

        try:

            future.result()

            self.message_queue.put(
                ("connected", None)
            )

        except Exception as error:

            self.message_queue.put(
                ("connection_failed", str(error))
            )

    # =====================================================
    # 5. BLE 断开连接
    # =====================================================

    def disconnect_device(self):

        if self.is_closing or self.is_disconnecting:
            return

        if not self.is_connected and not self.is_connecting:
            return

        self.is_disconnecting = True

        self.disconnect_button.config(state="disabled")
        self.scan_button.config(state="disabled")
        self.connect_button.config(state="disabled")

        self.status_label.config(
            text="Status: Disconnecting...",
            foreground="blue"
        )

        future = self._submit_coroutine(
            self.ble_client.disconnect()
        )

        future.add_done_callback(
            self._disconnect_finished
        )

    def _disconnect_finished(self, future):

        try:
            future.result()

        except Exception as error:

            self.message_queue.put(
                ("error", f"Disconnect error: {error}")
            )

        self.message_queue.put(
            ("disconnected", None)
        )

    def _handle_disconnected(self):

        if self.is_closing:
            return

        if self.disconnect_handled:
            return

        self.disconnect_handled = True

        self.is_connected = False
        self.is_connecting = False
        self.is_disconnecting = False

        self.scan_button.config(state="normal")
        self.connect_button.config(state="normal")
        self.disconnect_button.config(state="disabled")

        self.start_record_button.config(state="disabled")

        if self.data_logger.is_recording:
            self.stop_recording()

        self.status_label.config(
            text="Status: Disconnected",
            foreground="red"
        )

    # =====================================================
    # 6. BLE 数据和状态回调
    # =====================================================

    def _on_ble_data(self, ch1, ch2):

        arrival_time = time.perf_counter()

        self.message_queue.put(
            ("data", (arrival_time, ch1, ch2))
        )

    def _on_ble_status(self, status):

        self.message_queue.put(
            ("ble_status", status)
        )

    # =====================================================
    # 7. GUI 消息队列
    # =====================================================

    def _process_queue(self):

        if self.is_closed:
            return

        try:

            while True:

                message_type, data = self.message_queue.get_nowait()

                if message_type == "scan_complete":

                    if self.is_closing:
                        continue

                    self._show_scan_results(data)

                elif message_type == "scan_failed":

                    if self.is_closing:
                        continue

                    self.is_scanning = False
                    self.scan_button.config(state="normal")

                    self.status_label.config(
                        text="Status: Scan Failed",
                        foreground="red"
                    )

                    messagebox.showerror("Scan Error", data)

                elif message_type == "connected":

                    if self.is_closing:
                        continue

                    self.is_connected = True
                    self.is_connecting = False
                    self.is_disconnecting = False
                    self.disconnect_handled = False

                    self.times.clear()
                    self.ch1_values.clear()
                    self.ch2_values.clear()

                    self.first_data_time = None

                    self.plot.clear()

                    self.scan_button.config(state="disabled")
                    self.connect_button.config(state="disabled")
                    self.disconnect_button.config(state="normal")

                    self.start_record_button.config(state="normal")

                    self.status_label.config(
                        text="Status: Receiving",
                        foreground="green"
                    )

                elif message_type == "connection_failed":

                    if self.is_closing:
                        continue

                    self.is_connecting = False
                    self.is_connected = False
                    self.is_disconnecting = False
                    self.disconnect_handled = True

                    self.scan_button.config(state="normal")
                    self.connect_button.config(state="normal")
                    self.disconnect_button.config(state="disabled")

                    self.start_record_button.config(state="disabled")

                    self.status_label.config(
                        text="Status: Connection Failed",
                        foreground="red"
                    )

                    messagebox.showerror(
                        "Connection Failed",
                        data
                    )

                elif message_type == "disconnected":

                    self._handle_disconnected()

                elif message_type == "data":

                    if self.is_connected and not self.is_closing:

                        arrival_time, ch1, ch2 = data

                        self._update_sensor_data(
                            arrival_time,
                            ch1,
                            ch2
                        )

                elif message_type == "ble_status":

                    if data == "Disconnected":
                        self._handle_disconnected()

                elif message_type == "error":

                    if not self.is_closing:
                        messagebox.showerror("Error", data)

                elif message_type == "close_finished":

                    self._finish_close()

        except queue.Empty:
            pass

        if not self.is_closing:
            self.root.after(50, self._process_queue)

    # =====================================================
    # 8. 实时数据更新
    # =====================================================

    def _update_sensor_data(self, arrival_time, ch1, ch2):

        if self.first_data_time is None:
            self.first_data_time = arrival_time

        elapsed_time = arrival_time - self.first_data_time

        self.times.append(elapsed_time)
        self.ch1_values.append(ch1)
        self.ch2_values.append(ch2)

        self.ch1_label.config(text=f"CH1: {ch1}")
        self.ch2_label.config(text=f"CH2: {ch2}")

        self.plot.update_data(
            list(self.times),
            list(self.ch1_values),
            list(self.ch2_values)
        )

        if self.data_logger.is_recording:

            recording_elapsed = (
                arrival_time - self.recording_start_time
            )

            self.data_logger.write(
                recording_elapsed,
                ch1,
                ch2
            )

    # =====================================================
    # 9. CSV 数据记录
    # =====================================================

    def start_recording(self):

        if not self.is_connected:
            return

        if self.data_logger.is_recording:
            return

        try:

            file_path = self.data_logger.start()

            self.recording_start_time = time.perf_counter()

            self.start_record_button.config(state="disabled")
            self.stop_record_button.config(state="normal")

            self.recording_label.config(
                text=f"Recording: {file_path}"
            )

        except Exception as error:

            messagebox.showerror(
                "Recording Error",
                str(error)
            )

    def stop_recording(self):

        if not self.data_logger.is_recording:
            return

        file_path = self.data_logger.stop()

        self.recording_start_time = None

        self.start_record_button.config(
            state="normal" if self.is_connected else "disabled"
        )

        self.stop_record_button.config(state="disabled")

        self.recording_label.config(
            text=f"Saved: {file_path}"
        )

    # =====================================================
    # 10. 程序退出
    # =====================================================

    def _on_close(self):

        if self.is_closing:
            return

        self.is_closing = True

        # 停止数据记录，确保 CSV 文件正常保存
        if self.data_logger.is_recording:
            self.data_logger.stop()

        # 禁用所有按钮
        self.scan_button.config(state="disabled")
        self.connect_button.config(state="disabled")
        self.disconnect_button.config(state="disabled")
        self.start_record_button.config(state="disabled")
        self.stop_record_button.config(state="disabled")

        # 在 BLE 线程中执行断开操作
        try:
            future = self._submit_coroutine(
                self.ble_client.disconnect()
            )

            # 保存 Future，供 GUI 线程检查完成状态
            self.close_future = future

            # 启动 GUI 线程轮询
            self.root.after(50, self._check_close_finished)

        except Exception:
            self._finish_close()

    def _check_close_finished(self):

        if self.is_closed:
            return

        # 检查 BLE 断开任务是否完成
        if self.close_future.done():

            try:
                self.close_future.result()
            except Exception:
                pass

            self._finish_close()

        else:
            # 尚未完成，继续检查
            self.root.after(50, self._check_close_finished)

    def _finish_close(self):

        if self.is_closed:
            return

        self.is_closed = True

        # 停止 asyncio 事件循环
        if self.loop.is_running():
            self.loop.call_soon_threadsafe(
                self.loop.stop
            )

        # 销毁窗口
        self.root.destroy()


# =========================================================
# 程序入口
# =========================================================

if __name__ == "__main__":

    root = tk.Tk()

    app = StretchSenseApp(root)

    root.mainloop()
