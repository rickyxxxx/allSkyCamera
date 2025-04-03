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


def upload_image(image_buffer, image_name, type='image/jpg'):
    files = {
        "file": (image_name, image_buffer, type)  # Include filename and MIME type
    }
    form = {
        "camId": "pi",
        "datetime": "null",
        "location_lat": "null",
        "location_lng": "u"
    }
    response = requests.post(f"{domain}/upload_image", files=files, data=form)

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
            tstamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            form = {
                "msg": f"{tstamp},{aht.get_temperature()},{aht.get_humidity()}"
            }
            print(form["msg"])
            sleep(300)
            response = requests.post(f"{domain}/upload_data", data="form")
        except Exception:
            pass

def get_settings(get_sunrise_sunset: Callable) -> tuple[float, float]:
    sunrise, sunset = get_sunrise_sunset()

    today = datetime.now()
    right_now = datetime.now().time()

    sunrise_start = (sunrise - timedelta(hours=1)).time()
    sunrise_end = (sunrise + timedelta(hours=1)).time()

    if sunrise_start < right_now <= sunrise_end:
        # Convert time objects to datetime objects using today's date
        right_now_dt = datetime.combine(today, right_now)
        sunrise_start_dt = datetime.combine(today, sunrise_start)

        # Now subtract them
        difference = right_now_dt - sunrise_start_dt
        percent = difference / timedelta(hours=2)

        gain = 60 - (60 - 1) * percent
        exp = 10_000 - (10_000 - 0.25) * percent

        return gain, exp

    sunset_start = (sunset - timedelta(hours=1)).time()
    sunset_end = (sunset + timedelta(hours=1)).time()

    if sunrise_end < right_now <= sunset_start:
        return 1, 0.25

    if sunset_start < right_now <= sunset_end:
        # Convert time objects to datetime objects using today's date
        right_now_dt = datetime.combine(today, right_now)
        sunset_start_dt = datetime.combine(today, sunset_start)

        # Now subtract them
        difference = right_now_dt - sunset_start_dt
        percent = difference / timedelta(hours=2)

        gain = 1 + (60 - 1) * percent
        exp = 0.25 + (10_000 - 0.25) * percent

        return gain, exp

    return 60, 10_000


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


if __name__ == "__main__":
    from io import BytesIO
    from time import time as tt    
    import os
    import numpy as np
    cam = Camera()
    gss = init_sun_rise_set_calculator()
#    buf = BytesIO()
    try:
        aht = AHT20()
        cam.config_single_mode()
        st = Thread(target=update_setting)
        st.start()
        st2 = Thread(target=ns)
        st2.start()
        starttime = tt()

        id = cam.get_camera_id()
        while not settings:
            pass
        while True:
               
            buf = BytesIO()
            prefix = "night" if is_night() else "day"
            gain, exp = get_settings(gss)
            gain = int(gain)
            exp = int(exp * 1000)
            # gain = int(settings[f"{prefix}_gain"])
            interval = float(settings[f"{prefix}_int"])
            # exp = int(settings[f"{prefix}_exp"] * 1000)
            print(gain, exp, type(gain), type(exp))
            img, _ = cam.expose(exposure_time=exp, gain=gain)
            pixel_sum = np.sum(img.flatten())
            print(f"pixel sum: {pixel_sum}")
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            image_8bit = (img / 256).astype(np.uint8)

            # Convert to PIL Image and save as JPEG
            image_name = f"{id}_{ts}_{exp}_{gain}.jpg"
            image = Image.fromarray(image_8bit, mode='RGB')
            image.save(buf, format='JPEG')
            buf.seek(0)
            # file_size = os.path.getsize(image_name)
            if pixel_sum == 0:
                print("corrupted_file")
                os.system("sudo reboot now")
            upload_image(buf, image_name)

            # Convert to FITS format (channel-first: 3, 512, 512)
            fits_data = np.transpose(img, (2, 0, 1))  # (channels, height, width)

            # Create FITS HDU
            hdu = fits.PrimaryHDU(fits_data)
            hdul = fits.HDUList([hdu])

            # Create a BytesIO object and write the FITS file into it
            fits_buffer = io.BytesIO()
            hdul.writeto(fits_buffer)
            fits_buffer.seek(0)
        
            upload_image(fits_buffer, image_name.replace(".jpg", ".fits"), 'image/fits')

            print("image_uploaded")
            buf.close()
            while tt() - starttime < float(settings[f"{prefix}_int"]):
            	sleep(1)
            starttime = tt()

        st.join()
        st2.join()
    except KeyboardInterrupt:
        pass
    finally:
        cam.close()
