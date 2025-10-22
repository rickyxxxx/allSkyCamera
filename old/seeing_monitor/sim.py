import math
from itertools import product

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import animation
import matplotlib as mpl

mpl.use("Qt5Agg")

class Plot:

    def __init__(self, canvas_size=(2560, 1440), dpi=100):
        self.canvas_size = canvas_size
        self.dpi = dpi

        self.orbit_center = (self.canvas_size[0] / 2, self.canvas_size[1] / 2)
        self.orbit_radius = 500
        self.star_radius = 50
        self.star_std = 20
        self.brightness = 1
        self.theta = 0

        self.auxiliary_line = True

        self.fig, self.ax = plt.subplots(figsize=(self.canvas_size[0] / self.dpi, self.canvas_size[1] / self.dpi), dpi=self.dpi)

        self.image = self.ax.imshow(np.zeros(self.canvas_size).transpose(), cmap='gray')

    @staticmethod
    def create_star(size, brightness):
        star = np.zeros((size, size))
        center = size // 2

        xy = product(range(size), range(size))
        for x, y in xy:
            r = math.sqrt((x - center) ** 2 + (y - center) ** 2)
            if r > center:
                continue
            star[x, y] = brightness * (1 - r / center)
        return star

    def draw(self):
        canvas = np.zeros(self.canvas_size).transpose()

        star_center = (
            self.orbit_center[0] + self.orbit_radius * math.cos(self.theta),
            self.orbit_center[1] + self.orbit_radius * math.sin(self.theta)
        )
        x, y, r = int(star_center[1]), int(star_center[0]), int(self.star_radius)

        print(x, y, r)

        x0, x1 = x - r, x + r
        y0, y1 = y - r, y + r
        x0_, x1_ = max(0, x0), min(x1, self.canvas_size[1])
        y0_, y1_ = max(0, y0), min(y1, self.canvas_size[0])

        ax0, ax1 = x0_ - x0, (x1 - x1_) or 2 * r
        ay0, ay1 = y0_ - y0, (y1 - y1_) or 2 * r

        canvas[x0_:x1_, y0_:y1_] = self.create_star(2 * r, self.brightness)[ax0:ax1, ay0:ay1]

        self.image.set_data(canvas)

        # if self.auxiliary_line:
        #     # remove the previous orbit and star
        #     for artist in self.ax.artists:
        #         artist.remove()
        #
        #     # Draw the orbit
        #     orbit = plt.Circle(self.orbit_center, self.orbit_radius, edgecolor='red', facecolor='none', linewidth=1)
        #     self.ax.add_artist(orbit)
        #
        #     # Draw the star
        #     star = plt.Circle(star_center, self.star_std, edgecolor='blue', facecolor='none', linewidth=1)
        #     self.ax.add_artist(star)
        #
        # plt.show()


plot = Plot((1920, 1080))


def update(frame):
    plot.theta += 0.1
    plot.draw()
    return [plot.image] + plot.ax.artists

ani = animation.FuncAnimation(plot.fig, update, frames=np.arange(0, 100), interval=1000, blit=True)
plt.show()