import time
import ctypes

import cv2
import numpy as np
from astropy.io import fits


class Camera:

    def __init__(self, project_path: str) -> None:
        self.funcs = ctypes.CDLL(f"{project_path}/shared/libcamera.so")

        self._set_arg_res_types()

        self.sdk_version = self._get_sdk_version()
        self.camera_id = self._get_camera_id()
        self.cam_ptr = self._connect_camera()
        self._get_chip_info()
        # self.firmware_version = self._get_firmware_version()

        self.connected = False
        self.binMode = None
        self.expRegion = None
        self.bitDepth = None
        self.gain = None
        self.offset = None
        self.exposureTime = None

    def _get_sdk_version(self) -> str:
        sdk_version = np.zeros(4, dtype=np.uint32)
        ptr = sdk_version.ctypes.data_as(ctypes.POINTER(ctypes.c_uint32))
        self.funcs.SDKVersion(ptr)

        return f"V20{sdk_version[0]}{sdk_version[1]:02}{sdk_version[2]:02}_{sdk_version[3]}"

    def _get_firmware_version(self) -> str:
        firmware_version = np.zeros(4, dtype=np.uint16)
        ptr = firmware_version.ctypes.data_as(ctypes.POINTER(ctypes.c_uint32))
        self.funcs.FirmwareVersion(self.cam_ptr, ptr)

        print(firmware_version)

        return ""

    def _set_arg_res_types(self) -> None:
        self.funcs.getCameraId.argtypes = [ctypes.c_char_p]
        self.funcs.getCameraId.restype = ctypes.c_uint

        self.funcs.connectCamera.argtypes = [ctypes.c_char_p]
        self.funcs.connectCamera.restype = ctypes.c_void_p

        # self.funcs.FirmwareVersion.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint)]

        self.funcs.getChipInfo.restype = ctypes.c_uint
        self.funcs.initCamera.restype = ctypes.c_uint
        self.funcs.expose.restype = ctypes.c_uint

    def _get_camera_id(self) -> str:
        camera_id = ctypes.create_string_buffer(32)
        retVal = self.funcs.getCameraId(camera_id)

        if retVal == 0:
            return camera_id.value.decode("utf-8")
        elif retVal == 1:
            raise RuntimeError("Failed to initialize QHYCCD SDK")
        elif retVal == 2:
            raise RuntimeError("No camera found")
        elif retVal == 3:
            raise RuntimeError("Detected devices are not supported")
        elif retVal == 4:
            raise RuntimeError("SDK cannot be released")
        else:
            raise RuntimeError("Unknown error")

    def _get_chip_info(self) -> None:
        scan_info = np.zeros(3, dtype=np.uint32)
        p_scan_info = scan_info.ctypes.data_as(ctypes.POINTER(ctypes.c_uint32))
        chip_info = np.zeros(4, dtype=np.float64)
        p_chip_info = chip_info.ctypes.data_as(ctypes.POINTER(ctypes.c_double))

        retVal = self.funcs.getChipInfo(self.cam_ptr, p_scan_info, p_chip_info)

        if retVal:
            raise RuntimeError("Failed to get chip info")

        self.resolution = (int(scan_info[0]), int(scan_info[1]))
        self.chip_size = (float(chip_info[0]), float(chip_info[1]))
        self.pixel_size = (float(chip_info[2]), float(chip_info[3]))
        self.max_depth = int(scan_info[2])

    def _connect_camera(self) -> any:
        cam = bytes(self.camera_id, encoding='utf-8')
        cam_ptr = self.funcs.connectCamera(cam)

        if not cam_ptr:
            raise RuntimeError("Failed to get the camera's handle")

        self.connected = True

        retVal = self.funcs.initCamera(cam_ptr)
        if retVal == 1:
            raise RuntimeError("Failed to set the camera's stream mode")
        elif retVal == 2:
            raise RuntimeError("Failed to initialize the camera")

        retVal = self.funcs.checkTraffic(cam_ptr)
        if retVal:
            raise RuntimeError("usb traffic jam detected")

        return cam_ptr

    def _disconnect_camera(self) -> None:
        self.funcs.disconnectCamera(self.cam_ptr)

    def _release_sdk(self) -> None:
        self.funcs.releaseSDK()

    def _set_gain(self, gain: int) -> None:
        retVal = self.funcs.setGain(self.cam_ptr, gain)
        if retVal:
            raise RuntimeError("Error setting gain")

    def _set_offset(self, offset: int) -> None:
        retVal = self.funcs.setOffset(self.cam_ptr, offset)
        if retVal:
            raise RuntimeError("Error setting offset")

    def _set_exposure(self, exposureTime: int) -> None:
        if not (22 < exposureTime < 100000000):
            raise ValueError("Offset must be between 22us and 100s")
        retVal = self.funcs.setExposureTime(self.cam_ptr, exposureTime)
        if retVal:
            raise RuntimeError("Error setting exposure")

    def _set_exp_region(self, exp_region: tuple[int, int, int, int]) -> None:
        exp_region = np.array(exp_region, dtype=np.uint32)
        p_exp_region = exp_region.ctypes.data_as(ctypes.POINTER(ctypes.c_uint32))
        retVal = self.funcs.setResolution(self.cam_ptr, p_exp_region)
        if retVal:
            raise RuntimeError("Error setting resolution")

    def _set_bin_mode(self, bin_mode: tuple[int, int]) -> None:
        bin_mode = np.array(bin_mode, dtype=np.int32)
        p_bin_mode = bin_mode.ctypes.data_as(ctypes.POINTER(ctypes.c_int32))

        retVal = self.funcs.setBinMode(self.cam_ptr, p_bin_mode)
        if retVal:
            raise RuntimeError("Error setting bin mode")

    def _set_bit_depth(self, bit_depth: int) -> None:
        retVal = self.funcs.setBitDepth(self.cam_ptr, bit_depth)
        if retVal:
            raise RuntimeError("Error setting bit depth")

    def expose(self, exposureTime, exp_region=None, bin_mode=(1, 1), gain=10, offset=140, bbp=16) \
            -> tuple[np.ndarray, float]:
        if exp_region is None:
            exp_region = (0, 0, self.resolution[0], self.resolution[1])

        if self.binMode != bin_mode:
            self._set_bin_mode(bin_mode)
            self.binMode = bin_mode

        if self.expRegion != exp_region:
            self._set_exp_region(exp_region)
            self.expRegion = exp_region

        if self.bitDepth != bbp:
            self._set_bit_depth(bbp)
            self.bitDepth = bbp

        if self.gain != gain:
            self._set_gain(gain)
            self.gain = gain

        if self.offset != offset:
            self._set_offset(offset)
            self.offset = offset

        if self.exposureTime != exposureTime:
            self._set_exposure(exposureTime)
            self.exposureTime = exposureTime

        """for exp_region: (start_x, start_y, width, height)"""
        pixels = np.zeros(exp_region[2] * exp_region[3], dtype=np.uint16)
        p_pixels = pixels.ctypes.data_as(ctypes.POINTER(ctypes.c_uint16))

        exp_region = np.array(exp_region, dtype=np.uint32)
        p_exp_region = exp_region.ctypes.data_as(ctypes.POINTER(ctypes.c_uint32))

        exposure_start = time.time()
        retVal = self.funcs.expose(self.cam_ptr, p_pixels, bbp, p_exp_region)
        actual_exposure = time.time() - exposure_start

        match retVal:
            case 0:
                return pixels.reshape(exp_region[3], exp_region[2]), actual_exposure
            case 1:
                raise RuntimeError("Error starting exposure")
            case 2:
                raise RuntimeError("Error reading data")
            case _:
                raise RuntimeError("Unknown error")

    def close(self) -> None:
        if self.connected:
            self._disconnect_camera()
        self._release_sdk()

    def info(self) -> str:
        return (f"Camera ID: {self.camera_id}\n"
                f"SDK Version: {self.sdk_version}\n"
                f"Chip Size: {self.chip_size} mm\n"
                f"Resolution: {self.resolution}\n"
                f"Pixel Size: {self.pixel_size} um\n"
                f"Max Depth: {self.max_depth} bit")

    @staticmethod
    def array_to_fits(array: np.ndarray, filename: str) -> None:
        hdu = fits.PrimaryHDU(array)
        hudl = fits.HDUList([hdu])
        hudl.writeto(f"{filename}.fits", overwrite=True)

    @staticmethod
    def array_to_png(array: np.ndarray, filename: str) -> None:
        # Step 1: Read the 16-bit monochrome image array
        original_height, original_width = array.shape

        # Step 2: Resize the image to 1/4 of its original resolution
        new_width = original_width // 2
        new_height = original_height // 2
        resized_image = cv2.resize(array, (new_width, new_height), interpolation=cv2.INTER_AREA)

        # Step 3: Normalize the image data to 8-bit
        normalized_image = cv2.normalize(resized_image, None, 0, 255, cv2.NORM_MINMAX)
        normalized_image = np.uint8(normalized_image)

        # Step 4: Save the resized image as a PNG file
        cv2.imwrite(f"{filename}.png", normalized_image)


if __name__ == "__main__":
    import os
    camera = Camera(os.environ["ALL_SKY_CAMERA"])
    print(camera.info())
    for i in range(8):
        exp_time = 220 * (2 ** i)
        img, c_exposure_time = camera.expose(exp_time)
        print(f"Exposure time: {c_exposure_time:.2f} seconds")
        start = time.time()
        camera.array_to_fits(img, f"{os.environ['ALL_SKY_CAMERA']}shared/img/pic_{i}")
        print(f"{time.time() - start:.2f} seconds to save")
        start = time.time()
        camera.array_to_png(img, f"{os.environ['ALL_SKY_CAMERA']}shared/img/pic_{i}")
        print(f"{time.time() - start:.2f} seconds to convert")
    camera.close()


