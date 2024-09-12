//
// Created by ricky on 9/11/2024.
//
#include <string.h>
#include "qhyccd.h"

// functions that are to be called from Python
extern "C" {
    void SDKVersion(unsigned int*);
    unsigned int loadCameras(char*);
}

void SDKVersion(unsigned int* version) {
    GetQHYCCDSDKVersion(&version[0], &version[1], &version[2], &version[3]);
}

unsigned int loadCameraId(char* camId) {
    // init SDK
    unsigned int retVal = InitQHYCCDResource();
    if (retVal != QHYCCD_SUCCESS)
        return 1;      // error initializing SDK resources

    // scan cameras
    int camCount = ScanQHYCCD();
    if (camCount == 0)
        return 2;      // no cameras found

    for (int i = 0; i < camCount; ++i) {
        retVal = GetQHYCCDId(i, camId);
        if (retVal != QHYCCD_SUCCESS)
            continue;
        // return the camera Id to the python script

        return 0;
    }

    // release SDK resources
    retVal = ReleaseQHYCCDResource();
    if (retVal != QHYCCD_SUCCESS)
        // error releasing SDK resources
        // and the detected camera is not supported
        return 4;

    return 3;          // the detected camera is not supported
}