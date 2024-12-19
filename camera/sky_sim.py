import numpy as np
import matplotlib.pyplot as plt
import tqdm
from matplotlib.animation import FuncAnimation
import matplotlib as mpl
import matplotlib.pyplot as plt
mpl.use('Qt5Agg')  # or can use 'TkAgg', whatever you have/prefer

class SimCam:

    def __init__(self, stars=100, zoom=1):
        self.zoom = zoom
        self.stars = stars
        self.image = np.zeros((1080, 1920), dtype=np.float32)

        # coordinates of stars in terms of polar coordinates (r, theta)
        # relative to the center of Earth's rotation axis
        self.star_coords = np.random.random((stars, 2))
        # adjust the scale of r and theta to fit the stars into the image
        self.star_coords[:, 0] *= self.image.shape[1] // 2   # radius should not exceed half the width of the image
        self.star_coords[:, 1] *= 2 * np.pi  # angle should be in radians (0 to 2pi)

        # visibility of the stars
        self.visibility = np.random.normal(10, 5, (stars,))

        # offset of the rotation axis relative to the center of the image in terms of (x, y)
        offset_limit = 10
        # the offset should not exceed [offset_limit]% of the height of the image
        self.offset = np.int32(np.random.uniform(0, 0.5, (2,)) * self.image.shape[0] * offset_limit / 100)

        # current rotation angle of the Earth in radians
        self.theta = 0

        # create a star template
        self.template = self._create_template()

        # change the radius of the first star to 100 and change its visibility to 40 to simulate polaris
        self.star_coords[0, 0] = 100
        self.visibility[0] = 80

    def _create_template(self):
        template_size = self.image.shape[0] // 100 * self.zoom
        placeholder = np.zeros((template_size, template_size), dtype=np.float32)

        sigma = template_size / 10 * self.zoom

        for i, j in np.ndindex(placeholder.shape):
            r = np.sqrt((i - placeholder.shape[0] // 2) ** 2 + (j - placeholder.shape[1] // 2) ** 2)
            if r > np.sqrt(2) * template_size / 2:
                continue
            placeholder[i, j] = 1 / np.sqrt(2 * np.pi * sigma ** 2) * np.exp(-r ** 2 / (2 * sigma ** 2))

        return placeholder

    def _get_star_coord(self, r, theta):
        theta += self.theta
        # coordinate of the center of the image
        x = self.image.shape[1] // 2 + self.offset[0]
        y = self.image.shape[0] // 2 + self.offset[1]

        # coordinate of the star in cartesian coordinates
        x += int(r * np.cos(theta))
        y += int(r * np.sin(theta))

        return x, y

    def _draw_star(self, x, y, visibility):
        if not 0 <= x < self.image.shape[1]:
            return
        if not 0 <= y < self.image.shape[0]:
            return

        # copy the template to the image at the specified location

        temp_xcen = self.template.shape[1] // 2
        temp_ycen = self.template.shape[0] // 2

        x0_ = x - temp_xcen
        x1_ = x + temp_xcen
        y0_ = y - temp_ycen
        y1_ = y + temp_ycen

        x0 = max(x0_, 0)
        x1 = min(x1_, self.image.shape[1])
        y0 = max(y0_, 0)
        y1 = min(y1_, self.image.shape[0])

        x0_ = x0 - x0_
        x1_ = x1 - x1_ + self.template.shape[1]
        y0_ = y0 - y0_
        y1_ = y1 - y1_ + self.template.shape[0]

        self.image[y0:y1, x0:x1] += self.template[y0_:y1_, x0_:x1_] * visibility

    def expose(self):
        self.image = np.zeros_like(self.image)
        for star, visibility in zip(self.star_coords, self.visibility):
            x, y = self._get_star_coord(*star)
            self._draw_star(x, y, visibility)
        return self.image


if __name__ == '__main__':
    camera = SimCam(stars=1000, zoom=2)
    fig, ax = plt.subplots(figsize=(20, 10), dpi=100)
    img = ax.imshow(camera.expose(), cmap='gray', vmin=0, vmax=np.max(camera.image))
    ax.axis('off')
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)


    def update(frame):
        camera.theta += 0.005
        pic = camera.expose()
        img.set_data(pic)
        return [img]


    ani = FuncAnimation(fig, update, frames=np.arange(0, 100), interval=1, blit=True)
    plt.show()
