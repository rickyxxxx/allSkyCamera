//
// Created by ricky on 9/11/2024.
//
#include <string.h>
#include "qhyccd.h"

// functions that are to be called from Python
extern "C" {
    unsigned char* SDKVersion();
}

unsigned char* SDKVersion() {
    unsigned int YMDS[4];
    unsigned char sVersion[80];

    memset(sVersion, 0x00, sizeof(sVersion));
    GetQHYCCDSDKVersion(&YMDS[0], &YMDS[1], &YMDS[2], &YMDS[3]);

    if ((YMDS[1] < 10) && (YMDS[2] < 10)) {
        sprintf((char *)sVersion, "V20%d0%d0%d_%d\n", YMDS[0], YMDS[1], YMDS[2], YMDS[3]);
    } else if ((YMDS[1] < 10) && (YMDS[2] >= 10)) {
        sprintf((char *)sVersion, "V20%d0%d%d_%d\n", YMDS[0], YMDS[1], YMDS[2], YMDS[3]);
    } else if ((YMDS[1] >= 10) && (YMDS[2] < 10)) {
        sprintf((char *)sVersion, "V20%d%d0%d_%d\n", YMDS[0], YMDS[1], YMDS[2], YMDS[3]);
    } else {
        sprintf((char *)sVersion, "V20%d%d%d_%d\n", YMDS[0], YMDS[1], YMDS[2], YMDS[3]);
    }

    return sVersion;
}
