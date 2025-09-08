import threading
import serial
import serial.tools.list_ports as lp
from time import sleep
from typing import Optional

from micropyGPS import MicropyGPS as GPSDecoder


class GTU7:
    def __init__(self) -> None:
        self.status = "initializing gps device..."

        if (device := self.__get_device()) is None:
            return      # abort gps initialization if not connected

        self._gps_decoder = GPSDecoder()

        self._ser = serial.Serial(device, 9600, timeout=1)
        self._ser.readline()     # Skip the first line

        self._terminate = threading.Event()
        self._t = threading.Thread(target=self.main_loop)
        self._t.start()

        # self.timezone_finder = TimezoneFinder()

    def __get_device(self) -> Optional[str]:
        # establish serial connection between raspberry pi and the GPS module
        ports = serial.tools.list_ports.comports()
        for port in ports:
            if "GPS" not in port.description:
                continue
            self.status = "GPS device initialized"
            return port.device
        self.status = "GPS device not available!"

    def __connect_device(self) -> None:
        # connect to satellites for GPS readings
        while not self._terminate.is_set():
            self.update()
            # satellites currently in use, need 4 to get location
            if self._gps_decoder.satellites_in_use >= 4:
                return
            self.status = f"Searching for GPS signals; Satellites in view/used: {self.sat_in_view}/{self.sat_in_use}"
            sleep(1)

    @property
    def sat_in_view(self) -> str:
        return self._gps_decoder.satellites_in_view

    @property
    def sat_in_use(self) -> str:
        return self._gps_decoder.satellites_in_use

    def update(self) -> None:
        # update the GPS data from the device
        sentence = self._ser.readline().decode("utf-8")

        for word in sentence:
            self._gps_decoder.update(word)

    def update_location(self) -> None:
        gps = self._gps_decoder

        if not (1 <= gps.hdop < 50 and 1 <= gps.vdop < 50 and 1 <= gps.pdop < 50):
            return      # discard result if uncertainty is too high or too low

        lat, lng = gps.latitude, gps.longitude      # dtype: list(int, float, str)
        lat_m, lng_m = int(lat[1]), int(lng[1])
        lat_s, lng_s = (lat[1] - lat_m) * 60, (lng[1] - lng_m) * 60

        self.status = f"{lat[0]}°{lat_m}'{lat_s:.2f}\"{lat[2]} {lng[0]}°{lng_m}'{lng_s:.2f}\"{lng[2]}"

    def main_loop(self) -> None:
        self.__connect_device()

        while not self._terminate.is_set():
            self.update()
            self.update_location()
            sleep(300)

    def close(self) -> None:
        self._terminate.set()
        self._t.join()
        if self._ser is None:
            return
        self._ser.close()

    # def get_timezone(self) -> Optional[str]:
    #     ctr = 0
    #     while (coord := self.get_location()) is None:
    #         if ctr >= self.timeout:
    #             return
    #         ctr += 1
    #     lat, lng = coord
    #     lat = (lat[0] + lat[1] / 60) * (-1 if lat[2] == "S" else 1)
    #     lng = (lng[0] + lng[1] / 60) * (-1 if lng[2] == "W" else 1)
    #     return self.timezone_finder.timezone_at(lng=lng, lat=lat)
    #
    # def get_datetime(self) -> str:
    #     dt = datetime.now()
    #     if timezone := self.get_timezone():
    #         dt = dt.astimezone(ZoneInfo(timezone))
    #     return str(dt)


if __name__ == "__main__":
    gt_u7 = GTU7()
    while True:
        print(f'\r{gt_u7.status}', end='')
        sleep(0.5)
