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

    print(result, camera_id.value)



if __name__ == "__main__":
    get_sdk_version()
    get_camera_id()
