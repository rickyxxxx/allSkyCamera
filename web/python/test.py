import ctypes

# Load the shared library
lib = ctypes.CDLL('../../c++/libcamera.so')

sdk_version = lib.SDKVersion()

print(f"Version: {sdk_version}")