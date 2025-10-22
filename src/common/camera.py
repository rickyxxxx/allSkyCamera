import os
import sys
import ctypes
from typing import Callable

import numpy as np
from PIL import Image, ImageDraw, ImageFont

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(PROJECT_ROOT)

from src.common.gps import GTU7
from src.common.thermal import AHT20


class Camera:

    def __init__(self) -> None:
        self.lib = self._load_library()
        self.error_list = self._load_error_types()

        self.configured = False
        self.single_frame_mode = True
        self.streaming = False

        self.camera_id = self.get_camera_id()
        self.cam_ptr = self.get_camera_handle()
        self.color = self.is_color()
        self.bayer_matrix = self.get_bayer_matrix()
        self.gps = GTU7().connect()
        self.thermal = AHT20()

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

    @staticmethod
    def _load_library() -> ctypes:
        so_folder = os.path.join(PROJECT_ROOT, "cpp", "build")
        lib_files = filter(lambda x: x.endswith(".so"), os.listdir(so_folder))

        if (lib_file := next(lib_files, None)) is None:
            raise FileNotFoundError("Camera library file do not exists!")

        # TODO: check for the number of .so files under the folder and only keep the latest.

        return ctypes.CDLL(os.path.join(so_folder, lib_file))

    @staticmethod
    def _load_error_types() -> dict[int: str]:
        errors: dict[int: str] = {}
        path = os.path.join(PROJECT_ROOT, "cpp", "src", "camera.cpp")

        with open(path, 'r') as f:
            for line in f.readlines():
                if not line.startswith("#define"):
                    continue
                line = line.lstrip("#define ").rstrip("U\n")
                msg, value = line.split(" ")
                msg = msg.replace("_", " ").capitalize()
                errors[int(value)] = msg

        return errors

    def _error_check(self, func: Callable) -> Callable:
        def inner(*args, **kwargs) -> None:
            if not (ret := func(*args, **kwargs)):
                return  # do not throw error
            err_msg = self.error_list.get(ret)
            raise RuntimeError(f"Driver error: {err_msg}")

        return inner

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

        self.resolution = int(scan_info[0]), int(scan_info[1])
        self.chip_size = float(chip_info[0]), float(chip_info[1])
        self.pixel_size = float(chip_info[2]), float(chip_info[3])
        self.max_bit_depth = int(scan_info[2])

    def is_color(self) -> bool:     # check if the current camera is a colored camera
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
        if self.bit_depth == bit_depth:
            return

        if bit_depth not in [8, 16]:
            raise ValueError(f"Bit depth must be 8 or 16, got {bit_depth}")
        if not self.single_frame_mode:
            self._pause_live_stream()
        self._error_check(self.lib.setBitDepth)(self.cam_ptr, bit_depth)

        self.bit_depth = bit_depth

    def set_exposure_time(self, exposure_time: int) -> None:
        if self.exp_time == exposure_time:
            return

        if not 100 <= exposure_time <= 100_000_000:
            raise ValueError("Exposure time must be between 100us and 100s")
        if not self.single_frame_mode:
            self._pause_live_stream()
        self._error_check(self.lib.setExposureTime)(self.cam_ptr, exposure_time)

        self.exp_time = exposure_time

    def set_gain(self, gain: int) -> None:
        if self.gain == gain:
            return

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

        xy = max(xy[0], 0), (max(xy[1], 0))
        xy = min(xy[0], self.resolution[0] - wh[0]), min(xy[1], self.resolution[1] - wh[1])
        if not self.single_frame_mode:
            self._pause_live_stream()
        exp_region = np.array((*xy, *wh), dtype=np.uint32)
        p_exp_region = exp_region.ctypes.data_as(ctypes.POINTER(ctypes.c_uint32))
        self._error_check(self.lib.setROI)(self.cam_ptr, p_exp_region)

        self.roi = xy, wh

    def expose(self, exposure_time, roi=None, gain=10, bbp=16) -> np.ndarray:
        # exposure_time in us
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
        ctype = ctypes.c_uint16 if bbp == 16 else ctypes.c_uint8
        p_image = self.image_data.ctypes.data_as(ctypes.POINTER(ctype))

        wh = roi[1][0], roi[1][1]
        roi = np.array(roi, dtype=np.uint32).flatten()
        p_roi = roi.ctypes.data_as(ctypes.POINTER(ctypes.c_uint32))

        if not self.streaming and not self.single_frame_mode:
            self._error_check(self.lib.beginLiveStream)(self.cam_ptr)   
            self.streaming = True

        if self.single_frame_mode:
            self._error_check(self.lib.exposeSingle)(self.cam_ptr, p_image, bbp, p_roi)
        else:
            self._error_check(self.lib.exposeLive)(self.cam_ptr, p_image, bbp, p_roi)

        img_shape = (wh[1], wh[0], channel) if self.color else (wh[1], wh[0])

        return self.image_data.reshape(img_shape)

    def close(self):
        self.lib.close(self.cam_ptr)
        self.gps.close()

    @property
    def serial_number(self):
        return self.camera_id.split("-")[-1]

    @property
    def model(self):
        return self.camera_id.split("-")[0]

    def draw_text(self, text: str, data: np.ndarray):
        box_size = (600, 200)
        mode = "L" if len(data.shape) == 2 else "RGB"
        new_image = Image.new(mode, box_size, color=0)  # background black

        draw = ImageDraw.Draw(new_image)

        font_path = os.path.join(os.path.dirname(__file__), "../assets/font.ttf")
        font = ImageFont.truetype(font_path, 30)

        # Set white color for text
        if mode == "L":
            color = 255  # white in grayscale
        else:
            color = (255, 255, 255)  # white in RGB

        draw.text((0, 0), text, font=font, fill=color)

        # Convert image to NumPy array
        dtype = np.uint8 if self.bit_depth == 8 else np.uint16
        data[0:box_size[1], 0:box_size[0]] = np.array(new_image).astype(dtype)

    def save_jpg(self, filename, image):
        image = Image.fromarray(image, mode='L')
        image.save(filename, format='JPEG')


if __name__ == "__main__":
    cam = Camera()
    cam.config_single_mode()
    print(cam.model, cam.serial_number, cam.gps.status, cam.thermal.temp, cam.thermal.humidity)
    img = cam.expose(1_000, bbp=8)
    cam.save_jpg("img.jpg", img)
    cam.close()
