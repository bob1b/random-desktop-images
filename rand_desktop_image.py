import os, copy, sys, time, json, random, collections, hashlib, time
import math
import actmon
import pprint
import importlib
from os import listdir
from os.path import isfile, join

if hasattr(importlib, 'reload'):
    from importlib import reload

# encoding=utf8  
reload(sys)  
if hasattr(sys, 'setdefaultencoding'):
    print("setting encoding to utf8")
    sys.setdefaultencoding('utf8')


#image_directory = "/home/b/Desktop/sort"
image_directory = "/home/b/Pictures"
image_info_file = "/home/b/.rand_bg_data.json"
last_viewed_images_file = '/home/b/.rand_bg_last_viewed.html'
sleep_seconds = 60 # 2 * 60
wait_for_not_idle = True

#############################################
def get_file_list(directory):
    image_list = []

    try:
        dir_list = listdir(directory)
    except OSError :
        print("get_file_list(): unable to get directory listing! image_directory = %s" % image_directory)
        exit(1)

    for f in dir_list:
        file_path = join(directory, f)
        if isfile(file_path):
            image_list.append( {"path":file_path } )
        else:
            print("%s is not a file, ignoring" % file_path)

    print("found %d files" % len(image_list))
    return image_list


def add_image_md5s(images):
    for image in images:
        image['md5'] = hashlib.md5(image["path"]).hexdigest()


def add_last_seen(images):
    for image in images:
        if 'last_seen' not in image:
            image['last_seen'] = 0
    return images


def check_for_duplicate_images(images):
    # TODO - this is likely to be very inefficient, but is only run at startup
    md5s = sorted( [i['md5'] for i in images] )
    prev_md5 = None
    for md5 in md5s:
        if prev_md5 and md5 == prev_md5:
            images = image_info_by_md5(images, md5, allow_multiple=True)
            for image in images:
                print("\tdup md5: %s\t%s" % (image['md5'], image['path']))
        prev_md5 = md5

# TODO - check for lookalike images


# TODO- this fails for empty dir, I think?
def get_min_num_views(images):
    views = [i['views'] for i in images]
    val = min(views)
    return val


def seed_random():
    random.seed(int(time.time() * random.randint(0,100) * 10))


def random_image_with_view_count(images, view_count):
    print("random_image_with_view_count(): view_count = %d" % view_count)
    md5_subset = [ i['md5'] for i in images if i['views'] <= view_count ]

    if len(md5_subset) == 0:
        return None
    subset_image_num = random.randint(0, len(md5_subset) - 1)

    return image_num_by_md5(images, md5_subset[subset_image_num])


# TODO - test this function
def first_image_with_view_count(images, views):
    ''' This is a fallback function to find an image with a given view count
        after there were too many random searches '''
    try:
        image_views = [ i['views'] for i in images ]
        return image_views.index(min_num_views) # try to find first with correct view count
    except ValueError:
        return -1


def load_info_file(image_info_file):
    obj = None
    if os.path.isfile(image_info_file):
        print("opening info file: %s" % image_info_file)
        with open(image_info_file) as json_file:
            try:
                obj = json.load(json_file)
            except ValueError:
                print("Unable to parse json data from file");
    else: # file does not exist
        # TODO
        print("info file does not exist: %s" % image_info_file)

    return obj


def create_last_viewed_images_file(filename):
    last_viewed_images = copy.deepcopy(images)
    last_viewed_images.sort(key=lambda x:x['last_seen'], reverse=True)
    l = last_viewed_images[:100]

    try:
#       print("creating last_viewed html file: %s" % filename)
        with open(filename, 'w') as last_viewed_file:
            last_viewed_file.write("<html><body>")
            for i in l:
                if int(i['last_seen']) > 0:
                    last_viewed_file.write("<img src='{}' height='100'/>".format(i['path']))
            last_viewed_file.write("</body></html>")
    except IOError:
        print("Unable to write last_viewed_images_file: %s" % filename)


def write_info_file(image_info_file, images):
#   print("writing info file: %s", image_info_file)
    try:
        with open(image_info_file, 'w') as json_file:
            json_file.write(json.dumps(images, indent=2, sort_keys=True))
    except IOError:
        print("Unable to write info file: %s" % image_info_file)


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
            print("image_info_by_mdf5(): could not find any images info matching md5: %s" % md5)
            return None

    print("image_info_by_mdf5(): could not find image info matching md5: %s" % md5)
    return None


def image_num_by_md5(images, md5):
    for idx, image in enumerate(images):
        if image['md5'] == md5:
            return idx
    return None


# TODO - perhaps rename
# TODO - probably break into sub functions
def compare_current_images_to_had_images(images, had_images):
    if not had_images:
        return images

    md5s_current = [i['md5'] for i in images]
    md5s_before  = [i['md5'] for i in had_images]

    for idx, image in enumerate(images):
        # compare paths for same filenames (same md5, different path)
        # existing file, but check for name changes
        if image['md5'] in md5s_before:
            before_image_info = image_info_by_md5(had_images, image['md5'])
            if image['path'] != before_image_info['path']:
                print("Image changed names0 - md5: %s" % image['md5'])
                print("\t%s -> %s" % (before_image_info['path'], image['path']))


            # TODO - abstract views and last_seen, pull from info_file
            # take view count from info file and save in the current image info array
            if 'views' in before_image_info:
                images[idx]["views"] = before_image_info['views']

            # take last_seen from info file and save in the current image info array
            if 'last_seen' in before_image_info:
                images[idx]["last_seen"] = before_image_info['last_seen']

    min_num_views = get_min_num_views(had_images)
    print("min_num_views = %d" % min_num_views)

    for image in images:
        # new images? (in current_images but not in had_images)
        #     view count should be min_view_count - 1
        if image['md5'] not in md5s_before:
            print("new file: %s, md5: %s" % (image['path'], image['md5']))
            if min_num_views <= 0:
                image["views"] = 0
            else:
                image["views"] = min_num_views - 1
            print("\tset initial view count to %d" % image["views"])

    for had_image in had_images:
        # deleted images? (in had_images but not in images)
        if had_image['md5'] not in md5s_current:
            print("file deleted: %s, md5: %s" % (had_image['path'], had_image['md5']))

    # ensure images has correct info on what files exist now (mainly get view count)
    return images


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


def set_background_image(path):
    command = 'gsettings set org.gnome.desktop.background picture-uri "file://%s"' % images[rand_image_num]['path']
    p = os.popen(command)


def get_random_least_recently_viewed_image(images, min_num_views):
    now = int(time.time())

    least_viewed_images = [i for i in images if i['views'] <= min_num_views]
    print("num images with view_count <= %d: %d" % (min_num_views, len(least_viewed_images)))
    if len(least_viewed_images) == 0:
        least_viewed_images = [i for i in images if i['views'] <= min_num_views + 1]

    least_viewed_images.sort(key=lambda x:x['last_seen'])
    ten_perc = int(math.ceil(len(least_viewed_images) * 0.10))
    print("ten perc of {} elements is {}".format(len(least_viewed_images), ten_perc))
    if ten_perc < 30:
        ten_perc = min(30, len(least_viewed_images))

    image_num = random.randint(0, ten_perc-1)
    return least_viewed_images[image_num]['md5']


###############################################################
# main

images = get_file_list(image_directory)
add_image_md5s(images)


# load image data that was possibly saved from last run (eg. view count)
had_images = load_info_file(image_info_file)


images = compare_current_images_to_had_images(images, had_images)
images = add_last_seen(images)

check_for_duplicate_images(images)

write_info_file(image_info_file, images)

num_images = len(images)
seed_random()

print("num_images = %d" % num_images)

how_much, time_units = seconds_to_realistic_time(num_images*sleep_seconds)


print("It will take %s %s to view all images" % (how_much, time_units))

while (1):

    loop_count = 0
    rand_image_num = 0
    min_num_views = get_min_num_views(images)

    rand_md5 = get_random_least_recently_viewed_image(images, min_num_views)
    rand_image_num = image_num_by_md5(images, rand_md5)

    images[rand_image_num]['views'] = images[rand_image_num]['views'] + 1
    seconds_since_last_seen = int(time.time()) - images[rand_image_num]['last_seen']
    print("Using image #%s '%s'" % (rand_image_num, images[rand_image_num]['path']))
    print("now at num_views =  %d" % images[rand_image_num]['views'])
    print("last seen %s (%d seconds) ago\n" % (seconds_to_realistic_time(seconds_since_last_seen), seconds_since_last_seen))
    images[rand_image_num]['last_seen'] = int(time.time())

    set_background_image(images[rand_image_num]['path'])
    write_info_file(image_info_file, images)
    create_last_viewed_images_file(last_viewed_images_file)

    epoch_time = int(time.time())
    notified = False
    while (1):
        ready_to_change_pic = False
        # if time since last picture change is greater than "sleep_seconds" - ready to change image
        # but if the idle time is greater than 2/3 "sleep_seconds", wait until idle time goes back down
        if int(time.time()) - epoch_time >= sleep_seconds:
            ready_to_change_pic = True

        idle_ms = actmon.get_idle_time()

        if ready_to_change_pic:
            if idle_ms > (.5 * sleep_seconds * 1000) and wait_for_not_idle:
                if not notified:
                    print("ready to change pic, waiting for end of idle")
                    notified = True
#                   print("ready to change pic, sleeping: %f < %f" % (idle_ms, (.5 * sleep_seconds * 1000)))
            else:
                if notified:
                    print("Got it. Waiting 2 seconds")
                time.sleep(2)
                notified = False
                break
        else:
#           print("not ready to change pic, sleeping: %s" % idle_ms)
            next
        
        time.sleep(1)
