import ctypes
import numpy as np


# Load the shared library
lib = ctypes.CDLL('../../c++/libcamera.so')

lib.loadCameraId.argtypes = [ctypes.c_char_p]
lib.loadCameraId.restype = ctypes.c_uint


def get_sdk_version() -> str:
    sdk_version = np.zeros(4, dtype=np.uint32)
    ptr = sdk_version.ctypes.data_as(ctypes.POINTER(ctypes.c_uint32))
    lib.SDKVersion(ptr)

    return f"V20{sdk_version[0]}{sdk_version[1]:02}{sdk_version[2]:02}_{sdk_version[3]}"


def get_camera_id() -> str:
    camera_id = ctypes.create_string_buffer(32)
    result = lib.loadCameraId(camera_id)

    match result:
        case 0:
            return camera_id.value.decode("utf-8")
        case 1:
            raise RuntimeError("Failed to initialize QHYCCD SDK")
        case 2:
            raise RuntimeError("No camera found")
        case 3:
            raise RuntimeError("Detected devices are not supported")
        case 4:
            raise RuntimeError("SDK cannot be released")
        case _:
            raise RuntimeError("Unknown error")


if __name__ == "__main__":
    get_sdk_version()
    camera_id = get_camera_id()
    print(camera_id)
