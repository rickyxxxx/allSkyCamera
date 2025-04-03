import os
import ctypes
from time import time
from typing import Callable

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# from camera.gps_driver.GTU7 import GTU7


class Camera:

    def __init__(self) -> None:
        self.package_path = os.path.join(os.path.dirname(__file__), "camera_driver")
        lib_name = [f for f in os.listdir(self.package_path) if f.endswith(".so")][0]
        self.lib = ctypes.CDLL(os.path.join(self.package_path, lib_name))

        self.error_list: dict[int:str] = self._load_errors()
        self.configured = False
        self.single_frame_mode = True
        self.streaming = False

        self.camera_id = self.get_camera_id()
        self.cam_ptr = self.get_camera_handle()
        self.test()
        self.color = self.is_color()
        self.bayer_matrix = self.get_bayer_matrix()
        try:
            self.gps = GTU7()
        except:
            pass

        self.resolution: tuple[int, int] = (0, 0)
        self.chip_size: tuple[float, float] = (0.0, 0.0)
        self.pixel_size: tuple[float, float] = (0.0, 0.0)   # physical size in um
        self.max_bit_depth: int = 0
        self.roi: tuple[tuple[int, int], tuple[int, int]] | None = None
        self.exp_time: int | None = None
        self.bit_depth: int | None = None
        self.gain: int | None = None
        self.image_data = None

        self.get_chip_info()

    def _error_check(self, func: Callable) -> Callable:
        def inner(*args, **kwargs) -> None:
            if not (ret := func(*args, **kwargs)):
                return  # do not throw error
            err_msg = self.error_list.get(ret)
            raise RuntimeError(f"Driver error: {err_msg}")

        return inner

    def _load_errors(self) -> dict[int: str]:
        error_list = {}
        cpp_path = os.path.join(self.package_path, "camera.cpp")

        f = open(cpp_path, 'r')
        for line in f.readlines():
            if not line.startswith("#define"):
                continue
            line = line.lstrip("#define ").rstrip("U\n")
            msg, value = line.split(" ")
            msg = msg.replace("_", " ").capitalize()
            error_list[int(value)] = msg
        f.close()

        return error_list

    def get_camera_id(self) -> str:
        camera_id = ctypes.create_string_buffer(32)
        self._error_check(self.lib.getCameraId)(camera_id)
        return camera_id.value.decode("utf-8")

    def get_camera_handle(self) -> ctypes.c_void_p:
        cam_id = bytes(self.camera_id, encoding='utf-8')
        cam_ptr = self.lib.getCameraHandle(cam_id)

        if not cam_ptr:
            raise RuntimeError("Failed to get the camera's handle")

        return cam_ptr

    def get_chip_info(self) -> None:
        scan_info = np.zeros(3, dtype=np.uint32)
        p_scan_info = scan_info.ctypes.data_as(ctypes.POINTER(ctypes.c_uint32))
        chip_info = np.zeros(4, dtype=np.float64)
        p_chip_info = chip_info.ctypes.data_as(ctypes.POINTER(ctypes.c_double))

        self._error_check(self.lib.getChipInfo)(self.cam_ptr, p_scan_info, p_chip_info)

        # self._error_check(
        #     self.lib.getChipInfo(self.cam_ptr, p_scan_info, p_chip_info)
        # )

        self.resolution = int(scan_info[0]), int(scan_info[1])
        self.chip_size = float(chip_info[0]), float(chip_info[1])
        self.pixel_size = float(chip_info[2]), float(chip_info[3])
        self.max_bit_depth = int(scan_info[2])

    def is_color(self) -> bool:
        ret = self.lib.isColor(self.cam_ptr)
        return bool(ret)

    def get_bayer_matrix(self) -> str:
        if not self.color:
            return "Monochrome"
        ret = self.lib.getBayerMatrix(self.cam_ptr)
        if not 1 <= ret <= 4:
            raise RuntimeError("Invalid bayer matrix value")
        return ["GBRG", "GRBG", "BGGR", "RGGB"][ret - 1]

    def config_continuous_mode(self) -> None:
        self._error_check(self.lib.configContinuousMode)(self.cam_ptr)
        self.single_frame_mode = False
        self.configured = True
        
    def config_single_mode(self) -> None:
        self._error_check(self.lib.configSingleMode)(self.cam_ptr)
        self.single_frame_mode = True
        self.configured = True

    def _pause_live_stream(self) -> None:
        if not self.streaming:
            return
        self._error_check(self.lib.endLiveStream)(self.cam_ptr)
        self.streaming = False

    def set_bit_depth(self, bit_depth: int) -> None:
        
        # if self.color:
        #     bit_depth = 8

        if self.bit_depth == bit_depth:
            return

        print(f"change bbp to: {bit_depth}")

        if bit_depth not in [8, 16]:
            raise ValueError(f"Bit depth must be 8 or 16, got {bit_depth}")
        if not self.single_frame_mode:
            self._pause_live_stream()
        self._error_check(self.lib.setBitDepth)(self.cam_ptr, bit_depth)

        self.bit_depth = bit_depth

    def set_exposure_time(self, exposure_time: int) -> None:
        if self.exp_time == exposure_time:
            return
        print(f"change exp to: {exposure_time}")
        if not 100 <= exposure_time <= 100_000_000:
            raise ValueError("Exposure time must be between 100us and 100s")
        if not self.single_frame_mode:
            self._pause_live_stream()
        self._error_check(self.lib.setExposureTime)(self.cam_ptr, exposure_time)

        self.exp_time = exposure_time

    def set_gain(self, gain: int) -> None:
        if self.gain == gain:
            return

        print(f"change gain to: {gain}")

        if gain < 1:
            raise ValueError("Gain must be greater than or equal to 1")
        if not self.single_frame_mode:
            self._pause_live_stream()
        self._error_check(self.lib.setGain)(self.cam_ptr, gain)

        self.gain = gain

    def set_roi(self, xy: tuple[int, int], wh: tuple[int, int]) -> None:
        if (self.roi
                and self.roi[0][0] == xy[0]
                and self.roi[0][1] == xy[1]
                and self.roi[1][0] == wh[0]
                and self.roi[1][1] == wh[1]):
            return

        print(f"change roi to: {xy}, {wh}")

        xy = max(xy[0], 0), (max(xy[1], 0))
        xy = min(xy[0], self.resolution[0] - wh[0]), min(xy[1], self.resolution[1] - wh[1])
        if not self.single_frame_mode:
            self._pause_live_stream()
        exp_region = np.array((*xy, *wh), dtype=np.uint32)
        p_exp_region = exp_region.ctypes.data_as(ctypes.POINTER(ctypes.c_uint32))
        self._error_check(self.lib.setROI)(self.cam_ptr, p_exp_region)

        self.roi = xy, wh

    def expose(self, exposure_time, roi=None, gain=10, bbp=16) -> tuple[np.ndarray, float]:
        if roi is None:
            roi = (0, 0), self.resolution

        self.set_roi(*roi)
        self.set_exposure_time(exposure_time)
        self.set_bit_depth(bbp)
        self.set_gain(gain)

        bbp = self.bit_depth

        dtype = np.uint16 if bbp == 16 else np.uint8
        channel = 3 if self.color else 1
        if self.image_data is None:
            self.image_data = np.zeros(roi[1][0] * roi[1][1] * channel, dtype=dtype)
        else:
            self.image_data.fill(0)
        # image_data = np.zeros(roi[1][0] * roi[1][1] * channel, dtype=dtype)
        ctype = ctypes.c_uint16 if bbp == 16 else ctypes.c_uint8
        p_image = self.image_data.ctypes.data_as(ctypes.POINTER(ctype))

        wh = roi[1][0], roi[1][1]
        roi = np.array(roi, dtype=np.uint32).flatten()
        p_roi = roi.ctypes.data_as(ctypes.POINTER(ctypes.c_uint32))

        if not self.streaming and not self.single_frame_mode:
            self._error_check(self.lib.beginLiveStream)(self.cam_ptr)   
            self.streaming = True

        exposure_start = time()
        if self.single_frame_mode:
            self._error_check(self.lib.exposeSingle)(self.cam_ptr, p_image, bbp, p_roi)
        else:
            self._error_check(self.lib.exposeLive)(self.cam_ptr, p_image, bbp, p_roi)
        actual_exposure_time = time() - exposure_start

        img_shape = (wh[1], wh[0], channel) if self.color else (wh[1], wh[0])

        return self.image_data.reshape(img_shape), actual_exposure_time

    def close(self):
        self.lib.close(self.cam_ptr)

    @property
    def serial_number(self):
        return self.camera_id.split("-")[-1]

    @property
    def model(self):
        return self.camera_id.split("-")[0]

    def draw_text(self, text: str, data: np.ndarray) -> np.ndarray:
        box_size = (600, 200)
        mode = "L" if len(data.shape) == 2 else "RGB"
        new_image = Image.new(mode, box_size, color=0)

        draw = ImageDraw.Draw(new_image)

        font_path = os.path.join(os.path.dirname(__file__), "../assets/font.ttf")
        font = ImageFont.truetype(font_path, 30)

        # Draw text (black)
        color = (1 << self.bit_depth) - 1
        draw.text((0, 0), text, font=font, fill=color)

        # Convert image to NumPy array
        dtype = np.uint8 if self.bit_depth == 8 else np.uint16

        data[0:box_size[1], 0:box_size[0]] = np.array(new_image).astype(dtype)

    def exposure_text(self) -> str:
        loc = self.gps.get_location_str()
        datetime = self.gps.get_datetime()
        expt, unit = self.exp_time, "us"
        if expt >= 1000:
            expt /= 1000
            unit = "ms"
        if expt >= 1000:
            expt /= 1000
            unit = "s"
        setting = f"exposure time: {expt:.2f} {unit}"
        setting += f", gain: {self.gain}"
        return loc + "\n" + datetime + "\n" + setting

    def test(self):
        print("start testing")
        self.lib.test(self.cam_ptr)
        print("end testing")


if __name__ == "__main__":
    from PIL import Image
    import numpy as np
    import psutil

    cam = Camera()
    cam.config_single_mode()
    ctr = 0
    try:
        while True:
            ctr += 1
            img, _ = cam.expose(250, gain=10)
            ram_per = psutil.virtual_memory()[2]
            ram_used = psutil.virtual_memory()[3] / 1000_000_000
            print(f"{ctr}: {np.sum(img.flatten())}")
            print(f"{ram_per}%  used: {ram_used:.2f}GB")
    except Exception:
        pass
    # cam.test()

#    img, t = cam.expose(10_000, gain=10)
#    info = cam.exposure_text()

#    cam.draw_text(info, img)
#    image = Image.fromarray(img, 'RGB')
#    image.save(f"./image_{0}.png"
    finally:
        cam.close()

