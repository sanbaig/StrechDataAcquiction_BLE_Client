
"""
StretchSense BLE Acquisition System
BLE Client

文件功能：
1. 扫描附近的 BLE 设备
2. 搜索 StretchSense 设备
3. 建立 BLE 连接
4. 检查 GATT Service 和 Characteristic
5. 订阅 Notify，接收传感器数据
6. 将数据交给 DataParser 解析
7. 将数据和连接状态传递给 main.py
"""

import asyncio

from bleak import BleakScanner, BleakClient

from config import DEVICE_NAME, SERVICE_UUID, DATA_CHAR_UUID
from data_parser import DataParser


class BLEClient:

    def __init__(self, data_callback=None, status_callback=None):

        self.data_callback = data_callback
        self.status_callback = status_callback

        self.client = None
        self.parser = DataParser()

        self.device_address = None
        self.is_connected = False
        self.notifications_started = False

        # 防止重复清理同一个客户端
        self._disconnecting = False

    # ========================================================
    # 1. 扫描附近的 BLE 设备
    # ========================================================

    async def scan_devices(self):

        print("\nStarting BLE scan...")

        try:
            # 使用 discover 获取设备及广播数据
            discovered = await BleakScanner.discover(
                timeout=7.0,
                return_adv=True
            )

            target_devices = []

            for address, result in discovered.items():

                device, advertisement_data = result

                # 同时检查设备名称和广播名称
                device_name = device.name or ""
                local_name = (
                    advertisement_data.local_name or ""
                )

                name = device_name or local_name

                if DEVICE_NAME.lower() in name.lower():

                    target_devices.append(device)

                    print(f"Found device: {name}")
                    print(f"Address: {device.address}")

            if not target_devices:
                print("StretchSense not found.")

            return target_devices

        except Exception as error:

            print(f"BLE scan failed: {error}")
            raise

    # ========================================================
    # 2. 连接 BLE 设备
    # ========================================================

    async def connect(self, device_address):

        print("\nConnecting to StretchSense...")

        # 清理可能残留的旧客户端
        if self.client is not None:
            await self._cleanup_connection()

        self.device_address = device_address
        self._disconnecting = False

        try:

            self.client = BleakClient(
                device_address,
                disconnected_callback=self._on_disconnect,
                timeout=20.0
            )

            await self.client.connect()

            if not self.client.is_connected:
                raise RuntimeError(
                    "BLE connection was not established."
                )

            self.is_connected = True

            print("BLE connection successful.")

            await self.check_gatt_services()

            self._notify_status("Connected")

            return True

        except Exception as error:

            print(f"Connection failed: {error}")

            await self._cleanup_connection()

            self._notify_status(
                f"Connection failed: {error}"
            )

            raise

    # ========================================================
    # 3. 检查 GATT Service 和 Characteristic
    # ========================================================

    async def check_gatt_services(self):

        if not self.client or not self.client.is_connected:
            raise RuntimeError(
                "Cannot check GATT services: device is not connected."
            )

        services = self.client.services

        print("\nChecking GATT services...")

        service = services.get_service(SERVICE_UUID)

        if service is None:
            raise RuntimeError(
                f"GATT Service not found: {SERVICE_UUID}"
            )

        print("Sensor GATT Service found.")

        characteristic = services.get_characteristic(
            DATA_CHAR_UUID
        )

        if characteristic is None:
            raise RuntimeError(
                f"Data Characteristic not found: {DATA_CHAR_UUID}"
            )

        print("Sensor Data Characteristic found.")

        if "notify" not in characteristic.properties:
            raise RuntimeError(
                "Data Characteristic does not support Notify."
            )

        print("Notify property verified.")

        return True

    # ========================================================
    # 4. 启动 BLE Notify
    # ========================================================

    async def start_notifications(self):

        if not self.client or not self.client.is_connected:
            raise RuntimeError(
                "Cannot start Notify: BLE device is not connected."
            )

        if self.notifications_started:
            print("BLE notifications are already enabled.")
            return True

        try:

            await self.client.start_notify(
                DATA_CHAR_UUID,
                self._notification_handler
            )

            self.notifications_started = True

            print("BLE notifications enabled.")

            self._notify_status("Receiving")

            return True

        except Exception as error:

            print(f"Notify subscription failed: {error}")

            self.notifications_started = False
            raise

    # ========================================================
    # 5. 处理 BLE Notify 数据
    # ========================================================

    def _notification_handler(self, sender, data):

        try:

            ch1, ch2 = self.parser.parse_packet(data)

            print(f"CH1: {ch1} | CH2: {ch2}")

            if self.data_callback:
                self.data_callback(ch1, ch2)

        except Exception as error:

            print(f"Data processing error: {error}")

    # ========================================================
    # 6. 停止 Notify
    # ========================================================

    async def stop_notifications(self):

        client = self.client

        if client is None or not client.is_connected:
            self.notifications_started = False
            return

        if not self.notifications_started:
            return

        try:

            await client.stop_notify(DATA_CHAR_UUID)

            print("BLE notifications stopped.")

        except Exception as error:

            print(f"Stop Notify error: {error}")

        finally:

            self.notifications_started = False

    # ========================================================
    # 7. 断开 BLE 连接
    # ========================================================

    async def disconnect(self):

        print("\nDisconnecting BLE device...")

        await self._cleanup_connection()

        self._notify_status("Disconnected")

        print("BLE disconnected.")

    # ========================================================
    # 8. 清理 BLE 连接
    # ========================================================

    async def _cleanup_connection(self):

        client = self.client

        if client is None:
            self.is_connected = False
            self.notifications_started = False
            return

        if self._disconnecting:
            return

        self._disconnecting = True

        try:

            # 先停止 Notify
            if client.is_connected and self.notifications_started:

                try:
                    await client.stop_notify(DATA_CHAR_UUID)
                    print("BLE notifications stopped.")

                except Exception as error:
                    print(f"Stop Notify error: {error}")

            self.notifications_started = False

            # 再断开 BLE 连接
            if client.is_connected:

                try:
                    await client.disconnect()

                except Exception as error:
                    print(f"BLE disconnect error: {error}")

        finally:

            self.is_connected = False
            self.notifications_started = False

            if self.client is client:
                self.client = None

            self._disconnecting = False

    # ========================================================
    # 9. 处理意外断开
    # ========================================================

    def _on_disconnect(self, client):

        self.is_connected = False
        self.notifications_started = False

        # 只清理当前客户端，避免影响新连接
        if self.client is client:
            self.client = None

        print("BLE device disconnected.")

        self._notify_status("Disconnected")

    # ========================================================
    # 10. 连接状态回调
    # ========================================================

    def _notify_status(self, status):

        if self.status_callback:
            self.status_callback(status)


# ============================================================
# 11. 独立测试入口
# ============================================================

async def main():

    ble = BLEClient()

    try:

        devices = await ble.scan_devices()

        if not devices:
            print("No StretchSense device found.")
            return

        device = devices[0]

        await ble.connect(device.address)

        await ble.start_notifications()

        print("\nReceiving BLE data...")
        print("Press Ctrl+C to stop.")

        while True:
            await asyncio.sleep(1)

    except KeyboardInterrupt:

        print("\nStopping BLE acquisition...")

    except Exception as error:

        print(f"BLE test failed: {error}")

    finally:

        await ble.disconnect()


# ============================================================
# 12. 程序入口
# ============================================================

if __name__ == "__main__":

    asyncio.run(main())
