import logging

from device.seeing_monitor import start_seeing_monitor

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

if __name__ == "__main__":
    start_seeing_monitor()