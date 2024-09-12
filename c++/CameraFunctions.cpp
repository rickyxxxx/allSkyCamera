//
// Created by Ruitao Xu on 9/11/2024.
//
#include <string.h>
#include "qhyccd.h"

// functions that are to be called from Python
extern "C" {
    void SDKVersion(unsigned int *);
    void FirmwareVersion(qhyccd_handle *, unsigned int *);
    unsigned int getCameraId(char *);
    qhyccd_handle* connectCamera(char *);
}

void SDKVersion(unsigned int *version) {
    GetQHYCCDSDKVersion(&version[0], &version[1], &version[2], &version[3]);
}

void FirmwareVersion(qhyccd_handle *pCamHandle, unsigned int *version) {
    GetQHYCCDFWVersion(pCamHandle, &version[0], &version[1], &version[2], &version[3]);
}

unsigned int getCameraId(char *camId) {
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


qhyccd_handle* connectCamera(char *camId){
    return OpenQHYCCD(camId);
}


//unsigned int getChipInfo(qhyccd_handle *pCamHandle, unsigned int *scanInfo, double *chipInfo) {
//    // get effective area
//    unsigned int retVal = GetQHYCCDId(pCamHandle, &scanInfo[0], &scanInfo[1], &scanInfo[2], &scanInfo[3]);
//    if (QHYCCD_SUCCESS != retVal)
//        return 1;       // error getting the camera's effective area
//
//    // get chip info
//    retVal = GetQHYCCDChipInfo(pCamHandle, &chipInfo[0], &chipInfo[1], &scanInfo[4], &scanInfo[5], &chipInfo[2],
//                               &chipInfo[3], &scanInfo[6]);
//    if (QHYCCD_SUCCESS != retVal)
//        return 2;       // error getting the camera's chip info
//
//    return 0;
//}
//
//void exposure(qhyccd_handle *pCamHandle) {
////    SetQHYCCDParam(pCamHandle, CONTROL_EXPOSURE, expTime);
//}

