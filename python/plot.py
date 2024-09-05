import os

import numpy as np
from PIL import Image
import tqdm

binary_files = os.listdir("../shared/bin")

for file in tqdm.tqdm(binary_files):
    try:
        data = np.fromfile(f"../shared/bin/{file}", dtype=np.uint16).reshape(2180, 3856)
        image = Image.fromarray(data)
        image.save(f"../shared/img/{file.replace('.bin', '.tif')}")
    except ValueError:
        print(f"File {file} is not a valid binary file. Skipping...")
