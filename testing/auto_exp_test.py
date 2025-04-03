# from camera.gps_driver.GTU7 import GTU7
#
# gps = GTU7()
# loc = gps.get_location()
# print(loc)

from astral import LocationInfo
from astral.sun import sun
from datetime import datetime, timedelta
from typing import Callable


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


gss = init_sun_rise_set_calculator()
rises, sets = gss()

s = get_settings(gss)
print(s)


