import math
from itertools import product

import numpy as np
import matplotlib.pyplot as plt
import tqdm
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import Slider
import matplotlib as mpl
# mpl.use('Qt5Agg')  # or can use 'TkAgg', whatever you have/prefer/

class SimCam:

    def __init__(self, canvas_size, ax):
        self.canvas_size = canvas_size
        self.ax = ax

        self.image = np.zeros(canvas_size, dtype=np.float32).transpose()

        self.orbit_center = (self.canvas_size[0] / 2, self.canvas_size[1] / 2)
        self.orbit_radius = 500
        self.star_radius = 400
        self.star_std = 5
        self.brightness = 150
        self.brightness_std = 50
        self.theta = 0

        self.show_aux_lines = True

        self.history = []

    @staticmethod
    def _create_template(size, brightness, offset):
        star = np.zeros((size, size))
        center = size // 2

        xy = product(range(size), range(size))
        for x, y in xy:
            r = math.sqrt((x - (center + offset[0])) ** 2 + (y - (center + offset[1])) ** 2)
            if r > center:
                continue
            star[x, y] = brightness * (1 - r / center)
        return star

    def _draw_star(self, x, y, star):
        if not 0 <= x < self.image.shape[1]:
            return
        if not 0 <= y < self.image.shape[0]:
            return

        # copy the template to the image at the specified location

        temp_xcen = star.shape[1] // 2
        temp_ycen = star.shape[0] // 2

        x0_ = x - temp_xcen
        x1_ = x + temp_xcen
        y0_ = y - temp_ycen
        y1_ = y + temp_ycen

        x0 = max(x0_, 0)
        x1 = min(x1_, self.image.shape[1])
        y0 = max(y0_, 0)
        y1 = min(y1_, self.image.shape[0])

        x0_ = x0 - x0_
        x1_ = x1 - x1_ + star.shape[1]
        y0_ = y0 - y0_
        y1_ = y1 - y1_ + star.shape[0]

        self.image[y0:y1, x0:x1] += star[y0_:y1_, x0_:x1_]

    def _draw_aux_lines(self):
        # draw the orbit and the star on the image
        for artist in ax.artists:
            artist.remove()

        # Draw the orbit
        orbit = plt.Circle(self.orbit_center, self.orbit_radius, edgecolor='red', facecolor='none', linewidth=1)
        ax.add_artist(orbit)

        # Calculate star center
        star_center = (
            self.orbit_center[0] + self.orbit_radius * math.cos(self.theta),
            self.orbit_center[1] + self.orbit_radius * math.sin(self.theta)
        )

        # Draw the star
        star = plt.Circle(star_center, self.star_std, edgecolor='blue', facecolor='none', linewidth=1)
        ax.add_artist(star)

    def expose(self):
        self.image = np.zeros_like(self.image)

        x = self.orbit_center[0] + self.orbit_radius * math.cos(self.theta)
        y = self.orbit_center[1] + self.orbit_radius * math.sin(self.theta)

        x += np.random.normal(0, self.star_std)
        y += np.random.normal(0, self.star_std)

        offset = (x - int(x), y - int(y))

        brightness = self.brightness + np.random.normal(0, self.brightness_std)
        star = self._create_template(self.star_radius * 2, brightness, offset)
        self._draw_star(int(x), int(y), star)

        # print(f"Star center: {x, y}")
        avg = self.weighted_average()
        # print(f"estimated center: {avg}")
        error = np.sqrt(x ** 2 + y ** 2) - np.sqrt(avg[0] ** 2 + avg[1] ** 2)
        # print(f"error: {error}\n")

        self.image = np.zeros_like(self.image)
        theta = np.random.uniform(0, 2 * np.pi)
        tenth_arc_sec = 1 / 38
        offset = (offset[0] + np.cos(theta) * tenth_arc_sec, offset[1] + np.sin(theta) * tenth_arc_sec)
        star2 = self._create_template(self.star_radius * 2, brightness, offset)
        self._draw_star(int(x), int(y), star2)

        avg2 = self.weighted_average()

        diff = (avg[0] - avg2[0], avg[1] - avg2[1])
        p_error = abs(np.sqrt(diff[0] ** 2 + diff[1] ** 2) - tenth_arc_sec) / tenth_arc_sec * 100

        data = [x, y, float(avg[0]), float(avg[1]), error * 3.8, float(avg2[0]), float(avg2[1]), p_error]
        self.history.append(data)

        return self.image

    def weighted_average(self):
        # Get the indices of the image
        y_indices, x_indices = np.indices(self.image.shape)

        # Calculate the total weight
        total_weight = np.sum(self.image)

        # Calculate the weighted sums of the x and y coordinates
        x_weighted_sum = np.sum(x_indices * self.image)
        y_weighted_sum = np.sum(y_indices * self.image)

        # Calculate the weighted center
        x_center = x_weighted_sum / total_weight
        y_center = y_weighted_sum / total_weight

        return x_center, y_center


if __name__ == '__main__':
    fig, ax = plt.subplots(figsize=(20, 10), dpi=100)
    camera = SimCam((3856, 2180), ax)

    # img = ax.imshow(camera.expose(), cmap='gray', vmin=0, vmax=255)
    # ax.axis('off')
    # plt.subplots_adjust(left=0, right=1, top=1, bottom=0.2)
    #
    # # Add sliders for star_std and brightness_std
    # ax_star_std = plt.axes([0.2, 0.05, 0.65, 0.03], facecolor='lightgoldenrodyellow')
    # ax_brightness_std = plt.axes([0.2, 0.01, 0.65, 0.03], facecolor='lightgoldenrodyellow')
    # ax_rotation_speed = plt.axes([0.2, 0.09, 0.65, 0.03], facecolor='lightgoldenrodyellow')
    #
    # slider_star_std = Slider(ax_star_std, 'Star Std', 0.1, 100, valinit=camera.star_std)
    # slider_brightness_std = Slider(ax_brightness_std, 'Brightness Std', 0.1, 100.0, valinit=camera.brightness_std)
    # slider_rotation_speed = Slider(ax_rotation_speed, 'Rotation Speed', 0.0001, 0.1, valinit=0.01)
    #
    # def update(frame):
    #     camera.theta += slider_rotation_speed.val
    #     camera.star_std = slider_star_std.val
    #     camera.brightness_std = slider_brightness_std.val
    #     pic = camera.expose()
    #     img.set_data(pic)
    #     return [img] + ax.artists
    #
    # ani = FuncAnimation(fig, update, frames=np.arange(0, 100), interval=1, blit=True)
    # plt.show()

    for i in tqdm.tqdm(range(500)):
        camera.theta += 0.01
        pic = camera.expose()

    errors = np.array([data[-1] for data in camera.history])
    avg, std = np.mean(errors), np.std(errors)
    max_error = np.max(np.abs(errors))
    plt.hist(errors)  # arguments are passed to np.histogram
    plt.xlabel('Percentage Error (%)')
    plt.text(0.1, 0.1, f"Mean: {avg}\nStd: {std}\nMax Error:+-{max_error}",
             horizontalalignment='center', verticalalignment='center', transform=ax.transAxes)
    plt.show()

    # import pandas as pd
    # df = pd.DataFrame(camera.history, columns=['x (px)', 'y (px)', 'x_est (px)', 'y_est (px)', 'error (arc sec)'])
    # df.to_csv('sky_sim.csv', index=False)

