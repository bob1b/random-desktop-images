import os
import sys
import numpy as np
from PIL import Image as ImagePIL


# lightly adapted from https://www.geeksforgeeks.org/converting-image-ascii-image-python/
# gray scale level values from http://paulbourke.net/dataformats/asciiart/

# sets of characters increasing in brightness
sets_of_gray = [
    ''.join(("\u2588", "\u2593", "\u2592", "\u2591", ' '))[::-1],
    "$@B%8&WM#*oahkbdpqwmZO0QLCJUYXzcvunxrjft/\\|()1{}[]?-_+~<>i!lI;:,\"^`'. ",
    "!\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\]^_`abcdefghijklmnopqrstuvwxyz{|}~",
    ".:*I$VFNM",
    "@%#*+=-:. "
]


def average_luminance(image):
    """ Given PIL Image, return average value of grayscale value """
    im = np.array(image)
    w, h = im.shape
    return np.average(im.reshape(w*h))


def convert_image_to_ascii(filename, cols, scale, grayscale_chars):
    """
        Given Image and dims (rows, cols) returns an m*n list of Images
    """
    num_grayscale_chars = len(grayscale_chars)

    # open image and convert to grayscale
    image = ImagePIL.open(filename).convert('L')
    image_width, image_height = image.size[0], image.size[1]

    # compute width of tile
    w = image_width / cols

    # compute tile height based on aspect ratio and scale
    h = w / scale

    # compute number of rows
    rows = int(image_height / h)

    print(f"input image dims: {image_width} x {image_height}")
    print(f"cols: {cols}, rows: {rows}")
    print(f"tile dims: {w} x {h}")

    # check if image size is too small
    if cols > image_width or rows > image_height:
        print("Image too small for specified cols!")
        sys.exit()

    # ascii image is a list of character strings
    ascii_image = []
    # generate list of dimensions
    for j in range(rows):
        y1 = int(j*h)
        y2 = int((j+1)*h)

        # correct last tile
        if j == rows-1:
            y2 = image_height

        ascii_image.append("")

        for i in range(cols):
            # crop image to tile
            x1 = int(i*w)
            x2 = int((i+1)*w)

            # correct last tile
            if i == cols-1:
                x2 = image_width

            # crop image to extract tile
            img = image.crop((x1, y1, x2, y2))

            avg_lum = int(average_luminance(img))

            # append grayscale value (ascii char) to string
            ascii_image[j] += grayscale_chars[int((avg_lum*(num_grayscale_chars - 1))/255)]

    return ascii_image


def do_ascii_conversion(img_file):
    # set scale default as 0.43 which suits
    # a Courier font
    scale = 0.43

    # set cols
    cols = int(os.get_terminal_size().columns / 2)

    print('generating ASCII art...')
    # convert image to ascii txt

    return convert_image_to_ascii(img_file, cols, scale, sets_of_gray[0])
