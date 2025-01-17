import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches


class Plot:

    def __init__(self):
        self.star, self.orbit = None, None
        self.fig, (self.ax1, self.ax2) = plt.subplots(1, 2, figsize=(12, 6), dpi=200)

        self._config_plot()

    def _config_plot(self):
        self.fig.patch.set_facecolor('black')

        self.ax1.axis('off')
        self.ax1.set_facecolor('black')

        self.ax2.spines[['top', 'right']].set_visible(False)
        self.ax2.set_facecolor('black')
        self.ax2.tick_params(colors='white')
        for spine in self.ax2.spines.values():
            spine.set_edgecolor('white')

    def update_image(self, image, star_cen):
        if self.star:
            self.star.remove()

        self.ax1.imshow(image, cmap='gray')
        x, y, r = star_cen

        self.star = patches.Circle((x, y), r, edgecolor='red', facecolor='none', linewidth=0.2)
        self.ax1.add_patch(self.star)

    def update_orbit(self, orbit_cen, orbit_history):
        if self.orbit:
            self.orbit.remove()

        self.orbit = patches.Circle(orbit_cen, orbit_history[-1], edgecolor='red', facecolor='none', linewidth=0.2)
        self.ax1.add_patch(self.orbit)

        if not self.ax2.lines:
            self.ax2.plot(orbit_history, color='white', marker='o', linestyle='')
        else:
            self.ax2.lines[0].set_data(*orbit_history)

    @staticmethod
    def draw():
        plt.tight_layout()
        plt.show()


# Generate a random greyscale image
image = np.random.rand(2180, 3856)


# Generate data for the line plot
x = np.linspace(0, 10, 100)
y = np.sin(x)

p = Plot()

p.update_image(image, (50, 50, 50))
p.update_orbit((1000, 1000), [100, 200, 100, 500, 200, 300, 100, 600])
p.draw()

