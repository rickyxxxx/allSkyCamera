import ctypes

# Load the shared library
lib = ctypes.CDLL('../../c++/libcamera.so')

lib.SDKVersion.restype = ctypes.c_char_p

sdk_version = lib.SDKVersion()

print(f"Version: {sdk_version}")