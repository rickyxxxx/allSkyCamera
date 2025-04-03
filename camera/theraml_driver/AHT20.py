import time
import board
import adafruit_ahtx0


class AHT20:
    def __init__(self):
        i2c = board.I2C()  # uses board.SCL and board.SDA
        self.sensor = adafruit_ahtx0.AHTx0(i2c)

    def get_temperature(self):
        return self.sensor.temperature

    def get_humidity(self):
        return self.sensor.relative_humidity

if __name__ == "__main__":
    a = AHT20()
    while True:
        temp = a.get_temperature()
        hum = a.get_humidity()
        print(f"temperature: {temp}     humidity: {hum}")
        print(type(temp), type(hum))
        time.sleep(5)
