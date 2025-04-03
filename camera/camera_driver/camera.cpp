#include <iostream>
#include "qhyccd.h"

const char *VERSION = "0.1.0";

#define SUCCESS 0
#define QHYCCD_INIT_ERROR 1
#define NO_CAMERA_FOUND 2
#define TOO_MANY_CAMERA 3
#define CONNECTION_FAILED 4
#define ERROR_SETTING_READ_MODE 5
#define ERROR_SETTING_STREAM_MODE 6
#define CAMERA_INIT_ERROR 7
#define ERROR_GETTING_CHIP_INFO 8
#define ERROR_SETTING_BIN_MODE 9
#define ERROR_SETTING_OFFSET 10
#define ERROR_SETTING_USB_TRAFFIC 11
#define CONTROL_NOT_AVAILABLE 12
#define ERROR_SETTING_CCD_BIT_DEPTH 13
#define ERROR_SETTING_TRANSFER_BIT_DEPTH 14
#define ERROR_SETTING_REGION_OF_INTEREST 15
#define ERROR_SETTING_GAIN 16
#define ERROR_SETTING_EXPOSURE_TIME 17
#define ERROR_START_LIVE_STREAM 18
#define ERROR_STOP_LIVE_STREAM 19
#define FAILED_TO_EXPOSE 20
#define ERROR_SETTING_DEBAYER_MODE 21


extern "C"{
    int getCameraId(char *);
    qhyccd_handle* getCameraHandle(char *);
    int getChipInfo(qhyccd_handle *, unsigned int *, double *);
    int configContinuousMode(qhyccd_handle *);
    int configSingleMode(qhyccd_handle *);
    int setBitDepth(qhyccd_handle *, uint32_t);
    int setROI(qhyccd_handle *, uint32_t *);
    int setGain(qhyccd_handle *, int);
    int setExposureTime(qhyccd_handle *, int);
    int beginLiveStream(qhyccd_handle *);
    int endLiveStream(qhyccd_handle *);
    int exposeLive(qhyccd_handle *, uint8_t *, uint32_t, uint32_t *);
    int exposeSingle(qhyccd_handle *, uint8_t *, uint32_t, uint32_t *);
    void close(qhyccd_handle *);
    int isColor(qhyccd_handle *);
    int getBayerMatrix(qhyccd_handle *);
    void readoutmode(qhyccd_handle *pCam);
    void test(qhyccd_handle *);
}
void test(qhyccd_handle *pCam){
    uint32_t ret = IsQHYCCDControlAvailable(pCam,QHYCCD_3A_AUTOFOCUS);
    if (ret == QHYCCD_SUCCESS){
	printf("not available");
    } else {
	printf("Yes");
    } 
}

int getCameraId(char *camId){

    uint32_t ret = InitQHYCCDResource();
    if (ret != QHYCCD_SUCCESS)
        return QHYCCD_INIT_ERROR;

    int camCount = ScanQHYCCD();
    if (camCount == 0)
        return NO_CAMERA_FOUND;
    if (camCount > 1)
        return TOO_MANY_CAMERA;

    // only one camera should be connected
    ret = GetQHYCCDId(0, camId);
    if (ret != QHYCCD_SUCCESS)
        return CONNECTION_FAILED;

    return SUCCESS;
}

qhyccd_handle* getCameraHandle(char *camId) {
    return OpenQHYCCD(camId);
}

int getChipInfo(qhyccd_handle *pCam, unsigned int *scanInfo, double *chipInfo) {
    //  readoutmode(pCam);
    // get chip info
    uint32_t ret = GetQHYCCDChipInfo(pCam, &chipInfo[0], &chipInfo[1], &scanInfo[0], &scanInfo[1],
                                         &chipInfo[2], &chipInfo[3], &scanInfo[2]);
    if (ret != QHYCCD_SUCCESS)
        return ERROR_GETTING_CHIP_INFO;

    return SUCCESS;
}

int useDefaultSettings(qhyccd_handle *pCam){
    // default settings those will not be changed in any configurations
    uint32_t ret = SetQHYCCDBinMode(pCam, 1, 1);
    if (ret != QHYCCD_SUCCESS)
        return ERROR_SETTING_BIN_MODE;

    ret = SetQHYCCDParam(pCam, CONTROL_OFFSET, 0.0);
    if (ret != QHYCCD_SUCCESS)
        return ERROR_SETTING_OFFSET;

    // set USB traffic mode to maximum speed: 0.0
    ret = SetQHYCCDParam(pCam, CONTROL_USBTRAFFIC, 50.0);
    if (ret != QHYCCD_SUCCESS)
        return ERROR_SETTING_USB_TRAFFIC;

    ret = IsQHYCCDControlAvailable(pCam, CAM_IS_COLOR);
    if (ret == QHYCCD_SUCCESS){     // setup for colored cameras
        ret = SetQHYCCDDebayerOnOff(pCam, true);
        if (ret != QHYCCD_SUCCESS)
            return ERROR_SETTING_DEBAYER_MODE;
    }

    return SUCCESS;
}

int configContinuousMode(qhyccd_handle *pCam){
    uint32_t ret = SetQHYCCDReadMode(pCam, 0);
    if (ret != QHYCCD_SUCCESS)
        return ERROR_SETTING_READ_MODE;

    ret = SetQHYCCDStreamMode(pCam, 1);
    if (ret != QHYCCD_SUCCESS)
        return ERROR_SETTING_STREAM_MODE;

    ret = InitQHYCCD(pCam);
    if (ret != QHYCCD_SUCCESS)
        return CAMERA_INIT_ERROR;

    return useDefaultSettings(pCam);
}

int configSingleMode(qhyccd_handle *pCam){
    uint32_t ret = SetQHYCCDReadMode(pCam, 0);
    if (ret != QHYCCD_SUCCESS)
        return ERROR_SETTING_READ_MODE;
        
    ret = SetQHYCCDStreamMode(pCam, 0);
    if (ret != QHYCCD_SUCCESS)
        return ERROR_SETTING_STREAM_MODE;
        
    ret = InitQHYCCD(pCam);
    if (ret != QHYCCD_SUCCESS)
        return CAMERA_INIT_ERROR;
        
    return useDefaultSettings(pCam);
}

int setBitDepth(qhyccd_handle *pCam, uint32_t bpp) {
//    unsigned int ret = IsQHYCCDControlAvailable(pCam, CONTROL_TRANSFERBIT);
//    if (ret != QHYCCD_SUCCESS)
//        return CONTROL_NOT_AVAILABLE;

    // bit depth read by the CCD
    uint32_t ret = SetQHYCCDBitsMode(pCam, bpp);
    if (ret != QHYCCD_SUCCESS)
        return ERROR_SETTING_CCD_BIT_DEPTH;

    // bit depth used in data transfer
    ret = SetQHYCCDParam(pCam, CONTROL_TRANSFERBIT, (double) bpp);
    if (ret != QHYCCD_SUCCESS)
        return ERROR_SETTING_TRANSFER_BIT_DEPTH;

    return SUCCESS;
}

int setROI(qhyccd_handle *pCam, uint32_t *expRegion){
    unsigned int ret = SetQHYCCDResolution(pCam, expRegion[0], expRegion[1], expRegion[2], expRegion[3]);
    return ret == QHYCCD_SUCCESS ? SUCCESS : ERROR_SETTING_REGION_OF_INTEREST;
}

int setGain(qhyccd_handle *pCam, int gain) {
    uint32_t ret = SetQHYCCDParam(pCam, CONTROL_GAIN, (double) gain);
    
    if (ret != QHYCCD_SUCCESS)
        return ERROR_SETTING_GAIN;

    return SUCCESS;
}


int setExposureTime(qhyccd_handle *pCam, int exposureTime) {
    uint32_t ret = SetQHYCCDParam(pCam, CONTROL_EXPOSURE, (double) exposureTime);

    if (ret != QHYCCD_SUCCESS)
        return ERROR_SETTING_EXPOSURE_TIME;

    return SUCCESS;
}

int beginLiveStream(qhyccd_handle *pCam){
    uint32_t ret = BeginQHYCCDLive(pCam);
    if (ret != QHYCCD_SUCCESS)
        return ERROR_START_LIVE_STREAM;

    return SUCCESS;
}

int endLiveStream(qhyccd_handle *pCam){
    uint32_t ret = StopQHYCCDLive(pCam);
    if (ret != QHYCCD_SUCCESS)
        return ERROR_STOP_LIVE_STREAM;

    return SUCCESS;
}

int exposeLive(qhyccd_handle *pCam, uint8_t *pImg, uint32_t bpp, uint32_t *expRegion) {
    // for now, this drive only supports monochromatic cameras
    uint32_t channel = 1;

    uint32_t ret = QHYCCD_ERROR;

    int ctr = 0;
    while(ret != QHYCCD_SUCCESS){
        ret = GetQHYCCDLiveFrame(pCam, &expRegion[2], &expRegion[3], &bpp, &channel, pImg);

        if (ctr++ > 1000)
            return FAILED_TO_EXPOSE;
    }


    return SUCCESS;
}

int exposeSingle(qhyccd_handle *pCam, uint8_t *pImg, uint32_t bpp, uint32_t *expRegion) {
    uint32_t channel = 1;
    
    uint32_t ret = ExpQHYCCDSingleFrame(pCam);
    ret = GetQHYCCDSingleFrame(pCam, &expRegion[2], &expRegion[3], &bpp, &channel, pImg);
    
    return SUCCESS;
}

//void startBurstMode(qhyccd_handle *pCam){
//    uint32_t w = 100;
//    uint32_t h = 100;
//    uint32_t bpp = 8;
//    uint32_t channel = 1;
//    uint8_t *imgData = (uint8_t)malloc(GetQHYCCDMemLength(pCam));
//    beginLiveStream(pCam);
//    for (int i = 0; i < 2; ++i)
//        GetQHYCCDLiveFrame(pCam, &w, &h, &bpp, &channel, imgData);
    
//    uint32_t ret = EnableQHYCCDBurstMode(pCam, true);
//    ret = SetQHYCCDBurstModeStartEnd(pCam, start, end);
//    ret = SetQHYCCDBurstModePatchNumber(pCam, 32001);      
//}

void close(qhyccd_handle *pCam){
    StopQHYCCDLive(pCam);
    CloseQHYCCD(pCam);
    ReleaseQHYCCDResource();
}

void readoutmode(qhyccd_handle *pCam){
    uint32_t ret = QHYCCD_ERROR;
    uint32_t numberOfMode;
    ret = GetQHYCCDNumberOfReadModes(pCam, &numberOfMode);
    if (ret == QHYCCD_SUCCESS){
        printf("Number of Readout Modes: %d\n", numberOfMode);
    } else {
        return;
    }

    char name[80] = {0};
    for (int i = 0; i < numberOfMode; ++i){
        ret = GetQHYCCDReadModeName(pCam, i, name);
        printf("Current Read Mode (%d) is %s\n", i, name);
    }
}

int isColor(qhyccd_handle *pCam){
    uint32_t ret = IsQHYCCDControlAvailable(pCam, CAM_IS_COLOR);
    return ret == QHYCCD_SUCCESS ? 1 : 0;
}

int getBayerMatrix(qhyccd_handle *pCam){
    return IsQHYCCDControlAvailable(pCam, CAM_COLOR);
}
