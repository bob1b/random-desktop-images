import os
import sys
import time
import json
import random
import collections
import hashlib
import time
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
sleep_seconds = 2 * 60
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
            image_list.append( {"path":file_path, "views":0 } )
        else:
            print("%s is not a file, ignoring" % file_path)

    print("found %d files" % len(image_list))
    return image_list


def add_image_md5s(images):
    for image in images:
        image['md5'] = hashlib.md5(image["path"]).hexdigest()


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


# TODO- this fails for empty dir, I think?
def get_min_num_views(images):
    views = [i['views'] for i in images]
    val = min(views)
    return val


def seed_random():
    random.seed(int(time.time() * random.randint(0,100) * 10))


def first_image_with_view_count(images, views):
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
    else: # file does not exit
        # TODO
        print("info file does not exist: %s" % image_info_file)

    return obj


def write_info_file(image_info_file, images):
#   print("writing info file: %s", image_info_file)
    try:
        with open(image_info_file, 'w') as json_file:
#           json.dump(images, json_file)
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

            # take view count from info file and save in the current image info array
            if before_image_info['views'] is not None:
                images[idx]["views"] = before_image_info['views']

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
        return seconds, "seconds"

    minutes = seconds / 60.0
    if minutes < 60:
        return minutes, "minutes"

    hours = minutes / 60.0
    if hours < 24:
        return hours, "hours"

    days = hours / 24.0
    if days < 7:
        return days, "days"

    weeks = days / 7.0
    return weeks, "weeks"

    return how_much, time_units


def set_background_image(path):
    command = 'gsettings set org.gnome.desktop.background picture-uri "file://%s"' % images[rand_image_num]['path']
    p = os.popen(command)

###############################################################
# main

images = get_file_list(image_directory)
add_image_md5s(images)


# load image data that was possibly saved from last run (eg. view count)
had_images = load_info_file(image_info_file)


images = compare_current_images_to_had_images(images, had_images)

check_for_duplicate_images(images)

write_info_file(image_info_file, images)

num_images = len(images)
seed_random()

print("num_images = %d" % num_images)

how_much, time_units = seconds_to_realistic_time(num_images*sleep_seconds)


print("It will take %0.2f %s to view all images" % (how_much, time_units))

while (1):

    loop_count = 0
    rand_image_num = 0
    min_num_views = get_min_num_views(images)

    # TODO - might want to find a better way to do this later
    while (1):
        loop_count = loop_count + 1
        if (loop_count <= num_images*10):
            rand_image_num = random.randint(0, num_images - 1) # a <= X <= b
            if (images[rand_image_num]['views'] > min_num_views):
                print ("image #%d already has %d views" % (rand_image_num, images[rand_image_num]['views']))
                next
            else:
                break
        else: # too many searches, just pick an image
            print("too many searches for view count = %d" % min_num_views)
            rand_image_num = first_image_with_view_count(images, min_num_views)
            if rand_image_num >= 0:
                print("going with image number %d" % rand_image_num)
            else:
                print("didn't find an image that has only been viewed %d times" % min_num_views)
                rand_image_num = 0
            break

    images[rand_image_num]['views'] = images[rand_image_num]['views'] + 1
    print("Using image #%s '%s'   %d" %  (rand_image_num, images[rand_image_num]['path'], images[rand_image_num]['views']))

    set_background_image(images[rand_image_num]['path'])
    write_info_file(image_info_file, images)

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
                notified = False
                break
        else:
#           print("not ready to change pic, sleeping: %s" % idle_ms)
            next
        
        time.sleep(1)
