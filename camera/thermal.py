import board
import adafruit_ahtx0


class AHT20:
    def __init__(self) -> None:
        i2c = board.I2C()  # uses board.SCL and board.SDA
        self._sensor = adafruit_ahtx0.AHTx0(i2c)

        ret = self._sensor.calibrate()
        print(f"Thermal Sensor Calibrated: {ret}")

    @property
    def temp(self) -> str:
        return f"{self._sensor.temperature:.1f}°C"

    @property
    def humidity(self) -> str:
        return f"{self._sensor.relative_humidity:.1f}%"

    def temp_f(self) -> float:
        return self._sensor.temperature

    def humidity_f(self) -> float:
        return self._sensor.temperature


if __name__ == "__main__":
    sensor = AHT20()
    while True:
        print(sensor.temp, sensor.humidity)
