//
// Created by Ruitao Xu on 9/11/2024.
//
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
    unsigned int expose(qhyccd_handle *, unsigned int *, int *, int *, unsigned char *);
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
    unsigned int retVal = SetQHYCCDStreamMode(pCamHandle, 0);
    if (QHYCCD_SUCCESS != retVal)
        return 1;       // error setting the camera's stream mode

    retVal = InitQHYCCD(pCamHandle);
    if (QHYCCD_SUCCESS != retVal)
        return 2;       // error initializing the camera

    return 0;
}


unsigned int getChipInfo(qhyccd_handle *pCamHandle, unsigned int *scanInfo, double *chipInfo) {
    // get chip info
    unsigned int retVal = GetQHYCCDChipInfo(pCamHandle, &chipInfo[0], &chipInfo[1], &scanInfo[0], &scanInfo[1],
                                            &chipInfo[2], &chipInfo[3], &scanInfo[2]);
    if (QHYCCD_SUCCESS != retVal)
        return 1;       // error getting the camera's chip info

    return 0;
}

unsigned int expose(qhyccd_handle *pCamHandle, unsigned int *expRegion, int *binMode, int *settings,
                    unsigned char *pImgData) {
    uint32_t bpp = 16;

    // check usb traffic
    unsigned int retVal = IsQHYCCDControlAvailable(pCamHandle, CONTROL_USBTRAFFIC);
    if (QHYCCD_SUCCESS != retVal)
        return 1;       // error checking the camera's usb traffic

    retVal = SetQHYCCDParam(pCamHandle, CONTROL_USBTRAFFIC, 10);
    if (QHYCCD_SUCCESS != retVal)
        return 2;       // error setting the camera's usb traffic

    retVal = SetQHYCCDResolution(pCamHandle, expRegion[0], expRegion[1], expRegion[2], expRegion[3]);
    if (QHYCCD_SUCCESS != retVal)
        return 3;       // error setting the camera's resolution

    retVal = SetQHYCCDBinMode(pCamHandle, binMode[0], binMode[1]);
    if (QHYCCD_SUCCESS != retVal)
        return 4;       // error setting the camera's bin mode

    // check and set bit resolution
    retVal = IsQHYCCDControlAvailable(pCamHandle, CONTROL_TRANSFERBIT);
    if (QHYCCD_SUCCESS != retVal)
        return 5;       // error checking the camera's bit resolution
    retVal = SetQHYCCDBitsMode(pCamHandle, bpp);
    if (QHYCCD_SUCCESS != retVal)
        return 6;       // error setting the camera's bit resolution

    // check and set gain
    retVal = IsQHYCCDControlAvailable(pCamHandle, CONTROL_GAIN);
    if (retVal != QHYCCD_SUCCESS)
        return 7;       // error checking the camera's gain
    retVal = SetQHYCCDParam(pCamHandle, CONTROL_GAIN, settings[0]);
    if (QHYCCD_SUCCESS != retVal)
        getchar();
        return 8;       // error setting the camera's gain

    // check and set offset
    retVal = IsQHYCCDControlAvailable(pCamHandle, CONTROL_OFFSET);
    if (QHYCCD_SUCCESS != retVal)
        return 9;       // error checking the camera's offset
    retVal = SetQHYCCDParam(pCamHandle, CONTROL_OFFSET, settings[1]);
    if (QHYCCD_SUCCESS != retVal)
        getchar();
        return 10;      // error setting the camera's offset

    // set exposure time
    retVal = SetQHYCCDParam(pCamHandle, CONTROL_EXPOSURE, settings[2]);
    if (QHYCCD_SUCCESS != retVal)
        getchar();
        return 11;      // error setting the camera's exposure time


    // single frame
    printf("ExpQHYCCDSingleFrame(pCamHandle) - start...\n");
    retVal = ExpQHYCCDSingleFrame(pCamHandle);
    printf("ExpQHYCCDSingleFrame(pCamHandle) - end...\n");
    if (retVal == QHYCCD_ERROR){
        return 12;      // error exposing the camera's single frame
    }else if (retVal != QHYCCD_READ_DIRECTLY){
        sleep(1);
    }

    // get single frame
    unsigned int channels = 1;
    retVal = GetQHYCCDSingleFrame(pCamHandle, &expRegion[2], &expRegion[3], &bpp, &channels, pImgData);
    if (QHYCCD_SUCCESS != retVal)
        return 13;      // error getting the camera's single frame

    return 0;
}

