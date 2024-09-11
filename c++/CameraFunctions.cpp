//
// Created by ricky on 9/11/2024.
//
#include <string.h>
#include "qhyccd.h"

// functions that are to be called from Python
extern "C" {
    void SDKVersion(unsigned int*);
}

void SDKVersion(unsigned int* version) {
    GetQHYCCDSDKVersion(&version[0], &version[1], &version[2], &version[3]);
}
