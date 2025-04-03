import serial
import serial.tools.list_ports as lp
from time import time, sleep
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional

from timezonefinder import TimezoneFinder
from micropyGPS import MicropyGPS as GPSDecoder


Coord = list[int, float, str]


class GTU7:
    def __init__(self, refresh_interval=2, timeout=20000) -> None:
        device = self.__get_device()

        self.timeout = timeout
        self.refresh_interval = refresh_interval

        self.last_read_time = time()
        self.gps_decoder = GPSDecoder()
        self.timezone_finder = TimezoneFinder()
        self.ser = serial.Serial(device, 9600, timeout=1)

        self.ser.readline()     # Skip the first line
        self.__wait_for_connection()

    @staticmethod
    def __get_device() -> str:
        # search for the GPS device
        ports = serial.tools.list_ports.comports()
        for port in ports:
            if "GPS" not in port.description:
                continue
            return port.device
        raise RuntimeError("No GPS device found")

    def update(self) -> None:
        # update the GPS data from the device
        sentence = self.ser.readline().decode("utf-8")

        for word in sentence:
            self.gps_decoder.update(word)

        self.last_read_time = time()

    def __wait_for_connection(self) -> None:
        sat_in_use = 0      # need a minimum of 4 satellites to get a correct location
        for i in range(self.timeout):
            self.update()
            print(self.gps_decoder.satellites_in_use, self.gps_decoder.satellites_in_view)
            sat_in_use = self.gps_decoder.satellites_in_use
            if sat_in_use >= 4:
                return
            sleep(0.5)

        # timeout reached
        if sat_in_use:
            raise TimeoutError(f"Not enough satellites: {sat_in_use} were in use "
                               f"but a minimum of 4 are required.")
        else:
            raise TimeoutError("No satellites were connected")

    def get_location(self) -> Optional[tuple[Coord, Coord]]:
        if time() - self.last_read_time > self.refresh_interval:
            self.update()
        gps = self.gps_decoder

        latitude = gps.latitude
        longitude = gps.longitude

        if not (1 <= gps.hdop < 50 and 1 <= gps.vdop < 50 and 1 <= gps.pdop < 50):
            return None     # if the uncertainty is too high or too low, reject the data

        return latitude, longitude

    def get_location_str(self) -> str:
        coord = self.get_location()
        if coord is None:
            return "Location Not Available"
        lat, lng = coord
        lat_min = int(lat[1])
        lat_sec = (lat[1] - lat_min) * 60
        lng_min = int(lng[1])
        lng_sec = (lng[1] - lng_min) * 60
        return f"{lat[0]}°{lat_min}'{lat_sec:.2f}\"{lat[2]}  {lng[0]}°{lng_min}'{lng_sec:.2f}\"{lng[2]}"

    def get_timezone(self) -> Optional[str]:
        ctr = 0
        while (coord := self.get_location()) is None:
            if ctr >= self.timeout:
                return
            ctr += 1
        lat, lng = coord
        lat = (lat[0] + lat[1] / 60) * (-1 if lat[2] == "S" else 1)
        lng = (lng[0] + lng[1] / 60) * (-1 if lng[2] == "W" else 1)
        return self.timezone_finder.timezone_at(lng=lng, lat=lat)

    def get_datetime(self) -> str:
        dt = datetime.now()
        if timezone := self.get_timezone():
            dt = dt.astimezone(ZoneInfo(timezone))
        return str(dt)

    def close(self) -> None:
        if self.ser is None:
            return
        self.ser.close()


if __name__ == "__main__":
    from time import sleep
    gt_u7 = GTU7()
    while True:
        try:
            print(gt_u7.get_location_str())
            print(gt_u7.get_datetime())
            print()
            sleep(2)
        except KeyboardInterrupt:
            gt_u7.close()

