import ctypes
import numpy as np


class Camera:

    def __init__(self, project_path: str) -> None:
        self.funcs = ctypes.CDLL(f"{project_path}/shared/libcamera.so")

        self._set_arg_res_types()

        self.sdk_version = self._get_sdk_version()
        self.camera_id = self._get_camera_id()
        self.cam_ptr = self._connect_camera()
        self._get_chip_info()
        # self.firmware_version = self._get_firmware_version()

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

        return cam_ptr

    def _disconnect_camera(self) -> None:
        pass

    def _release_sdk(self) -> None:
        pass

    def expose(self, exposure, exp_region=None, bin_mode=(1, 1), gain=10, offset=140) -> np.ndarray:
        if exp_region is None:
            exp_region = (0, 0, self.resolution[0], self.resolution[1])

        """for exp_region: (start_x, start_y, width, height)"""
        settings = np.array([gain, offset, exposure], dtype=np.int32)
        p_settings = settings.ctypes.data_as(ctypes.POINTER(ctypes.c_int32))

        exp_region = np.array(exp_region, dtype=np.uint32)
        p_exp_region = exp_region.ctypes.data_as(ctypes.POINTER(ctypes.c_uint32))

        bin_mode = np.array(bin_mode, dtype=np.int32)
        p_bin_mode = bin_mode.ctypes.data_as(ctypes.POINTER(ctypes.c_int32))

        pixels = np.zeros(exp_region[2] * exp_region[3], dtype=np.uint16)
        p_pixels = pixels.ctypes.data_as(ctypes.POINTER(ctypes.c_uint16))

        retVal = self.funcs.expose(self.cam_ptr, p_exp_region, p_bin_mode, p_settings, p_pixels)
        match retVal:
            case 0:
                return pixels.reshape(exp_region[3], exp_region[2])
            case 1:
                raise RuntimeError("USB communication error")
            case 2:
                raise RuntimeError("Error setting the USB speed")
            case 3:
                raise RuntimeError("Error setting the resolution")
            case 4:
                raise RuntimeError("Error setting the binning mode")
            case 5:
                raise RuntimeError("Error checking the camera's bit depth")
            case 6:
                raise RuntimeError("Error setting the camera's bit depth")
            case 7:
                raise RuntimeError("Error checking the camera's gain")
            case 8:
                raise RuntimeError("Error setting the camera's gain")
            case 9:
                raise RuntimeError("Error checking the camera's offset")
            case 10:
                raise RuntimeError("Error setting the camera's offset")
            case 11:
                raise RuntimeError("Error setting the camera's exposure time")
            case 12:
                raise RuntimeError("Error starting the exposure")
            case 13:
                raise RuntimeError("Error reading the data")
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


if __name__ == "__main__":
    import os
    import matplotlib.pyplot as plt
    camera = Camera(os.environ["ALL_SKY_CAMERA"])
    print(camera.info())
    for i in range(10):
        input("Press Enter to take a picture")
        img = camera.expose(22000)
        plt.imsave(f"img_{i}.png", img)


