//
// Created by ricky on 9/11/2024.
//
#include <string.h>
#include "qhyccd.h"

// functions that are to be called from Python
extern "C" {
    unsigned int* SDKVersion();
}

unsigned int* SDKVersion() {
    unsigned int YMDS[4];
    GetQHYCCDSDKVersion(&YMDS[0], &YMDS[1], &YMDS[2], &YMDS[3]);
    return YMDS;
}
