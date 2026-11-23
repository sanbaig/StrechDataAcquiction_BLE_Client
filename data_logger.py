
# ============================================================
# StretchSense BLE Acquisition System
# Data Logger
#
# 文件功能：
# 1. 创建 CSV 数据文件
# 2. 保存双通道传感器数据
# 3. 自动记录采集时间
# 4. 支持开始和停止数据记录
#
# CSV 文件保存位置：
# StretchSense_BLE_Client/data/
# ============================================================


import csv
import os

# 用于生成带日期和时间的文件名
from datetime import datetime


class DataLogger:

    # --------------------------------------------------------
    # 1. 初始化数据记录器
    # --------------------------------------------------------

    def __init__(self, folder="data"):

        # 设置数据保存文件夹
        self.folder = folder

        # 初始化文件对象
        self.file = None

        # 初始化 CSV 写入对象
        self.writer = None

        # 保存当前 CSV 文件路径
        self.file_path = None

        # 记录当前是否正在采集数据
        self.is_recording = False


    # --------------------------------------------------------
    # 2. 开始数据记录
    # --------------------------------------------------------

    def start(self):

        # 如果 data 文件夹不存在，则自动创建
        os.makedirs(self.folder, exist_ok=True)

        # 获取当前日期和时间
        current_time = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        # 根据日期和时间生成 CSV 文件名
        filename = f"StretchSense_{current_time}.csv"

        # 拼接完整文件路径
        self.file_path = os.path.join(
            self.folder,
            filename
        )

        # 创建 CSV 文件
        # newline="" 避免 Windows 下出现多余空行
        # encoding="utf-8" 保证文件编码正常
        self.file = open(
            self.file_path,
            mode="w",
            newline="",
            encoding="utf-8"
        )

        # 创建 CSV 写入对象
        self.writer = csv.writer(self.file)

        # 写入 CSV 表头
        self.writer.writerow([
            "Time_s",
            "CH1_raw",
            "CH2_raw"
        ])

        # 更新数据记录状态
        self.is_recording = True

        print(f"Data recording started: {self.file_path}")

        # 返回文件路径
        return self.file_path


    # --------------------------------------------------------
    # 3. 写入一组双通道数据
    # --------------------------------------------------------

    def write(self, elapsed_time, ch1, ch2):

        # 只有在记录状态开启时才保存数据
        if self.is_recording and self.writer:

            # 将时间和两个通道的数据写入 CSV
            self.writer.writerow([
                f"{elapsed_time:.4f}",
                ch1,
                ch2
            ])

            # 立即刷新缓冲区
            # 降低程序异常退出时的数据丢失风险
            self.file.flush()


    # --------------------------------------------------------
    # 4. 停止数据记录
    # --------------------------------------------------------

    def stop(self):

        # 检查文件是否已经打开
        if self.file:

            # 关闭 CSV 文件
            self.file.close()

        # 清空文件对象
        self.file = None

        # 清空 CSV 写入对象
        self.writer = None

        # 更新数据记录状态
        self.is_recording = False

        print(f"Data recording stopped: {self.file_path}")

        # 返回已保存文件的路径
        return self.file_path
