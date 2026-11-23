
"""
realtime_plot.py

功能：
1. 在 Tkinter 界面中嵌入 Matplotlib 实时绘图区域。
2. 同时显示 CH1 和 CH2 两路传感器数据。
3. 随着 BLE 数据到达，动态更新两条曲线。
4. 默认显示最近 30 秒的数据。

注意：
本文件只负责绘图，不负责蓝牙通信和 CSV 数据保存。
"""

from collections import deque

import tkinter as tk

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


class RealtimePlot(tk.Frame):
    """
    实时双通道绘图组件。

    后续在 main.py 中可以这样调用：

        plot = RealtimePlot(root)
        plot.pack(fill="both", expand=True)

        plot.update_data(times, ch1_values, ch2_values)
    """

    def __init__(self, parent):
        """
        初始化绘图区域。

        parent：Tkinter 主窗口或其他 Frame。
        """

        super().__init__(parent)

        # 设置实时显示的时间窗口，单位为秒
        self.time_window = 30

        # 保存最近一段时间的数据
        # deque 可以高效地在数据队列两端添加和删除元素
        self.times = deque()
        self.ch1_values = deque()
        self.ch2_values = deque()

        # 创建 Matplotlib 图形对象
        self.figure = Figure(
            figsize=(9, 5),
            dpi=100
        )

        # 创建坐标轴
        self.ax = self.figure.add_subplot(111)

        # 设置图表标题和坐标轴名称
        self.ax.set_title(
            "Real-time Stretch Sensor Data",
            fontsize=13
        )

        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Sensor Reading")

        # 显示网格
        self.ax.grid(
            True,
            linestyle="--",
            alpha=0.4
        )

        # 初始化两条曲线
        # 后续更新数据时只修改曲线数据，不重复创建曲线
        self.line_ch1, = self.ax.plot(
            [],
            [],
            label="CH1",
            linewidth=1.5
        )

        self.line_ch2, = self.ax.plot(
            [],
            [],
            label="CH2",
            linewidth=1.5
        )

        # 显示图例
        self.ax.legend(loc="upper right")

        # 调整图表布局，避免坐标轴标签被遮挡
        self.figure.tight_layout()

        # 将 Matplotlib 图表嵌入 Tkinter 界面
        self.canvas = FigureCanvasTkAgg(
            self.figure,
            master=self
        )

        # 获取图表对应的 Tkinter 控件
        self.canvas_widget = self.canvas.get_tk_widget()

        # 让图表填充整个绘图区域
        self.canvas_widget.pack(
            fill=tk.BOTH,
            expand=True
        )

        # 首次绘制图表
        self.canvas.draw()

    def update_data(self, times, ch1_values, ch2_values):
        """
        更新实时曲线数据。

        参数：
        times：时间数据列表，单位为秒。
        ch1_values：CH1 传感器数据列表。
        ch2_values：CH2 传感器数据列表。

        三组数据必须长度一致。
        """

        # 检查输入数据长度是否一致
        if not (
            len(times) == len(ch1_values) == len(ch2_values)
        ):
            return

        # 更新内部数据队列
        self.times = deque(times)
        self.ch1_values = deque(ch1_values)
        self.ch2_values = deque(ch2_values)

        # 如果当前没有数据，则不更新图表
        if len(self.times) == 0:
            return

        # 获取最新时间
        latest_time = self.times[-1]

        # 只显示最近 time_window 秒的数据
        while (
            self.times
            and latest_time - self.times[0] > self.time_window
        ):
            self.times.popleft()
            self.ch1_values.popleft()
            self.ch2_values.popleft()

        # 更新 CH1 和 CH2 曲线
        self.line_ch1.set_data(
            list(self.times),
            list(self.ch1_values)
        )

        self.line_ch2.set_data(
            list(self.times),
            list(self.ch2_values)
        )

        # 设置 X 轴显示范围
        x_min = max(0, latest_time - self.time_window)
        x_max = max(self.time_window, latest_time)

        self.ax.set_xlim(x_min, x_max)

        # 根据两路数据自动调整 Y 轴范围
        all_values = (
            list(self.ch1_values)
            + list(self.ch2_values)
        )

        if all_values:
            y_min = min(all_values)
            y_max = max(all_values)

            # 防止两路数据完全相同时，Y 轴范围为零
            if y_min == y_max:
                y_min -= 10
                y_max += 10
            else:
                # 上下各留出 10% 的显示空间
                margin = (y_max - y_min) * 0.1
                y_min -= margin
                y_max += margin

            self.ax.set_ylim(y_min, y_max)

        # 请求 Tkinter 刷新图表
        self.canvas.draw_idle()

    def clear(self):
        """
        清空当前曲线数据。
        后续可以用于主界面的 Clear 按钮。
        """

        self.times.clear()
        self.ch1_values.clear()
        self.ch2_values.clear()

        self.line_ch1.set_data([], [])
        self.line_ch2.set_data([], [])

        self.ax.set_xlim(0, self.time_window)
        self.ax.set_ylim(0, 100)

        self.canvas.draw_idle()
