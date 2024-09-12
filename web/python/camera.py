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
        scan_info = np.zeros(7, dtype=np.uint32)
        p_scan_info = scan_info.ctypes.data_as(ctypes.POINTER(ctypes.c_uint32))
        chip_info = np.zeros(4, dtype=np.float64)
        p_chip_info = chip_info.ctypes.data_as(ctypes.POINTER(ctypes.c_double))

        retVal = self.funcs.getChipInfo(self.cam_ptr, p_scan_info, p_chip_info)
        print(scan_info, chip_info)

    def _connect_camera(self) -> any:
        cam = bytes(self.camera_id, encoding='utf-8')
        cam_ptr = self.funcs.connectCamera(cam)

        print("cam_ptr type: ", type(cam_ptr))

        if not cam_ptr:
            raise RuntimeError("Failed to connect to the camera")

        return cam_ptr

    def _disconnect_camera(self) -> None:
        pass

    def _release_sdk(self) -> None:
        pass

    def exposure(self) -> np.ndarray:
        pass

    def close(self) -> None:
        pass

    def info(self) -> str:
        pass


if __name__ == "__main__":
    import os
    camera = Camera(os.environ["ALL_SKY_CAMERA"])
    print("sdk version: ", camera.sdk_version)
    print("camera id: ", camera.camera_id)

