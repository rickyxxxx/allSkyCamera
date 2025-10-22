import threading
import logging
from time import sleep, time
from typing import Optional

import serial
import serial.tools.list_ports as lp

from micropyGPS import MicropyGPS as GPSDecoder


class GTU7:
    """
    GTU7 GPS Device Controller

    This class manages communication with a GTU7 GPS module over a serial interface.
    It automatically detects the GPS device, starts a background thread to
    continuously update position and status, and provides readable status strings.
    """

    def __init__(self, refresh_interval: int = 300, timeout=60) -> None:
        self.logger = logging.getLogger(__name__)

        self.__refresh_interval = refresh_interval
        self.__timeout = timeout
        self.__is_running = True
        self.__status = "initializing gps device..."

        self.__ser: Optional[serial.Serial] = None
        self.__gps_decoder: Optional[GPSDecoder] = None

        self.__terminate = threading.Event()
        self.__t: Optional[threading.Thread] = None

    def __get_device(self) -> Optional[str]:
        # establish serial connection between raspberry pi and the GPS module
        ports = serial.tools.list_ports.comports()
        for port in ports:
            if "gps" not in port.description.lower():
                continue

            # found GPS device
            self.__status = "GPS device initialized"
            self.logger.info(f"GPS device found at {port.device}")
            return port.device

        self.__status = "GPS device not available!"

    def __connect_device(self) -> None:
        """
        Connect to the GPS device
        This function will not exit until a valid GPS signal is found.
        """
        start_time = time()
        while not self.__terminate.is_set():
            self.__update()
            # satellites currently in use, need 4 to get location
            if self.__gps_decoder.satellites_in_use >= 4:
                return

            sat_in_view = self.__gps_decoder.satellites_in_view
            sat_in_use = self.__gps_decoder.satellites_in_use
            self.__status = f"Searching for GPS signals; Satellites in view/used: {sat_in_view}/{sat_in_use}"
            sleep(1)
            if time() - start_time > self.__timeout:
                self.__status = "GPS connection timeout!"
                self.logger.error(f"GPS connection timeout! -  Could not get a valid GPS signal."
                                  f"\n{sat_in_view} satellites in view, {sat_in_use} satellites in use.")
                self.__is_running = False
                return

    def __update(self) -> None:
        # update the GPS data from the device
        sentence = self.__ser.readline().decode("utf-8")

        for word in sentence:
            self.__gps_decoder.update(word)

    def __update_location(self) -> None:
        gps = self.__gps_decoder

        if not (1 <= gps.hdop < 50 and 1 <= gps.vdop < 50 and 1 <= gps.pdop < 50):
            return      # discard result if uncertainty is too high or too low

        lat, lng = gps.latitude, gps.longitude      # dtype: list(int, float, str)
        lat_m, lng_m = int(lat[1]), int(lng[1])
        lat_s, lng_s = (lat[1] - lat_m) * 60, (lng[1] - lng_m) * 60

        self.__status = f"{lat[0]}°{lat_m}'{lat_s:.2f}\"{lat[2]} {lng[0]}°{lng_m}'{lng_s:.2f}\"{lng[2]}"

    def __main_loop(self) -> None:
        self.__connect_device()

        while not self.__terminate.is_set():
            self.__update()
            self.__update_location()
            sleep(self.__refresh_interval)

    def connect(self) -> Optional["GTU7"]:
        if (device := self.__get_device()) is None:
            self.logger.error("GPS device not found.")
            return      # abort gps initialization if not connected

        try:
            self.__gps_decoder = GPSDecoder()

            self.__ser = serial.Serial(device, 9600, timeout=1)
            self.__ser.readline()     # Skip the first line, which may be incomplete

            self.__terminate.clear()
            self.__t = threading.Thread(target=self.__main_loop)
            self.__t.start()
        except KeyboardInterrupt:
            self.close()
            logging.info("GPS device connection terminated by user.")
        except Exception as e:
            self.close()
            self.logger.error(f"Failed to initialize GPS device: {e}")
            return

        return self

    def close(self) -> None:
        self.__terminate.set()

        self.__t.join()
        self.__is_running = False

        if self.__ser is None:
            return
        self.__ser.close()

    @property
    def status(self) -> str:
        return self.__status

    @property
    def is_running(self) -> bool:
        return self.__is_running


if __name__ == "__main__":
    gt_u7 = GTU7().connect()
    while True:
        if not gt_u7.is_running:
            gt_u7 = GTU7().connect()

        print(f'\r{gt_u7.status}')
        sleep(0.5)
