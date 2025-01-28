import os
import cv2
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Button, Slider, TextBox
from matplotlib.animation import FuncAnimation

import matplotlib
matplotlib.use('TkAgg')

from camera import Camera


class RealTimeImaging:
    def __init__(self):
        # 初始化图形界面
        self.fig, self.ax = plt.subplots()
        plt.subplots_adjust(left=0.1, bottom=0.4)

        # 初始化图像数据
        self.img_data = np.random.rand(100, 100)
        self.im = self.ax.imshow(self.img_data, cmap='gray', vmin=0, vmax=1)
        self.locked_image = None
        self.roi = ((0, 0), (100, 100))

        # 初始化控制参数
        self.tracking = False
        self.locking = False
        self.exposure = 100 * 1000  # 初始曝光时间（ms）
        self.gain = 100
        self.unit = 'ms'
        self.ctr = 0

        # 创建控件
        self._create_widgets()

        # 设置动画更新
        self.ani = FuncAnimation(self.fig, self._update, interval=50)

    def _create_widgets(self):
        lock_ax = plt.axes([0.05, 0.9, 0.15, 0.075])
        self.lock_btn = Button(lock_ax, 'Lock')
        self.lock_btn.on_clicked(self._toggle_locking)


        # Track按钮
        track_ax = plt.axes([0.2, 0.9, 0.15, 0.075])
        self.track_btn = Button(track_ax, 'Track')
        self.track_btn.set_active(self.locking)
        self.track_btn.on_clicked(self._toggle_tracking)

        update_ax = plt.axes([0.8, 0.9, 0.15, 0.075])
        self.update_btn = Button(update_ax, 'Change Settings')
        self.update_btn.on_clicked(self._change_settings)


        text_ax = plt.axes([0.3, 0.1, 0.5, 0.03])
        self.text_box = TextBox(text_ax, 'Exposure Time (ms)', initial=str(self.exposure / 1000))
        # self.text_box.on_submit(self._submit_text)

        # Gain滑块
        gain_ax = plt.axes([0.3, 0.15, 0.5, 0.03])
        self.gain_slider = Slider(gain_ax, 'Gain', 1, 1000, valinit=self.gain, valstep=1)
        # self.gain_slider.on_changed(self._update_gain)

    def _toggle_tracking(self, event):
        self.tracking = not self.tracking
        self.track_btn.label.set_text('Track' if not self.tracking else 'Stop')
        print(f"Tracking {'enabled' if self.tracking else 'disabled'}")

    def _toggle_locking(self, event):
        self.locking = not self.locking
        self.lock_btn.label.set_text('Lock' if not self.locking else 'Unlock')
        self.track_btn.set_active(self.locking)
        print(f"Locking {'enabled' if self.locking else 'disabled'}")

    def _change_settings(self, event):
        try:
            self.exposure = int(float(self.text_box.text) * 1000)
        except ValueError:
            self.text_box.set_val(str(self.exposure / 1000))
        self.gain = self.gain_slider.val
        print(f"Settings updated: exposure={self.exposure}, gain={self.gain}")

    def _update_exposure(self, val):
        self.exposure = val
        print(f"Exposure updated: {self._get_actual_exposure():.4f} s")

    def _update_gain(self, val):
        self.gain = val
        print(f"Gain updated: {self.gain:.2f}")

    def _get_actual_exposure(self):
        # 根据单位和滑块值计算实际曝光时间（秒）
        return {
            'ms': self.exposure * 1e-3,
            'us': self.exposure * 1e-6,
            's': self.exposure
        }[self.unit]

    @staticmethod
    def weighted_average(image):
        # Get the indices of the image
        y_indices, x_indices = np.indices(image.shape)

        # Calculate the total weight
        total_weight = np.sum(image)

        # Calculate the weighted sums of the x and y coordinates
        x_weighted_sum = np.sum(x_indices * image)
        y_weighted_sum = np.sum(y_indices * image)

        # Calculate the weighted center
        x_center = x_weighted_sum / total_weight
        y_center = y_weighted_sum / total_weight

        if np.isnan(x_center) or np.isnan(y_center):
            print("No object detected")
            return 50, 50

        return x_center, y_center

    def image_filter(self, image, target_size=100):
        masked = image.copy()
        masked[masked != 0] = 255

        size = min(image.shape)

        def trim_image():
            nonlocal masked, size

            size /= 2
            if size < target_size:
                size = target_size
            x_cen, y_cen = self.weighted_average(masked)

            x0, x1 = max(0, int(x_cen - size // 2)), min(masked.shape[1], int(x_cen + size // 2))
            y0, y1 = max(0, int(y_cen - size // 2)), min(masked.shape[0], int(y_cen + size // 2))

            masked = masked[y0:y1, x0:x1]

            return x0, y0

            # return x_cen, y_cen

        x_offset, y_offset = 0, 0

        while size != target_size:
            offset = trim_image()

            x_offset += offset[0]
            y_offset += offset[1]

        roi = slice(y_offset, y_offset + target_size), slice(x_offset, x_offset + target_size)
        return image[roi], (y_offset + target_size // 2, x_offset + target_size // 2)

    def _update(self, frame):
        if not self.locking:
            new_data, _ = cam.expose(int(self.exposure), gain=int(self.gain), bbp=8)
            self.locked_image = None
            self.ctr = 0
        elif self.locking and not self.tracking:
            if self.locked_image is not None:
                return [self.im]
            img, _ = cam.expose(int(self.exposure), gain=int(self.gain), bbp=8)
            img, roi = self.image_filter(img)

            self.locked_image = img
            new_data = img
            self.roi = ((int(roi[0] - 50), int(roi[1] - 50)), (100, 100))
            self.ctr = 0
        else:
            self.ctr += 1
            new_data, _ = cam.expose(int(self.exposure), gain=int(self.gain), bbp=8, roi=self.roi)
            self.locked_image = None
            if self.ctr % 200 == 0:
                x_cen, y_cen = self.weighted_average(new_data)
                self.roi = ((int(self.roi[0][0] + x_cen - 50), int(self.roi[0][1] + y_cen - 50)), (100, 100))
            image_path = os.path.join('images', f'frame_{self.ctr:07d}.png')
            cv2.imwrite(image_path, new_data.astype(np.uint8))

        new_data = new_data.transpose()

        self.im.set_data(new_data)
        self.im.set_clim(vmin=0, vmax=255)

        # 更新图像尺寸
        if new_data.shape != self.img_data.shape:
            self.img_data = new_data
            self.im.set_extent([0, new_data.shape[1], 0, new_data.shape[0]])

        if self.tracking:
            x, y = self.roi[0]
            self.ax.set_title(f"ROI: ({x:.0f}, {y:.0f})")
        else:
            self.ax.set_title('')

        return [self.im]


if __name__ == "__main__":
    cam = Camera()
    cam.config_continuous_mode()
    viewer = RealTimeImaging()
    plt.show()
