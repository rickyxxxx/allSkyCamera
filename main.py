from astropy.io import fits
import io

import requests
from camera.camera import Camera
from threading import Thread
from time import sleep
from PIL import Image
import datetime

import time
import board
import adafruit_ahtx0
from datetime import datetime, time, timedelta

from astral import LocationInfo
from astral.sun import sun
from typing import Callable


domain = "http://camserver.physics.ucsb.edu"
settings = {}


def get_camera_settings():
    global settings
    response = requests.get(f"{domain}/get_setting/1")
    if response.status_code == 200:
        response_json = response.json()
        settings = {k: float(v) for (k, v) in response_json.items()}


def update_setting():
    while True:
        try:
            get_camera_settings()
        # print(f"settings: {settings}")
            sleep(1)
        except Exception:
            pass


def upload_image(image_buffer, image_name, type='image/jpg', ts="ts", gain=0, exp=0):
    files = {
        "file": (image_name, image_buffer, type)  # Include filename and MIME type
    }
    startt, endt = gss()
    startt = startt.replace(tzinfo=None)
    endt = endt.replace(tzinfo=None)# now aware
    nowtime = datetime.now() + tdelta(hours=7)
    nts = nowtime.strftime("%Y-%m-%dT%H:%M:%S.%f")
    try:
        a, b = nts.split(".")
        b = b[:3]
        nts = a + "." + b
    except Exception:
        pass

    isDaytime = "1" if startt <= datetime.now() <= endt else "0"
    form = {
        "id": cam.camera_id,
        "name": "UCSB Broida Roof - Color",
        "date": nts,
        "bit": 16,
        "gain": gain,
        "exp": exp,
        "lng": -119.8610,
        "lat": 34.4133,
        "temp": aht.get_temperature(),
        "hum": aht.get_humidity(),
        "tz": "America/Los_Angeles",
        "isDay": isDaytime,
    }
    try:
        response = requests.post(f"{domain}/upload_image", files=files, data=form)
    except Exception:
        pass

    try:
        response_json = response.json()
    except Exception:
        # Handle JSON parsing errors here
        pass


def is_night():
    now = datetime.now().time()
    start_time = time(17, 0)  # 5 PM
    end_time = time(7, 0)     # 7 AM

    if start_time <= now or now <= end_time:
        return True
    return False


class AHT20:
    def __init__(self):
        i2c = board.I2C()  # uses board.SCL and board.SDA
        self.sensor = adafruit_ahtx0.AHTx0(i2c)

    def get_temperature(self):
        return self.sensor.temperature

    def get_humidity(self):
        return self.sensor.relative_humidity


def ns():
    while True:
        try:
            tstamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]

            form = {
                "id": cam.camera_id,
                "date": tstamp,
                "temp": aht.get_temperature(),
                "humidity": aht.get_humidity()
            }

            sleep(60)
            response = requests.post(f"{domain}/upload_data", data=form)
        except Exception:
            pass

def get_gain(get_sunrise_sunset: Callable):
    sunrise, sunset = get_sunrise_sunset()

    right_now = datetime.now().time()

    sunrise_start = (sunrise - timedelta(hours=1)).time()
    sunset_end = (sunset + timedelta(hours=1)).time()

    if sunrise_start <= right_now <= sunset_end:
        return 1
    return 60


def init_sun_rise_set_calculator() -> Callable:
    latitude = 34.4133
    longitude = -119.8610
    location = LocationInfo(latitude=latitude, longitude=longitude)

    def get_sunrise_sunset() -> tuple[datetime, datetime]:
        s = sun(location.observer, date=datetime.now())

        sunrise = s['sunrise'].astimezone()
        sunset = s['sunset'].astimezone()

        return sunrise, sunset

    return get_sunrise_sunset


def get_exp_time(cam, exp_now, target_sum, gain, roi):
    exp_list = [exp_now * (1 + 0.05 * i) for i in range(5)]
    pix_sum = []
    for exp_ in exp_list:
        img, _ = cam.expose(int(exp_), gain=gain, bbp=16, roi=roi)
        pix_sum.append(np.sum(img.flatten()))

    a, b = np.polyfit(exp_list, pix_sum, 1)
    print(a, b)
    exp_setting = (target_sum - b) / a
    return int(exp_setting)

'''
def get_gain(cam, gain_now, target_sum, expNow, roi):
    gain_list = [gain_now + i for i in range(5)]
    pix_sum = []
    for gain_ in gain_list:
        img, _ = cam.expose(expNow, gain=gain_, bbp=16, roi=roi)
        pix_sum.append(np.sum(img.flatten()))

    a, b = np.polyfit(gain_list, pix_sum, 1)
    print(a, b)
    gain_setting = (target_sum - b) / a
    return int(gain_setting)
'''


def auto_exp(cam, exp_now, target_sum, gain, roi):
    exp_est = get_exp_time(cam, exp_now, target_sum, gain, roi)

    # if exp_est > 25_000_000:
    #     exp_est = 25_000_000
    if exp_est > 40_000_000:
        return 40_000_000
    if exp_est < 100:
        exp_est = 100

    test_img, _ = cam.expose(exp_est, gain=gain, bbp=16, roi=roi)
    pixsum = np.sum(test_img.flatten())

    ctr = 0
    while not 150 * base <= pixsum <= 250 * base:
        exp_est = get_exp_time(cam, exp_est, target_sum, gain, roi)
        # test_img, _ = cam.expose(exp_est, gain=gain, bbp=16, roi=roi)
        # pixsum = np.sum(test_img.flatten())

        # if exp_est > 25_000_000:
        #     exp_est = 25_000_000
        #     ctr += 1
        if exp_est >= 40_000_000:
            exp_est = 40_000_000
            ctr += 1
        if exp_est < 100:
            exp_est = 100
            ctr += 1
        if ctr == 2:
            return exp_est
        test_img, _ = cam.expose(exp_est, gain=gain, bbp=16, roi=roi)
        pixsum = np.sum(test_img.flatten())

    return exp_est

'''
def auto_gain(cam, exp_now, target_sum, gain, roi):
    exp_est = get_gain(cam, gain, target_sum, exp_now, roi)

    if exp_est > 40_000_000:
        exp_est = 40_000_000
    if exp_est > 150:
        return 150
    if exp_est < 1:
        exp_est = 1

    test_img, _ = cam.expose(exp_now, gain=exp_est, bbp=16, roi=roi)
    pixsum = np.sum(test_img.flatten())

    ctr = 0
    while not 150 * base <= pixsum <= 250 * base:
        exp_est = get_gain(cam, gain, target_sum, exp_now, roi)
        # test_img, _ = cam.expose(exp_est, gain=gain, bbp=16, roi=roi)
        # pixsum = np.sum(test_img.flatten())

        # if exp_est > 25_000_000:
        #     exp_est = 25_000_000
        #     ctr += 1
        if exp_est >= 150:
            exp_est = 150
            ctr += 1
        if exp_est < 1:
            exp_est = 1
            ctr += 1
        if ctr == 2:
            return exp_est
        test_img, _ = cam.expose(exp_now, gain=exp_est, bbp=16, roi=roi)
        pixsum = np.sum(test_img.flatten())

    return exp_est
'''

if __name__ == "__main__":
    from io import BytesIO
    from time import time as tt    
    import os
    import numpy as np
    from datetime import timedelta as tdelta
    cam = Camera()
    gss = init_sun_rise_set_calculator()
    tw = 2500
    roi = ((3856 - tw) / 2, 0), (tw, 2180)
    gain = get_gain(gss)



    #    buf = BytesIO()
    try:
        aht = AHT20()
        cam.config_single_mode()

        # st2 = Thread(target=ns)
        # st2.start()
        starttime = tt()
        interval = 300
        id = cam.get_camera_id()

        start = tt()
        ctr = 0

        base = 1e9
        print("call auto exp")
        exp = auto_exp(cam, 250, 200 * base, gain, roi)
        print("end auto exp")
#
#        target_date_str = "12/04/2025 05:00 AM"
#        target_date_format = "%d/%m/%Y %I:%M %p"

#        end_date_str = "12/04/2025 06:00 AM"

        # Convert string to datetime
#        target_date = datetime.strptime(target_date_str, target_date_format)
#        end_date = datetime.strptime(end_date_str, target_date_format)

        while True:

#            timenow = datetime.now()

#            if timenow > target_date:
#                interval = 0
#            if timenow > end_date:
#                interval = 300

            buf = BytesIO()
            gain = get_gain(gss)

            print(gain, exp, type(gain), type(exp))
            img, _ = cam.expose(exposure_time=exp, gain=gain, roi=roi)
            pixel_sum = np.sum(img.flatten())
            print(f"pixel sum: {pixel_sum}")
            ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
            print(ts)

            image_8bit = (img / 256).astype(np.uint8)

            # Convert to PIL Image and save as JPEG
            image_name = f"{id}_{ts}.jpg"
            mode = 'RGB' if cam.is_color() else "L"
            image = Image.fromarray(image_8bit, mode=mode)
            image.save(buf, format='JPEG')
            buf.seek(0)
            # file_size = os.path.getsize(image_name)
            if pixel_sum == 0:
                print("corrupted_file")
                os.system("sudo reboot now")
            upload_image(buf, image_name, ts=ts, gain=gain, exp=exp)

            # Convert to FITS format (channel-first: 3, 512, 512)
            fits_data = np.transpose(img, (2, 0, 1))  # (channels, height, width)

            # Create FITS HDU
            hdu = fits.PrimaryHDU(fits_data)
            hdul = fits.HDUList([hdu])

            # Create a BytesIO object and write the FITS file into it
            fits_buffer = io.BytesIO()
            hdul.writeto(fits_buffer)
            fits_buffer.seek(0)
        
            upload_image(fits_buffer, image_name.replace(".jpg", ".fits"), 'image/fits', ts=ts, gain=gain, exp=exp)

            print("image_uploaded")
            buf.close()

            if not 150 * base <= pixel_sum <= 250 * base:
                exp = auto_exp(cam, 250, 200 * base, gain, roi)
                print("auto exp called")
                # if exp == 1_000_000:
                #     gain = auto_gain(cam, 250, 200 * base, gain, roi)

            while tt() - starttime < interval:
            	sleep(1)
            starttime = tt()

        # st.join()
        st2.join()
    except KeyboardInterrupt:
        pass
    finally:
        cam.close()
