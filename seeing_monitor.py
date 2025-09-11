import requests
from datetime import datetime
from multiprocessing import cpu_count, Queue, Lock, Process, Event

from time import sleep

import numpy as np
import cv2

from camera.camera import Camera


SERVER_URL = 'http://camserver.physics.ucsb.edu/upload_live'


def frame_post_process(image: np.ndarray, **kwargs) -> None:
    image_8bit = cv2.convertScaleAbs(image, alpha=(255.0/65535.0))
    success, encoded_image = cv2.imencode('.png', image_8bit)

    if not success:
        return

    response = requests.post(SERVER_URL, data=encoded_image.tobytes())
    print(response.status_code, kwargs.get('timestamp', 'no timestamp'))


def main_loop() -> None:
    while True:
        frame = camera.expose(exposure_time=EXPOSURE_TIME, gain=GAIN, bbp=BPP)
        timestamp = datetime.now().strftime("%S.%f")
        with queue_lock:
            if task_queue.qsize() >= MAX_PENDING_TASKS:
                continue
            task_queue.put((frame, timestamp))
        sleep(1)


def worker() -> None:
    while not terminated.is_set():
        with queue_lock:
            if task_queue.qsize() == 0:
                continue
            frame, timestamp = task_queue.get()
        frame_post_process(frame, timestamp=timestamp)


if __name__ == "__main__":
    EXPOSURE_TIME = 10_000  # unit in us
    GAIN = 1
    BPP = 8  # bit depth

    camera = Camera()
    camera.config_continuous_mode()

    # main loop
    while True:
        try:
            frame = camera.expose(exposure_time=EXPOSURE_TIME, gain=GAIN, bbp=BPP)
            timestamp = datetime.now().strftime("%S.%f")
            success, encoded_image = cv2.imencode('.jpg', frame)

            files = {
                "image": ("image.jpg", encoded_image.tobytes(), "image/jpg"),
            }
            data = {
                "ts": timestamp,
                "serial": camera.serial_number,
            }
            response = requests.post(SERVER_URL, data=data, files=files, timeout=5)

            settings = response.json().get("settings", {})
            EXPOSURE_TIME = settings.get("exposure", EXPOSURE_TIME)
            GAIN = settings.get("gain", GAIN)
            print(EXPOSURE_TIME, GAIN)
        except Exception as e:
            print(e)

# if __name__ == "__main__":
#     EXPOSURE_TIME = 10_000  # unit in us
#     GAIN = 1
#     BPP = 8  # bit depth
#
#     MAX_PENDING_TASKS = 10
#     task_queue = Queue()
#     queue_lock = Lock()
#     terminated = Event()
#     camera = Camera()
#     camera.config_continuous_mode()
#
#     processes = [Process(target=worker) for _ in range(cpu_count() - 1)]
#     for p in processes:
#         p.start()
#
#     try:
#         main_loop()
#     except Exception as e:
#         print(e)
#         terminated.set()
#
#     for p in processes:
#         p.join()
#
#     camera.close()
#     # TODO: reboot the camera after crash
