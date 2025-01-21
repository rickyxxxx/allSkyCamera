#include <string.h>
#include <iostream>
#include <fstream>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include "qhyccd.h"


// functions that are to be called from Python
extern "C" {
    void SDKVersion(unsigned int *);
    unsigned int getCameraId(char *);
    qhyccd_handle* connectCamera(char *);
    unsigned int getChipInfo(qhyccd_handle *, unsigned int *, double *);
    unsigned int initCamera(qhyccd_handle *);
    unsigned int expose(qhyccd_handle *, unsigned char *, uint32_t, unsigned int *);
    void disconnectCamera(qhyccd_handle *pCamHandle);
    void releaseSDK();
    unsigned int checkTraffic(qhyccd_handle *);
    unsigned int setResolution(qhyccd_handle *, unsigned int *);
    unsigned int setBinMode(qhyccd_handle *, int *);
    unsigned int setBitDepth(qhyccd_handle *, uint32_t);
    unsigned int setGain(qhyccd_handle *, int);
    unsigned int setOffset(qhyccd_handle *, int);
    unsigned int setExposureTime(qhyccd_handle *, int);
    unsigned int beginLiveStream(qhyccd_handle *);
    void endLiveStream(qhyccd_handle *);
}


void SDKVersion(unsigned int *version) {
    GetQHYCCDSDKVersion(&version[0], &version[1], &version[2], &version[3]);
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


qhyccd_handle* connectCamera(char *camId) {
    return OpenQHYCCD(camId);
}


unsigned int initCamera(qhyccd_handle *pCamHandle) {
    unsigned int retVal = SetQHYCCDStreamMode(pCamHandle, 1);  // Enable streaming mode for fast exposure
    if (QHYCCD_SUCCESS != retVal)
        return 1;       // error setting the camera's stream mode

    retVal = InitQHYCCD(pCamHandle);
    if (QHYCCD_SUCCESS != retVal)
        return 2;

    // Enable burst mode by default
    retVal = EnableQHYCCDBurstMode(pCamHandle, true);
    if (QHYCCD_SUCCESS != retVal)
        return 3;

    return 0;
}

unsigned int setGain(qhyccd_handle *pCamHandle, int gain) {
    unsigned int retVal = IsQHYCCDControlAvailable(pCamHandle, CONTROL_GAIN);
    if (retVal != QHYCCD_SUCCESS)
        return 1;       // error checking the camera's gain
    retVal = SetQHYCCDParam(pCamHandle, CONTROL_GAIN, gain);
    if (QHYCCD_SUCCESS != retVal) {
        getchar();
        return 2;       // error setting the camera's gain
    }

    return 0;
}

unsigned int setOffset(qhyccd_handle *pCamHandle, int offset) {
    // check and set gain
    unsigned int retVal = IsQHYCCDControlAvailable(pCamHandle, CONTROL_OFFSET);
    if (retVal != QHYCCD_SUCCESS)
        return 1;       // error checking the camera's gain
    retVal = SetQHYCCDParam(pCamHandle, CONTROL_OFFSET, offset);
    if (QHYCCD_SUCCESS != retVal) {
        getchar();
        return 2;       // error setting the camera's gain
    }

    return 0;
}

unsigned int setExposureTime(qhyccd_handle *pCamHandle, int exposureTime) {
    unsigned int retVal = SetQHYCCDParam(pCamHandle, CONTROL_EXPOSURE, exposureTime);
    if (QHYCCD_SUCCESS != retVal){
        getchar();
        return 1;      // error setting the camera's exposure time
    }
    return 0;
}

unsigned int beginLiveStream(qhyccd_handle *pCamHandle){
    unsigned int retVal = BeginQHYCCDLive(pCamHandle);
    return (QHYCCD_SUCCESS != retVal) ? 1 : 0;
}

void endLiveStream(qhyccd_handle *pCamHandle){
    StopQHYCCDLive(pCamHandle);
}

unsigned int expose(qhyccd_handle *pCamHandle, unsigned char *pImgData, uint32_t bpp, unsigned int *expRegion) {

    uint32_t w, h, channels;
    unsigned int retVal = GetQHYCCDLiveFrame(pCamHandle, &w, &h, &bpp, &channels, pImgData);
    if (QHYCCD_SUCCESS != retVal) {
        StopQHYCCDLive(pCamHandle);
        return 2;
    }

    return 0;
}

void disconnectCamera(qhyccd_handle *pCamHandle) {
    StopQHYCCDLive(pCamHandle);
    CloseQHYCCD(pCamHandle);
}

void releaseSDK() {
    ReleaseQHYCCDResource();
}
