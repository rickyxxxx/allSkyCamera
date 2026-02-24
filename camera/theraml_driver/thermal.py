
import RPi.GPIO as GPIO
import requests

import board
import adafruit_ahtx0

class AHT20:

    class WeatherParams:
        latitude = 34.4132
        longitude = -119.8489
        hourly = "temperature_2m"
    
    WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
    PULL_SECONDS = 5
    HTTP_TIMEOUT = 5
    TARGET_TEMPERATURE = 24

    GPIO_PIN = 26

    def __init__(self, pin: int = GPIO_PIN, target_temperature: float = TARGET_TEMPERATURE, weather_params: WeatherParams = WeatherParams()):
        self.GPIO_PIN = pin
        self.TARGET_TEMPERATURE = target_temperature
        self.WEATHER_PARAMS = {
            "latitude": weather_params.latitude,
            "longitude": weather_params.longitude,
            "hourly": weather_params.hourly
        }
        self.sensor = adafruit_ahtx0.AHTx0(board.I2C())
        self._heater_setup()
    
    def fetch_weather(self) -> dict:
        '''
        Fetch the weather data from the Open-Meteo API. Returns a dictionary containing hourly temperature data for the specified location.
        
        :return: Description
        :rtype: dict
        '''

        r = requests.get(self.WEATHER_URL, params=self.WEATHER_PARAMS, timeout=self.HTTP_TIMEOUT)
        print(r.url)
        r.raise_for_status()
        data=r.json()
        return data
    
    def _heater_setup(self):
        '''
        Configure the GPIO pin for controlling the heater. Sets the specified GPIO pin as an output and initializes it to LOW (heater off).
        '''

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.GPIO_PIN, GPIO.OUT, initial=GPIO.LOW)

    def get_temperature(self) -> float:
        '''
        Fetch the temperature from the temperature sensor.
        
        :return: The current temperature reading from the sensor.
        :rtype: float
        '''

        temperature = self.sensor.temperature
        return temperature
    
    def get_humidity(self) -> float:
        '''
        Fetch the humidity from the sensor.
        
        :return: The current humidity reading from the sensor.
        :rtype: float
        '''

        humidity = self.sensor.relative_humidity
        return humidity
    
    def _heat_on(self):
        '''
        Turn the heater on
        '''

        GPIO.output(self.GPIO_PIN, GPIO.HIGH)

    def _heat_off(self):
        '''
        Turn the heater off
        '''

        GPIO.output(self.GPIO_PIN, GPIO.LOW)

    def update(self) -> None:
        current_temperature = self.get_temperature()
        if current_temperature < self.TARGET_TEMPERATURE:
            self._heat_on()
        else:
            self._heat_off()