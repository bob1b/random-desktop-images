import sys
import numpy as np # for ascii image
from PIL import Image as ImagePIL


# lightly adapted from https://www.geeksforgeeks.org/converting-image-ascii-image-python/

# gray scale level values from:
# http://paulbourke.net/dataformats/asciiart/

# 70 levels of gray
gscale1 = ''.join(("\u2588", "\u2593", "\u2592", "\u2591", ' '))[::-1]
# "$@B%8&WM#*oahkbdpqwmZO0QLCJUYXzcvunxrjft/\\|()1{}[]?-_+~<>i!lI;:,\"^`'. "
# "!\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\]^_`abcdefghijklmnopqrstuvwxyz{|}~"
# .:*I$VFNM


# 10 levels (shades?!) of gray
# '@%#*+=-:. '

def get_average_l(image):
    """ Given PIL Image, return average value of grayscale value """

    # get image as numpy array
    im = np.array(image)

    # get shape
    w, h = im.shape

    # get average
    return np.average(im.reshape(w*h))

def convertImageToAscii(fileName, cols, scale):
    """
    Given Image and dims (rows, cols) returns an m*n list of Images
    """
    # declare globals
    global gscale1

    # open image and convert to grayscale
    image = ImagePIL.open(fileName).convert('L')

    # store dimensions
    W, H = image.size[0], image.size[1]
    print("input image dims: %d x %d" % (W, H))

    # compute width of tile
    w = W/cols

    # compute tile height based on aspect ratio and scale
    h = w/scale

    # compute number of rows
    rows = int(H/h)

    print("cols: %d, rows: %d" % (cols, rows))
    print("tile dims: %d x %d" % (w, h))

    # check if image size is too small
    if cols > W or rows > H:
        print("Image too small for specified cols!")
        sys.exit()

    # ascii image is a list of character strings
    aimg = []
    # generate list of dimensions
    for j in range(rows):
        y1 = int(j*h)
        y2 = int((j+1)*h)

        # correct last tile
        if j == rows-1:
            y2 = H

        # append an empty string
        aimg.append("")

        for i in range(cols):

            # crop image to tile
            x1 = int(i*w)
            x2 = int((i+1)*w)

            # correct last tile
            if i == cols-1:
                x2 = W

            # crop image to extract tile
            img = image.crop((x1, y1, x2, y2))

            # get average luminance
            avg = int(get_average_l(img))

            # look up ascii char
            gsval = gscale1[int((avg*(len(gscale1) - 1))/255)]

            # append ascii char to string
            aimg[j] += gsval

    # return txt image
    return aimg

def do_conversion(img_file):
    # set scale default as 0.43 which suits
    # a Courier font
    scale = 0.43

    # set cols
    # TODO - use terminal height and width to ensure generated image fits
    cols = int(os.get_terminal_size().columns / 2)

    print('generating ASCII art...')
    # convert image to ascii txt
    aimg = convertImageToAscii(img_file, cols, scale)

    for row in aimg:
        print(row)

