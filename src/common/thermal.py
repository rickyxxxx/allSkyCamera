import logging

import board
import adafruit_ahtx0


class AHT20:
    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)

        i2c = board.I2C()  # uses board.SCL and board.SDA
        self._sensor = adafruit_ahtx0.AHTx0(i2c)
        self.logger.info("Thermal Sensor Initialized")

        calibrated = self._sensor.calibrate()
        if calibrated:
            self.logger.info("Thermal Sensor Calibrated")
        else:
            self.logger.warn("Thermal Sensor Calibration Failed, Readings May Be Inaccurate")

    @property
    def temp(self) -> str:
        return f"{self._sensor.temperature:.1f}°C"

    @property
    def humidity(self) -> str:
        return f"{self._sensor.relative_humidity:.1f}%"

    @property
    def temp_f(self) -> float:
        return self._sensor.temperature

    @property
    def humidity_f(self) -> float:
        return self._sensor.temperature


if __name__ == "__main__":
    sensor = AHT20()
    while True:
        print(sensor.temp, sensor.humidity)
