import os

import astropy.io.fits as fits
import numpy as np
import matplotlib.pyplot as plt
import imageio
from tqdm import tqdm


def load_image(path):
    # Open the FITS file
    with fits.open(path) as hdul:
        # Access the primary HDU data
        image_data = hdul[0].data
    # Convert to a NumPy array
    image = np.array(image_data)
    return image


def weighted_average(image):
    # Get the indices of the image
    y_indices, x_indices = np.indices(image.shape)

    # Calculate the total weight
    total_weight = np.sum(image)

    # Calculate the weighted sums of the x and y coordinates
    x_weighted_sum = np.sum(x_indices * image)
    y_weighted_sum = np.sum(y_indices * image)

    # Calculate the weighted center
    x_center = x_weighted_sum / total_weight
    y_center = y_weighted_sum / total_weight

    return x_center, y_center


def image_filter(image, index, target_size=40):
    masked = image.copy()
    masked[masked != 0] = 255

    size = min(image.shape)

    def trim_image():
        nonlocal masked, size

        size /= 2
        if size < target_size:
            size = target_size
        x_cen, y_cen = weighted_average(masked)

        x0, x1 = max(0, int(x_cen - size // 2)), min(masked.shape[1], int(x_cen + size // 2))
        y0, y1 = max(0, int(y_cen - size // 2)), min(masked.shape[0], int(y_cen + size // 2))

        masked = masked[y0:y1, x0:x1]

        """
        x_cen, y_cen = weighted_average(masked)
        plt.imshow(masked, cmap='gray')
        plt.scatter(x_cen, y_cen, color='red', s=10)
        plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
        plt.show()
        """

        return x0, y0

        # return x_cen, y_cen

    x_offset, y_offset = 0, 0

    while size != target_size:
        offset = trim_image()

        x_offset += offset[0]
        y_offset += offset[1]

    filtered_image = np.zeros_like(image)
    roi = slice(y_offset, y_offset + target_size), slice(x_offset, x_offset + target_size)
    filtered_image[roi] = image[roi]

    x_cen, y_cen = weighted_average(filtered_image)

    # clear the previous scatter plot
    # plt.clf()
    #
    # plt.imshow(image[roi], cmap='gray')
    # plt.scatter(x_cen - x_offset, y_cen - y_offset, color='red', s=10)
    # plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    # plt.savefig(f"temp/{index}.png")

    return filtered_image


def make_mp4():
    images = os.listdir("temp")
    images.sort(key=lambda key: int(key.split(".")[0]))
    images = [f for f in images if f.endswith(".png")]
    images = [os.path.join("temp", f) for f in images]

    with imageio.get_writer(f'{source_dir}.mp4', mode='I', fps=2) as writer:
        for filename in images:
            image = imageio.imread(filename)
            writer.append_data(image)
            os.remove(filename)

    # remove temp files
    for filename in images:
        os.remove(filename)


if __name__ == "__main__":

    source_dir = "2 10ms 30G 100 Frames"
    files = os.listdir(source_dir)
    files = [f for f in files if f.endswith(".fits")]
    files = [os.path.join(source_dir, f) for f in files]

    shape = (2180, 3856)
    coords = []

    for i, file in enumerate(tqdm(files)):
        image = load_image(file)
        image = image_filter(image, i)
        x, y = weighted_average(image)

        coords.append((x, y))

    # make_mp4()

    plt.scatter(*zip(*coords), color='red', s=10)
    plt.show()



    # image = load_image("img.fits")
    #
    # image = image_filter(image)
    # x, y = weighted_average(image)
    #
    # print(x, y)
    #
    # plt.figure(figsize=(image.shape[1] / 100, image.shape[0] / 100), dpi=100)
    #
    # plt.imshow(image, cmap='gray')
    # plt.scatter(x, y, color='red', s=1, marker='x', alpha=0.5)
    # plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    # plt.show()
