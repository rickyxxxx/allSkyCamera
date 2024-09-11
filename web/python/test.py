import ctypes
import numpy as np


# Load the shared library
lib = ctypes.CDLL('../../c++/libcamera.so')


def get_sdk_version() -> str:
    sdk_version = np.zeros(4, dtype=np.uint32)
    ptr = sdk_version.ctypes.data_as(ctypes.POINTER(ctypes.c_uint32))
    lib.SDKVersion(ptr)
    print(f"Version: {sdk_version}")
    return None


if __name__ == "__main__":
    get_sdk_version()
