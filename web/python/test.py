import ctypes

# Load the shared library
lib = ctypes.CDLL('../../c++/libcamera.so')

# Specify the return type of the SDKVersion function
lib.SDKVersion.restype = ctypes.POINTER(ctypes.c_uint * 4)

# Call the SDKVersion function
sdk_version_ptr = lib.SDKVersion()

# Convert the result to a Python list
sdk_version = list(sdk_version_ptr.contents)

print(f"Version: {sdk_version}")
