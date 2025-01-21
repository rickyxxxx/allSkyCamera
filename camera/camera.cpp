#include "qhyccd.h"

const char *VERSION = "0.1.0";

#define SUCCESS 0U
#define QHYCCD_INIT_ERROR 1U
#define NO_CAMERA_FOUND 2U
#define TOO_MANY_CAMERA 3U
#define CONNECTION_FAILED 4U
#define ERROR_SETTING_READ_MODE 5U
#define ERROR_SETTING_STREAM_MODE 6U
#define CAMERA_INIT_ERROR 7U
#define ERROR_GETTING_CHIP_INFO 8U
#define ERROR_SETTING_BIN_MODE 9U
#define ERROR_SETTING_OFFSET 10U
#define ERROR_SETTING_USB_TRAFFIC 11U
#define CONTROL_NOT_AVAILABLE 12U
#define ERROR_SETTING_CCD_BIT_DEPTH 13U
#define ERROR_SETTING_TRANSFER_BIT_DEPTH 14U
#define ERROR_SETTING_REGION_OF_INTEREST 15U
#define ERROR_SETTING_GAIN 16U
#define ERROR_SETTING_EXPOSURE_TIME 17U
#define ERROR_START_LIVE_STREAM 18U
#define ERROR_STOP_LIVE_STREAM 19U
#define FAILED_TO_EXPOSE 20U


extern "C"{
    unsigned int getCameraId(char *);
    qhyccd_handle* getCameraHandle(char *);
    unsigned int getChipInfo(qhyccd_handle *, unsigned int *, double *);
    unsigned int configContinuousMode(qhyccd_handle *);
    unsigned int setBitDepth(qhyccd_handle *, uint32_t);
    unsigned int setROI(qhyccd_handle *, unsigned int *);
    unsigned int setGain(qhyccd_handle *, int);
    unsigned int setExposureTime(qhyccd_handle *, int);
    unsigned int beginLiveStream(qhyccd_handle *);
    unsigned int endLiveStream(qhyccd_handle *);
    unsigned int expose(qhyccd_handle *, unsigned char *, uint32_t, unsigned int *);
    void close(qhyccd_handle *);
}


unsigned int getCameraId(char *camId){

    unsigned int ret = InitQHYCCDResource();
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

unsigned int getChipInfo(qhyccd_handle *pCam, unsigned int *scanInfo, double *chipInfo) {
    // get chip info
    unsigned int ret = GetQHYCCDChipInfo(pCam, &chipInfo[0], &chipInfo[1], &scanInfo[0], &scanInfo[1],
                                         &chipInfo[2], &chipInfo[3], &scanInfo[2]);
    if (ret != QHYCCD_SUCCESS)
        return ERROR_GETTING_CHIP_INFO;

    return SUCCESS;
}

unsigned int useDefaultSettings(qhyccd_handle *pCam){
    // default settings those will not be changed in any configurations
    unsigned int ret = SetQHYCCDBinMode(pCam, 1, 1);
    if (ret != QHYCCD_SUCCESS)
        return ERROR_SETTING_BIN_MODE;

    ret = SetQHYCCDParam(pCam, CONTROL_OFFSET, 0.0);
    if (ret != QHYCCD_SUCCESS)
        return ERROR_SETTING_OFFSET;

    // set USB traffic mode to maximum speed: 0.0
    ret = SetQHYCCDParam(pCam, CONTROL_USBTRAFFIC, 0.0);
    if (ret != QHYCCD_SUCCESS)
        return ERROR_SETTING_USB_TRAFFIC;

    return SUCCESS;
}

unsigned int configContinuousMode(qhyccd_handle *pCam){
    unsigned int ret = SetQHYCCDReadMode(pCam, 0);
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

unsigned int setBitDepth(qhyccd_handle *pCam, uint32_t bpp) {
    unsigned int ret = IsQHYCCDControlAvailable(pCam, CONTROL_TRANSFERBIT);
    if (ret != QHYCCD_SUCCESS)
        return CONTROL_NOT_AVAILABLE;

    // bit depth read by the CCD
    ret = SetQHYCCDBitsMode(pCam, bpp);
    if (ret != QHYCCD_SUCCESS)
        return ERROR_SETTING_CCD_BIT_DEPTH;

    // bit depth used in data transfer
    ret = SetQHYCCDParam(pCam, CONTROL_TRANSFERBIT, (float) bpp);
    if (ret != QHYCCD_SUCCESS)
        return ERROR_SETTING_TRANSFER_BIT_DEPTH;

    return SUCCESS;
}

unsigned int setROI(qhyccd_handle *pCam, unsigned int *expRegion){
    unsigned int ret = SetQHYCCDResolution(pCam, expRegion[0], expRegion[1], expRegion[2], expRegion[3]);
    return ret == QHYCCD_SUCCESS ? SUCCESS : ERROR_SETTING_REGION_OF_INTEREST;

}

unsigned int setGain(qhyccd_handle *pCam, int gain) {
    unsigned int ret = IsQHYCCDControlAvailable(pCam, CONTROL_GAIN);
    if (ret != QHYCCD_SUCCESS)
        return CONTROL_NOT_AVAILABLE;

    ret = SetQHYCCDParam(pCam, CONTROL_GAIN, gain);
    if (ret != QHYCCD_SUCCESS)
        return ERROR_SETTING_GAIN;

    return SUCCESS;
}

unsigned int setExposureTime(qhyccd_handle *pCam, int exposureTime) {
    unsigned int ret = SetQHYCCDParam(pCam, CONTROL_EXPOSURE, exposureTime);
    if (ret != QHYCCD_SUCCESS)
        return ERROR_SETTING_EXPOSURE_TIME;

    return SUCCESS;
}

unsigned int beginLiveStream(qhyccd_handle *pCam){
    unsigned int ret = BeginQHYCCDLive(pCam);
    if (ret != QHYCCD_SUCCESS)
        return ERROR_START_LIVE_STREAM;

    return SUCCESS;
}

unsigned int endLiveStream(qhyccd_handle *pCam){
    unsigned int ret = StopQHYCCDLive(pCam);
    if (ret != QHYCCD_SUCCESS)
        return ERROR_STOP_LIVE_STREAM;

    return SUCCESS;
}

unsigned int expose(qhyccd_handle *pCam, unsigned char *pImg, uint32_t bpp, unsigned int *expRegion) {
    // for now, this drive only supports monochromatic cameras
    unsigned int channel = 1;

    unsigned int ret = GetQHYCCDLiveFrame(pCam, &expRegion[2], &expRegion[3], &bpp, &channel, pImg);
    if (ret != QHYCCD_SUCCESS)
        return FAILED_TO_EXPOSE;

    return SUCCESS;
}

void close(qhyccd_handle *pCam){
    StopQHYCCDLive(pCam);
    CloseQHYCCD(pCam);
    ReleaseQHYCCDResource();
}