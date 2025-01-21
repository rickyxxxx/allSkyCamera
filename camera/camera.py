import os
import ctypes
from time import time
from typing import Callable

import numpy as np
# import matplotlib.pyplot as plt


class Camera:

    def __init__(self) -> None:
        self.package_path = os.path.dirname(__file__)
        lib_name = [f for f in os.listdir(self.package_path) if f.endswith(".so")][0]
        self.lib = ctypes.CDLL(os.path.join(self.package_path, lib_name))

        self.error_list: dict[int:str] = self._load_errors()
        self.configured = False
        self.single_frame_mode = True
        self.streaming = False

        self.camera_id = self.get_camera_id()
        self.cam_ptr = self.get_camera_handle()

        self.resolution: tuple[int, int] = (0, 0)
        self.chip_size: tuple[float, float] = (0.0, 0.0)
        self.pixel_size: tuple[float, float] = (0.0, 0.0)   # physical size in um
        self.max_bit_depth: int = 0
        self.roi: tuple[tuple[int, int], tuple[int, int]] | None = None
        self.exp_time: int | None = None
        self.bit_depth: int | None = None
        self.gain: int | None = None
        self.pixels_np = None
        self.p_pixels = None
        self.roi_np = None
        self.p_roi = None

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

        self._error_check(
            self.lib.getChipInfo(self.cam_ptr, p_scan_info, p_chip_info)
        )

        self.resolution = int(scan_info[0]), int(scan_info[1])
        self.chip_size = float(chip_info[0]), float(chip_info[1])
        self.pixel_size = float(chip_info[2]), float(chip_info[3])
        self.max_bit_depth = int(scan_info[2])

    def config_continuous_mode(self) -> None:
        self._error_check(self.lib.configContinuousMode)(self.cam_ptr)
        self.single_frame_mode = False
        self.configured = True

    def _pause_live_stream(self) -> None:
        if not self.streaming:
            return
        self._error_check(self.lib.endLiveStream)(self.cam_ptr)
        self.streaming = False

    def set_bit_depth(self, bit_depth: int) -> None:
        if bit_depth not in [8, 16]:
            raise ValueError(f"Bit depth must be 8 or 16, got {bit_depth}")
        self._pause_live_stream()
        self._error_check(self.lib.setBitDepth)(self.cam_ptr, bit_depth)

    def set_exposure_time(self, exposure_time: int) -> None:
        if not 100 <= exposure_time <= 100_000_000:
            raise ValueError("Exposure time must be between 100us and 100s")
        self._pause_live_stream()
        self._error_check(self.lib.setExposureTime)(self.cam_ptr, exposure_time)

    def set_gain(self, gain: int) -> None:
        if gain < 1:
            raise ValueError("Gain must be greater than or equal to 1")
        self._pause_live_stream()
        self._error_check(self.lib.setGain)(self.cam_ptr, gain)

    def set_roi(self, xy: tuple[int, int], wh: tuple[int, int]) -> None:
        self._pause_live_stream()
        exp_region = np.array((*xy, *wh), dtype=np.uint32)
        p_exp_region = exp_region.ctypes.data_as(ctypes.POINTER(ctypes.c_uint32))
        self._error_check(self.lib.setROI)(self.cam_ptr, p_exp_region)

    def expose(self, exposure_time, roi=None, gain=10, bbp=16) -> tuple[np.ndarray, float]:
        if roi is None:
            roi = (0, 0), self.resolution

        if self.roi != roi:
            self.set_roi(*roi)
            self.roi = roi

        if self.exp_time != exposure_time:
            self.set_exposure_time(exposure_time)
            self.exp_time = exposure_time

        if self.bit_depth != bbp:
            self.set_bit_depth(bbp)
            self.bit_depth = bbp

        if self.gain != gain:
            self.set_gain(gain)
            self.gain = gain

        dtype = np.uint16 if bbp == 16 else np.uint8
        self.pixels_np = np.zeros(roi[1][0] * roi[1][1], dtype=dtype)
        self.p_pixels = self.pixels_np.ctypes.data_as(ctypes.POINTER(ctypes.c_uint16))

        self.roi_np = np.array(roi, dtype=np.uint32).flatten()
        self.p_roi = self.roi_np.ctypes.data_as(ctypes.POINTER(ctypes.c_uint32))

        if not self.streaming:
            self._error_check(self.lib.beginLiveStream)(self.cam_ptr)
            self.streaming = True

        exposure_start = time()
        self._error_check(self.lib.expose)(self.cam_ptr, self.p_pixels, bbp, self.p_roi)
        actual_exposure_time = time() - exposure_start

        return self.pixels_np.reshape(roi[-1]), actual_exposure_time

    def close(self):
        self.lib.close(self.cam_ptr)


# if __name__ == "__main__":
#     cam = Camera()
#     cam.config_continuous_mode()
#     image, time = cam.expose(10_000, ((0, 0), (500, 500)), bbp=8)
#     print(image, time)
#     cam.close()



if __name__ == "__main__":
    print(os.getcwd())
    path = os.path.join(os.getcwd(), "qhyDriver.so")
    print(path)
    funcs = ctypes.CDLL(path)

    camera_id = ctypes.create_string_buffer(32)
    id = funcs.getCameraId(camera_id)

    pCam = funcs.getCameraHandle(camera_id)
    funcs.configContinuousMode(pCam)

    scan_info = np.zeros(3, dtype=np.uint32)
    p_scan_info = scan_info.ctypes.data_as(ctypes.POINTER(ctypes.c_uint32))
    chip_info = np.zeros(4, dtype=np.float64)
    p_chip_info = chip_info.ctypes.data_as(ctypes.POINTER(ctypes.c_double))


    exp_region = (0, 0, 3856, 2160)
    exp_region = np.array(exp_region, dtype=np.uint32)
    p_exp_region = exp_region.ctypes.data_as(ctypes.POINTER(ctypes.c_uint32))
    retVal = funcs.setROI(pCam, p_exp_region)

    funcs.setBitDepth(pCam, 8)

    funcs.setExposureTime(pCam, 10_000)
    funcs.setGain(pCam, 10)
    funcs.beginLiveStream(pCam)

    pixels = np.zeros(exp_region[2] * exp_region[3], dtype=np.uint8)
    p_pixels = pixels.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8))
    for _ in range(20):
        exposure_start = time()
        retVal = funcs.expose(pCam, p_pixels, 8, p_exp_region)
        actual_exposure = time() - exposure_start

        pixels = pixels.reshape((3856, 2160))

    funcs.endLiveStream(pCam)
