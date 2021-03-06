# -*- coding: utf-8 -*-
import os
import copy
import sys
import time
import json
import random
import hashlib
import math
import getopt
import pprint
import importlib
from datetime import datetime
from os import listdir
from os.path import isfile, join
from shutil import copyfile
from pynput.keyboard import Listener

import cv2  ## pip3 install opencv

from colorama import Fore, Back, Style
from PIL import Image as ImagePIL
from PIL.ExifTags import TAGS, GPSTAGS

import numpy as np # for ascii image
import gajim_common_idle as idle


# ensure python 3
if sys.version_info.major < 3:
    sys.exit("This is not Python 3")


# TODO - clean up code
# TODO - config file (yaml?)
# TODO - delete file from polling prompt
# TODO - change to polling mode without exiting
# TODO - go back to previous pic (affects history?)
# TODO - go to specific pic (by number or path or filename? wildcard or typeahead?)
# TODO - list files - filter by props, eg. landscape or above a certain size
# TODO - change all config during runtime
# TODO - save new config during runtime
# TODO - error log file
# TODO - check for file dups when running?
# TODO - pic ranking
# TODO - deal with overlength exif or corrupted data
# TODO - warn if image size is too low, or set skipped files
# TODO - instead of delete, move to 'to_delete' directory
# TODO - write exif info?

################################################ ascii
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

def getAverageL(image):
    """
    Given PIL Image, return average value of grayscale value
    """

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
            avg = int(getAverageL(img))

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


def is_windows():
    return sys.platform.startswith('win32')

def is_linux():
    return sys.platform.startswith('linux')

key_releases = 0
def on_press(key):
    pass

def on_release(key):
    global key_releases
    key_releases = key_releases + 1
#   print("key releases = %d" % key_releases)


################################################ /ascii


# windows only (install from https://github.com/mhammond/pywin32/releases)
if is_windows():
    import win32api, win32con, win32gui

if not is_windows() and not is_linux():
    sys.exit("Unsupported platform: '" + sys.platform + "'. Exiting")


if hasattr(importlib, 'reload'):
    from importlib import reload

# encoding=utf8
reload(sys)
if hasattr(sys, 'setdefaultencoding'):
    # print("setting encoding to utf8")
    sys.setdefaultencoding('utf8')


check_images = True
check_images_after_first_pic_change = True

#base = "C:/Users/b/Desktop/rand_bg_image/"
#image_directory = "C:/Users/b/Desktop/other/pictures"
#image_info_file =         base + "rand_bg_data.json"
#last_viewed_images_file = base + "rand_bg_last_viewed.html"
#temp_image_file =         base + "rand_bg_temp_image.png"
#thumbnail_directory =     base + "thumbnails/"

image_directory = "/home/b/Pictures"
image_info_file = "/home/b/.rand_bg_data.json"
last_viewed_images_file = "/home/b/.rand_bg_last_viewed.html"
temp_image_file = "/home/b/.rand_bg_temp_image.png"
thumbnail_directory = "/home/b/.rand_bg_thumbs"

thumbnail_size = 512, 512
sleep_seconds = 15
after_idle_wait_seconds = 2
percentage = 50 # randomly choose from this percentage of the least recently viewed images
wait_for_not_idle = True
span_multiple_images = 1
polling = 0
write_info_only = 0

do_ascii_image = 0

num_key_releases = 0
listener = Listener(on_press=on_press, on_release=on_release)
listener.start()


#############################################
def num_seen_since(images, seconds_ago):
    count = 0
    for i in images:
        if i['last_seen'] > 0:
            if (int(time.time()) - i['last_seen']) <= seconds_ago:
                count = count + 1
    return count

#############################################
def num_seen(images):
    now = datetime.now()
    seconds_since_midnight = \
      (now - now.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds()
    seconds_24_hours = 60 * 60 * 24
    seconds_per_week = seconds_24_hours * 7
    seconds_per_month = seconds_per_week * 52 / 12
    seconds_per_year = seconds_per_week * 52

    info("%d images seen since midnight" % num_seen_since(images, seconds_since_midnight))
    info("%d images seen in last 24 hours" % num_seen_since(images, seconds_24_hours))
    info("%d images seen in last week" % num_seen_since(images, seconds_per_week))
    info("%d images seen in last month" % num_seen_since(images, seconds_per_month))
    info("%d images seen in last year" % num_seen_since(images, seconds_per_year))


#############################################
def info(msg):
    print(f"{Fore.BLUE}%s{Style.RESET_ALL}" % msg)

#############################################
def warning(msg):
    print(f"{Back.RED}{Fore.WHITE}%s{Style.RESET_ALL}" % msg)

#############################################
def create_thumbnail(image):
    if not os.path.isdir(thumbnail_directory) or not os.path.exists(thumbnail_directory):
        warning("create_thumbnail(): thumbnail directory '%s' does not exist. Creating\n" \
          % thumbnail_directory)
        os.makedirs(thumbnail_directory)
    image_path = image['path']
    thumbnail_image_path = thumbnail_path_from_image(image)

    try:
        im = ImagePIL.open(image_path)
        im.thumbnail(thumbnail_size)
        im.save(thumbnail_image_path, "JPEG")
    except IOError:
        warning("cannot create thumbnail for '%s'" % image_path)
#   except:
#       warning("! cannot create thumbnail for '%'" % image_path)


#############################################
def get_file_list(directory):
    image_list = []

    try:
        dir_list = listdir(directory)
    except OSError:
        warning("get_file_list(): unable to get directory listing! image_directory = %s" \
          % image_directory)
        exit(1)

    for f in dir_list:
        file_path = join(directory, f)
        if isfile(file_path):
            image_list.append({"path":file_path})
        else:
            warning("%s is not a file, ignoring" % file_path)

    return image_list


#############################################
# wonder if there's a way to get the checksum for the image content only
def add_image_md5s(images):
    for image in images:
        image['md5'] = hashlib.md5(image["path"].encode('utf-8')).hexdigest()


#############################################
def add_last_seen(images):
    for image in images:
        if 'last_seen' not in image:
            image['last_seen'] = 0
    return images


#############################################
def check_for_duplicate_images(images):
    # TODO - this is likely to be very inefficient, but is only run at startup
    md5s = sorted([i['md5'] for i in images])
    prev_md5 = None
    for md5 in md5s:
        if prev_md5 and md5 == prev_md5:
            images = image_info_by_md5(images, md5, allow_multiple=True)
            for image in images:
                warning("\tdup md5: %s\t%s" % (image['md5'], image['path']))
        prev_md5 = md5


#############################################
# TODO - check for lookalike images


#############################################
def get_min_num_views(images):
    views = []
    if not images or len(images) == 0:
        return 0
    for i in images:
        if 'views' not in i:
            i['views'] = 0
        views.append(i['views'])

    val = min(views)
    #print("      min_num_views = %d" % val)

    # we have some unseen images
    if val == 0:
        num_unseen = 0
        for i in images:
            if i['views'] == 0:
                num_unseen = num_unseen + 1
        info("      there are %d images that have not been seen yet" % num_unseen)

    return val


#############################################
def seed_random():
    random.seed(int(time.time() * random.randint(0, 100) * 10))


#############################################
def random_image_with_view_count(images, view_count):
    print("random_image_with_view_count(): view_count = %d" % view_count)
    md5_subset = [i['md5'] for i in images if i['views'] <= view_count]

    if len(md5_subset) == 0:
        return None
    subset_image_num = random.randint(0, len(md5_subset) - 1)

    return image_num_by_md5(images, md5_subset[subset_image_num])


#############################################
# TODO - test this function
def first_image_with_view_count(images, views):
    ''' This is a fallback function to find an image with a given view count
        after there were too many random searches '''
    try:
        image_views = [i['views'] for i in images]
        return image_views.index(min_num_views) # try to find first with correct view count
    except ValueError:
        return -1


#############################################
def load_info_file(image_info_file):
    obj = None
    if os.path.isfile(image_info_file):
        copyfile(image_info_file, image_info_file + "_BCK")

        with open(image_info_file) as json_file:
            try:
                obj = json.load(json_file)
            except ValueError:
                warning("Unable to parse json data from file")
    else: # file does not exist
        # TODO
        warning("info file does not exist: %s" % image_info_file)

    return obj


#############################################
def thumbnail_path_from_image(image):
    return thumbnail_directory + "/" + image['md5']+".jpg"


#############################################
def create_last_viewed_images_file():
    last_viewed_images = copy.deepcopy(images)
    last_viewed_images.sort(key=lambda x: x['last_seen'], reverse=True)

    try:
        with open(last_viewed_images_file, 'w') as last_viewed_file:
            last_viewed_file.write("""
                <html>
                  <head>
                    <script src="https://ajax.googleapis.com/ajax/libs/jquery/3.4.1/jquery.min.js"></script>
                    <style>
                      body { font-family:sans; }
                      ul { list-style-type:none; }
                      ul.blocks > li { float: left;
                           margin: 10px;
                           border: 1px solid #ccc;
                           font-size: 0.7em;
                           text-align: center; }
                      ul.file-info li {}
                    </style>
                  </head>
                  <body>
                        <table>
                          <tr><td>number of images</td><td>%d</td></tr>
                          <tr><td>image directory</td><td>%s</td></tr>
                          <tr><td>image info file</td><td>%s</td></tr>
                          <tr><td>last viewed images file</td><td>%s</td></tr>
                          <tr><td>thumbnail directory</td><td>%s</td></tr>
                          <tr><td>thumbnail size</td><td>%d x %d</td></tr>
                          <tr><td>sleep seconds</td><td>%d</td></tr>
                          <tr><td>after idle wait seconds</td><td>%d</td></tr>
                          <tr><td>Time to view all images</td><td>%s %s</td></tr>
                        </table>
                        <p><b>Most recently viewed image first</b></p>
                        <ul class="blocks">
            """ % (num_images, image_directory, image_info_file, last_viewed_images_file,
                   thumbnail_directory, thumbnail_size[0], thumbnail_size[1], sleep_seconds,
                   after_idle_wait_seconds, how_much, time_units))

#           for i in l:
#               if int(i['last_seen']) > 0:
#                   seconds_since_last_seen = int(time.time()) - i['last_seen']
#                   last_viewed_file.write("""
#                     <li>
#                       <a href='{}'><img src='{}' height='200'/></a>
#                       <ul class="file-info">
#                         <li>{}</li>
#                         <li>{} views</li>
#                         <li>last seen {}</li>
#                       </ul>
#                     </li>
#                   """.format(i['path'], thumbnail_path_from_image(i), i['md5'], i['views'],
#                              seconds_to_realistic_time(seconds_since_last_seen)))

            last_viewed_file.write("""
                  </ul>
                  <script> """ + "\
                    var images = " + json.dumps(last_viewed_images) + ";" + """
                    $(document).ready(function(){
                      console.log(images);
                    });
                  </script> 
                  </body></html>""")

    except IOError:
        warning("Unable to write last_viewed_images_file: %s" % last_viewed_images_file)


#############################################
def write_info_file(image_info_file, images):
    try:
        with open(image_info_file, 'w') as json_file:
            json_file.write(json.dumps(images, indent=2, sort_keys=True))
    except IOError:
        warning("Unable to write info file: %s" % image_info_file)


#############################################
def image_info_by_md5(images, md5, allow_multiple=False):
    found_images = []
    for image in images:
        if image['md5'] == md5:
            if allow_multiple:
                found_images.append(image)
                next
            else:
                return image

    if allow_multiple:
        if len(found_images) > 0:
            return found_images
        else:
            warning("image_info_by_mdf5(): could not find any images info matching md5: %s" % md5)
            return None

    warning("image_info_by_mdf5(): could not find image info matching md5: %s" % md5)
    return None


#############################################
def image_num_by_md5(images, md5):
    for idx, image in enumerate(images):
        if image['md5'] == md5:
            return idx
    return None


#############################################
def completion_printout(idx, final_count, prev_tick):
    perc = float(idx)/final_count*100
#   print("{} {} {}".format(idx, final_count, prev_tick))
    if int(time.time()) >= prev_tick + 2:
        prev_tick = int(time.time())
        info("      {} % ({} of {})".format(int(perc), idx, final_count))
    return prev_tick


#############################################
# TODO - perhaps rename
# TODO - probably break into sub functions
def compare_current_images_to_had_images(images, had_images):
    if not check_images:
        if not os.path.exists(image_info_file):
            warning("Info file doesn't exist, cannot skip compare_current_images_to_had_images()")
        else:
            return had_images


    if not had_images:
        return images

    md5s_current = [i['md5'] for i in images]
    md5s_before = [i['md5'] for i in had_images]
    md5s_before_dict = {image['md5']: image for image in had_images}

    for idx, image in enumerate(images):
        # compare paths for same filenames (same md5, different path)
        # existing file, but check for name changes
        if image['md5'] in md5s_before_dict:
            before_image_info = md5s_before_dict[image['md5']]
            if image['path'] != before_image_info['path']:
                warning("Image changed names - md5: %s" % image['md5'])
                warning("\t%s -> %s" % (before_image_info['path'], image['path']))

            # TODO - abstract views and last_seen, pull from info_file
            # take view count from info file and save in the current image info array
            if 'views' in before_image_info:
                images[idx]["views"] = before_image_info['views']

            # take last_seen from info file and save in the current image info array
            if 'last_seen' in before_image_info:
                images[idx]["last_seen"] = before_image_info['last_seen']

    #print("\nChecking for new images")
    for idx, image in enumerate(images):
        # new images? (in current_images but not in had_images)
        #     view count should be min_view_count - 1
        if image['md5'] not in md5s_before_dict:
            info("new file: %s, md5: %s" % (image['path'], image['md5']))
            if min_num_views <= 0:
                image["views"] = 0
            else:
                image["views"] = min_num_views - 1
            info("\tset initial view count to %d" % image["views"])

    md5s_current_dict = {image['md5']: image for image in images}
    #print("\nChecking for deleted images")
    for idx, had_image in enumerate(had_images):
        # deleted images? (in had_images but not in images)
        if had_image['md5'] not in md5s_current_dict:
            warning("file deleted: %s, md5: %s" % (had_image['path'], had_image['md5']))

    # ensure images has correct info on what files exist now (mainly get view count)
    return images


#############################################
def seconds_to_realistic_time(seconds):
    if seconds <= 60:
        return (seconds, "seconds")

    minutes = seconds / 60.0
    if minutes < 60:
        return ("%.2f" % minutes, 'minutes')

    hours = minutes / 60.0
    if hours < 24:
        return ("%.2f" % hours, 'hours')

    days = hours / 24.0
    if days < 7:
        return ("%.2f" % days, 'days')

    weeks = days / 7.0
    return ("%.2f" % weeks, 'weeks')

def print_exif(fn):
    ret = {}
    try:
        i = ImagePIL.open(fn)
        info = i._getexif()
        if not info:
            return {}
    except:
        print(Back.RED + Fore.WHITE + "Unable to open file for reading exif" + Style.RESET_ALL)
        return {}

    for tag, value in info.items():
        decoded = TAGS.get(tag, tag)
        ret[decoded] = value
        print((Fore.YELLOW + "\t%s %s" + Style.RESET_ALL) % (str(decoded).ljust(20, ' '), value))


#############################################
def set_background_image(image):
    if is_windows():
        set_background_image_windows(image)
    else: # assume linux
        set_background_image_linux(image)

#############################################
def set_background_image_windows(image):
    path = image
    if isinstance(image, dict):
        path = image['path']

    key = win32api.RegOpenKeyEx(win32con.HKEY_CURRENT_USER, \
      "Control Panel\\Desktop", 0, win32con.KEY_SET_VALUE)
    win32api.RegSetValueEx(key, "WallpaperStyle", 1, win32con.REG_SZ, "1")
    win32api.RegSetValueEx(key, "TileWallpaper", 0, win32con.REG_SZ, "0")
    win32gui.SystemParametersInfo(win32con.SPI_SETDESKWALLPAPER, path, 1+2)


#############################################
def set_background_image_linux(image):
    path = image
    if isinstance(image, dict):
        path = image['path']
    # TODO - list

    # get scaling method
    command = 'gsettings get org.gnome.desktop.background picture-options'
    p = os.popen(command)
    scaling = p.read().split('\n')[0] # TODO - might be a better way to do this

    command = 'gsettings set org.gnome.desktop.background picture-uri "file://%s"' % path
    p = os.popen(command)

    if scaling != "'scaled'":
        print("setting scale method")
        command = 'gsettings set org.gnome.desktop.background picture-options none ; ' + \
         'gsettings set org.gnome.desktop.background picture-options scaled'
        p = os.popen(command)
#   command = 'gsettings set org.gnome.desktop.background picture-options scaled'
#   p = os.popen(command)


#############################################
def get_random_least_recently_viewed_image(images, min_num_views):
    # now = int(time.time())  XXX unused?

    least_viewed_images = [i for i in images if i['views'] <= min_num_views]
    #print("      num images with view_count <= %d: %d" % (min_num_views, len(least_viewed_images)))
    if len(least_viewed_images) == 0:
        least_viewed_images = [i for i in images if i['views'] <= min_num_views + 1]

    least_viewed_images.sort(key=lambda x: x['last_seen'])

    percent = int(math.ceil(len(least_viewed_images) * (float(percentage) / 100.0)))
    if percent < 30:
        percent = min(30, len(least_viewed_images))

    image_num = random.randint(0, percent-1)
    #print("rand image num = %d" % image_num)
    return least_viewed_images[image_num]['md5']


#############################################
def next_random_image(images):
    rand_image_num = 0
    min_num_views = get_min_num_views(images)
    rand_md5 = get_random_least_recently_viewed_image(images, min_num_views)
    rand_image_num = image_num_by_md5(images, rand_md5)
    images[rand_image_num]['views'] = images[rand_image_num]['views'] + 1
    seconds_since_last_seen = int(time.time()) - images[rand_image_num]['last_seen']
    msg = "\n#%s, '%s'" % (rand_image_num, images[rand_image_num]['path'])
#   print("now at num_views =  %d" % images[rand_image_num]['views'])

    # TODO - move to a function
    now = datetime.now()
    seconds_since_midnight = \
      (now - now.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds()
    num_since_midnight = num_seen_since(images, seconds_since_midnight)

    if images[rand_image_num]['last_seen'] > 0:
        print((Fore.MAGENTA + "%s, last seen %s (%d seconds) ago (#%d)" + \
          Style.RESET_ALL) % \
          (msg, seconds_to_realistic_time(seconds_since_last_seen), \
           seconds_since_last_seen, num_since_midnight))
    else:
        info("%s, first time viewing image (#%d)" % (msg, num_since_midnight))
    sizes = image_sizes(images, rand_image_num)
    info("%s x %s, %s kB" % (sizes['width'], sizes['height'], sizes['size']))

    # TODO - if we're viewing multiple images at once (2+ display, spanned),
    #        update all of the images' last_seen value
    images[rand_image_num]['last_seen'] = int(time.time())
    return images[rand_image_num]

#############################################
def image_sizes(images, image_num):
    file = images[image_num]['path']
    img = cv2.imread(file, 0)
    try:
        height, width = img.shape[:2]
    except:
        height = "??"
        width = "??"
    try:
        file_stats = os.stat(file)
        file_size = (float(file_stats.st_size) / 1024.0)
    except:
        file_size = '??'
    return {'width':width, 'height':height, 'size':file_size}


#############################################
def get_idle_time():
    if is_windows():
        return win32api.GetTickCount() - win32api.GetLastInputInfo()

    # assume linux
    return idle.getIdleSec() * 1000


#############################################
# this is the wait for idle loop
def do_wait():
    epoch_time = int(time.time())
    notified = False

    prev_key_releases = key_releases
    while 1:
        try:
            ready_to_change_pic = False
            # If time since last picture change is greater than "sleep_seconds"
            #   then we're ready to change the image.
            # But if the idle time is greater than 1/2 of "sleep_seconds",
            #   wait until idle time goes back down
            if int(time.time()) - epoch_time >= sleep_seconds:
                ready_to_change_pic = True

            idle_ms = get_idle_time()

            if ready_to_change_pic:
                if idle_ms > (.5 * sleep_seconds * 1000) and wait_for_not_idle:
                    if not notified:
                        print(f"{Fore.BLUE}ready to change pic, waiting for end of idle{Style.RESET_ALL}")
                        notified = True
                else:
                    if notified:
                        print(f"{Fore.BLUE}Waiting %d seconds{Style.RESET_ALL}" % after_idle_wait_seconds)
                    time.sleep(after_idle_wait_seconds)
                    notified = False
                    break

            # check for keypress
            #   https://pypi.org/project/pynput/
#           print("key_releases = %d, prev = %d" % (key_releases, prev_key_releases))
            if key_releases > prev_key_releases:
                pass
#               print("new key press")
#               prev_key_releases = key_releases

#               global polling
#               polling = 1
#               return

            time.sleep(0.5)
        except KeyboardInterrupt:
            sys.exit()


###############################################################
# main

usage = 'python ' + sys.argv[0] + ' -c <count: num images before exit> ' + \
        '-p <1>(poll: enter goes to next image immediately ' + \
        '-I <1>(check for new/deleted images and write image file only) )'

image_count_to = -1
try:
    opts, args = getopt.getopt(sys.argv[1:], "c:o:p:I", ["c", "p", "I"])
except getopt.GetoptError:
    info(usage)
    sys.exit(2)

for opt, arg in opts:
    if opt == '-h':
        info(usage)
        sys.exit()
    elif opt == '-c':
        image_count_to = int(arg)
    elif opt == '-p':
        polling = 1
    elif opt == '-I':
        write_info_only = 1

images = get_file_list(image_directory)
add_image_md5s(images)


# load image data that was possibly saved from last run (eg. view count)
had_images = load_info_file(image_info_file)

min_num_views = get_min_num_views(had_images)

images = compare_current_images_to_had_images(images, had_images)
images = add_last_seen(images)

check_for_duplicate_images(images)

write_info_file(image_info_file, images)
if write_info_only:
    print("Exiting after writing image file")
    sys.exit()

num_images = len(images)
seed_random()

per_day = (24 * 60 * 60) / sleep_seconds
how_much, time_units = seconds_to_realistic_time(num_images*sleep_seconds)
print("######################\n## %d files, %s %s, %s per day" \
  % (len(images), how_much, time_units, str(int(per_day))))

num_seen(images)

counter = 0

# main loop
while 1:

    if span_multiple_images > 1:
        image_paths = []
        for i in range(0, span_multiple_images):
            image = next_random_image(images)
            create_thumbnail(image)
            image_paths.append(image['path'])
        opened_images = map(ImagePIL.open, image_paths)
        widths, heights = zip(*(i.size for i in opened_images))

        total_width = sum(widths)
        max_height = max(heights)

        new_im = ImagePIL.new('RGB', (total_width, max_height))

        x_offset = 0
        for im in opened_images:
            new_im.paste(im, (x_offset, 0))
            x_offset += im.size[0]

        new_im.save(temp_image_file)
        set_background_image(temp_image_file) # TODO

    else:
        image = next_random_image(images)

        exifd = print_exif(image['path'])

        set_background_image(image)
        create_thumbnail(image)

        if do_ascii_image:
            do_conversion(image['path'])

    write_info_file(image_info_file, images)
    create_last_viewed_images_file()

    counter = counter + 1
#   if image_count_to > 0 and counter >= image_count_to:
    if counter >= image_count_to > 0:
        break

    if polling:
        input("\n" + Back.BLUE + Fore.WHITE + "polling - enter for next image: " + Style.RESET_ALL)
    else:
        print(f"{Fore.BLUE}Waiting %d seconds{Style.RESET_ALL}" % sleep_seconds)
        do_wait()
